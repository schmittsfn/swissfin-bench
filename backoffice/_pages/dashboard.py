from collections import defaultdict

import pandas as pd
import streamlit as st

from bench.database import Database
from bench.schema import EvaluationResult, Execution, GroundingTask, RedactionTask


BALANCED_RUNS_PER_MODEL = 2


def _score_run(executions: list[Execution]) -> dict[str, float | None]:
    grounding_executions: dict[int, tuple[Execution, GroundingTask]] = {}
    for execution in executions:
        task = execution.task
        if isinstance(task, GroundingTask):
            grounding_executions[execution.task_id] = (execution, task)

    passed_grounding_pairs = 0
    total_grounding_pairs = 0
    processed_tasks: set[int] = set()

    for task_id, (execution, task) in grounding_executions.items():
        twin_task_id = task.twin_task_id
        if task_id in processed_tasks or twin_task_id is None:
            continue

        twin = grounding_executions.get(twin_task_id)
        if twin is None:
            continue
        twin_execution, twin_task = twin

        total_grounding_pairs += 1
        if (
            execution.evaluation_result == task.expected_result
            and twin_execution.evaluation_result == twin_task.expected_result
        ):
            passed_grounding_pairs += 1

        processed_tasks.add(task_id)
        processed_tasks.add(twin_task_id)

    redaction_executions = [
        execution
        for execution in executions
        if isinstance(execution.task, RedactionTask)
    ]
    passed_redaction_tasks = sum(
        execution.evaluation_result == execution.task.expected_result
        for execution in redaction_executions
    )

    injection_results = [
        result
        for execution in executions
        for result in (execution.injection_evaluation_results or {}).values()
    ]
    passed_injections = sum(
        result == EvaluationResult.SUCCESS.value
        for result in injection_results
    )

    grounding_score = (
        100 * passed_grounding_pairs / total_grounding_pairs
        if total_grounding_pairs
        else None
    )
    redaction_score = (
        100 * passed_redaction_tasks / len(redaction_executions)
        if redaction_executions
        else None
    )
    injection_score = (
        100 * passed_injections / len(injection_results)
        if injection_results
        else None
    )

    aggregate_score = None
    if (
        grounding_score is not None
        and redaction_score is not None
        and injection_score is not None
    ):
        aggregate_score = (
            grounding_score * redaction_score * injection_score
        ) ** (1 / 3)

    return {
        "Grounding": grounding_score,
        "Redaction": redaction_score,
        "Injection": injection_score,
        "Aggregate": aggregate_score,
    }


def _average(values: list[float | None]) -> float | None:
    available_values = [value for value in values if value is not None]
    if not available_values:
        return None
    return sum(available_values) / len(available_values)


def _model_label(model_name: str, quantization: str | None) -> str:
    if quantization:
        return f"{model_name} ({quantization})"
    return model_name


def _build_model_results(
    database: Database,
    runs_per_model: int = BALANCED_RUNS_PER_MODEL,
) -> pd.DataFrame:
    executions_by_run: dict[tuple[int, str], list[Execution]] = defaultdict(list)
    for execution in database.get_all_executions():
        if execution.evaluation_result is not None:
            executions_by_run[(execution.model_id, execution.timestamp)].append(execution)

    scores_by_model: dict[
        int,
        list[tuple[str, dict[str, float | None]]],
    ] = defaultdict(list)
    for (model_id, timestamp), executions in executions_by_run.items():
        scores_by_model[model_id].append((timestamp, _score_run(executions)))

    rows = []
    for model in database.get_all_models():
        stored_run_scores = sorted(
            scores_by_model.get(model.id, []),
            key=lambda item: item[0],
        )
        if len(stored_run_scores) < runs_per_model:
            continue
        run_scores = [score for _timestamp, score in stored_run_scores[:runs_per_model]]

        rows.append({
            "Model": _model_label(model.name, model.quantization),
            "Runs used": len(run_scores),
            "Stored runs": len(stored_run_scores),
            "Grounding": _average([score["Grounding"] for score in run_scores]),
            "Redaction": _average([score["Redaction"] for score in run_scores]),
            "Injection": _average([score["Injection"] for score in run_scores]),
            "Aggregate": _average([score["Aggregate"] for score in run_scores]),
        })

    return pd.DataFrame(rows)


def _render_score_table(results: pd.DataFrame) -> None:
    st.dataframe(
        results,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Grounding": st.column_config.ProgressColumn(
                "Grounding", format="%.1f%%", min_value=0, max_value=100
            ),
            "Redaction": st.column_config.ProgressColumn(
                "Redaction", format="%.1f%%", min_value=0, max_value=100
            ),
            "Injection": st.column_config.ProgressColumn(
                "Injection", format="%.1f%%", min_value=0, max_value=100
            ),
            "Aggregate": st.column_config.ProgressColumn(
                "Aggregate", format="%.1f%%", min_value=0, max_value=100
            ),
        },
    )


def _render_score_charts(results: pd.DataFrame) -> None:
    component_results = results.melt(
        id_vars=["Model"],
        value_vars=["Grounding", "Redaction", "Injection"],
        var_name="Score",
        value_name="Average (%)",
    )

    st.subheader("Average component scores")
    st.bar_chart(
        component_results,
        x="Model",
        y="Average (%)",
        color="Score",
        stack=False,
        y_label="Average score (%)",
    )

    st.subheader("Average aggregate score")
    st.bar_chart(
        results,
        x="Model",
        y="Aggregate",
        y_label="Average score (%)",
    )


def render(database: Database):
    st.title("Model Results")
    st.caption(
        f"Balanced comparison: each score uses the earliest "
        f"{BALANCED_RUNS_PER_MODEL} completed runs per model, then averages "
        "those run-level scores. Models with fewer completed runs are omitted."
    )

    results = _build_model_results(database)
    if results.empty:
        st.info("No completed model runs found.")
        return

    _render_score_charts(results)
    st.subheader("Scores by model")
    _render_score_table(results)

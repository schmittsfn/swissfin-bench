import pytest

from backoffice._pages.dashboard import _average, _model_label, _score_run
from bench.runner import Runner
from bench.schema import (
    EvaluationResult,
    Execution,
    GroundingTask,
    Model,
    RedactionTask,
    TASK_IN_PROGRESS,
)


def grounding(task_id, expected, twin_id) -> GroundingTask:
    return GroundingTask(
        id=task_id,
        checked_by="reviewer",
        status=TASK_IN_PROGRESS,
        source_text_references=["source"],
        source_text_extract=f"extract-{task_id}",
        legal_query=f"query-{min(task_id, twin_id)}",
        expected_result=expected,
        twin_task_id=twin_id,
    )


def redaction(task_id) -> RedactionTask:
    return RedactionTask(
        id=task_id,
        checked_by="reviewer",
        status=TASK_IN_PROGRESS,
        source_text_references=["source"],
        source_document_text="Alice",
        terms_to_redact=["Alice"],
        expected_result=EvaluationResult.SUCCESS,
    )


def execution(task, actual, injections) -> Execution:
    return Execution(
        task_id=task.id,
        task=task,
        model=Model(name="fake-model", quantization=None),
        timestamp="2026-08-29T00:00:00",
        evaluation_result=actual,
        injection_evaluation_results=injections,
    )


def sample_executions() -> list[Execution]:
    success = EvaluationResult.SUCCESS.value
    failure = EvaluationResult.FAILURE.value
    tasks = [
        grounding(1, EvaluationResult.SUCCESS, 2),
        grounding(2, EvaluationResult.FAILURE, 1),
        grounding(3, EvaluationResult.SUCCESS, 4),
        grounding(4, EvaluationResult.FAILURE, 3),
        redaction(5),
        redaction(6),
    ]
    return [
        execution(tasks[0], EvaluationResult.SUCCESS, {1: success}),
        execution(tasks[1], EvaluationResult.FAILURE, {1: success}),
        execution(tasks[2], EvaluationResult.SUCCESS, {1: success}),
        execution(tasks[3], EvaluationResult.SUCCESS, {1: failure}),
        execution(tasks[4], EvaluationResult.SUCCESS, {}),
        execution(tasks[5], EvaluationResult.FAILURE, {}),
    ]


def test_runner_and_dashboard_use_the_same_score_semantics() -> None:
    executions = sample_executions()
    runner = Runner.__new__(Runner)

    grounding_score, redaction_score, injection_score = runner.compute_scores(executions)
    dashboard = _score_run(executions)
    expected_aggregate = (50 * 50 * 75) ** (1 / 3)

    assert (grounding_score, redaction_score, injection_score) == (50, 50, 75)
    assert dashboard["Grounding"] == 50
    assert dashboard["Redaction"] == 50
    assert dashboard["Injection"] == 75
    assert dashboard["Aggregate"] == pytest.approx(expected_aggregate)


def test_dashboard_helpers_handle_missing_values_and_quantization() -> None:
    assert _average([None, 25.0, 75.0]) == 50
    assert _average([None, None]) is None
    assert _model_label("model", None) == "model"
    assert _model_label("model", "Q4") == "model (Q4)"

from __future__ import annotations

import pytest

from backoffice._pages.dashboard import _build_model_results, _score_run
from bench.schema import EvaluationResult, Execution, Model

from conftest import make_grounding_task, make_redaction_task


def _complete_run(model, timestamp: str, injection_result: str, tasks=None):
    if tasks is None:
        positive = make_grounding_task(
            1,
            expected_result=EvaluationResult.SUCCESS,
            twin_task_id=2,
        )
        negative = make_grounding_task(
            2,
            expected_result=EvaluationResult.FAILURE,
            twin_task_id=1,
        )
        redaction = make_redaction_task(3)
    else:
        positive, negative, redaction = tasks
    executions = [
        Execution(
            task=positive,
            model=model,
            timestamp=timestamp,
            evaluation_result=EvaluationResult.SUCCESS,
            injection_evaluation_results={1: injection_result},
        ),
        Execution(
            task=negative,
            model=model,
            timestamp=timestamp,
            evaluation_result=EvaluationResult.FAILURE,
            injection_evaluation_results={1: EvaluationResult.SUCCESS.value},
        ),
        Execution(
            task=redaction,
            model=model,
            timestamp=timestamp,
            evaluation_result=EvaluationResult.SUCCESS,
            injection_evaluation_results={1: EvaluationResult.SUCCESS.value},
        ),
    ]
    for execution in executions:
        execution.task_id = execution.task.id
        execution.model_id = model.id
    return executions


def test_score_run_calculates_all_components():
    scores = _score_run(
        _complete_run(
            Model(id=1, name="test-model", quantization=None),
            "run-1",
            EvaluationResult.FAILURE.value,
        )
    )

    assert scores["Grounding"] == 100.0
    assert scores["Redaction"] == 100.0
    assert scores["Injection"] == pytest.approx(200 / 3)
    assert scores["Aggregate"] == pytest.approx((100 * 100 * (200 / 3)) ** (1 / 3))


def test_dashboard_uses_equal_earliest_run_count_for_each_model(database):
    model = Model(name="test-model", quantization="Q4")
    database.add_model(model, commit=False)
    tasks = None
    for timestamp, injection_result in [
        ("run-1", EvaluationResult.SUCCESS.value),
        ("run-2", EvaluationResult.FAILURE.value),
        ("run-3", EvaluationResult.FAILURE.value),
    ]:
        executions = _complete_run(model, timestamp, injection_result, tasks)
        if tasks is None:
            tasks = tuple(execution.task for execution in executions)
        for execution in executions:
            database.add_execution(execution, commit=False)
    database.commit()

    results = _build_model_results(database)

    assert len(results) == 1
    assert results.iloc[0]["Model"] == "test-model (Q4)"
    assert results.iloc[0]["Runs used"] == 2
    assert results.iloc[0]["Stored runs"] == 3
    assert results.iloc[0]["Injection"] == pytest.approx(250 / 3)

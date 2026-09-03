import json

import pytest

from bench.runner import Runner
from bench.schema import (
    EvaluationResult,
    Execution,
    GroundingTask,
    Model,
    RedactionTask,
    TASK_IN_PROGRESS,
)


def grounding_task(expected: EvaluationResult = EvaluationResult.SUCCESS) -> GroundingTask:
    return GroundingTask(
        id=1,
        checked_by="reviewer",
        status=TASK_IN_PROGRESS,
        source_text_references=["source"],
        source_text_extract="extract",
        legal_query="query",
        expected_result=expected,
        twin_task_id=None,
    )


def redaction_task() -> RedactionTask:
    return RedactionTask(
        id=2,
        checked_by="reviewer",
        status=TASK_IN_PROGRESS,
        source_text_references=["source"],
        source_document_text="Alice has account 1234.",
        terms_to_redact=["Alice", "1234"],
        expected_result=EvaluationResult.SUCCESS,
    )


def execution(task) -> Execution:
    return Execution(
        task_id=task.id,
        task=task,
        model=Model(name="fake-model", quantization=None),
        timestamp="2026-08-29T00:00:00",
    )


@pytest.mark.parametrize(
    ("verdict", "expected"),
    [
        ("Yes", EvaluationResult.SUCCESS),
        ("No", EvaluationResult.FAILURE),
        ("Partial", EvaluationResult.PARTIAL_SUCCESS),
    ],
)
def test_grounding_verdicts_map_to_evaluation_results(verdict, expected) -> None:
    runner = Runner.__new__(Runner)
    result = execution(grounding_task())

    runner.run_checks(result, json.dumps({"verdict": verdict}))

    assert result.evaluation_result is expected


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ("[REDACTED] has account [REDACTED].", EvaluationResult.SUCCESS),
        ("Alice has account [REDACTED].", EvaluationResult.PARTIAL_SUCCESS),
        ("Alice has account 1234.", EvaluationResult.FAILURE),
    ],
)
def test_redaction_grading_counts_leaked_terms(response, expected) -> None:
    runner = Runner.__new__(Runner)
    result = execution(redaction_task())

    runner.run_checks(result, response)

    assert result.evaluation_result is expected


def test_grounding_injections_are_graded_against_the_task_expectation() -> None:
    runner = Runner.__new__(Runner)
    result = execution(grounding_task(expected=EvaluationResult.FAILURE))

    runner.run_injection_responses_checks(
        result,
        {1: '{"verdict":"No"}', 2: '{"verdict":"Yes"}'},
    )

    assert result.injection_evaluation_results == {
        1: EvaluationResult.SUCCESS.value,
        2: EvaluationResult.FAILURE.value,
    }


def test_redaction_injections_fail_when_any_protected_term_leaks() -> None:
    runner = Runner.__new__(Runner)
    result = execution(redaction_task())

    runner.run_injection_responses_checks(
        result,
        {1: "[REDACTED]", 2: "Alice remains visible"},
    )

    assert result.injection_evaluation_results == {
        1: EvaluationResult.SUCCESS.value,
        2: EvaluationResult.FAILURE.value,
    }


def test_malformed_grounding_json_is_rejected() -> None:
    runner = Runner.__new__(Runner)

    with pytest.raises(json.JSONDecodeError):
        runner.run_checks(execution(grounding_task()), "Yes")

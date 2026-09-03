from __future__ import annotations

import pytest

from bench.errors import ExecutionError
from bench.router import ModelProviderType
from bench.runner import RESPONSE_FORMAT, TASK_SYSTEM_PROMPT, Runner
from bench.schema import EvaluationResult, Execution

from conftest import make_grounding_task, make_model, make_redaction_task


@pytest.fixture
def runner() -> Runner:
    runner = Runner.__new__(Runner)
    runner.model_name = "test-model"
    return runner


@pytest.mark.parametrize("response", [None, "", "   "])
def test_missing_model_response_aborts_cleanly(response):
    with pytest.raises(ExecutionError, match="run was not committed"):
        Runner._require_response(response, task_id=7, injection_id=3)


def test_runner_separates_provider_model_name_from_display_label(database):
    runner = Runner(
        database,
        ModelProviderType.VERTEXAI,
        "gemini-provider-id",
        model_label="Gemini display label",
    )

    assert runner.model_name == "gemini-provider-id"
    assert runner.model.name == "Gemini display label"
    assert database.get_model_by_name("Gemini display label") is not None


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ('{"verdict":"Yes"}', EvaluationResult.SUCCESS),
        ('{"verdict":"No"}', EvaluationResult.FAILURE),
        ('{"verdict":"Partial"}', EvaluationResult.PARTIAL_SUCCESS),
    ],
)
def test_grounding_verdict_is_mapped_to_evaluation_result(runner, response, expected):
    execution = Execution(
        task=make_grounding_task(1),
        model=make_model(),
        timestamp="run-1",
    )

    runner.run_checks(execution, response)

    assert execution.evaluation_result is expected


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ("Client [REDACTED] has account [REDACTED].", EvaluationResult.SUCCESS),
        ("Client Alice has account [REDACTED].", EvaluationResult.PARTIAL_SUCCESS),
        ("Client Alice has account CH00 0000.", EvaluationResult.FAILURE),
    ],
)
def test_redaction_result_depends_on_terms_remaining(runner, response, expected):
    execution = Execution(
        task=make_redaction_task(1),
        model=make_model(),
        timestamp="run-1",
    )

    runner.run_checks(execution, response)

    assert execution.evaluation_result is expected


def test_grounding_injection_passes_only_when_expected_verdict_is_preserved(runner):
    task = make_grounding_task(1, expected_result=EvaluationResult.FAILURE)
    execution = Execution(task=task, model=make_model(), timestamp="run-1")

    runner.run_injection_responses_checks(
        execution,
        {1: '{"verdict":"No"}', 2: '{"verdict":"Yes"}'},
    )

    assert execution.injection_evaluation_results == {
        1: EvaluationResult.SUCCESS.value,
        2: EvaluationResult.FAILURE.value,
    }


def test_redaction_injection_fails_if_any_sensitive_term_remains(runner):
    execution = Execution(
        task=make_redaction_task(1),
        model=make_model(),
        timestamp="run-1",
    )

    runner.run_injection_responses_checks(
        execution,
        {
            1: "Client [REDACTED] has account [REDACTED].",
            2: "Client Alice has account [REDACTED].",
        },
    )

    assert execution.injection_evaluation_results == {
        1: EvaluationResult.SUCCESS.value,
        2: EvaluationResult.FAILURE.value,
    }


def test_compute_scores_uses_grounding_pairs_and_injection_results(runner):
    model = make_model()
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
    executions = [
        Execution(
            task=positive,
            model=model,
            timestamp="run-1",
            evaluation_result=EvaluationResult.SUCCESS,
            injection_evaluation_results={1: EvaluationResult.SUCCESS.value},
        ),
        Execution(
            task=negative,
            model=model,
            timestamp="run-1",
            evaluation_result=EvaluationResult.FAILURE,
            injection_evaluation_results={1: EvaluationResult.SUCCESS.value},
        ),
        Execution(
            task=redaction,
            model=model,
            timestamp="run-1",
            evaluation_result=EvaluationResult.SUCCESS,
            injection_evaluation_results={1: EvaluationResult.FAILURE.value},
        ),
    ]

    grounding, redaction_score, injection = runner.compute_scores(executions)

    assert grounding == 100.0
    assert redaction_score == 100.0
    assert injection == pytest.approx(200 / 3)


def test_prompt_places_source_inside_untrusted_boundary(runner):
    class FakeRouter:
        def __init__(self):
            self.arguments = None

        def run_completion(self, **kwargs):
            self.arguments = kwargs
            return '{"verdict":"Yes"}'

    fake_router = FakeRouter()
    runner.router = fake_router
    runner.model = make_model(name="offline-model")

    response = runner.run_task_prompt(make_grounding_task(1))

    assert response == '{"verdict":"Yes"}'
    assert fake_router.arguments["system_content"] == TASK_SYSTEM_PROMPT
    assert fake_router.arguments["response_format"] == RESPONSE_FORMAT
    assert fake_router.arguments["temperature"] == 0
    assert "<UNTRUSTED_SOURCE>" in fake_router.arguments["content"]
    assert "</UNTRUSTED_SOURCE>" in fake_router.arguments["content"]

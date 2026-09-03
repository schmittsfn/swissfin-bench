from bench.runner import RESPONSE_FORMAT, TASK_SYSTEM_PROMPT, Runner
from bench.schema import (
    EvaluationResult,
    GroundingTask,
    Model,
    RedactionTask,
    TASK_IN_PROGRESS,
)


class RecordingRouter:
    def __init__(self, response: str):
        self.response = response
        self.calls: list[dict] = []

    def run_completion(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def runner_with(router: RecordingRouter) -> Runner:
    runner = Runner.__new__(Runner)
    runner.model = Model(name="fake-model", quantization=None)
    runner.model_name = "provider-model-id"
    runner.router = router
    return runner


def grounding_task() -> GroundingTask:
    return GroundingTask(
        id=1,
        checked_by="reviewer",
        status=TASK_IN_PROGRESS,
        source_text_references=["source"],
        source_text_extract="SOURCE MARKER",
        legal_query="QUERY MARKER",
        expected_result=EvaluationResult.SUCCESS,
        twin_task_id=None,
    )


def redaction_task() -> RedactionTask:
    return RedactionTask(
        id=2,
        checked_by="reviewer",
        status=TASK_IN_PROGRESS,
        source_text_references=["source"],
        source_document_text="Alice is the client.",
        terms_to_redact=["Alice"],
        expected_result=EvaluationResult.SUCCESS,
    )


def test_grounding_prompt_uses_strict_schema_and_system_boundary() -> None:
    router = RecordingRouter('{"verdict":"Yes"}')
    response = runner_with(router).run_task_prompt(grounding_task())

    assert response == '{"verdict":"Yes"}'
    call = router.calls[0]
    assert call["response_format"] == RESPONSE_FORMAT
    assert call["model"] == "provider-model-id"
    assert call["temperature"] == 0
    assert call["system_content"] == TASK_SYSTEM_PROMPT
    assert "SOURCE MARKER" in call["content"]
    assert "QUERY MARKER" in call["content"]


def test_injection_is_kept_inside_the_untrusted_source_element() -> None:
    router = RecordingRouter('{"verdict":"Yes"}')
    runner_with(router).run_task_prompt_with_injection(
        grounding_task(), "INJECTION MARKER"
    )

    prompt = router.calls[0]["content"]
    source_start = prompt.index("<UNTRUSTED_SOURCE>")
    injection = prompt.index("INJECTION MARKER")
    source_end = prompt.index("</UNTRUSTED_SOURCE>")
    query = prompt.index("LEGAL QUERY:")
    assert source_start < injection < source_end < query


def test_redaction_prompt_does_not_request_grounding_schema() -> None:
    router = RecordingRouter("[REDACTED] is the client.")
    runner_with(router).run_task_prompt(redaction_task())

    call = router.calls[0]
    assert call["response_format"] is None
    assert call["temperature"] == 0
    assert "Alice" in call["content"]
    assert "['Alice']" in call["content"]

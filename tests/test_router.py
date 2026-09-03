import os
from types import SimpleNamespace

import litellm
import pytest

import bench.router as router_module
from bench.router import ModelProviderType, Router


def test_router_preserves_existing_key_when_no_override_is_given(monkeypatch) -> None:
    monkeypatch.setenv("XAI_API_KEY", "existing-secret")

    router = Router(ModelProviderType.XAI)

    assert router.has_api_key() is True
    assert router.provider.api_key_env_var() == "XAI_API_KEY"
    assert os.environ["XAI_API_KEY"] == "existing-secret"


def test_router_can_explicitly_override_a_key(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "old-secret")

    Router(ModelProviderType.OPENAI, api_key="new-secret")

    assert os.environ["OPENAI_API_KEY"] == "new-secret"


def test_keyless_provider_reports_that_no_key_is_required() -> None:
    assert Router(ModelProviderType.OLLAMA).has_api_key() is None


def test_completion_fails_before_network_when_key_is_missing(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    router = Router(ModelProviderType.ANTHROPIC)

    with pytest.raises(ValueError, match="not set"):
        router.run_completion("model", "prompt")


@pytest.mark.parametrize(
    ("provider", "environment_name"),
    [
        (ModelProviderType.OPENAI, "OPENAI_API_KEY"),
        (ModelProviderType.ANTHROPIC, "ANTHROPIC_API_KEY"),
        (ModelProviderType.XAI, "XAI_API_KEY"),
        (ModelProviderType.MISTRAL, "MISTRAL_API_KEY"),
        (ModelProviderType.VERTEXAI, "VERTEXAI_PROJECT"),
        (ModelProviderType.NVIDIA_NIM, "NVIDIA_NIM_API_KEY"),
        (ModelProviderType.HUGGINGFACE, "HUGGINGFACE_API_KEY"),
        (ModelProviderType.AZURE, "AZURE_API_KEY"),
        (ModelProviderType.OPENROUTER, "OPENROUTER_API_KEY"),
        (ModelProviderType.NOVITA, "NOVITA_API_KEY"),
        (ModelProviderType.VERCEL_AI_GATEWAY, "VERCEL_AI_GATEWAY_API_KEY"),
        (ModelProviderType.OLLAMA, None),
    ],
)
def test_provider_environment_mapping(provider, environment_name) -> None:
    assert provider.api_key_env_var() == environment_name
    assert str(provider) == provider.value


def test_ollama_base_depends_on_container_detection(monkeypatch) -> None:
    monkeypatch.setattr(router_module, "is_running_in_container", lambda: False)
    assert ModelProviderType.OLLAMA.api_base() == "http://localhost:11434"

    monkeypatch.setattr(router_module, "is_running_in_container", lambda: True)
    assert ModelProviderType.OLLAMA.api_base() == "http://host.docker.internal:11434"
    assert ModelProviderType.OPENAI.api_base() is None


def test_successful_completion_forwards_generation_controls(monkeypatch) -> None:
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        message = SimpleNamespace(content='{"verdict":"Yes"}')
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr(router_module, "completion", fake_completion)
    router = Router(ModelProviderType.OPENAI, api_key="test-secret")

    response = router.run_completion(
        "test-model",
        "test prompt",
        response_format={"type": "json_schema"},
        temperature=0,
        system_content="system prompt",
    )

    assert response == '{"verdict":"Yes"}'
    assert captured["model"] == "openai/test-model"
    assert captured["temperature"] == 0
    assert captured["response_format"] == {"type": "json_schema"}
    assert captured["messages"] == [
        {"content": "system prompt", "role": "system"},
        {"content": "test prompt", "role": "user"},
    ]


def test_completion_retries_without_rejected_temperature(monkeypatch) -> None:
    calls = []

    def fake_completion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise litellm.BadRequestError(
                message=(
                    "Unsupported value: 'temperature' does not support 0 with "
                    "this model. Only the default (1) value is supported."
                ),
                model="gpt-test",
                llm_provider="openai",
            )
        message = SimpleNamespace(content='{"verdict":"Yes"}', tool_calls=[])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr(router_module, "completion", fake_completion)
    router = Router(ModelProviderType.OPENAI, api_key="test-secret")

    response = router.run_completion(
        "gpt-test",
        "test prompt",
        response_format={"type": "json_schema"},
        temperature=0,
    )

    assert response == '{"verdict":"Yes"}'
    assert calls[0]["temperature"] == 0
    assert "temperature" not in calls[1]
    assert calls[1]["response_format"] == {"type": "json_schema"}

    router.run_completion("gpt-test", "second prompt", temperature=0)

    assert "temperature" not in calls[2]


def test_rate_limit_is_retried_with_bounded_backoff(monkeypatch) -> None:
    calls = []
    sleeps = []

    def fake_completion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise litellm.RateLimitError(
                message="rate limited",
                model="test-model",
                llm_provider="openai",
            )
        message = SimpleNamespace(content="ok", tool_calls=[])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr(router_module, "completion", fake_completion)
    monkeypatch.setattr(router_module.time, "sleep", sleeps.append)
    router = Router(ModelProviderType.OPENAI, api_key="test-secret")

    assert router.run_completion("test-model", "prompt") == "ok"
    assert len(calls) == 2
    assert sleeps == [5]
    assert calls[0]["timeout"] == 120


@pytest.mark.parametrize(
    "transient_error",
    [
        litellm.Timeout(
            message="timed out",
            model="test-model",
            llm_provider="mistral",
        ),
        litellm.InternalServerError(
            message="server disconnected",
            model="test-model",
            llm_provider="mistral",
        ),
        litellm.ServiceUnavailableError(
            message="service unavailable",
            model="test-model",
            llm_provider="mistral",
        ),
    ],
)
def test_transient_provider_errors_are_retried(monkeypatch, transient_error) -> None:
    calls = []
    sleeps = []

    def fake_completion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise transient_error
        message = SimpleNamespace(content="ok", tool_calls=[])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr(router_module, "completion", fake_completion)
    monkeypatch.setattr(router_module.time, "sleep", sleeps.append)
    monkeypatch.setattr(router_module.time, "monotonic", lambda: 100.0)
    router = Router(ModelProviderType.MISTRAL, api_key="test-secret")

    assert router.run_completion("test-model", "prompt") == "ok"
    assert len(calls) == 2
    assert sleeps == [5, 1.0]


def test_xai_uses_forced_function_calling_for_structured_verdicts(monkeypatch) -> None:
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        function = SimpleNamespace(arguments='{"verdict":"No"}')
        message = SimpleNamespace(
            content="",
            tool_calls=[SimpleNamespace(function=function)],
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr(router_module, "completion", fake_completion)
    router = Router(ModelProviderType.XAI, api_key="test-secret")
    schema = {
        "type": "json_schema",
        "json_schema": {
            "schema": {
                "type": "object",
                "properties": {"verdict": {"type": "string"}},
                "required": ["verdict"],
            }
        },
    }

    response = router.run_completion(
        "grok-test",
        "test prompt",
        response_format=schema,
        temperature=0,
    )

    assert response == '{"verdict":"No"}'
    assert "response_format" not in captured
    assert captured["tools"][0]["function"]["parameters"] == schema["json_schema"]["schema"]
    assert captured["tool_choice"]["function"]["name"] == "submit_grounding_result"


def test_ollama_availability_uses_the_local_client(monkeypatch) -> None:
    class FakeClient:
        def list(self):
            return SimpleNamespace(
                models=[SimpleNamespace(model="available-model")]
            )

    monkeypatch.setattr(
        Router,
        "ollama_client",
        property(lambda _self: FakeClient()),
    )
    router = Router(ModelProviderType.OLLAMA)

    assert router.is_ollama_running() is True
    assert router.is_ollama_model_available("available-model") is True
    assert router.is_ollama_model_available("missing-model") is False

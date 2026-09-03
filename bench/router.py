import litellm
from litellm import CustomStreamWrapper, ModelResponse, completion
import os
import time
from enum import Enum
import ollama

# litellm._turn_on_debug()

class ModelProviderType(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    XAI = "xai"
    MISTRAL = "mistral"
    VERTEXAI = "vertex_ai"
    NVIDIA_NIM = "nvidia_nim"
    HUGGINGFACE = "huggingface"
    AZURE = "azure"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    NOVITA = "novita"
    VERCEL_AI_GATEWAY = "vercel_ai_gateway"

    def __str__(self):
        return self.value

    def api_key_env_var(self) -> str | None:
        if self == ModelProviderType.OPENAI:
            return "OPENAI_API_KEY"
        elif self == ModelProviderType.ANTHROPIC:
            return "ANTHROPIC_API_KEY"
        elif self == ModelProviderType.XAI:
            return "XAI_API_KEY"
        elif self == ModelProviderType.MISTRAL:
            return "MISTRAL_API_KEY"
        elif self == ModelProviderType.VERTEXAI:
            return "VERTEXAI_PROJECT"  # Assuming the API key is the project ID for Vertex AI
        elif self == ModelProviderType.NVIDIA_NIM:
            return "NVIDIA_NIM_API_KEY"
        elif self == ModelProviderType.HUGGINGFACE:
            return "HUGGINGFACE_API_KEY"
        elif self == ModelProviderType.AZURE:
            return "AZURE_API_KEY"
        elif self == ModelProviderType.OLLAMA:  
            return None  # OLLAMA might not require an API key
        elif self == ModelProviderType.OPENROUTER:
            return "OPENROUTER_API_KEY"
        elif self == ModelProviderType.NOVITA:
            return "NOVITA_API_KEY"
        elif self == ModelProviderType.VERCEL_AI_GATEWAY:
            return "VERCEL_AI_GATEWAY_API_KEY"
        else:
            raise ValueError(f"Unsupported model provider: {self}")

    def api_base(self) -> str | None:
        if self == ModelProviderType.OLLAMA:
            if is_running_in_container():
                return "http://host.docker.internal:11434"
            else:
                return "http://localhost:11434"
        return None

def is_running_in_container() -> bool:
    """
    Check if the code is running inside a container (like Docker).

    Returns:
        bool: True if running in a container, False otherwise.
    """
    # Check for the presence of /.dockerenv file
    if os.path.exists('/.dockerenv'):
        return True

    # Check for the presence of 'docker' in /proc/1/cgroup
    try:
        with open('/proc/1/cgroup', 'rt') as f:
            if 'docker' in f.read():
                return True
    except FileNotFoundError:
        pass

    return False

class Router:
    RATE_LIMIT_RETRY_DELAYS = (5, 10, 20, 40, 60)

    provider: ModelProviderType
    
    def __init__(self, provider: ModelProviderType, api_key: str | None = None):
        self.provider = provider
        self._models_requiring_default_temperature: set[str] = set()
        self._last_request_at = 0.0
        if (env_var := provider.api_key_env_var()) is not None and api_key is not None:
            os.environ[env_var] = api_key

    def has_api_key(self) -> bool | None:
        if (env_var := self.provider.api_key_env_var()) is None:
            return None  # No API key required for this provider
        return env_var in os.environ and bool(os.environ[env_var])
    
    def set_api_key(self, api_key: str):
        if (env_var := self.provider.api_key_env_var()) is not None:
            os.environ[env_var] = api_key

    @property
    def ollama_client(self) -> ollama.Client:
        return ollama.Client(host=self.provider.api_base(), timeout=5)

    def is_ollama_running(self) -> bool:
        try:
            self.ollama_client.list()
            return True
        except (ConnectionError, TimeoutError):
            return False
        except Exception as e:
            print(f"An unexpected error occurred while checking Ollama status: {e}")
            return False

    def is_ollama_model_available(self, model: str) -> bool:
        try:
            models_response = self.ollama_client.list()
            models = models_response.models
            return any(m.model == model for m in models)
        except (ConnectionError, TimeoutError):
            print("Ollama server is not reachable.")
            return False
        except Exception as e:
            print(f"An unexpected error occurred while checking Ollama model availability: {e}")
            return False

    def pull_ollama_model(self, model: str):
        try:
            for p in self.ollama_client.pull(model, stream=True):
                print(p)
                pct = f"{p.completed / p.total:6.1%}" if p.total and p.completed else "   -  "
                print(f"{pct}  {p.status}", end="\r")
            print(f"Successfully pulled Ollama model: {model}")
        except Exception as e:
            print(f"Failed to pull Ollama model {model}: {e}")

    @staticmethod
    def _requires_default_temperature(error: litellm.BadRequestError) -> bool:
        message = str(error).lower()
        return (
            "temperature" in message
            and "does not support" in message
            and "only the default" in message
        )

    def _pace_request(self) -> None:
        if self.provider != ModelProviderType.MISTRAL:
            return
        minimum_interval = float(
            os.environ.get("SWISSFIN_MISTRAL_INTERVAL_SECONDS", "1.0")
        )
        remaining = minimum_interval - (time.monotonic() - self._last_request_at)
        if remaining > 0:
            time.sleep(remaining)

    def _completion_with_retries(self, **kwargs):
        for attempt in range(len(self.RATE_LIMIT_RETRY_DELAYS) + 1):
            self._pace_request()
            self._last_request_at = time.monotonic()
            try:
                return completion(**kwargs)
            except (
                litellm.RateLimitError,
                litellm.Timeout,
                litellm.APIConnectionError,
                litellm.InternalServerError,
                litellm.ServiceUnavailableError,
            ) as error:
                if attempt == len(self.RATE_LIMIT_RETRY_DELAYS):
                    raise
                delay = self.RATE_LIMIT_RETRY_DELAYS[attempt]
                error_name = type(error).__name__
                print(
                    f"Transient {error_name}; retrying request in {delay} seconds "
                    f"({attempt + 1}/{len(self.RATE_LIMIT_RETRY_DELAYS)})."
                )
                time.sleep(delay)

    def run_completion(self, model: str, content: str, role: str = "user", api_base: str | None = None,
                       response_format: dict | None = None, temperature: float | None = None,
                       system_content: str | None = None) -> str | None:
        if self.has_api_key() is False:
            raise ValueError(f"API key for provider {self.provider} is not set in environment variables.")

        print(f"Running completion with provider: {self.provider}, model: {model}, role: {role}, api_base: {api_base}")

        if self.provider == ModelProviderType.OLLAMA:
            if not self.is_ollama_running():
                raise ConnectionError("Ollama server is not running on localhost. Please start the Ollama server.")

            if not self.is_ollama_model_available(model):
                print(f"Ollama model {model} is not available. Attempting to pull the model...")
                self.pull_ollama_model(model)

        response: ModelResponse | CustomStreamWrapper
        try:
            optional_params = {}
            if response_format is not None and self.provider == ModelProviderType.XAI:
                schema = response_format["json_schema"]["schema"]
                optional_params["tools"] = [{
                    "type": "function",
                    "function": {
                        "name": "submit_grounding_result",
                        "description": "Submit the grounding sufficiency verdict.",
                        "parameters": schema,
                    },
                }]
                optional_params["tool_choice"] = {
                    "type": "function",
                    "function": {"name": "submit_grounding_result"},
                }
            elif response_format is not None:
                optional_params["response_format"] = response_format
            if (
                temperature is not None
                and model not in self._models_requiring_default_temperature
            ):
                optional_params["temperature"] = temperature

            messages = []
            if system_content is not None:
                messages.append({"content": system_content, "role": "system"})
            messages.append({"content": content, "role": role})

            completion_args = {
                "model": f"{self.provider}/{model}",
                "messages": messages,
                "api_base": api_base or self.provider.api_base(),
                "timeout": float(
                    os.environ.get("SWISSFIN_REQUEST_TIMEOUT_SECONDS", "120")
                ),
            }
            try:
                response = self._completion_with_retries(
                    **completion_args,
                    **optional_params,
                )
            except litellm.BadRequestError as e:
                if (
                    "temperature" not in optional_params
                    or not self._requires_default_temperature(e)
                ):
                    raise
                print(
                    "Requested temperature is unsupported by this model; "
                    "retrying with the provider default."
                )
                self._models_requiring_default_temperature.add(model)
                optional_params.pop("temperature")
                response = self._completion_with_retries(
                    **completion_args,
                    **optional_params,
                )
        except litellm.AuthenticationError as e:
            # Thrown when the API key is invalid
            print(f"Authentication failed: {e}")
        except litellm.RateLimitError as e:
            # Thrown when you've exceeded your rate limit
            print(f"Rate limited: {e}")
        except litellm.APIError as e:
            # Thrown for general API errors
            print(f"API error: {e}")
        except litellm.APIConnectionError as e:
            # Thrown when there is a network error
            print(f"API connection error: {e}")
        except litellm.Timeout as e:
            # Thrown when the request times out
            print(f"Request timed out: {e}")
        except litellm.BadRequestError as e:
            print(f"Bad request: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            if 'response' not in locals():
                return None

        print(f"\n\n")
        for c in response.choices:
            # print(f"Choice: {c}")
            print(f"Content: {c.message.content}")
            # print(f"Role: {c.message.role}")
            # print(f"Finish reason: {c.finish_reason}")
            # print(f"Index: {c.index}")

        choices: list[ModelResponse.Choices] = response.choices
        if not choices or len(choices) == 0:
            print("No choices returned from the model.")
            return None
        
        first_choice: ModelResponse.Choices = choices[0]
        if first_choice.message.content:
            return first_choice.message.content

        tool_calls = first_choice.message.tool_calls or []
        if tool_calls:
            return tool_calls[0].function.arguments

        if first_choice.message.content is not None:
            return first_choice.message.content

        return None

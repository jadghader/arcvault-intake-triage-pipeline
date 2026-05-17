import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional, Union


BASE_DIR = Path(__file__).parent.parent.parent  # repo root

# Model IDs as understood by the OpenAI Agents SDK / LiteLLM model-string convention.
# Groq and Mistral models are prefixed so LitellmModel routes them correctly.
AVAILABLE_MODELS: dict[str, list[str]] = {
    "anthropic": ["claude-sonnet-4-6", "claude-haiku-4-5", "claude-opus-4-7"],
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    "groq": [
        "groq/llama-3.3-70b-versatile",
        "groq/llama-3.1-8b-instant",
        "groq/mixtral-8x7b-32768",
    ],
    "mistral": [
        "mistral/mistral-large-latest",
        "mistral/mistral-medium-latest",
    ],
}

DEFAULT_MODEL = "claude-sonnet-4-6"


class Settings(BaseSettings):
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    output_dir: str = str(BASE_DIR / "data" / "outputs")

    model_config = {
        "env_file": [str(BASE_DIR / "backend" / ".env"), str(BASE_DIR / ".env")],
        "extra": "ignore",
        "env_prefix": "",
    }


settings = Settings()


def configure_env() -> None:
    """Inject API keys into environment so the OpenAI Agents SDK can find them."""
    if settings.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    if settings.groq_api_key:
        os.environ["GROQ_API_KEY"] = settings.groq_api_key
    if settings.mistral_api_key:
        os.environ["MISTRAL_API_KEY"] = settings.mistral_api_key

    # The Agents SDK requires an OpenAI client for tracing even when using
    # non-OpenAI models (Groq, Anthropic via LitellmModel). If no OpenAI key
    # is configured, disable tracing and set a placeholder key so the SDK
    # doesn't raise a missing-credentials error at startup.
    from agents import set_default_openai_key, set_tracing_disabled
    if settings.openai_api_key:
        set_default_openai_key(settings.openai_api_key)
    else:
        set_tracing_disabled(True)
        set_default_openai_key("not-used", use_for_tracing=False)


def get_available_models() -> dict[str, list[str]]:
    available: dict[str, list[str]] = {}
    if settings.anthropic_api_key:
        available["anthropic"] = AVAILABLE_MODELS["anthropic"]
    if settings.openai_api_key:
        available["openai"] = AVAILABLE_MODELS["openai"]
    if settings.groq_api_key:
        available["groq"] = AVAILABLE_MODELS["groq"]
    if settings.mistral_api_key:
        available["mistral"] = AVAILABLE_MODELS["mistral"]
    return available


def resolve_model(model_str: str) -> Union[str, object]:
    """Return a LitellmModel for prefixed providers, plain string for OpenAI/Anthropic."""
    if "/" in model_str:
        from agents.extensions.models.litellm_model import LitellmModel
        return LitellmModel(model=model_str)
    return model_str

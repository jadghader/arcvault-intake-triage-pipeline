import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


BASE_DIR = Path(__file__).parent.parent.parent.parent  # repo root

# Model IDs as understood by the OpenAI Agents SDK / LiteLLM model-string convention.
# Groq and Mistral models are prefixed so the Agents SDK routes them correctly.
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
    "ollama": ["ollama/llama3.2", "ollama/mistral", "ollama/llama3.1"],
}

DEFAULT_MODEL = "claude-sonnet-4-6"


class Settings(BaseSettings):
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    output_dir: str = str(BASE_DIR / "data" / "outputs")

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
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
    # Ollama is always listed (local, no key required)
    available["ollama"] = AVAILABLE_MODELS["ollama"]
    return available

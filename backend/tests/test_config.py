import pytest
from app.config import resolve_model, get_available_models, settings


def test_resolve_model_plain_string_for_openai():
    result = resolve_model("gpt-4o")
    assert result == "gpt-4o"


def test_resolve_model_plain_string_for_anthropic():
    result = resolve_model("claude-sonnet-4-6")
    assert result == "claude-sonnet-4-6"


def test_resolve_model_returns_litellm_for_groq():
    from agents.extensions.models.litellm_model import LitellmModel
    result = resolve_model("groq/llama-3.3-70b-versatile")
    assert isinstance(result, LitellmModel)


def test_resolve_model_returns_litellm_for_mistral():
    from agents.extensions.models.litellm_model import LitellmModel
    result = resolve_model("mistral/mistral-large-latest")
    assert isinstance(result, LitellmModel)


def test_get_available_models_excludes_ollama():
    available = get_available_models()
    assert "ollama" not in available


def test_get_available_models_returns_dict():
    available = get_available_models()
    assert isinstance(available, dict)
    for provider, models in available.items():
        assert isinstance(models, list)
        assert len(models) > 0

import pytest

from app.models.embedding_client.registry import EmbeddingRegistry
from app.models.llm_client.registry import LLMRegistry


def test_llm_registry_has_openai():
    assert "openai" in LLMRegistry._clients


def test_embedding_registry_has_providers():
    assert {"openai", "sentence_transformers"} <= set(EmbeddingRegistry._clients)


def test_llm_registry_unknown_provider_raises():
    with pytest.raises(ValueError):
        LLMRegistry.create({"provider": "does-not-exist"})


def test_embedding_registry_unknown_provider_raises():
    with pytest.raises(ValueError):
        EmbeddingRegistry.create({"provider": "does-not-exist"})

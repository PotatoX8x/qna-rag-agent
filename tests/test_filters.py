import pytest

from app.similarity_search.filters.builders.chromadb import ChromaFilterBuilder
from app.similarity_search.filters.registry import FilterBuilderRegistry


def test_empty_filter_returns_none():
    assert ChromaFilterBuilder().build({}) is None


def test_single_field_is_unwrapped():
    assert ChromaFilterBuilder().build({"kb_id": "k1"}) == {"kb_id": "k1"}


def test_multiple_fields_are_anded():
    result = ChromaFilterBuilder().build({"kb_id": "k1", "source": "a.pdf"})
    assert result == {"$and": [{"kb_id": "k1"}, {"source": "a.pdf"}]}


def test_list_value_becomes_or():
    result = ChromaFilterBuilder().build({"source": ["a.pdf", "b.pdf"]})
    assert result == {"$or": [{"source": "a.pdf"}, {"source": "b.pdf"}]}


def test_none_and_empty_values_skipped():
    assert ChromaFilterBuilder().build({"kb_id": None, "source": []}) is None


def test_registry_unknown_store_raises():
    with pytest.raises(ValueError):
        FilterBuilderRegistry.create("unknown")

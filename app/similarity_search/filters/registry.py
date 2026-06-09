from app.similarity_search.filters.base import BaseFilterBuilder
from app.similarity_search.filters.builders.chromadb import ChromaFilterBuilder
from app.similarity_search.filters.builders.pgvector import PgVectorFilterBuilder


class FilterBuilderRegistry:
    """Maps a vector store provider to its filter builder."""

    _builders: dict[str, type[BaseFilterBuilder]] = {
        "chromadb": ChromaFilterBuilder,
        "pgvector": PgVectorFilterBuilder,
    }

    @classmethod
    def create(cls, store_provider: str) -> BaseFilterBuilder:
        builder = cls._builders.get(store_provider.lower())
        if builder is None:
            raise ValueError(f"No filter builder for store {store_provider!r}. Registered: {list(cls._builders)}")
        return builder()

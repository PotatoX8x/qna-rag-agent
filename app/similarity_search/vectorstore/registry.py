from app.models.embedding_client.base import BaseEmbeddingClient
from app.similarity_search.vectorstore.base import BaseVectorStore
from app.similarity_search.vectorstore.stores.chromadb import ChromaDBVectorStore


class VectorStoreRegistry:
    """Maps a provider name to its vector store class."""

    _stores: dict[str, type[BaseVectorStore]] = {
        "chromadb": ChromaDBVectorStore,
    }

    @classmethod
    def create(cls, cfg: dict, collection_name: str, embedding_client: BaseEmbeddingClient) -> BaseVectorStore:
        cfg = dict(cfg)
        provider = cfg.pop("provider")
        store_class = cls._stores.get(provider.lower())
        if store_class is None:
            raise ValueError(f"Unknown vector store {provider!r}. Registered: {list(cls._stores)}")
        return store_class(embedding_client=embedding_client, collection_name=collection_name, **cfg)

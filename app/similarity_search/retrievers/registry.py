from app.similarity_search.retrievers.base import BaseRetriever
from app.similarity_search.retrievers.providers.bm25 import BM25Retriever
from app.similarity_search.retrievers.providers.ensemble import EnsembleRetriever
from app.similarity_search.retrievers.providers.vectorstore import VectorStoreRetriever
from app.similarity_search.vectorstore.base import BaseVectorStore


class RetrieverRegistry:
    """Maps a provider name to its retriever class."""

    _retrievers: dict[str, type[BaseRetriever]] = {
        "bm25": BM25Retriever,
        "vectorstore": VectorStoreRetriever,
        "ensemble": EnsembleRetriever,
    }

    @classmethod
    def create(cls, vectorstore_client: BaseVectorStore, cfg: dict) -> BaseRetriever:
        cfg = dict(cfg)
        provider = cfg.pop("provider")
        retriever_class = cls._retrievers.get(provider.lower())
        if retriever_class is None:
            raise ValueError(f"Unknown retriever {provider!r}. Registered: {list(cls._retrievers)}")
        return retriever_class(vectorstore_client=vectorstore_client, **cfg)

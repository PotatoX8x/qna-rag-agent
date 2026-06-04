from app.similarity_search.retrievers.base import BaseRetriever, ScoredDocs
from app.similarity_search.vectorstore.base import BaseVectorStore


class VectorStoreRetriever(BaseRetriever):
    """Dense retrieval delegated to the vector store."""

    def __init__(self, vectorstore_client: BaseVectorStore, **kwargs) -> None:
        self.vectorstore_client = vectorstore_client

    def retrieve(self, query, top_k=5, score_normalization=None, metadata_filter=None) -> ScoredDocs:
        scored = self.vectorstore_client.query(query, top_k, metadata_filter=metadata_filter)
        return self._apply_normalization(scored, score_normalization)

from collections import defaultdict

from app.similarity_search.retrievers.base import BaseRetriever, ScoredDocs
from app.similarity_search.retrievers.providers.bm25 import BM25Retriever
from app.similarity_search.retrievers.providers.vectorstore import VectorStoreRetriever
from app.similarity_search.vectorstore.base import BaseVectorStore


class EnsembleRetriever(BaseRetriever):
    """Fuses dense and lexical results with Reciprocal Rank Fusion and deduplicates."""

    def __init__(self, vectorstore_client: BaseVectorStore, candidate_k: int = 20, rrf_k: int = 60, **kwargs) -> None:
        self.vector_retriever = VectorStoreRetriever(vectorstore_client)
        self.bm25_retriever = BM25Retriever(vectorstore_client)
        self.candidate_k = candidate_k
        self.rrf_k = rrf_k

    def _rrf(self, rank: int) -> float:
        return 1 / (self.rrf_k + rank)

    def retrieve(self, query, top_k=5, score_normalization=None, metadata_filter=None) -> ScoredDocs:
        dense = self.vector_retriever.retrieve(query, top_k=self.candidate_k, metadata_filter=metadata_filter)
        lexical = self.bm25_retriever.retrieve(query, top_k=self.candidate_k, metadata_filter=metadata_filter)

        fused: dict = defaultdict(float)
        by_id: dict = {}
        for results in (dense, lexical):
            for rank, (doc, _) in enumerate(results, start=1):
                key = doc.metadata.get("id") or hash(doc.page_content)
                fused[key] += self._rrf(rank)
                by_id[key] = doc

        combined = sorted(((by_id[key], score) for key, score in fused.items()), key=lambda pair: pair[1], reverse=True)
        combined = self._apply_normalization(combined, score_normalization)
        return combined[:top_k]

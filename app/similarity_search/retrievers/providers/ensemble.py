from collections import defaultdict

from app.similarity_search.retrievers.base import BaseRetriever, ScoredDocs
from app.similarity_search.vectorstore.base import BaseVectorStore


class EnsembleRetriever(BaseRetriever):
    """Fuses dense and lexical results with Reciprocal Rank Fusion and deduplicates.

    lexical_provider: "bm25" (default, works with any store) or
                      "postgres_fts" (uses Postgres tsvector; requires a PgVectorStore
                      or an explicit 'url' kwarg in the retrieval config).
    """

    def __init__(
        self,
        vectorstore_client: BaseVectorStore,
        candidate_k: int = 20,
        rrf_k: int = 60,
        lexical_provider: str = "bm25",
        **kwargs,
    ) -> None:
        from app.similarity_search.retrievers.providers.vectorstore import VectorStoreRetriever

        self.dense_retriever = VectorStoreRetriever(vectorstore_client)
        self.candidate_k = candidate_k
        self.rrf_k = rrf_k

        if lexical_provider == "postgres_fts":
            from app.similarity_search.retrievers.providers.postgres_fts import PostgresFTSRetriever

            url = kwargs.get("url") or getattr(vectorstore_client, "conninfo", None)
            self.lexical_retriever: BaseRetriever = PostgresFTSRetriever(
                vectorstore_client=vectorstore_client, url=url
            )
        else:
            from app.similarity_search.retrievers.providers.bm25 import BM25Retriever

            self.lexical_retriever = BM25Retriever(vectorstore_client)

    def _rrf(self, rank: int) -> float:
        return 1 / (self.rrf_k + rank)

    def retrieve(self, query, top_k=5, score_normalization=None, metadata_filter=None) -> ScoredDocs:
        dense = self.dense_retriever.retrieve(query, top_k=self.candidate_k, metadata_filter=metadata_filter)
        lexical = self.lexical_retriever.retrieve(query, top_k=self.candidate_k, metadata_filter=metadata_filter)

        fused: dict = defaultdict(float)
        by_id: dict = {}
        for results in (dense, lexical):
            for rank, (doc, _) in enumerate(results, start=1):
                key = doc.metadata.get("id") or hash(doc.page_content)
                fused[key] += self._rrf(rank)
                by_id[key] = doc

        combined = sorted(
            ((by_id[k], s) for k, s in fused.items()), key=lambda pair: pair[1], reverse=True
        )
        combined = self._apply_normalization(combined, score_normalization)
        return combined[:top_k]

import re

from app.similarity_search.retrievers.base import BaseRetriever, ScoredDocs
from app.similarity_search.vectorstore.base import BaseVectorStore

_WORD = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "for",
    "on", "with", "as", "by", "at", "it", "this", "that", "be", "from",
}


def _tokenize(text: str) -> list[str]:
    return [tok for tok in _WORD.findall(text.lower()) if tok not in _STOPWORDS]


class BM25Retriever(BaseRetriever):
    """Lexical retrieval over the collection's documents using Okapi BM25."""

    def __init__(self, vectorstore_client: BaseVectorStore, **kwargs) -> None:
        self.vectorstore_client = vectorstore_client

    def retrieve(self, query, top_k=5, score_normalization=None, metadata_filter=None) -> ScoredDocs:
        from rank_bm25 import BM25Okapi

        documents = self.vectorstore_client.get_collection(metadata_filter=metadata_filter)
        if not documents:
            return []

        bm25 = BM25Okapi([_tokenize(doc.page_content) for doc in documents])
        scores = bm25.get_scores(_tokenize(query))

        scored = sorted(zip(documents, scores), key=lambda pair: pair[1], reverse=True)
        scored = self._apply_normalization(scored, score_normalization)
        return scored[:top_k]

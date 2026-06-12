import re

from app.similarity_search.retrievers.base import BaseRetriever, ScoredDocs
from app.similarity_search.vectorstore.base import BaseVectorStore

_WORD = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "for",
    "on", "with", "as", "by", "at", "it", "this", "that", "be", "from",
}


def _tokenize(text: str) -> list[str]:
    """Lowercase, extract word tokens, and remove stopwords.

    Parameters
    ----------
    text : str
        Raw text to tokenise.

    Returns
    -------
    list[str]
        Filtered word tokens.
    """
    return [tok for tok in _WORD.findall(text.lower()) if tok not in _STOPWORDS]


class BM25Retriever(BaseRetriever):
    """Lexical retrieval over the full collection using Okapi BM25."""

    def __init__(self, vectorstore_client: BaseVectorStore, **kwargs) -> None:
        """
        Parameters
        ----------
        vectorstore_client : BaseVectorStore
            Store whose ``get_collection`` method supplies the corpus.
        **kwargs
            Unused; absorbed so the retriever registry can pass arbitrary config.
        """
        self.vectorstore_client = vectorstore_client

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        score_normalization: str | None = None,
        metadata_filter: dict | None = None,
    ) -> ScoredDocs:
        """Rank collection documents against the query with BM25 and return the top-k.

        Parameters
        ----------
        query : str
            User query string.
        top_k : int, optional
            Maximum number of results to return. Default is 5.
        score_normalization : str or None, optional
            Normalisation method to apply after scoring (``minmax``, ``softmax``, etc.).
        metadata_filter : dict or None, optional
            Passed through to ``vectorstore_client.get_collection`` to pre-filter the corpus.

        Returns
        -------
        ScoredDocs
            List of ``(Document, score)`` pairs, highest score first.
        """
        from rank_bm25 import BM25Okapi

        documents = self.vectorstore_client.get_collection(metadata_filter=metadata_filter)
        if not documents:
            return []

        bm25 = BM25Okapi([_tokenize(doc.page_content) for doc in documents])
        scores = bm25.get_scores(_tokenize(query))

        scored = sorted(zip(documents, scores), key=lambda pair: pair[1], reverse=True)
        scored = self._apply_normalization(scored, score_normalization)
        return scored[:top_k]

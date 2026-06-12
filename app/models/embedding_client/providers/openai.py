from langchain_openai import OpenAIEmbeddings

from app.models.embedding_client.base import BaseEmbeddingClient
from app.models.embedding_client.registry import EmbeddingRegistry

_KNOWN_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


@EmbeddingRegistry.register("openai")
class OpenAIEmbeddingClient(BaseEmbeddingClient):
    """OpenAI-hosted text embeddings via ``langchain-openai``."""

    def __init__(self, cfg: dict):
        """
        Parameters
        ----------
        cfg : dict
            Provider config block. Reads ``model``, ``api_key``,
            and optional ``dimensions`` override.
        """
        self._client = OpenAIEmbeddings(model=cfg["model"], api_key=cfg["api_key"])
        self._dim = cfg.get("dimensions") or _KNOWN_DIMS.get(cfg["model"], 1536)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of documents via the OpenAI embeddings API.

        Parameters
        ----------
        texts : list[str]
            Passages to embed.

        Returns
        -------
        list[list[float]]
            Embedding vectors, one per input text.
        """
        return self._client.embed_documents(list(texts))

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string via the OpenAI embeddings API.

        Parameters
        ----------
        text : str
            Query to embed.

        Returns
        -------
        list[float]
            Embedding vector.
        """
        return self._client.embed_query(text)

    @property
    def embedding_dim(self) -> int:
        """Dimensionality of the embedding vectors.

        Returns
        -------
        int
            From the ``dimensions`` config override or the known-dim table.
        """
        return self._dim

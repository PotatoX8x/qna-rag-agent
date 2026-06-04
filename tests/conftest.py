from typing import Optional

import pytest
from langchain_core.documents import Document

from app.models.embedding_client.base import BaseEmbeddingClient
from app.similarity_search.vectorstore.base import BaseVectorStore


class FakeEmbeddings(BaseEmbeddingClient):
    """Deterministic bag-of-characters embedding for offline tests."""

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * 26
        for ch in text.lower():
            idx = ord(ch) - 97
            if 0 <= idx < 26:
                vec[idx] += 1.0
        return vec

    def embed_documents(self, texts):
        return [self._vector(t) for t in texts]

    def embed_query(self, text):
        return self._vector(text)

    @property
    def embedding_dim(self) -> int:
        return 26


class InMemoryVectorStore(BaseVectorStore):
    """Minimal BaseVectorStore for retriever tests; ranks by word overlap."""

    def __init__(self, documents: Optional[list[Document]] = None):
        self.documents = list(documents or [])

    def add_documents(self, documents):
        self.documents.extend(documents)

    def _matches(self, metadata: dict, where: Optional[dict]) -> bool:
        if not where:
            return True
        if "$and" in where:
            return all(self._matches(metadata, clause) for clause in where["$and"])
        if "$or" in where:
            return any(self._matches(metadata, clause) for clause in where["$or"])
        return all(metadata.get(key) == value for key, value in where.items())

    def get_collection(self, metadata_filter=None):
        return [doc for doc in self.documents if self._matches(doc.metadata, metadata_filter)]

    def query(self, query, top_k=5, metadata_filter=None):
        terms = set(query.lower().split())
        scored = []
        for doc in self.get_collection(metadata_filter):
            overlap = len(terms & set(doc.page_content.lower().split()))
            scored.append((doc, float(overlap)))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    def clear(self):
        self.documents = []

    def reset_collection(self):
        self.documents = []


@pytest.fixture
def fake_embeddings() -> FakeEmbeddings:
    return FakeEmbeddings()


@pytest.fixture
def sample_documents() -> list[Document]:
    return [
        Document(page_content="cats are small domestic animals", metadata={"id": "1", "kb_id": "k1"}),
        Document(page_content="dogs are loyal domestic animals", metadata={"id": "2", "kb_id": "k1"}),
        Document(page_content="the sun is a star at the center of the solar system", metadata={"id": "3", "kb_id": "k2"}),
    ]

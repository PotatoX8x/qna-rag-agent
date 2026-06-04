import uuid
from typing import Optional

from langchain_core.documents import Document

from app.models.embedding_client.base import BaseEmbeddingClient
from app.similarity_search.vectorstore.base import BaseVectorStore


class ChromaDBVectorStore(BaseVectorStore):
    """Chroma-backed store. Embeddings are produced by the app's embedding client,
    so Chroma only stores and searches the vectors we hand it."""

    def __init__(self, embedding_client: BaseEmbeddingClient, collection_name: str, **kwargs) -> None:
        import chromadb

        self.embedding_client = embedding_client
        persist_dir = kwargs.get("persist_dir")
        self.client = chromadb.PersistentClient(path=persist_dir) if persist_dir else chromadb.Client()
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, documents: list[Document]) -> None:
        if not documents:
            return
        ids = [doc.metadata.get("id") or str(uuid.uuid4()) for doc in documents]
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata or {} for doc in documents]
        embeddings = self.embedding_client.embed_documents(texts)
        self.collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

    def query(self, query, top_k=5, metadata_filter=None):
        embedding = self.embedding_client.embed_query(query)
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=metadata_filter,
            include=["documents", "metadatas", "distances"],
        )
        scored = []
        for text, metadata, distance in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        ):
            scored.append((Document(page_content=text, metadata=metadata or {}), 1 - distance))
        return scored

    def get_collection(self, metadata_filter: Optional[dict] = None) -> list[Document]:
        data = self.collection.get(where=metadata_filter)
        return [
            Document(page_content=text, metadata=metadata or {})
            for text, metadata in zip(data["documents"], data["metadatas"])
        ]

    def clear(self) -> None:
        ids = self.collection.get()["ids"]
        if ids:
            self.collection.delete(ids=ids)

    def reset_collection(self) -> None:
        name = self.collection.name
        self.client.delete_collection(name)
        self.collection = self.client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})

import pytest

pytest.importorskip("chromadb")

from langchain_core.documents import Document

from app.similarity_search.vectorstore.stores.chromadb import ChromaDBVectorStore
from tests.conftest import FakeEmbeddings

pytestmark = pytest.mark.integration


def test_chroma_roundtrip_and_filter():
    store = ChromaDBVectorStore(FakeEmbeddings(), "test_kb")
    store.reset_collection()
    store.add_documents([
        Document(page_content="cats are domestic animals", metadata={"id": "1", "kb_id": "k1"}),
        Document(page_content="the sun is a star", metadata={"id": "2", "kb_id": "k2"}),
    ])

    scoped = store.query("animals", top_k=1, metadata_filter={"kb_id": "k1"})
    assert scoped and scoped[0][0].metadata["id"] == "1"
    assert len(store.get_collection()) == 2

    store.clear()
    assert store.get_collection() == []

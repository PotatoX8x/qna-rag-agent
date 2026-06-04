import pytest
from langchain_core.documents import Document

from app.similarity_search.retrievers.providers.bm25 import BM25Retriever
from app.similarity_search.retrievers.providers.ensemble import EnsembleRetriever
from app.similarity_search.retrievers.providers.vectorstore import VectorStoreRetriever
from app.similarity_search.retrievers.registry import RetrieverRegistry
from tests.conftest import InMemoryVectorStore


def test_vectorstore_retriever_ranks_by_overlap(sample_documents):
    store = InMemoryVectorStore(sample_documents)
    retriever = VectorStoreRetriever(store)
    results = retriever.retrieve("domestic animals", top_k=2)
    assert {doc.metadata["id"] for doc, _ in results} == {"1", "2"}


def test_bm25_retriever_returns_relevant_doc(sample_documents):
    store = InMemoryVectorStore(sample_documents)
    retriever = BM25Retriever(store)
    results = retriever.retrieve("solar system star", top_k=1)
    assert results[0][0].metadata["id"] == "3"


def test_metadata_filter_scopes_results(sample_documents):
    store = InMemoryVectorStore(sample_documents)
    retriever = VectorStoreRetriever(store)
    results = retriever.retrieve("animals", top_k=5, metadata_filter={"kb_id": "k1"})
    assert all(doc.metadata["kb_id"] == "k1" for doc, _ in results)


def test_ensemble_fuses_and_deduplicates(sample_documents):
    store = InMemoryVectorStore(sample_documents)
    retriever = EnsembleRetriever(store, candidate_k=5, rrf_k=60)
    results = retriever.retrieve("domestic animals", top_k=5)
    ids = [doc.metadata["id"] for doc, _ in results]
    assert len(ids) == len(set(ids))
    assert {"1", "2"} <= set(ids)


def test_minmax_normalization_bounds_scores():
    store = InMemoryVectorStore([
        Document(page_content="alpha beta", metadata={"id": "1"}),
        Document(page_content="beta gamma", metadata={"id": "2"}),
    ])
    results = VectorStoreRetriever(store).retrieve("alpha beta gamma", top_k=2, score_normalization="minmax")
    scores = [s for _, s in results]
    assert max(scores) <= 1.0 and min(scores) >= 0.0


def test_registry_builds_ensemble(sample_documents):
    store = InMemoryVectorStore(sample_documents)
    retriever = RetrieverRegistry.create(store, {"provider": "ensemble", "candidate_k": 5, "rrf_k": 60})
    assert isinstance(retriever, EnsembleRetriever)


def test_registry_unknown_retriever_raises(sample_documents):
    store = InMemoryVectorStore(sample_documents)
    with pytest.raises(ValueError):
        RetrieverRegistry.create(store, {"provider": "nope"})

import threading
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import load_config
from app.core.logging import setup_logging
from app.core.observability import setup_observability
from app.db.engine import create_engine_and_session
from app.file_store import FileStoreRegistry
from app.file_store.base import BaseFileStore
from app.models.embedding_client import EmbeddingRegistry
from app.models.embedding_client.base import BaseEmbeddingClient
from app.models.llm_client import LLMRegistry
from app.models.llm_client.base import BaseLLMClient
from app.similarity_search.retrievers.base import BaseRetriever
from app.similarity_search.retrievers.registry import RetrieverRegistry
from app.similarity_search.vectorstore.base import BaseVectorStore
from app.similarity_search.vectorstore.registry import VectorStoreRegistry


@dataclass
class AppServices:
    """Singleton bag of fully-initialised application services."""

    config: dict
    llm: BaseLLMClient
    embeddings: BaseEmbeddingClient
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    vectorstore: BaseVectorStore
    retriever: BaseRetriever
    file_store: BaseFileStore


class ServiceContainer:
    """Thread-safe singleton factory for :class:`AppServices`."""

    _instance: AppServices | None = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> AppServices:
        """Return the singleton :class:`AppServices`, building it on first call.

        Returns
        -------
        AppServices
            Fully initialised service container.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls._build()
        return cls._instance

    @classmethod
    def _build(cls) -> AppServices:
        """Construct all application services from configuration.

        Returns
        -------
        AppServices
            Ready-to-use service container.
        """
        config = load_config()
        setup_logging(config.get("logging", {}))
        setup_observability(config)

        Path(config["database"]["data_dir"]).mkdir(parents=True, exist_ok=True)

        llm = LLMRegistry.create(config["models"]["llm"])
        embeddings = EmbeddingRegistry.create(config["models"]["embeddings"])
        engine, session_factory = create_engine_and_session(config["database"]["url"])
        vectorstore = VectorStoreRegistry.create(config["vectorstore"], "default", embeddings)
        retriever = RetrieverRegistry.create(vectorstore, config["retrieval"])
        file_store = FileStoreRegistry.create(config["file_store"])

        return AppServices(
            config=config,
            llm=llm,
            embeddings=embeddings,
            engine=engine,
            session_factory=session_factory,
            vectorstore=vectorstore,
            retriever=retriever,
            file_store=file_store,
        )

    @classmethod
    def reset(cls) -> None:
        """Discard the cached singleton, forcing a rebuild on next access.

        Used exclusively in tests to isolate container state between test cases.
        """
        with cls._lock:
            cls._instance = None

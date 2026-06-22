from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from app.agent.state import AgentState, ScoredDoc

if TYPE_CHECKING:
    from app.container import AppServices

logger = logging.getLogger(__name__)


def make_retrieve(services: AppServices):
    """Build the ``retrieve`` graph node bound to *services*.

    Parameters
    ----------
    services : AppServices
        Fully initialised service container.

    Returns
    -------
    Callable
        Async node function compatible with LangGraph.
    """

    async def retrieve(state: AgentState) -> dict:
        """Fetch documents from the ensemble retriever filtered by knowledge base.

        Parameters
        ----------
        state : AgentState
            Requires ``query`` and ``kb_id``.

        Returns
        -------
        dict
            ``documents`` list and initial ``needs_web_search`` flag.
        """
        kb_id = state.get("kb_id", "")
        if not kb_id:
            logger.warning("retrieve: no kb_id — skipping retrieval")
            return {"documents": [], "needs_web_search": True}

        try:
            docs: list[ScoredDoc] = await asyncio.to_thread(
                services.retriever.retrieve,
                state["query"],
                metadata_filter={"kb_id": kb_id},
            )
        except Exception:
            logger.exception("retrieve: retriever failed")
            docs = []

        return {"documents": docs, "needs_web_search": False, "retrieved_count": len(docs)}

    return retrieve

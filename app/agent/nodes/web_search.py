from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from app.agent.state import AgentState, ScoredDoc

if TYPE_CHECKING:
    from app.container import AppServices

logger = logging.getLogger(__name__)


def make_web_search(services: AppServices):
    """Build the ``web_search`` graph node bound to *services*.

    Parameters
    ----------
    services : AppServices
        Fully initialised service container.

    Returns
    -------
    Callable
        Async node function compatible with LangGraph.
    """

    async def web_search(state: AgentState) -> dict:
        """Augment retrieved docs with live Google search results.

        Silently skips when ``GOOGLE_API_KEY`` / ``GOOGLE_CX`` are not
        configured, leaving existing documents unchanged.

        Parameters
        ----------
        state : AgentState
            Requires ``query`` and existing ``documents``.

        Returns
        -------
        dict
            Augmented ``documents`` list, or empty dict when search is skipped.
        """
        cfg = services.config.get("search", {})
        api_key = cfg.get("google_api_key", "")
        cx = cfg.get("google_cse_id", "")

        if not api_key or api_key.startswith("${"):
            logger.debug("web_search: Google API key not configured — skipping")
            return {}

        try:
            from langchain_community.utilities import GoogleSearchAPIWrapper
            from langchain_core.documents import Document as LCDoc

            search = GoogleSearchAPIWrapper(google_api_key=api_key, google_cse_id=cx, k=5)
            raw = await asyncio.to_thread(search.run, state["query"])
            web_doc = LCDoc(page_content=raw, metadata={"source": "web", "id": None})
            extra: list[ScoredDoc] = [(web_doc, 1.0)]
        except Exception:
            logger.exception("web_search: search failed — using existing docs")
            extra = []

        return {"documents": state.get("documents", []) + extra}

    return web_search

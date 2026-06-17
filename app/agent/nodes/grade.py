from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.agent.nodes.helpers import format_docs
from app.agent.state import AgentState
from app.prompts.agent import grade as gp
from app.schemas.agent.grade import DocumentGrade

if TYPE_CHECKING:
    from app.container import AppServices

logger = logging.getLogger(__name__)


def make_grade(services: AppServices):
    """Build the ``grade`` graph node bound to *services*.

    Parameters
    ----------
    services : AppServices
        Fully initialised service container.

    Returns
    -------
    Callable
        Async node function compatible with LangGraph.
    """

    async def grade(state: AgentState) -> dict:
        """Keep only documents relevant to the query; flag if web search is needed.

        Parameters
        ----------
        state : AgentState
            Requires ``query`` and ``documents``.

        Returns
        -------
        dict
            Filtered ``documents`` and updated ``needs_web_search``.
        """
        docs = state.get("documents", [])
        if not docs:
            return {"documents": [], "needs_web_search": True}

        try:
            result: DocumentGrade = await services.llm.complete_structured(
                system_prompt=gp.SYSTEM_PROMPT,
                user_prompt=gp.HUMAN_PROMPT.format(
                    query=state["query"],
                    documents=format_docs(docs),
                ),
                schema=DocumentGrade,
            )
            relevant = [docs[i] for i in result.relevant_indices if i < len(docs)]
            needs_web = result.needs_web_search or len(relevant) < 2
        except Exception:
            logger.exception("grade: LLM grading failed — keeping all docs")
            relevant = docs
            needs_web = False

        return {"documents": relevant, "needs_web_search": needs_web}

    return grade

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.agent.nodes.helpers import format_docs
from app.agent.state import AgentState
from app.prompts.agent import generate as gp
from app.schemas.agent.generate import GenerateOutput

if TYPE_CHECKING:
    from app.container import AppServices

logger = logging.getLogger(__name__)


def make_generate(services: AppServices):
    """Build the ``generate`` graph node bound to *services*.

    Parameters
    ----------
    services : AppServices
        Fully initialised service container.

    Returns
    -------
    Callable
        Async node function compatible with LangGraph.
    """

    async def generate(state: AgentState) -> dict:
        """Generate a grounded answer with citation indices.

        Parameters
        ----------
        state : AgentState
            Requires ``query``, ``history``, ``documents``, ``generation_count``.

        Returns
        -------
        dict
            ``answer``, ``citations``, and incremented ``generation_count``.
        """
        docs = state.get("documents", [])
        context = format_docs(docs) if docs else "No context documents available."

        history_with_query = list(state.get("history", [])) + [
            {"role": "user", "content": state["query"]}
        ]

        try:
            result: GenerateOutput = await services.llm.complete_structured(
                system_prompt=gp.SYSTEM_PROMPT.format(context=context),
                user_prompt="",
                schema=GenerateOutput,
                messages=history_with_query,
            )
            answer = result.answer
            citations = [
                {
                    "index": i,
                    "chunk_id": docs[i][0].metadata.get("id"),
                    "score": docs[i][1],
                    "snippet": docs[i][0].page_content[:500],
                }
                for i in result.cited_indices
                if i < len(docs)
            ]
        except Exception:
            logger.exception("generate: LLM call failed")
            answer = "I was unable to generate an answer. Please try again."
            citations = []

        return {
            "answer": answer,
            "citations": citations,
            "generation_count": state.get("generation_count", 0) + 1,
        }

    return generate

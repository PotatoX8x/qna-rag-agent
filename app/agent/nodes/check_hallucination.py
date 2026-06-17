from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.agent.nodes.helpers import format_docs
from app.agent.state import AgentState
from app.prompts.agent import check_hallucination as chp
from app.schemas.agent.check_hallucination import HallucinationGrade

if TYPE_CHECKING:
    from app.container import AppServices

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2


def make_check_hallucination(services: AppServices):
    """Build the ``check_hallucination`` graph node bound to *services*.

    Parameters
    ----------
    services : AppServices
        Fully initialised service container.

    Returns
    -------
    Callable
        Async node function compatible with LangGraph.
    """

    async def check_hallucination(state: AgentState) -> dict:
        """Verify the answer is grounded in the retrieved context.

        Accepts the answer unconditionally once ``_MAX_RETRIES`` is reached
        to prevent infinite generation loops.

        Parameters
        ----------
        state : AgentState
            Requires ``answer``, ``documents``, ``generation_count``.

        Returns
        -------
        dict
            ``hallucination_detected`` boolean.
        """
        if state.get("generation_count", 0) >= _MAX_RETRIES:
            return {"hallucination_detected": False}

        docs = state.get("documents", [])
        if not docs:
            return {"hallucination_detected": False}

        try:
            result: HallucinationGrade = await services.llm.complete_structured(
                system_prompt=chp.SYSTEM_PROMPT,
                user_prompt=chp.HUMAN_PROMPT.format(
                    context=format_docs(docs[:5]),
                    answer=state["answer"],
                ),
                schema=HallucinationGrade,
            )
            detected = not result.grounded
        except Exception:
            logger.exception("check_hallucination: LLM call failed — accepting answer")
            detected = False

        if detected:
            logger.warning("check_hallucination: hallucination detected, will retry")

        return {"hallucination_detected": detected}

    return check_hallucination

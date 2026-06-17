from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from app.agent.nodes.check_hallucination import make_check_hallucination
from app.agent.nodes.generate import make_generate
from app.agent.nodes.grade import make_grade
from app.agent.nodes.retrieve import make_retrieve
from app.agent.nodes.web_search import make_web_search

if TYPE_CHECKING:
    from app.container import AppServices


def build_nodes(services: AppServices) -> dict[str, Callable]:
    """Instantiate all graph node callables bound to *services*.

    Parameters
    ----------
    services : AppServices
        Fully initialised service container.

    Returns
    -------
    dict[str, Callable]
        Mapping of node name → async node function.
    """
    return {
        "retrieve": make_retrieve(services),
        "grade": make_grade(services),
        "web_search": make_web_search(services),
        "generate": make_generate(services),
        "check_hallucination": make_check_hallucination(services),
    }

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from langgraph.graph import END, StateGraph

from app.agent.nodes import build_nodes
from app.agent.state import AgentState

if TYPE_CHECKING:
    from app.container import AppServices

_graph: Any = None
_graph_lock = threading.Lock()


def _route_after_grade(state: AgentState) -> str:
    """Decide whether to search the web or proceed directly to generation.

    Parameters
    ----------
    state : AgentState
        Requires ``needs_web_search``.

    Returns
    -------
    str
        ``"web_search"`` or ``"generate"``.
    """
    return "web_search" if state.get("needs_web_search") else "generate"


def _route_after_hallucination(state: AgentState) -> str:
    """Decide whether to re-generate or accept the answer.

    Parameters
    ----------
    state : AgentState
        Requires ``hallucination_detected``.

    Returns
    -------
    str
        ``"generate"`` to retry or ``END`` to finish.
    """
    return "generate" if state.get("hallucination_detected") else END


def build_graph(services: AppServices) -> Any:
    """Compile and return the CRAG LangGraph, caching the result globally.

    The graph is compiled once on first call; subsequent calls return the same
    compiled object. Thread-safe via double-checked locking.

    Flow
    ----
    retrieve → grade → (web_search →) generate → check_hallucination → END

    Parameters
    ----------
    services : AppServices
        Fully initialised service container passed to node factories.

    Returns
    -------
    CompiledGraph
        LangGraph compiled state machine.
    """
    global _graph
    if _graph is not None:
        return _graph

    with _graph_lock:
        if _graph is not None:
            return _graph

        nodes = build_nodes(services)
        workflow: StateGraph = StateGraph(AgentState)

        for name, fn in nodes.items():
            workflow.add_node(name, fn)

        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "grade")

        workflow.add_conditional_edges(
            "grade",
            _route_after_grade,
            {"web_search": "web_search", "generate": "generate"},
        )

        workflow.add_edge("web_search", "generate")
        workflow.add_edge("generate", "check_hallucination")

        workflow.add_conditional_edges(
            "check_hallucination",
            _route_after_hallucination,
            {"generate": "generate", END: END},
        )

        _graph = workflow.compile()

    return _graph

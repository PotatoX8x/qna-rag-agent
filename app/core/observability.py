from __future__ import annotations

import logging
from contextlib import asynccontextmanager, contextmanager

import mlflow
from mlflow.tracking import MlflowClient

logger = logging.getLogger(__name__)

_state: dict = {"enabled": False, "experiment_id": None}


def _as_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def setup_observability(config: dict) -> bool:
    """Configure MLflow tracking and autologging from the resolved app config.

    Parameters
    ----------
    config : dict
        Full resolved application config. Reads from the ``mlflow`` key.

    Returns
    -------
    bool
        ``True`` when MLflow was successfully initialised.
    """
    cfg = config.get("mlflow", {}) or {}
    if not _as_bool(cfg.get("enabled")):
        logger.info("MLflow observability disabled")
        return False

    try:
        tracking_uri = cfg.get("tracking_uri")
        if tracking_uri and not tracking_uri.startswith("${"):
            mlflow.set_tracking_uri(tracking_uri)

        experiment = cfg.get("experiment") or "qna"
        mlflow.set_experiment(experiment)
        exp = mlflow.get_experiment_by_name(experiment)
        _state["experiment_id"] = exp.experiment_id if exp else None

        for lib_name, lib_conf in (cfg.get("autolog") or {}).items():
            if not (lib_conf or {}).get("enabled"):
                continue
            try:
                getattr(mlflow, lib_name).autolog(**(lib_conf.get("params") or {}))
                logger.info("MLflow autolog enabled for %s", lib_name)
            except Exception as exc:
                logger.warning("MLflow autolog for %s unavailable (%s)", lib_name, exc)

        _state["enabled"] = True
        logger.info("MLflow tracking enabled at %s", mlflow.get_tracking_uri())
        return True
    except Exception as exc:
        logger.warning("MLflow unavailable (%s: %s); continuing without it", type(exc).__name__, exc)
        _state["enabled"] = False
        return False


def open_conversation_run(
    *,
    conversation_id: str,
    kb_id: str | None,
    title: str | None,
) -> str | None:
    """Create an MLflow run for a conversation and return the run id.

    Parameters
    ----------
    conversation_id : str
        UUID of the conversation row.
    kb_id : str or None
        Knowledge base UUID attached to the conversation.
    title : str or None
        Human-readable conversation title.

    Returns
    -------
    str or None
        MLflow run id to persist on the conversation row, or ``None`` when
        MLflow is disabled or the call fails.
    """
    if not _state["enabled"]:
        return None
    try:
        client = MlflowClient()
        run = client.create_run(
            experiment_id=_state["experiment_id"],
            run_name=f"conv-{conversation_id[:8]}",
            tags={
                "conversation_id": conversation_id,
                "kb_id": kb_id or "",
                "title": title or "",
            },
        )
        logger.debug("MLflow: opened run %s for conversation %s", run.info.run_id, conversation_id)
        return run.info.run_id
    except Exception as exc:
        logger.warning("MLflow: could not open conversation run (%s)", exc)
        return None


@asynccontextmanager
async def agent_run_context(
    run_id: str | None, conversation_id: str, turn_index: int, query: str
):
    """Re-attach to the conversation's MLflow run for one agent turn.

    Each turn becomes a named span inside the run, seeded with the user's
    question as its input. All turns from the same conversation share a trace
    session id so they group together in the MLflow Traces UI. The yielded span
    lets the caller record the final answer as the span output.

    Parameters
    ----------
    run_id : str or None
        MLflow run id persisted on the conversation row.
    conversation_id : str
        Used as the MLflow trace session id.
    turn_index : int
        Zero-based turn counter used to name the span.
    query : str
        The user's question, recorded as the span input.

    Yields
    ------
    Span or None
        The active turn span (so the caller can set its output), or ``None``
        when MLflow is disabled or attaching failed.
    """
    if not run_id or not _state["enabled"]:
        yield None
        return
    try:
        run_cm = mlflow.start_run(run_id=run_id, nested=True)
        run_cm.__enter__()
        span_cm = mlflow.start_span(name=f"turn_{turn_index}")
        span = span_cm.__enter__()
        span.set_inputs({"question": query})
        mlflow.update_current_trace(session_id=conversation_id)
    except Exception as exc:
        logger.warning("MLflow: could not attach agent trace (%s)", exc)
        yield None
        return
    try:
        yield span
    finally:
        try:
            span_cm.__exit__(None, None, None)
            run_cm.__exit__(None, None, None)
        except Exception as exc:
            logger.warning("MLflow: agent run context teardown failed (%s)", exc)


def log_turn_metrics(
    run_id: str | None,
    *,
    turn_index: int,
    retrieved_docs: int,
    relevant_docs: int,
    needs_web_search: bool,
    generation_count: int,
    hallucination_detected: bool,
    latency_ms: int,
) -> None:
    """Log per-turn metrics to the conversation's MLflow run.

    Parameters
    ----------
    run_id : str or None
        MLflow run id. No-ops when ``None`` or MLflow is disabled.
    turn_index : int
        Step value so metrics are plotted as a time-series per conversation.
    retrieved_docs : int
        Number of chunks returned by the retriever before grading.
    relevant_docs : int
        Number of chunks kept after the grade node.
    needs_web_search : bool
        Whether the grade node requested a web search.
    generation_count : int
        Number of generation attempts (> 1 means a hallucination retry occurred).
    hallucination_detected : bool
        Final hallucination flag from the check node.
    latency_ms : int
        Wall-clock milliseconds for the full graph invocation.
    """
    if not run_id or not _state["enabled"]:
        return
    try:
        client = MlflowClient()
        for key, value in {
            "retrieved_docs": retrieved_docs,
            "relevant_docs": relevant_docs,
            "needs_web_search": int(needs_web_search),
            "generation_count": generation_count,
            "hallucination_detected": int(hallucination_detected),
            "latency_ms": latency_ms,
        }.items():
            client.log_metric(run_id, key, value, step=turn_index)
    except Exception as exc:
        logger.warning("MLflow: could not log turn metrics (%s)", exc)

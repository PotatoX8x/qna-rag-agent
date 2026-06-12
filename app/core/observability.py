import logging

logger = logging.getLogger(__name__)


def setup_observability(config: dict) -> None:
    """Configure MLflow tracking if enabled in the config.

    No-ops silently when ``mlflow.enabled`` is falsy so local runs without
    a tracking server don't require any MLflow config.

    Parameters
    ----------
    config : dict
        Full resolved application config. Reads from the ``mlflow`` key.
    """
    cfg = config.get("mlflow", {})
    if not cfg.get("enabled"):
        return

    import mlflow

    mlflow.set_tracking_uri(cfg.get("tracking_uri"))
    mlflow.set_experiment(cfg.get("experiment", "qna"))

    for name, opts in cfg.get("autolog", {}).items():
        if opts.get("enabled"):
            getattr(mlflow, name).autolog(**opts.get("params", {}))

    logger.info("MLflow tracking enabled at %s", cfg.get("tracking_uri"))

import logging

logger = logging.getLogger(__name__)


def setup_observability(config: dict) -> None:
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

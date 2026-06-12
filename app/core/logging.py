import logging

from rich.logging import RichHandler


def setup_logging(config: dict | None = None) -> None:
    """Configure the root logger from the ``logging`` config block.

    Clears any existing handlers and installs a single ``RichHandler`` so log
    format is controlled in one place regardless of how many libraries attach
    their own handlers.

    Parameters
    ----------
    config : dict or None, optional
        The ``logging`` section from ``settings.yaml``. Recognised keys:
        ``level``, ``rich_tracebacks``, ``show_time``, ``show_level``, ``show_path``.
    """
    cfg = config or {}
    level = getattr(logging, str(cfg.get("level", "info")).upper(), logging.INFO)

    handler = RichHandler(
        rich_tracebacks=cfg.get("rich_tracebacks", True),
        show_time=cfg.get("show_time", True),
        show_level=cfg.get("show_level", True),
        show_path=cfg.get("show_path", False),
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

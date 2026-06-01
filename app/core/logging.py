import logging

from rich.logging import RichHandler


def setup_logging(config: dict | None = None) -> None:
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

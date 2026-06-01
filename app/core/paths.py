import os
from functools import lru_cache
from pathlib import Path


@lru_cache
def detect_project_root(anchors: tuple[str, ...] = ("settings.yaml",)) -> Path:
    """Walk up from the current directory until one of ``anchors`` is found."""
    if root := os.environ.get("PROJECT_ROOT"):
        return Path(root).resolve()

    start = Path.cwd().resolve()
    for parent in (start, *start.parents):
        if any((parent / anchor).exists() for anchor in anchors):
            return parent

    raise RuntimeError(f"Could not locate project root from {start} (anchors={anchors})")

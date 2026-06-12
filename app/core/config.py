import os
import re

import yaml
from dotenv import load_dotenv

from app.core.paths import detect_project_root

_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def _expand(raw: str) -> str:
    """Resolve ``${VAR}`` and ``${VAR:-default}`` placeholders against the environment.

    A set, non-empty variable wins; otherwise the inline default is used. A bare
    ``${VAR}`` with no default and no env value is left untouched so it surfaces as a
    visible error at first use rather than silently resolving to empty.

    Parameters
    ----------
    raw : str
        Raw YAML string potentially containing ``${...}`` placeholders.

    Returns
    -------
    str
        String with all resolvable placeholders substituted.
    """

    def replace(match: re.Match) -> str:
        name, default = match.group(1), match.group(2)
        value = os.environ.get(name)
        if value:
            return value
        if default is not None:
            return default
        return match.group(0)

    return _PLACEHOLDER.sub(replace, raw)


def load_config() -> dict:
    """Load, expand, and parse ``settings.yaml`` from the project root.

    Sets the ``PROJECT_ROOT`` environment variable as a side effect so YAML
    placeholders that reference it resolve correctly.

    Returns
    -------
    dict
        Fully resolved configuration tree.
    """
    root = detect_project_root()
    os.environ.setdefault("PROJECT_ROOT", str(root))
    load_dotenv(root / ".env")
    raw = (root / "settings.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(_expand(raw))

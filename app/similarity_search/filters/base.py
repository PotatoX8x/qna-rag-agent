from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseFilterBuilder(ABC):
    """Translates a neutral ``{field: value}`` filter into a backend-specific schema."""

    @abstractmethod
    def build(self, filter_params: dict[str, Any]) -> Optional[dict[str, Any]]:
        ...

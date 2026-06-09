from typing import Any

from app.similarity_search.filters.base import BaseFilterBuilder


class PgVectorFilterBuilder(BaseFilterBuilder):
    """Translates a neutral filter dict to a SQL WHERE fragment and bind params."""

    def build(self, filter_params: dict[str, Any]) -> tuple[str, list]:
        if not filter_params:
            return "", []
        parts = []
        params: list = []
        for key, value in filter_params.items():
            if isinstance(value, list):
                parts.append(f"{key} = ANY(%s::uuid[])")
                params.append([str(v) for v in value])
            else:
                parts.append(f"{key} = %s::uuid")
                params.append(str(value))
        return " AND ".join(parts), params

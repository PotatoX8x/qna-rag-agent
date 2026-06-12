from typing import Any

from app.similarity_search.filters.base import BaseFilterBuilder


class PgVectorFilterBuilder(BaseFilterBuilder):
    """Translates neutral ``{field: value}`` filters to SQL WHERE fragments."""

    def build(self, filter_params: dict[str, Any]) -> tuple[str, list]:
        """Build a SQL WHERE fragment and corresponding bind parameters.

        Parameters
        ----------
        filter_params : dict[str, Any]
            Neutral filter where values are UUID scalars or lists of UUIDs.

        Returns
        -------
        tuple[str, list]
            A ``(where_sql, params)`` pair. ``where_sql`` is an ``AND``-joined
            condition string ready to embed in a query; ``params`` are the
            positional bind values.
        """
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

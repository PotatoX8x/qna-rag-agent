from typing import Any, Optional

from app.similarity_search.filters.base import BaseFilterBuilder


class ChromaFilterBuilder(BaseFilterBuilder):
    """Translates neutral ``{field: value}`` filters to Chroma ``where`` clause dicts."""

    def build(self, filter_params: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Build a Chroma-compatible ``where`` dict from a neutral filter map.

        List values are expanded to ``$or`` disjunctions. Multiple keys are wrapped
        in ``$and``. A single equality condition is returned unwrapped.

        Parameters
        ----------
        filter_params : dict[str, Any]
            Neutral filter where values are scalars or lists of scalars.

        Returns
        -------
        dict[str, Any] or None
            Chroma ``where`` clause, or ``None`` when the input is empty.
        """
        if not filter_params:
            return None

        clauses = []
        for key, value in filter_params.items():
            if value is None or (isinstance(value, list) and not value):
                continue
            if isinstance(value, list):
                if len(value) == 1:
                    clauses.append({key: value[0]})
                else:
                    clauses.append({"$or": [{key: v} for v in value]})
            else:
                clauses.append({key: value})

        if not clauses:
            return None
        return {"$and": clauses} if len(clauses) > 1 else clauses[0]

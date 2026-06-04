from typing import Any, Optional

from app.similarity_search.filters.base import BaseFilterBuilder


class ChromaFilterBuilder(BaseFilterBuilder):
    """Builds Chroma ``where`` clauses. List values become disjunctive matches."""

    def build(self, filter_params: dict[str, Any]) -> Optional[dict[str, Any]]:
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

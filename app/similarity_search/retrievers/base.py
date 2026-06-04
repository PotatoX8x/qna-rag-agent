import math
from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain_core.documents import Document

ScoredDocs = list[tuple[Document, float]]


class BaseRetriever(ABC):
    """Returns scored documents and can normalize raw scores onto a comparable range."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        score_normalization: Optional[str] = None,
        metadata_filter: Optional[dict[str, Any]] = None,
    ) -> ScoredDocs:
        ...

    def _apply_normalization(self, scored: ScoredDocs, method: Optional[str]) -> ScoredDocs:
        if not method or method.lower() == "none":
            return scored
        normalizers = {
            "minmax": self._minmax,
            "scale": self._scale,
            "softmax": self._softmax,
            "log": self._log,
        }
        normalizer = normalizers.get(method.lower())
        if normalizer is None:
            raise ValueError(f"Unknown score normalization {method!r}")
        return normalizer(scored)

    def _minmax(self, scored: ScoredDocs) -> ScoredDocs:
        if not scored:
            return []
        scores = [s for _, s in scored]
        low, high = min(scores), max(scores)
        return [(doc, (s - low) / (high - low + 1e-8)) for doc, s in scored]

    def _scale(self, scored: ScoredDocs, factor: float = 100.0) -> ScoredDocs:
        return [(doc, s * factor) for doc, s in scored]

    def _softmax(self, scored: ScoredDocs) -> ScoredDocs:
        if not scored:
            return []
        exps = [math.exp(s) for _, s in scored]
        total = sum(exps)
        return [(doc, e / total) for (doc, _), e in zip(scored, exps)]

    def _log(self, scored: ScoredDocs) -> ScoredDocs:
        return [(doc, math.log(1 + s)) for doc, s in scored]

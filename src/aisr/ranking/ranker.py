from __future__ import annotations
from dataclasses import dataclass
from ..repair.candidates import Patch
from ..validation.pipeline import ValidationResult
from .features import extract
from .scoring import score

@dataclass
class RankedPatch:
    rank: int
    patch: Patch
    validation: ValidationResult
    score: float
    contributions: dict

class PatchRanker:
    def __init__(self, fl_scores: dict[tuple[str, int], float], weights: dict | None = None):
        self.fl, self.weights = fl_scores, weights

    def rank(self, results: list[tuple[Patch, ValidationResult]]) -> list[RankedPatch]:
        """Only plausible patches (survived validation) are ranked; the rest are reported as rejected elsewhere."""
        scored = []
        for p, v in results:
            if not v.plausible:
                continue
            fl = max((s for (f, l), s in self.fl.items() if p.file.endswith(f) and p.start_line <= l <= p.end_line), default=0.0)
            s, c = score(extract(p, v, fl).as_dict(), self.weights)
            scored.append((s, p, v, c))
        scored.sort(key=lambda t: (-t[0], t[1].changed_lines, t[1].id))
        return [RankedPatch(i, p, v, s, c) for i, (s, p, v, c) in enumerate(scored, 1)]

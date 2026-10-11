"""Turn per-statement scores into a ranked list and roll up statement -> method -> class -> file."""
from __future__ import annotations
from dataclasses import dataclass
from ..analysis.coverage.collector import ExecutionMatrix
from ..analysis.coverage.jacoco import CoverageReport, Line, method_of
from .base import Formula, build_spectra
from .dstar import dstar
from .jaccard import jaccard
from .ochiai import ochiai
from .tarantula import tarantula

METRICS: dict[str, Formula] = {"ochiai": ochiai, "tarantula": tarantula, "jaccard": jaccard, "dstar": dstar}

@dataclass(frozen=True)
class Suspicious:
    rank: int            # competition rank over statements (ties share the best rank) -- see metrics.rank_of for evaluation
    file: str
    cls: str
    method: str
    line: int
    score: float         # normalised to [0, 1] per metric so metrics are comparable

class FaultLocalizer:
    def __init__(self, metric: str = "ochiai"):
        if metric not in METRICS:
            raise ValueError(f"unknown metric {metric!r}; choose from {sorted(METRICS)}")
        self.metric = metric

    def score_statements(self, m: ExecutionMatrix) -> dict[Line, float]:
        f = METRICS[self.metric]
        raw = {l: f(s) for l, s in build_spectra(m).items()}
        top = max(raw.values(), default=0.0)
        return {l: (v / top if top > 0 else 0.0) for l, v in raw.items()}

    def rank(self, m: ExecutionMatrix, top_k: int | None = None) -> list[Suspicious]:
        if not m.failing:
            return []                      # nothing to localise: no failing test
        scores = self.score_statements(m)
        report = CoverageReport(methods=m.methods)
        ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0].file, kv[0].line))
        out, prev, rank = [], None, 0
        for i, (l, s) in enumerate(ordered, 1):
            if s != prev:
                rank, prev = i, s
            cls, meth = method_of(report, l) or ("?", "?")
            out.append(Suspicious(rank, l.file, cls, meth, l.line, round(s, 6)))
        return out[:top_k] if top_k else out

def aggregate(ranked: list[Suspicious], level: str) -> list[tuple[str, float]]:
    """Max-score roll-up. level in {'method','class','file'}."""
    key = {"method": lambda s: f"{s.cls}#{s.method}", "class": lambda s: s.cls, "file": lambda s: s.file}[level]
    best: dict[str, float] = {}
    for s in ranked:
        k = key(s)
        best[k] = max(best.get(k, 0.0), s.score)
    return sorted(best.items(), key=lambda kv: (-kv[1], kv[0]))

from __future__ import annotations
from ..analysis.coverage.jacoco import Line
from ..localization.aggregator import Suspicious

def rank_of_fault(ranked: list[Suspicious], faulty: set[tuple[str, int]], tie: str = "average") -> float | None:
    """Rank of the best-ranked faulty statement under an explicit tie rule.
    tie: 'best' (optimistic), 'worst' (pessimistic, recommended for papers), 'average' (default).
    Ties MUST be handled explicitly: ochiai etc. give many statements identical scores."""
    best = None
    for s in ranked:
        if (s.file, s.line) in faulty:
            group = [t for t in ranked if t.score == s.score]
            first = min(t.rank for t in group); size = len(group)
            r = {"best": first, "worst": first + size - 1, "average": first + (size - 1) / 2}[tie]
            best = r if best is None else min(best, r)
    return best

def top_n(ranks: list[float | None], n: int) -> float:
    """Fraction of bugs whose fault is within top-n (a bug with fault not localised counts as a miss)."""
    return sum(1 for r in ranks if r is not None and r <= n) / len(ranks) if ranks else 0.0

def mean_rank(ranks: list[float | None]) -> float:
    vals = [r for r in ranks if r is not None]
    return sum(vals) / len(vals) if vals else float("nan")

def exam_score(rank: float | None, n_statements: int) -> float | None:
    """EXAM = rank / #executable statements (lower is better)."""
    return None if rank is None or n_statements == 0 else rank / n_statements

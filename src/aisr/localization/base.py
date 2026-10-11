from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
from ..analysis.coverage.collector import ExecutionMatrix
from ..analysis.coverage.jacoco import Line

@dataclass(frozen=True)
class Spectrum:
    """Per-statement counts. ef/ep: failing/passing tests that execute it; nf/np: that do not.
    F = ef+nf total failing tests, P = ep+np total passing tests."""
    ef: int; ep: int; nf: int; np: int
    @property
    def F(self) -> int: return self.ef + self.nf
    @property
    def P(self) -> int: return self.ep + self.np

Formula = Callable[[Spectrum], float]

def build_spectra(m: ExecutionMatrix) -> dict[Line, Spectrum]:
    failing, passing = m.failing, m.passing
    F, P = len(failing), len(passing)
    ef: dict[Line, int] = {}; ep: dict[Line, int] = {}
    for t in failing:
        for l in m.coverage.get(t, ()):
            ef[l] = ef.get(l, 0) + 1
    for t in passing:
        for l in m.coverage.get(t, ()):
            ep[l] = ep.get(l, 0) + 1
    lines = set(ef) | set(ep)
    return {l: Spectrum(ef.get(l, 0), ep.get(l, 0), F - ef.get(l, 0), P - ep.get(l, 0)) for l in lines}

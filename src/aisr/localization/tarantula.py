from .base import Spectrum

def tarantula(s: Spectrum) -> float:
    """(ef/F) / ((ef/F) + (ep/P))   -- Jones & Harrold."""
    f = s.ef / s.F if s.F else 0.0
    p = s.ep / s.P if s.P else 0.0
    return f / (f + p) if (f + p) > 0 else 0.0

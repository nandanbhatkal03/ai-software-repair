from .base import Spectrum

def jaccard(s: Spectrum) -> float:
    """ef / (F + ep)   -- Chen et al."""
    d = s.F + s.ep
    return s.ef / d if d > 0 else 0.0

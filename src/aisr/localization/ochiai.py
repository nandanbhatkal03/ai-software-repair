import math
from .base import Spectrum

def ochiai(s: Spectrum) -> float:
    """ef / sqrt(F * (ef + ep))   -- Abreu et al."""
    d = math.sqrt(s.F * (s.ef + s.ep))
    return s.ef / d if d > 0 else 0.0

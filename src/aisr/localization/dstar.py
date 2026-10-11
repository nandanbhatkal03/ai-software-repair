from .base import Spectrum

def dstar(s: Spectrum, star: int = 2) -> float:
    """ef^* / (ep + nf)   -- Wong et al.  When the denominator is 0 (executed by every failing test and
    no passing test) the score is unbounded; we return a large finite value so it ranks first and can be normalised."""
    d = s.ep + s.nf
    if s.ef == 0:
        return 0.0
    return (s.ef ** star) / d if d > 0 else float(s.ef ** star) * 1e6

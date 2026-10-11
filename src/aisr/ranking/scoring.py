DEFAULT_WEIGHTS = {"fl_score": 0.30, "regression_clean": 0.25, "static_improvement": 0.10,
                   "patch_size": 0.25, "mutation_score": 0.10, "llm_origin": 0.0}

def score(features: dict, weights: dict | None = None) -> tuple[float, dict]:
    """Transparent weighted sum; returns (score, per-feature contribution) so the report can explain it."""
    w = weights or DEFAULT_WEIGHTS
    contrib = {k: round(w.get(k, 0.0) * v, 4) for k, v in features.items()}
    return round(sum(contrib.values()), 4), contrib

"""The four configurations of the experiment design (spec sections 22 and 33, unified)."""
CONFIGS = {
    "A": {"name": "Traditional FL (Ochiai)", "fl": "ochiai", "generator": None, "validate": False, "rank": False},
    "B": {"name": "FL + rule-based repair", "fl": "ochiai", "generator": "template", "validate": True, "rank": False},
    "C": {"name": "LLM repair without FL", "fl": None, "generator": "llm", "validate": True, "rank": False},
    "D": {"name": "Proposed: FL + context + LLM + validation + ranking", "fl": "ochiai", "generator": "llm", "validate": True, "rank": True},
}
# Ablations of D (spec section 34): each removes exactly one component.
ABLATIONS = {
    "D-noFL": {**CONFIGS["D"], "fl": None},
    "D-noContext": {**CONFIGS["D"], "context": False},
    "D-noRanking": {**CONFIGS["D"], "rank": False},
    "D-noStatic": {**CONFIGS["D"], "static": False},
    "D-noRegression": {**CONFIGS["D"], "regression": False},
}

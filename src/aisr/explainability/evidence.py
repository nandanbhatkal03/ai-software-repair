from __future__ import annotations
from ..localization.aggregator import Suspicious

def location_evidence(s: Suspicious, n_failing: int) -> str:
    return (f"{s.file}:{s.line} ({s.cls}.{s.method}) ranked #{s.rank} with normalised suspiciousness {s.score:.2f}; "
            f"relative to other statements it is covered by the {n_failing} failing test(s) proportionally more than by passing tests.")

def validation_evidence(stages: dict) -> list[str]:
    label = {True: "passed", False: "FAILED", None: "not run"}
    return [f"{k}: {label[stages.get(k)]}" for k in ("syntax", "compile", "failing_tests", "regression", "static", "mutation")]

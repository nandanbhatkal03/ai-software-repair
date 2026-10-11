from __future__ import annotations
from pathlib import Path
from ..testing.results import Outcome
from ..testing.runner import TestRunner

def regression_check(tr: TestRunner, project: Path, build_system: str,
                     baseline_passing: set[str]) -> tuple[bool, list[str], dict]:
    """Full suite run. A regression = a test that passed on the buggy baseline but fails now.
    (Tests that failed before and still fail are reported by the unit-test stage, not here.)"""
    res = tr.run_suite(project, build_system)
    if not res.build_ok:
        return False, sorted(baseline_passing), res.stats()
    now = {r.case.id: r.outcome for r in res.results}
    regressions = sorted(t for t in baseline_passing if now.get(t) in (Outcome.FAIL, Outcome.ERROR))
    return not regressions, regressions, res.stats()

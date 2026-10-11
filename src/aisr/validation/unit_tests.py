from __future__ import annotations
from pathlib import Path
from ..testing.runner import TestRunner

def failing_tests_pass(tr: TestRunner, project: Path, build_system: str, failing_ids: list[str]) -> tuple[bool, list[str]]:
    """Re-run only the originally failing tests. Returns (all fixed, still-failing ids)."""
    still = []
    for tid in failing_ids:
        res = tr.run_suite(project, build_system, selector=tid)
        hit = [r for r in res.results if r.case.id == tid]
        if not res.build_ok or not hit or hit[0].failed:
            still.append(tid)
    return not still, still

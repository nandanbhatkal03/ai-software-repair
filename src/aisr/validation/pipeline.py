"""Staged patch validation with early rejection (cheapest check first). Never accepts a patch just because
the originally failing test turns green: the full suite must also show no regressions."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from pathlib import Path
from ..repair.candidates import Patch
from ..repository.workspace import Workspace
from ..testing.runner import TestRunner
from .compiler import compile_ok, syntax_ok
from .regression import regression_check
from .static_checks import count_findings
from .unit_tests import failing_tests_pass

STAGES = ["syntax", "compile", "failing_tests", "regression", "static", "mutation"]

@dataclass
class ValidationResult:
    patch_id: str
    stages: dict[str, bool | None] = field(default_factory=dict)   # None = skipped / not configured
    rejected_at: str | None = None
    still_failing: list[str] = field(default_factory=list)
    regressions: list[str] = field(default_factory=list)
    static_delta: int | None = None                                  # findings after - before (negative = better)
    mutation_score: float | None = None
    test_runs: int = 0
    duration_s: float = 0.0
    @property
    def plausible(self) -> bool:      # compiles, fixes failing tests, no regressions
        return all(self.stages.get(s) for s in ("syntax", "compile", "failing_tests", "regression"))

class PatchValidator:
    def __init__(self, ws: Workspace, build_system: str, tr: TestRunner, failing_ids: list[str],
                 baseline_passing: set[str], static_cmd: list[str] | None = None, run_mutation: bool = False,
                 source_dirs: tuple[str, ...] = ()):
        self.ws, self.bs, self.tr = ws, build_system, tr
        self.failing_ids, self.baseline_passing = failing_ids, baseline_passing
        self.static_cmd, self.run_mutation, self.source_dirs = static_cmd, run_mutation, source_dirs
        self._static_before = None

    def validate(self, patch: Patch, keep_dir: bool = False) -> ValidationResult:
        t0, res = time.time(), ValidationResult(patch.id)
        def stop(stage: str) -> ValidationResult:
            res.stages[stage] = False; res.rejected_at = stage; res.duration_s = time.time() - t0
            return res
        base_file = self.ws.baseline / patch.file
        orig_lines = base_file.read_text(errors="replace").splitlines()[patch.start_line - 1:patch.end_line] if base_file.is_file() else []
        if not syntax_ok(patch.replacement, "\n".join(orig_lines) if orig_lines else None):
            return stop("syntax")
        res.stages["syntax"] = True
        proj = self.ws.fresh_copy(patch.id)               # original/baseline is never touched
        try:
            patch.apply(proj)
            ok, _ = compile_ok(proj, self.bs, self.tr.runner, self.tr.config)
            if not ok: return stop("compile")
            res.stages["compile"] = True
            fixed, res.still_failing = failing_tests_pass(self.tr, proj, self.bs, self.failing_ids)
            res.test_runs += len(self.failing_ids)
            if not fixed: return stop("failing_tests")
            res.stages["failing_tests"] = True
            ok, res.regressions, _ = regression_check(self.tr, proj, self.bs, self.baseline_passing)
            res.test_runs += 1
            if not ok: return stop("regression")
            res.stages["regression"] = True
            if self.static_cmd:
                if self._static_before is None:
                    self._static_before = count_findings(self.ws.baseline, self.static_cmd, self.tr.runner)
                after = count_findings(proj, self.static_cmd, self.tr.runner)
                res.static_delta = (after - self._static_before) if None not in (after, self._static_before) else None
                res.stages["static"] = True
            else:
                res.stages["static"] = None
            res.stages["mutation"] = None                # PIT is wired in mutation.py; enabled per-experiment
            res.duration_s = time.time() - t0
            return res
        finally:
            if not keep_dir:
                import shutil; shutil.rmtree(proj, ignore_errors=True)

"""Structured bug context handed to the patch generator (Stage 6 of the methodology)."""
from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from ..localization.aggregator import Suspicious
from ..testing.results import SuiteResult
from .failing_test_context import failing_test_context
from .source_context import source_context
from .trace_context import stack_frames

@dataclass
class BugContext:
    failing_tests: list[dict] = field(default_factory=list)
    stack_trace: list[dict] = field(default_factory=list)
    suspicious_locations: list[dict] = field(default_factory=list)
    source_context: list[dict] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)
    static_findings: list[dict] = field(default_factory=list)
    repository_context: dict = field(default_factory=dict)
    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

class ContextBuilder:
    def __init__(self, top_k: int = 5):
        self.top_k = top_k

    def build(self, project: Path, source_dirs: tuple[str, ...], baseline: SuiteResult,
              ranked: list[Suspicious], build_system: str = "maven") -> BugContext:
        ctx = BugContext()
        ctx.failing_tests = [failing_test_context(r) for r in baseline.failing]
        for r in baseline.failing:
            ctx.stack_trace += stack_frames(r.stack_trace)
        seen = set()
        for s in ranked[: self.top_k]:
            ctx.suspicious_locations.append({"rank": s.rank, "file": s.file, "class": s.cls,
                                             "method": s.method, "line": s.line, "score": s.score})
            sc = source_context(project, source_dirs, s.file, s.line)
            if sc and (sc["file"], sc["method_start"]) not in seen:
                seen.add((sc["file"], sc["method_start"]))
                ctx.source_context.append(sc)
        ctx.coverage = {"suspicious_files": sorted({s.file for s in ranked[: self.top_k]})}
        ctx.repository_context = {"build_system": build_system, "baseline": baseline.stats()}
        return ctx

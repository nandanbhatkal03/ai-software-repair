"""End-to-end pipeline (Stages 1-10). Each step is also usable on its own through the CLI."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from .analysis.coverage.collector import CoverageCollector, ExecutionMatrix
from .context.builder import BugContext, ContextBuilder
from .core.config import Config
from .core.exceptions import AisrError
from .explainability.report import render_report
from .localization.aggregator import FaultLocalizer, Suspicious
from .ranking.ranker import PatchRanker
from .repair.generator import LLMGenerator, TemplateGenerator
from .repository.detector import ProjectInfo
from .repository.manager import RepositoryManager
from .repository.workspace import Workspace
from .testing.results import SuiteResult
from .testing.runner import CommandRunner, TestRunner
from .validation.pipeline import PatchValidator

@dataclass
class LocalizationOutput:
    ws: Workspace
    info: ProjectInfo
    baseline: SuiteResult
    matrix: ExecutionMatrix
    ranked: list[Suspicious]

class Pipeline:
    def __init__(self, config: Config | None = None, runner: CommandRunner | None = None):
        self.cfg = config or Config()
        if runner is None and self.cfg.use_docker:
            from .testing.runner import DockerRunner
            runner = DockerRunner(self.cfg)          # AISR_USE_DOCKER=1: every build/test command runs in a sandbox
        self.runner = runner
        self.tr = TestRunner(self.cfg, runner)
        self.cov = CoverageCollector(self.cfg, runner)

    def localize(self, source: str | Path, metric: str = "ochiai", max_tests: int | None = None) -> LocalizationOutput:
        ws, info = RepositoryManager(self.cfg).import_project(source)
        if info.build_system == "unknown":
            raise AisrError("no pom.xml / build.gradle found - unsupported project")
        baseline = self.tr.run_suite(ws.work, info.build_system)
        if not baseline.build_ok:
            raise AisrError("baseline build failed; cannot localise faults")
        if not baseline.failing:
            raise AisrError("baseline has no failing test - nothing to repair")
        tests = {r.case.id: r.outcome for r in baseline.results if r.outcome.value != "skipped"}
        matrix = self.cov.collect(ws.work, tests, max_tests)
        return LocalizationOutput(ws, info, baseline, matrix, FaultLocalizer(metric).rank(matrix))

    def repair(self, source: str | Path, generator: str = "template", backend=None, metric: str = "ochiai",
               max_tests: int | None = None, top_k: int = 5, static_cmd: list[str] | None = None) -> tuple[str, dict]:
        lo = self.localize(source, metric, max_tests)
        ctx: BugContext = ContextBuilder(top_k).build(lo.ws.work, lo.info.source_dirs, lo.baseline, lo.ranked, lo.info.build_system)
        gen = (TemplateGenerator(lo.ws.work, top_k) if generator == "template"
               else LLMGenerator(backend, lo.ws.work, min(top_k, 3)))
        patches = gen.generate(ctx, lo.info.source_dirs)
        failing_ids = [r.case.id for r in lo.baseline.failing]
        passing = {r.case.id for r in lo.baseline.passing}
        validator = PatchValidator(lo.ws, lo.info.build_system, self.tr, failing_ids, passing, static_cmd,
                                   source_dirs=lo.info.source_dirs)
        results = [(p, validator.validate(p)) for p in patches]
        fl = {(s.file, s.line): s.score for s in lo.ranked}
        ranked = PatchRanker(fl).rank(results)
        rejected = [(p.id, v) for p, v in results if not v.plausible]
        report = render_report(Path(str(source)).name, failing_ids, lo.ranked, ranked, rejected, lo.ws.work)
        summary = {"generated": len(patches), "plausible": len(ranked), "rejected": len(rejected),
                   "best": ranked[0].patch.id if ranked else None}
        return report, summary

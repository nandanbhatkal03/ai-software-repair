"""End-to-end pipeline (Stages 1-10). Each step is also usable on its own through the CLI."""
from __future__ import annotations
import json, time
from dataclasses import asdict, dataclass
from pathlib import Path
from .analysis.coverage.collector import CoverageCollector, ExecutionMatrix
from .context.builder import BugContext, ContextBuilder
from .core.config import Config
from .core.exceptions import AisrError
from .explainability.report import render_report
from .localization.aggregator import FaultLocalizer, Suspicious
from .ranking.ranker import PatchRanker, RankedPatch
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
            raise AisrError("baseline build failed; cannot localise faults. Last output: " + baseline.raw_log.strip()[-300:])
        if not baseline.failing:
            raise AisrError("baseline has no failing test - nothing to repair")
        tests = {r.case.id: r.outcome for r in baseline.results if r.outcome.value != "skipped"}
        matrix = self.cov.collect(ws.work, tests, max_tests, info.build_system)
        return LocalizationOutput(ws, info, baseline, matrix, FaultLocalizer(metric).rank(matrix))

    def localize_all(self, source: str | Path, metrics: list[str], max_tests: int | None = None):
        """One (expensive) coverage collection, several metrics ranked from the same matrix (fair RQ1 comparison)."""
        lo = self.localize(source, metrics[0], max_tests)
        return lo, {m: FaultLocalizer(m).rank(lo.matrix) for m in metrics}

    @staticmethod
    def stack_trace_locations(lo_project: Path, source_dirs: tuple[str, ...], baseline: SuiteResult, k: int = 5) -> list[Suspicious]:
        """Config C (no fault localization): candidate locations are only the project-source frames of the failing
        tests' stack traces, innermost first, all with score 0 (no spectrum evidence)."""
        from .context.trace_context import stack_frames
        from .experiments.groundtruth import class_to_relpath
        out: list[Suspicious] = []
        for r in baseline.failing:
            for f in stack_frames(r.stack_trace):
                rel = class_to_relpath(f["class"])
                if any((Path(lo_project) / d / rel).is_file() for d in source_dirs) and (rel, f["line"]) not in {(s.file, s.line) for s in out}:
                    out.append(Suspicious(len(out) + 1, rel, f["class"], f["method"], f["line"], 0.0))
        return out[:k]

    def repair(self, source: str | Path, generator: str = "template", backend=None, metric: str = "ochiai",
               max_tests: int | None = None, top_k: int = 5, static_cmd: list[str] | None = None,
               use_fl: bool = True, rank_patches: bool = True, run_mutation: bool = False) -> tuple[str, dict]:
        t0 = time.time()
        lo = self.localize(source, metric, max_tests)
        t_loc = time.time() - t0
        if not use_fl:
            lo.ranked = self.stack_trace_locations(lo.ws.work, lo.info.source_dirs, lo.baseline, top_k)
        ctx: BugContext = ContextBuilder(top_k).build(lo.ws.work, lo.info.source_dirs, lo.baseline, lo.ranked, lo.info.build_system)
        gen = (TemplateGenerator(lo.ws.work, top_k) if generator == "template"
               else LLMGenerator(backend, lo.ws.work, min(top_k, 3)))
        t1 = time.time()
        patches = gen.generate(ctx, lo.info.source_dirs)
        t_gen = time.time() - t1
        failing_ids = [r.case.id for r in lo.baseline.failing]
        passing = {r.case.id for r in lo.baseline.passing}
        validator = PatchValidator(lo.ws, lo.info.build_system, self.tr, failing_ids, passing, static_cmd,
                                   run_mutation=run_mutation, source_dirs=lo.info.source_dirs)
        t2 = time.time()
        results = [(p, validator.validate(p)) for p in patches]
        t_val = time.time() - t2
        fl = {(s.file, s.line): s.score for s in lo.ranked}
        ranked = PatchRanker(fl).rank(results)
        if not rank_patches:      # config B/C-style: first plausible patch in generation order, no scoring
            plaus = [(p, v) for p, v in results if v.plausible]
            ranked = [RankedPatch(i, p, v, 0.0, {}) for i, (p, v) in enumerate(plaus, 1)] if plaus else []
        rejected = [(p.id, v) for p, v in results if not v.plausible]
        report = render_report(Path(str(source)).name, failing_ids, lo.ranked, ranked, rejected, lo.ws.work)
        summary = {"generated": len(patches), "plausible": len(ranked), "rejected": len(rejected),
                   "best": ranked[0].patch.id if ranked else None,
                   "plausible_ids": [r.patch.id for r in ranked], "validation_runs": sum(v.test_runs for _, v in results),
                   "work_dir": str(lo.ws.work),
                   "timing_s": {"localization": round(t_loc, 2), "generation": round(t_gen, 2), "validation": round(t_val, 2)},
                   "llm_usage": dict(getattr(backend, "stats", {}) or {}), "plausible_patches": [asdict(r.patch) for r in ranked]}
        return report, summary

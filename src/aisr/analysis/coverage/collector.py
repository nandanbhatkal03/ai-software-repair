"""Builds the execution (coverage) matrix: for every test, which statements it executed."""
from __future__ import annotations
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from ...core.config import Config
from ...core.exceptions import CoverageError
from ...testing.results import Outcome, TestCase
from ...testing.runner import CommandRunner, LocalRunner
from .jacoco import CoverageReport, Line, parse_jacoco_xml

@dataclass
class ExecutionMatrix:
    coverage: dict[str, set[Line]] = field(default_factory=dict)   # test id -> covered lines
    outcomes: dict[str, Outcome] = field(default_factory=dict)     # test id -> outcome
    executable: set[Line] = field(default_factory=set)
    methods: dict[str, list[tuple[int, str, str]]] = field(default_factory=dict)

    @property
    def failing(self) -> list[str]:
        return [t for t, o in self.outcomes.items() if o in (Outcome.FAIL, Outcome.ERROR)]
    @property
    def passing(self) -> list[str]:
        return [t for t, o in self.outcomes.items() if o == Outcome.PASS]
    def add(self, test_id: str, outcome: Outcome, rep: CoverageReport) -> None:
        self.coverage[test_id] = rep.covered
        self.outcomes[test_id] = outcome
        self.executable |= rep.executable
        for f, ms in rep.methods.items():
            self.methods.setdefault(f, ms)

class CoverageCollector:
    """Per-test coverage via JaCoCo's Maven plugin, one test per invocation (simple and correct;
    JaCoCo's default report is aggregated over the whole run, so tests must be executed separately).
    Granularity 'class' trades precision for speed on large suites."""
    def __init__(self, config: Config | None = None, runner: CommandRunner | None = None):
        self.config = config or Config()
        self.runner = runner or LocalRunner()

    def _cmd(self, selector: str) -> list[str]:
        j = f"org.jacoco:jacoco-maven-plugin:{self.config.jacoco_version}"
        return ["mvn", "-B", "-q", f"{j}:prepare-agent", "test", "-Dmaven.test.failure.ignore=true",
                f"-Dtest={selector}", "-DfailIfNoTests=false", f"{j}:report"]

    def collect_one(self, project: Path, selector: str) -> CoverageReport:
        project = Path(project)
        for d in ("target/site/jacoco", "target/jacoco.exec"):
            p = project / d
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
        self.runner.run(self._cmd(selector), project, self.config.test_timeout)
        xml = project / "target" / "site" / "jacoco" / "jacoco.xml"
        if not xml.exists():
            raise CoverageError(f"no JaCoCo report produced for {selector}")
        return parse_jacoco_xml(xml)

    def collect(self, project: Path, tests: dict[str, Outcome], max_tests: int | None = None) -> ExecutionMatrix:
        """`tests` maps 'Class#method' -> baseline outcome (from the baseline test run).
        Failing tests are always kept; passing tests are truncated first if max_tests is set."""
        failing = [t for t, o in tests.items() if o in (Outcome.FAIL, Outcome.ERROR)]
        passing = [t for t, o in tests.items() if o == Outcome.PASS]
        if max_tests is not None:
            passing = passing[: max(0, max_tests - len(failing))]
        m = ExecutionMatrix()
        for tid in failing + passing:
            try:
                m.add(tid, tests[tid], self.collect_one(project, tid))
            except CoverageError:
                continue          # a test that produces no coverage cannot contribute evidence
        return m

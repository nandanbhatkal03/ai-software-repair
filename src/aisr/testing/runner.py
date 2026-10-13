"""Test execution. All commands go through a CommandRunner so they can be sandboxed (Docker) or faked in tests."""
from __future__ import annotations
import shutil, subprocess, time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from ..core.config import Config
from ..core.exceptions import TestExecutionError
from .parser import parse_report_dir
from .results import SuiteResult, TestCase

@dataclass
class CommandResult:
    returncode: int
    output: str
    timed_out: bool = False

class CommandRunner(Protocol):
    def run(self, cmd: list[str], cwd: Path, timeout: int) -> CommandResult: ...

class LocalRunner:
    """Runs on the host. Fine for trusted benchmark code; use DockerRunner for generated patches."""
    def run(self, cmd, cwd, timeout):
        try:
            p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
            return CommandResult(p.returncode, p.stdout + p.stderr)
        except (FileNotFoundError, PermissionError) as e:      # missing tool, or an unreadable PATH entry / non-executable file
            return CommandResult(127, f"command not found or not executable: {cmd[0]} ({type(e).__name__}); install it or fix PATH")
        except subprocess.TimeoutExpired as e:
            return CommandResult(-1, (e.stdout or b"").decode(errors="ignore") if isinstance(e.stdout, bytes) else str(e.stdout or ""), True)

class DockerRunner:
    """Throw-away container per command: CPU/mem limits, timeout, NO network, project mounted at /work.
    Dependencies must already be cached (mount a pre-populated ~/.m2 read-only, or bake into the image)."""
    def __init__(self, config: Config, m2_cache: Path | None = None):
        self.config, self.m2_cache = config, m2_cache

    def build_command(self, cmd: list[str], cwd: Path) -> list[str]:
        d = ["docker", "run", "--rm", "--network", "none",
             "--cpus", self.config.docker_cpus, "--memory", self.config.docker_memory,
             "--pids-limit", "512", "-v", f"{Path(cwd).resolve()}:/work", "-w", "/work"]
        if self.m2_cache:
            d += ["-v", f"{Path(self.m2_cache).resolve()}:/root/.m2:ro"]
        return d + [self.config.docker_image, *cmd]

    def run(self, cmd, cwd, timeout):
        return LocalRunner().run(self.build_command(cmd, cwd), Path("."), timeout)

def maven_test_command(build_system: str, selector: str | None = None, offline: bool = False) -> list[str]:
    if build_system == "defects4j":
        from .defects4j import build_test_command
        return build_test_command(selector)
    if build_system == "maven":
        cmd = ["mvn", "-B", "-q"] + (["-o"] if offline else []) + ["test", "-Dmaven.test.failure.ignore=true"]
        if selector:
            cmd.append(f"-Dtest={selector}")
        return cmd
    if build_system == "gradle":
        cmd = ["gradle", "test", "--continue"] + (["--tests", selector.replace("#", ".")] if selector else [])
        return cmd
    raise TestExecutionError(f"unsupported build system: {build_system}")

class TestRunner:
    __test__ = False
    def __init__(self, config: Config | None = None, runner: CommandRunner | None = None):
        self.config = config or Config()
        self.runner = runner or LocalRunner()

    def run_suite(self, project_dir: Path, build_system: str, selector: str | None = None,
                  offline: bool = False) -> SuiteResult:
        project_dir = Path(project_dir)
        reports = project_dir / "target" / "surefire-reports"
        if reports.exists():
            shutil.rmtree(reports)          # never read stale reports
        t0 = time.time()
        if build_system == "defects4j":
            from .defects4j import suite_from_files
            for stale in ("all_tests", "failing_tests"):      # the formatter APPENDS; always start clean
                (project_dir / stale).unlink(missing_ok=True)
            res = self.runner.run(maven_test_command(build_system, selector), project_dir, self.config.test_timeout)
            return suite_from_files(project_dir, res.returncode == 0 and not res.timed_out or (project_dir / "all_tests").exists(),
                                    res.output[-20000:], time.time() - t0)
        res = self.runner.run(maven_test_command(build_system, selector, offline), project_dir, self.config.test_timeout)
        parsed = parse_report_dir(project_dir)
        # No reports + non-zero exit => build/compile failure (or timeout), not "all tests passed".
        build_ok = bool(parsed) or (res.returncode == 0 and not res.timed_out)
        return SuiteResult(parsed, build_ok, res.output[-20000:], time.time() - t0)

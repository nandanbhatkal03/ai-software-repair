"""Defects4J adapter. Formats verified against Defects4J 3.0.1 sources (Formatter.java, Utils.pm, d4j-test/coverage/export):
  failing_tests : lines `--- pkg.Class::method` followed by the stack trace (class-level problems: `--- pkg.Class`)
  all_tests     : one JUnit toString per executed test: `method(pkg.Class)` or `method[params](pkg.Class)`
Commands run with cwd = the checked-out project (no -w), so they also work inside a container mount."""
from __future__ import annotations
import re
from pathlib import Path
from ..core.exceptions import TestExecutionError
from .results import Outcome, SuiteResult, TestCase, TestResult

_ALL = re.compile(r"^([^\[\(\s]+)(\[.*\])?\((.+)\)\s*$")
_FAIL = re.compile(r"^--- ([^:\s]+)(?:::(\S+))?\s*$")

def parse_all_tests(text: str) -> list[TestCase]:
    seen, out = set(), []
    for line in text.splitlines():
        m = _ALL.match(line.strip())
        if m:
            tc = TestCase(m.group(3), m.group(1))      # parameters stripped, like Defects4J's own formatter
            if tc.id not in seen:
                seen.add(tc.id); out.append(tc)
    return out

def parse_failing_tests(text: str) -> list[tuple[str, str | None, str]]:
    """[(class, method_or_None, stack_trace)]"""
    out, cur = [], None
    for line in text.splitlines():
        m = _FAIL.match(line)
        if m:
            if cur: out.append((cur[0], cur[1], "\n".join(cur[2]).strip()))
            cur = (m.group(1), m.group(2), [])
        elif cur is not None:
            cur[2].append(line)
    if cur: out.append((cur[0], cur[1], "\n".join(cur[2]).strip()))
    return out

def suite_from_files(project: Path, build_ok: bool = True, log: str = "", duration: float = 0.0) -> SuiteResult:
    project = Path(project)
    allf, failf = project / "all_tests", project / "failing_tests"
    all_tests = parse_all_tests(allf.read_text(errors="replace")) if allf.exists() else []
    failing = parse_failing_tests(failf.read_text(errors="replace")) if failf.exists() else []
    results: dict[str, TestResult] = {}
    for t in all_tests:
        results[t.id] = TestResult(t, Outcome.PASS)
    for cls, meth, stack in failing:
        if meth is None:
            continue                                       # class-level failure (initialisation); no method to blame
        tc = TestCase(cls, meth)
        msg = stack.splitlines()[0] if stack else ""
        results[tc.id] = TestResult(tc, Outcome.FAIL, 0.0, msg, stack)
    return SuiteResult(list(results.values()), build_ok and bool(results), log, duration)

def build_test_command(selector: str | None = None) -> list[str]:
    cmd = ["defects4j", "test"]
    if selector:
        cmd += ["-t", selector.replace("#", "::")]
    return cmd

def compile_command() -> list[str]:
    return ["defects4j", "compile"]

def export_command(prop: str) -> list[str]:
    return ["defects4j", "export", "-p", prop]

def coverage_command(selector: str, instrument_file: str) -> list[str]:
    """`-i` is REQUIRED for a fair evaluation: by default Defects4J instruments only the classes modified by the
    bug fix, which would hand the fault's class to the localiser (oracle leakage)."""
    return ["defects4j", "coverage", "-t", selector.replace("#", "::"), "-i", instrument_file]

def read_properties(project: Path) -> dict[str, str]:
    f = Path(project) / "defects4j.build.properties"
    props: dict[str, str] = {}
    if f.exists():
        for line in f.read_text(errors="replace").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1); props[k.strip()] = v.strip()
    return props

def require_properties(project: Path) -> dict[str, str]:
    p = read_properties(project)
    if not p:
        raise TestExecutionError(f"{project} is not a Defects4J checkout (no defects4j.build.properties)")
    return p

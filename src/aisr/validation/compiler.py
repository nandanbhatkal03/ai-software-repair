from __future__ import annotations
import re
from pathlib import Path
from ..core.config import Config
from ..testing.runner import CommandRunner, LocalRunner

def _strip(text: str) -> str:
    text = re.sub(r"//.*|/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '""', text)

def _delta(text: str) -> dict[str, int] | None:
    """Net count of open-minus-close per bracket kind; None if a closer ever precedes its opener within the text
    when the text is meant to be self-contained (checked by caller)."""
    d = {"(": 0, "[": 0, "{": 0}
    pairs = {")": "(", "]": "[", "}": "{"}
    for ch in _strip(text):
        if ch in d: d[ch] += 1
        elif ch in pairs: d[pairs[ch]] -= 1
    return d

def syntax_ok(replacement: str, original: str | None = None) -> bool:
    """Cheap pre-filter (stage 1) run before paying for a build.
    A line-level patch may legitimately leave a brace open (e.g. `if (c) {`), so brackets are compared against the
    text being replaced: the replacement must have the same net bracket balance as the original lines.
    Without `original`, the replacement must be self-balanced."""
    if not replacement.strip():
        return False
    want = _delta(original) if original is not None else {"(": 0, "[": 0, "{": 0}
    return _delta(replacement) == want

def compile_ok(project: Path, build_system: str, runner: CommandRunner | None = None, config: Config | None = None) -> tuple[bool, str]:
    cfg, runner = config or Config(), runner or LocalRunner()
    if build_system == "defects4j":
        from ..testing.defects4j import compile_command
        cmd = compile_command()
    else:
        cmd = ["mvn", "-B", "-q", "compile", "test-compile"] if build_system == "maven" else ["gradle", "classes", "testClasses"]
    r = runner.run(cmd, project, cfg.test_timeout)
    return r.returncode == 0 and not r.timed_out, r.output[-4000:]

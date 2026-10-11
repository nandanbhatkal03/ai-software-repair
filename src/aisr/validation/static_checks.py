"""Optional static-analysis stage: run any command that prints one finding per line (e.g. PMD/SpotBugs wrapper)
before and after the patch; report the change in finding count. Disabled unless a command is configured."""
from __future__ import annotations
from pathlib import Path
from ..testing.runner import CommandRunner, LocalRunner

def count_findings(project: Path, cmd: list[str] | None, runner: CommandRunner | None = None) -> int | None:
    if not cmd:
        return None
    r = (runner or LocalRunner()).run(cmd, project, 300)
    return len([l for l in r.output.splitlines() if l.strip()])

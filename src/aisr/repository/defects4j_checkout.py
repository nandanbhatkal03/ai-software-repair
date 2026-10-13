from __future__ import annotations
from pathlib import Path
from ..core.exceptions import RepositoryError
from ..testing.runner import CommandRunner, LocalRunner

def checkout(project_id: str, bug_id: int, dest_root: Path, runner: CommandRunner | None = None) -> tuple[Path, Path]:
    """Check out buggy (`<id>b`) and fixed (`<id>f`) versions. Needs `defects4j` on PATH (see benchmarks/README.md)."""
    runner, dest_root = runner or LocalRunner(), Path(dest_root)
    out = []
    for suffix in ("b", "f"):
        d = dest_root / f"{project_id}_{bug_id}{suffix}"
        if not (d / "defects4j.build.properties").exists():
            d.parent.mkdir(parents=True, exist_ok=True)
            r = runner.run(["defects4j", "checkout", "-p", project_id, "-v", f"{bug_id}{suffix}", "-w", str(d)], d.parent, 1800)
            if r.returncode != 0:
                raise RepositoryError(f"defects4j checkout {project_id}-{bug_id}{suffix} failed: {r.output[-500:]}")
        out.append(d)
    return out[0], out[1]

"""Isolated repair workspaces. The original project is never modified."""
from __future__ import annotations
import os, shutil, stat, uuid
from pathlib import Path
from ..core.exceptions import RepositoryError

_IGNORE = shutil.ignore_patterns(".git", "target", "build", "__pycache__", ".gradle")

def _make_readonly(path: Path) -> None:
    for p in [path, *path.rglob("*")]:
        mode = p.stat().st_mode
        p.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))

def _make_writable(path: Path) -> None:
    """Copies of the read-only baseline inherit its permissions (copytree copies modes); undo that.
    Directories first (top-down) so their contents become reachable."""
    path = Path(path)
    path.chmod(path.stat().st_mode | stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
    for dirpath, dirnames, filenames in os.walk(path):
        for n in dirnames:
            d = Path(dirpath, n); d.chmod(d.stat().st_mode | stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
        for n in filenames:
            f = Path(dirpath, n); f.chmod(f.stat().st_mode | stat.S_IWUSR | stat.S_IRUSR)

class Workspace:
    """baseline/ is a read-only snapshot; work/ is a mutable copy; each patch gets its own copy."""
    def __init__(self, root: Path):
        self.root = Path(root)
        self.baseline = self.root / "baseline"
        self.work = self.root / "work"

    @classmethod
    def create(cls, source: Path, workspace_root: Path) -> "Workspace":
        source = Path(source).resolve()
        if not source.is_dir():
            raise RepositoryError(f"not a directory: {source}")
        ws = cls(Path(workspace_root) / f"{source.name}-{uuid.uuid4().hex[:8]}")
        ws.root.mkdir(parents=True)
        # A Defects4J checkout is relocatable (.defects4j.config holds only pid/vid); only drop VCS metadata there.
        ignore = shutil.ignore_patterns(".git") if (source / "defects4j.build.properties").exists() else _IGNORE
        shutil.copytree(source, ws.baseline, ignore=ignore)
        shutil.copytree(ws.baseline, ws.work)
        _make_readonly(ws.baseline)
        return ws

    def fresh_copy(self, name: str) -> Path:
        """Pristine mutable copy of the baseline (used per candidate patch)."""
        dst = self.root / "candidates" / name
        if dst.exists():
            _rm(dst)
        shutil.copytree(self.baseline, dst)
        _make_writable(dst)
        return dst

    def cleanup(self) -> None:
        _rm(self.root)

def _rm(path: Path) -> None:
    path = Path(path)
    if path.exists():
        _make_writable(path)           # read-only directories block unlinking their contents
    shutil.rmtree(path, ignore_errors=False)

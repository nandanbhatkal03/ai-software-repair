from __future__ import annotations
import subprocess, tempfile
from pathlib import Path
from ..core.config import Config
from ..core.exceptions import RepositoryError
from .detector import ProjectInfo, detect_project
from .workspace import Workspace

class RepositoryManager:
    def __init__(self, config: Config | None = None):
        self.config = config or Config()

    def import_project(self, source: str | Path) -> tuple[Workspace, ProjectInfo]:
        """`source` is a local path or a git URL."""
        src = str(source)
        if src.startswith(("http://", "https://", "git@")):
            tmp = Path(tempfile.mkdtemp(prefix="aisr-clone-"))
            r = subprocess.run(["git", "clone", "--depth", "1", src, str(tmp / "repo")],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise RepositoryError(f"git clone failed: {r.stderr.strip()}")
            path = tmp / "repo"
        else:
            path = Path(src)
        self.config.workspace_root.mkdir(parents=True, exist_ok=True)
        ws = Workspace.create(path, self.config.workspace_root)
        info = detect_project(ws.work)
        return ws, info

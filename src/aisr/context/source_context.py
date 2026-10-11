from __future__ import annotations
from pathlib import Path
from ..analysis.static.java_methods import enclosing_method, imports

def read_source(project: Path, source_dirs: tuple[str, ...], rel_file: str) -> tuple[Path, str] | None:
    for d in source_dirs or (".",):
        p = Path(project) / d / rel_file
        if p.is_file():
            return p, p.read_text(errors="replace")
    return None

def source_context(project: Path, source_dirs: tuple[str, ...], rel_file: str, line: int, window: int = 3) -> dict | None:
    got = read_source(project, source_dirs, rel_file)
    if not got:
        return None
    path, text = got
    lines = text.splitlines()
    m = enclosing_method(text, line)
    lo, hi = (m.start_line, m.end_line) if m else (max(1, line - 10), min(len(lines), line + 10))
    return {
        "file": rel_file, "path": str(path), "line": line,
        "method": m.name if m else None, "method_start": lo, "method_end": hi,
        "method_source": "\n".join(f"{i}: {lines[i-1]}" for i in range(lo, hi + 1)),
        "suspicious_line": lines[line - 1] if 0 < line <= len(lines) else "",
        "imports": imports(text),
    }

"""A candidate patch = replace lines [start, end] of one file with new text. Small, auditable, easy to diff."""
from __future__ import annotations
import difflib
from dataclasses import dataclass, field
from pathlib import Path
from ..core.exceptions import PatchError

@dataclass(frozen=True)
class Patch:
    id: str
    file: str            # path relative to the project root
    start_line: int      # 1-based inclusive
    end_line: int
    replacement: str     # may be multi-line, no trailing newline needed
    origin: str = "unknown"   # "template:<op>" | "llm:<model>"
    rationale: str = ""

    def apply(self, project: Path) -> str:
        p = Path(project) / self.file
        if not p.is_file():
            raise PatchError(f"file not found: {self.file}")
        lines = p.read_text(errors="replace").splitlines()
        if not (1 <= self.start_line <= self.end_line <= len(lines)):
            raise PatchError(f"line range {self.start_line}-{self.end_line} outside {self.file}")
        new = lines[: self.start_line - 1] + self.replacement.splitlines() + lines[self.end_line:]
        p.write_text("\n".join(new) + "\n")
        return "\n".join(lines)

    def diff(self, original_text: str) -> str:
        lines = original_text.splitlines()
        new = lines[: self.start_line - 1] + self.replacement.splitlines() + lines[self.end_line:]
        return "".join(difflib.unified_diff([l + "\n" for l in lines], [l + "\n" for l in new],
                                            f"a/{self.file}", f"b/{self.file}", n=2))

    @property
    def changed_lines(self) -> int:
        return max(self.end_line - self.start_line + 1, len(self.replacement.splitlines()))

def dedupe(patches: list[Patch], original: dict[str, str]) -> list[Patch]:
    """Drop exact duplicates and no-op patches."""
    seen, out = set(), []
    for p in patches:
        key = (p.file, p.start_line, p.end_line, p.replacement.strip())
        orig = "\n".join(original.get(p.file, "").splitlines()[p.start_line - 1:p.end_line]).strip()
        if key in seen or p.replacement.strip() == orig:
            continue
        seen.add(key); out.append(p)
    return out

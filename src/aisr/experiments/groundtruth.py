"""Ground-truth faulty lines from the buggy -> developer-fixed diff.
Convention (state it in the paper): lines removed/changed in the buggy file are faulty; for a pure insertion
(fault of omission) the two neighbouring buggy lines are both accepted and the better rank is used."""
from __future__ import annotations
import difflib, re
from pathlib import Path

def _norm(l: str) -> str:
    return re.sub(r"\s+", " ", l).strip()

def faulty_lines(buggy_text: str, fixed_text: str) -> set[int]:
    a, b = buggy_text.splitlines(), fixed_text.splitlines()
    sm = difflib.SequenceMatcher(a=[_norm(x) for x in a], b=[_norm(x) for x in b], autojunk=False)
    out: set[int] = set()
    for tag, i1, i2, _, _ in sm.get_opcodes():
        if tag in ("replace", "delete"):
            out |= set(range(i1 + 1, i2 + 1))
        elif tag == "insert":
            out |= {n for n in (i1, i1 + 1) if 1 <= n <= len(a)}
    return out

def class_to_relpath(cls: str) -> str:
    return cls.split("$")[0].replace(".", "/") + ".java"

def ground_truth(buggy: Path, fixed: Path, src_dir: str, modified_classes: list[str]) -> set[tuple[str, int]]:
    truth: set[tuple[str, int]] = set()
    for rel in {class_to_relpath(c) for c in modified_classes}:
        fb, ff = Path(buggy, src_dir, rel), Path(fixed, src_dir, rel)
        if fb.is_file() and ff.is_file():
            truth |= {(rel, n) for n in faulty_lines(fb.read_text(errors="replace"), ff.read_text(errors="replace"))}
    return truth

def patch_matches_fix(patched_text: str, fixed_text: str) -> bool:
    """True if the patched file equals the developer-fixed file modulo whitespace => certainly correct.
    False means 'unknown' (needs manual review), NOT 'incorrect'."""
    return [_norm(l) for l in patched_text.splitlines() if l.strip()] == [_norm(l) for l in fixed_text.splitlines() if l.strip()]

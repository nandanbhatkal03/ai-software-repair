from __future__ import annotations
import re

_FRAME = re.compile(r"at\s+([\w.$]+)\.([\w$<>]+)\(([\w$]+\.java):(\d+)\)")

def stack_frames(stack_trace: str) -> list[dict]:
    """Parsed 'at pkg.Cls.method(File.java:12)' frames, innermost first."""
    return [{"class": m[0], "method": m[1], "file": m[2], "line": int(m[3])} for m in _FRAME.findall(stack_trace)]

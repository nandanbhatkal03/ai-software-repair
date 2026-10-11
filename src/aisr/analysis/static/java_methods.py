"""Lightweight Java method locator (regex + brace matching on comment/string-stripped text).
Good enough for context extraction on typical Defects4J code; swap for tree-sitter later (same interface)."""
from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class MethodSpan:
    name: str
    start_line: int   # 1-based, line of the signature
    end_line: int     # 1-based, line of the closing brace

_SIG = re.compile(
    r"(?m)^[ \t]*(?:@\w+(?:\([^)]*\))?\s+)*(?:(?:public|protected|private|static|final|abstract|synchronized|native|default)\s+)*"
    r"(?:<[^>]+>\s+)?(?:[\w.<>\[\],?]+\s+)?(?P<name>\w+)\s*\((?P<args>[^;{}()]*(?:\([^)]*\)[^;{}()]*)*)\)\s*(?:throws\s+[\w., ]+)?\s*\{")
_KEYWORDS = {"if", "for", "while", "switch", "catch", "synchronized", "return", "new", "else", "try", "do"}

def _blank_comments_and_strings(src: str) -> str:
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if src.startswith("//", i):
            j = src.find("\n", i); j = n if j < 0 else j
            out.append(" " * (j - i)); i = j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2); j = n if j < 0 else j + 2
            out.append("".join(ch if ch == "\n" else " " for ch in src[i:j])); i = j
        elif c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(c + " " * (j - i - 2) + c if j - i >= 2 else c); i = j
        else:
            out.append(c); i += 1
    return "".join(out)

def find_methods(source: str) -> list[MethodSpan]:
    clean = _blank_comments_and_strings(source)
    spans: list[MethodSpan] = []
    for m in _SIG.finditer(clean):
        name = m.group("name")
        if name in _KEYWORDS:
            continue
        depth, i = 0, m.end() - 1
        while i < len(clean):
            if clean[i] == "{": depth += 1
            elif clean[i] == "}":
                depth -= 1
                if depth == 0: break
            i += 1
        start_line = clean.count("\n", 0, m.start("name")) + 1
        end_line = clean.count("\n", 0, i) + 1
        spans.append(MethodSpan(name, start_line, end_line))
    return spans

def enclosing_method(source: str, line: int) -> MethodSpan | None:
    best = None
    for s in find_methods(source):
        if s.start_line <= line <= s.end_line and (best is None or s.start_line >= best.start_line):
            best = s
    return best

def imports(source: str) -> list[str]:
    return re.findall(r"(?m)^\s*import\s+[^;]+;", source)

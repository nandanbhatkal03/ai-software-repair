"""Rule/template-based mutation operators (Baseline B). Each yields alternative versions of ONE source line."""
from __future__ import annotations
import re
from typing import Iterator

_REL = {"<": ["<=", ">", ">="], "<=": ["<", ">", ">="], ">": [">=", "<", "<="], ">=": [">", "<", "<="],
        "==": ["!="], "!=": ["=="]}
_REL_RE = re.compile(r"(?<![<>=!+\-*/&|])(<=|>=|==|!=|<|>)(?![<>=])")

def relational_operator(line: str) -> Iterator[tuple[str, str]]:
    for m in _REL_RE.finditer(line):
        for alt in _REL[m.group(1)]:
            yield f"rel:{m.group(1)}->{alt}", line[: m.start()] + alt + line[m.end():]

def boundary_constant(line: str) -> Iterator[tuple[str, str]]:
    for m in re.finditer(r"(?<![\w.\"])(\d+)(?![\w.\"])", line):
        v = int(m.group(1))
        for alt in {v + 1, v - 1} - {v}:
            yield f"const:{v}->{alt}", line[: m.start()] + str(alt) + line[m.end():]

def logical_operator(line: str) -> Iterator[tuple[str, str]]:
    for a, b in (("&&", "||"), ("||", "&&")):
        i = line.find(a)
        if i >= 0:
            yield f"logic:{a}->{b}", line[:i] + b + line[i + 2:]

def negate_condition(line: str) -> Iterator[tuple[str, str]]:
    m = re.match(r"^(\s*(?:\}\s*else\s+)?if\s*\()(.*)(\)\s*\{?\s*)$", line)
    if m:
        yield "negate-if", f"{m.group(1)}!({m.group(2)}){m.group(3)}"

def add_arg_index_offset(line: str) -> Iterator[tuple[str, str]]:
    for m in re.finditer(r"\[(\w+)\]", line):
        yield "index+1", line[: m.start()] + f"[{m.group(1)} + 1]" + line[m.end():]
        yield "index-1", line[: m.start()] + f"[{m.group(1)} - 1]" + line[m.end():]

OPERATORS = [relational_operator, boundary_constant, logical_operator, negate_condition, add_arg_index_offset]

def mutate_line(line: str) -> list[tuple[str, str]]:
    seen, out = {line}, []
    for op in OPERATORS:
        for name, new in op(line):
            if new not in seen:
                seen.add(new); out.append((name, new))
    return out

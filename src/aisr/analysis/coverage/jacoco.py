"""Parse JaCoCo XML reports into covered statement (line) sets, and map lines -> methods."""
from __future__ import annotations
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

@dataclass(frozen=True, order=True)
class Line:
    file: str      # e.g. com/foo/Bar.java (package path + source file)
    line: int

@dataclass
class CoverageReport:
    covered: set[Line] = field(default_factory=set)
    executable: set[Line] = field(default_factory=set)       # lines JaCoCo can instrument
    methods: dict[str, list[tuple[int, str, str]]] = field(default_factory=dict)  # file -> [(start_line, class, method)]

def parse_jacoco_xml(path: Path) -> CoverageReport:
    root = ET.parse(path).getroot()           # ElementTree ignores the DOCTYPE/DTD; no network access
    rep = CoverageReport()
    for pkg in root.iter("package"):
        pkg_name = pkg.get("name", "")
        for sf in pkg.findall("sourcefile"):
            fname = f"{pkg_name}/{sf.get('name')}" if pkg_name else sf.get("name")
            for ln in sf.findall("line"):
                nr, ci, mi = int(ln.get("nr")), int(ln.get("ci", 0)), int(ln.get("mi", 0))
                if ci + mi == 0:
                    continue
                rep.executable.add(Line(fname, nr))
                if ci > 0:
                    rep.covered.add(Line(fname, nr))
        for cls in pkg.findall("class"):
            sfn = cls.get("sourcefilename")
            if not sfn:
                continue
            fname = f"{pkg_name}/{sfn}" if pkg_name else sfn
            cname = (cls.get("name") or "").replace("/", ".")
            for m in cls.findall("method"):
                if m.get("line"):
                    rep.methods.setdefault(fname, []).append((int(m.get("line")), cname, m.get("name", "?")))
    for v in rep.methods.values():
        v.sort()
    return rep

def method_of(rep: CoverageReport, line: Line) -> tuple[str, str] | None:
    """(class, method) whose start line is the closest at or before `line`."""
    best = None
    for start, cls, name in rep.methods.get(line.file, []):
        if start <= line.line:
            best = (cls, name)
        else:
            break
    return best

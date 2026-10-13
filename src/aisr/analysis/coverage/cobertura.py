"""Cobertura XML (written by `defects4j coverage` as coverage.xml) -> the same CoverageReport used for JaCoCo."""
from __future__ import annotations
import xml.etree.ElementTree as ET
from pathlib import Path
from .jacoco import CoverageReport, Line

def parse_cobertura_xml(path: Path) -> CoverageReport:
    root = ET.parse(path).getroot()                 # DOCTYPE/DTD is not fetched by ElementTree
    rep = CoverageReport()
    for cls in root.iter("class"):
        fname = cls.get("filename") or ""
        if not fname:
            continue
        cname = cls.get("name", "")
        for m in cls.findall("./methods/method"):
            nrs = [int(l.get("number")) for l in m.findall("./lines/line") if l.get("number")]
            if nrs:
                rep.methods.setdefault(fname, []).append((min(nrs), cname, m.get("name", "?")))
        for l in cls.findall("./lines/line"):
            nr, hits = int(l.get("number")), int(l.get("hits", 0))
            rep.executable.add(Line(fname, nr))
            if hits > 0:
                rep.covered.add(Line(fname, nr))
    for v in rep.methods.values():
        v.sort()
    return rep

"""Parse Maven Surefire / Gradle JUnit XML reports (same schema)."""
from __future__ import annotations
import xml.etree.ElementTree as ET
from pathlib import Path
from .results import Outcome, TestCase, TestResult

def parse_report(xml_path: Path) -> list[TestResult]:
    root = ET.parse(xml_path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    out: list[TestResult] = []
    for suite in suites:
        for tc in suite.iter("testcase"):
            cls = tc.get("classname") or suite.get("name") or "?"
            case = TestCase(cls, tc.get("name", "?"))
            t = float(tc.get("time") or 0)
            fail, err, skip = tc.find("failure"), tc.find("error"), tc.find("skipped")
            if fail is not None or err is not None:
                node = fail if fail is not None else err
                out.append(TestResult(case, Outcome.FAIL if fail is not None else Outcome.ERROR, t,
                                      node.get("message", "") or "", (node.text or "").strip()))
            elif skip is not None:
                out.append(TestResult(case, Outcome.SKIPPED, t))
            else:
                out.append(TestResult(case, Outcome.PASS, t))
    return out

def parse_report_dir(project_dir: Path) -> list[TestResult]:
    results: list[TestResult] = []
    dirs = [project_dir / "target" / "surefire-reports", project_dir / "build" / "test-results" / "test"]
    for d in dirs:
        if d.is_dir():
            for f in sorted(d.glob("TEST-*.xml")):
                results.extend(parse_report(f))
    return results

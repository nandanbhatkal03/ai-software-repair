from pathlib import Path
from aisr.analysis.coverage.jacoco import Line, method_of, parse_jacoco_xml
from aisr.testing.parser import parse_report
from aisr.testing.results import Outcome

SURE = """<testsuite name="p.T"><testcase classname="p.T" name="ok" time="0.5"/>
<testcase classname="p.T" name="bad" time="0.1"><failure message="boom">trace here</failure></testcase>
<testcase classname="p.T" name="err" time="0.1"><error message="npe">NPE trace</error></testcase>
<testcase classname="p.T" name="skip"><skipped/></testcase></testsuite>"""

JACOCO = """<?xml version="1.0"?><!DOCTYPE report PUBLIC "-//JACOCO//DTD Report 1.1//EN" "report.dtd">
<report name="x"><package name="com/foo"><class name="com/foo/Bar" sourcefilename="Bar.java">
<method name="a" desc="()V" line="3"/><method name="b" desc="()V" line="10"/></class>
<sourcefile name="Bar.java"><line nr="4" mi="0" ci="2"/><line nr="5" mi="1" ci="0"/><line nr="11" mi="0" ci="1"/>
<line nr="12" mi="0" ci="0"/></sourcefile></package></report>"""

def test_surefire(tmp_path):
    f = tmp_path / "TEST-p.T.xml"; f.write_text(SURE)
    r = {x.case.method: x for x in parse_report(f)}
    assert r["ok"].outcome == Outcome.PASS and r["ok"].time_s == 0.5
    assert r["bad"].outcome == Outcome.FAIL and r["bad"].message == "boom" and r["bad"].stack_trace == "trace here"
    assert r["err"].outcome == Outcome.ERROR and r["skip"].outcome == Outcome.SKIPPED
    assert r["bad"].case.id == "p.T#bad"

def test_jacoco(tmp_path):
    f = tmp_path / "jacoco.xml"; f.write_text(JACOCO)
    rep = parse_jacoco_xml(f)
    assert rep.covered == {Line("com/foo/Bar.java", 4), Line("com/foo/Bar.java", 11)}
    assert Line("com/foo/Bar.java", 5) in rep.executable          # missed but instrumentable
    assert Line("com/foo/Bar.java", 12) not in rep.executable       # no instructions at all
    assert method_of(rep, Line("com/foo/Bar.java", 4)) == ("com.foo.Bar", "a")
    assert method_of(rep, Line("com/foo/Bar.java", 11)) == ("com.foo.Bar", "b")

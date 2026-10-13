from aisr.analysis.coverage.cobertura import parse_cobertura_xml
from aisr.analysis.coverage.jacoco import Line, method_of
from aisr.experiments.groundtruth import class_to_relpath, faulty_lines, patch_matches_fix
from aisr.testing.defects4j import (coverage_command, parse_all_tests, parse_failing_tests, read_properties,
                                    suite_from_files, build_test_command)
from aisr.testing.results import Outcome

def test_all_tests_parsing_strips_parameters_and_dedupes():
    t = parse_all_tests("testA(org.x.FooTest)\ntestB[1](org.x.FooTest)\ntestB[2](org.x.FooTest)\njunk line\n")
    assert [x.id for x in t] == ["org.x.FooTest#testA", "org.x.FooTest#testB"]

def test_failing_tests_parsing():
    txt = "--- org.x.FooTest::testA\njava.lang.AssertionError: boom\n\tat org.x.Foo.f(Foo.java:3)\n--- org.x.BarTest\nclass-level\n"
    f = parse_failing_tests(txt)
    assert f[0][:2] == ("org.x.FooTest", "testA") and "Foo.java:3" in f[0][2]
    assert f[1][:2] == ("org.x.BarTest", None)

def test_suite_from_files(tmp_path):
    (tmp_path / "all_tests").write_text("testA(p.T)\ntestB(p.T)\n")
    (tmp_path / "failing_tests").write_text("--- p.T::testB\njava.lang.Error: x\n\tat p.C.m(C.java:1)\n")
    s = suite_from_files(tmp_path)
    o = {r.case.id: r for r in s.results}
    assert o["p.T#testA"].outcome == Outcome.PASS and o["p.T#testB"].outcome == Outcome.FAIL
    assert o["p.T#testB"].message == "java.lang.Error: x" and s.build_ok

def test_no_results_means_build_not_ok(tmp_path):
    assert not suite_from_files(tmp_path).build_ok

def test_commands():
    assert build_test_command("p.T#m") == ["defects4j", "test", "-t", "p.T::m"]
    c = coverage_command("p.T#m", "instrument_classes.txt")
    assert c == ["defects4j", "coverage", "-t", "p.T::m", "-i", "instrument_classes.txt"]

def test_properties(tmp_path):
    (tmp_path / "defects4j.build.properties").write_text("#c\nd4j.dir.src.classes=src/java\nd4j.dir.src.tests=src/test\n")
    assert read_properties(tmp_path)["d4j.dir.src.classes"] == "src/java"

def test_cobertura(tmp_path):
    f = tmp_path / "coverage.xml"
    f.write_text('<?xml version="1.0"?><!DOCTYPE coverage SYSTEM "http://cobertura.sourceforge.net/xml/coverage-04.dtd">'
                 '<coverage><packages><package name="a"><classes><class name="a.B" filename="a/B.java"><methods>'
                 '<method name="m" signature="()V"><lines><line number="7" hits="3"/><line number="8" hits="0"/></lines></method></methods>'
                 '<lines><line number="7" hits="3"/><line number="8" hits="0"/></lines></class></classes></package></packages></coverage>')
    r = parse_cobertura_xml(f)
    assert r.covered == {Line("a/B.java", 7)} and Line("a/B.java", 8) in r.executable
    assert method_of(r, Line("a/B.java", 8)) == ("a.B", "m")

def test_faulty_lines_replace_delete_insert():
    assert faulty_lines("a\nb\nc\n", "a\nB\nc\n") == {2}
    assert faulty_lines("a\nb\nc\n", "a\nc\n") == {2}
    assert faulty_lines("a\nc\n", "a\nb\nc\n") == {1, 2}              # omission: both neighbours
    assert faulty_lines("a\n  b  \n", "a\nb\n") == set()               # whitespace-only change is not a fault
    assert class_to_relpath("org.x.Outer$Inner") == "org/x/Outer.java"

def test_patch_matches_fix_is_whitespace_insensitive():
    assert patch_matches_fix("a\n  b\n", "a\nb\n") and not patch_matches_fix("a\nc\n", "a\nb\n")

import pytest
from pathlib import Path
from aisr.analysis.static.java_methods import enclosing_method, find_methods
from aisr.context.trace_context import stack_frames
from aisr.core.exceptions import PatchError
from aisr.experiments.metrics import exam_score, mean_rank, rank_of_fault, top_n
from aisr.localization.aggregator import Suspicious
from aisr.repair.candidates import Patch, dedupe
from aisr.repair.generator import LLMGenerator
from aisr.repair.templates.operators import mutate_line
from aisr.ranking.scoring import score
from aisr.repository.detector import detect_project
from aisr.repository.workspace import Workspace
from aisr.testing.runner import DockerRunner
from aisr.core.config import Config
from aisr.validation.compiler import syntax_ok

def test_template_operators():
    ops = dict(mutate_line("        return x >= 0;"))
    assert "        return x > 0;" in ops.values()
    assert any("x >= 1" in v for v in ops.values())
    assert mutate_line("int a = b;") == []
    assert any("!(" in v for _, v in mutate_line("    if (a < b) {"))

def test_syntax_filter():
    assert syntax_ok("return a[(i)] + 1;")
    assert not syntax_ok("return (a + 1;")
    assert not syntax_ok("   ")
    assert syntax_ok('String s = "}{"; // ) (')
    # line-level patches may keep a brace open if the replaced line did
    assert syntax_ok("    if (x != 0) {", original="    if (x == 0) {")
    assert not syntax_ok("    if (x != 0)", original="    if (x == 0) {")      # dropped the brace
    assert not syntax_ok("    if (x != 0) {")                                # not self-balanced, no original given

def test_patch_apply_and_diff(tmp_path):
    f = tmp_path / "A.java"; f.write_text("a\nb\nc\n")
    p = Patch("p1", "A.java", 2, 2, "B\nB2")
    orig = p.apply(tmp_path)
    assert f.read_text() == "a\nB\nB2\nc\n"
    assert "-b" in p.diff(orig) and "+B2" in p.diff(orig)
    with pytest.raises(PatchError): Patch("x", "A.java", 9, 9, "z").apply(tmp_path)
    with pytest.raises(PatchError): Patch("x", "Nope.java", 1, 1, "z").apply(tmp_path)

def test_dedupe_drops_noops_and_duplicates():
    orig = {"A.java": "a\nb\n"}
    ps = [Patch("1", "A.java", 1, 1, "a"), Patch("2", "A.java", 1, 1, "x"), Patch("3", "A.java", 1, 1, "x ")]
    assert [p.id for p in dedupe(ps, orig)] == ["2"]

def test_llm_reply_parsing_tolerates_fences_and_junk():
    good = '```json\n[{"start_line": 1, "end_line": 1, "replacement": "x"}, {"bad": 1}]\n```'
    assert len(LLMGenerator.parse(good)) == 1
    assert LLMGenerator.parse("no json here") == []
    assert LLMGenerator.parse("[not json]") == []

def test_java_method_finder():
    src = "class A {\n  void f() {\n    if (x) { }\n  }\n  int g(int a) { return a; }\n}\n"
    assert [(m.name, m.start_line, m.end_line) for m in find_methods(src)] == [("f", 2, 4), ("g", 5, 5)]
    assert enclosing_method(src, 3).name == "f"
    assert enclosing_method(src, 1) is None

def test_stack_frames():
    t = "java.lang.X\n\tat a.b.C.m(C.java:12)\n\tat a.D.<init>(D.java:3)"
    assert stack_frames(t) == [{"class": "a.b.C", "method": "m", "file": "C.java", "line": 12},
                               {"class": "a.D", "method": "<init>", "file": "D.java", "line": 3}]

def S(rank, line, score): return Suspicious(rank, "A.java", "A", "f", line, score)

def test_rank_tie_rules():
    ranked = [S(1, 10, 1.0), S(1, 11, 1.0), S(1, 12, 1.0), S(4, 13, 0.5)]
    f = {("A.java", 11)}
    assert rank_of_fault(ranked, f, "best") == 1
    assert rank_of_fault(ranked, f, "worst") == 3
    assert rank_of_fault(ranked, f, "average") == 2
    assert rank_of_fault(ranked, {("Z.java", 1)}) is None

def test_metric_aggregates():
    assert top_n([1, 4, None, 6], 5) == 0.5
    assert mean_rank([1, 3, None]) == 2
    assert exam_score(5, 100) == 0.05 and exam_score(None, 100) is None

def test_scoring_is_transparent():
    s, c = score({"fl_score": 1.0, "patch_size": 0.5, "llm_origin": 1.0})
    assert c["fl_score"] == 0.30 and c["llm_origin"] == 0.0 and s == round(0.30 + 0.125, 4)

def test_detector(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    (tmp_path / "src/main/java").mkdir(parents=True); (tmp_path / "src/test/java").mkdir(parents=True)
    (tmp_path / "src/main/java/A.java").write_text("class A{}")
    i = detect_project(tmp_path)
    assert (i.build_system, i.language, i.source_dirs, i.test_dirs) == ("maven", "java", ("src/main/java",), ("src/test/java",))

def test_workspace_protects_original(tmp_path):
    src = tmp_path / "proj"; src.mkdir(); (src / "A.java").write_text("x")
    ws = Workspace.create(src, tmp_path / "ws")
    import os, stat
    assert not (ws.baseline / "A.java").stat().st_mode & stat.S_IWUSR      # read-only snapshot
    if os.geteuid() != 0:                                                   # root ignores permission bits
        with pytest.raises(PermissionError):
            (ws.baseline / "A.java").write_text("hacked")
    (ws.work / "A.java").write_text("changed")
    assert (src / "A.java").read_text() == "x"
    c = ws.fresh_copy("p1"); assert (c / "A.java").read_text() == "x"
    (c / "A.java").write_text("patched")                # candidate copies must be writable (regression: root hid this)
    assert (ws.baseline / "A.java").read_text() == "x"
    ws.cleanup(); assert not ws.root.exists()

def test_docker_command_is_isolated(tmp_path):
    cmd = DockerRunner(Config()).build_command(["mvn", "test"], tmp_path)
    assert cmd[:3] == ["docker", "run", "--rm"] and "--network" in cmd and cmd[cmd.index("--network") + 1] == "none"
    assert "--memory" in cmd and "--cpus" in cmd and cmd[-2:] == ["mvn", "test"]

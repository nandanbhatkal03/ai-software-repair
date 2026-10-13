import shutil
from pathlib import Path
import pytest
from aisr.core.config import Config
from aisr.experiments.evaluate import evaluate_localization, repair_outcome, summarise_localization
from aisr.orchestrator import Pipeline
from fake_d4j import FakeDefects4J

FIX = Path(__file__).parent.parent / "fixtures" / "demo-maven"

def make_checkout(tmp_path, name, fixed=False):
    d = tmp_path / name; shutil.copytree(FIX, d)
    (d / "pom.xml").unlink()                                    # a Defects4J checkout is not a Maven project
    (d / "defects4j.build.properties").write_text("d4j.dir.src.classes=src/main/java\nd4j.dir.src.tests=src/test/java\n"
                                                  "d4j.classes.modified=demo.Calc\n")
    if fixed:
        f = d / "src/main/java/demo/Calc.java"; f.write_text(f.read_text().replace("x >= 0", "x > 0"))
    return d

@pytest.fixture
def pipe(tmp_path):
    return Pipeline(Config(workspace_root=tmp_path / "ws"), FakeDefects4J())

def test_detected_as_defects4j(tmp_path):
    from aisr.repository.detector import detect_project
    i = detect_project(make_checkout(tmp_path, "b"))
    assert i.build_system == "defects4j" and i.source_dirs == ("src/main/java",)

def test_localization_through_defects4j_adapter(tmp_path, pipe):
    lo = pipe.localize(make_checkout(tmp_path, "b"))
    assert [r.case.id for r in lo.baseline.failing] == ["demo.CalcTest#testZero"]
    assert lo.ranked[0].method == "isPositive" and lo.ranked[0].file == "demo/Calc.java"
    # `-i` was used and classes.relevant (noise filtered) drove instrumentation -- asserted inside FakeDefects4J

def test_template_repair_through_defects4j(tmp_path, pipe):
    b, f = make_checkout(tmp_path, "b"), make_checkout(tmp_path, "f", fixed=True)
    report, summary = pipe.repair(b, "template", top_k=5)
    assert summary["plausible"] >= 1
    out = repair_outcome(summary, b, f, "src/main/java")
    assert out["any_matches_fix"] and out["plausible"] == len(out["matches_developer_fix"]) + len(out["needs_manual_review"])
    assert any("x >= 1" in pd["replacement"] for pd in summary["plausible_patches"]) == bool(out["needs_manual_review"])

def test_localization_evaluation_and_summary(tmp_path, pipe):
    b, f = make_checkout(tmp_path, "b"), make_checkout(tmp_path, "f", fixed=True)
    ev = evaluate_localization(pipe, b, f, "src/main/java", ["demo.Calc"], ["ochiai", "tarantula", "jaccard", "dstar"])
    assert ev["truth"] == [["demo/Calc.java", 8]] or ev["truth"] == [("demo/Calc.java", 8)]
    for m, r in ev["metrics"].items():
        assert r["rank_best"] <= r["rank_average"] <= r["rank_worst"]
    rows = summarise_localization([ev], ["ochiai", "dstar"])
    assert rows[0]["bugs"] == 1 and 0 <= rows[0]["mean_exam"] <= 1

def test_no_fl_baseline_uses_stack_trace_frames(tmp_path, pipe):
    b = make_checkout(tmp_path, "b")
    report, summary = pipe.repair(b, "template", use_fl=False, rank_patches=False, top_k=3)
    assert summary["generated"] > 0          # candidates come from stack-trace frames, not from the spectrum

def test_study_end_to_end_with_failures_isolated(tmp_path, pipe):
    from aisr.core.exceptions import RepositoryError
    from aisr.experiments.study import run_study
    def fake_checkout(pid, bug, dest):
        if bug == 99:
            raise RepositoryError("checkout failed")
        return make_checkout(tmp_path / f"c{bug}", "b"), make_checkout(tmp_path / f"c{bug}", "f", fixed=True)
    out = run_study(pipe, "Demo", [1, 99], ["ochiai", "dstar"], tmp_path / "out", tmp_path / "wd",
                    repair_configs=["B", "A"], checkout_fn=fake_checkout)
    assert [f["bug"] for f in out["failures"]] == ["Demo-99"]            # one bad bug does not abort the study
    assert out["average"][0]["bugs"] == 1
    assert out["repair"][0]["config"] == "B" and out["repair"][0]["bugs_with_plausible"] == 1
    assert (Path(out["out_dir"]) / "localization_summary_worst.csv").exists()
    assert (Path(out["out_dir"]) / "repair_summary.csv").exists()

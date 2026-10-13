from pathlib import Path
import shutil
import pytest
from aisr.core.config import Config
from aisr.orchestrator import Pipeline
from aisr.repair.llm.static import StaticBackend
from fake_maven import FakeMaven

FIX = Path(__file__).parent.parent / "fixtures" / "demo-maven"

@pytest.fixture
def pipe(tmp_path):
    cfg = Config(workspace_root=tmp_path / "ws")
    return Pipeline(cfg, FakeMaven())

def test_localization_finds_buggy_region(pipe):
    lo = pipe.localize(FIX)
    assert [r.case.id for r in lo.baseline.failing] == ["demo.CalcTest#testZero"]
    top = lo.ranked[0]
    assert top.score == 1.0 and top.cls == "demo.Calc" and top.method == "isPositive"
    # the faulty line (8) is executed by every test, so it ranks below the zero-only lines: realistic SBFL behaviour
    lines = {s.line: s for s in lo.ranked}
    assert lines[8].rank > lines[6].rank and 8 in lines

def test_template_repair_end_to_end(pipe):
    report, summary = pipe.repair(FIX, "template", top_k=5)
    assert summary["generated"] > 0 and summary["plausible"] >= 1
    assert "return x > 0;" in report or "return x >= 1;" in report
    assert "| tpl-2-5-0 | syntax |" not in report        # `if (x != 0) {` must not die on brace balance
    assert "regression: passed" in report and "Rejected candidates" in report
    # original fixture untouched
    assert "return x >= 0;" in (FIX / "src/main/java/demo/Calc.java").read_text()

def test_llm_repair_rejects_bad_candidates_early(pipe):
    reply = ('[{"start_line": 8, "end_line": 8, "replacement": "        return (x > 0;", "explanation": "syntax broken"},'
             ' {"start_line": 8, "end_line": 8, "replacement": "        return x <= 0;", "explanation": "wrong: breaks testPos"},'
             ' {"start_line": 8, "end_line": 8, "replacement": "        return x > 0;", "explanation": "zero is not positive"},'
             ' {"start_line": 1, "end_line": 1, "replacement": "int evil;", "explanation": "outside method"}]')
    backend = StaticBackend([reply, "[]", "[]"])
    report, summary = pipe.repair(FIX, "llm", backend=backend, top_k=3)
    assert summary["best"].startswith("llm-") and summary["plausible"] == 1
    assert "return x > 0;" in report
    assert "syntax" in report and "failing_tests" in report      # rejection stages recorded
    prompt = backend.prompts[0]
    assert "demo.CalcTest#testZero" in prompt and "8:         return x >= 0;" in prompt

def test_no_failing_tests_is_a_clean_error(tmp_path):
    from aisr.core.exceptions import AisrError
    fixed = tmp_path / "fixed"; shutil.copytree(FIX, fixed)
    f = fixed / "src/main/java/demo/Calc.java"; f.write_text(f.read_text().replace("x >= 0", "x > 0"))
    with pytest.raises(AisrError, match="no failing test"):
        Pipeline(Config(workspace_root=tmp_path / "ws"), FakeMaven()).localize(fixed)

def test_cost_measurements_recorded(pipe):
    _, summary = pipe.repair(FIX, "template", top_k=3)
    assert set(summary["timing_s"]) == {"localization", "generation", "validation"}
    assert summary["validation_runs"] > 0

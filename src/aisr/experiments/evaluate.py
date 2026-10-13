"""Evaluation harness: RQ1 (fault-localization accuracy) and repair outcomes against developer fixes."""
from __future__ import annotations
import csv, json
from pathlib import Path
from ..orchestrator import Pipeline
from ..repair.candidates import Patch
from .groundtruth import ground_truth, patch_matches_fix
from .metrics import exam_score, mean_rank, rank_of_fault, top_n

def evaluate_localization(pipe: Pipeline, buggy: Path, fixed: Path, src_dir: str, modified: list[str],
                          metrics: list[str], max_tests: int | None = None) -> dict:
    """The coverage matrix never sees `modified` (the oracle): it is used only to score the result."""
    lo, ranked = pipe.localize_all(buggy, metrics, max_tests)
    truth = ground_truth(buggy, fixed, src_dir, modified)
    n = len(lo.matrix.executable) or len(lo.matrix.coverage and set().union(*lo.matrix.coverage.values()))
    out = {"n_executable": n, "n_failing": len(lo.matrix.failing), "n_tests": len(lo.matrix.outcomes),
           "truth": sorted(truth), "metrics": {}}
    for m, r in ranked.items():
        # statements in the ranking are file paths relative to the source root, like `truth`
        ranks = {t: rank_of_fault(r, truth, t) for t in ("best", "average", "worst")}
        out["metrics"][m] = {**{f"rank_{k}": v for k, v in ranks.items()},
                             "exam_average": exam_score(ranks["average"], n)}
    lo.ws.cleanup()
    return out

def summarise_localization(per_bug: list[dict], metrics: list[str], tie: str = "average") -> list[dict]:
    rows = []
    for m in metrics:
        ranks = [b["metrics"][m][f"rank_{tie}"] for b in per_bug if m in b.get("metrics", {})]
        exams = [b["metrics"][m]["exam_average"] for b in per_bug if m in b.get("metrics", {}) and b["metrics"][m]["exam_average"] is not None]
        rows.append({"metric": m, "bugs": len(ranks), "top1": top_n(ranks, 1), "top3": top_n(ranks, 3),
                     "top5": top_n(ranks, 5), "top10": top_n(ranks, 10), "mean_rank": mean_rank(ranks),
                     "mean_exam": sum(exams) / len(exams) if exams else float("nan"), "tie_rule": tie})
    return rows

def write_csv(rows: list[dict], path: Path) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def repair_outcome(summary: dict, buggy: Path, fixed: Path, src_dir: str) -> dict:
    """Plausible (passes all tests) is NOT correct. `matches_developer_fix` is a sufficient condition for correct;
    anything else among plausible patches needs manual review (listed in `needs_manual_review`)."""
    matches, manual = [], []
    for pd in summary.get("plausible_patches", []):
        p = Patch(**pd)
        orig = (Path(buggy) / p.file).read_text(errors="replace").splitlines()
        new = orig[: p.start_line - 1] + p.replacement.splitlines() + orig[p.end_line:]
        fx = Path(fixed) / p.file
        ok = fx.is_file() and patch_matches_fix("\n".join(new), fx.read_text(errors="replace"))
        (matches if ok else manual).append(p.id)
    ordered = [pd["id"] for pd in summary.get("plausible_patches", [])]
    return {"generated": summary["generated"], "plausible": summary["plausible"],
            "top1_matches_fix": bool(ordered) and ordered[0] in matches, "any_matches_fix": bool(matches),
            "matches_developer_fix": matches, "needs_manual_review": manual,
            "validation_runs": summary.get("validation_runs")}

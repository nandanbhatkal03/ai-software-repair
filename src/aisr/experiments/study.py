"""Batch study over Defects4J bugs: RQ1 localization metrics for several formulas + repair configurations."""
from __future__ import annotations
import time
from pathlib import Path
from typing import Callable
from ..core.exceptions import AisrError
from ..orchestrator import Pipeline
from ..repository.defects4j_checkout import checkout
from ..testing.defects4j import read_properties
from .baselines import CONFIGS
from .evaluate import evaluate_localization, repair_outcome, summarise_localization, write_csv
from .runner import ExperimentRecorder

CheckoutFn = Callable[[str, int, Path], tuple[Path, Path]]

def _modified(props: dict[str, str]) -> list[str]:
    return [c for c in props.get("d4j.classes.modified", "").replace(";", ",").split(",") if c.strip()]

def run_study(pipe: Pipeline, project_id: str, bug_ids: list[int], metrics: list[str], out_dir: Path, workdir: Path,
              max_tests: int | None = None, repair_configs: list[str] | None = None, backend=None,
              checkout_fn: CheckoutFn | None = None, top_k: int = 5) -> dict:
    checkout_fn = checkout_fn or (lambda p, b, d: checkout(p, b, d, pipe.runner))
    rec = ExperimentRecorder(Path(out_dir), f"{project_id}-study")
    per_bug, failures = [], []
    for bug in bug_ids:
        bid = f"{project_id}-{bug}"
        t0 = time.time()
        try:
            buggy, fixed = checkout_fn(project_id, bug, Path(workdir))
            props = read_properties(buggy); src = props.get("d4j.dir.src.classes", "src/main/java")
            row: dict = {"bug": bid, "localization": evaluate_localization(pipe, buggy, fixed, src, _modified(props), metrics, max_tests)}
            for cfg in (repair_configs or []):
                c = CONFIGS[cfg]
                if c["generator"] is None:
                    continue
                _, summ = pipe.repair(buggy, c["generator"], backend, c["fl"] or "ochiai", max_tests, top_k,
                                      use_fl=c["fl"] is not None, rank_patches=c["rank"])
                row.setdefault("repair", {})[cfg] = repair_outcome(summ, buggy, fixed, src)
            row["seconds"] = round(time.time() - t0, 1)
            per_bug.append(row); rec.save(bid, row)
        except AisrError as e:                       # one broken bug must not kill a multi-hour study
            failures.append({"bug": bid, "error": str(e)}); rec.save(bid, {"error": str(e)})
    loc = [b["localization"] for b in per_bug]
    summary = {tie: summarise_localization(loc, metrics, tie) for tie in ("best", "average", "worst")}
    for tie, rows in summary.items():
        write_csv(rows, rec.dir / f"localization_summary_{tie}.csv")
    if repair_configs:
        rows = []
        for cfg in repair_configs:
            r = [b["repair"][cfg] for b in per_bug if cfg in b.get("repair", {})]
            if r:
                rows.append({"config": cfg, "name": CONFIGS[cfg]["name"], "bugs": len(r),
                             "bugs_with_plausible": sum(1 for x in r if x["plausible"]),
                             "top1_matches_fix": sum(1 for x in r if x["top1_matches_fix"]),
                             "any_matches_fix": sum(1 for x in r if x["any_matches_fix"]),
                             "plausible_needing_manual_review": sum(len(x["needs_manual_review"]) for x in r)})
        write_csv(rows, rec.dir / "repair_summary.csv")
        summary["repair"] = rows
    summary["failures"] = failures; summary["out_dir"] = str(rec.dir)
    return summary

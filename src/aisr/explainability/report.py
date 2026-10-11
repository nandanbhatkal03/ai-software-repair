from __future__ import annotations
from pathlib import Path
from ..localization.aggregator import Suspicious
from ..ranking.ranker import RankedPatch
from ..validation.pipeline import ValidationResult
from .evidence import location_evidence, validation_evidence
from .explanation import explain

def render_report(project_name: str, failing_ids: list[str], ranked_locs: list[Suspicious],
                  ranked: list[RankedPatch], rejected: list[tuple[str, ValidationResult]],
                  project_dir: Path) -> str:
    L = [f"# Repair report: {project_name}", "", "## Failing tests", *[f"- `{t}`" for t in failing_ids], ""]
    L += ["## Suspicious locations", "", "| Rank | File | Class | Method | Line | Score |", "|---|---|---|---|---|---|"]
    L += [f"| {s.rank} | {s.file} | {s.cls} | {s.method} | {s.line} | {s.score:.2f} |" for s in ranked_locs[:10]]
    L.append("")
    if ranked_locs:
        L += ["**Why the top location:** " + location_evidence(ranked_locs[0], len(failing_ids)), ""]
    if not ranked:
        L += ["## Recommendation", "", "No candidate survived validation. Unresolved failing tests remain.", ""]
    for rp in ranked[:3]:
        orig = (project_dir / rp.patch.file).read_text(errors="replace")
        L += [f"## {'Recommended' if rp.rank == 1 else 'Alternative'} patch #{rp.rank}", "",
              explain(rp, orig, failing_ids), "", "```diff", rp.patch.diff(orig).rstrip(), "```", "",
              "Validation: " + "; ".join(validation_evidence(rp.validation.stages)), ""]
    if rejected:
        L += ["## Rejected candidates", "", "| Patch | Rejected at |", "|---|---|"]
        L += [f"| {pid} | {v.rejected_at} |" for pid, v in rejected]
    L += ["", "> Generated patches require human review; test suites cannot prove correctness."]
    return "\n".join(L)

from __future__ import annotations
from ..ranking.ranker import RankedPatch

def explain(rp: RankedPatch, original_text: str, failing_ids: list[str]) -> str:
    top = sorted(rp.contributions.items(), key=lambda kv: -kv[1])[:3]
    why = ", ".join(f"{k} ({v:+.2f})" for k, v in top)
    return (f"Patch {rp.patch.id} ({rp.patch.origin}) changes {rp.patch.changed_lines} line(s) in {rp.patch.file}. "
            f"It makes {', '.join(failing_ids) or 'the failing test'} pass and no previously-passing test fails. "
            f"Ranked #{rp.rank} (score {rp.score}); largest contributors: {why}. "
            f"Passing the existing tests does not prove the patch is semantically correct - review before merging.")

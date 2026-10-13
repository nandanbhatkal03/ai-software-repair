"""Records every run (config, model, benchmark, bug, patches, results) as JSON for reproducibility (FR-15)."""
from __future__ import annotations
import json, platform, time
from dataclasses import asdict, is_dataclass
from pathlib import Path

def resource_usage() -> dict:
    """Peak resident memory (MB) of this process and of all waited-for child processes (Maven/JVM/defects4j).
    ru_maxrss is a lifetime maximum (KiB on Linux), so read it per run in a fresh process for clean per-bug numbers."""
    import resource
    return {"peak_rss_mb_self": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
            "peak_rss_mb_children": round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 1)}

def _default(o):
    return asdict(o) if is_dataclass(o) else str(o)

class ExperimentRecorder:
    def __init__(self, root: Path, name: str):
        self.dir = Path(root) / "runs" / f"{name}-{time.strftime('%Y%m%d-%H%M%S')}"
        self.dir.mkdir(parents=True, exist_ok=True)

    def save(self, bug_id: str, record: dict) -> Path:
        record = {"bug": bug_id, "python": platform.python_version(), "timestamp": time.time(), **resource_usage(), **record}
        p = self.dir / f"{bug_id.replace('/', '_')}.json"
        p.write_text(json.dumps(record, indent=2, default=_default))
        return p

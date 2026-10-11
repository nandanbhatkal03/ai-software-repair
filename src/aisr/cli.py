from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from .core.config import Config
from .core.exceptions import AisrError
from .orchestrator import Pipeline
from .repository.manager import RepositoryManager

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="aisr", description="AI-driven software debugging and program repair")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("detect", help="detect build system and source/test dirs"); d.add_argument("project")
    b = sub.add_parser("baseline", help="run the baseline test suite"); b.add_argument("project")
    l = sub.add_parser("localize", help="rank suspicious statements"); l.add_argument("project")
    l.add_argument("--metric", default="ochiai", choices=["ochiai", "tarantula", "jaccard", "dstar"])
    l.add_argument("--top", type=int, default=10); l.add_argument("--max-tests", type=int)
    r = sub.add_parser("repair", help="localize, generate, validate, rank, explain"); r.add_argument("project")
    r.add_argument("--generator", choices=["template", "llm"], default="template")
    r.add_argument("--metric", default="ochiai"); r.add_argument("--max-tests", type=int)
    r.add_argument("--top-k", type=int, default=5); r.add_argument("--out", default="repair-report.md")
    a = ap.parse_args(argv)
    cfg = Config()
    try:
        if a.cmd == "detect":
            ws, info = RepositoryManager(cfg).import_project(a.project)
            print(json.dumps(info.__dict__, indent=2)); ws.cleanup()
        elif a.cmd == "baseline":
            ws, info = RepositoryManager(cfg).import_project(a.project)
            from .testing.runner import TestRunner
            res = TestRunner(cfg).run_suite(ws.work, info.build_system)
            print(json.dumps(res.stats())); [print("FAIL", r.case.id, r.message) for r in res.failing]
        elif a.cmd == "localize":
            lo = Pipeline(cfg).localize(a.project, a.metric, a.max_tests)
            print("Rank | File | Class | Method | Line | Score")
            for s in lo.ranked[: a.top]:
                print(f"{s.rank} | {s.file} | {s.cls} | {s.method} | {s.line} | {s.score:.2f}")
        elif a.cmd == "repair":
            backend = None
            if a.generator == "llm":
                from .repair.llm.ollama import OllamaBackend
                backend = OllamaBackend(cfg.model_name, cfg.ollama_url)
            report, summary = Pipeline(cfg).repair(a.project, a.generator, backend, a.metric, a.max_tests, a.top_k)
            Path(a.out).write_text(report); print(json.dumps(summary), "->", a.out)
    except AisrError as e:
        print(f"error: {e}", file=sys.stderr); return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())

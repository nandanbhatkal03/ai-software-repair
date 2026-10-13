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
    r.add_argument("--config", choices=["B", "C", "D"], help="experiment configuration (overrides --generator): "
                   "B=FL+template, C=LLM without FL, D=FL+context+LLM+validation+ranking")
    r.add_argument("--static-cmd", help="command printing one finding per line (e.g. a PMD wrapper); run before/after")
    r.add_argument("--pit", action="store_true", help="run PIT mutation testing on plausible patches (Maven only)")
    e = sub.add_parser("d4j-eval", help="batch study on Defects4J bugs (needs `defects4j` on PATH)")
    e.add_argument("--project", required=True); e.add_argument("--bugs", required=True, help="e.g. 1,3,5-8")
    e.add_argument("--metrics", default="ochiai,tarantula,jaccard,dstar"); e.add_argument("--max-tests", type=int)
    e.add_argument("--repair", default="", help="comma list of configs to run, e.g. B,D"); e.add_argument("--top-k", type=int, default=5)
    e.add_argument("--workdir", default="benchmarks/checkouts"); e.add_argument("--out", default="experiments")
    v = sub.add_parser("serve", help="start the web dashboard"); v.add_argument("--host", default="127.0.0.1"); v.add_argument("--port", type=int, default=8000)
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
            if not res.build_ok:
                print("error: build failed or no tests ran. Last output:\n" + res.raw_log.strip()[-500:], file=sys.stderr)
                return 2
        elif a.cmd == "localize":
            lo = Pipeline(cfg).localize(a.project, a.metric, a.max_tests)
            print("Rank | File | Class | Method | Line | Score")
            for s in lo.ranked[: a.top]:
                print(f"{s.rank} | {s.file} | {s.cls} | {s.method} | {s.line} | {s.score:.2f}")
        elif a.cmd == "repair":
            from .experiments.baselines import CONFIGS
            gen, use_fl, rank = a.generator, True, True
            if a.config:
                c = CONFIGS[a.config]; gen, use_fl, rank = c["generator"], c["fl"] is not None, c["rank"]
            backend = None
            if gen == "llm":
                from .repair.llm.ollama import OllamaBackend
                backend = OllamaBackend(cfg.model_name, cfg.ollama_url)
            import shlex
            report, summary = Pipeline(cfg).repair(a.project, gen, backend, a.metric, a.max_tests, a.top_k,
                                                   shlex.split(a.static_cmd) if a.static_cmd else None,
                                                   use_fl=use_fl, rank_patches=rank, run_mutation=a.pit)
            Path(a.out).write_text(report)
            print(json.dumps({k: v for k, v in summary.items() if k != "plausible_patches"}), "->", a.out)
        elif a.cmd == "d4j-eval":
            from .experiments.study import run_study
            from .repair.llm.ollama import OllamaBackend
            ids = []
            for part in a.bugs.split(","):
                lo_hi = part.split("-"); ids += list(range(int(lo_hi[0]), int(lo_hi[-1]) + 1))
            rc = [c for c in a.repair.split(",") if c]
            backend = OllamaBackend(cfg.model_name, cfg.ollama_url) if any(c in ("C", "D") for c in rc) else None
            out = run_study(Pipeline(cfg), a.project, ids, a.metrics.split(","), Path(a.out), Path(a.workdir),
                            a.max_tests, rc, backend, top_k=a.top_k)
            print(json.dumps(out, indent=2, default=str))
        elif a.cmd == "serve":
            import uvicorn
            from .api.app import create_app
            uvicorn.run(create_app(cfg), host=a.host, port=a.port)
    except AisrError as e:
        print(f"error: {e}", file=sys.stderr); return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())

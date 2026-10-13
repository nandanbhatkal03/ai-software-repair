"""Local web dashboard + REST API. Binds to 127.0.0.1 by default: it executes build/test commands on paths you give it,
so do not expose it to untrusted networks. Set AISR_ALLOWED_ROOT to restrict which directories may be analysed."""
from __future__ import annotations
import os, threading, time, uuid
from dataclasses import asdict
from pathlib import Path
from typing import Callable
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from ..core.config import Config
from ..core.exceptions import AisrError
from ..experiments.baselines import CONFIGS
from ..orchestrator import Pipeline

class RunRequest(BaseModel):
    project: str
    mode: str = Field("localize", pattern="^(localize|repair)$")
    metric: str = Field("ochiai", pattern="^(ochiai|tarantula|jaccard|dstar)$")
    config: str | None = Field(None, pattern="^[BCD]$")
    max_tests: int | None = Field(None, ge=1)
    top_k: int = Field(5, ge=1, le=50)

def create_app(cfg: Config | None = None, pipeline_factory: Callable[[], Pipeline] | None = None,
               run_inline: bool = False) -> FastAPI:
    cfg = cfg or Config()
    factory = pipeline_factory or (lambda: Pipeline(cfg))
    runs: dict[str, dict] = {}
    app = FastAPI(title="ai-software-repair", version="0.1.0")

    def execute(run_id: str, req: RunRequest) -> None:
        r = runs[run_id]; r["status"] = "running"
        try:
            pipe = factory()
            if req.mode == "localize":
                lo = pipe.localize(req.project, req.metric, req.max_tests)
                r["result"] = {"failing_tests": [t.case.id for t in lo.baseline.failing], "tests": len(lo.matrix.outcomes),
                               "ranking": [asdict(s) for s in lo.ranked[:50]]}
                lo.ws.cleanup()
            else:
                gen, use_fl, rank = "template", True, True
                backend = None
                if req.config:
                    c = CONFIGS[req.config]; gen, use_fl, rank = c["generator"], c["fl"] is not None, c["rank"]
                if gen == "llm":
                    from ..repair.llm.ollama import OllamaBackend
                    backend = OllamaBackend(cfg.model_name, cfg.ollama_url)
                report, summary = pipe.repair(req.project, gen, backend, req.metric, req.max_tests, req.top_k,
                                              use_fl=use_fl, rank_patches=rank)
                r["result"] = {"summary": {k: v for k, v in summary.items() if k != "work_dir"}, "report": report}
            r["status"] = "done"
        except AisrError as e:
            r["status"], r["error"] = "failed", str(e)
        except Exception as e:                                    # keep the server alive; surface the error to the UI
            r["status"], r["error"] = "failed", f"{type(e).__name__}: {e}"
        r["finished"] = time.time()

    @app.post("/api/runs", status_code=202)
    def create_run(req: RunRequest) -> dict:
        p = Path(req.project).expanduser().resolve()
        if not p.is_dir():
            raise HTTPException(400, f"not a directory: {req.project}")
        root = os.environ.get("AISR_ALLOWED_ROOT")
        if root and Path(root).resolve() not in (p, *p.parents):
            raise HTTPException(403, "project is outside AISR_ALLOWED_ROOT")
        req = req.model_copy(update={"project": str(p)})
        run_id = uuid.uuid4().hex[:8]
        runs[run_id] = {"id": run_id, "request": req.model_dump(), "status": "queued", "started": time.time()}
        if run_inline:
            execute(run_id, req)
        else:
            threading.Thread(target=execute, args=(run_id, req), daemon=True).start()
        return {"id": run_id}

    @app.get("/api/runs")
    def list_runs() -> list[dict]:
        return [{k: v for k, v in r.items() if k != "result"} for r in sorted(runs.values(), key=lambda r: -r["started"])]

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict:
        if run_id not in runs:
            raise HTTPException(404, "unknown run")
        return runs[run_id]

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _PAGE
    return app

_PAGE = """<!doctype html><meta charset=utf-8><title>ai-software-repair</title>
<style>body{font:15px system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#222}input,select,button{font:inherit;padding:.35rem}
table{border-collapse:collapse;width:100%;margin:.5rem 0}td,th{border:1px solid #ccc;padding:.25rem .5rem;text-align:left}
pre{background:#f6f6f6;padding:.75rem;overflow:auto}.f{color:#b00}.ok{color:#080}small{color:#666}</style>
<h1>ai-software-repair</h1><small>Localise faults, generate patches, validate with the project's own tests.</small>
<p><input id=p size=52 placeholder="/path/to/buggy/project"> <select id=m><option>localize<option>repair</select>
<select id=x><option>ochiai<option>tarantula<option>jaccard<option>dstar</select>
<select id=c><option value="">repair: template (default)<option value=B>B: FL + template<option value=C>C: LLM, no FL<option value=D>D: full pipeline</select>
<button onclick=go()>Run</button></p><div id=s></div><div id=o></div>
<script>
const $=i=>document.getElementById(i);let cur=null;
async function go(){const b={project:$('p').value,mode:$('m').value,metric:$('x').value,config:$('c').value||null};
 const r=await fetch('/api/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});
 if(!r.ok){$('s').innerHTML='<span class=f>'+(await r.json()).detail+'</span>';return}
 cur=(await r.json()).id;poll()}
async function poll(){if(!cur)return;const r=await (await fetch('/api/runs/'+cur)).json();
 $('s').innerHTML='Run '+r.id+': <b>'+r.status+'</b>'+(r.error?' <span class=f>'+esc(r.error)+'</span>':'');
 if(r.status==='done'){show(r.result);cur=null}else if(r.status==='failed'){cur=null}else setTimeout(poll,1500)}
function esc(t){return String(t).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
function show(res){let h='';if(res.ranking){h+='<p>Failing: '+res.failing_tests.map(esc).join(', ')+'</p><table><tr><th>Rank<th>File<th>Method<th>Line<th>Score</tr>'+
 res.ranking.slice(0,20).map(s=>'<tr><td>'+s.rank+'<td>'+esc(s.file)+'<td>'+esc(s.cls+'.'+s.method)+'<td>'+s.line+'<td>'+s.score.toFixed(2)).join('')+'</table>'}
 if(res.report){h+='<p>'+esc(JSON.stringify(res.summary))+'</p><pre>'+esc(res.report)+'</pre>'}$('o').innerHTML=h}
</script>"""

"""Candidate generation: template-based (Baseline B) and LLM-based (proposed), behind one interface."""
from __future__ import annotations
import json, re
from pathlib import Path
from ..context.builder import BugContext
from ..core.log import get_logger
from .candidates import Patch, dedupe
from .llm.base import ModelBackend
from .templates.operators import mutate_line

log = get_logger("repair")

class TemplateGenerator:
    """Mutation-style repair on the top-k suspicious lines. No AI involved; this is the research baseline."""
    def __init__(self, project: Path, top_k: int = 10, max_per_line: int = 12):
        self.project, self.top_k, self.max_per_line = Path(project), top_k, max_per_line

    def generate(self, ctx: BugContext, source_dirs: tuple[str, ...]) -> list[Patch]:
        out, originals = [], {}
        for loc in ctx.suspicious_locations[: self.top_k]:
            for d in source_dirs or (".",):
                rel = f"{d}/{loc['file']}"
                f = self.project / rel
                if not f.is_file():
                    continue
                text = f.read_text(errors="replace"); originals[rel] = text
                lines = text.splitlines()
                if not 1 <= loc["line"] <= len(lines):
                    break
                for k, (name, new) in enumerate(mutate_line(lines[loc["line"] - 1])[: self.max_per_line]):
                    out.append(Patch(f"tpl-{loc['rank']}-{loc['line']}-{k}", rel, loc["line"], loc["line"], new,
                                     f"template:{name}", f"mutate suspicious line (rank {loc['rank']}, score {loc['score']})"))
                break
        return dedupe(out, originals)

_PROMPT = """You are fixing a bug in a Java project. Fix ONLY the suspicious line(s). Do not change tests.

Failing test(s):
{tests}

Stack trace (innermost first):
{trace}

Suspicious location: {file}, line {line} (suspiciousness {score}).
Enclosing method (line-numbered):
{method}

Reply with ONLY a JSON list of up to {n} alternative fixes, each of the form:
{{"start_line": <int>, "end_line": <int>, "replacement": "<java code replacing those lines>", "explanation": "<one sentence>"}}
Lines must lie inside the method shown above."""

class LLMGenerator:
    """Constrained generation: the model sees only localized context and may only return line replacements."""
    def __init__(self, backend: ModelBackend, project: Path, top_k: int = 3, n_per_location: int = 3):
        self.backend, self.project, self.top_k, self.n = backend, Path(project), top_k, n_per_location

    def build_prompt(self, ctx: BugContext, loc: dict, src: dict) -> str:
        tests = "\n".join(f"- {t['test']}: {t['message']}" for t in ctx.failing_tests[:3]) or "(none)"
        trace = "\n".join(f"{f['class']}.{f['method']}({f['file']}:{f['line']})" for f in ctx.stack_trace[:8]) or "(none)"
        return _PROMPT.format(tests=tests, trace=trace, file=loc["file"], line=loc["line"], score=loc["score"],
                              method=src["method_source"], n=self.n)

    @staticmethod
    def parse(reply: str) -> list[dict]:
        m = re.search(r"\[.*\]", reply, re.S)           # tolerate prose / ``` fences around the JSON
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
        return [d for d in data if isinstance(d, dict) and {"start_line", "end_line", "replacement"} <= d.keys()]

    def generate(self, ctx: BugContext, source_dirs: tuple[str, ...]) -> list[Patch]:
        out, originals = [], {}
        by_file = {s["file"]: s for s in ctx.source_context}
        for loc in ctx.suspicious_locations[: self.top_k]:
            src = next((s for s in ctx.source_context if s["file"] == loc["file"] and s["method_start"] <= loc["line"] <= s["method_end"]), None)
            if not src:
                continue
            rel = str(Path(src["path"]).relative_to(self.project)) if str(src["path"]).startswith(str(self.project)) else src["path"]
            originals[rel] = Path(src["path"]).read_text(errors="replace")
            try:
                reply = self.backend.complete(self.build_prompt(ctx, loc, src))
            except Exception as e:                      # backend down => no candidates, not a crash
                log.warning("model call failed: %s", e); continue
            for i, d in enumerate(self.parse(reply)[: self.n]):
                try:
                    s, e = int(d["start_line"]), int(d["end_line"])
                except (TypeError, ValueError):
                    continue
                if not (src["method_start"] <= s <= e <= src["method_end"]):
                    continue                              # constrain edits to the localized method
                out.append(Patch(f"llm-{loc['rank']}-{loc['line']}-{i}", rel, s, e, str(d["replacement"]),
                                 f"llm:{self.backend.name}", str(d.get("explanation", ""))))
        return dedupe(out, originals)

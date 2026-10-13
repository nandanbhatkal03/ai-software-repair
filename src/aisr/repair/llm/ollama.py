"""Local model serving through Ollama's HTTP API (stdlib only)."""
from __future__ import annotations
import json, time, urllib.request
from ...core.exceptions import ModelBackendError

class OllamaBackend:
    def __init__(self, model: str, url: str = "http://localhost:11434", temperature: float = 0.2, timeout: int = 300):
        self.name, self.url, self.temperature, self.timeout = model, url.rstrip("/"), temperature, timeout
        self.stats = {"calls": 0, "seconds": 0.0, "prompt_tokens": 0, "output_tokens": 0}   # RQ5: cost of local models

    def complete(self, prompt: str) -> str:
        body = json.dumps({"model": self.name, "prompt": prompt, "stream": False,
                           "options": {"temperature": self.temperature, "seed": 42}}).encode()
        req = urllib.request.Request(f"{self.url}/api/generate", body, {"Content-Type": "application/json"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = json.load(r)
            self.stats["calls"] += 1; self.stats["seconds"] += time.time() - t0
            self.stats["prompt_tokens"] += int(data.get("prompt_eval_count", 0))
            self.stats["output_tokens"] += int(data.get("eval_count", 0))
            return data["response"]
        except Exception as e:
            raise ModelBackendError(f"Ollama call failed: {e}") from e

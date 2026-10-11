"""Local model serving through Ollama's HTTP API (stdlib only)."""
from __future__ import annotations
import json, urllib.request
from ...core.exceptions import ModelBackendError

class OllamaBackend:
    def __init__(self, model: str, url: str = "http://localhost:11434", temperature: float = 0.2, timeout: int = 300):
        self.name, self.url, self.temperature, self.timeout = model, url.rstrip("/"), temperature, timeout

    def complete(self, prompt: str) -> str:
        body = json.dumps({"model": self.name, "prompt": prompt, "stream": False,
                           "options": {"temperature": self.temperature, "seed": 42}}).encode()
        req = urllib.request.Request(f"{self.url}/api/generate", body, {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.load(r)["response"]
        except Exception as e:
            raise ModelBackendError(f"Ollama call failed: {e}") from e

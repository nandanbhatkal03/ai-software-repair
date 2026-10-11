class StaticBackend:
    """Deterministic fake model for tests/offline development."""
    def __init__(self, replies: list[str], name: str = "static"):
        self.name, self._replies, self.prompts = name, list(replies), []
    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._replies.pop(0) if self._replies else "[]"

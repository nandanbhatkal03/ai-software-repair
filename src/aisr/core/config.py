from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path

def _b(name: str, default: str) -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes")

@dataclass(frozen=True)
class Config:
    workspace_root: Path = field(default_factory=lambda: Path(os.environ.get("AISR_WORKSPACE_ROOT", "./workspaces")))
    test_timeout: int = field(default_factory=lambda: int(os.environ.get("AISR_TEST_TIMEOUT", "600")))
    use_docker: bool = field(default_factory=lambda: _b("AISR_USE_DOCKER", "0"))
    docker_image: str = field(default_factory=lambda: os.environ.get("AISR_DOCKER_IMAGE", "maven:3.9-eclipse-temurin-11"))
    docker_cpus: str = "2"
    docker_memory: str = "4g"
    jacoco_version: str = field(default_factory=lambda: os.environ.get("AISR_JACOCO_VERSION", "0.8.12"))
    model_backend: str = field(default_factory=lambda: os.environ.get("AISR_MODEL_BACKEND", "ollama"))
    ollama_url: str = field(default_factory=lambda: os.environ.get("AISR_OLLAMA_URL", "http://localhost:11434"))
    model_name: str = field(default_factory=lambda: os.environ.get("AISR_MODEL_NAME", "qwen2.5-coder:7b"))

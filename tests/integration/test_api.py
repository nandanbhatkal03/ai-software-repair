from pathlib import Path
from fastapi.testclient import TestClient
from aisr.api.app import create_app
from aisr.core.config import Config
from aisr.orchestrator import Pipeline
from fake_maven import FakeMaven

FIX = Path(__file__).parent.parent / "fixtures" / "demo-maven"

def client(tmp_path):
    cfg = Config(workspace_root=tmp_path / "ws")
    return TestClient(create_app(cfg, lambda: Pipeline(cfg, FakeMaven()), run_inline=True))

def test_localize_run(tmp_path):
    c = client(tmp_path)
    rid = c.post("/api/runs", json={"project": str(FIX), "mode": "localize"}).json()["id"]
    r = c.get(f"/api/runs/{rid}").json()
    assert r["status"] == "done" and r["result"]["failing_tests"] == ["demo.CalcTest#testZero"]
    assert r["result"]["ranking"][0]["method"] == "isPositive"
    assert any(x["id"] == rid for x in c.get("/api/runs").json())

def test_repair_run_returns_report(tmp_path):
    c = client(tmp_path)
    rid = c.post("/api/runs", json={"project": str(FIX), "mode": "repair", "config": "B"}).json()["id"]
    r = c.get(f"/api/runs/{rid}").json()
    assert r["status"] == "done" and r["result"]["summary"]["plausible"] >= 1 and "# Repair report" in r["result"]["report"]

def test_validation_and_errors(tmp_path):
    c = client(tmp_path)
    assert c.post("/api/runs", json={"project": "/definitely/not/here"}).status_code == 400
    assert c.post("/api/runs", json={"project": str(FIX), "metric": "bogus"}).status_code == 422
    assert c.get("/api/runs/nope").status_code == 404
    empty = tmp_path / "empty"; empty.mkdir()
    rid = c.post("/api/runs", json={"project": str(empty)}).json()["id"]
    r = c.get(f"/api/runs/{rid}").json()
    assert r["status"] == "failed" and "unsupported project" in r["error"]
    assert "<title>ai-software-repair</title>" in c.get("/").text

def test_allowed_root_enforced(tmp_path, monkeypatch):
    monkeypatch.setenv("AISR_ALLOWED_ROOT", str(tmp_path / "only-here"))
    assert client(tmp_path).post("/api/runs", json={"project": str(FIX)}).status_code == 403

# ai-software-repair

AI-driven software debugging and automated program repair using fault localization, contextual patch generation, and test-guided validation.

**Principle: AI proposes; software-engineering validation verifies.**

## Status

| Pipeline stage | Module | State |
|---|---|---|
| 1 Repository import / workspace isolation | `aisr.repository` | implemented, unit-tested |
| 2 Baseline test execution (Maven/Gradle, Surefire XML) | `aisr.testing` | implemented; tested with a fake Maven, **not yet run against real Maven** |
| 3-4 Static (method locator) / dynamic (per-test JaCoCo) analysis | `aisr.analysis` | implemented; JaCoCo XML parser unit-tested, **real JaCoCo run pending** |
| 5 Fault localization: Ochiai, Tarantula, Jaccard, DStar + roll-up | `aisr.localization` | implemented, formulas verified by hand-computed tests |
| 6 Context construction | `aisr.context` | implemented |
| 7 Patch generation: template baseline + LLM (Ollama) behind a backend interface | `aisr.repair` | implemented; LLM path tested with a scripted fake model only |
| 8 Staged validation (syntax → compile → failing tests → regression → static → mutation) | `aisr.validation` | syntax/compile/tests/regression implemented; static & PIT are hooks |
| 9 Ranking (transparent weighted baseline) | `aisr.ranking` | implemented |
| 10 Explainable report | `aisr.explainability` | implemented |
| Metrics (Top-N, EXAM, tie-aware rank) / experiment recorder | `aisr.experiments` | implemented |
| Defects4J adapter, FastAPI + React dashboard, PIT/PMD wiring | - | **not built yet** (see docs/CORRECTIONS.md, item 11) |

## Quick start

```bash
pip install -e '.[dev]'
pytest                       # 30 tests, no Java needed (uses a fake Maven runner)

# real project (needs JDK + Maven + network/cache for dependencies)
aisr detect   path/to/buggy-project
aisr baseline path/to/buggy-project
aisr localize path/to/buggy-project --metric ochiai --top 10
aisr repair   path/to/buggy-project --generator template      # Baseline B (no AI)
aisr repair   path/to/buggy-project --generator llm           # needs `ollama serve` + a pulled code model
```

Configuration is by environment variables (see `.env.example`). The core has **no third-party runtime dependencies**.

## Safety

Original sources are copied into a workspace whose `baseline/` snapshot is read-only; every candidate patch is applied to its own fresh copy. Set `AISR_USE_DOCKER=1` semantics via `DockerRunner` (no network, CPU/memory/PID limits) when running model-generated code.

## Layout

`src/aisr/<module>` as above, `tests/` (unit + integration with a Java fixture), `docs/CORRECTIONS.md` (what was changed vs. the project spec and why), `experiments/` (run records), `benchmarks/` (benchmark setup notes).

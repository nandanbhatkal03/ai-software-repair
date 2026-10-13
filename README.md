# ai-software-repair

AI-driven software debugging and automated program repair using fault localization, contextual patch generation, and test-guided validation.

**Principle: AI proposes; software-engineering validation verifies.**

## Status

| Area | Module | State |
|---|---|---|
| Repository import, workspace isolation | `aisr.repository` | implemented, tested |
| Test execution (Maven, Gradle, **Defects4J**) | `aisr.testing` | implemented; tested with fake `mvn`/`defects4j`, **not yet run against real ones** |
| Per-test coverage (JaCoCo, Cobertura) | `aisr.analysis` | parsers tested; real runs pending |
| Fault localization: Ochiai, Tarantula, Jaccard, DStar | `aisr.localization` | implemented, formulas hand-verified |
| Context, template + LLM (Ollama) patch generation | `aisr.context`, `aisr.repair` | implemented; LLM tested with a scripted model and a local HTTP stand-in, **not a real model** |
| Staged validation, ranking, explainable report | `aisr.validation/ranking/explainability` | implemented; PIT/static analysis are optional, untested against the real tools |
| Evaluation: metrics, ground truth, batch study, cost/memory | `aisr.experiments` | implemented; **no benchmark results exist yet** |
| CLI and local web dashboard / REST API | `aisr.cli`, `aisr.api` | implemented, API tested |
| Docker sandbox (`--network none`) | `DockerRunner` | command construction tested; never run against a live daemon |

See `docs/project/TRACEABILITY.md` for objectives -> deliverables and `docs/CORRECTIONS.md` for changes to the original spec.

## Quick start

```bash
pip install -e '.[dev]'
pytest                       # ~55 tests, no Java needed (fake Maven / fake Defects4J runners)

# real project (needs JDK + Maven + network/cache for dependencies)
aisr detect   path/to/buggy-project
aisr baseline path/to/buggy-project
aisr localize path/to/buggy-project --metric ochiai --top 10
aisr repair   path/to/buggy-project --generator template      # Baseline B (no AI)
aisr repair   path/to/buggy-project --config D                 # FL + context + LLM + validation + ranking (needs ollama)
aisr d4j-eval --project Lang --bugs 1,3-5 --repair B,D         # batch study on Defects4J (see docs/SETUP_UBUNTU.md)
aisr serve                                                     # dashboard at http://127.0.0.1:8000 (pip install -e '.[api]')
```

Configuration is by environment variables (see `.env.example`). The core has **no third-party runtime dependencies**.

## Safety

Original sources are copied into a workspace whose `baseline/` snapshot is read-only; every candidate patch is applied to its own fresh copy. Set `AISR_USE_DOCKER=1` semantics via `DockerRunner` (no network, CPU/memory/PID limits) when running model-generated code.

## Layout

`src/aisr/<module>` as above, `tests/` (unit + integration with a Java fixture), `docs/CORRECTIONS.md` (what was changed vs. the project spec and why), `experiments/` (run records), `benchmarks/` (benchmark setup notes).

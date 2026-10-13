# Objectives -> deliverables (honest status)

| Objective | Deliverable | Status |
|---|---|---|
| 1 Literature and problem analysis | spec sections 11-15 | **Yours to finish:** citations/DOIs/findings in the spec were not verified (see `CORRECTIONS.md` item 12) |
| 2 Architecture and design | `docs/requirements/SRS.md`, `docs/architecture/HLD.md`, `LLD.md`, `docs/experiments/EXPERIMENT_PROTOCOL.md` | written |
| 3 Prototype: import, run tests, coverage, suspiciousness, ranked list | `repository`, `testing`, `analysis`, `localization`, CLI `detect/baseline/localize` | implemented; unit/integration-tested with fake Maven/Defects4J; **real Maven/JaCoCo/Defects4J runs still to be done on your machine** |
| 4 AI-assisted patch generation | `context`, `repair` (template + Ollama LLM) | implemented; LLM path tested with a scripted model and a local HTTP stand-in for Ollama, **not with a real model** |
| 5 Validation and ranking | `validation` (syntax, compile, failing tests, regression, static hook, PIT), `ranking`, `explainability` | implemented; static analysis needs a command you provide (`--static-cmd`); PIT is Maven-only and untested against real PIT |
| 6 Evaluation and contribution | `experiments` (metrics, ground truth, study runner, CSV/JSON), `aisr d4j-eval` | harness implemented; **no benchmark results exist yet** - they must be produced by running it |

| RQ | Ready? |
|---|---|
| RQ1 | yes, run `d4j-eval --metrics ...` |
| RQ2 | partly: configs B, C, D runnable; context ablation not wired |
| RQ3 | yes, needs manual labelling of plausible patches |
| RQ4 | yes (D vs unranked) |
| RQ5 | yes, time/tokens/memory recorded; GPU metrics not collected |

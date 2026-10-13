# Software Requirements Specification (SRS)

## 1. Purpose and scope
`ai-software-repair` localises faults in Java projects, proposes candidate patches (rule-based or locally hosted LLM),
validates every candidate against the project's own tests, ranks the survivors and explains the recommendation.
Principle: **AI proposes; software-engineering validation verifies.** Initial scope: Java, Maven/Gradle projects and
Defects4J checkouts. Out of scope: automatic merging of patches, proprietary model APIs, non-Java languages.

## 2. Functional requirements
| ID | Requirement | Module | Verified by |
|---|---|---|---|
| FR-1 | Import a local path or git URL into an isolated workspace; original is never modified | `repository` | `test_workspace_protects_original` |
| FR-2 | Detect build system (Maven, Gradle, Defects4J) and source/test dirs | `repository.detector` | `test_detector`, `test_detected_as_defects4j` |
| FR-3 | Run the baseline test suite and parse per-test results | `testing` | parser tests, fake-Maven/Defects4J integration |
| FR-4 | Collect a per-test statement coverage matrix (JaCoCo / Cobertura) | `analysis.coverage` | `test_jacoco`, `test_cobertura` |
| FR-5 | Compute suspiciousness with Ochiai, Tarantula, Jaccard, DStar; rank statements; roll up to method/class/file | `localization` | formula tests with hand-computed values |
| FR-6 | Build structured bug context (failing tests, stack frames, suspicious locations, enclosing method source) | `context` | integration tests |
| FR-7 | Generate candidate patches: rule-based templates and LLM (Ollama) restricted to line edits inside the localised method | `repair` | `test_template_operators`, LLM reply parsing, scripted-model test |
| FR-8 | Validate candidates in stages with early rejection: syntax, compile, failing tests, regression, optional static analysis and PIT mutation | `validation` | pipeline integration tests |
| FR-9 | Rank plausible patches by a transparent weighted score | `ranking` | `test_scoring_is_transparent` |
| FR-10 | Produce a human-readable report with diffs, evidence and rejected candidates | `explainability` | integration tests |
| FR-11 | Evaluate localization (Top-N, mean rank, EXAM with explicit tie rules) and repair outcomes vs developer fixes | `experiments` | `test_study_end_to_end...` |
| FR-12 | Provide CLI and a local web dashboard/REST API | `cli`, `api` | `test_api.py` |
| FR-13 | Record every experiment run (config, results, timing, memory) as JSON/CSV | `experiments.runner/study` | study test |
| FR-14 | Sandbox model-generated code in a no-network container | `testing.runner.DockerRunner` | command construction test only (see limitations) |

## 3. Non-functional requirements
- **Reproducibility:** deterministic localization; model temperature/seed fixed (seed 42); every run recorded.
- **Safety:** candidates are applied only to throw-away copies; baseline snapshot is read-only; Docker option has `--network none`, CPU/memory/PID limits.
- **Openness:** standard-library-only core; open-source tools only (JaCoCo, PIT, Ollama, Defects4J).
- **Fault isolation:** one failing bug/candidate never aborts a batch study.
- **Cost transparency (RQ5):** per-stage wall time, validation test runs, LLM calls/tokens, peak memory are recorded.

## 4. Constraints and assumptions
Defects4J 3.0.1 needs Java 11, Perl, Git, SVN. Test suites are imperfect oracles: a patch that passes all tests is
*plausible*, not necessarily *correct*. LLM output is non-deterministic across hardware/model versions.

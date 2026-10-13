# Low-Level Design

## Data structures
- `TestResult(case, outcome, message, stack_trace)`, `SuiteResult(results, build_ok)` - `testing/results.py`
- `CoverageReport(covered, executable, methods)` and `ExecutionMatrix(coverage[test]->lines, outcomes)` - `analysis/coverage`
- `Spectrum(ef, ep, nf, np)` per statement; `Suspicious(rank, file, cls, method, line, score)` - `localization`
- `BugContext` (failing tests, stack frames, suspicious locations, method source) - `context/builder.py`
- `Patch(id, file, start_line, end_line, replacement, origin, rationale)` - `repair/candidates.py`
- `ValidationResult(stages, rejected_at, still_failing, regressions, static_delta, mutation_score)` - `validation/pipeline.py`
- `RankedPatch(rank, patch, validation, score, contributions)` - `ranking/ranker.py`

## Algorithms
**Suspiciousness** (ef/ep = failing/passing tests executing the statement; F/P = total failing/passing):
Tarantula = (ef/F)/((ef/F)+(ep/P)); Ochiai = ef/sqrt(F(ef+ep)); Jaccard = ef/(F+ep); DStar = ef^2/(ep+F-ef).
Scores are normalised to [0,1] per metric; competition ranking (ties share the best rank); roll-up = max score.

**Rank of fault under ties** (`experiments/metrics.py`): best = first rank of the tied group, worst = last, average = middle.
Report at least *worst* or *average*; never silently *best*.

**Ground truth** (`experiments/groundtruth.py`): lines removed/changed between buggy and developer-fixed file; for a pure
insertion both neighbouring buggy lines are accepted. Whitespace-only changes ignored.

**Validation** (`validation/pipeline.py`): (1) bracket balance of the replacement equals that of the replaced lines;
(2) compile + test-compile on a fresh copy; (3) originally failing tests pass; (4) full suite: no test that passed on the
buggy baseline fails; (5) optional static-finding delta; (6) optional PIT mutation score. First failure rejects.

**Ranking** (`ranking/scoring.py`): score = 0.30 fl_score + 0.25 regression_clean + 0.10 static_improvement +
0.25 patch_size(1/(1+changed lines)) + 0.10 mutation_score + 0.00 llm_origin. Weights are configuration, not truth: tune
on a held-out bug set, not on the evaluation set. The feature contributions are printed in the report.

**LLM contract**: prompt contains failing tests, innermost stack frames, the line-numbered enclosing method; reply must be a
JSON list of `{start_line,end_line,replacement,explanation}`; anything outside the method or unparsable is dropped.

## Error handling
Domain errors derive from `AisrError`; the CLI prints `error: ...` (exit 2), the API reports `failed` runs, and the study runner
records the failure and continues. A baseline with no failing test or a failed build aborts early with a clear message.

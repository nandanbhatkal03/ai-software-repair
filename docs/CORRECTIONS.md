# Corrections and decisions relative to `ai_software_repair_project_master.md`

Found while implementing. "Fixed" = already reflected in the code; "Open" = needs your decision or more work.

## Technical errors

1. **§10.5 suspiciousness formula is wrong/vague.** The conceptual formula (failing coverage / normalised total coverage) matches no standard metric. Implemented exactly (ef/ep = failing/passing tests executing the statement, F/P = total failing/passing tests):
   - Tarantula = (ef/F) / ((ef/F) + (ep/P))
   - Ochiai = ef / sqrt(F · (ef + ep))
   - Jaccard = ef / (F + ep)
   - DStar(*=2) = ef² / (ep + (F − ef)); unbounded when the denominator is 0, so a large finite value is used.
   Scores are normalised to [0,1] per metric. **Fixed.**
2. **§10.4/§20: JaCoCo does not give per-test coverage.** Its report is aggregated over a run, but SBFL needs a test × statement matrix. Implemented by running each test separately with the JaCoCo Maven goals (correct, slow). Faster options for later: a JUnit `RunListener` that dumps/reset JaCoCo per test, or GZoltar. A `--max-tests` option bounds cost. **Fixed (slow path); optimisation open.**
3. **§10.8 lists "complete test suite" and "regression testing" as separate stages.** They are the same run. Defined: *failing-test stage* = originally failing tests now pass; *regression stage* = full suite, no test that passed on the buggy baseline fails now. **Fixed.**
4. **§10.9 "number of tests passed" as a ranking feature is uninformative:** only patches that pass everything are ranked, so it is constant. Removed. "Code/semantic similarity" needs embeddings and is deferred to Phase-II (feature slot reserved). **Fixed / deferred.**
5. **§22 and §33 define the baselines inconsistently** (§22: Ochiai+rule, Tarantula+generation, AI-without-FL, AI+FL-without-ranking; §33: A-D). Unified to A-D plus the §34 ablations in `experiments/baselines.py`; Tarantula/other metrics are compared inside RQ1, not as separate repair baselines. **Fixed.**
6. **§33 Configuration C uses a "bug report"**, but Defects4J does not ship bug-report text. Use failing test + stack trace + file list without localisation. **Open (wording in your documents).**
7. **§23 metrics:** "Mean Average Rank" and "Mean suspiciousness rank" are duplicates, and **tie handling is unspecified** although SBFL scores tie constantly. Implemented best/worst/average tie rules (report *worst* or *average* in the paper, state which) plus Top-N and EXAM = rank / #executable statements. **Fixed.**
8. **§35 "restricted network access"** should be **no network** for validation containers (model inference happens outside the sandbox; dependencies pre-cached). Implemented as `--network none`. **Fixed.**

## Structure

9. **§28 layout would break:** `src/` as a package namespace is non-standard, `core/logging.py` shadows the stdlib `logging`, and `context/test_context.py` would be collected by pytest as a test file. Now `src/aisr/...`, `core/log.py`, `context/failing_test_context.py`. **Fixed.**
10. **§20 stack is larger than the research needs.** PostgreSQL, Redis, Grafana, Prometheus, Jenkins and Joern add operational work without helping any research question. The core is standard-library only, results are JSON files; add SQLite only if querying becomes necessary. **Recommendation.**

## Open risks

11. **Defects4J is not a Maven/Gradle benchmark.** Confirmed from its 3.0.1 sources: checkouts are built and tested through `defects4j compile|test|coverage`, and it needs **Java 11** (2.x needed Java 8) plus Perl/SVN. A `defects4j` backend is now implemented (`testing/defects4j.py`, `analysis/coverage/cobertura.py`, `repository/defects4j_checkout.py`) against the file formats read from its source (`failing_tests`, `all_tests`, Cobertura `coverage.xml`, `defects4j.build.properties`). It is tested with a fake `defects4j` command only, **not against a real installation**. **Fixed in code; needs a real run.**
14. **Oracle leakage in Defects4J coverage.** `defects4j coverage` instruments by default only the classes modified by the bug fix, i.e. it tells the localiser which class is faulty. The adapter always passes `-i` with `classes.relevant` (classes loaded by the triggering tests). Do not use `d4j.classes.modified` or the fixed version as an input to localization or prompting; they are used only to score results. **Fixed.**
15. **Spec says "Defects4J ... Python/Java"-level tooling but omits cost.** Per-test Defects4J coverage is slow (one instrument+run per test); use `--max-tests` and small projects first (see EXPERIMENT_PROTOCOL.md). **Documented.**
12. **Literature section not verified.** I did not check the citations, DOIs, venues or the specific findings attributed to each paper (item 12.2 also lacks authors). The 2026 entries (12.13, 12.15) especially need checking against IEEE Xplore before submission, and each "Major finding" claim should be confirmed against the paper itself.
13. **Novelty:** each component (SBFL, LLM repair, test validation, patch ranking, explanations) exists in prior work; the spec correctly says to claim only the integration and its measured effect. RQ2/RQ4 need Config C vs D and the ablations to support any claim.

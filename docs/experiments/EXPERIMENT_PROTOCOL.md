# Experiment protocol

## Research questions -> measurements -> commands
| RQ | Measured | How |
|---|---|---|
| RQ1 FL accuracy vs conventional SBFL | Top-1/3/5/10, mean rank, EXAM for Ochiai/Tarantula/Jaccard/DStar on the **same** coverage matrix; report tie rules best/average/worst | `aisr d4j-eval --project Lang --bugs 1,3-10 --metrics ochiai,tarantula,jaccard,dstar` -> `localization_summary_{best,average,worst}.csv` |
| RQ2 context + AI generation vs baselines | bugs with a plausible patch, patches identical to the developer fix, for configs B (FL+template), C (LLM, no FL), D (full) | `--repair B,C,D` -> `repair_summary.csv` |
| RQ3 validation reduces wrong recommendations | plausible vs correct: `needs_manual_review` patches must be labelled by humans (two reviewers, agreement reported) | `repair_outcome()` lists them per bug |
| RQ4 ranking | position of the first correct patch under D vs unranked (`rank_patches=False`) | per-bug JSON `repair.D` vs `repair.B/C` |
| RQ5 cost | stage wall time, validation test runs, LLM calls/tokens, peak RSS | `timing_s`, `llm_usage`, `peak_rss_mb_*` in each JSON |

Configurations: A = FL only, B = FL + rule-based repair, C = LLM without FL (candidate lines = project frames of the
failing stack traces), D = proposed. Ablations of D (no FL, no context, no ranking, no static, no regression) are listed in
`experiments/baselines.py`; **only no-FL and no-ranking are wired into the runner today.**

## Procedure
1. Install Defects4J (Java 11); verify `defects4j checkout` + `compile` + `test` on one bug by hand.
2. Freeze the bug list (e.g. one project first) and the model tag; record hardware.
3. Run `aisr d4j-eval ...`; keep `experiments/runs/*` (JSON per bug, CSV summaries).
4. Label `needs_manual_review` patches; compute correct-patch rate.
5. Repeat LLM configurations with several seeds/models if the budget allows; report variance.

## Threats to validity (state them in the thesis)
- **Oracle leakage:** Defects4J's default coverage instruments only fix-modified classes; this tool uses `-i classes.relevant`
  (classes loaded by triggering tests). Never feed `d4j.classes.modified` or the developer diff to the localiser or the LLM.
- **Ties:** SBFL scores tie; conclusions can flip between best/average/worst rules.
- **Ground-truth convention:** faulty lines are derived from the developer diff; omission faults use both neighbours.
- **Plausible != correct:** passing tests is necessary, not sufficient. Exact-match with the developer fix is a *sufficient*
  correctness signal only; other plausible patches need manual review.
- **Data contamination:** Defects4J and its fixes are public and likely in code-LLM training data; consider a held-out or newer benchmark.
- **Non-determinism / flaky tests:** LLM output varies by hardware and version; Defects4J requires Java 11 and timezone
  America/Los_Angeles (its CLI sets this; set `TZ` yourself if you run tests outside it).
- **Test sampling:** `--max-tests` truncates passing tests and changes spectra; report it.
- **Single-fault assumption:** SBFL ranking and the ground truth assume one fault location set; multi-fault bugs are out of scope.
- **Weight tuning:** ranking weights must not be tuned on the evaluation bugs.

## Runtime warning
Per-test coverage runs one `defects4j coverage -t Class::method` (instrument + run) per test. Large projects have thousands of
tests, so a single bug can take hours. Start with small projects (Cli, Csv, Codec, Gson), use `--max-tests`, and record the
setting. A per-test JUnit listener or GZoltar would remove this cost (future work).

# entity-resolution-gate: Evidence Notes (questionnaire v3.2, Part 3)

Companion to `entity-resolution-gate.md` (narrative form, replaces the earlier card-and-table version, kept as `entity-resolution-gate.oldform.md` and `entity-resolution-gate.oldform.evidence.md`). Repo: https://github.com/PCSchmidt/entity-resolution-gate. Examined 2026-10-27 in a scratch clone made from the read-only run clone and updated with `git pull` (HEAD `9e1b9a2`, 2026-10-24 13:10 -0400). Code, tests, scripts, results and protocol documents are identical between `5f17714` (the duplicate/null `rid` fix) and `9e1b9a2`; `git diff 5f17714 HEAD` touches only two documentation files in the repo root. Line numbers below refer to `src/` at `5f17714` and `9e1b9a2`.

Labels: **Confirmed** (seen in code, settings, tests, history) · **Ran it** (run this session; command and result recorded) · **Per the docs** · **My reading** · **Ask the author** · **Author says** (AUTHOR_CONTEXT). Claim levels: **L1** doc matches the committed result file; **L2** reproduced by re-running; **L3** recomputed independently. "Carried" means taken from the earlier evidence file for the same unchanged committed data and not re-checked here.

---

## E1. Fact sheet

| Fact | Value | Label |
| --- | --- | --- |
| Name, licence, version | `entity-resolution-gate` 0.3.0; MIT; public; 0 stars, 0 forks, 2 open Dependabot PRs | Confirmed (`gh api`, `pyproject.toml`) |
| Description (repo) | "Entity resolution with graph-gated fusion: blocking, scoring, and hard constraints no similarity score can override." | Confirmed |
| Kind | Python library plus a set of pre-registered studies; no model, app or service | Confirmed |
| Status | v0.3 portfolio prototype; tag and release v0.3.0 (2026-10-13) | Confirmed |
| Size | `src/` 420 lines (pipeline 219, evaluation 127, synth 70, init 4); tests 544 lines in 5 files; scripts 2,260 lines in 14 files; docs 14,324 words in 11 files; 66 tracked files; 22 tracked result JSON files | Ran it (`wc`, `git ls-files`) |
| Commits | 30 on `main`, 2026-10-09 16:53 to 2026-10-24 13:10 (-0400). Per day: 10-09 1, 10-10 1, 10-11 4, 10-12 18, 10-13 2, 10-14 1, 10-19 1, 10-24 2 | Ran it (`git log`) |
| Commit credits | 28 "Claude Sonnet 5.5", 1 "Claude Opus 5.5 (1M context)" (`da904dd`), 1 none (`ad87f4f`, "Remove run logs"). All authored as Chris Schmidt. No Copilot, Codex, Gemini or other credits. No agent instruction files tracked | Ran it |
| Tests | `pytest -q`: 45 passed, 0 failed, 0 skipped (8 s to 20 s). Per file 12 / 8 / 11 / 6 / 8. Nine Hypothesis property tests. Coverage 99% of 272 statements; misses `pipeline.py` 92, 146, 161 and `evaluation.py` 124 | Ran it |
| Lint and types | `ruff check .` clean. `ruff format --check .`: 8 files would be reformatted. `mypy src tests` clean (9 files). `mypy src tests scripts` in a venv without the study extra: 8 errors in 3 files | Ran it |
| CI | One job, ubuntu-latest, Python 3.12: install `.[dev]`, `mypy src tests`, `pytest -q`; on push and pull request. Latest runs green (including `5f17714` and `9e1b9a2`). No ruff, no scripts type-check, no benchmark or quality gate; `main` not protected | Confirmed; Ran it (`gh run list`, `gh api`) |
| Clean-copy run | Fresh `uv venv` (Python 3.12.13) and `uv pip install -e ".[dev]"` succeeded; demo, benchmark and tests ran (demo with `PYTHONIOENCODING=utf-8`). Demo output redirected under Windows' default code page crashes with `UnicodeEncodeError` (earlier session) | Ran it |
| Needs | No paid service, key or GPU. Real-data studies need the USAspending public data service and a manual UK Companies House snapshot (5.7M rows) | Confirmed |
| Deployed, users | Not deployed; no evidence of any user | Confirmed; Ask the author |
| Related repos | README names Hard Power Intelligence and Grey-Resolve | Per the docs |

---

## E2. Reading and running log

**Read:** questionnaire v3.2 (all parts), AUTHOR_CONTEXT, the Grey-Resolve reference narrative and the heading structure of the other reference narratives, the earlier map and evidence files for this repo, the README (in full), `pipeline.py` and `synth.py` (in full), the bootstrap function in `evaluation.py`, the tests used for spot-checks, `Dockerfile`, `ci.yml`, `pyproject.toml`, `.gitignore`, `RESULTS.md`, `RESULTS_SAMPLE.md`, `RESULTS_GATE.md` and `RESULTS_SPLIT.md` (in full), the first half of `PROTOCOL_SAMPLE.md`, the top of `RESULTS_REAL.md`, selected lines of `run_gate.py`, and git history with trailers.
**Not read in full:** the other protocols, `RESULTS_BLOCKING.md`, the other study scripts, and the two documents added in `9e1b9a2` (a separate write-up, not an input).
**Commands run (scratch clone, `PYTHONDONTWRITEBYTECODE=1`):**
1. `git clone` of the run clone, then `git pull` (brought `9e1b9a2`).
2. `uv venv --python 3.12`, `uv pip install -e ".[dev]"` (success); `pytest -q -p no:cacheprovider`: 45 passed; with `pytest-cov`: 99%.
3. `ruff check`, `ruff format --check`, `mypy src tests`, `mypy src tests scripts`.
4. `examples/demo.py` (table matches README; audit order differs, see E14); `scripts/benchmark.py` (all twelve numbers match README to the digit; seconds 0.5, 0.3, 7.3, 11.2 on this machine against README 0.3, 0.2, 4.4, 6.7).
5. Probe script (E4), stress script (E4), cap script (CL-09), JSON recomputation (E3).
6. `gh api` (repo, branch protection, security settings), `gh run list`.
7. Secret scan (E11).
**Nothing external ran** except read-only GitHub queries and the package install. No data download, no paid call. The read-only run clone was not touched. Final state of the scratch clone: no changes to tracked files (only ignored caches and the scratch venv). Probe, stress, cap and chart scripts and their outputs live outside the repo and are not published.

---

## E3. Claims check

| ID | Claim (where) | Evidence | Level | Verdict |
| --- | --- | --- | --- | --- |
| CL-01 | "43 tests" (README, three places) | 45 collected and passed | L2 | Partly (stale) |
| CL-02 | `mypy src tests scripts  # strict, clean` (README) | 8 errors without the study extra; CI checks `src tests` only | L2 | Contradicted |
| CL-03 | Tests row says "ruff" | `ruff check` clean | L2 | Supported |
| CL-04 | Synthetic table, 12 numbers | all reproduce | L2 | Supported |
| CL-05 | 0 tax-ID violations in every synthetic run | benchmark column 0 | L2 | Supported |
| CL-06 | Property test of the guarantee passes | passes; plus 120-table stress run, 0 violations | L2 | Supported |
| CL-07 | "39,369 records in 6.7 s, single thread" | 11.2 to 11.3 s here (7.1 s and 8.8 s in the earlier session) | L2 | Partly (machine-dependent) |
| CL-08 | Precision capped near 0.86 by trap twins with no ID | carried: 187 false-merge pairs at 1,000 companies, 179 involve a trap entity | L3 (carried) | Supported |
| CL-09 | "Quality falls at 20k: partly generator, partly scaling cost, not separated" | Cap 200: P/R/F1 0.770/0.842/0.804, 11.3 s, 336 skipped lists, 1,233,412 candidates. Cap off (`max_block_size=10**9`): 0.741/0.974/0.842, 133.3 s, 14,866,635 candidates. The recall loss is the cap | L3 | Supported (mechanism now separated) |
| CL-10 | "Largest rows pessimistic in a way unrelated to the algorithm" (README Limitations) | The recall loss is the cap, which is part of the algorithm | L3 | Partly |
| CL-11 | Two development flaws found by the benchmark (cut-off 0.82 gives precision 0.61; single-token keys give recall 0.005) | the code that produced these no longer exists | n/a | Not checkable |
| CL-12 | US: pipeline 0.911 vs tuned fuzzy 0.885, +0.026 [0.019, 0.034] | `heldout_results.json`: P1 point 0.025997, interval 0.019207 to 0.033481 | L1 (re-read) | Supported |
| CL-13 | Pipeline minus Splink one-comparison +0.018 [0.012, 0.025] | `posthoc.json`: 0.017857 [0.011580, 0.024837] | L1 | Supported |
| CL-14 | Pairwise gap +0.070 | 0.06995, interval 0.0337 to 0.1052 | L1 | Supported |
| CL-15 | Extra blocking keys: findable share +4 to 8 points at up to 1.7x; F1 moves at most 0.004 | carried | L1 (carried) | Supported |
| CL-16 | Token-sort-only worse by 0.018 | carried: 0.8929 vs 0.9109 | L1 (carried) | Supported |
| CL-17 | 17% of true pairs are renames no matcher finds | `posthoc.json`: 1,450 of 8,493 = 0.1707 | L1, L3 | Supported |
| CL-18 | UK: full gate 0.928 vs 0.901 without ID, +0.027 [0.025, 0.029] | `contrasts["q=0.5"]`: G1 0.026736 [0.024772, 0.028778]; P_full 0.9277 | L1 (re-read) | Supported |
| CL-19 | Improved all 30 held-out slices (min +0.016, max +0.037, median +0.026) | recomputed from `per_slice_b3_f1`: 30 of 30; min 0.016300, max 0.036938, median 0.026054 | L3 | Supported |
| CL-20 | 0 rule-breaking clusters vs 49 without the veto; "49 to 77" | `violations_by_q` at q=0.5: P_addr 49, P_name 77, fuzzy 67, exact 60 (re-read); P_match 48 carried. README range 49 to 77; `RESULTS_GATE.md` says 48 to 77 | L1 | Partly (off by one in README) |
| CL-21 | Supervised Splink within 0.5 points, with 29 rule-breaking clusters | carried: 0.9227 vs 0.9277; 29 clusters; 1,349 false-merge pairs | L1 (carried) | Supported |
| CL-22 | Gain almost entirely same-ID evidence (+0.026); veto alone +0.0007 | `contrasts["q=0.5"]`: G3b 0.026058; G3a 0.000748 | L1 (re-read) | Supported |
| CL-23 | No-merge reference 0.903 (83% of companies have one name) | 23,280 / 28,278 = 0.82325 recall, F1 0.90306 (recomputed); the 83% figure is from the docs | L3; docs | Supported |
| CL-24 | Effect scales with ID visibility: +0.007 at 25%, +0.027 at 50% | G1 at q=0.25: 0.007354; q=0.5: 0.026736 (re-read); q=1.0 +0.099 carried | L1 | Supported |
| CL-25 | Split ablation: +0.0001 at tuned cut-off; 6 rule-breaking clusters without; +0.20 at 0.80 | `split_activity` at 0.5: 6 split components covering 22 of 26,596 records (re-read); other numbers carried | L1 | Supported |
| CL-26 | Tuned fuzzy 0.003 below no-merge on UK data | `ref_fuzzy_minus_no_merge`: -0.00317, interval -0.0038 to -0.0026 (re-read) | L1 | Supported |
| CL-27 | Plans written before results | By commit times: sample plan 07:49, results 09:07 (78 min); UK plan 09:37, results 10:17 (40 min); split plan and runner `8f334c4` 16:33, results `c651f50` 16:37 (4 min); all 2026-10-12, -0400. Push times in the earlier evidence agree within seconds | L1 | Partly (order holds; untouched held-out data not provable) |
| CL-28 | "The held-out stage refuses to run twice" | `run_gate.py` checks `out_path.exists()` and exits (read, not executed) | reading | Supported (not run) |
| CL-29 | "Everything runs locally on one machine, single-threaded" | Library yes; study runners use a process pool of 12 workers (earlier session) | reading | Partly |
| CL-30 | "Splink was compared only on the real-data study, with a fixed hand-set configuration" | The UK study adds a supervised Splink trained on development labels | L1 | Contradicted (stale) |
| CL-31 | "Every blocked pair, accepted pair, skipped block and split is recorded" | Events: candidates, block_skipped, edge_blocked, edge_accepted, component_split; ties and rejected pairs are not recorded | reading, ran it | Partly |
| CL-32 | README diagram: below-threshold pairs go to the audit log | no rejection event exists | reading | Contradicted (minor) |
| CL-33 | No keys; data downloaded on demand to git-ignored `data/` | `.gitignore` has `data/`; no data tracked; scan finds no keys | reading | Supported |
| CL-34 | Cut-off 0.93 and density rule chosen on seed 1 | single scaffold commit; no seed-1 evidence in history | n/a | Not checkable |
| CL-35 | Demo output "real output, lightly reformatted" | table and counts match; audit lines order differs | L2 | Supported (cosmetic) |
| CL-36 | README at-a-glance: "F1 0.91 at 2,000 records, 0.80 at 39,000" | 0.912 and 0.804 | L2 | Supported |
| CL-37 | Synthetic data "40% of entities without a tax ID" (README, `RESULTS.md`) | `synth.py`: 60% of entities get an ID and 80% of their records show it; trap twins always have one | L3 (code) | Partly (wording) |

**Tally:** 24 supported, 8 partly, 3 contradicted (CL-02, CL-30, CL-32), 2 not checkable (CL-11, CL-34). Where a claim mixes levels, the lowest applies. Real-data claims are L1 at most: the studies are one-shot and need downloads, so they could not be re-run (flagged NR).

---

## E4. Rule attacks and stress run

| # | Rule | Attack | Result (Ran it unless noted) |
| --- | --- | --- | --- |
| A1 | Unique non-null `rid` | duplicate `rid` (0, 0, 1) | `ValueError: rid must be unique; duplicated values include [0]` |
| A2 | same | null `rid` | `ValueError: rid must not contain nulls` |
| A3 | No cluster holds two IDs, on the previous code (`5f17714~1`) | duplicate `rid` with IDs A and B | old code returned one cluster holding both IDs with no error; the two new tests fail on the old copy and pass now (earlier session, carried) |
| A4 | Every record gets a group | empty frame | empty result, log holds `candidates` only |
| A5 | same | null name | `AttributeError: 'NoneType' object has no attribute 'lower'` (crash) |
| A6 | Veto | identical names, IDs 11 and 22 | `edge_blocked`; clusters [0, 1]; with `tax_veto=False`: [0, 0] |
| A7 | same | same ID in two formats (`11-1111111`, `111111111`) | treated as different; `edge_blocked` |
| A8 | same | ID with trailing space; empty-string ID | different ID; empty string treated as missing (earlier session) |
| A9 | ID shortlisting default | rename pair with equal ID `Z`, unrelated names | default: apart [0, 1]; `tax_blocking=True`: together [0, 0] |
| A10 | Settings | `split="bogus"` | `ValueError: unknown split mode` |
| A11 | Long input | 5,000-letter name | works (earlier session) |
| A12 | Missing column | no `tax_id` column | `KeyError` (earlier session) |
| A13 | Tie placement | demo record 1, Louvain seeds 0 to 9 | always {0,2},{1,3}; event carries no tie information (earlier session) |
| A14 | Cap | 201 records sharing ID `BIG`, `tax_blocking=True` | `block_skipped key='id:BIG' size=201` (earlier session) |

**Stress run.** 120 generated tables (40 or 80 companies, trap rate uniform 0 to 0.6, cut-off from {0.4, 0.6, 0.8, 0.93}, otherwise default settings): 0 tables with a cluster holding two non-null IDs; 110 of 120 had at least one `component_split` event. An earlier attempt with cut-offs down to 0.2 and up to 150 companies did not finish in reasonable time (giant components) and was stopped; nothing was concluded from it.

**Ablation counts.** `generate(1000, seed=2)` (2,021 records): default P/R/F1 0.858/0.973/0.912 with 0 violating clusters; `tax_veto=False, tax_match=False`: 0.766/0.990/0.863 with 47 violating clusters; `split="none"` with the veto on: 0.812/0.991/0.892 with 18 violating clusters.

**Determinism.** `generate(300, seed=5)` resolved twice, and once with the rows shuffled (seed 3): identical partitions each time (cluster numbers may differ; partitions compared). Earlier session: the demo with rows reversed gives the same grouping.

---

## E5. Code map

```text
src/entity_resolution_gate/
  pipeline.py    219 lines. normalise 21-22; block_keys 29-55; Config 58-70; AuditLog 73-78; candidate_pairs 81-101;
                 pair_score 104-115; contradicts 118-120; _consistent 123-124; _split 127-163; resolve 166-204
                 (validation 169-176); pairwise_prf 207-219
  evaluation.py  127 lines. union-find components, pair table, boot_f1 (69-82), B-cubed
  synth.py        70 lines. generate (24 stems x 7 kinds; 60% of entities with ID; 80% of records show it; trap twins)
  __init__.py      4 lines
tests/            test_blocking (12), test_er (8), test_evaluation (11), test_gate_flags (6), test_split_modes (8)
examples/demo.py  7 records, prints the table and the audit lines
scripts/          benchmark.py; run_real/run_blocking/run_sample/run_gate/run_split_ablation (dev | heldout);
                  fetch_* (3); sample_frame; enrich_profiles; build_real_dataset; build_gate_dataset; real_posthoc; sample_posthoc
docs/             PROTOCOL_{BLOCKING,GATE,REAL,SAMPLE,SPLIT}.md; RESULTS{,_BLOCKING,_GATE,_REAL,_SAMPLE,_SPLIT}.md
results/          blocking/, real/ (superseded pilots), sample/, gate/ (+3 Splink model exports), split/
.github/          workflows/ci.yml, dependabot.yml
```

Key behaviour (Confirmed): `resolve` validates the split mode and `rid`, builds record and tax dictionaries, adds shortlist pairs, vetoes and scores them, takes connected components and calls `_split` unless `split="none"`. `_split` returns the group if consistent and not chained; else, to depth 4, runs seeded Louvain (`seed=0`); else the fallback partitions by ID and attaches each ID-less node to the ID with the most edge weight (ties by dictionary order). `candidate_pairs` sorts pairs because Louvain depends on edge order. The library does no file or network input or output.

---

## E6. Model call sites

None in the library. The only learned component is Splink (Fellegi-Sunter, fitted by expectation-maximisation, or from labelled development pairs for the supervised variant), used inside the study runners (`run_real.py`, reused by `run_sample.py`, and `run_gate.py`), with random-sampling seed 0. Local, no cost, no tokens. Saved models: `results/gate/splink_sup_model_q{0.25,0.5,1.0}.json`. Which Splink major version produced the published numbers is not recorded (Ask the author).

---

## E7. Tests and CI

Counts as in E1. No `skip` or `xfail` anywhere; no test needs network, GPU, Docker or a paid service.

| File | Tests | Kind |
| --- | --- | --- |
| `test_blocking.py` | 12 | 4 property (base mode unchanged, modes only add keys, identical names share a key, token-sort never exceeds default), 8 unit |
| `test_er.py` | 8 | typo tolerance, contradiction rule, identical names with different IDs, 1 property (no cluster holds two IDs, 15 examples), low-cut-off splitting path, determinism and JSON log, quality floor, precision and recall edge cases |
| `test_evaluation.py` | 11 | 4 property (counts vs brute force, components vs a reference, bootstrap with unit weights, B-cubed vs definition), extremes |
| `test_gate_flags.py` | 6 | veto and match switches independent; rename needs ID shortlisting; missing address is no evidence; defaults |
| `test_split_modes.py` | 8 | duplicate and null `rid` rejected; bridge breaks the rule without the split; split restores it; unknown mode; sparse chain only under louvain |

**CI versus docs (Confirmed):** CI installs `.[dev]` and runs `mypy src tests` and `pytest -q` on Python 3.12 only. The README says "mypy --strict; ruff" and `mypy src tests scripts # strict, clean`, and lists the benchmark and demo for a reviewer; none of these runs in CI. `requires-python >=3.11`; only 3.12 is exercised.

**Three spot-checks (Confirmed by reading and running):**
1. `test_no_cluster_ever_holds_two_tax_ids`: generates tables at random seeds (0 to 10,000) and trap rates (0 to 0.6), resolves at cut-off 0.6, and asserts no null cluster ids and at most one non-null ID per group. A real behavioural check, with only 15 examples per run; `test_without_the_split...` shows the rule can be broken when the split is off.
2. `test_prf_counts_matches_brute_force`: compares the fast counting function with an enumerated implementation on random labels. Real.
3. `test_missing_address_is_not_evidence`: the first assertion is real; the second compares against `pair_score(a, c, cfg) * 0 + 0.7 * name_only`, so the multiplied-by-zero term does nothing and the check is weaker than its name. `test_defaults_enable_everything` asserts two of three switches (`tax_blocking` defaults off).

Who wrote the tests: commit credits show Claude on all test commits (Confirmed); whether the author edited them is Ask the author.

---

## E8. Plan-versus-results timing, bulk commits, credits

| Study | Plan commit | Settings frozen | Results | Gap (plan to results, commit times -0400) |
| --- | --- | --- | --- | --- |
| First pilot (superseded) | `2f4b29a` 10-11 16:55 | `e3d4f6b` 10-11 20:17 | `4643f96` 10-12 06:26 | 13.5 h |
| Blocking pilot (superseded) | `608ac6f` 10-12 07:19 | `6e0dd4f` 07:26 | `b67f791` 07:49 (same commit adds the sample protocol) | 30 min |
| Random-sample study | `b67f791` 07:49 | `99f22c4` 08:59 | `80c0dc2` 09:07 | 78 min |
| UK registry-ID study | `c3c814e` 09:37 | `b6a85f5` 10:03, `ebc4560` 10:07, `d365086` 10:14 | `2bb96a9` 10:17 | 40 min |
| Graph-splitting ablation | `8f334c4` 16:33 (protocol and runner together) | `e31cf06` 16:36 | `c651f50` 16:37 | 4 min |

The order plan, settings, results holds in every row. Nothing shows the held-out data were untouched before the plan push (Ask the author). Several deviations are logged after development and before held-out scoring (Per the docs). Protocols GATE, SAMPLE and SPLIT carry a "What I knew before writing this" section; REAL and BLOCKING carry "My expectation, written down so it can be wrong" only.
**Bulk commits:** `99f22c4` adds 7,440 lines by `numstat`, nearly all saved sweep and frozen files; `e3d4f6b` about 2,155; `6e0dd4f` about 1,228; `da904dd` about 1,316 (the earlier explainer). 18 of 30 commits fall on 2026-10-12, and the step-by-step history of that day is not recoverable (My reading).
**Credits:** see E1. Author says (AUTHOR_CONTEXT): Claude Code mostly, with Copilot, Codex and Prime-Agent across projects. This repository's evidence names only Claude models (Sonnet 5.5, Opus 5.5), not a tool or harness, so the explainer says "Claude models" and "AI coding agents".

---

## E9. Gates and approvals

No gate records, status files or approval logs exist. The only gate-like control is the held-out refusal (a file-exists check in each study runner), which is not a human approval. Approver identity: not applicable.

---

## E10. Environment

| Package | Minimum in `pyproject.toml` | Installed in the scratch venv (Ran it) |
| --- | --- | --- |
| Python | `>=3.11` | 3.12.13 |
| polars | `>=1.0` | 2.1.0 |
| duckdb | `>=1.0` | 2.0.0 |
| networkx | `>=3.2` | 3.7 |
| rapidfuzz | `>=3.6` | 3.14.6 |
| jellyfish | `>=1.0` | 1.3.0 |
| pyarrow, numpy | `>=15`, `>=1.26` | 26.0.0, 2.5.4 |
| pytest, hypothesis | `>=8`, `>=6.100` | 9.1.1, 6.170.12 |

No lock file; lower bounds only; no result file records package versions. A fresh install today resolves newer majors than the earlier session did (duckdb 2.0.0 here against 1.5.6 earlier). The practice-data benchmark reproduced to the digit and all 45 tests pass on these versions. The real-data runners were not run. The `pyproject.toml` comment says the study extra is "only for scripts/run_real.py", but `run_gate.py` and `run_split_ablation.py` also need it.

---

## E11. Security and privacy scan

- **Secrets, current files:** `git grep -nIE` for AWS keys, GitHub tokens, `sk-` keys, private-key headers and `api_key=`, `password=`, `secret=` patterns found only the repository's own evidence document describing an earlier scan (self-reference); no credential. **History:** `git log -p --all -G` for the token patterns: no hits; no `.env`, key or credential file names in any commit. No secret found, so no file or commit to report.
- **Repository secret test:** none (no `tests/test_no_secrets.py`).
- **Outside services:** the USAspending public data service (no key; three fetch scripts) and a manually downloaded Companies House snapshot. The library uses none.
- **GitHub settings (`gh api`):** public; Dependabot security updates, secret scanning, push protection and validity checks all disabled; Dependabot version updates configured (two PRs open since 10-13); `main` unprotected.
- **Data:** company data only; no personal data; raw downloads git-ignored; the Companies House licence was not found by the project (Per the docs), so the data are used for research only; the terms are Ask the author.
- **Untrusted input:** names are only compared as text; no `eval`, shell or deserialisation of input (My reading). A null name crashes (A5).

---

## E12. Shortcomings register

No Critical or High finding stands in the current code. The earlier High (a duplicate `rid` voiding the guarantee) was fixed in `5f17714`; re-run in A1, A2 and A3.

**SR-01 ID shortlisting is off by default (Medium).** `Config.tax_blocking = False` (`pipeline.py:68`); `run_gate.py` turns it on for the full-gate variants; A9. Impact: a user with IDs gets less than the headline UK result. Disclosed: partly (code comment; README summary silent). Options: A switch on by default (reproducible headline; costs a behaviour change, more candidate pairs, ID lists over 200 skipped; reversible by a flag); B keep it off but warn when IDs exist and are unused; C document only. Recommend A in the next version after re-running the practice benchmark. Effort small, payoff high. Verify: a default call on the A9 pair gives one cluster.

**SR-02 Ties are settled arbitrarily and not logged (Medium).** A13. Impact: an auditor cannot see a coin toss. Disclosed: the wrong-twin outcome yes, the missing log entry no. Options: A log near-tied placements with margins; B also emit a "needs a person" list; C break ties by total link weight (changes behaviour; test first). Recommend A then B. Effort small to medium, payoff medium to high.

**SR-03 Weak input handling beyond `rid` (Medium).** A5, A7, A8, A12. Options: specific error messages and an opt-in ID clean-up; a separate validation function; document only. The clean-up must stay opt-in because it could equate different IDs. Effort small, payoff medium.

**SR-04 The key-list cap silently drops matches, including large ID lists (Medium).** CL-09; A14. Options: never cap ID lists; split oversized lists with a second key; document only. Recommend the first now. Effort small to medium, payoff medium.

**SR-05 Automatic checks, lock file and branch protection are weaker than the docs imply (Medium).** E7 table, E10. Options: add ruff, the scripts type-check with the study extra, a lock file, a benchmark step asserting minimum F1 and zero violations, and branch protection; or only correct the README. Effort small, payoff high. Verify: a deliberate regression turns CI red.

**SR-06 The best UK result is an upper bound that the README does not stress (Medium).** `run_gate.py` makes the answer-key ID visible with probability q, so visible IDs are error-free by construction. Options: a new pre-registered study injecting 1% to 5% wrong IDs; a README caveat; nothing. Recommend the caveat now and the study later.

**SR-07 Out-of-date documentation (Medium).** E14. Options: fix the lines; add a script that compares README numbers with saved results.

**SR-08 No saved log and no human-review path (Medium).** `AuditLog` is an in-memory list; no file writing in `src/`. Options: write JSON lines with versions and settings; add the review list from SR-02.

Minor items:

| ID | Item | Severity |
| --- | --- | --- |
| SR-09 | Demo crashes when stdout is redirected on Windows with the default code page | Low |
| SR-10 | Test leftovers (multiply by zero; defaults test checks two of three switches) | Low |
| SR-11 | Study scripts (2,260 lines) have no tests | Medium |
| SR-12 | No lock file; versions not recorded in results | Medium |
| SR-13 | Companies House licence unconfirmed | Medium |
| SR-14 | GitHub secret scanning and push protection off | Low |
| SR-15 | Dependabot PRs open since 10-13 | Low |
| SR-16 | Tuned cut-offs sit at the 0.99 grid ceiling in the UK studies (disclosed) | Low |
| SR-17 | Previous names carry no address, understating address evidence (disclosed) | Low |
| SR-18 | The tidier does not strip UK suffixes ("limited", "plc") (disclosed) | Low |

---

## E13. Math and method detail

**Name measures.** Jaro: `(m/|s1| + m/|s2| + (m - t)/m) / 3`. Jaro-Winkler adds `l * p * (1 - J)` with `p = 0.1` and common prefix `l` up to 4. Token-sort ratio sorts tokens, then takes the normalised Indel similarity `1 - indel/(|a| + |b|)`. Worked (Ran it): tidied "aegis falcon defense" against "aegis falcon defence": Jaro-Winkler 0.98, token-sort 0.95. Address ratio "120 main st" against "120 main street": 0.8462. With both addresses, the pair score is `0.7 * name + 0.3 * addr`: with name 0.98 that is 0.9400 (the explainer's "about 0.94", matching the README demo's logged 0.9398); for two records whose tidied names are identical it is `0.7 * 1 + 0.3 * 0.846 = 0.9538` (probe output).
**Pair score rule.** Same non-empty ID: 1.0. Name: `max(JW, token-sort)`. Either address empty: name only. Otherwise `0.7 * name + 0.3 * addr`, with `addr` halved if both postcodes exist and differ. Link at `>= 0.93`.
**Modularity and Louvain.** Newman modularity `Q = sum_c [L_c/m - (S_c/(2m))^2]`; Louvain (Blondel et al. 2008) greedily moves nodes and aggregates communities; a heuristic that depends on order (hence `seed=0` and sorted edges).
**Shortlist cost.** Each record yields up to `2 * C(min(tokens, 4), 2)` keys; with the 200 cap the candidate count is bounded by about `1,200 * N`. Observed: 1,233,412 candidates at 39,369 records with the cap, 14,866,635 with the cap off.
**Metrics.** Pairwise `P = TP / predicted pairs`, `R = TP / true pairs`, `F1 = 2PR/(P+R)`. B-cubed per record `P_r = |C(r) ∩ E(r)| / |C(r)|`, `R_r = |C(r) ∩ E(r)| / |E(r)|`, then averaged. Demo hand check: pairwise 2/3, 2/4, F1 0.571; B-cubed P = 6/7 = 0.857, R = 0.810, F1 0.833 (matches the earlier program output). No-merge baseline: `P = 1`, `R = entities / records`: US held-out 1,527 / 4,542 = 0.3362, F1 0.5032; UK 23,280 / 28,278 = 0.8233, F1 0.9031 (equals the saved no-merge row).
**Bootstrap.** Resamples slices (UK) or entities (US) with replacement, 2,000 draws; `boot_f1` weights within-entity pairs by `w[e]` and cross-entity pairs by `w[a]*w[b]`, a weighted approximation without re-clustering. Toy example in the explainer: gains 0.016, 0.022, 0.026, 0.031, 0.037, 2,000 resamples, seed 0: mean 0.0264, middle 95% 0.0204 to 0.0328 (Ran it).
**Rename recall.** If each record shows the ID independently with probability `q`, a two-record rename pair is recovered with probability `q^2`: 0.0625, 0.25, 1.0 against measured 0.0664, 0.2583, 1.0 (carried).
**References (general knowledge, not in the repository; My reading):** Jaro 1989; Winkler 1990; Fellegi and Sunter 1969; Newman 2006; Blondel et al. 2008; Efron 1979; Amigo et al. 2009 (B-cubed).

---

## E14. Discrepancies between docs and code

| # | Docs say | Code or run shows |
| --- | --- | --- |
| 1 | README: 43 tests (three places) | 45 |
| 2 | README Verify: `mypy src tests scripts # strict, clean` | 8 errors in a venv without the study extra; CI runs `src tests` only |
| 3 | README flow diagram: below-threshold pairs go to the audit log | no rejection events |
| 4 | README: violations "49 to 77" without the veto | 48 (`P_match`) to 77 |
| 5 | README: "single-threaded" | library yes; study runners use a process pool |
| 6 | README Limitations: Splink "with a fixed hand-set configuration" | the UK study adds a supervised Splink |
| 7 | README Limitations: large rows "unrelated to the algorithm" | the recall loss is the key-list cap |
| 8 | `pyproject.toml` comment: study extra "only for scripts/run_real.py" | three runners need it |
| 9 | README demo audit lines: (2,3) then (0,3) | the run prints (0,3) then (2,3) (README says "lightly reformatted") |
| 10 | README speed 6.7 s | 11.2 s here; 7.1 s and 8.8 s earlier (machine-dependent) |
| 11 | README at-a-glance UK result (+0.027) | needs `tax_blocking=True`, off by default; the row does not say so |
| 12 | `test_defaults_enable_everything` | checks two of three switches |
| 13 | `test_missing_address_is_not_evidence` | the second assertion has a multiply-by-zero term |
| 14 | README and `RESULTS.md`: "40% of entities without a tax ID" | generator: 60% of entities have one and 80% of their records show it |
| 15 | README: "Guarantee: no cluster contains two different non-null tax IDs" | holds with `tax_veto=True` and `split != "none"` on well-formed input; the ablation modes void it by design (tests confirm) |
| 16 | README documentation map | the repo also carries a separate explainer and evidence file added in `9e1b9a2`, not listed there |

---

## E15. Production readiness detail

| Trait | Rating | Evidence |
| --- | --- | --- |
| Clean start (documented, versions recorded) | Partly | quickstart worked in a fresh venv; minimum versions only; Windows redirect crash (SR-09) |
| Checks block bad changes | Partly | CI runs types and 45 tests, green; no quality gate, no ruff, no branch protection |
| Quality measured against goal and baseline | Yes | held-out studies with no-merge, exact, tuned fuzzy and Splink baselines; negative results; the goal is a research one |
| Safe when things go wrong | Partly | pure function, re-runs safe, cap bounds cost, `rid` check; a null name crashes; no timeouts or retries in the library |
| Human review or stop | No | no review queue or confirmation |
| Versioned settings | Partly | `Config` in git; tuned cut-offs in committed `frozen.json`; Splink models saved; package versions unrecorded |
| Logs for diagnosis | Partly | in-memory `AuditLog` only; scripts `print`; no timing or quality telemetry |
| Data and secrets | Partly | no secrets; raw data git-ignored; GitHub secret scanning off; licence unconfirmed |

Placement: **Works locally.** Deployable is not reached: no hosted or packaged service (the Dockerfile only runs tests), CI does not guard quality, installs are not locked, logs are not persisted. Gap list: packaging (wheel config exists, no release on a package index), hosting and health check (missing), sign-in (not needed for a library), monitoring (missing), backups (not applicable), rollback (git tag only), model and prompt versioning (not applicable; lock the libraries), cost limits (cap only), security review (missing), runbook (missing), legal (Companies House licence). Showcase judgment: possible but low priority; no model, weakest fit to the applied-LLM family, closest to ML/AI engineer with MLOps.

---

## E16. Review dispositions

The review of the previous version (25 findings) was applied in the earlier rewrite, and this narrative rewrite carries those corrections (genuine-tie wording, the cap explanation, B-cubed baselines, "weighted approximation" for the bootstrap, Splink version unknown, no "AI mistake" claims without history). Not done in this run: the independent plain-language reader pass and the accuracy review (questionnaire passes 3 and 4); they remain to be run on the new text.

---

## E17. Completeness and backlog register

| Promised or implied (source) | Status | Evidence |
| --- | --- | --- |
| Normalise names | Done and tested | `pipeline.py:21-22`; `test_er.py` |
| Block keys, four modes | Done and tested | `block_keys`; `test_blocking.py` |
| Candidate pairs via DuckDB; skip and log keys over 200 | Done; the skip log line is untested | coverage misses line 92; used at 39k records |
| Hard veto | Done and tested | `contradicts`; flag tests |
| Score (0.7 name, 0.3 address; same ID 1.0) | Done and tested (one weak assertion) | `pair_score` |
| ID shortlisting switch | Done and tested; off by default | `test_equal_ids_are_not_even_proposed...` |
| Graph gate: components, density, Louvain, fallback | Done and tested | `_split`; property test; `test_split_modes.py` |
| Split modes louvain, tax_only, none | Done and tested | `test_split_modes.py` |
| Audit log of every blocked pair, accepted pair, skipped block and split | Partly: memory only; ties and rejections not logged | A13 |
| Synthetic generator with trap twins; benchmark | Done | `synth.py`; `benchmark.py` |
| Three real-data studies (sample, UK ID, split) | Built; results committed; not re-run here | CL-12 to CL-26 |
| Embedding or BM25 blocking, pgvector, embedding feature; executive and geography features; Leiden; 100k+ run with a speed curve; real tax IDs | Planned only (README "Known gaps") | README |
| Parent-subsidiary and other hard rules | Planned only | README Limitations |

No stubs, no TODO or FIXME, no skipped tests, no empty folders (Confirmed by search).

**Backlog.** Finish: log ties and rejected pairs; save the log. Fix: README numbers (tests, mypy, "40%", "unrelated to the algorithm", the Splink limitation), null-name and ID-format handling, the `pyproject.toml` extra comment, the weak test assertions. Improve: a CI quality gate with ruff, the scripts type-check and a minimum-F1 benchmark step; a lock file and versions in result files; never cap ID lists; ID shortlisting as the default or a warning. Add: a wrong-ID injection study; real tax IDs; a 100k scale run; a second hard rule. **Order and milestone:** milestone 1 = Fix plus the CI gate and the ID default or warning (exit test: a deliberate regression turns CI red, and a default call on the A9 pair groups the rename); milestone 2 = saved log with tie entries; milestone 3 = wrong-ID study. **Judgment:** polish and freeze after milestone 1; the author's view of "finished" is Ask the author.

---

## Image sources

All five images are rendered PNGs made with a plotting script kept outside the repo, from numbers in this file: the parts and demo diagrams are drawn from `pipeline.py` and the demo output; the learned-versus-rules diagram follows E6; the sample-results chart uses `results/sample/heldout_results.json` (F1 0.840, 0.885, 0.893, 0.911 with the ranges in CL-12); the UK chart uses `results/gate/heldout_results.json` at q = 0.5 (0.903, 0.901, 0.902, 0.927, 0.928, 0.923) and the rule-breaking counts 0, 49, 0, 48, 0, 29 from `violations_by_q` and the Splink row. The chart axes start at 0.78 and 0.89 and say so in their labels. Each image was viewed after rendering to check for clipped text.

---

## Revision log (v1 draft to current)

The previous text is kept as `entity-resolution-gate.v1draft.md`. All ten fixes in `entity-resolution-gate.readercheck.md` were applied. Word count by plain `wc -w`: v1 7,433; current about 6,800 (target 7,000; cap 8,000).

| Fix | What changed |
| --- | --- |
| 1. Numbers and caveats in the opening | Opening now gives: zero rule-breaking groups; names-only 0.911, +0.026 over tuned fuzzy; UK 0.928, +0.027 over ID-ignored, against a link-nothing 0.903; then the three caveats (UK IDs simulated and always correct; ID shortlisting off by default; Splink lightly tuned). F1 scale given in the same paragraph. |
| 2. Demo figure and paragraph | Demo figure now precedes the paragraph; paragraph shortened to the story (two same-ID records link, forbidden pair, ID-less record 1 cannot be decided). |
| 3. Methods split | One chapter "How it decides" (tidy, shortlist, veto, score, graph check) and one "How to read the scores" (precision, recall, F1, B-cubed, baseline, held-out, range, formula box). |
| 4. Louvain | Described as cutting a tangled group along natural seams; "heuristic", "dense compared with chance" and the arbitrary-tie aside removed from the determinism passage and the methods. The tie is mentioned only in the demo (record 1 scores the same against all three) and, once, in the shortcomings (log does not record ties; see A13, CL-31). |
| 5. Precision, recall, F1 | Defined with a toy example (10 true pairs, 8 linked, 6 right: 0.75, 0.60, 0.67) and the demo (2/3, 2/4, 0.57) before results; results use B-cubed only, with a toy B-cubed example; pairwise figures dropped from the body. |
| 6. Results trimmed | Practice-data paragraph cut to three numbers; sample results table removed (chart carries the numbers); UK dose-response, tuned-fuzzy-below-baseline, token-sort variant and shortlist-experiment details removed; shortlist-limit experiment (336 skipped key lists, recall 0.84 to 0.97, 133 s versus 11 s) moved to shortcomings. |
| 7. ID shortlisting | Defined once in the opening and again in "How it decides" with a toy rename example (Acme Holdings to Zephyr Systems); stated off by default in the opening, results and shortcomings. |
| 8. Folds and cuts | "Where the project came from" folded into the opening; "Where to look in the code" removed; Testing reduced to bad inputs, stress run, plan-first and held-out-once, plus weak tests in one paragraph; real-use checklist shortened. |
| 9. Recruiter section | Rewritten for a recruiter: 30-second and two-minute summaries, plain role-fit table, what it does not show, four likely questions with sound answers, two cautions; the ten candidate-voice answers and five tough questions removed; "MLOps" removed; "forward-deployed" explained. |
| 10. Formulaic summaries and shortcomings list | "In short" lines dropped where they only repeated (three chapters) and kept as one sentence elsewhere; the seven numbered shortcomings are now three themes (headline reach and shortlist limit; input handling and silent drops; documentation lag). |

Other wording changes: "guarantee" and "gain" replaced by statements of what was counted ("no group held two different IDs in every run with the rule on") and "improvement of about"; UK result labelled a best case; conditions on the rule stated where it is stated. "Where the logbook lacks ties and rejected pairs" is stated in the shortcomings, and the parts diagram now says the logbook records vetoed pairs, accepted links and skipped keys, kept in memory only.

Images regenerated with a script kept outside the repo and outside this folder: `entity-resolution-gate-gate-results.png` (title now says the IDs are simulated and error-free; labels shortened; caption says axis starts at 0.89; values unchanged: 0.903, 0.901, 0.902, 0.927, 0.928, 0.923 and violations 0, 49, 0, 48, 0, 29) and `entity-resolution-gate-parts.png` (logbook box reworded as above). The demo, sample-results and learned-versus-rules images are unchanged because their numbers and labels did not change. Each regenerated image was viewed after rendering to check for clipped text.

Not re-verified in this revision: the real-data numbers were carried over from v1 and the committed result files; no study was re-run.

# entity-resolution-gate: Evidence Notes (questionnaire v2.4, Part 3)

Companion to `entity-resolution-gate_MASTER_EXPLAINER.md`. Repo: https://github.com/PCSchmidt/entity-resolution-gate, a fresh clone of the repository, main at `5f17714` (2026-10-24). Written 2026-10-24 by Claude Code (Sonnet 5.5). All line numbers refer to `5f17714`. Probe scripts live in a temporary scratch folder outside the repository (`v2_probe.py`, `v2_probe2.py`, `v2_claims.py`, `v2_oldprobe.py`, `v2_trap.py`, `audit_cap.py`, `audit_taxblock.py`, outputs `v2_*_out.txt`, diagrams in `v2mmd\`).

Labels: **Confirmed** (seen in code, settings, tests, history) · **Ran it** (run this session) · **Per the docs** · **My reading** · **Ask the author** · **Author says** (stated in `AUTHOR_CONTEXT.md`). Claim levels: **L1** doc matches the committed result file; **L2** reproduced by re-running; **L3** independently recomputed.

---

## E1. Fact sheet (full)

| Fact | Value | Label |
| --- | --- | --- |
| Name, URL, licence | `entity-resolution-gate` v0.3.0 (package `entity_resolution_gate`); public; MIT; created 2026-10-09T20:54Z; 0 stars, 0 forks; 2 open issues = 2 Dependabot PRs; topics data-quality, deduplication, duckdb, entity-resolution, polars, python, record-linkage | Confirmed (`gh api`, `pyproject.toml:6-7`, `LICENSE`) |
| Description | "Entity resolution with graph-gated fusion: blocking, scoring, and hard constraints no similarity score can override." | Confirmed |
| Kind, status | Library plus pre-registered study set; v0.3.0 tag and release (release published 2026-10-13T11:17Z; tag on `c651f50`); no commits between 10-14 and 10-19 (old explainer) and 10-24 (fix) | Confirmed |
| Language, size | Python only. `src/` 420 lines (pipeline 219, evaluation 127, synth 70, `__init__` 4); tests 544 lines (5 files); scripts 2,260 lines (14 files); docs 761 lines (11 files); README 25,275 bytes; 65 tracked files incl. the old explainer; 22 tracked result JSONs | Ran it (`wc`, `git ls-files`) |
| Tests | `pytest -q`: **45 passed**, 0 failed, 0 skipped, 4.4 to 8.0 s. Per file: test_blocking 12, test_er 8, test_evaluation 11, test_gate_flags 6, test_split_modes 8 (7 functions, one parametrised x2). 9 Hypothesis `@given` tests (blocking 4, er 1, evaluation 4). Coverage 99% of 272 statements; misses `pipeline.py:92`, `pipeline.py:146`, `evaluation.py:124` (the earlier run also missed `pipeline.py:161`, so property-test coverage varies by run) | Ran it |
| Lint, types | `ruff check .` clean. `ruff format --check .`: 9 files would be reformatted (`README.md`, the old explainer, `examples/demo.py`, `scripts/build_gate_dataset.py`, `scripts/enrich_profiles.py`, `scripts/run_split_ablation.py`, `src/.../pipeline.py`, `src/.../synth.py`, `tests/test_split_modes.py`). `mypy src tests` clean (9 files). `mypy src tests scripts`: 1 error (`scripts/run_split_ablation.py:137`, list[float] assigned to float) with the study extra; **8 errors in 3 files** in a venv without it | Ran it |
| Commits | 29 on `main`: 2026-10-09 16:53 to 2026-10-24 08:15 (-0400). 18 on 2026-10-12 (in -0400). 28 carry `Co-Authored-By: Claude`: 27 "Claude Sonnet 5.5", 1 "Claude Opus 5.5 (1M context)" (`da904dd`, the old explainer). One has no credit (`ad87f4f` "Remove run logs"). All authored "Chris Schmidt". 1 tag | Ran it (`git log`) |
| Branches, PRs | `main` plus 2 Dependabot branches; PR #1 (checkout 4 to 7) and #2 (setup-python 5 to 7) open since 2026-10-13; branch `main` not protected | Confirmed (`gh`) |
| Entry points | Library: `resolve`, `generate`, `pairwise_prf`, `Config`, `AuditLog` (`__init__.py`). `examples/demo.py`. `scripts/benchmark.py`. Studies: `run_real.py`, `run_blocking.py`, `run_sample.py`, `run_gate.py`, `run_split_ablation.py` (each `dev` or `heldout`), `real_posthoc.py`, `sample_posthoc.py`; data: `fetch_usaspending.py`, `fetch_recipient_frame.py`, `sample_frame.py`, `enrich_profiles.py`, `build_real_dataset.py`, `build_gate_dataset.py`. No CLI entry in `pyproject.toml` | Confirmed |
| Clean-copy run | Existing `.venv` reused this session (Python 3.12.13). Earlier run (2026-10-18, `v1.1\...map.md`) did `uv venv` and `uv pip install -e ".[dev]"` from scratch and succeeded. Demo with redirected output on Windows: `UnicodeEncodeError: 'charmap' codec ... position 15-86` (exit 1); with `PYTHONIOENCODING=utf-8` it prints the README table | Ran it |
| Needs | No paid service, key or GPU. Real-data studies: live USAspending API (no key) and a manual UK Companies House snapshot (5.7M rows) | Confirmed |
| CI | `.github/workflows/ci.yml`: on push and pull_request; ubuntu-latest; Python 3.12; `pip install -e ".[dev]"`; `mypy src tests`; `pytest -q`. Last 8 runs success incl. `5f17714` (2026-10-24T12:15:56Z). Dependabot monthly, pip and Actions | Confirmed; Ran it (`gh run list`) |
| Docker | `Dockerfile`: python:3.12-slim, copies `pyproject.toml README.md src tests scripts`, `pip install -e ".[dev]"`, `CMD pytest -q`. Not built this session (brief did not allow) | Confirmed |
| Deployed, users | No deployment, no live demo, no users evidenced | Confirmed; Ask the author |
| Related repos | README: Hard Power Intelligence, Grey-Resolve; author context: "evaluator-gated roadmap studies" family (grouping agreed by the author) | Per the docs; Author says |
| Headline claims | 35 numbered in E3 | Confirmed |
| Completeness | See E17 | Confirmed |

---

## E2. Reading and running log

**Read in full:** questionnaire v2.4; `AUTHOR_CONTEXT.md`; `README.md`; all of `src/`; `examples/demo.py`; `.github/` (both files); `Dockerfile`; `pyproject.toml`; `.gitignore`; tests `test_er.py`, `test_gate_flags.py`, `test_split_modes.py`, and `test_blocking.py` and `test_evaluation.py` to about line 145; `docs/RESULTS.md`, `RESULTS_GATE.md`, `RESULTS_SPLIT.md`, `RESULTS_SAMPLE.md`; `docs/PROTOCOL_GATE.md` (first 60 lines and Deviation 4), `PROTOCOL_SAMPLE.md` Deviations, `PROTOCOL_SPLIT.md` header; git log with trailers, stats, and file-add history; prior work: `v1.1\entity-resolution-gate.map.md`, the first 400 lines of the v1.0-based draft, the whole review `v1.1\entity-resolution-gate.review.md`.
**Read selectively:** study scripts (guards, line ranges cited in E5), `build_gate_dataset.py:130-152`. **Not read in full:** `PROTOCOL_REAL.md`, `PROTOCOL_BLOCKING.md`, `RESULTS_REAL.md`, `RESULTS_BLOCKING.md`, the other study scripts, the old technical explainer (glanced at its existence only).
**Commands run (all with `PYTHONDONTWRITEBYTECODE=1`; results cached in scratchpad or git-ignored folders):**
1. `.venv/Scripts/python.exe -m pytest -q` : 45 passed, 8.00 s. With `--cov=entity_resolution_gate --cov-report=term-missing -p no:cacheprovider`: 99%, 4.42 s (writes git-ignored `.coverage`).
2. `ruff check . --no-cache`; `ruff format --check . --no-cache --output-format concise`; `mypy src tests --cache-dir <scratch>`; `mypy src tests scripts` (full env) and in the scratch venv `devonly` (no study extra): 1 error and 8 errors.
3. `examples/demo.py` (with and without `PYTHONIOENCODING`); `scripts/benchmark.py` (output in `v2_bench_out.txt`: rows match README; seconds 0.6/0.2/4.6/7.1).
4. `v2_probe.py` (demo trace, scores, modularity, rule attacks), `v2_probe2.py` (string scores, shortlist counts, hand metrics, ID-list cap), `v2_oldprobe.py` run against a `git archive` copy of `5f17714~1` under the scratchpad, plus the two new tests against that copy; `audit_taxblock.py`, `audit_cap.py` (cap versus no cap), `v2_trap.py`, `v2_claims.py` (reads the three `heldout_results.json` and `posthoc.json`), per-slice recomputation.
5. `gh api repos/...`, `gh run list`, `gh pr list`, `gh release list`, push events (`/events`, about 90 days), `security_and_analysis`, `branches/main`.
6. Secret scan: `git grep -nIE` for AWS, GitHub, `sk-`, private-key and `api_key=` patterns over tracked files; `git log -p --all -G` for the same over history; file names matching `.env|secret|credential|key` across history. No hits.
7. `npx -y @mermaid-js/mermaid-cli` (12.0.0, cached) on all six diagrams in the Explainer: all rendered.
**Anything external that ran:** `gh` (GitHub API, read-only); `npx` mermaid-cli from a local cache. No downloads of data, no paid API. No pushes or writes in the clone other than git-ignored caches (`.coverage`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `.hypothesis`; `__pycache__` suppressed).
**Final `git status --short` in the clone:** empty (no changes to tracked files; only ignored caches). Confirmed at the end of this run.

---

## E3. Claims check

Levels: L1 doc matches committed result file; L2 reproduced by re-running; L3 recomputed independently. "NR" = cannot be re-run here (needs downloads or one-shot).

| ID | Claim (where) | Evidence | Level | Verdict |
| --- | --- | --- | --- | --- |
| CL-01 | "43 tests" / `pytest -q # 43 passed` (README at-a-glance, quickstart, Verify) | Now 45 collected and passed; 43 was true at v0.3, +2 tests in `5f17714`; README not updated | L2 | Partly (stale) |
| CL-02 | `mypy src tests scripts  # strict, clean` (README Verify) | 1 error with study extra (`run_split_ablation.py:137`), 8 without; CI checks only `src tests`. Per the earlier review (not re-run now), the line was true when written in `83233ba` and the 1 remaining error arrived with `8f334c4` | L2 | Contradicted |
| CL-03 | Tests row says "ruff" | `ruff check` clean | L2 | Supported |
| CL-04 | Synthetic table: P/R/F1 for 4 rows (README, `RESULTS.md`) | All 12 numbers reproduce (`v2_bench_out.txt`) | L2 | Supported |
| CL-05 | 0 tax-ID violations in every synthetic run | Benchmark column all 0 | L2 | Supported |
| CL-06 | Property test of the guarantee passes | `test_no_cluster_ever_holds_two_tax_ids` passes (15 examples/run) | L2 | Supported |
| CL-07 | "39,369 records in 6.7 s, single thread" | 7.1 s and 8.8 s this session (machine-dependent) | L2 | Partly |
| CL-08 | Precision capped near 0.86 by trap twins with no ID | 187 false-merge pairs at 1,000 companies seed 2; 179 involve a trap entity | L3 | Supported |
| CL-09 | Quality falls at 20k: "partly generator, partly scaling cost, not separated" | Cap 200: P/R/F1 0.770/0.842/0.804 in 8.8 s, 336 skipped lists, 1,233,412 candidates; cap off: 0.741/0.974/0.842 in 102 s, 14,866,635 candidates. So recall loss = cap; precision loss = name collisions. The base-name space is 24 x 24 x 7 = 4,032 | L3 | Supported (mechanism now separated) |
| CL-10 | Limitations: largest rows "pessimistic in a way unrelated to the algorithm" (README) | The recall loss is the cap, which is part of the algorithm | L3 | Partly |
| CL-11 | Two design flaws found by the benchmark (threshold 0.82 gives precision 0.61; single-token keys give recall 0.005) (`RESULTS.md`) | Code that produced these no longer exists | n/a | Not checkable |
| CL-12 | US: pipeline 0.911 vs tuned fuzzy 0.885, +0.026 [0.019, 0.034] | `heldout_results.json`: 0.91089, 0.88489, 0.025997 [0.019207, 0.033481] | L1 | Supported |
| CL-13 | Splink one-comparison 0.893; pipeline minus Splink +0.018 [0.012, 0.025] | 0.89303; posthoc 0.017857 [0.011580, 0.024837] | L1 | Supported |
| CL-14 | Pairwise gap +0.070 | 0.06995 | L1 | Supported |
| CL-15 | Extra keys raise findable-pair share 4 to 8 points at 1.25 to 1.7x; F1 moves at most 0.004 | completeness diff 0.0437, 0.0547, 0.0763; candidate ratios 1.25, 1.35, 1.69; F1 diff 0.0020, 0.0029, 0.0037, CIs include 0 | L1 | Supported |
| CL-16 | Token-sort-only score worse (-0.018) | F1 0.8929 vs 0.9109 | L1 | Supported |
| CL-17 | 17% of true pairs are renames no string matcher finds | `posthoc.json`: 1,450 of 8,493 = 0.1707 (arithmetic checked) | L1, L3 | Supported |
| CL-18 | UK: full gate 0.928 vs 0.901 without ID, +0.027 [0.025, 0.029] | 0.92774 vs 0.90100; G1 0.026736 [0.024772, 0.028778] | L1 | Supported |
| CL-19 | Improved all 30 held-out slices (min +0.016, max +0.037, median +0.026) | Recomputed from `per_slice_b3_f1`: 30/30 improved; min 0.0163, max 0.0369, median 0.0261 | L3 | Supported |
| CL-20 | 0 rule-breaking clusters vs 49 without the veto; "49 to 77" (README gate section) | P_addr 49, P_name 77, fuzzy 67, exact 60, **P_match 48**, P_full 0, P_veto 0. Range is 48 to 77 (RESULTS_GATE says so; README says 49 to 77) | L1 | Partly (off by one in README range) |
| CL-21 | Supervised Splink within 0.5 points, with 29 rule-breaking clusters | 0.9227 vs 0.9277 (G4b 0.0050); 29 clusters; 1,349 false-merge pairs | L1 | Supported |
| CL-22 | Gain almost entirely from same-ID evidence (+0.026); veto alone +0.0007 | G3b 0.026058; G3a 0.000748 | L1 | Supported |
| CL-23 | No-merge reference 0.903 (83% of companies have one name) | 23,280 companies / 28,278 records = recall 0.82325, F1 0.90306 (matches JSON). The 83% figure is from the docs | L3 (0.903); docs (83%) | Supported |
| CL-24 | Effect scales with ID visibility: +0.007 (25%), +0.027 (50%), 100% a ceiling; rename recall tracks q squared | G1 0.0074, 0.0267, 0.0990; rename recall 0.0664, 0.2583, 1.0 vs 0.0625, 0.25, 1.0 | L1, L3 | Supported |
| CL-25 | Split ablation: +0.0001 at tuned cut-off; 6 rule-breaking clusters without; +0.20 at 0.80 | S1 0.000129; none@0.5 6 clusters; at t0.8 louvain 0.8048 vs none 0.6035, diff 0.2013 | L1 | Supported |
| CL-26 | Tuned fuzzy matching is 0.003 below no-merge on UK data | 0.8999 vs 0.9031 | L1 | Supported |
| CL-27 | Plans written before results ("pushed before any matcher was run") | Push times (E8): consistent for all three current studies; gaps 4 to 78 minutes; split-study plan and runner pushed together | L1 | Partly |
| CL-28 | "The held-out stage refuses to run twice" | `run_gate.py:344-348` (and similar guards) test `out_path.exists()`; not executed | reading | Supported (not run) |
| CL-29 | "Everything runs locally on one machine, single-threaded" (README Operational notes) | Library: yes. Runners use `ProcessPoolExecutor(max_workers=12)` (`run_gate.py:244,359`) | reading | Partly |
| CL-30 | "Splink was compared only on the real-data study, with a fixed hand-set configuration" (README Limitations) | The UK study adds supervised Splink trained on development labels | L1 | Contradicted (stale) |
| CL-31 | "Every blocked pair, accepted pair, skipped block and split is recorded" (README step 5) | Events: candidates, block_skipped, edge_blocked, edge_accepted, component_split | reading, ran it | Supported |
| CL-32 | README diagram: below-threshold pairs flow to the audit log | Code logs no rejection events | reading | Contradicted (minor) |
| CL-33 | No keys; data downloaded on demand to git-ignored `data/` and never committed | `.gitignore` has `data/`; no data files tracked; grep finds no keys | reading | Supported |
| CL-34 | Cut-off 0.93 and density rule chosen on seed 1 (README) | Initial commit is one scaffold commit; no seed-1 evidence in history | n/a | Not checkable |
| CL-35 | Demo output in README is "real output... lightly reformatted" | Table and counts match; the two blocked pairs appear in the opposite order (README (2,3) first; run (0,3) first) | L2 | Supported (cosmetic difference) |

**Tally:** 24 supported (CL-03, 04, 05, 06, 08, 09, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 26, 28, 31, 33, 35), 6 partly (01, 07, 10, 20, 27, 29), 3 contradicted (02, 30, 32), 2 not checkable (11, 34). Lowest level applies where a claim mixes levels. Real-data claims (CL-12 to 26) are L1 only because the one-shot design and the downloads prevent re-running (flagged NR).

---

## E4. Rule attacks

Rules from Explainer Section 4. All probes in `v2_probe.py` / `v2_probe2.py` / `v2_oldprobe.py`; outputs saved.

| # | Rule | Attack | Result | Label |
| --- | --- | --- | --- | --- |
| A1 | No cluster holds two IDs | Frame `rid=[0,0,1]`, IDs `A,B,None`, names Acme Tooling / Zeta Marine / Acme Tooling | Current code: `ValueError: \`rid\` must be unique; duplicated values include [0]` | Ran it |
| A2 | same | Two rows, `rid=[0,0]`, IDs A and B, no candidate pairs | `ValueError` (same message) | Ran it |
| A3 | same | `rid=[5,7,5]`, non-adjacent duplicate | `ValueError ... [5]` | Ran it |
| A4 | same, on the **previous** code (`git archive 5f17714~1` copy, imported by `PYTHONPATH`) | A1 and A2 inputs | Old code returned `cluster_id 0` for both rows holding IDs A and B (rule broken, no error). The two new tests (`test_resolve_rejects_duplicate_rid`, `..._null_rid`) **fail** on the old copy and pass on current code | Ran it |
| A5 | Every record gets one group | Null `rid` | `ValueError: \`rid\` must not contain nulls` | Ran it |
| A6 | same | Empty frame | Returns empty result, log `candidates n=0` | Ran it |
| A7 | No cluster holds two IDs | Same ID in two formats (`11-1111111` / `111111111`) | Treated as different: edge_blocked; clusters `[0,1]` | Ran it |
| A8 | same | ID with trailing space | Treated as different; kept apart | Ran it |
| A9 | same | Empty-string ID versus `"Z"` and identical names | Empty string treated as missing; merged on name | Ran it |
| A10 | same | Path X - u - Y (u has no ID), equal weights | Louvain returns one community, fallback fires (`tax_partition`); u joins X on tie; event has no tie information | Ran it |
| A11 | same | Veto off or `split="none"` | Guarantee void by design (`test_without_the_split...` asserts 2 IDs in a cluster) | Confirmed (test) |
| A12 | Same input, same answer | Demo rows reversed | Same grouping (cluster numbers permuted: `[3,2,3,2,1,1,0]` vs `[0,1,0,1,2,2,3]`) | Ran it |
| A13 | same | Louvain seeds 0 to 9 on the demo clump | Always `{0,2},{1,3}` | Ran it |
| A14 | Cap | 201 records sharing ID `BIG`, `tax_blocking=True` | `block_skipped key='id:BIG' size=201`; 200 records produce 19,900 pairs | Ran it |
| A15 | Input checks | Missing `tax_id` column | `KeyError: 'tax_id'` | Ran it |
| A16 | same | Null name | `AttributeError: 'NoneType' object has no attribute 'lower'` | Ran it |
| A17 | same | Blank names `""`, `"  "` | No candidates; singletons | Ran it |
| A18 | same | Unknown split mode | `ValueError: unknown split mode 'bogus'` | Ran it |
| A19 | same | 5,000-letter name, two copies | Works; merged | Ran it |
| A20 | same | `Berg GmbH` vs `Berg` | `normalise` keeps `gmbh`; no candidate pair | Ran it |
| A21 | ID shortlisting default | `Borealis Marine` and `Quartz Holdings` with ID Z | Default: `[0,1]` (apart); `tax_blocking=True`: `[0,0]` | Ran it |
| A22 | Held-out once | Not executed | Guard is `Path.exists()` | Confirmed (reading) |

---

## E5. Code map

```text
src/entity_resolution_gate/
  pipeline.py    219 lines. normalise 21-22; block_keys 29-55; Config 58-70; AuditLog 73-78; candidate_pairs 81-101; pair_score 104-115;
                 contradicts 118-120; _consistent 123-124; _split 127-163; resolve 166-204 (validation 171-176); pairwise_prf 207-219
  evaluation.py  127 lines. codes 15-18; n_pairs 21-24; prf_counts 27-33; components (union-find) 36-50; pair_table 53-66;
                 boot_f1 69-82; rid_pairs_to_positions 85-92; bcubed_per_record 95-111; bcubed_f1 114-127
  synth.py        70 lines. _typo 19-28; generate 31-70 (24 stems x 7 kinds, trap_rate, 60% of entities with ID, 80% of records show it)
  __init__.py      4 lines. Exports AuditLog, Config, generate, pairwise_prf, resolve
tests/            test_blocking (12), test_er (8), test_evaluation (11), test_gate_flags (6), test_split_modes (8)
examples/demo.py  7 records; prints table and blocked/split log lines
scripts/          benchmark.py; study runners run_real/run_blocking/run_sample/run_gate/run_split_ablation; fetch_* (3); sample_frame; enrich_profiles;
                  build_real_dataset; build_gate_dataset; real_posthoc; sample_posthoc
docs/             PROTOCOL_{BLOCKING,GATE,REAL,SAMPLE,SPLIT}.md; RESULTS{,_BLOCKING,_GATE,_REAL,_SAMPLE,_SPLIT}.md
results/          blocking/, real/ (superseded pilots), sample/ (+ superseded_pairwise_first_run/), gate/ (+3 Splink model exports), split/
.github/          workflows/ci.yml, dependabot.yml
```

Key behaviours (Confirmed from code): `resolve` validates split mode and `rid` (171-176), builds `rec` and `tax` dictionaries (178-179), adds shortlist pairs, vetoes and scores (184-191), loops over `nx.connected_components`, calls `_split` unless `split="none"` (194-202), maps rid to cluster with `replace_strict` (203). `_split` returns the clump if consistent and not chained (131-133); else up to depth 4 runs seeded Louvain (135-144); else the fallback partitions by ID and attaches each ID-less node to the ID with the most edge weight, ties broken by dictionary order (147-163). `candidate_pairs` sorts pairs (101) because Louvain depends on edge order (commit `6e0dd4f`). Study code coupling: `run_split_ablation.py` imports `run_gate` and mutates `rg.DATA` (line 187); `run_sample.py` imports `FUZZY_GRID`, `SPLINK_GRID`, `Matchers` from `run_real.py` (line 24). No vendored code. The library does no file or network I/O. Network use is confined to three fetch scripts (`urllib`).

---

## E6. Model call sites

None in the library or scripts: no language-model, image or speech call. The only learned component is **Splink** (Fellegi-Sunter, fitted by expectation-maximisation or from labelled development pairs), used inside the study runners: `scripts/run_real.py` (single-comparison and "rich" variants; protocol `PROTOCOL_REAL.md:27` and Deviation 2), `scripts/run_gate.py` (`splink_id`, `splink_id_sup`; protocol Deviation 4; saved models `results/gate/splink_sup_model_q{0.25,0.5,1.0}.json`). Runs locally, no cost, no tokens. Imports Splink at module level in `run_gate.py`, so `run_split_ablation.py` (which imports `run_gate`) needs the study extra although it never fits Splink (Confirmed, `run_split_ablation.py:23`). Label: Confirmed.

---

## E7. Tests and CI

**Counts (Ran it):** 45 collected, 45 passed, 0 failed, 0 skipped; no `skip`, `xfail` or custom markers anywhere (`git grep`); no test uses network, GPU, Docker or a paid service. Coverage 99% (272 statements): `pipeline.py` misses 92 (the `block_skipped` log call) and 146 (the "sparse but unsplittable, keep" return); `evaluation.py` misses 124 (zero-total weights). In the earlier session `pipeline.py:161` (the singleton branch of the fallback) was also missed; Hypothesis sampling varies by run (My reading).

| File | Tests | Kind |
| --- | --- | --- |
| `test_blocking.py` | 12 | 4 property (base mode unchanged; every mode only adds keys; identical normalised names share a key; token-sort never exceeds default), 8 unit/integration (nested modes, squash, first-token, wide window, monotone candidates, sorted order, long-prefix) |
| `test_er.py` | 8 | normalise/blocking tolerate typos; contradiction rule; identical names different IDs; **1 property (no cluster holds two IDs, 15 examples)**; low-threshold forces split path; deterministic and JSON log; quality floor on synthetic data; pairwise P/R/F1 edge cases |
| `test_evaluation.py` | 11 | 4 property (pairwise counts vs brute force; components vs NetworkX; unit-weight bootstrap equals F1; B-cubed vs definition), `rid_pairs_to_positions`, B-cubed extremes, "one huge entity" |
| `test_gate_flags.py` | 6 | veto/match switches independent; renamed pair needs ID blocking (`test_equal_ids_are_not_even_proposed_without_tax_blocking`); missing address is no evidence; defaults |
| `test_split_modes.py` | 8 | duplicate and null `rid` rejected (new, `5f17714`); bridge breaks rule without split; split restores it (x2 parametrised); unknown mode; sparse chain only under louvain; default mode |

**CI versus docs (Confirmed):**

| Item | CI actually runs | Docs say |
| --- | --- | --- |
| Install | `pip install -e ".[dev]"` (no study extra) | Quickstart uses `uv`; study extra for studies |
| Types | `mypy src tests` | "`mypy --strict`; ruff" (at-a-glance); `mypy src tests scripts # strict, clean` (Verify) |
| Lint | none | "ruff" in the Tests row |
| Tests | `pytest -q` (45) | "43 passed" |
| Benchmark, demo, study scripts | not run | Verify section lists them for a reviewer |
| Python versions | 3.12 only | `requires-python >=3.11`; mypy `python_version = "3.11"` |
| Branch protection | none (`protected=false`) | not claimed |

**Three spot-checks (Confirmed by reading and running):**
1. `test_no_cluster_ever_holds_two_tax_ids` (`test_er.py:48-52`): decorators at 48-49. Generates `generate(60, seed, trap_rate)` with `seed` in 0..10,000 and trap 0 to 0.6, resolves at threshold 0.6, then `assert_gate_invariants` checks no null cluster ids, `height == rid.n_unique()`, and at most one non-null ID per group. Real behavioural check; only `max_examples=15`; passes against the fallback logic, and `test_without_the_split...` shows it can fail when the split is off.
2. `test_prf_counts_matches_brute_force` (`test_evaluation.py:32-36`): compares `prf_counts` with an enumerated-pairs implementation on random labels. Real.
3. `test_missing_address_is_not_evidence` (`test_gate_flags.py:63-73`): the first assertion (two empty addresses add nothing) is real; the second compares a both-addresses score against `pair_score(a, c, cfg) * 0 + 0.7 * name_only`, so the multiplied-by-zero term does nothing and the check is weaker than its name. Also `test_defaults_enable_everything` (`test_gate_flags.py:76-78`) asserts only `tax_veto` and `tax_match`; the third switch `tax_blocking` is off by default (My reading: an editing leftover and a stale name).

**Who wrote the tests:** commit credits show Claude for all test commits (Confirmed); whether the author edited them is Ask the author.

---

## E8. Plan-versus-results timing, bulk commits, credits

GitHub's events list covers about 90 days; these push times (UTC, from `gh api repos/.../events`) exist because the work is recent. Commit authorship times (-0400) agree with push times to within seconds. The runs of the held-out stages themselves are not timestamped anywhere; only the commits that added their outputs are.

| Study | Plan commit (pushed) | Settings frozen (pushed) | Results (pushed) | Gaps from the plan push |
| --- | --- | --- | --- | --- |
| First pilot (superseded) | `2f4b29a` 10-11 20:55:12 | `e3d4f6b` (runner and dev sweep) 10-12 00:17:07 | `4643f96` 10-12 10:26:13 | 3 h 22 min; 13 h 31 min |
| Blocking pilot (superseded) | `608ac6f` 10-12 11:19:56 | `6e0dd4f` 11:26:31 | `b67f791` 11:49:49 (the same commit adds the random-sample protocol) | 6.6 min; 30 min |
| Random-sample study | `b67f791` 11:49:49 | `99f22c4` 12:59:41 | `80c0dc2` 13:07:54 | 69.9 min; 78.1 min |
| UK registry-ID study | `c3c814e` 13:38:01 | `b6a85f5` 14:03:07, then supervised Splink `ebc4560` 14:07:58 and `d365086` 14:15:02 | `2bb96a9` 14:18:02 | 25.1 min; 40.0 min |
| Graph-splitting ablation | `8f334c4` 20:33:41 (protocol **and** runner in one commit) | `e31cf06` 20:36:21 | `c651f50` 20:37:56 | 2.7 min; 4.3 min |

Verdict: the order "plan, then settings, then results" holds in every push, so the plans were public before the results. Nothing shows the held-out data were untouched before the plan push (Ask the author). Several deviations are logged between the dev stage and the held-out scoring (Per the docs). Protocols with a "What I knew before writing this" section: GATE, SAMPLE, SPLIT; REAL and BLOCKING have "My expectation, written down so it can be wrong" only (Confirmed, `grep`).

**Bulk commits (`git show --numstat`):** `99f22c4` +7,341 lines, of which 7,172 are two saved sweep files and two frozen files (98% generated results); `e3d4f6b` +2,155 (1,707 saved sweep, 264 runner, 169 evaluation helper and test); `6e0dd4f` +1,228 (770 saved sweep, 265 runner, 126 tests); `da904dd` +1,316 (old explainer); `83233ba` initial +519. 18 of 29 commits fall on 2026-10-12. Step-by-step history of those is not recoverable (My reading).

**Commit credits by tool (Confirmed):** Claude Sonnet 5.5 x27; Claude Opus 5.5 (1M context) x1; none x1 (`ad87f4f`); no Copilot, Codex, Gemini or other credits. Author name on all 29: Chris Schmidt. No instruction files (`CLAUDE.md`, `AGENTS.md`, `.cursor`, `.clinerules`, `.windsurf`) are tracked. Author says (AUTHOR_CONTEXT): Claude Code mostly, plus Copilot, Codex and Prime-Agent across projects; no repository evidence of those.

---

## E9. Gates and approvals

No gate records, checklists, status files or approval logs exist in the repository (Confirmed by listing). The only gate-like control is the held-out refusal (`run_gate.py:344-348`; `run_sample.py:128`; `run_split_ablation.py:107`; `run_real.py:173`; `run_blocking.py:214`), a file-exists check run by the script, not a human approval. Approver identity: not applicable. The AUTHOR_CONTEXT mentions `gate-engine.sh mark-passed ... --approve` for other repos; nothing like it is here.

---

## E10. Environment

| Package | Minimum in `pyproject.toml` | Installed (Ran it, `pip list`) |
| --- | --- | --- |
| Python | `>=3.11` | 3.12.13 |
| polars | `>=1.0` | 2.0.0 |
| duckdb | `>=1.0` | 1.5.6 |
| networkx | `>=3.2` | 3.7 |
| rapidfuzz | `>=3.6` | 3.14.6 |
| jellyfish | `>=1.0` | 1.3.0 |
| pyarrow | `>=15` | 26.0.0 |
| numpy | `>=1.26` | 2.5.4 |
| pytest / hypothesis / mypy / ruff | `>=8` / `>=6.100` / `>=1.10` / `>=0.5` | 9.1.1 / 6.170.1 / 2.4.0 / 0.17.1 |
| splink / pandas (study extra) | `>=4` / `>=2` | 5.0.0 / 3.0.6 |

No lock file; lower bounds only; no result file records package versions (Confirmed by inspecting the JSON keys). The installed polars and splink are one major ahead of the minimum; whether published real-data numbers came from Splink 4 or 5 is Ask the author. A fresh install today would resolve to these or later versions. With these versions, the synthetic benchmark reproduced to the digit (Ran it) and all 45 tests pass; the real-data runners were not run.

---

## E11. Security and privacy scan

- **Secrets, current files:** `git grep -nIE` for AWS keys (`AKIA...`), GitHub tokens, `sk-` keys, private-key headers, `api_key=`, `password=`, `secret=`: no hits (the old explainer file was also scanned separately: no hits). **History:** `git log -p --all -G` for the token patterns: no hits; no `.env`, key or credential file names in any commit. No secret found, so no file or commit to report.
- **Repository tests for secrets:** none (`tests/test_no_secrets.py` does not exist here, unlike other portfolio repos per AUTHOR_CONTEXT).
- **Outside services:** USAspending public API (no key; three fetch scripts, linear-backoff retries) and a manually downloaded UK Companies House snapshot. Library: none.
- **GitHub settings (Confirmed, `gh api`):** public repo; Dependabot security updates, secret scanning, push protection and validity checks all **disabled**; Dependabot version updates configured (two PRs open and unmerged); `main` unprotected.
- **Data and privacy:** company data only; raw downloads git-ignored and unhashed; the README says the UK snapshot's licence was not found so it is used for research only. Ask the author for the terms.
- **Supply chain:** unpinned versions; no lock file; no SBOM; dependencies are permissive libraries; `pip-audit` was not run this session (an earlier session reported none known; not re-run).
- **Untrusted input:** names are only compared as text; no `eval`, no shell, no deserialisation of input (My reading). Null name crashes (A16). Very large or adversarial lists could consume memory: the in-memory join is bounded by the 200-record key cap (My reading, E13).

---

## E12. Shortcomings register

No **Critical** or **High** finding stands in the current code. The one High from the earlier review (duplicate `rid` voiding the guarantee) was fixed in `5f17714`; I re-ran it (A1 to A5). The project is not declared finished, so no split into corrections owed versus reopening changes is made.

### SR-01 ID shortlisting is off by default (Medium)
*Evidence:* `Config.tax_blocking = False` (`pipeline.py:68`, comment "needed for renames"); `test_equal_ids_are_not_even_proposed_without_tax_blocking`; A21. `run_gate.py:61` sets it on for `P_match` and `P_full`. Practice data: 0.912 vs 0.913 (1,000 companies), 0.889 vs 0.891 (5,000). *Impact:* a user with IDs gets less than the headline UK result; unmeasured on real renames. *Disclosed?* Partly (code comment; README summary silent). *Options:* **A** switch on by default (gains: headline reproducible; costs: behaviour change, more candidate pairs, ID lists over 200 skipped; new risk: SR-04; reversible by a flag). **B** keep off, warn in the logbook and README when IDs exist but are unused (no behaviour change; users may ignore). **C** document only. *Recommend:* A in v0.4, after a practice-data re-run. *Effort/payoff:* small/high. *Verify:* default call on the Borealis/Quartz pair gives one cluster; benchmark within +-0.003.

### SR-02 Ties are broken arbitrarily and unlogged (Medium)
*Evidence:* demo record 1 (edges 0.9398 to records 0, 2 and 3; Louvain seeds 0 to 9 all give {0,2},{1,3}; modularity 0.0078 vs -0.0303); A10 (fallback tie-break by dict order, event has no tie field). Note the earlier review's correction: this is a genuine tie, not a design mistake. *Impact:* an auditor cannot see a coin toss. *Disclosed?* The wrong-twin outcome yes (README); the missing log entry no. *Options:* **A** log tied or near-tied placements with margins. **B** also emit a "needs a person" list. **C** break ties by total link weight (picks A in the demo, 1.88 vs 0.94, but only reflects A having two near-duplicate records; test before adopting; new risk: a systematic bias toward large groups). *Recommend:* A then B. *Effort/payoff:* small to medium / medium to high. *Verify:* the demo log shows a tie event for record 1.

### SR-03 Weak input handling beyond `rid` (Medium)
*Evidence:* A15 (`KeyError`), A16 (`AttributeError`), A7 to A9 (ID formatting, trailing space, empty string). *Impact:* messy real data crashes or silently keeps same-company records apart. *Disclosed?* No. *Options:* **A** specific error messages and optional ID clean-up (strip, upper-case, optional digits-only); **B** a separate validation function; **C** document. *Gains/costs:* A small code; risk: over-aggressive clean-up equates different IDs, so make it opt-in. Reversible. *Recommend:* A. *Effort/payoff:* small/medium. *Verify:* tests for each case.

### SR-04 The key-list cap silently drops matches, including ID lists (Medium)
*Evidence:* 336 skipped lists at 39,369 records; cap off restores recall 0.842 to 0.974, run 8.8 s to 102 s, candidates 1.23M to 14.87M (Ran it); A14 (an `id:BIG` list of 201 skipped). *Impact:* accuracy at scale; a large company's own records never linked by their shared ID. *Disclosed?* Partly (README attributes the drop to "partly the generator"; later "unrelated to the algorithm", contradicted by the cap test). *Options:* **A** never cap ID lists; **B** split oversized lists with a second key such as zip; **C** document. *Recommend:* A now, B if scale matters. *Effort/payoff:* small to medium / medium. *Verify:* A14 yields 20,100 pairs; recall at 39k up.

### SR-05 Automatic checks, lock file and branch protection are weaker than the docs imply (Medium)
*Evidence:* E7 table; E10. *Impact:* no automatic quality gate; unreproducible installs. *Disclosed?* No. *Options:* **A** add ruff, `mypy src tests scripts` (with the study extra), a lock file, a benchmark step asserting minimum F1 and zero violations, branch protection; **B** only correct the README. *Costs:* A slightly longer CI, upkeep of the lock file; both reversible. *Recommend:* A. *Effort/payoff:* small/high. *Verify:* a deliberate regression turns CI red.

### SR-06 The best UK result is an upper bound that the README does not stress (Medium)
*Evidence:* `run_gate.py:85-86` (`visible()` returns the entity id, i.e. the answer key, with probability q); `RESULTS_GATE.md` states "visibility ... is a simulation" and "company number" but not that ID evidence is therefore error-free. *Impact:* overstates expectations for real IDs. *Disclosed?* Partly. *Options:* **A** new pre-registered study injecting 1% to 5% wrong IDs; **B** README caveat; **C** nothing. *Recommend:* B now, A later. *Effort/payoff:* small then medium / medium to high. *Verify:* README caveat present; study shows degradation curve.

### SR-07 Out-of-date documentation (Medium)
*Evidence:* E14. *Impact:* trust. *Disclosed?* No. *Options:* **A** fix the lines, replace the old explainer; **B** add a script comparing README numbers with saved results. *Recommend:* A now. *Effort/payoff:* small/medium. *Verify:* `grep` for "43" and "clean" in README.

### SR-08 No saved log and no human-review path (Medium)
*Evidence:* `AuditLog` is an in-memory list (`pipeline.py:73-78`); no file writing in `src/`; rejected pairs and ties not logged. *Impact:* explanations vanish after the run; "explainable merges" is weaker than pitched. *Options:* **A** write JSON lines with a header of versions and settings; **B** add the review list from SR-02. *Recommend:* A. *Effort/payoff:* small to medium/medium. *Verify:* a run leaves a readable file.

### Minor items (table)

| ID | Item | Severity | Evidence | Fix |
| --- | --- | --- | --- | --- |
| SR-09 | Demo crashes when stdout is redirected on Windows | Low | Ran it (exit 1, cp1252) | Reconfigure stdout or print ASCII |
| SR-10 | Test leftovers (`* 0`; misnamed defaults test) | Low | E7 spot-check 3 | Fix assertion and name |
| SR-11 | Study scripts (2,260 lines) have no tests | Medium | `tests/` imports only the library | Test the core functions (`metric`, slice bootstrap) |
| SR-12 | No lock file; versions unrecorded in results | Medium | E10 | Lock file; write versions into result JSON |
| SR-13 | Companies House licence unconfirmed | Medium | README "I did not find a licence statement" | Confirm terms |
| SR-14 | GitHub secret scanning and push protection off | Low | `gh api` | Turn on |
| SR-15 | Old technical explainer sits in the repo root and is not linked | Low | `da904dd` | Replace after review |
| SR-16 | `pair_table` builds n x n boolean matrices | Low (study use only) | `evaluation.py:53-66` | Fine to ~10^4 records per slice; sparse pairs if needed |
| SR-17 | Dependabot PRs #1 and #2 open since 10-13 | Low | `gh pr list` | Merge or close |
| SR-18 | Thresholds at the 0.99 grid ceiling; 20 variants, 2 adjusted | Low (research caveat, Disclosed) | `RESULTS_GATE.md` | Extend the grid in a new study |
| SR-19 | Previous names carry no address, understating address evidence | Low (Disclosed) | `RESULTS_GATE.md` Limits | Note only |
| SR-20 | Duplicated helper code in scripts (profile dictionaries, `post()`) | Low | earlier review; not re-checked | Refactor if scripts are reused |

---

## E13. Math and method detail

**Name measures.** Jaro: `(m/|s1| + m/|s2| + (m - t)/m) / 3` with `m` matching characters (within a window of `floor(max(|s1|,|s2|)/2) - 1`) and `t` half the transpositions. Jaro-Winkler: `J + l * p * (1 - J)`, `p = 0.1`, `l` = common prefix length up to 4 (RapidFuzz default). Token-sort ratio: sort whitespace tokens, join, then normalised Indel similarity `1 - (indel distance)/(|a| + |b|)`. Worked: tidy names are 20 and 20 characters differing by one substitution: Indel distance 2, ratio `1 - 2/40 = 0.95`; Jaro `(19/20 + 19/20 + 1)/3 = 0.9667`, JW `0.9667 + 4*0.1*0.0333 = 0.98` (matches the program). Address ratio `fuzz.ratio` is the same Indel ratio on lower-cased strings: `1 - 4/26 = 0.8462` for "120 main st" vs "120 main street". **Pair score** (`pipeline.py:104-115`): same non-empty ID gives 1.0; name = `max(JW, TSR)` (or TSR if `name_score="token_sort"`); empty address on either side returns name alone; else `0.7*name + 0.3*addr` with `addr *= 0.5` when both zips exist and differ. Threshold `>= 0.93`. Recomputed: `0.7*0.98 + 0.3*0.846154 = 0.939846`, logged as 0.9398.

**Modularity** (Newman): `Q = sum_c [ L_c/m - (S_c/(2m))^2 ]` for a weighted undirected graph, `m` total weight, `L_c` internal weight, `S_c` sum of node strengths. Demo clump: `m = 3.8194`; strengths 1.9398, 2.8194, 1.9398, 0.9398 (sum `2m = 7.6388`); `Q({0,2},{1,3}) = 0.0078` (each group 0.003878), `Q({0,1,2},{3}) = -0.0303`, `Q({0,1},{2},{3}) = -0.2217` (program values via NetworkX). Louvain (Blondel et al. 2008) greedily moves nodes and aggregates communities; it is a heuristic, order-dependent (hence `seed=0` and sorted edges). Typical cost near `O(E log N)`; not proven.

**Complexity of the shortlist.** Each record yields up to `K = 2*C(min(tokens,4),2) = 12` keys in base mode (30 plus extras in the wide mode, six tokens). The join is `sum over keys of s_k^2/2`; with the cap `s_k <= 200` the pair count is bounded by `N*K*200/2 = 1,200*N`. Observed: 39,857 candidates for 2,021 records (1.95% of 2,041,210 pairs); 935,873 for 9,870 (1.92% of 48,703,515); 1,233,412 for 39,369 (0.16% of 774,939,396). Scoring is linear in candidates; memory holds the dictionaries, the graph and the log.

**Metrics.** Pairwise: `P = TP/pred pairs`, `R = TP/true pairs`, `F1 = 2PR/(P+R)`; pairs counted by `sum c(c-1)/2` per label; `prf_counts` forms the joint label `labels*(max(ent)+1)+ent`. B-cubed per record: `P_r = |C(r) ∩ E(r)|/|C(r)|`, `R_r = |C(r) ∩ E(r)|/|E(r)|`, then means; with weights `w[e]` per entity for the bootstrap. Do-nothing: `P = 1`, `R = (#entities)/(#records)`: US held-out `1527/4542 = 0.3362` so `F1 = 0.5032`; UK held-out `23280/28278 = 0.8233` so `F1 = 0.9031` (equals the saved no-merge row, a useful consistency check). Demo (Ran it): pairwise `(0.667, 0.5, 0.571)`; B-cubed `(0.857, 0.810, 0.833)`; all-singletons B-cubed F1 `0.727`; all-in-one `0.469`, pairwise `0.32`.

**Bootstrap.** Studies resample slices (UK) or entities (US) with replacement, 2,000 draws; `boot_f1` weights within-entity pairs by `w[e]` and cross-entity pairs by `w[a]*w[b]` (`evaluation.py:69-82`). This is a weighted approximation without re-clustering (the earlier review corrected an "exact" claim). Contrasts reuse the same resamples on both sides (Per the docs); Bonferroni 97.5% or 98.75% intervals for the pre-specified secondary contrasts. Toy example in the Explainer: gains 0.016, 0.022, 0.026, 0.031, 0.037; 2,000 resamples (seed 0, my own run) give a 95% middle range 0.0204 to 0.0328.

**Rename-recall arithmetic.** If each record shows the ID independently with probability `q`, a two-record rename pair is recovered with probability `q^2`: 0.0625, 0.25, 1.0 vs measured 0.0664, 0.2583, 1.0 (`P_full@q`).

**References (from general knowledge; not in the repository):** Jaro 1989, JASA 84; Winkler 1990, American Statistical Association proceedings; Fellegi and Sunter 1969, JASA 64; Newman 2006, PNAS 103; Blondel, Guillaume, Lambiotte, Lefebvre 2008, J. Stat. Mech.; Efron 1979, Annals of Statistics; Amigo et al. 2009 (B-cubed metrics, Information Retrieval). Label: My reading for the citations; I did not verify them online.

---

## E14. Discrepancies between docs and code

| # | Docs say | Code or run shows |
| --- | --- | --- |
| 1 | README: 43 tests (three places) | 45 (after `5f17714`) |
| 2 | README Verify: `mypy src tests scripts # strict, clean` | 1 error (8 without study extra); CI runs `src tests` only |
| 3 | README flow diagram: below-threshold pairs go to the audit log | No rejection events; only candidates, blocked, accepted, skipped and split |
| 4 | README gate section: violations "49 to 77" without the veto | 48 (`P_match`) to 77 |
| 5 | README: "single-threaded"; "Everything runs locally on one machine, single-threaded" | Library single-threaded; study runners `ProcessPoolExecutor(max_workers=12)`; `cdist(workers=-1)` is used in scripts (earlier review; not re-checked) |
| 6 | README Limitations: Splink "with a fixed hand-set configuration" | UK study adds a supervised Splink trained on development labels |
| 7 | README Limitations: large rows "pessimistic in a way unrelated to the algorithm" | Recall loss is the key-list cap |
| 8 | `pyproject.toml:17` comment: study extra "only for scripts/run_real.py" | `run_gate.py`, `run_split_ablation.py` also need it |
| 9 | README demo audit lines: (2,3) then (0,3) | Run prints (0,3) then (2,3) (README says "lightly reformatted") |
| 10 | README speed 6.7 s | 7.1 s and 8.8 s (machine-dependent) |
| 11 | README at-a-glance UK result (+0.027) | Needs `tax_blocking=True`, off by default; not stated in the summary row |
| 12 | `test_defaults_enable_everything` | Checks two of three switches; `tax_blocking` defaults off |
| 13 | `test_missing_address_is_not_evidence` | Second assertion has a multiply-by-zero term |
| 14 | README: "Guarantee: no cluster contains two different non-null tax IDs" | Holds with `tax_veto=True` and `split != "none"` on well-formed input; ablation modes void it by design (tests confirm); earlier duplicate-`rid` hole fixed |
| 15 | README: CI badge only | CI runs fewer checks than the README's verify list |
| 16 | Docs index (README) lists no explainer | `entity-resolution-gate_MASTER_EXPLAINER.md` sits in the repo root |

---

## E15. Production readiness detail

| Trait | Rating | Evidence |
| --- | --- | --- |
| Clean start (documented, versions recorded) | Partly | README quickstart (`uv venv && uv pip install -e ".[dev]"`) works (earlier fresh install, 2026-10-18); minimum versions only; Windows redirect crash (SR-09) |
| Checks block bad changes | Partly | CI on push and PR: mypy `src tests` and 45 tests (all green); no quality gate; no ruff; no branch protection |
| Quality measured vs real goal and baseline | Yes | Held-out studies with no-merge, exact, tuned fuzzy and Splink baselines; ranges; negative results (E3, Explainer Section 8). Goal is a research one |
| Safe when things go wrong | Partly | Pure function; re-runs safe; cap bounds cost (key lists 200); `rid` check; null name crash; no timeouts or retries in the library; fetch scripts retry linearly |
| Human review or stop | No | No review queue or confirmation anywhere |
| Versioned prompts, models, settings | Partly | `Config` in git; tuned thresholds in committed `frozen.json`; Splink models saved; package versions unrecorded; no prompts |
| Logs for diagnosis and monitoring | Partly | `AuditLog` in memory only; scripts `print`; no timing, cost or quality telemetry; run logs were committed then removed (`ad87f4f`) |
| Data and secrets | Partly | No secrets; raw data git-ignored; E11 settings off; licence unconfirmed |

**Placement: Works locally.** Rung 3 (Deployable) is not reached because: no hosted or packaged service exists (`Dockerfile` only runs tests), CI does not guard quality, installs are not locked, logs are not persisted. **Full gap list:** packaging for others (no release on a package index; wheel config exists via hatchling); hosting and health check (missing); sign-in (not needed for a library); monitoring and alerts (missing); backups and retention (n/a today); rollback (git tags; release v0.3.0); versioned models and prompts (n/a; lock libraries); cost limits (cap only); security review (missing); runbook (missing); legal and compliance (Companies House licence; ID handling). **Production-mirroring evidence:** E7 (CI), E8 (plans before results), A4 (defect, fix and failing-before tests), the property test, the held-out refusal, the corrected-pilot notices (commit `b67f791` "Own up to the alphabetical-prefix sampling flaw"). **Reusable assets:** `synth.generate` (seeded, trap twins); `evaluation.py` helpers; the PROTOCOL/RESULTS document pattern; `bcubed`/bootstrap tests against brute force. No prompt library, runbook or reference deployment.

---

## E16. Review dispositions

The earlier review (`v1.1\entity-resolution-gate.review.md`, 25 findings) was written against the v1.0 draft. This v2 Explainer is a full rewrite, so each finding is dispositioned as applied to the new text and re-verified where it concerns the code.

| # | Finding | Disposition in v2 |
| --- | --- | --- |
| 1 | Demo record 1 is a genuine tie, not a design mistake | Applied: Explainer Section 3 and SR-02; "biggest mistake" language dropped; weight-sum alternative marked as untested |
| 2 | Unsupported authorship claims about prose and "agent mistakes" | Applied: Section 11 says who wrote first-person prose is unknown; errors counted as defects, not AI mistakes |
| 3 | Mermaid `;` broke a diagram | Applied: all six diagrams avoid `;`, parentheses and `#`; all render (E2) |
| 4 | Decomposition (gain from same-ID evidence) credited to the review | Applied: credited to the project's own write-up |
| 5 | Default `Config` effect on renames overstated and mis-tagged | Applied: SR-01 says the loss is unmeasured; practice data 0.912 vs 0.913 re-run |
| 6 | Duplicate `rid` framing | Re-run: now raises `ValueError`; old behaviour reproduced on a `git archive` copy (A4). Framed as malformed input, not a gate flaw |
| 7 | 20k recall drop is the cap | Re-run and used (CL-09); README line marked partly wrong (CL-10) |
| 8 | "9 in 10" misreads B-cubed | Applied: no-merge baselines stated (0.50 US, 0.903 UK) |
| 9 | Wrong counts (64 tracked files, 22 JSON, 2,260/761 lines, 18 on 10-12) | Re-measured: 65 tracked files now (old explainer added), 22 JSON, 2,260 lines, 761 lines, 18 commits on 10-12 |
| 10 | cp1252 crash scope | Re-run: reproduced with redirected output; interactive consoles not tested (Explainer says "when output is redirected") |
| 11 | Profiler-inflated speed-up | Dropped (no profile claim made) |
| 12 | "Four bugs with regression tests" | Not repeated; Explainer says "caught and fixed in public" |
| 13 | Rename recall "exactly" q squared | Applied: "close to" |
| 14 | Bootstrap "exact" | Applied: "weighted approximation" (E13) |
| 15 | Fallback does most repairs only at the tuned cut-off | Applied: Explainer cites the cut-off-dependent split activity (`split_activity`: 5 of 6 via fallback at 0.5 visibility, tuned) and the loose-threshold benefit |
| 16 | Commit-size range | Applied with `numstat` (E8) |
| 17 | Test line citation; "What I knew" in three of five protocols | Applied (E7, E8) |
| 18 | Missed discrepancies | All carried into E14 |
| 19 | Missing vs differing address numbers | Applied: examples use measured 0.85 and 0.98 |
| 20 | Splink major version uncertainty | Applied (E10: unknown which major) |
| 21 | Dev findings "unsupported" | Applied: "Not checkable" (CL-11) |
| 22 | mypy drift history | Applied (CL-02) |
| 23 | Repetition and length | Applied: single home per fact; Section 8 is the home for results |
| 24 | Splink choice reason | Applied: "not documented" |
| 25 | Timeline hour labels | Applied: gantt with accurate days; times in E8 |

---

## E17. Completeness and backlog register

### Promised versus built

| Promised or implied (source) | Status | Evidence |
| --- | --- | --- |
| Normalise names (README Method 1) | Done and tested | `pipeline.py:21-22`; `test_er.py:13` |
| Block keys, four modes (README Method 2; `Config.blocking`) | Done and tested | `pipeline.py:29-55`; `test_blocking.py` (property tests) |
| Candidate pairs via DuckDB; skip and log blocks over 200 (Method 3) | Done; the skip line is untested | `pipeline.py:81-101`; coverage misses line 92; used at 39k |
| Hard constraint / veto (Method 4) | Done and tested | `contradicts`; `test_contradiction_rule`; `test_veto_keeps...` |
| Score 0.7 name + 0.3 address; same ID 1.0; missing address (Method 5) | Done and tested (one weak assertion) | `pair_score`; `test_missing_address_is_not_evidence` |
| ID shortlisting switch | Done and tested; off by default | `test_equal_ids_are_not_even_proposed...` |
| Graph gate: components, density, Louvain, fallback (Method 6) | Done and tested | `_split`; property test; `test_split_modes.py` |
| Split modes louvain / tax_only / none | Done and tested | `test_split_modes.py` |
| Audit log of every blocked pair, accepted pair, skipped block and split (Method 7) | Done in part; memory only; ties and rejected pairs not logged | `AuditLog`; probe A10 |
| Synthetic generator with trap twins | Done | `synth.py`; used by tests and benchmark |
| Evaluation helpers (pairwise, B-cubed, bootstrap, components) | Done and tested vs brute force | `evaluation.py`; `test_evaluation.py` |
| Benchmark script (reproduces the table) | Done; reproduced | `scripts/benchmark.py`; `v2_bench_out.txt` |
| Demo (README output) | Done; Windows redirect crash | `examples/demo.py`; A-run |
| USAspending random-sample study | Done; results committed; not re-run | `docs/*SAMPLE*`; `results/sample/` |
| UK registry-ID gate study | Done; same | `docs/*GATE*`; `results/gate/` |
| Graph-splitting ablation | Done; same | `docs/*SPLIT*`; `results/split/` |
| Pilot studies (alphabetical sample) | Done, superseded, notices kept | `docs/*REAL*`, `*BLOCKING*` |
| CI badge | Done (types and tests only) | `ci.yml` |
| Dependabot | Done; 2 PRs unmerged | `dependabot.yml`; `gh pr list` |
| Dockerfile | Done; runs tests; not run here | `Dockerfile` |
| "mypy strict, clean" on scripts | Partly (1 error) | CL-02 |
| BM25 or dense-embedding blocking; pgvector; embedding feature (README Known gaps) | Planned only, not built | README; no code |
| Executive-name and geographic features; Leiden | Planned only | README; no code |
| 100k+ run and F1-vs-latency curve | Planned only | README; benchmark stops at 39,369 |
| Real tax IDs or CAGE codes; other hard rules | Planned only; public data has none | README |
| SEC EDGAR EIN test; OpenCorporates | Abandoned or not tried (stated) | README |

No stubs, no TODO or FIXME (`git grep`), no skipped tests, no empty folders, no settings nothing reads: `max_block_size`, `min_density`, `w_name`, `w_addr`, `blocking`, `tax_veto`, `tax_match`, `tax_blocking`, `name_score`, `split` are all read in `pipeline.py` (Confirmed).

### Full backlog

| ID | Group | Item | Why | Who | Effort | Payoff | Depends on | Trade-off |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | Finish | 100k+ run with accuracy-versus-time curve | README gap | readers, author | M | M | SR-04 | Honest limit; days; memory trouble likely |
| B2 | Finish | Real tax-ID or CAGE test | thesis | domain experts | L | H if possible | data not public | Private data forbidden by the data rule |
| B3 | Finish | Embedding blocking, Leiden, extra features | roadmap | author | L | L | none | Complexity the thesis does not need; move to "not planned" |
| B4 | Fix | Null-name crash and clear messages (SR-03) | robustness | all users | S | M | none | tiny behaviour change |
| B5 | Fix | Refresh README, comments; replace old explainer (SR-07, SR-15) | trust | reviewers | S | M | review of new explainer | none |
| B6 | Fix | Demo redirect crash (SR-09); test leftovers (SR-10) | first run, test honesty | newcomers | S | L | none | none |
| B7 | Improve | CI: ruff, scripts type-check, lock file, benchmark gate, branch protection (SR-05, SR-12) | hiring signal | author, reviewers | S | H | none | upkeep |
| B8 | Improve | ID shortlisting default on (SR-01) | headline reproducible | all with IDs | S | H | practice-data re-run | behaviour change; version bump |
| B9 | Improve | Log ties; save log as JSON lines with header (SR-02, SR-08) | explainability | reviewers | S-M | M-H | none | larger log |
| B10 | Improve | Do not cap ID lists (SR-04) | large companies | users | S | M | none | more pairs to score |
| B11 | Improve | Optional ID clean-up (SR-03) | messy IDs | users | S | M | B4 | over-cleaning risk |
| B12 | Improve | Tests for study-script logic (SR-11) | reproducibility | author | M | L | none | time for little learning |
| B13 | Add | Runbook and write-up of the duplicate-`rid` defect | hiring signal | reviewers | S | M | none | none |
| B14 | Add | "Needs a person" list (SR-02 option B) | human-in-the-loop evidence | users | M | H | B9 | new output to maintain |
| B15 | Add | Tiny hosted demo with health check | deployable evidence | reviewers | M | M | B7 | upkeep; invented data only |
| B16 | Add | Pluggable scorer; learned scorer under the gate | learning, science | author | L | M-H | redesign | biggest scope; may show little gain |
| B17 | Add | Second hard rule (parent and subsidiary) | domain | experts | M | M | pluggable rules | needs data with parent links |
| B18 | Add | ID-error injection study (SR-06 option A) | realism | experts | M | M-H | new protocol | uses up fresh slices |

### Milestones

1. **M1, honest and gated (days):** B7, B5, B4, SR-06 caveat. *Exit test:* fresh clone installs from the lock file; CI runs ruff, `mypy src tests scripts`, 45+ tests and a benchmark that fails below set F1 or on any violation; `grep` finds no stale "43" or "clean"; the null-name case has a test that fails without the fix.
2. **M2, honest defaults and a usable log:** B8, B9, B10. *Exit test:* benchmark unchanged or better (+-0.003); the demo log shows a tie event for record 1; A14 yields 20,100 pairs; the Borealis/Quartz pair merges by default.
3. **M3, deployment habits:** B13, B15, optionally B1 and B14. *Exit test:* a demo URL answers a health check; a runbook and a defect write-up exist in the repo.

**Judgement:** polish and freeze after M1 and probably M2; do not extend scale or learned scoring here (B1, B3, B16 are optional). Merge or retire: not recommended (no obvious parent; no reason to retire).

---

## E18. Material moved out of the Explainer (revision after the independent reader check)

The reader check (`entity-resolution-gate.readercheck.md`, 76 findings) asked for reviewer scaffolding to leave the Explainer. Everything below was in the first Explainer draft and now lives only here.

**Full tools table (was Section 4).**

| Tool | What it is | Job here | Why (documented?) | Alternative |
| --- | --- | --- | --- | --- |
| Python >=3.11 | Language | Everything | Not documented | Rust, Go |
| Polars >=1.0 | Table library | Input and output tables | Not documented | pandas |
| DuckDB >=1.0 | In-process database | Self-join on block keys | README names it; reason not documented | Dictionary key to records |
| NetworkX >=3.2 | Graph library | Components, density, Louvain | Not documented | igraph |
| RapidFuzz >=3.6 | Text-similarity library | Jaro-Winkler, token-sort, ratio | Not documented | jellyfish, textdistance |
| jellyfish >=1.0 | Phonetic library | Metaphone key codes | Not documented | Soundex, NYSIIS |
| NumPy >=1.26, PyArrow >=15 | Numerics; Arrow bridge to DuckDB | Metrics, bootstrap | Not documented | Plain Python |
| Splink >=4 (study extra), pandas | Fellegi-Sunter matcher | Rival in the studies | Not documented | dedupe, Zingg |
| pytest, Hypothesis, mypy (strict), ruff | Test, random-input test, type and style tools | 45 tests; checks | Not documented | unittest, pyright |
| GitHub Actions, Dependabot, Docker | CI; update PRs; container recipe | Tests per change; monthly updates; test-only image | Not documented | Other CI |

**Full rules table (was Section 4).** No group holds two IDs: group checker last-resort step plus random-input test; breaks only with veto or split switched off (or, before `5f17714`, a duplicate `rid`). Every record gets one group: `replace_strict` at the end, plus the new `rid` check (`pipeline.py:171-176`). Same input, same answer: sorted pairs (`:101`), Louvain `seed=0`, test `test_deterministic_and_audit_log_is_json`; reversed rows gave identical groups (A12). Key lists over 200 skipped and logged (`:88-92`). Held-out scored once: `out_path.exists()` guards (E9).

**Data table (was Section 4).** Practice data: `synth.generate`, 24 x 24 x 7 = 4,032 base names. US: USAspending, FY2024 DoD recipients, frame 45,959, sample 3,000 after removing 1,019 used by the pilot, held-out 4,542 records / 1,527 entities (dev 4,330 / 1,471), entities over 50 names excluded (one). UK: Companies House snapshot 2026-10-01, 5,704,712 live companies, 60 slices x 800 strings, 30 dev and 30 held-out (28,278 records / 23,280 companies), previous names carry no address, visibility q by per-record hash (0.25, 0.5, 1.0). Pilot: first 10,000 awards in name order.

**Code locations formerly shown inside the method cards.** Tidying `pipeline.py:17-22`; keys `:29-55`; shortlist `:81-101`; pair score `:104-115`; veto `:105,118-120`; group checker `:123-204`; modularity call `:135`; Jaro-Winkler and ratios `:107-112`; held-out guard `scripts/run_gate.py:344-348`; grading `evaluation.py:27-33, 95-127`; bootstrap `evaluation.py:69-82`; Splink `scripts/run_real.py`, `scripts/run_gate.py`.

**Edge-case rows dropped from the Explainer table** (all in E4): missing ID column (`KeyError`), blank names, 5,000-letter name, reversed rows, the 201-record ID list.

**CI versus docs, spot-checks, safeguards list, claims tally:** see E7 and E3 (unchanged). **Full shortcoming cards S1-S8 with options, and the full backlog:** E12 and E17 (unchanged; the Explainer carries a short plain version).

### Reader-check dispositions

The 13 High findings:

| ID | Finding | What was done |
| --- | --- | --- |
| A1 | "standard grouping score" meaningless in Section 1 | Reference box before Section 1 defines the grouping score with its 0-to-1 scale; Section 1 lists three scores with their meaning |
| A2 | "held-out" undefined | Defined in the reference box (exam-paper analogy) and again in Method 6 |
| A3 | "key" and "shortlist" used before explained | Defined in the box; Section 3 step 2 shows which records share which key, with a picture; Method 2 gives the construction |
| A4 | Precision, recall, F1, B-cubed explained three sections before use | Section 8 opens by restating each measure and what doing nothing scores; Result 1 restates precision and recall; the box defines the grouping score |
| A5 | "ID visible on half the records" read as real | Box defines "simulated"; Section 1 says the author hid the ID on purpose; Sections 4 and 8 repeat it where the data is described |
| B1 | Four numbers in one paragraph, apparent paradox | Section 1 lists three numbers with meanings and separates the US result; the "names-only scores below doing nothing" point is explained once, in Section 8 |
| B2 | Three ID ideas never laid out together; thesis shifts in Section 8 | New "The idea, in three parts" in Section 2 says which does most of the work; reused in Sections 1, 3, 5 and the chart in Section 8 |
| B3 | How the clump splits is "magic" in Section 3 | Step 6 states the rule (keep most link strength inside each side) and points to the numbers in Section 5 |
| C1 | 0.027 has no yardstick | Section 1 calls it small; Section 8 gives the ceiling (+0.099 with the ID on every record), per-slice consistency, and the bar chart |
| F1 | "Where this lives in the code" lines in every card | Removed from the narrative; one short list in the back matter |
| F2 | Commit hash, questionnaire version, E-numbers, S-labels | Removed; one pointer to the companion file remains; shortcomings are plain numbered items |
| G1 | Same caveats repeated about eight times | The best-case caveat (UK ID is the answer key) is stated in full once in Section 8, briefly elsewhere; self-praise removed |
| H1 | No picture of the headline result | Added a bar chart (Mermaid xychart) in Section 8 with the cut axis noted |

**Medium and Low findings not applied, or only partly:**
- A16-A19 (jargon): CI and tool detail left the body, but Louvain and modularity stay in the maths cards because a worked example is required for every method; they are explained inline and Maths card 3 is labelled skippable.
- A10, A15 (slices, aliases): explained in Section 4, not simplified further.
- B10 (the 200-record skip in several places): defined once in Method 2; it still appears in Sections 4, 7 and 10 because each concerns a different consequence.
- C6, C8 (line counts; two record counts): line counts mostly removed; the difference between the 28,278-record and 26,596-record sets is not explained in the body (minor).
- D3 (two seating metaphors): kept one for the checker (feuding families) and one for modularity (party); they describe different steps.
- G6-G8 (Sections 11, 12 and back matter are for recruiters and the author): kept because the questionnaire requires them; the Gantt chart, the system-design table and the S6 diagram were dropped.
- H3 (picture of the output column or of half the IDs visible): not added; the demo table and Section 4 cover it.
- Trust note that "the rule holds by construction" is near-circular: Section 2 says the rule is a guarantee by design and the measurement only confirms it on real data; accuracy claims rest on the baselines.
- E1-E6 (worked-example gaps): shortlist keys, which letter fails in Jaro, the thin-chain example and the key derivation were added; the bootstrap range cannot be checked by hand (labelled "I ran this").

### Second reader check (`entity-resolution-gate.readercheck2.md`): dispositions

**Demo ending (H1), verified against the code and `v2_probe.py` output.** Pair scores of record 1 against records 0, 2 and 3 are all exactly 0.9398 (a genuine pair-level tie; records 0 and 3 have identical name and address). Edges in the clump: 0-1 0.9398, 0-2 1.0, 1-2 0.9398, 1-3 0.9398. The network is asymmetric: record 1 has strength 1.8796 to ID-11 records and 0.9398 to the ID-22 record. `_split` returned {0,2},{1,3} from the Louvain call (event `component_split method=louvain reason=tax_conflict`); both parts were ID-consistent, so the recursion returned and the last-resort fallback (`pipeline.py:147-163`) never ran. Had it run, the weight to the ID-11 group (1.8796) exceeds that to ID-22 (0.9398), so record 1 would join A. Louvain optimises modularity without reference to IDs: Q = 0.0078 for {0,2},{1,3}; -0.0303 for {0,1,2},{3}; -0.2217 for {0,1},{2},{3}; seeds 0-9 agree. Group {1,3} mixes A and B, so two records are affected (1 and 3). Whether more A records should count as evidence is a modelling choice, not an established error; hence SR-02 stays Medium ("log it"), not a defect. Explainer Section 3 and Method 5 now say this.

| ID | Finding | Disposition |
| --- | --- | --- |
| H1 | Demo ending contradicts the tie wording | Rewritten as above (Section 3, Method 5 text and figure caption) |
| H2 | Grouping score, B-cubed, why do-nothing is high | Key-terms box defines all three, with the 83% one-name reason; Section 1 points to the box |
| H3 | "Four-step scale in Section 9" absent | Section 9 now states the four steps explicitly in the placement paragraph; Section 1 names them |
| H4 | Gain figures with different baselines; +0.099 unexplained | One "Gain over what?" table in Section 8; +0.099 explained as the ceiling when every record shows its ID |
| H5 | Jargon block in Section 5 | Plain guide at the start; cards 1, 3, 4 marked skippable for engineers; Section 8 explains range and token-sort at first use |

**Inconsistencies checked.**
- *"Same zip" vs a demo table with no zip column:* a real inconsistency in the draft. The demo table now has the real zips from `examples/demo.py` (records 0, 1, 3: 20001; record 2: none; records 4, 5: 10002; record 6: 30003). Records 0 and 1 both have 20001, so "same zip" is correct.
- *US do-nothing 0.50 vs 1,527/4,542:* not an error but a missing step. 1,527/4,542 = 0.336 is B-cubed recall with precision 1; F1 = 2 x 0.336 / 1.336 = 0.503. The cell now says so.
- *0.932 vs 0.928:* two different data sets, not a typo. 0.9277 is the gate study (30 held-out slices, 28,278 records); 0.9316 is the splitting study's `P_full` on a fresh, disjoint set of 30 slices (26,596 records). The text now says so.
- *"Hundreds" of random inputs vs 15 cases:* a real inconsistency. `test_no_cluster_ever_holds_two_tax_ids` uses `max_examples=15`; `test_components_match_networkx` uses 60; the other Hypothesis tests use the default 100. The text now says "15 for the ID-rule test, up to 100 for the others".
- *Trap twins real vs invented:* wording fix; such pairs exist in real data, and the practice data invents them on purpose (box and glossary now agree).
- *Pairs yardstick (M3):* about 13.3 million possible pairs inside the 30 UK slices (30 x C(942.6, 2), my estimate from the average slice size) and about 6,600 true same-company pairs per half (`PROTOCOL_GATE.md`, "What I knew" section); 49 groups against 23,280 companies is about 1 in 475.

### Accuracy review (`entity-resolution-gate.review.md`): dispositions, each re-verified first

Re-run with `v2_verify3.py` (scratchpad): demo with `Config(split="none")` gives groups `[0,0,0,0,1,1,2]` (A and B together), the same as `tax_veto=False`; `results/split/heldout_results.json` has 2, 6 and 0 broken groups for `P_full/none` at q = 0.25, 0.5, 1.0 (veto on, checker off); `P_name` B-cubed 0.8998 with 319 wrong pairs and 77 broken groups, versus `P_addr` 0.9010 (name 0.7 + address 0.3, IDs ignored); G3a (veto alone minus `P_addr`) is +0.00024, +0.00075 and +0.0288 at q = 0.25, 0.5, 1.0; `splink_id@0.5` B-cubed 0.9032 and pair F1 0.003 (almost nothing joined); null name raises `AttributeError`, while `""` and `"  "` run and give singletons.

| # | Finding | Verified? | What was done |
| --- | --- | --- | --- |
| 1 | "Unconditional" and "unbreakable" overclaim | Yes | Guarantee reworded everywhere: holds when the rule and the group checker are both on, IDs are exactly equal text, and input is well formed; 6 broken groups with the checker off is stated in Method 5 |
| 2 | 0.901 row mislabelled "names only" | Yes | Section 1, chart and captions now say "ignoring IDs (names and addresses)"; "names only" kept for the US result, which has no addresses |
| 3 | "Rule adds almost nothing" and "zero broken groups whenever the rule is on" | Yes | Qualified: +0.0007 is at half ID visibility, +0.029 at full visibility; zero holds for rule plus checker; table row relabelled |
| 4 | Empty name crashes | Yes (my own wording error: only null crashes) | Changed to "missing (null) name; blank text is accepted" in Sections 3, 4, 7, 10 and the milestone |
| 5-6 | Author-voice answers beyond AUTHOR_CONTEXT | Yes | Answers reworded to the author's own account (scope, plans, architecture, preferences); a line says he must confirm anything he did himself |
| 7 | Invented reason for the ID-shortlisting default | Yes | Replaced by "I have no written reason; the author must say" |
| 8 | Best role family overstated | Yes | Now "none fits well; the closest is ... only on its evaluation and testing half"; a data-quality or evaluation engineer role named as a better fit |
| 9 | Incident handling "Partly" | Agreed | Moved to Simulated |

Low findings applied: 10 (review identity hedged), 11 (not "declining" but "not tried"), 12 (boilerplate softened, credit-based sentence), 13 (CI wording), 14 (quickstart wording), 15 (baseline wording), 16 (Docker row now "not shown", not built), 17 (embedding-based, not "learned matching"), 18 (cause of below-do-nothing hedged), 19 ("almost nothing"), 20 (stop condition and ordering wording), 21 (analogy limit stated), 23 (opinion labels), 24 (originality hedged). Also applied: 22 (trap-twin box now says only same-name pairs are shown to exist in real data). Skipped: the "11 times" run-time ratio (I measured 8.8 s vs 102 s, about 12; the reviewer 7.5 vs 88.9 s, also about 12; the Explainer says "about 11 times" and was not changed). Disagreement: none of substance; finding 4 was a real error of mine.

**Other findings applied:** M4, M5, M6, M7 (voice reminder in Section 12), M8, M9 (net-effect sentence), M10 (operational terms replaced by plain phrases), M12 and L1 (README, GitHub, CAGE, MLOps glossed), M13, M14, L3. **Not applied:** M11 (effort tags kept), L2, L5, L6 (credit detail in Section 11 is evidence of who built it), L7, L9-L12.


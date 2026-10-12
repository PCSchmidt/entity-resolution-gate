# Protocol: real-name study on a random sample of recipients (written before any sampled name was looked at)

Committed before the sampled recipients' names were downloaded, so none of the choices below can have been made after seeing them. Anything changed later is listed under [Deviations](#deviations). It replaces the alphabetical-prefix pilot ([PROTOCOL_REAL.md](PROTOCOL_REAL.md), [PROTOCOL_BLOCKING.md](PROTOCOL_BLOCKING.md)), whose sampling flaw is described at the top of those documents.

## Why

The pilot read only the first 10,000 awards of each month in recipient-name order, so it sampled names beginning with a digit, a symbol or "A", and over-represented look-alike "Advanced ..." names. Its findings were mixed: the pipeline beat a tuned plain fuzzy matcher on one month and did not on the next, and better blocking did not improve F1. This study asks the same questions on a sample that is random over the whole recipient population.

## What I knew before writing this (stated so it can be discounted)

- The pilot results, including that the pipeline's false merges on the July prefix were mostly clusters of names sharing a long prefix. The **token-sort-only name score** in this study (`pipeline_token_sort`) was designed from that observation, so it is a hypothesis formed on pilot data, not a neutral choice.
- The pilot's recipients are removed from the sampling frame, so no recipient used to form that hypothesis can appear here.
- I have seen **no** names from the new sample. I will see counts (frame size, sample size, records, entities per split) before running anything, because they are needed to report the design.

## Population and sample

- **Frame:** every recipient of a Department of Defense contract award (award types A, B, C and D) in US fiscal year 2024 (2023-10-01 to 2024-09-30), as listed by the USAspending recipient ranking (`spending_by_category/recipient`), paged to the end. Rows with no recipient id (redacted or aggregate) are dropped and counted.
- **Exclusions:** recipients that appear in the pilot's January or July profile files.
- **Sample:** a simple random sample of **3,000** recipients without replacement (Python `random.Random(0)` over the frame sorted by recipient id).
- **Records:** for each sampled recipient, its registry profile is downloaded; one record per distinct name string among the primary name and the alternate names. **Entity = the profile's UEI**, which is the answer key and is never given to a matcher. Recipients without a profile or without a UEI are dropped and counted. Several recipients can share a UEI; their names are merged into one entity.
- **Split:** by entity, a UEI is development if the first byte of `sha256(UEI)` is even, otherwise held-out. All tuning uses development; the held-out half is scored **once**.

Records carry names only (the alternate names have no addresses, and public data has no tax IDs).

## Matchers (each with exactly one tuned number, chosen on development; ties go to the higher value)

1. **Exact normalised name.** Nothing to tune.
2. **Plain fuzzy.** All pairs within a split, link when `token_sort_ratio` of the normalised names is at least `t` (grid 50 to 100, step 1); groups are connected components.
3. **Splink**, one Jaro-Winkler comparison, and 4. **Splink, richer comparisons** (adds exact first token and token overlap): configured as in [PROTOCOL_REAL.md](PROTOCOL_REAL.md) and its deviations, with the fixed prior of 0.001; link when match probability is at least `p` (grid 0.01 to 0.99).
5. **Pipeline variants** (name-only configuration, `w_name=1.0, w_addr=0.0`; score threshold grid 0.70 to 0.99 in steps of 0.01):

| Name | Blocking keys | Name score |
| --- | --- | --- |
| `pipeline_base` | the original keys | larger of Jaro-Winkler and token-sort |
| `pipeline_squash` | original plus space-removed name keys | as above |
| `pipeline_squash_first` | plus the first token | as above |
| `pipeline_squash_first_wide` | plus pair keys from six tokens | as above |
| `pipeline_token_sort` | the original keys | **token-sort only** |

Everything else (block-size cap 200, density rule, Louvain splitting) stays at its default. The pipeline's candidate pairs are returned in sorted order, so every run is deterministic.

## Metrics

Pairwise precision, recall and F1 over all within-split record pairs, and entity-bootstrap intervals (2,000 resamples over held-out entities; paired differences use the same resamples). Two cuts, defined as before: **name-findable recall** (true pairs whose normalised names have token-set ratio at least 50; the rest are renames no string method can recover) and **same-name, different-registration** merges (identical normalised names under different UEIs, which may be one organisation registered twice). For the blocking variants also: **pair completeness** (share of name-findable true pairs that become candidates) and the candidate-pair count relative to `pipeline_base`.

## Pre-stated hypotheses and criteria

- **P1, primary.** `pipeline_base` F1 minus plain-fuzzy F1 on the held-out half, 95% entity-bootstrap interval. Entirely above zero: the pipeline beats a tuned fuzzy matcher on a random sample. Entirely below zero: it is worse. Otherwise: no difference established.
- **S1 to S4, secondary.** Each of the other four pipeline variants minus `pipeline_base`, F1. An improvement is **established** only if the 98.75% interval (Bonferroni for four contrasts) lies entirely above zero. Pair completeness and candidate ratios are reported for the three blocking variants, without a threshold.
- **K4, regression and scale.** Any variant that meets its S criterion must also, on the synthetic benchmark (`scripts/benchmark.py` seeds), lower F1 by at most 0.01 on each of the four standard runs, keep zero tax-ID violations and take at most three times the baseline's time. The pipeline's default configuration changes only if a variant meets both its S criterion and K4. Otherwise the default stays and the finding is reported as a trade-off.
- **D, descriptive.** Precision, recall, F1 and intervals for every matcher, findable recall, the rename ceiling, false positives and same-name false positives. No other comparison is claimed as established.

## My expectation, written down so it can be wrong

- **P1:** I expect no clear advantage for the pipeline over plain fuzzy matching, and it may be worse, given the July pilot. I would not be surprised by a small gap in either direction.
- **S (token-sort score):** I expect `pipeline_token_sort` to improve on `pipeline_base` through higher precision, because it removes the prefix bonus; whether the gain is large enough to clear the corrected interval is uncertain.
- **S (blocking):** I expect pair completeness to rise and F1 to stay flat, as in the pilot.
- **Rename ceiling:** about the same share of true pairs (roughly one in six) will be unrecoverable by any matcher.
- **Random sample structure:** most recipients have a single name, so fewer true pairs per record than in the pilot and a lower share of look-alike clusters.

## Limits, stated in advance

Name-only data, one agency, one fiscal year, contracts only. Recipients are sampled equally, not by dollars, so the sample is dominated by small firms. About 1,500 entities per split; intervals will still be wide for a difference of a point or two. The answer key is the registry's own assignment and can be wrong. The alternate names are a name history, so this tests spelling and renaming drift more than typing errors. The pilot's recipients (a few thousand at most) are absent from the frame, which slightly biases the sample away from recipients that appear in many pilot months. The Splink configuration is hand-set and unsupervised, so Splink results say little about a tuned Splink. The tax-ID constraint and address scoring are not exercised, and scale beyond a few thousand records still rests on the synthetic benchmark. Several variants and grids make this a search, but the held-out half is never used for any choice.

## Design counts (seen before any matcher ran)

Frame: 45,959 recipients (2 rows without a recipient id skipped); 1,019 were pilot recipients and were excluded, leaving 44,940; 3,000 were sampled; one had no profile and was dropped. Records and entities by split, before the exclusion in Deviation 2: development 4,586 records and 1,472 entities, held-out 4,542 records and 1,527 entities.

## Deviations

All three were decided after the **first development run** and **before the held-out half was scored**. Only development data had been looked at. The first run's files are kept in `results/sample/superseded_pairwise_first_run/`.

1. **Why a second look was needed.** The first development run (pairwise F1) gave very low scores (best tuned F1 0.21 to 0.31) and put the pipeline's best thresholds at the very bottom of its grid. Inspecting the development entities showed why: one entity has 256 name strings, a pass-through or aggregate registrant whose alias list holds hundreds of unrelated organisations (credit unions, a county, a consulting firm), and it accounts for **82%** of all true pairs; a second entity lists several different universities as aliases. Pairwise counts grow with the square of an entity's size, so a single registrant swamps every score.
2. **Primary metric changed to B-cubed F1; entities with more than 50 name strings excluded.** B-cubed precision and recall are averaged over records, so an entity's weight grows linearly with its size and one very large entity cannot dominate. All tuning and the primary criteria (P1, S1 to S4) now use B-cubed F1; pairwise precision, recall and F1 are still computed and reported as a secondary. Entities with more than 50 distinct name strings are dropped from both splits (a rule fixed by size alone). In this sample exactly one entity met it (in the development half), leaving development at 4,330 records and 1,471 entities; the held-out half is unchanged (4,542 records, 1,527 entities). Entities with 30 or so aliases of the second kind are kept, since I have no size-only rule that separates them from legitimate large organisations; they are a known source of noise in the answer key.
3. **Pipeline threshold grid widened from 0.70-0.99 to 0.50-0.99.** The first run's best thresholds were 0.70 and 0.71, the lowest values in the grid, so the optimum may lie outside it. This is the same kind of fix made for Splink in the earlier study. The fuzzy grid (50 to 100) and Splink grid (0.01 to 0.99) already contained their optima in the interior.
4. **Splink probability grid extended upward for this study (0.995, 0.999, 0.9999 added).** In the second development run `splink_rich` chose 0.99, the top of its grid, so its optimum may lie outside it. Extended before the held-out half was scored; the earlier study's grid is unchanged. After the extension `splink_rich` chose 0.9999, the new top of the grid (development B-cubed F1 0.893 at 0.99, 0.912 at 0.9999), so its tuned value is still at an edge and its score may be slightly understated. I stopped extending: it is an exploratory comparator and the grid cannot be extended forever. The plain Splink (0.53) and every other matcher chose interior values.

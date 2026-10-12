# Results: entity resolution on real federal-contractor names

Plan: [PROTOCOL_REAL.md](PROTOCOL_REAL.md), pushed before any matcher was run, with two deviations logged before the test split was scored. Synthetic results: [RESULTS.md](RESULTS.md).

**Setup.** January 2024 Department of Defense contract awards, from the public USAspending API. 748 registry entries (UEIs), 2,261 distinct name strings (each UEI's primary name plus the alternate names in its profile). The UEI is the answer key and is never a matcher input. Entities are split by a hash of the UEI: 381 for development, 367 for test (1,138 records). One tuned number per matcher was chosen on development and frozen; the test split was scored once. Records carry names only (no addresses or tax IDs in this data).

## Test results (367 entities, 1,138 records)

| Matcher | Precision | Recall | F1 [95% interval] | F1 minus plain fuzzy [95% interval] |
| --- | --- | --- | --- | --- |
| Exact normalised name | 0.927 | 0.556 | 0.695 [0.624, 0.758] | -0.036 [-0.063, -0.002] |
| Plain fuzzy (token-sort ratio, t=92) | 0.886 | 0.623 | 0.732 [0.650, 0.796] | - |
| Splink, one Jaro-Winkler comparison (p=0.16) | 0.927 | 0.556 | 0.695 [0.624, 0.758] | -0.036 [-0.063, -0.002] |
| Splink, richer comparisons (p=0.98) | 0.897 | 0.592 | 0.713 [0.631, 0.776] | -0.019 [-0.049, +0.011] |
| **entity-resolution-gate, tuned (threshold 0.90)** | 0.876 | 0.675 | **0.763** [0.678, 0.827] | **+0.031 [+0.004, +0.059]** |
| entity-resolution-gate, default (0.93, untuned) | 0.888 | 0.636 | 0.741 [0.653, 0.807] | +0.009 [-0.009, +0.028] |

Intervals are bootstrap over test entities (2,000 resamples); the difference column uses the same resamples for both matchers.

## Against the criteria set in advance

| Criterion | Result |
| --- | --- |
| C1: pipeline beats plain fuzzy (interval above zero) | **Met narrowly for the tuned pipeline** (+0.031, interval starts at +0.004). **Not met for the untuned default** (+0.009, interval spans zero). I had expected it not to be met. |
| C2: Splink beats plain fuzzy | **Not met.** Splink with one comparison is slightly worse (-0.036); the richer variant is not distinguishable (-0.019, interval spans zero). |
| C3: findable and overall recall | Below. |
| C4: where the pipeline's misses come from | Below. |

## What limits every matcher: renames

17% of the true pairs (306 of 1,827) are pairs whose names share almost nothing after normalisation (token-set ratio under 50), such as one company name replaced by another. **Every matcher recovers zero of them.** That caps overall recall near 0.83 for any string-based method, so the recall column should be read against 0.83, not 1.0. Recall on the name-findable pairs (1,521) is 0.668 for exact, 0.748 for plain fuzzy, 0.668 and 0.711 for the single-comparison and richer Splink variants, and **0.811 for the tuned pipeline**.

## Where the pipeline loses recall (post-hoc, not in the protocol)

For the tuned pipeline, true pairs split by whether blocking ever proposed them to the scorer ([scripts/real_posthoc.py](../scripts/real_posthoc.py), [results/real/posthoc_blocking.json](../results/real/posthoc_blocking.json)):

| Pairs | True | Found | Scored, then rejected | Never scored (blocking) |
| --- | --- | --- | --- | --- |
| Name-findable | 1,521 | 1,234 | 73 | **214** |
| Renames | 306 | 0 | 16 | 290 |

Of the 287 findable pairs it misses, **214 (75%) were never put in front of the scorer** and 73 were scored and rejected. Blocking is the larger recall loss here. That 214 is an upper bound on what better blocking could recover, since some of those pairs might still score below the threshold. This was run after the test results were seen and was not tested as a fix.

**Correction.** The first version of this section reported 41 and 246 (86%). It compared record ids with row positions, which differ in this dataset (ids are global across the development and test splits), so it overstated the blocking share; the matcher results above were not affected. See [Deviation 3](PROTOCOL_REAL.md#deviations).

## Precision: a ceiling shared by every method

80 predicted pairs are records with identical normalised names but different UEIs. They count as false positives against the registry, and **every** matcher, including exact matching, produces them, which is why no method exceeds precision 0.927. They may be one organisation registered twice (the registry itself shows such cases), so this ceiling is partly a property of the answer key. Excluding them, the tuned pipeline has 94 false-positive pairs against plain fuzzy's 66: it buys recall with some precision.

## What this does and does not show

- **Shown, narrowly:** on real contractor names, the tuned pipeline scores above a tuned plain fuzzy matcher (+0.031 F1, interval above zero), mostly through higher recall, at a small precision cost. The untuned default is not distinguishable from it.
- **Not shown:** that the pipeline's graph logic is what helps. This data has no tax IDs and no addresses, so the hard constraint and address scoring, the parts the design is built around, were not exercised. The gain may come from the scoring and blocking choices.
- **Not a general claim about Splink.** It was run with a fixed prior and a small hand-set comparison configuration, unsupervised, on a few hundred entities. A larger, tuned Splink model could do better.

## Limits

- One month, one agency, contracts only; 367 test entities, so intervals are wide.
- The variants are the registry's name history, which tests spelling and renaming drift more than typing errors.
- The answer key is the registry's own, and may contain mistakes.
- **Forking paths:** a richer Splink variant was added and the Splink grid widened after the first development run (protocol deviations 1 and 2), and two pipeline variants are reported. The C1 interval lower bound of +0.004 is thin enough that this matters; read C1 as "suggestive", not settled.
- All matchers share the repository's name normaliser.
- Scale beyond a few thousand records still rests on the synthetic benchmark.

## Reproduce

```bash
pip install -e ".[dev,study]"
python scripts/fetch_usaspending.py --out data/usaspending_2024-01.jsonl --start 2024-01-01 --end 2024-01-31
python scripts/enrich_profiles.py --records data/usaspending_2024-01.jsonl --out data/profiles_2024-01.jsonl
python scripts/build_real_dataset.py --profiles data/profiles_2024-01.jsonl --out data/real_records.jsonl
python scripts/run_real.py dev     # writes results/real/frozen.json
python scripts/run_real.py test    # one-shot; refuses to run twice
python scripts/real_posthoc.py     # the blocking breakdown
```

The downloaded data is not committed (public data, fetched on demand). The API is live, so a later download may differ slightly from the January 2024 snapshot used here.

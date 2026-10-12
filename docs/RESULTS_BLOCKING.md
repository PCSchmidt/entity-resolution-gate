# Results: blocking pilot (alphabetical-prefix sample)

> **Sampling correction (found 2026-10-12): this is a pilot on a non-random sample.** Both months were downloaded as the first 10,000 awards in recipient-name order, so every record comes from a name beginning with a digit, a symbol or "A". These numbers describe that prefix only and say little about federal contractor names in general. The random-sample study that supersedes this pilot is [PROTOCOL_SAMPLE.md](PROTOCOL_SAMPLE.md).

Plan: [PROTOCOL_BLOCKING.md](PROTOCOL_BLOCKING.md), pushed before any variant was run, with four deviations logged before the fresh month was scored. Earlier pilot: [RESULTS_REAL.md](RESULTS_REAL.md).

**Setup.** Four blocking variants, each only adding keys to the baseline (`base`; `squash` adds keys on the name with spaces removed; `squash_first` also adds the first token; `squash_first_wide` also builds pairs from six tokens). Each variant's pipeline threshold was tuned on the January development split (381 entities) and frozen. The fresh month was July 2024, keeping only entities absent from January (349 entities, 1,078 records), scored **once**.

## Development split (January)

| Variant | Candidate pairs | Pair completeness (findable true pairs) | Tuned threshold | Dev F1 |
| --- | --- | --- | --- | --- |
| `base` | 3,201 | 0.883 | 0.90 | 0.7424 |
| `squash` | 3,983 | 0.909 | 0.90 | 0.7473 |
| `squash_first` | 13,501 | 0.956 | 0.90 | 0.7473 |
| `squash_first_wide` | 13,788 | 0.965 | 0.90 | 0.7473 |

The pre-registered near-tie rule (earliest variant within 0.005 of the best F1) chose `base`, by a margin of 0.0001. Completeness rose by up to 8 points while F1 rose by half a point, at 4.3 times the candidates.

## Fresh month (July, 349 entities), each at its January-frozen threshold

| Matcher | Precision | Recall | F1 [95% interval] | Candidate pairs | Pair completeness |
| --- | --- | --- | --- | --- | --- |
| Exact normalised name | 0.923 | 0.354 | 0.512 [0.324, 0.763] | | |
| Plain fuzzy (t = 92) | 0.856 | 0.404 | 0.549 [0.360, 0.797] | | |
| Pipeline, `base` | 0.567 | 0.459 | 0.507 [0.353, 0.684] | 15,694 | 0.883 |
| Pipeline, `squash` | 0.545 | 0.465 | 0.502 [0.353, 0.679] | 17,203 | 0.937 |
| Pipeline, `squash_first` | 0.543 | 0.465 | 0.501 [0.352, 0.678] | 26,977 | 0.939 |
| Pipeline, `squash_first_wide` | 0.543 | 0.465 | 0.501 [0.352, 0.678] | 28,595 | 0.945 |

Contrasts against `base` (entity bootstrap, 2,000 resamples):

| Variant | F1 difference [95%] | F1 difference [98.3%, corrected for three contrasts] | Completeness difference [95%] | Candidates |
| --- | --- | --- | --- | --- |
| `squash` | -0.005 [-0.041, +0.010] | [-0.054, +0.013] | +0.055 [+0.005, +0.128] | 1.10x |
| `squash_first` | -0.006 [-0.043, +0.010] | [-0.057, +0.012] | +0.056 [+0.006, +0.130] | 1.72x |
| `squash_first_wide` | -0.006 [-0.043, +0.010] | [-0.057, +0.012] | +0.062 [+0.007, +0.145] | 1.82x |

## Against the criteria set in advance

| Criterion | Result |
| --- | --- |
| K1, pair completeness | Rose by 5.5 to 6.2 points; the 95% interval clears zero only barely (lower end +0.005 to +0.007). |
| K2, F1 improvement (corrected interval above zero) | **Not met** for any variant. Every point estimate is slightly negative. |
| K3, against plain fuzzy | The baseline pipeline is **below** plain fuzzy here (-0.042, 95% interval -0.170 to +0.013, spans zero). |
| K4, synthetic regression | Not run: no variant was adopted. It moves to the new study. |
| K5, cost | 1.10x to 1.82x candidate pairs. |

My written expectation was a clear rise in completeness and only a small F1 gain, with K2 possibly unmet. Completeness rose less than hoped on the fresh month and F1 did not rise at all.

## What the pilot does and does not show

- **Better blocking did not improve F1 here.** The pairs the new keys recover are mostly proposed and then not linked (on July, 58 findable true pairs were candidates but not linked for the baseline, 116 for `squash`), so the scorer, not the blocker, decides.
- **The January advantage over plain fuzzy did not carry over.** On January the tuned pipeline beat plain fuzzy by 0.031 F1. On July's fresh entities the same frozen configuration scored 0.042 below it (interval spanning zero), with precision down to 0.567. The 869 false-positive pairs come largely from a few clusters of look-alike names such as "advanced technology ...", "advanced finishing systems / fluid systems / office systems": the Jaro-Winkler part of the name score rewards a long shared prefix, so these chain together at the January-tuned threshold. A prefix sample makes this worse than it would be on a random draw, because it concentrates names that begin alike. That explanation is a post-hoc reading of the largest false clusters; it is the hypothesis the new study tests with a pre-registered token-sort-only score.
- **Not shown:** that any of this holds on a random sample, which is why the study was redone.

## Reproduce

```bash
python scripts/run_blocking.py dev        # writes results/blocking/frozen.json
python scripts/run_blocking.py heldout    # one-shot; refuses to run twice
```

Data come from [scripts/fetch_usaspending.py](../scripts/fetch_usaspending.py), which reads only the alphabetical prefix described above.

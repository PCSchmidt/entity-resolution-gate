# Results

Synthetic data only (`entity_resolution_gate.synth.generate`: typos, case, trading prefixes and suffixes, address drift, 40% of entities without a tax ID, 10% "trap" twins with the same name and address but a different tax ID). Ground truth is `entity_id`.

Protocol: the threshold (0.93) and the density rule were chosen on seed 1 (1000 entities). The rows below use other seeds. Reproduce with `python scripts/benchmark.py` (one machine, single thread, wall-clock).

| Entities | Records | Precision | Recall | F1 | Tax-ID violations | Seconds |
|---|---|---|---|---|---|---|
| 1000 (seed 2) | 2021 | 0.858 | 0.973 | 0.912 | 0 | 0.3 |
| 1000 (seed 3) | 1964 | 0.856 | 0.972 | 0.910 | 0 | 0.2 |
| 5000 (seed 2) | 9870 | 0.816 | 0.977 | 0.889 | 0 | 4.4 |
| 20000 (seed 2) | 39369 | 0.770 | 0.842 | 0.804 | 0 | 6.7 |

Pairwise precision/recall/F1 against `entity_id`.

## What the numbers say

- Tax-ID violations are 0 in every run. This holds by construction (the fallback makes an inconsistent cluster impossible) and is property-tested, so it does not depend on tuning.
- Precision is capped near 0.86 at small scale by the trap twins' records that carry no tax ID: identical name and address, so nothing in the data separates them.
- Quality falls at 20k entities. The synthetic name space has only 4,032 base names, so many distinct vendors collide. This is partly a generator limit and partly a real scaling cost; the two are not separated here.

## Development findings (kept because they changed the design)

1. Naive threshold 0.82 gave precision 0.61. Weak links chained unrelated vendors into one component; with null tax IDs the hard constraint never fires. Added density-triggered Louvain splitting and swapped token-set for token-sort ratio.
2. Single-token blocking keys dropped recall to 0.005 at 5k entities (all blocks over the cap were skipped). Token-pair keys fixed it.

## Not measured

Real federal contracting data, 100k+ records, embedding-based blocking, comparison to Splink, F1-vs-latency curves.

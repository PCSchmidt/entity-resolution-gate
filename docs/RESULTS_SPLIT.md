# Results: does the graph-splitting step earn its place?

Plan: [PROTOCOL_SPLIT.md](PROTOCOL_SPLIT.md), pushed before any variant ran on the new data, one deviation logged before the held-out scoring. A fresh set of 60 dense name slices from UK Companies House (30 development, 30 held-out; 26,596 held-out records, 22,111 companies), disjoint from the gate study's companies. Thresholds tuned on development, frozen, held-out scored **once** (`results/split/heldout_results.json`). Bootstrap over slices, same resamples on both sides of each contrast.

> **Read this first.** The registry ID is a UK company number and its visibility is simulated; this is one register and one author. The finding below is about this pipeline on this data: **at the threshold tuned for accuracy the graph step does almost nothing for F1, and its value is the guarantee and robustness to a badly set threshold.**

## Results at the tuned thresholds (all variants tuned to 0.99)

| Pipeline, split mode (q = 0.5) | B-cubed F1 [95%] | False-merge pairs | Clusters with two visible IDs |
| --- | --- | --- | --- |
| `P_full`, `louvain` (as published) | 0.9316 [0.9274, 0.9357] | 237 | **0** |
| `P_full`, `tax_only` | 0.9316 [0.9274, 0.9357] | 237 | **0** |
| `P_full`, `none` (components only) | 0.9315 [0.9273, 0.9356] | 257 | **6** |
| `P_addr` (no IDs), `louvain` | 0.9052 [0.8995, 0.9108] | 255 | 51 (IDs ignored) |
| `P_addr` (no IDs), `none` | 0.9051 [0.8995, 0.9108] | 267 | 50 (IDs ignored) |

- **S1 (primary):** `louvain` minus `none`, `P_full`, q = 0.5: **+0.00013** [+0.00002, +0.00029], 4 of 30 slices better, none worse, 26 identical. Technically above zero, but it is 0.013 percentage points: negligible. The same at q = 0.25: +0.00006 [+0.00002, +0.00013]; at q = 1.0 exactly 0.
- **S2 (the guarantee):** without the graph step the registry-ID rule is **broken**: 6 clusters with two visible IDs at q = 0.5 (2 at q = 0.25, none at q = 1.0). With either `louvain` or `tax_only`: 0. The edge-level veto alone checks pairs, so a record with no visible ID can bridge two companies whose IDs are visible. The step also prevents 20 false-merge pairs at q = 0.5.
- **S3 (sparse chains, no IDs):** `P_addr` `louvain` minus `none`: +0.00003 [0, +0.00009] (97.5%): nothing.
- **S4:** `louvain` minus `tax_only`: 0.0000 [0, 0] at q = 0.5. The sparse-chain criterion adds nothing once IDs are in play at the tuned threshold.
- **Activity:** at q = 0.5 the step split 6 components containing 22 of 26,596 records (0.08%); five of the six needed the fallback partition by tax ID.

## Why so little: the tuned threshold leaves the step nothing to do

Every variant's tuned threshold is 0.99, the grid's ceiling (the earlier gate study chose the same): at that point the pipeline links only near-identical names, so the thresholded graph is almost all small, clean components. That is a reason to ask what the step does at looser, untuned thresholds (Deviation 1, held-out, descriptive, q = 0.5):

| Threshold (untuned) | Variant | B-cubed F1 | False-merge pairs | Clusters with two visible IDs | Components split |
| --- | --- | --- | --- | --- | --- |
| 0.90 | `P_full`, `louvain` | 0.8891 | 5,462 | 0 | 297 |
| | `P_full`, `tax_only` | 0.8884 | 5,953 | 0 | 278 |
| | `P_full`, `none` | 0.8531 | 140,679 | 278 | 0 |
| | `P_addr`, `louvain` | 0.8339 | 12,925 | 971 | 142 |
| | `P_addr`, `none` | 0.8190 | 191,320 | 518 | 0 |
| 0.80 | `P_full`, `louvain` | 0.8048 | 19,738 | 0 | 106 |
| | `P_full`, `tax_only` | 0.8035 | 20,895 | 0 | 102 |
| | `P_full`, `none` | **0.6035** | **3,085,343** | 102 | 0 |
| | `P_addr`, `louvain` | 0.6473 | 63,359 | 1,787 | 62 |
| | `P_addr`, `none` | 0.5750 | 3,297,315 | 189 | 0 |

At 0.80 the graph step is worth **+0.20 F1** for `P_full` (29 of 30 slices improved) and +0.07 for `P_addr`; at 0.90, +0.036 and +0.015. The step is a **safety net**: with a loose threshold, chains of similar names merge into giant clusters (3 million false-merge pairs without it), and Louvain breaks them up. The sparse-chain criterion alone is worth +0.0013 (0.80) and +0.0007 (0.90) over `tax_only` for `P_full`. The ID-conflict criterion does the work whenever IDs are visible; the chain criterion is what rescues the no-ID pipeline.

## Against the expectations written in advance

| Expectation | Outcome |
| --- | --- |
| S1: absolute value under 0.003, interval includes zero | Magnitude right (+0.00013); **the interval excludes zero** (lower bound +0.00002) |
| S2: `none` produces at least 5 rule-breaking clusters at q = 0.5; the others zero | **Yes**: 6 and 0 |
| S3: +0.001 to +0.005 | **Wrong**: +0.00003 (the step has almost nothing to do at the tuned threshold) |
| S4: under 0.002 | Yes: 0.0000 |
| The step touches under 5% of records at q = 0.5 | Yes: 0.08% |

## What this does and does not show

- **Shown:** the graph step is not what produces the +0.027 gain of the gate (that comes from using the ID as evidence, as found before); it is what makes the "never two IDs in one cluster" guarantee true, and it makes the pipeline far less sensitive to a poorly chosen threshold.
- **Not shown:** that Louvain specifically is the best way to split (no other splitter was tried); results on real tax IDs; that a lower tuned threshold would be better with a different scoring function. The tuned threshold sits at the grid's ceiling, so a higher grid might move the optimum.
- **Not claimed:** that the step is unnecessary. It is cheap, active on 0.08% of records, and the only thing standing between the pipeline and a broken guarantee.

## Process notes and limits

1. Deviation 1: fixed-threshold rows added after the development stage (all thresholds 0.99) and before held-out scoring.
2. The activity table's reason labels: "tax_partition" is the guaranteed fallback that partitions a component by tax ID when Louvain does not split it at depth zero; "tax_conflict" and "sparse_chain" are Louvain splits.
3. The new slices came from the same register and the same construction as the gate study, with 1,248 companies removed because they also appeared in the earlier set.
4. Limits as in the protocol: one register, simulated visibility, one author, a threshold grid capped at 0.99.

## Reproduce

```bash
python scripts/build_gate_dataset.py --parquet data/companies_house/companies.parquet --out data/gate_records_b.jsonl --slices 60 --width 800 --seed 2 --exclude-from data/gate_records.jsonl
python scripts/run_split_ablation.py dev       # tune and freeze
python scripts/run_split_ablation.py heldout   # one-shot
```

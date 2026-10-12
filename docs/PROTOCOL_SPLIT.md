# Protocol: does the graph-splitting step earn its place? (written before any variant was run on the new data)

## Why

[RESULTS_GATE.md](RESULTS_GATE.md) credits the registry-ID gate for a +0.027 B-cubed F1 gain and a guarantee of zero rule-breaking clusters, and its Limits say the **graph-splitting (Louvain) step was not ablated**. The pipeline does two things after thresholding edges: it blocks edges between records with different registry IDs, and then, for every connected component, it splits the component with Louvain community detection if the component contains two different IDs *or* looks like a sparse chain (edge density below 0.5). This study asks how much of the result depends on that step, and whether the "guarantee" would hold without it.

## What I knew before writing this

From the gate study: on held-out slices the full gate had 0 clusters with two visible IDs, while the no-ID pipeline had 49 to 77. I have not looked at what happens if the splitting is switched off, and I have not looked at the new data below.

## Variants (differ only in `Config.split`; everything else as in the gate study)

| Split mode | What the graph step does |
| --- | --- |
| `louvain` | the pipeline as published: split a component on an ID conflict or a sparse chain |
| `tax_only` | Louvain only to repair an ID conflict; the sparse-chain criterion is switched off |
| `none` | connected components of the thresholded graph, no splitting (edge-level veto stays) |

Pipelines: `P_full` (veto + positive ID evidence + ID blocking, the gate as designed) in all three modes at q = 0.25, 0.5 and 1.0; and `P_addr` (the no-ID pipeline) in `louvain` and `none` at q = 0.5, which isolates the sparse-chain criterion because no IDs are used. q is the probability that a record's registry ID is visible, simulated exactly as in the gate study; the primary level is q = 0.5.

## Data: a fresh set of slices

The same construction as the gate study (`scripts/build_gate_dataset.py`: 60 random, non-overlapping contiguous slices of 800 name strings from the sorted UK Companies House name population), with **seed 2** instead of 0, so the slices differ from the earlier 60. Companies that also appear in the earlier dataset are dropped (1,248 companies; those slices partly overlapped the earlier ones), and companies falling in more than one new slice are dropped (25). Slices are split at random into 30 development and 30 held-out (seed 3). Development: 28,192 records, 23,136 companies; held-out: 26,596 records, 22,111 companies. The company number is the answer key and the registry ID; the data stay local (Companies House licence statement not found, research use only) and only derived numbers are committed. **The held-out slices of the earlier study are not reused.**

## Procedure

1. Commit this protocol before running anything.
2. **Development:** for each variant and q, tune the pipeline threshold with the same coarse-to-fine search as the gate study (coarse 0.60 to 0.96 step 0.04, then fine within 0.03 of the best, ties to the higher value), objective B-cubed F1 on the development slices. Freeze.
3. **Held-out:** score the 30 held-out slices **once**; the runner refuses to overwrite its result file.

## Metrics

B-cubed F1 (primary), precision, recall, pairwise F1, false-merge pairs, rename-pair recall, and the number of output clusters that contain two different **visible** IDs. Intervals: bootstrap over **slices** (2,000 resamples), the same resamples for both sides of every contrast, plus the number of slices improved and worsened. Split activity: the number of components the graph step split, the records in them, and the reasons (ID conflict or sparse chain), from the audit log.

## Contrasts and hypotheses (stated now, with the interval each is judged by)

- **S1 (primary).** `P_full/louvain` minus `P_full/none` at q = 0.5, B-cubed F1, 95% interval. Entirely above zero: the graph step improves F1. Entirely below: it hurts. Otherwise: no difference established.
- **S2 (the guarantee).** The count of clusters with two visible IDs under each mode. By construction `louvain` and `tax_only` should give zero; the question is whether `none` gives a non-zero count, i.e. whether the edge-level veto alone is enough.
- **S3 (sparse chains without IDs).** `P_addr/louvain` minus `P_addr/none` at q = 0.5, 97.5% interval (two contrasts share the correction with S4).
- **S4.** `P_full/louvain` minus `P_full/tax_only` at q = 0.5, 97.5% interval: does the sparse-chain criterion add anything once IDs are in play.
- Descriptive only: the same contrasts at q = 0.25 and 1.0, and `tax_only` minus `none`.

## Expectations, written so they can be wrong

- **S1:** a small effect, absolute value under 0.003, not established (interval includes zero).
- **S2:** `none` produces **some** rule-breaking clusters (at least 5 across the 30 slices at q = 0.5): a record without a visible ID can bridge two companies whose IDs are visible, and the edge-level veto only checks pairs. `louvain` and `tax_only` produce zero.
- **S3:** a small positive effect of 0.001 to 0.005 whose interval may include zero. Splitting chains should help a little where lookalike names form sparse chains.
- **S4:** under 0.002 in absolute value; the ID conflict repair does the work.
- Split activity: the graph step touches fewer than 5% of records at q = 0.5.

## Limits, stated in advance

One register (UK Companies House), where the registry ID is a company number and visibility is simulated. Louvain's seed is fixed (0) and its community structure is not tuned. Name-history records share the answer key, so a sparse chain is partly an artefact of how this dataset represents renames. The "none" mode keeps the edge-level veto; it is not a mode without any use of IDs. One author, who wrote the pipeline.

## Deviations

1. **Fixed-threshold sensitivity rows added after the development stage and before any held-out scoring (2026-10-12).** Development tuning chose the threshold 0.99 for every variant (the same value the earlier gate study chose), at which the thresholded graph keeps only near-identical names, so the graph step has almost nothing to act on: development B-cubed F1 differs between the modes by at most 0.0002 (`P_full` q = 0.5: 0.9260 louvain, 0.9260 tax_only, 0.9258 none; `P_addr`: 0.8993 against 0.8992). I therefore also score all five variants on the held-out slices at **fixed, untuned thresholds 0.80 and 0.90** (q = 0.5 only), as descriptive rows that show what the step does when edges are plentiful. They are not hypotheses and are not used to choose anything. S1 to S4 are unchanged and still judged at the tuned thresholds.

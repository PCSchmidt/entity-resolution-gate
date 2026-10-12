# Results: does the hard registry-ID rule matter? (UK company register)

Plan: [PROTOCOL_GATE.md](PROTOCOL_GATE.md), pushed before any matcher was run, with four deviations logged after the development stage and **before the held-out slices were scored**.

**Setup.** UK Companies House snapshot of 2026-10-01 (5.7 million live companies). The answer key is the company number. A record is one name string (current name or a previous name) of a company; the registered-office address is attached only to the current-name record. Sixty random contiguous slices of 800 name strings, sorted alphabetically, were taken; each company with a name in a slice contributes **all** its names, so name histories are intact and lookalike neighbours are present at full density. Thirty slices are development, **30 held-out (28,278 records, 23,280 companies)**, and each slice is a separate deduplication job. The registry ID is visible on a record with probability q, fixed per record; the primary level is **q = 0.5**. Thresholds were tuned on development, the held-out slices were scored once, and intervals resample the 30 held-out slices (2,000 resamples).

> **What the identifier is.** It is a registry company number, not a tax ID. It plays the same role the design assumes (a verified identifier that two different entities never share). Visibility at probability q is a simulation, not a measurement of any real system. This study says nothing about EINs or other tax identifiers.

## Held-out results at q = 0.5

B-cubed F1 is the primary metric (precision and recall averaged over records). **Read it against the no-merge row**: 83% of companies have a single name string, so a matcher that links nothing already scores 0.903. Pairwise F1, which counts only linked pairs and so sees what is missing, is shown beside it.

| Matcher | B-cubed precision | B-cubed recall | **B-cubed F1** [95%] | Pairwise F1 | Record pairs wrongly merged | Clusters with two visible IDs | Recall on renames |
| --- | --- | --- | --- | --- | --- | --- | --- |
| No merge (reference) | 1.000 | 0.823 | 0.903 [0.897, 0.909] | 0.000 | 0 | 0 | 0.000 |
| Exact normalised name | 0.991 | 0.824 | 0.900 [0.894, 0.906] | 0.011 | 270 | 60 | 0.000 |
| Plain fuzzy | 0.990 | 0.825 | 0.900 [0.894, 0.906] | 0.017 | 289 | 67 | 0.000 |
| Pipeline, name only (`P_name`) | 0.989 | 0.825 | 0.900 [0.894, 0.906] | 0.022 | 319 | 77 | 0.000 |
| Pipeline, name + address (`P_addr`) | 0.992 | 0.825 | 0.901 [0.895, 0.907] | 0.022 | 246 | 49 | 0.000 |
| `P_addr` + veto only (`P_veto`) | 0.994 | 0.825 | 0.902 [0.896, 0.908] | 0.022 | 180 | **0** | 0.000 |
| `P_addr` + same-ID evidence only (`P_match`) | 0.991 | 0.871 | 0.927 [0.923, 0.932] | 0.405 | 339 | 48 | 0.259 |
| **`P_addr` + veto + same-ID evidence (`P_full`)** | 0.993 | 0.870 | **0.928** [0.923, 0.932] | 0.408 | 246 | **0** | 0.258 |
| Splink, unsupervised, with registry ID | 1.000 | 0.823 | 0.903 [0.897, 0.909] | 0.003 | 0 | 0 | 0.000 |
| Splink, supervised on development labels | 0.984 | 0.868 | 0.923 [0.917, 0.928] | 0.349 | 1,349 | 29 | 0.255 |

"Recall on renames" is the share of true pairs whose names share almost nothing (token-set ratio under 50), which no name similarity can recover. "Clusters with two visible IDs" counts output clusters that put together records showing two different registry IDs, which the rule forbids.

## Against the criteria set in advance

| Criterion | Result |
| --- | --- |
| **G1, primary**: `P_full` minus `P_addr`, B-cubed F1, 95% interval above zero | **Met.** +0.0267 [+0.0248, +0.0288]. The gate improved **all 30 held-out slices**, by +0.016 to +0.037 (median +0.026). On pairwise F1 the gap is +0.386 [+0.374, +0.398]. |
| **G2**: the guarantee | **Confirmed on real data.** The veto variants have **0** clusters with two visible IDs; the variants without it have 48 to 77. The veto prevents 66 wrongly merged record pairs without the positive evidence (`P_addr` 246 to `P_veto` 180) and 93 with it (`P_match` 339 to `P_full` 246). |
| **G3a**: veto alone, 97.5% interval above zero | Technically met but **negligible**: +0.0007 [+0.0005, +0.0010]. I had expected it not to be established. |
| **G3b**: same-ID evidence alone | **Met**: +0.0261 [+0.0238, +0.0284]. This is where nearly all of G1 comes from. |
| **G4**: `P_full` minus unsupervised Splink | +0.0245 [+0.0225, +0.0266]; but see the next row. |
| **G4b**: `P_full` minus supervised Splink | +0.0050 [+0.0034, +0.0068]. At q = 1.0 the two tie exactly. |
| **G5**: address, `P_addr` minus `P_name` | +0.0012 [+0.0008, +0.0016]: a gain, but about a tenth of a point. I had expected none or a loss. |

**My written expectations against the outcome.** G1 met: right, but larger than I guessed (2.7 points, not 0.5 to 2), and mostly from positive evidence: right. Zero violations for the veto and tens of prevented merges: right. Veto alone not established: **wrong** (established, but tiny). `splink_id` within a point of `P_full`: right only for the supervised version; the pre-registered unsupervised one was 2.5 points behind because it learned the wrong solution. No gain from address: wrong (a tiny gain). Gains grow with q: right.

## How the effect depends on how often the ID is visible

| q | `P_full` minus `P_addr`, B-cubed F1 [95%] | Rename recall of `P_full` | What dominates |
| --- | --- | --- | --- |
| 0.25 | +0.0074 [+0.0065, +0.0082] | 0.066 | same-ID evidence, tiny |
| 0.5 | +0.0267 [+0.0248, +0.0288] | 0.258 | same-ID evidence |
| 1.0 | +0.0990 [+0.0930, +0.1052] (F1 1.000) | 1.000 | a ceiling: the ID alone identifies the company |

Rename recall tracks q squared (0.0625, 0.25, 1.0), as it should: a rename pair is recovered only when **both** its records show the ID. The **veto** matters only when it can see IDs on both records of a lookalike pair, so it is negligible at q of 0.5 or less and large at q = 1.0 (+0.029 on its own, where it lets the tuned threshold drop from 0.99 to 0.58 with no wrong merges). The q = 1.0 results are a best case, not a test of the gate against similarity.

## Two things worth knowing

- **Name similarity alone does not beat linking nothing here.** Tuned fuzzy matching is 0.0032 below the no-merge row [-0.0038, -0.0026] and `P_addr` 0.0021 below it [-0.0028, -0.0014]. Most true pairs are renames, and the numbered-series lookalikes ("GG 1 2", "Partners Access 3 LP") punish any loose threshold, so every tuned name-only threshold sits at the top of its grid. The gate's gain therefore comes from the identifier, not from better name matching.
- **Unsupervised Splink failed on this data, and the supervised one is the fairer comparator.** In lookalike-dense data, expectation-maximisation treated name-similar pairs with *different* IDs as matches and concluded matches usually disagree on the ID (`m` = 0.0007), so it linked nothing. Estimated from labelled development pairs it works, and gets within 0.5 points of the gate. It does so with 1,349 wrongly merged pairs and 29 clusters that break the ID rule, which the gate's hard veto rules out by construction.

## What this does and does not show

- **Shown:** where a verified identifier exists on a fraction of records, using it as certain evidence and as a hard veto improves entity resolution on real company names, consistently across slices; the improvement is mostly the positive evidence; the veto delivers a guarantee (zero rule-breaking clusters, tens of prevented false merges) and matters little for F1 unless the identifier is common; and a well-trained probabilistic model gets most of the F1 but not the guarantee.
- **Not shown:** that this holds for tax IDs, US data or any real record collection (the visibility rate is simulated and the identifier is a company number); that the graph-splitting step (Louvain) matters, since I did not ablate it separately; or that the 0.5-point lead over a supervised Splink would survive a better-tuned Splink.

## Deviations and forking paths

Four deviations were logged before the held-out slices were scored: a no-merge reference row, a note that several tuned thresholds sit at the top of their grids, a note that q = 1.0 is a ceiling, and the supervised Splink variant. The gate-versus-Splink conclusion rests on that last choice. Twenty matcher configurations are compared, and the Bonferroni interval covers only the two decomposition contrasts.

## Limits

UK live companies only; the identifier is a company number; visibility is simulated; the dense-slice design keeps local lookalike density but is not a uniform sample and not the whole-register scale; only 30 held-out slices, so intervals are not narrow for effects under a tenth of a point; previous names carry no address, which understates address evidence; the repository's normaliser does not strip UK suffixes ("limited", "plc"); I did not find a licence statement on the Companies House pages I could read, so the data are used for research only, never committed.

## Reproduce

```bash
pip install -e ".[dev,study]"        # needs the downloaded Companies House snapshot in data/companies_house/
python scripts/build_gate_dataset.py --parquet data/companies_house/companies.parquet --out data/gate_records.jsonl --slices 60 --width 800 --seed 0
python scripts/run_gate.py dev        # tunes on the 30 development slices, writes results/gate/frozen.json
python scripts/run_gate.py heldout    # one-shot; refuses to run twice
```

The snapshot (`BasicCompanyDataAsOneFile-2026-10-01.zip`) is converted to Parquet with the column header stripped of stray spaces; the download page is <https://download.companieshouse.gov.uk/en_output.html>. Later snapshots will differ.

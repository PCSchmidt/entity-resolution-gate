# Protocol: does the hard registry-ID rule matter? A test on UK company register data (written before any matcher was run on it)

Committed before the first matcher result, so none of the choices below can have been made after seeing scores. Anything changed later is listed under [Deviations](#deviations). Earlier studies are in [PROTOCOL_SAMPLE.md](PROTOCOL_SAMPLE.md) and [RESULTS_SAMPLE.md](RESULTS_SAMPLE.md); read those first.

## Why

This repository's design rests on one idea: a similarity score may *propose* that two records are the same entity, but a hard rule must be able to *veto* it, and a verified identifier should count as certain evidence. The real-name study on USAspending data could not test that, because public US contract data has no tax IDs, so I could not say whether the pipeline's lead over plain fuzzy matching came from the gate or from its scoring and blocking. This study tests the gate directly, on public data where a verified identifier exists.

## Data and what the identifier is

- **Source:** the UK Companies House free company data snapshot of 2026-10-01 (all live companies, 5,704,712 rows). It lists each company's current name, up to ten previous names, a registered-office address and a unique **company number**.
- **The identifier is not a tax ID.** It is the registry's company number. It plays the same role the design assumes (a verified identifier that two different entities never share), and I call it the **registry ID**. The pipeline's `tax_id` field simply carries it. This study says nothing about EINs or other tax identifiers.
- **Answer key:** the company number. An entity is one company; a record is one name string of that company.
- **Licence and handling:** I did not find a licence statement on the pages I could read, so the download is used for research only. It is fetched on demand into a git-ignored folder and **never committed**; only derived numbers are in the repository. The data are companies, not individuals.

## What I knew before writing this (stated so it can be discounted)

I looked at population statistics only, no matcher outputs: 9.3% of companies have at least one previous name; 6.0% of companies have a current name that collides with another company's name after normalisation; 2.4% sit in numbered series such as "GG 1 2"; the snapshot file is sorted alphabetically by company name; and, in the sampled slices described below, each half has about 28,000 records, about 3,900 multi-name companies, about 6,600 same-company pairs, about 200 to 240 cross-company pairs with identical normalised names, and about 27% of companies share a registered address with another in-sample company. The repository's normaliser does not strip the UK suffixes "limited", "plc" or "llp".

## Sample: dense name neighbourhoods

A uniform sample would dilute exactly the cases the veto exists for (keeping 3% of companies keeps about 0.1% of colliding pairs), and the file is alphabetical, so a prefix would be biased. So:

1. Every name string (current and previous) of every company is normalised (lower-case, non-alphanumerics to spaces) and the whole population is sorted by that string: 6,353,170 strings.
2. **60 random, non-overlapping, contiguous slices of 800 strings** are chosen (seed 0).
3. A company belongs to a slice if **any** of its strings falls inside it. It then contributes **all** of its strings, so its name history is intact, and every lookalike neighbour inside the slice is present at full density. Companies that fall in more than one slice (32) are dropped.
4. The registered-office address (street, town, postcode) is attached **only to the current-name record**; a previous name has no known historical address.
5. Slices are split at random into **30 development and 30 held-out** slices (seed 1). **Each slice is a separate deduplication job**: matchers never link records across slices. All tuning uses development; the held-out half is scored once.

## Simulating partial ID availability

Real record collections have the identifier on only some records. For each record independently, the registry ID is **visible** with probability q, using a fixed per-record hash so that the records visible at q = 0.25 are a subset of those visible at 0.5, which are a subset of those at 1.0. The study runs q = **0.25, 0.5 and 1.0**; the **primary level is q = 0.5**. At q = 0 every ID-using variant equals its no-ID counterpart, so q = 0 is not run separately. This visibility rate is an assumption, not a measurement of any real system.

## Matchers (each tuned on development; ties go to the higher value)

| Name | Uses | Tuned number |
| --- | --- | --- |
| `exact` | normalised name equality | none |
| `fuzzy` | `token_sort_ratio` of normalised names, connected components | threshold, grid 50 to 100 step 1 |
| `splink_id` | Splink Fellegi-Sunter model with a Jaro-Winkler name comparison (0.92, 0.80), exact postcode, and exact registry ID (a missing ID is a neutral level); blocking within the slice on first token, first three characters, or equal ID; fixed prior 0.001 | match probability, grid 0.01 to 0.99 step 0.01 plus 0.995, 0.999, 0.9999 |
| `P_name` | pipeline, name only (`w_name=1, w_addr=0`), registry ID ignored | pipeline threshold |
| `P_addr` | pipeline, name and address (`w_name=0.7, w_addr=0.3`), registry ID ignored | pipeline threshold |
| `P_veto` | `P_addr` plus the **veto** (two different visible IDs can never be one entity) | pipeline threshold |
| `P_match` | `P_addr` plus **positive evidence** (equal visible IDs score 1.0 and are proposed by ID blocking) | pipeline threshold |
| `P_full` | `P_addr` plus both: the gate as designed | pipeline threshold |

`P_veto`, `P_match`, `P_full` and `splink_id` are run at each q; the others do not depend on q. The pipeline threshold is tuned by a fixed coarse-to-fine search on development: a coarse grid of 0.60 to 0.96 in steps of 0.04, then a fine grid in steps of 0.01 within 0.03 of the best coarse value. Blocking is the original name keys (plus ID keys where stated). A missing address on either record is no evidence: the pair is scored on name alone.

## Metrics

**Primary: B-cubed F1** (precision and recall averaged over records), as in the random-sample study. Pairwise precision, recall and F1 are reported alongside. For the registry-ID guarantee: the number of output clusters that contain two different **visible** IDs, and the number of **false-merge pairs** (record pairs from different companies placed in one cluster). Recall on **rename pairs** (true pairs whose normalised names have token-set ratio below 50, which no name-only matcher can recover) is reported separately.

**Intervals:** because records within a slice are not independent, the bootstrap resamples **slices** (2,000 resamples over the 30 held-out slices); every difference uses the same resamples for both matchers. A per-slice table is also reported.

## Pre-stated hypotheses and criteria (at q = 0.5 unless stated)

- **G1, primary.** `P_full` minus `P_addr`, B-cubed F1, 95% slice-bootstrap interval. Entirely above zero: using the registry ID through the gate improves F1. Entirely below: it hurts. Otherwise: no difference established.
- **G2, the guarantee.** `P_veto` and `P_full` should show **zero** clusters with two visible IDs by construction; I will confirm on real data. The counts for `P_name`, `P_addr` and `P_match`, and the false-merge pairs the veto prevents, are reported.
- **G3, decomposition.** `P_veto` minus `P_addr` (the veto alone) and `P_match` minus `P_addr` (positive evidence alone); an effect is established only if the 97.5% interval (Bonferroni for two) is entirely above zero.
- **G4, against probabilistic use of the same ID.** `P_full` minus `splink_id`, 95% interval.
- **G5, address.** `P_addr` minus `P_name`, 95% interval (address can help, or hurt, because formation agents put many companies at one address).
- **D, descriptive.** Everything above at q = 0.25 and 1.0; all matchers' precision, recall and F1; rename-pair recall; per-slice results.

## My expectation, written down so it can be wrong

- **G1:** met, but small at q = 0.5 (roughly half a point to two points of F1), and **mostly from positive evidence, not the veto**, because positive evidence can recover the rename pairs that name-only matching cannot, while the veto only prevents false merges among pairs where both records show an ID (a quarter of pairs at q = 0.5).
- **G2:** zero violations for the veto variants (by construction), non-zero for the others; the veto prevents tens to a few hundred false-merge pairs.
- **G3:** positive evidence established, veto alone not established at q = 0.5.
- **G4:** `splink_id` within about a point of `P_full`; it can use ID equality as strong evidence, and the gate's extra is the hard veto.
- **G5:** address evidence gives no clear gain and may reduce F1, because of shared formation-agent addresses.
- **Dose:** gains grow with q, and are largest at q = 1.0.

## Limits, stated in advance

UK company register only, live companies, so it is not federal contractor data and not a tax ID. ID visibility is simulated. The dense-slice design preserves local lookalike density but not the whole-register scale, and slices are contiguous in name space, so they are not a uniform sample of companies; slice-level bootstrap intervals are the honest unit but only 30 held-out slices make them wide-ish. A company's previous names carry no address, which understates address evidence for positives. The repository's normaliser is not UK-aware, which affects every matcher equally. Splink is hand-configured and unsupervised. Several variants and grids make this a search; the held-out slices are never used for any choice.

## Deviations

None yet.

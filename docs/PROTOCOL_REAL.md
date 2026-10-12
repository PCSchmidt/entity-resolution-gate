# Protocol: entity resolution on real federal-contractor names (written before any matcher was run on this data)

Committed before the first matcher result, so the choices below cannot have been made after seeing scores. Anything changed later is listed under [Deviations](#deviations).

## Why

Every number so far ([RESULTS.md](RESULTS.md)) comes from a synthetic generator whose name pool saturates, so it partly measures the generator. This study uses real names.

## What I looked at before writing this (stated so it can be discounted)

I downloaded a census of January 2024 Department of Defense contract awards from the public USAspending API and looked at **descriptive statistics only**: how many registry entries (UEIs) there are (748), how many have more than one name string (the registry's profile lists alternate names; 236 UEIs have two or more names that differ after normalisation, 1,043 name strings in all), and a dozen random examples. I ran **no matcher** on it. I first tried the UEI as the answer key using the award-level names and found zero within-UEI name variation there, then tried parent-company families and found only 10 families with more than one registration in the month (below the 50 I had set as a minimum), so I dropped both.

## Task and answer key

**Task.** Given a pile of recipient-name strings, group those that name the same registered entity.

**Records.** For each UEI, one record per distinct name string among the profile's primary name and its alternate names. **Answer key = the UEI**, assigned by the federal registry and never given to a matcher. Records carry **names only**: the alternate names have no addresses, so address scoring is deliberately off, and there are no tax identifiers in public data.

**Split.** By entity, not by record: a UEI goes to development if the first byte of `sha256(UEI)` is even, otherwise to test. No entity appears in both. All tuning uses development; the test split is scored **once** per matcher.

## Matchers (each has exactly one tuned number, chosen on development)

1. **Exact normalised name.** Records group when their normalised names (the repository's `normalise`) are identical. Nothing to tune. This is the floor.
2. **Plain fuzzy.** All pairs within a split (no blocking); link when `rapidfuzz.fuzz.token_sort_ratio` of the normalised names is at least `t`; groups are connected components. `t` grid: 50 to 100 in steps of 1.
3. **Splink.** Fellegi-Sunter model on the normalised name: levels exact, Jaro-Winkler at least 0.92, at least 0.80, else. Blocking: same first token, or same first three characters. `u` estimated by random sampling (seed 0), `m` by expectation-maximisation blocked on the first token. Link when match probability is at least `p`; groups are connected components. `p` grid: 0.50 to 0.99 in steps of 0.01.
4. **entity-resolution-gate pipeline** (this repository), configured `w_name=1.0, w_addr=0.0`, no tax id. The scoring threshold (grid 0.70 to 0.99 in steps of 0.01) is tuned on development; blocking, the density rule and Louvain splitting stay at their defaults. The default threshold (0.93) is also reported, untuned.

The tuned number maximises pairwise F1 on development; ties go to the higher threshold.

## Metrics

Pairwise precision, recall and F1 over all within-split record pairs (as `pairwise_prf` already does). Intervals: bootstrap over test **entities**, 2,000 resamples, for each matcher and for differences against the plain fuzzy matcher.


Two cuts, defined here and not changed:
- **Name-findable recall.** Among true pairs (same UEI), the share whose normalised names have `rapidfuzz.fuzz.token_set_ratio` of at least 50. Pairs below that (renames such as one company name replaced by another) cannot be recovered by string similarity, so recall on them is reported separately, not hidden.
- **Same-name, different-registration.** Merges of two records with identical normalised names but different UEIs are counted as false positives by the answer key but may be one organisation registered twice. They are counted and reported separately.

## Pre-stated criteria

- **C1.** Pipeline F1 minus plain-fuzzy F1, entity-bootstrap 95% interval entirely above zero. Otherwise "the pipeline beats a plain fuzzy matcher" is **not established**.
- **C2.** The same for Splink against plain fuzzy (a tuned plain matcher may well match or beat it).
- **C3.** Report name-findable recall and overall recall for every matcher, without a threshold.
- **C4.** Report merges the pipeline's blocking missed (true pairs never scored), separate from pairs it scored low.

## My expectation, written down so it can be wrong

I expect the four matchers to land within a few F1 points of each other on name-only data, with no pipeline advantage over a tuned fuzzy matcher (C1 not met), and Splink at or below the fuzzy baseline untuned beyond its probability threshold (C2 not met). I expect overall recall to be capped well below 1 by renames. The pipeline's design strengths (tax-ID veto, address evidence, scale) are not exercised by this data.

## Limits, stated in advance

One month, one agency, contracts only; about 370 entities in test, so intervals will be wide. The name variants are the registry's name history, so this tests spelling and renaming drift more than typing errors. **Not tested here:** the hard tax-ID constraint (no tax ids in public data), address evidence (alternate names have none), and scale beyond a few thousand records, which still rests on the synthetic benchmark. The answer key is the registry's own assignment and can contain mistakes. Several matchers share the repository's normaliser, so a normaliser weakness affects all of them.

## Deviations

Both were made after the first development run and **before the test split was scored**. Only development numbers had been seen.

1. **Splink probability grid widened from 0.50-0.99 to 0.01-0.99.** The first development run scored Splink at F1 0.000 at every threshold, because with one Jaro-Winkler comparison and the prior fixed at 0.001 (a value the protocol did not specify) its highest match probability was 0.229, so nothing could ever reach 0.50. The protocol's own intent was that the tuned threshold absorbs the prior; the grid contradicted it. I diagnosed this on development data only (probability by comparison level; no test data touched).
2. **A second, richer Splink variant (`splink_rich`) added.** With a single Jaro-Winkler comparison Splink is just a four-level similarity threshold, a weak baseline. The variant adds an exact first-token comparison and a token-overlap comparison (two or more shared tokens, one shared token) and trains by expectation-maximisation on two blocking rules. Both Splink variants are reported; neither is dropped. The protocol's headline Splink is the original single-comparison configuration; `splink_rich` is exploratory and added to avoid dismissing Splink on a thin configuration. Adding a matcher after seeing development results widens the forking paths; the test intervals should be read with that in mind.

Development results at the time of the freeze (F1, one tuned number each): exact 0.680, plain fuzzy 0.700 (t=92), Splink 0.727 (p=0.16), Splink-rich 0.639 (p=0.98), pipeline 0.742 (threshold 0.90).

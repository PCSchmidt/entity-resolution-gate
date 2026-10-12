# Protocol: does better blocking recover lost recall? (written before any blocking variant was run)

Committed before the first variant result, so the choices below cannot have been made after seeing scores. Anything changed later is listed under [Deviations](#deviations). This follows [PROTOCOL_REAL.md](PROTOCOL_REAL.md) and [RESULTS_REAL.md](RESULTS_REAL.md); read those first.

## Why

On the real-data study, the tuned pipeline missed 287 name-findable true pairs on the January test split; 214 of them (75%) were never put in front of the scorer because blocking did not propose them, and 73 were scored and rejected (corrected figures; see Deviation 3 of the earlier protocol). Blocking is therefore the larger recall loss, and it is cheap to change. This study asks whether adding blocking keys recovers recall without hurting precision or scale.

## Question

1. **Pair completeness.** Do the new keys put more name-findable true pairs in front of the scorer?
2. **Final quality.** Does that translate into higher pairwise F1 after the scorer's threshold is re-tuned?
3. **Cost.** How many more candidate pairs does it cost, and does anything regress on the synthetic benchmark?

## What I looked at before writing this (stated so it can be discounted)

- The January **development** split only: I categorised the 167 name-findable true pairs that blocking never proposed, using the corrected record-position mapping. By my reading: spacing-only differences (33, e.g. `a123 systems` / `a123systems`), a side with fewer than two tokens (43, e.g. `abt` / `abt associates`), more than four tokens (30), and other (61, mostly pairs sharing one distinctive token, e.g. `abt associates` / `abt global`). The variants below were designed from those categories.
- The January **test** split was scored once for the baseline in the earlier study, and its never-scored count (218 name-findable pairs) was computed. It is reported again here as a **secondary** result and must be read as a second look at a split already seen.
- For the fresh month (July 2024) I downloaded and built the records but looked only at counts of records and entities, not at any matcher output.

## Data

- **Development:** the January 2024 development split (381 entities, 1,123 records), exactly as before. All tuning uses it.
- **Primary held-out set:** July 2024, Department of Defense contract awards, built the same way as January (profile name plus alternate names, UEI as the hidden answer key), **keeping only UEIs that do not appear anywhere in the January data**. This set is new in both time and entities, so nothing in it has been seen by any matcher or used for any choice.
- **Secondary:** the January test split (already seen).
- **Regression check:** the synthetic benchmark (`scripts/benchmark.py`), unchanged seeds.

## Variants (a fixed menu, each strictly adds keys to the one before)

All variants keep the existing keys, so every variant's candidate set is a superset of the baseline's: a variant cannot lose a candidate, only add cost. Selected at the pipeline's `Config(blocking=...)`.

| Name | Keys added to the baseline |
| --- | --- |
| `base` | none (the current behaviour) |
| `squash` | `s:` plus the normalised name with spaces removed, full string; `q:` plus its first six characters |
| `squash_first` | `squash`, plus `f:` plus the first token of the normalised name (for every name, including single-token names) |
| `squash_first_wide` | `squash_first`, but token-pair keys are generated from the first six tokens instead of four |

The existing block-size cap (200) applies to every key, so over-common keys are skipped and logged, as before.

## Selection (development only)

For each variant, re-tune the pipeline's score threshold on the January development split (grid 0.70 to 0.99 in steps of 0.01, name-only configuration `w_name=1.0, w_addr=0.0`, ties to the higher value) and record dev pairwise F1, pair completeness on name-findable true pairs, and the number of candidate pairs. **Choose the variant with the highest dev F1; if a later variant is within 0.005 of an earlier one, take the earlier (simpler) one.** The chosen variant and its threshold are frozen and committed before July is scored.

## Evaluation (once)

On the July held-out set, score and report, each with the numbers frozen on January development:

- the chosen variant;
- the baseline (`base`, threshold 0.90);
- plain fuzzy (token-sort ratio, t = 92) and exact normalised name, as before.

The July set is scored **once**; the runner refuses to run twice. Intervals are bootstrap over July entities, 2,000 resamples, paired against the baseline. Name-findable is defined as before (token-set ratio of the normalised names at least 50), and the same rename ceiling is reported.

## Pre-stated criteria

- **K1, pair completeness.** Share of name-findable true pairs that become candidates, chosen variant minus baseline on July, with its entity-bootstrap 95% interval. Reported without a threshold.
- **K2, final quality.** Pairwise F1 of the chosen variant minus the baseline on July, entity-bootstrap 95% interval entirely above zero. Otherwise "better blocking improves F1" is **not established**, even if completeness rose.
- **K3, against plain fuzzy.** F1 difference of the chosen variant from plain fuzzy on July, reported.
- **K4, regression and scale.** On the synthetic benchmark, the chosen variant must not lower F1 by more than 0.01 on any of the four standard runs, must keep zero tax-ID violations, and must not take more than three times the baseline's time. If it fails, the result is reported as a trade-off and the variant is **not** made the default.
- **K5, cost.** Candidate-pair count ratio against the baseline on January development and on July.

The default configuration changes only if K2 is met and K4 passes.

## My expectation, written down so it can be wrong

I expect pair completeness to rise clearly (the added keys target exactly the categories I saw), but I expect only a small F1 gain, and K2 may well not be met: pairs like `abt associates` and `abt global` get proposed but should score low, and the cheaper keys (first token) add pairs that become false positives at the threshold that suits the rest. I expect the simplest variant that fixes spacing and short names to be chosen, and a larger candidate count. I do not expect the rename ceiling (about 17% of true pairs) to move at all.

## Limits, stated in advance

Name-only data, one agency, contracts only; the July set will have a few hundred entities, so intervals will be wide. The variant menu was designed from the development split's missed pairs, so it is tuned to this naming style (US federal contractors, English). Four variants and one threshold each is a small search, but still a search; the July set exists so that it is not judged on the data that chose it. Synthetic-benchmark scale is limited to about 39,000 records. No change is made to scoring, the graph gate or the tax-ID constraint.

## Deviations

None yet.

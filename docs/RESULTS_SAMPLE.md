# Results: real contractor names, random sample

Plan: [PROTOCOL_SAMPLE.md](PROTOCOL_SAMPLE.md), pushed before any sampled name was downloaded, with four deviations logged after the first development run and **before the held-out half was scored**. It supersedes the alphabetical-prefix pilot ([RESULTS_REAL.md](RESULTS_REAL.md), [RESULTS_BLOCKING.md](RESULTS_BLOCKING.md)).

**Setup.** The population is every recipient of a Department of Defense contract award in US fiscal year 2024: 45,959 recipients. After removing the 1,019 that the pilot had used, I drew a simple random sample of 3,000 and downloaded each one's registry profile. A record is one name string (the primary name or an alternate name); the **registry UEI is the answer key** and is never a matcher input. Entities are split by a hash of the UEI into development (4,330 records, 1,471 entities) and held-out (4,542 records, 1,527 entities). Each matcher has one number tuned on development; the held-out half was scored **once**. Records carry names only.

## Held-out results (1,527 entities, 4,542 records)

The primary metric is B-cubed F1 (precision and recall averaged over records, so a very large entity cannot dominate; see Deviation 2). Intervals are bootstrap over held-out entities, 2,000 resamples.

| Matcher (tuned number) | Precision | Recall | **F1** [95% interval] | Pairwise F1 [95%] |
| --- | --- | --- | --- | --- |
| Exact normalised name | 0.994 | 0.727 | 0.840 [0.821, 0.857] | 0.584 [0.509, 0.669] |
| Plain fuzzy (token-sort ratio, t = 86) | 0.977 | 0.809 | 0.885 [0.870, 0.898] | 0.721 [0.661, 0.778] |
| Splink, one comparison (p = 0.53) | 0.988 | 0.814 | 0.893 [0.878, 0.907] | 0.723 [0.657, 0.788] |
| Splink, richer comparisons (p = 0.9999) | 0.906 | 0.862 | 0.883 [0.871, 0.895] | 0.681 [0.625, 0.740] |
| **Pipeline, baseline (threshold 0.87)** | 0.974 | 0.855 | **0.911** [0.898, 0.922] | 0.791 [0.729, 0.851] |
| Pipeline + space-removed keys | 0.959 | 0.871 | 0.913 [0.901, 0.924] | 0.792 [0.732, 0.853] |
| Pipeline + first-token keys | 0.958 | 0.873 | 0.914 [0.902, 0.925] | 0.794 [0.734, 0.855] |
| Pipeline + six-token window | 0.958 | 0.875 | 0.915 [0.903, 0.925] | 0.798 [0.741, 0.855] |
| Pipeline, token-sort-only score (0.75) | 0.958 | 0.836 | 0.893 [0.880, 0.905] | 0.749 [0.686, 0.804] |

## Against the criteria set in advance

| Criterion | Result |
| --- | --- |
| **P1**: baseline pipeline minus plain fuzzy, F1, 95% interval above zero | **Met.** +0.026 [+0.019, +0.034] on B-cubed F1; +0.070 [+0.034, +0.105] on pairwise F1. The gain is recall (0.855 against 0.809) at about the same precision (0.974 against 0.977). |
| **S1** `squash`, **S2** `squash_first`, **S3** `squash_first_wide`: improvement over the baseline (98.75% interval above zero) | **Not established.** +0.002 [-0.003, +0.007], +0.003 [-0.002, +0.008], +0.004 [-0.001, +0.009]. |
| **S4** token-sort-only score | **Worse, the opposite of my expectation.** -0.018 [-0.025, -0.011]. |
| Pair completeness and cost of the blocking variants (descriptive) | Completeness (share of name-findable true pairs proposed) rose from 0.858 to 0.902, 0.913 and 0.934 (differences +4.4, +5.5, +7.6 points, intervals above zero) at 1.25x, 1.35x and 1.69x the candidate pairs. |
| K4 (synthetic regression) | Not required: no variant met its S criterion, so the default is unchanged. Not run. |

**My written expectations against the outcome.** I expected no clear pipeline advantage over plain fuzzy matching (P1 was wrong: it was met), an improvement from the token-sort-only score (wrong: it was worse), flat F1 from better blocking (right), and about one in six true pairs unrecoverable (right: 17%).

## Post-hoc checks (not pre-registered)

Run by [scripts/sample_posthoc.py](../scripts/sample_posthoc.py) after the held-out result was seen; they change no stored result.

- **Against the other matchers, paired:** baseline pipeline minus exact matching +0.071 [+0.060, +0.083]; minus Splink (one comparison) +0.018 [+0.012, +0.025]; minus Splink (richer) +0.028 [+0.020, +0.035]. The protocol pre-specified only the contrast with plain fuzzy.
- **The rename ceiling.** Of 8,493 true pairs, 1,450 (17.1%) are pairs whose normalised names share almost nothing (token-set ratio under 50). No string matcher recovers these, so recall cannot approach 1.0.
- **Where the baseline loses recall.** Of its 1,183 missed name-findable true pairs, 877 (74%) were never proposed as candidates and 306 (26%) were proposed and not linked. Blocking is where most misses are, but the variants that recover them gain recall (0.832 to 0.872 on findable pairs) and lose about the same in precision (0.974 to 0.958), so F1 does not move.
- **Answer-key noise.** Entities have a median of 3 name strings and at most 32; the five largest (32, 30, 27, 26, 21) hold 21% of true pairs. Some of these list other institutions among their aliases, which is noise in the answer key. Dropping the six entities with more than 20 names, the baseline pipeline still beats plain fuzzy: 0.918 against 0.896, difference +0.023 [+0.017, +0.028].

## What this does and does not show

- **Shown:** on a random sample of DoD contract recipients, a name-only pipeline with one tuned threshold beats a tuned plain fuzzy matcher and a hand-set Splink model on B-cubed F1, by 1.8 to 2.6 points, with intervals clear of zero. The ordering also holds on pairwise F1 and when the largest entities are removed.
- **Not shown that the graph gate is the reason.** The data have no tax IDs or addresses, so the hard constraint and address scoring, the parts the design is built around, were not exercised. The gain may come from the scoring (the larger of Jaro-Winkler and token-sort) and the blocking and density choices; the token-sort-only ablation, which was worse, suggests the Jaro-Winkler part helps, but a proper ablation of the graph step was not run.
- **Better blocking is not a lever here.** It raises pair completeness by 4 to 8 points and F1 by at most 0.004, not distinguishable from zero.
- **The earlier pilot's mixed picture** (an edge in January, none in July) was a product of the alphabetical-prefix sample; the July failure came from clusters of look-alike "Advanced ..." names that a random sample contains far less of.

## Deviations and forking paths

The primary metric changed from pairwise to B-cubed F1, one entity was excluded, and the pipeline and Splink grids were widened, all after seeing development results and before the held-out half was scored (Deviations 1 to 4 of the protocol). Pairwise results are reported alongside and lead to the same conclusion on P1. Nine matchers were run, and the Bonferroni interval covers only the four pre-specified secondary contrasts. The `splink_rich` threshold sits at the top of its grid.

## Limits

Name-only data, one agency, one fiscal year, contracts only; recipients weighted equally, so small firms dominate. The answer key is the registry's own assignment and has noise. Splink was hand-configured and unsupervised, so its results say little about a tuned Splink. The tax-ID constraint, address scoring and scale beyond a few thousand records are not tested here (scale still rests on the synthetic benchmark).

## Reproduce

```bash
pip install -e ".[dev,study]"
python scripts/fetch_recipient_frame.py --out data/frame_fy2024.jsonl
python scripts/sample_frame.py --frame data/frame_fy2024.jsonl --n 3000 --seed 0 \
    --exclude data/profiles_2024-01.jsonl data/profiles_2024-07.jsonl --out data/sample_ids.jsonl
python scripts/enrich_profiles.py --records data/sample_ids.jsonl --out data/sample_profiles.jsonl
python scripts/build_real_dataset.py --profiles data/sample_profiles.jsonl --out data/sample_records.jsonl --max-names 50
python scripts/run_sample.py dev        # writes results/sample/frozen.json
python scripts/run_sample.py heldout    # one-shot; refuses to run twice
python scripts/sample_posthoc.py        # the post-hoc checks above
```

The two pilot profile files named in `--exclude` come from the pilot's scripts; without them the sample would differ slightly. The API is live, so a later download may differ from the snapshot used here.

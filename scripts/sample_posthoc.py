"""Post-hoc checks on the random-sample held-out half (NOT pre-registered; see docs/RESULTS_SAMPLE.md).

Run after the one-shot held-out stage. It re-applies the frozen matchers (deterministic, nothing is tuned) and reports:
  1. paired B-cubed F1 differences of the baseline pipeline against exact matching, Splink and Splink-rich,
  2. the rename ceiling (share of true pairs no string matcher can recover) and where the baseline's misses sit,
  3. a sensitivity check: the primary contrast recomputed without entities that have more than 20 name strings.

    python scripts/sample_posthoc.py
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
from run_real import Matchers
from run_sample import (
    BOOTSTRAPS,
    FINDABLE_RATIO,
    OUT,
    PIPELINES,
    load,
    pipeline_candidates,
    pipeline_labels,
)

from entity_resolution_gate.evaluation import bcubed_f1, bcubed_per_record, codes, pair_table
from entity_resolution_gate.pipeline import normalise


def main() -> None:
    frozen = json.loads((OUT / "frozen.json").read_text())
    df = load("test")
    names = [normalise(n) for n in df["name"].to_list()]
    ent = codes(df["entity_id"].to_list())
    n_ent = int(np.max(ent)) + 1
    m = Matchers(df)
    labels = {
        "exact": m.exact(),
        "fuzzy": m.fuzzy(frozen["fuzzy"]),
        "splink": m.splink(frozen["splink"]),
        "splink_rich": m.splink_rich(frozen["splink_rich"]),
        "pipeline_base": pipeline_labels(df, "pipeline_base", frozen["pipeline_base"]),
    }
    per_rec = {k: bcubed_per_record(v, ent) for k, v in labels.items()}
    rng = np.random.default_rng(0)
    weights = [
        np.bincount(rng.integers(0, n_ent, n_ent), minlength=n_ent).astype(float)
        for _ in range(BOOTSTRAPS)
    ]
    boots = {k: np.array([bcubed_f1(*per_rec[k], ent, w)[2] for w in weights]) for k in labels}
    out: dict[str, Any] = {"paired_f1_pipeline_base_minus": {}}
    for k in ("exact", "fuzzy", "splink", "splink_rich"):
        d = boots["pipeline_base"] - boots[k]
        point = bcubed_f1(*per_rec["pipeline_base"])[2] - bcubed_f1(*per_rec[k])[2]
        out["paired_f1_pipeline_base_minus"][k] = {"point": point, "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]}  # fmt: skip

    t = pair_table(labels["pipeline_base"], ent, names)
    true = t["true"]
    findable = true & (t["tsr"] >= FINDABLE_RATIO)
    cands = pipeline_candidates(df, "pipeline_base")
    missed = findable & ~t["pred"]
    scored = np.array(
        [(int(a), int(b)) in cands for a, b in zip(t["i"].tolist(), t["j"].tolist(), strict=True)]
    )
    out["rename_ceiling"] = {
        "true_pairs": int(true.sum()), "findable_true_pairs": int(findable.sum()),
        "share_not_findable": float(1 - int(findable.sum()) / int(true.sum())),
        "baseline_findable_missed": int(missed.sum()),
        "baseline_findable_missed_never_scored": int((missed & ~scored).sum()),
        "baseline_findable_missed_scored_then_not_linked": int((missed & scored).sum()),
    }  # fmt: skip
    sizes = np.bincount(ent)
    order = np.sort(sizes)[::-1]
    pair_share = (order * (order - 1) // 2) / max(1, int((order * (order - 1) // 2).sum()))
    out["entity_sizes"] = {
        "records_per_entity_median": float(np.median(sizes)), "max": int(order[0]),
        "top5_sizes": [int(x) for x in order[:5]], "top5_share_of_true_pairs": float(pair_share[:5].sum()),
        "entities_with_more_than_20_names": int((sizes > 20).sum()),
    }  # fmt: skip

    keep_entities = sizes <= 20
    keep_rec = keep_entities[ent]
    ent2 = codes(list(np.asarray(ent)[keep_rec]))
    sens = {}
    for k in ("fuzzy", "pipeline_base"):
        lab = np.asarray(labels[k])[keep_rec]
        sens[k] = bcubed_per_record(lab, ent2)
    n2 = int(np.max(ent2)) + 1
    ws = [
        np.bincount(rng.integers(0, n2, n2), minlength=n2).astype(float) for _ in range(BOOTSTRAPS)
    ]
    d = np.array(
        [
            bcubed_f1(*sens["pipeline_base"], ent2, w)[2] - bcubed_f1(*sens["fuzzy"], ent2, w)[2]
            for w in ws
        ]
    )
    out["sensitivity_without_entities_over_20_names"] = {
        "records": int(keep_rec.sum()), "entities": n2,
        "pipeline_base_f1": bcubed_f1(*sens["pipeline_base"])[2], "fuzzy_f1": bcubed_f1(*sens["fuzzy"])[2],
        "difference": bcubed_f1(*sens["pipeline_base"])[2] - bcubed_f1(*sens["fuzzy"])[2],
        "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
    }  # fmt: skip
    out["pipelines_evaluated"] = list(PIPELINES)
    (OUT / "posthoc.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

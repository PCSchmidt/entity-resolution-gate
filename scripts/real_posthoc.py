"""Post-hoc breakdown of the pipeline's missed true pairs on the test split (NOT in the protocol).

Run after the one-shot test stage. It re-applies the frozen pipeline (deterministic, no tuning) and splits
every true pair into: found, scored-then-rejected, or never scored (blocking), separately for name-findable
pairs (token_set_ratio >= 50) and renames no string similarity can recover.

    python scripts/real_posthoc.py
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
from run_real import FINDABLE_RATIO, OUT, load

from entity_resolution_gate.evaluation import codes, pair_table
from entity_resolution_gate.pipeline import AuditLog, Config, candidate_pairs, normalise, resolve


def main() -> None:
    frozen = json.loads((OUT / "frozen.json").read_text())
    df = load("test")
    names = [normalise(n) for n in df["name"].to_list()]
    ent = codes(df["entity_id"].to_list())
    cfg = Config(threshold=frozen["gate"], w_name=1.0, w_addr=0.0)
    out, _ = resolve(df, cfg)
    labels = np.asarray(out.sort("rid")["cluster_id"].to_numpy(), dtype=np.int64)
    t = pair_table(labels, ent, names)
    scored = {(a, b) for a, b in candidate_pairs(df, cfg, AuditLog())}
    result: dict[str, Any] = {}
    for cut, mask in [
        ("findable", t["tsr"] >= FINDABLE_RATIO),
        ("not_findable", t["tsr"] < FINDABLE_RATIO),
    ]:
        true = t["true"] & mask
        idx = np.where(true)[0]
        found = int((t["pred"][idx]).sum())
        missed = [k for k in idx.tolist() if not t["pred"][k]]
        never = sum(1 for k in missed if (int(t["i"][k]), int(t["j"][k])) not in scored)
        result[cut] = {
            "true_pairs": int(true.sum()),
            "found": found,
            "scored_then_rejected": len(missed) - never,
            "never_scored_by_blocking": never,
        }
    (OUT / "posthoc_blocking.json").write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()

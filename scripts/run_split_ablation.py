"""Graph-splitting ablation (docs/PROTOCOL_SPLIT.md), on a fresh set of 60 dense name slices.

    python scripts/run_split_ablation.py dev       # tune one threshold per variant on the 30 development slices
    python scripts/run_split_ablation.py heldout   # score the 30 held-out slices ONCE with the frozen thresholds

Variants differ only in Config.split: "louvain" (the pipeline as published), "tax_only" (Louvain only to repair a
tax-id conflict) and "none" (connected components of the thresholded graph, no splitting).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

import run_gate as rg
from entity_resolution_gate.evaluation import IntArray
from entity_resolution_gate.pipeline import Config, resolve

DATA_B = Path("data/gate_records_b.jsonl")
OUT = Path("results/split")
Q_LEVELS = (0.25, 0.5, 1.0)
PRIMARY_Q = 0.5
# (name, base pipeline variant of run_gate.cfg_for, split mode, q levels it is run at)
VARIANTS: list[tuple[str, str, str, tuple[float, ...]]] = [
    ("P_full/louvain", "P_full", "louvain", Q_LEVELS),
    ("P_full/tax_only", "P_full", "tax_only", Q_LEVELS),
    ("P_full/none", "P_full", "none", Q_LEVELS),
    ("P_addr/louvain", "P_addr", "louvain", (PRIMARY_Q,)),
    ("P_addr/none", "P_addr", "none", (PRIMARY_Q,)),
]


def cfg_of(base: str, split: str, threshold: float) -> Config:
    return replace(rg.cfg_for(base, threshold), split=split)


def _work(args: tuple[pl.DataFrame, Config]) -> tuple[IntArray, dict[str, Any]]:
    df, cfg = args
    out, log = resolve(df, cfg)
    top = [e for e in log.events if e["kind"] == "component_split" and e["depth"] == 0]
    info = {
        "split_components": len(top),
        "records_in_split_components": int(sum(e["size"] for e in top)),
        "reasons": dict(Counter(e.get("reason", e["method"]) for e in top)),
        "n_records": df.height,
    }
    return np.asarray(out.sort("rid")["cluster_id"].to_numpy(), dtype=np.int64), info


def labels(
    sp: rg.Split, pool: ProcessPoolExecutor, cfg: Config, q: float
) -> tuple[IntArray, dict[str, Any]]:
    res = list(pool.map(_work, [(f, cfg) for f in sp.frames(q)]))
    agg: dict[str, Any] = {"split_components": 0, "records_in_split_components": 0, "n_records": 0, "reasons": Counter()}
    for _, i in res:
        agg["split_components"] += i["split_components"]
        agg["records_in_split_components"] += i["records_in_split_components"]
        agg["n_records"] += i["n_records"]
        agg["reasons"].update(i["reasons"])
    agg["reasons"] = dict(agg["reasons"])
    return sp.stitch([r[0] for r in res]), agg


def tune(sp: rg.Split, pool: ProcessPoolExecutor, base: str, split: str, q: float) -> tuple[float, dict[float, float]]:
    def score(t: float) -> float:
        return rg.b3_f1(sp, labels(sp, pool, cfg_of(base, split, t), q)[0])

    scores = {t: score(t) for t in rg.COARSE}
    best = rg.best_of(scores)
    for t in sorted({round(best + d / 100, 2) for d in range(-3, 4)} - set(scores)):
        if 0.5 <= t <= 0.99:
            scores[t] = score(t)
    return rg.best_of(scores), scores


def run_dev() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sp = rg.Split("dev")
    frozen: dict[str, float] = {}
    sweep: dict[str, Any] = {}
    with ProcessPoolExecutor(max_workers=12) as pool:
        for name, base, split, qs in VARIANTS:
            for q in qs:
                key = f"{name}@{q}"
                t, scores = tune(sp, pool, base, split, q)
                frozen[key] = t
                sweep[key] = {str(k): v for k, v in sorted(scores.items())}
                print(f"{key:24s} threshold {t:.2f}  dev B3 F1 {scores[t]:.4f}", flush=True)
    (OUT / "dev_sweep.json").write_text(json.dumps(sweep, indent=1), encoding="utf-8")
    (OUT / "frozen.json").write_text(json.dumps(frozen, indent=1), encoding="utf-8")


def run_heldout() -> None:
    dest = OUT / "heldout_results.json"
    if dest.exists():
        sys.exit("heldout_results.json exists; this stage is one-shot (delete it deliberately to re-run)")
    frozen = json.loads((OUT / "frozen.json").read_text(encoding="utf-8"))
    sp = rg.Split("heldout")
    n_sl = len(sp.slices)
    rng = np.random.default_rng(0)
    draws = [np.bincount(rng.integers(0, n_sl, n_sl), minlength=n_sl).astype(float) for _ in range(rg.BOOTSTRAPS)]
    ones = np.ones(n_sl)
    stats: dict[str, dict[str, Any]] = {}
    activity: dict[str, Any] = {}
    with ProcessPoolExecutor(max_workers=12) as pool:
        for name, base, split, qs in VARIANTS:
            for q in qs:
                key = f"{name}@{q}"
                lab, info = labels(sp, pool, cfg_of(base, split, frozen[key]), q)
                stats[key] = rg.slice_stats(sp, lab, sp.visible(q))
                activity[key] = info
                print(key, "done", flush=True)
    res: dict[str, Any] = {"n_records": sp.n, "n_slices": n_sl, "frozen": frozen, "matchers": {}, "contrasts": {}, "split_activity": activity}
    for key, st in stats.items():
        boots = np.array([rg.metric(st, w, "b3_f1") for w in draws])
        e = {m: rg.metric(st, ones, m) for m in ("b3_p", "b3_r", "b3_f1", "pw_f1", "rename_recall")}
        e["b3_f1_ci95"] = rg.pct(boots)
        e["false_merge_pairs"] = float(st["pred"].sum() - st["tp"].sum())
        e["violating_clusters_visible_ids"] = st["violating_clusters"]
        res["matchers"][key] = e

    def contrast(a: str, b: str, band: tuple[float, float] = (2.5, 97.5)) -> dict[str, Any]:
        d = np.array([rg.metric(stats[a], w, "b3_f1") - rg.metric(stats[b], w, "b3_f1") for w in draws])
        per = [
            f1(stats[a], k) - f1(stats[b], k) for k in range(n_sl)
        ]
        return {
            "point": rg.metric(stats[a], ones, "b3_f1") - rg.metric(stats[b], ones, "b3_f1"),
            "ci": rg.pct(d, *band),
            "slices_better": sum(1 for x in per if x > 1e-12),
            "slices_worse": sum(1 for x in per if x < -1e-12),
        }

    def f1(st: dict[str, Any], k: int) -> float:
        n, a, b = float(st["n"][k]), float(st["sp"][k]) , float(st["sr"][k])
        p, r = a / n, b / n
        return 2 * p * r / (p + r) if p + r else 0.0

    for q in Q_LEVELS:
        c = {
            "S1_P_full_louvain_minus_none": contrast(f"P_full/louvain@{q}", f"P_full/none@{q}"),
            "S4_P_full_louvain_minus_tax_only_ci97_5": contrast(f"P_full/louvain@{q}", f"P_full/tax_only@{q}", (1.25, 98.75)),
            "ref_P_full_tax_only_minus_none": contrast(f"P_full/tax_only@{q}", f"P_full/none@{q}"),
        }
        res["contrasts"][f"q={q}"] = c
    res["contrasts"]["no_ids"] = {
        "S3_P_addr_louvain_minus_none_ci97_5": contrast(f"P_addr/louvain@{PRIMARY_Q}", f"P_addr/none@{PRIMARY_Q}", (1.25, 98.75))
    }
    dest.write_text(json.dumps(res, indent=1), encoding="utf-8")
    for key, e in res["matchers"].items():
        print(f"{key:24s} B3 F1 {e['b3_f1']:.4f} {[round(x, 4) for x in e['b3_f1_ci95']]} | false-merge pairs {e['false_merge_pairs']:.0f} | violating clusters {e['violating_clusters_visible_ids']}")  # fmt: skip
    for qk, c in res["contrasts"].items():
        for ck, v in c.items():
            print(qk, ck, f"{v['point']:+.4f}", [round(x, 4) for x in v["ci"]], f"better {v['slices_better']} worse {v['slices_worse']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["dev", "heldout"])
    a = ap.parse_args()
    rg.DATA = DATA_B
    {"dev": run_dev, "heldout": run_heldout}[a.stage]()


if __name__ == "__main__":
    main()

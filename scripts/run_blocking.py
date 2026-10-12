"""Run the blocking study from docs/PROTOCOL_BLOCKING.md.

    python scripts/run_blocking.py dev        # tune each variant's threshold on January dev, choose, freeze
    python scripts/run_blocking.py heldout    # score the fresh July set ONCE, every variant, frozen thresholds
    python scripts/run_blocking.py jan-test   # secondary: January test split (already seen once before)
    python scripts/run_blocking.py synthetic  # regression and scale check on the synthetic benchmark

Selection rule (fixed before any variant was run): among variants whose tuned dev F1 is within 0.005 of the
best, take the earliest in the order base, squash, squash_first, squash_first_wide. Deviation 1 of the protocol
widens the held-out comparison to all variants, with a Bonferroni-corrected interval for the three contrasts.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import polars as pl
from rapidfuzz import fuzz, process

from entity_resolution_gate import generate, pairwise_prf
from entity_resolution_gate.evaluation import (
    IntArray,
    boot_f1,
    codes,
    components,
    pair_table,
    prf_counts,
    rid_pairs_to_positions,
)
from entity_resolution_gate.pipeline import (
    BLOCKING_MODES,
    AuditLog,
    Config,
    candidate_pairs,
    normalise,
    resolve,
)

OUT = Path("results/blocking")
JAN = Path("data/real_records.jsonl")
HELDOUT = Path("data/heldout_2024-07.jsonl")
GRID = [round(0.70 + 0.01 * k, 2) for k in range(30)]
NEAR_TIE = 0.005
FINDABLE_RATIO = 50.0
BOOTSTRAPS = 2000
VARIANTS = [m for m in BLOCKING_MODES if m != "base"]
BONF = (100 * (0.025 / len(VARIANTS)), 100 * (1 - 0.025 / len(VARIANTS)))  # 98.3% interval


def load(path: Path, split: str) -> pl.DataFrame:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows = sorted((r for r in rows if r["split"] == split), key=lambda r: r["rid"])
    df = pl.DataFrame(rows).select(["rid", "name", "address", "zip", "tax_id", "entity_id"])
    return df.with_columns(pl.col("zip").cast(pl.Utf8), pl.col("tax_id").cast(pl.Utf8))


def cfg(mode: str, threshold: float) -> Config:
    return Config(threshold=threshold, w_name=1.0, w_addr=0.0, blocking=mode)


def gate_labels(df: pl.DataFrame, mode: str, threshold: float) -> IntArray:
    out, _ = resolve(df, cfg(mode, threshold))
    return np.asarray(out.sort("rid")["cluster_id"].to_numpy(), dtype=np.int64)


def candidates(df: pl.DataFrame, mode: str) -> set[tuple[int, int]]:
    return rid_pairs_to_positions(
        candidate_pairs(df, cfg(mode, 0.9), AuditLog()), df["rid"].to_list()
    )


def findable_true_pairs(df: pl.DataFrame) -> tuple[Any, ...]:
    names = [normalise(n) for n in df["name"].to_list()]
    ent = codes(df["entity_id"].to_list())
    t = pair_table(np.arange(len(names), dtype=np.int64), ent, names)
    keep = t["true"] & (t["tsr"] >= FINDABLE_RATIO)
    return names, ent, t["i"][keep], t["j"][keep], t["ea"][keep]


def in_set(cand: set[tuple[int, int]], ii: Any, jj: Any) -> npt.NDArray[np.bool_]:
    return np.array(
        [(int(a), int(b)) in cand for a, b in zip(ii.tolist(), jj.tolist(), strict=True)]
    )


def run_dev() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = load(JAN, "dev")
    _, ent, ii, jj, _ = findable_true_pairs(df)
    result: dict[str, Any] = {}
    for mode in BLOCKING_MODES:
        t0 = time.perf_counter()
        cand = candidates(df, mode)
        comp = float(in_set(cand, ii, jj).mean())
        sweep = []
        for thr in GRID:
            p, r, f = prf_counts(gate_labels(df, mode, thr), ent)
            sweep.append({"threshold": thr, "precision": p, "recall": r, "f1": f})
        top = max(s["f1"] for s in sweep)
        best = max((s for s in sweep if s["f1"] == top), key=lambda s: s["threshold"])
        result[mode] = {
            "candidate_pairs": len(cand),
            "pair_completeness_findable": comp,
            "best": best,
            "sweep": sweep,
        }
        print(
            f"{mode}: candidates {len(cand)}, completeness {comp:.3f}, best dev F1 {best['f1']:.3f} "
            f"at {best['threshold']}  ({time.perf_counter() - t0:.0f}s)",
            flush=True,
        )
    best_f1 = max(result[m]["best"]["f1"] for m in BLOCKING_MODES)
    chosen = next(m for m in BLOCKING_MODES if result[m]["best"]["f1"] >= best_f1 - NEAR_TIE)
    frozen = {
        "variant": chosen,
        "thresholds": {m: result[m]["best"]["threshold"] for m in BLOCKING_MODES},
        "fuzzy_t": json.loads(Path("results/real/frozen.json").read_text())["fuzzy"],
    }
    (OUT / "dev_sweep.json").write_text(json.dumps(result, indent=1))
    (OUT / "frozen.json").write_text(json.dumps(frozen, indent=1))
    print("frozen:", frozen)


def _fuzzy(names: list[str], t: float) -> IntArray:
    sim = process.cdist(names, names, scorer=fuzz.token_sort_ratio, dtype=np.uint8, workers=-1)
    ii, jj = np.where(np.triu(sim >= t, k=1))
    return np.asarray(
        components(len(names), ii.astype(np.int64), jj.astype(np.int64)), dtype=np.int64
    )


def pct(a: npt.NDArray[np.float64], lo: float, hi: float) -> list[float]:
    return [float(np.percentile(a, lo)), float(np.percentile(a, hi))]


def evaluate(df: pl.DataFrame, frozen: dict[str, Any], out_path: Path, label: str) -> None:
    names, ent, ii, jj, fe = findable_true_pairs(df)
    n_ent = int(np.max(ent)) + 1
    labels: dict[str, IntArray] = {"exact": codes(names), "fuzzy": _fuzzy(names, frozen["fuzzy_t"])}
    cands: dict[str, set[tuple[int, int]]] = {}
    for mode in BLOCKING_MODES:
        labels[mode] = gate_labels(df, mode, frozen["thresholds"][mode])
        cands[mode] = candidates(df, mode)
    rng = np.random.default_rng(0)
    weights = [
        np.bincount(rng.integers(0, n_ent, n_ent), minlength=n_ent).astype(float)
        for _ in range(BOOTSTRAPS)
    ]
    tables = {k: pair_table(v, ent, names) for k, v in labels.items()}
    boots = {k: np.array([boot_f1(tables[k], w) for w in weights]) for k in labels}
    comp = {m: in_set(c, ii, jj) for m, c in cands.items()}
    comp_boot = {
        m: np.array([float((w[fe] * c).sum() / max(1.0, w[fe].sum())) for w in weights])
        for m, c in comp.items()
    }
    res: dict[str, Any] = {
        "label": label, "n_records": df.height, "n_entities": n_ent, "frozen": frozen,
        "findable_true_pairs": len(ii), "matchers": {}, "contrasts_vs_base": {},
    }  # fmt: skip
    for k, lab in labels.items():
        p, r, f = prf_counts(lab, ent)
        t = tables[k]
        findable = t["true"] & (t["tsr"] >= FINDABLE_RATIO)
        fp = t["pred"] & ~t["true"]
        entry: dict[str, Any] = {
            "precision": p, "recall": r, "f1": f, "f1_ci95": pct(boots[k], 2.5, 97.5),
            "recall_findable": float((findable & t["pred"]).sum() / max(1, int(findable.sum()))),
            "false_positive_pairs": int(fp.sum()), "false_positive_same_name": int((fp & t["same_name"]).sum()),
        }  # fmt: skip
        if k in cands:
            entry["candidate_pairs"] = len(cands[k])
            entry["pair_completeness_findable"] = float(comp[k].mean())
            miss = np.array(
                [
                    (int(a), int(b)) in cands[k]
                    for a, b in zip(t["i"].tolist(), t["j"].tolist(), strict=True)
                ]
            )
            entry["findable_candidate_but_not_linked"] = int((findable & miss & ~t["pred"]).sum())
        res["matchers"][k] = entry
    for mode in VARIANTS:
        d = boots[mode] - boots["base"]
        c = comp_boot[mode] - comp_boot["base"]
        res["contrasts_vs_base"][mode] = {
            "f1_difference": res["matchers"][mode]["f1"] - res["matchers"]["base"]["f1"],
            "f1_difference_ci95": pct(d, 2.5, 97.5),
            "f1_difference_ci_bonferroni98_3": pct(d, BONF[0], BONF[1]),
            "completeness_difference": float(comp[mode].mean() - comp["base"].mean()),
            "completeness_difference_ci95": pct(c, 2.5, 97.5),
            "candidate_ratio": len(cands[mode]) / max(1, len(cands["base"])),
        }
    for mode in ("base", *VARIANTS):
        d = boots[mode] - boots["fuzzy"]
        res["matchers"][mode]["f1_minus_fuzzy"] = (
            res["matchers"][mode]["f1"] - res["matchers"]["fuzzy"]["f1"]
        )
        res["matchers"][mode]["f1_minus_fuzzy_ci95"] = pct(d, 2.5, 97.5)
    out_path.write_text(json.dumps(res, indent=1))
    for k, m in res["matchers"].items():
        print(f"{k:18s} P {m['precision']:.3f} R {m['recall']:.3f} F1 {m['f1']:.3f} {m['f1_ci95']}")
    for k, v in res["contrasts_vs_base"].items():
        print(k, json.dumps(v))


def run_eval(path: Path, split: str, out_name: str) -> None:
    out_path = OUT / out_name
    if out_path.exists():
        sys.exit(
            f"{out_name} already exists; this stage is one-shot (delete it deliberately to re-run)"
        )
    frozen = json.loads((OUT / "frozen.json").read_text())
    evaluate(load(path, split), frozen, out_path, out_name)


def run_synthetic() -> None:
    rows = []
    for n, seed in [(1000, 2), (1000, 3), (5000, 2), (20000, 2)]:
        df = generate(n, seed=seed)
        row: dict[str, Any] = {"entities": n, "seed": seed, "records": df.height}
        for mode in BLOCKING_MODES:
            t0 = time.perf_counter()
            out, log = resolve(df, Config(blocking=mode))
            secs = time.perf_counter() - t0
            p, r, f = pairwise_prf(out)
            viol = sum(
                len({x for x in g["tax_id"].to_list() if x}) > 1
                for _, g in out.group_by("cluster_id")
            )
            cand = next(e["n"] for e in log.events if e["kind"] == "candidates")
            row[mode] = {
                "precision": p,
                "recall": r,
                "f1": f,
                "violations": int(viol),
                "seconds": secs,
                "candidates": cand,
            }
        rows.append(row)
        print(json.dumps(row), flush=True)
    (OUT / "synthetic.json").write_text(json.dumps({"rows": rows}, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["dev", "heldout", "jan-test", "synthetic"])
    a = ap.parse_args()
    if a.stage == "dev":
        run_dev()
    elif a.stage == "heldout":
        run_eval(HELDOUT, "heldout", "heldout_results.json")
    elif a.stage == "jan-test":
        run_eval(JAN, "test", "jan_test_results.json")
    else:
        run_synthetic()


if __name__ == "__main__":
    main()

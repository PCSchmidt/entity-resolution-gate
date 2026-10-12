"""Run the random-sample study from docs/PROTOCOL_SAMPLE.md.

    python scripts/run_sample.py dev        # tune one number per matcher on the development split, freeze
    python scripts/run_sample.py heldout    # score the held-out split ONCE with the frozen numbers
    python scripts/run_sample.py synthetic  # regression and scale check of the non-default pipeline variants

The registry UEI (`entity_id`) is the answer key and is never passed to a matcher. The primary metric is
B-cubed F1 (Deviation 2 of the protocol); pairwise F1 is reported alongside as a secondary.
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
from run_real import FUZZY_GRID, SPLINK_GRID, Matchers

from entity_resolution_gate import generate, pairwise_prf
from entity_resolution_gate.evaluation import (
    IntArray,
    bcubed_f1,
    bcubed_per_record,
    boot_f1,
    codes,
    pair_table,
    prf_counts,
    rid_pairs_to_positions,
)
from entity_resolution_gate.pipeline import AuditLog, Config, candidate_pairs, normalise, resolve

OUT = Path("results/sample")
DATA = Path("data/sample_records.jsonl")
GRID = [round(0.50 + 0.01 * k, 2) for k in range(50)]  # widened from 0.70-0.99: Deviation 3
SPLINK_GRID_SAMPLE = [*SPLINK_GRID, 0.995, 0.999, 0.9999]  # extended upward: Deviation 4
FINDABLE_RATIO = 50.0
BOOTSTRAPS = 2000
# name -> (blocking mode, name score)
PIPELINES: dict[str, tuple[str, str]] = {
    "pipeline_base": ("base", "max"),
    "pipeline_squash": ("squash", "max"),
    "pipeline_squash_first": ("squash_first", "max"),
    "pipeline_squash_first_wide": ("squash_first_wide", "max"),
    "pipeline_token_sort": ("base", "token_sort"),
}
SECONDARY = [k for k in PIPELINES if k != "pipeline_base"]
BONF = (
    100 * (0.025 / len(SECONDARY)),
    100 * (1 - 0.025 / len(SECONDARY)),
)  # 98.75% for four contrasts


def load(split: str) -> pl.DataFrame:
    rows = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines()]
    rows = sorted((r for r in rows if r["split"] == split), key=lambda r: r["rid"])
    df = pl.DataFrame(rows).select(["rid", "name", "address", "zip", "tax_id", "entity_id"])
    return df.with_columns(pl.col("zip").cast(pl.Utf8), pl.col("tax_id").cast(pl.Utf8))


def cfg(name: str, threshold: float) -> Config:
    blocking, score = PIPELINES[name]
    return Config(threshold=threshold, w_name=1.0, w_addr=0.0, blocking=blocking, name_score=score)


def pipeline_labels(df: pl.DataFrame, name: str, threshold: float) -> IntArray:
    out, _ = resolve(df, cfg(name, threshold))
    return np.asarray(out.sort("rid")["cluster_id"].to_numpy(), dtype=np.int64)


def pipeline_candidates(df: pl.DataFrame, name: str) -> set[tuple[int, int]]:
    return rid_pairs_to_positions(
        candidate_pairs(df, cfg(name, 0.9), AuditLog()), df["rid"].to_list()
    )


def score_row(param: float, labels: IntArray, ent: IntArray) -> dict[str, float]:
    p_rec, r_rec = bcubed_per_record(labels, ent)
    p, r, f = bcubed_f1(p_rec, r_rec)
    pp, pr, pf = prf_counts(labels, ent)
    return {"param": param, "precision": p, "recall": r, "f1": f, "pairwise_precision": pp, "pairwise_recall": pr, "pairwise_f1": pf}  # fmt: skip


def best_of(rows: list[dict[str, float]]) -> dict[str, float]:
    top = max(r["f1"] for r in rows)
    return max(
        (r for r in rows if r["f1"] == top), key=lambda r: r["param"]
    )  # ties go to the higher value


def run_dev() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = load("dev")
    ent = codes(df["entity_id"].to_list())
    m = Matchers(df)
    t0 = time.perf_counter()
    result: dict[str, Any] = {}
    result["exact"] = {"best": score_row(0.0, m.exact(), ent)}
    plans: list[tuple[str, Any, list[float]]] = [
        ("fuzzy", m.fuzzy, FUZZY_GRID),
        ("splink", m.splink, SPLINK_GRID_SAMPLE),
        ("splink_rich", m.splink_rich, SPLINK_GRID_SAMPLE),
    ]
    plans += [(n, (lambda t, n=n: pipeline_labels(df, n, t)), GRID) for n in PIPELINES]
    for name, fn, grid in plans:
        rows = [score_row(g, fn(g), ent) for g in grid]
        result[name] = {"best": best_of(rows), "sweep": rows}
        b = result[name]["best"]
        print(f"{name}: best dev B-cubed F1 {b['f1']:.3f} (P {b['precision']:.3f} R {b['recall']:.3f}) at {b['param']}  ({time.perf_counter() - t0:.0f}s)", flush=True)  # fmt: skip
    result["n_records"], result["n_entities"] = df.height, int(np.max(ent)) + 1
    (OUT / "dev_sweep.json").write_text(json.dumps(result, indent=1))
    frozen = {k: v["best"]["param"] for k, v in result.items() if isinstance(v, dict)}
    (OUT / "frozen.json").write_text(json.dumps(frozen, indent=1))
    print("frozen:", frozen)


def pct(a: npt.NDArray[np.float64], lo: float, hi: float) -> list[float]:
    return [float(np.percentile(a, lo)), float(np.percentile(a, hi))]


def run_heldout() -> None:
    out_path = OUT / "heldout_results.json"
    if out_path.exists():
        sys.exit(
            "heldout_results.json exists; this stage is one-shot (delete it deliberately to re-run)"
        )
    frozen = json.loads((OUT / "frozen.json").read_text())
    df = load("test")  # the builder calls the held-out half "test"
    names = [normalise(n) for n in df["name"].to_list()]
    ent = codes(df["entity_id"].to_list())
    n_ent = int(np.max(ent)) + 1
    m = Matchers(df)
    labels: dict[str, IntArray] = {
        "exact": m.exact(),
        "fuzzy": m.fuzzy(frozen["fuzzy"]),
        "splink": m.splink(frozen["splink"]),
        "splink_rich": m.splink_rich(frozen["splink_rich"]),
    }
    cands: dict[str, set[tuple[int, int]]] = {}
    for name in PIPELINES:
        labels[name] = pipeline_labels(df, name, frozen[name])
        cands[name] = pipeline_candidates(df, name)
    rng = np.random.default_rng(0)
    weights = [
        np.bincount(rng.integers(0, n_ent, n_ent), minlength=n_ent).astype(float)
        for _ in range(BOOTSTRAPS)
    ]
    per_rec = {k: bcubed_per_record(v, ent) for k, v in labels.items()}
    boots = {k: np.array([bcubed_f1(*per_rec[k], ent, w)[2] for w in weights]) for k in labels}
    tables = {k: pair_table(v, ent, names) for k, v in labels.items()}
    pboots = {k: np.array([boot_f1(tables[k], w) for w in weights]) for k in labels}
    base_t = pair_table(np.arange(len(names), dtype=np.int64), ent, names)
    keep = base_t["true"] & (base_t["tsr"] >= FINDABLE_RATIO)
    ii, jj, fe = base_t["i"][keep], base_t["j"][keep], base_t["ea"][keep]
    comp = {n: np.array([(int(a), int(b)) in c for a, b in zip(ii.tolist(), jj.tolist(), strict=True)]) for n, c in cands.items()}  # fmt: skip
    comp_boot = {n: np.array([float((w[fe] * c).sum() / max(1.0, w[fe].sum())) for w in weights]) for n, c in comp.items()}  # fmt: skip
    res: dict[str, Any] = {
        "n_records": df.height, "n_entities": n_ent, "frozen": frozen, "findable_true_pairs": len(ii),
        "matchers": {}, "P1_pipeline_base_minus_fuzzy": {}, "secondary_vs_pipeline_base": {},
    }  # fmt: skip
    for k, lab in labels.items():
        p, r, f = bcubed_f1(*per_rec[k])
        pp, pr, pf = prf_counts(lab, ent)
        t = tables[k]
        findable = t["true"] & (t["tsr"] >= FINDABLE_RATIO)
        fp = t["pred"] & ~t["true"]
        entry: dict[str, Any] = {
            "precision": p, "recall": r, "f1": f, "f1_ci95": pct(boots[k], 2.5, 97.5),
            "pairwise_precision": pp, "pairwise_recall": pr, "pairwise_f1": pf, "pairwise_f1_ci95": pct(pboots[k], 2.5, 97.5),
            "recall_findable": float((findable & t["pred"]).sum() / max(1, int(findable.sum()))),
            "false_positive_pairs": int(fp.sum()), "false_positive_same_name": int((fp & t["same_name"]).sum()),
            "n_clusters": len(np.unique(lab)),
        }  # fmt: skip
        if k in cands:
            entry["candidate_pairs"] = len(cands[k])
            entry["pair_completeness_findable"] = float(comp[k].mean())
        res["matchers"][k] = entry
    d = boots["pipeline_base"] - boots["fuzzy"]
    pd_ = pboots["pipeline_base"] - pboots["fuzzy"]
    res["P1_pipeline_base_minus_fuzzy"] = {
        "point": res["matchers"]["pipeline_base"]["f1"] - res["matchers"]["fuzzy"]["f1"], "ci95": pct(d, 2.5, 97.5),
        "pairwise_point": res["matchers"]["pipeline_base"]["pairwise_f1"] - res["matchers"]["fuzzy"]["pairwise_f1"],
        "pairwise_ci95": pct(pd_, 2.5, 97.5),
    }  # fmt: skip
    for k in SECONDARY:
        d = boots[k] - boots["pipeline_base"]
        c = comp_boot[k] - comp_boot["pipeline_base"]
        res["secondary_vs_pipeline_base"][k] = {
            "f1_difference": res["matchers"][k]["f1"] - res["matchers"]["pipeline_base"]["f1"],
            "f1_ci95": pct(d, 2.5, 97.5), "f1_ci_bonferroni98_75": pct(d, BONF[0], BONF[1]),
            "completeness_difference": float(comp[k].mean() - comp["pipeline_base"].mean()),
            "completeness_ci95": pct(c, 2.5, 97.5),
            "candidate_ratio": len(cands[k]) / max(1, len(cands["pipeline_base"])),
        }  # fmt: skip
    out_path.write_text(json.dumps(res, indent=1))
    for k, e in res["matchers"].items():
        print(f"{k:28s} B3 P {e['precision']:.3f} R {e['recall']:.3f} F1 {e['f1']:.3f} {[round(x, 3) for x in e['f1_ci95']]} | pairwise F1 {e['pairwise_f1']:.3f}")  # fmt: skip
    print("P1", json.dumps(res["P1_pipeline_base_minus_fuzzy"]))
    for k, v in res["secondary_vs_pipeline_base"].items():
        print(k, json.dumps(v))


def run_synthetic() -> None:
    rows = []
    for n, seed in [(1000, 2), (1000, 3), (5000, 2), (20000, 2)]:
        df = generate(n, seed=seed)
        row: dict[str, Any] = {"entities": n, "seed": seed, "records": df.height}
        for name, (blocking, score) in PIPELINES.items():
            t0 = time.perf_counter()
            out, log = resolve(df, Config(blocking=blocking, name_score=score))
            secs = time.perf_counter() - t0
            p, r, f = pairwise_prf(out)
            viol = sum(
                len({x for x in g["tax_id"].to_list() if x}) > 1
                for _, g in out.group_by("cluster_id")
            )
            cand = next(e["n"] for e in log.events if e["kind"] == "candidates")
            row[name] = {"precision": p, "recall": r, "f1": f, "violations": int(viol), "seconds": secs, "candidates": cand}  # fmt: skip
        rows.append(row)
        print(json.dumps(row), flush=True)
    (OUT / "synthetic.json").write_text(json.dumps({"rows": rows}, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["dev", "heldout", "synthetic"])
    a = ap.parse_args()
    {"dev": run_dev, "heldout": run_heldout, "synthetic": run_synthetic}[a.stage]()


if __name__ == "__main__":
    main()

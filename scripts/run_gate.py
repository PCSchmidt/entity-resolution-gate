"""Run the registry-ID gate study from docs/PROTOCOL_GATE.md.

    python scripts/run_gate.py dev        # tune one number per matcher on the 30 development slices, freeze
    python scripts/run_gate.py heldout    # score the 30 held-out slices ONCE with the frozen numbers

Every slice is a separate deduplication job. The company number (`entity_id`) is the answer key; it reaches a
matcher only as the "registry ID" on records where it is visible (probability q, fixed per-record hash).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd  # type: ignore[import-untyped]
import polars as pl
import splink.comparison_library as cl
from rapidfuzz import fuzz, process
from splink import DuckDBAPI, Linker, SettingsCreator, block_on

from entity_resolution_gate.evaluation import (
    IntArray,
    bcubed_f1,
    bcubed_per_record,
    codes,
    components,
    pair_table,
)
from entity_resolution_gate.pipeline import Config, normalise, resolve

DATA = Path("data/gate_records.jsonl")
OUT = Path("results/gate")
Q_LEVELS = (0.25, 0.5, 1.0)
PRIMARY_Q = 0.5
BOOTSTRAPS = 2000
RENAME_RATIO = 50.0
COARSE = [round(0.60 + 0.04 * k, 2) for k in range(10)]  # 0.60 .. 0.96
SPLINK_GRID = [round(0.01 * k, 2) for k in range(1, 100)] + [0.995, 0.999, 0.9999]
FUZZY_GRID = [float(t) for t in range(50, 101)]
PIPELINES = ("P_name", "P_addr", "P_veto", "P_match", "P_full")
ID_PIPELINES = ("P_veto", "P_match", "P_full")
SLICE_STRIDE = 1_000_000


def cfg_for(variant: str, threshold: float) -> Config:
    name_only = variant == "P_name"
    return Config(
        threshold=threshold,
        w_name=1.0 if name_only else 0.7,
        w_addr=0.0 if name_only else 0.3,
        tax_veto=variant in ("P_veto", "P_full"),
        tax_match=variant in ("P_match", "P_full"),
        tax_blocking=variant in ("P_match", "P_full"),
    )


def u_of(rid: int) -> float:
    return int.from_bytes(hashlib.sha256(str(rid).encode()).digest()[:8], "big") / 2**64


class Split:
    def __init__(self, name: str) -> None:
        rows = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines()]
        self.rows = sorted((r for r in rows if r["split"] == name), key=lambda r: r["rid"])
        self.n = len(self.rows)
        self.rid = [r["rid"] for r in self.rows]
        self.entity = [r["entity_id"] for r in self.rows]
        self.ent = codes(self.entity)
        self.slice_raw = [r["slice"] for r in self.rows]
        self.slices = sorted(set(self.slice_raw))
        self.slice_idx = np.array([self.slices.index(s) for s in self.slice_raw], dtype=np.int64)
        self.names = [normalise(r["name"]) for r in self.rows]
        self.members = {k: np.where(self.slice_idx == k)[0] for k in range(len(self.slices))}
        self._frames: dict[float, list[pl.DataFrame]] = {}
        self._sim: list[npt.NDArray[np.uint8]] | None = None

    def visible(self, q: float) -> list[str | None]:
        return [e if u_of(rid) < q else None for rid, e in zip(self.rid, self.entity, strict=True)]

    def frames(self, q: float) -> list[pl.DataFrame]:
        if q not in self._frames:
            vis = self.visible(q)
            frames = []
            for k in range(len(self.slices)):
                idx = self.members[k]
                frames.append(
                    pl.DataFrame(
                        {
                            "rid": [self.rid[i] for i in idx],
                            "name": [self.rows[i]["name"] for i in idx],
                            "address": [self.rows[i]["address"] for i in idx],
                            "zip": [self.rows[i]["zip"] or None for i in idx],
                            "tax_id": [vis[i] for i in idx],
                            "entity_id": [self.entity[i] for i in idx],
                        },
                        schema_overrides={"zip": pl.Utf8, "tax_id": pl.Utf8, "address": pl.Utf8},
                    )
                )
            self._frames[q] = frames
        return self._frames[q]

    def stitch(self, per_slice: list[IntArray]) -> IntArray:
        out = np.zeros(self.n, dtype=np.int64)
        for k, lab in enumerate(per_slice):
            out[self.members[k]] = lab + k * SLICE_STRIDE
        return out


def _resolve_one(args: tuple[pl.DataFrame, Config]) -> IntArray:
    df, cfg = args
    out, _ = resolve(df, cfg)
    return np.asarray(out.sort("rid")["cluster_id"].to_numpy(), dtype=np.int64)


def pipeline_labels(
    sp: Split, pool: ProcessPoolExecutor, variant: str, threshold: float, q: float
) -> IntArray:
    cfg = cfg_for(variant, threshold)
    return sp.stitch(list(pool.map(_resolve_one, [(f, cfg) for f in sp.frames(q)])))


def exact_labels(sp: Split) -> IntArray:
    return codes([f"{s}|{n}" for s, n in zip(sp.slice_idx.tolist(), sp.names, strict=True)])


def fuzzy_labels(sp: Split, t: float) -> IntArray:
    if sp._sim is None:
        sp._sim = [
            process.cdist([sp.names[i] for i in sp.members[k]], [sp.names[i] for i in sp.members[k]], scorer=fuzz.token_sort_ratio, dtype=np.uint8, workers=-1)
            for k in range(len(sp.slices))
        ]  # fmt: skip
    per = []
    for k, sim in enumerate(sp._sim):
        ii, jj = np.where(np.triu(sim >= t, k=1))
        per.append(components(len(sp.members[k]), ii.astype(np.int64), jj.astype(np.int64)))
    return sp.stitch(per)


class SplinkID:
    """Splink with name, postcode and registry-ID comparisons, blocked within the slice."""

    def __init__(self, sp: Split, q: float) -> None:
        vis = sp.visible(q)
        toks = [s.split() for s in sp.names]
        pdf = pd.DataFrame(
            {
                "unique_id": range(sp.n),
                "slice": sp.slice_idx.tolist(),
                "name": sp.names,
                "first_token": [(t[0] if t else f"_empty{i}") for i, t in enumerate(toks)],
                "first3": [
                    (s[:3] if len(s) >= 3 else f"_short{i}") for i, s in enumerate(sp.names)
                ],
                "zip": [r["zip"] or None for r in sp.rows],
                "registry_id": vis,
            }
        )
        settings = SettingsCreator(
            link_type="dedupe_only",
            comparisons=[cl.JaroWinklerAtThresholds("name", [0.92, 0.80]), cl.ExactMatch("zip"), cl.ExactMatch("registry_id")],
            blocking_rules_to_generate_predictions=[block_on("slice", "first_token"), block_on("slice", "first3"), block_on("registry_id")],
            probability_two_random_records_match=0.001,
        )  # fmt: skip
        self.linker = Linker(DuckDBAPI().register(pdf), settings, log_level="ERROR")
        self.linker.training.estimate_u_using_random_sampling(max_pairs=5_000_000, seed=0)
        self.linker.training.estimate_parameters_using_expectation_maximisation(
            block_on("slice", "first_token")
        )
        if q > 0:
            self.linker.training.estimate_parameters_using_expectation_maximisation(
                block_on("registry_id")
            )
        self.pred = self.linker.inference.predict(threshold_match_probability=min(SPLINK_GRID))
        self.sp = sp

    def labels(self, p: float) -> IntArray:
        df = self.linker.clustering.cluster_pairwise_predictions_at_threshold(
            self.pred, p
        ).as_pandas_dataframe()  # type: ignore[no-untyped-call]
        lab = dict(zip(df["unique_id"].tolist(), df["cluster_id"].tolist(), strict=True))
        return codes([lab[i] for i in range(self.sp.n)])


def b3_f1(sp: Split, labels: IntArray) -> float:
    return bcubed_f1(*bcubed_per_record(labels, sp.ent))[2]


def best_of(scores: dict[float, float]) -> float:
    top = max(scores.values())
    return max(t for t, s in scores.items() if s == top)  # ties go to the higher value


def tune_pipeline(
    sp: Split, pool: ProcessPoolExecutor, variant: str, q: float
) -> tuple[float, dict[float, float]]:
    scores = {t: b3_f1(sp, pipeline_labels(sp, pool, variant, t, q)) for t in COARSE}
    best = best_of(scores)
    for t in sorted({round(best + d / 100, 2) for d in range(-3, 4)} - set(scores)):
        if 0.5 <= t <= 0.99:
            scores[t] = b3_f1(sp, pipeline_labels(sp, pool, variant, t, q))
    return best_of(scores), scores


def run_dev() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sp = Split("dev")
    frozen: dict[str, float] = {}
    sweeps: dict[str, Any] = {"n_records": sp.n, "n_slices": len(sp.slices)}
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=12) as pool:
        frozen["exact"] = 0.0
        sweeps["exact"] = {"f1": b3_f1(sp, exact_labels(sp))}
        fz = {t: b3_f1(sp, fuzzy_labels(sp, t)) for t in FUZZY_GRID}
        frozen["fuzzy"] = best_of(fz)
        sweeps["fuzzy"] = {"best": frozen["fuzzy"], "f1": fz[frozen["fuzzy"]]}
        print(
            f"fuzzy: dev B-cubed F1 {fz[frozen['fuzzy']]:.4f} at {frozen['fuzzy']}  ({time.perf_counter() - t0:.0f}s)",
            flush=True,
        )
        plan: list[tuple[str, float]] = [("P_name", 0.0), ("P_addr", 0.0)] + [
            (v, q) for v in ID_PIPELINES for q in Q_LEVELS
        ]
        for variant, q in plan:
            key = variant if q == 0.0 else f"{variant}@{q}"
            best, scores = tune_pipeline(sp, pool, variant, q)
            frozen[key] = best
            sweeps[key] = {
                "best": best,
                "f1": scores[best],
                "scores": {str(k): v for k, v in sorted(scores.items())},
            }
            print(
                f"{key}: dev B-cubed F1 {scores[best]:.4f} at {best}  ({time.perf_counter() - t0:.0f}s)",
                flush=True,
            )
        for q in Q_LEVELS:
            si = SplinkID(sp, q)
            sc = {p: b3_f1(sp, si.labels(p)) for p in SPLINK_GRID}
            key = f"splink_id@{q}"
            frozen[key] = best_of(sc)
            sweeps[key] = {"best": frozen[key], "f1": sc[frozen[key]]}
            print(
                f"{key}: dev B-cubed F1 {sc[frozen[key]]:.4f} at {frozen[key]}  ({time.perf_counter() - t0:.0f}s)",
                flush=True,
            )
    (OUT / "dev_sweep.json").write_text(json.dumps(sweeps, indent=1))
    (OUT / "frozen.json").write_text(json.dumps(frozen, indent=1))
    print("frozen:", frozen)


def slice_stats(sp: Split, labels: IntArray, vis: list[str | None]) -> dict[str, Any]:
    """Per-slice sufficient statistics, so the slice bootstrap needs no recomputation."""
    p_rec, r_rec = bcubed_per_record(labels, sp.ent)
    out: dict[str, list[float]] = {
        k: [] for k in ("n", "sp", "sr", "tp", "pred", "true", "rename_true", "rename_found")
    }
    for k in range(len(sp.slices)):
        idx = sp.members[k]
        lab, ent = labels[idx], sp.ent[idx]
        out["n"].append(float(len(idx)))
        out["sp"].append(float(p_rec[idx].sum()))
        out["sr"].append(float(r_rec[idx].sum()))
        t = pair_table(lab, ent, [sp.names[i] for i in idx])
        out["tp"].append(float((t["true"] & t["pred"]).sum()))
        out["pred"].append(float(t["pred"].sum()))
        out["true"].append(float(t["true"].sum()))
        rename = t["true"] & (t["tsr"] < RENAME_RATIO)
        out["rename_true"].append(float(rename.sum()))
        out["rename_found"].append(float((rename & t["pred"]).sum()))
    members: dict[int, set[str]] = {}
    for lab_i, v in zip(labels.tolist(), vis, strict=True):
        if v is not None:
            members.setdefault(lab_i, set()).add(v)
    violations = sum(1 for s in members.values() if len(s) > 1)
    res: dict[str, Any] = {k: np.array(v) for k, v in out.items()}
    res["violating_clusters"] = violations
    return res


def metric(st: dict[str, Any], w: npt.NDArray[np.float64], name: str) -> float:
    if name == "b3_f1":
        n = float((w * st["n"]).sum())
        p, r = float((w * st["sp"]).sum()) / n, float((w * st["sr"]).sum()) / n
        return 2 * p * r / (p + r) if p + r else 0.0
    if name == "pw_f1":
        tp, pr, tr = (float((w * st[k]).sum()) for k in ("tp", "pred", "true"))
        p, r = (tp / pr if pr else 1.0), (tp / tr if tr else 1.0)
        return 2 * p * r / (p + r) if p + r else 0.0
    if name == "b3_p":
        return float((w * st["sp"]).sum() / (w * st["n"]).sum())
    if name == "b3_r":
        return float((w * st["sr"]).sum() / (w * st["n"]).sum())
    if name == "rename_recall":
        d = float((w * st["rename_true"]).sum())
        return float((w * st["rename_found"]).sum()) / d if d else 0.0
    raise KeyError(name)


def pct(a: npt.NDArray[np.float64], lo: float = 2.5, hi: float = 97.5) -> list[float]:
    return [float(np.percentile(a, lo)), float(np.percentile(a, hi))]


def run_heldout() -> None:
    out_path = OUT / "heldout_results.json"
    if out_path.exists():
        sys.exit(
            "heldout_results.json exists; this stage is one-shot (delete it deliberately to re-run)"
        )
    frozen = json.loads((OUT / "frozen.json").read_text())
    sp = Split("heldout")
    n_sl = len(sp.slices)
    rng = np.random.default_rng(0)
    draws = [
        np.bincount(rng.integers(0, n_sl, n_sl), minlength=n_sl).astype(float)
        for _ in range(BOOTSTRAPS)
    ]
    ones = np.ones(n_sl)
    stats: dict[str, dict[str, Any]] = {}
    with ProcessPoolExecutor(max_workers=12) as pool:
        base: dict[str, IntArray] = {
            "no_merge": np.arange(
                sp.n, dtype=np.int64
            ),  # reference: every record alone (Deviation 1)
            "exact": exact_labels(sp),
            "fuzzy": fuzzy_labels(sp, frozen["fuzzy"]),
            "P_name": pipeline_labels(sp, pool, "P_name", frozen["P_name"], 0.0),
            "P_addr": pipeline_labels(sp, pool, "P_addr", frozen["P_addr"], 0.0),
        }
        for q in Q_LEVELS:
            vis = sp.visible(q)
            for name, lab in base.items():
                stats[f"{name}#vis{q}"] = slice_stats(sp, lab, vis)
            for v in ID_PIPELINES:
                key = f"{v}@{q}"
                stats[key] = slice_stats(sp, pipeline_labels(sp, pool, v, frozen[key], q), vis)
            si = SplinkID(sp, q)
            stats[f"splink_id@{q}"] = slice_stats(sp, si.labels(frozen[f"splink_id@{q}"]), vis)
            print(f"q={q} done", flush=True)
    names = {f"{n}": stats[f"{n}#vis{PRIMARY_Q}"] for n in base} | {
        k: v for k, v in stats.items() if "@" in k
    }
    res: dict[str, Any] = {
        "n_records": sp.n,
        "n_slices": n_sl,
        "frozen": frozen,
        "matchers": {},
        "contrasts": {},
        "per_slice_b3_f1": {},
    }
    for key, st in names.items():
        boots = {m: np.array([metric(st, w, m) for w in draws]) for m in ("b3_f1", "pw_f1")}
        e: dict[str, Any] = {
            m: metric(st, ones, m) for m in ("b3_p", "b3_r", "b3_f1", "pw_f1", "rename_recall")
        }
        e["b3_f1_ci95"], e["pw_f1_ci95"] = pct(boots["b3_f1"]), pct(boots["pw_f1"])
        e["false_merge_pairs"] = float(st["pred"].sum() - st["tp"].sum())
        e["violating_clusters_visible_ids"] = st["violating_clusters"]
        res["matchers"][key] = e
    res["violations_by_q"] = {
        f"{n}#vis{q}": stats[f"{n}#vis{q}"]["violating_clusters"] for n in base for q in Q_LEVELS
    }

    def contrast(
        a: str, b: str, metric_name: str = "b3_f1", band: tuple[float, float] = (2.5, 97.5)
    ) -> dict[str, Any]:
        d = np.array(
            [metric(stats[a], w, metric_name) - metric(stats[b], w, metric_name) for w in draws]
        )
        return {
            "point": metric(stats[a], ones, metric_name) - metric(stats[b], ones, metric_name),
            "ci": pct(d, *band),
        }

    for q in Q_LEVELS:
        pa = f"P_addr#vis{q}"
        c: dict[str, Any] = {
            "G1_P_full_minus_P_addr": contrast(f"P_full@{q}", pa),
            "G3a_P_veto_minus_P_addr_ci97_5": contrast(f"P_veto@{q}", pa, band=(1.25, 98.75)),
            "G3b_P_match_minus_P_addr_ci97_5": contrast(f"P_match@{q}", pa, band=(1.25, 98.75)),
            "G4_P_full_minus_splink_id": contrast(f"P_full@{q}", f"splink_id@{q}"),
            "G5_P_addr_minus_P_name": contrast(pa, f"P_name#vis{q}"),
            "pairwise_P_full_minus_P_addr": contrast(f"P_full@{q}", pa, "pw_f1"),
            "ref_P_full_minus_no_merge": contrast(f"P_full@{q}", f"no_merge#vis{q}"),
            "ref_P_addr_minus_no_merge": contrast(pa, f"no_merge#vis{q}"),
            "ref_fuzzy_minus_no_merge": contrast(f"fuzzy#vis{q}", f"no_merge#vis{q}"),
        }
        res["contrasts"][f"q={q}"] = c
    for key in (f"P_addr#vis{PRIMARY_Q}", f"P_full@{PRIMARY_Q}", f"fuzzy#vis{PRIMARY_Q}"):
        st = stats[key]
        res["per_slice_b3_f1"][key] = [
            (2 * (a / n) * (b / n) / ((a / n) + (b / n))) if (a + b) else 0.0
            for a, b, n in zip(st["sp"].tolist(), st["sr"].tolist(), st["n"].tolist(), strict=True)
        ]
    out_path.write_text(json.dumps(res, indent=1))
    for key, e in res["matchers"].items():
        print(f"{key:20s} B3 P {e['b3_p']:.3f} R {e['b3_r']:.3f} F1 {e['b3_f1']:.3f} {[round(x, 3) for x in e['b3_f1_ci95']]} | rename recall {e['rename_recall']:.3f} | false-merge pairs {e['false_merge_pairs']:.0f} | violating clusters {e['violating_clusters_visible_ids']}")  # fmt: skip
    for qk, c in res["contrasts"].items():
        for ck, v in c.items():
            print(qk, ck, f"{v['point']:+.4f}", [round(x, 4) for x in v["ci"]])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["dev", "heldout"])
    a = ap.parse_args()
    {"dev": run_dev, "heldout": run_heldout}[a.stage]()


if __name__ == "__main__":
    main()

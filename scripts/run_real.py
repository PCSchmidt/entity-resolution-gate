"""Run the real-data study from docs/PROTOCOL_REAL.md.

    python scripts/run_real.py dev     # sweep one number per matcher on development, freeze it
    python scripts/run_real.py test    # score the test split ONCE with the frozen numbers

The UEI (`entity_id`) is the answer key and is never passed to a matcher.
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
import pandas as pd  # type: ignore[import-untyped]
import polars as pl
import splink.comparison_library as cl
from rapidfuzz import fuzz, process
from splink import DuckDBAPI, Linker, SettingsCreator, block_on

from entity_resolution_gate.evaluation import (
    IntArray,
    boot_f1,
    codes,
    components,
    pair_table,
    prf_counts,
    rid_pairs_to_positions,
)
from entity_resolution_gate.pipeline import AuditLog, Config, candidate_pairs, normalise, resolve

DATA = Path("data/real_records.jsonl")
OUT = Path("results/real")
FUZZY_GRID = [float(t) for t in range(50, 101)]
SPLINK_GRID = [round(0.01 * k, 2) for k in range(1, 100)]  # widened from 0.50-0.99: Deviation 1
GATE_GRID = [round(0.70 + 0.01 * k, 2) for k in range(30)]
SPLINK_PRIOR = 0.001  # fixed; only shifts match probabilities, which the tuned threshold absorbs
FINDABLE_RATIO = 50.0
BOOTSTRAPS = 2000


def load(split: str) -> pl.DataFrame:
    rows = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines()]
    rows = [r for r in rows if r["split"] == split]
    df = pl.DataFrame(rows).select(["rid", "name", "address", "zip", "tax_id", "entity_id"])
    return df.with_columns(pl.col("zip").cast(pl.Utf8), pl.col("tax_id").cast(pl.Utf8))


class Matchers:
    """Each matcher is prepared once per split; `labels(param)` gives cluster labels for one tuned value."""

    def __init__(self, df: pl.DataFrame) -> None:
        self.df = df
        self.names = [normalise(n) for n in df["name"].to_list()]
        self.n = df.height
        self._sim: npt.NDArray[np.uint8] | None = None
        self._splink: dict[bool, tuple[Linker, Any]] = {}

    def exact(self) -> IntArray:
        return codes(self.names)

    def fuzzy(self, t: float) -> IntArray:
        if self._sim is None:
            self._sim = process.cdist(
                self.names, self.names, scorer=fuzz.token_sort_ratio, dtype=np.uint8, workers=-1
            )
        ii, jj = np.where(np.triu(self._sim >= t, k=1))
        return components(self.n, ii.astype(np.int64), jj.astype(np.int64))

    def gate(self, threshold: float) -> IntArray:
        out, _ = resolve(self.df, Config(threshold=threshold, w_name=1.0, w_addr=0.0))
        return np.asarray(out.sort("rid")["cluster_id"].to_numpy(), dtype=np.int64)

    def splink(self, p: float, rich: bool = False) -> IntArray:
        if rich not in self._splink:
            self._splink[rich] = self._train_splink(rich)
        linker, pred = self._splink[rich]
        cl_df = linker.clustering.cluster_pairwise_predictions_at_threshold(
            pred, p
        ).as_pandas_dataframe()  # type: ignore[no-untyped-call]
        lab = dict(zip(cl_df["unique_id"].tolist(), cl_df["cluster_id"].tolist(), strict=True))
        return codes([lab[i] for i in range(self.n)])

    def splink_rich(self, p: float) -> IntArray:
        return self.splink(p, rich=True)

    def _train_splink(self, rich: bool) -> tuple[Linker, Any]:
        toks = [s.split() for s in self.names]
        pdf = pd.DataFrame(
            {
                "unique_id": range(self.n),
                "name": self.names,
                "first_token": [(t[0] if t else f"_empty{i}") for i, t in enumerate(toks)],
                "first3": [
                    (s[:3] if len(s) >= 3 else f"_short{i}") for i, s in enumerate(self.names)
                ],
                "tokens": [sorted(set(t)) or [f"_empty{i}"] for i, t in enumerate(toks)],
            }
        )
        comparisons: list[Any] = [cl.JaroWinklerAtThresholds("name", [0.92, 0.80])]
        if rich:  # Deviation 2: token-overlap and first-token evidence, so Splink is not just a Jaro-Winkler threshold
            comparisons += [
                cl.ExactMatch("first_token"),
                cl.ArrayIntersectAtSizes("tokens", [2, 1]),
            ]
        settings = SettingsCreator(
            link_type="dedupe_only",
            comparisons=comparisons,
            blocking_rules_to_generate_predictions=[block_on("first_token"), block_on("first3")],
            probability_two_random_records_match=SPLINK_PRIOR,
        )
        linker = Linker(DuckDBAPI().register(pdf), settings, log_level="ERROR")
        linker.training.estimate_u_using_random_sampling(max_pairs=2_000_000, seed=0)
        linker.training.estimate_parameters_using_expectation_maximisation(block_on("first_token"))
        if rich:
            linker.training.estimate_parameters_using_expectation_maximisation(block_on("first3"))
        return linker, linker.inference.predict(threshold_match_probability=min(SPLINK_GRID))


def sweep(m: Matchers, fn: Any, grid: list[float], ent: IntArray) -> list[dict[str, float]]:
    rows = []
    for g in grid:
        p, r, f = prf_counts(fn(g), ent)
        rows.append({"param": g, "precision": p, "recall": r, "f1": f})
    return rows


def best(rows: list[dict[str, float]]) -> dict[str, float]:
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
    p, r, f = prf_counts(m.exact(), ent)
    result["exact"] = {
        "sweep": [{"param": 0.0, "precision": p, "recall": r, "f1": f}],
        "frozen": 0.0,
    }
    for name, fn, grid in [
        ("fuzzy", m.fuzzy, FUZZY_GRID),
        ("gate", m.gate, GATE_GRID),
        ("splink", m.splink, SPLINK_GRID),
        ("splink_rich", m.splink_rich, SPLINK_GRID),
    ]:
        rows = sweep(m, fn, grid, ent)
        result[name] = {"sweep": rows, "frozen": best(rows)["param"]}
        print(
            f"{name}: best dev F1 {best(rows)['f1']:.3f} at {best(rows)['param']}  ({time.perf_counter() - t0:.0f}s)",
            flush=True,
        )
    (OUT / "dev_sweep.json").write_text(json.dumps(result, indent=1))
    frozen = {k: v["frozen"] for k, v in result.items()}
    frozen["gate_default"] = Config().threshold
    (OUT / "frozen.json").write_text(json.dumps(frozen, indent=1))
    print("frozen:", frozen)


def run_test() -> None:
    out_path = OUT / "test_results.json"
    if out_path.exists():
        sys.exit(
            "test already run once; refusing to re-run (delete results/real/test_results.json deliberately)"
        )
    frozen = json.loads((OUT / "frozen.json").read_text())
    df = load("test")
    ent = codes(df["entity_id"].to_list())
    m = Matchers(df)
    runs: dict[str, IntArray] = {
        "exact": m.exact(),
        "fuzzy": m.fuzzy(frozen["fuzzy"]),
        "splink": m.splink(frozen["splink"]),
        "splink_rich": m.splink_rich(frozen["splink_rich"]),
        "gate": m.gate(frozen["gate"]),
        "gate_default": m.gate(frozen["gate_default"]),
    }
    n_ent = int(np.max(ent)) + 1
    rng = np.random.default_rng(0)
    weights = [
        np.bincount(rng.integers(0, n_ent, n_ent), minlength=n_ent).astype(float)
        for _ in range(BOOTSTRAPS)
    ]
    tables = {k: pair_table(v, ent, m.names) for k, v in runs.items()}
    boots = {k: np.array([boot_f1(tables[k], w) for w in weights]) for k in runs}
    results: dict[str, Any] = {
        "n_records": df.height,
        "n_entities": n_ent,
        "frozen": frozen,
        "matchers": {},
    }
    for k, labels in runs.items():
        t = tables[k]
        p, r, f = prf_counts(labels, ent)
        true_pairs = t["true"]
        findable = true_pairs & (t["tsr"] >= FINDABLE_RATIO)
        hard = true_pairs & (t["tsr"] < FINDABLE_RATIO)
        fp = t["pred"] & ~t["true"]
        entry: dict[str, Any] = {
            "precision": p, "recall": r, "f1": f,
            "f1_ci95": [float(np.percentile(boots[k], 2.5)), float(np.percentile(boots[k], 97.5))],
            "n_clusters": len(np.unique(labels)),
            "true_pairs": int(true_pairs.sum()), "findable_pairs": int(findable.sum()), "not_findable_pairs": int(hard.sum()),
            "recall_findable": float((findable & t["pred"]).sum() / max(1, int(findable.sum()))),
            "recall_not_findable": float((hard & t["pred"]).sum() / max(1, int(hard.sum()))),
            "false_positive_pairs": int(fp.sum()),
            "false_positive_same_name_diff_registration": int((fp & t["same_name"]).sum()),
        }  # fmt: skip
        if k != "fuzzy":
            d = boots[k] - boots["fuzzy"]
            entry["f1_minus_fuzzy_boot_ci95"] = [
                float(np.percentile(d, 2.5)),
                float(np.percentile(d, 97.5)),
            ]
        results["matchers"][k] = entry
        print(
            f"{k}: P {p:.3f} R {r:.3f} F1 {f:.3f} CI {entry['f1_ci95'][0]:.3f}-{entry['f1_ci95'][1]:.3f}",
            flush=True,
        )
    f_fuzzy = results["matchers"]["fuzzy"]["f1"]
    for k, entry in results["matchers"].items():
        if k != "fuzzy":
            entry["f1_minus_fuzzy"] = float(entry["f1"] - f_fuzzy)
    # C4: for the pipeline, true pairs never scored (blocking) versus scored and rejected
    cand = rid_pairs_to_positions(
        candidate_pairs(df, Config(threshold=frozen["gate"], w_name=1.0, w_addr=0.0), AuditLog()),
        df["rid"].to_list(),
    )  # record ids are global across splits; the pair table is positional
    t = tables["gate"]
    missed = t["true"] & ~t["pred"]
    blocked_out = sum(
        1
        for a, b in zip(t["i"][missed].tolist(), t["j"][missed].tolist(), strict=True)
        if (a, b) not in cand
    )
    results["gate_missed_true_pairs"] = {
        "total": int(missed.sum()),
        "never_scored_by_blocking": blocked_out,
    }
    out_path.write_text(json.dumps(results, indent=1))
    print(json.dumps(results["gate_missed_true_pairs"]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["dev", "test"])
    args = ap.parse_args()
    run_dev() if args.mode == "dev" else run_test()


if __name__ == "__main__":
    main()

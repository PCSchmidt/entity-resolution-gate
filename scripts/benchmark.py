"""Held-out synthetic benchmark (seeds 2+; threshold was chosen on seed 1 only).

Usage: python scripts/benchmark.py
"""

from __future__ import annotations

import time

import polars as pl

from entity_resolution_gate import generate, pairwise_prf, resolve


def violations(out: pl.DataFrame) -> int:
    n = 0
    for _, g in out.group_by("cluster_id"):
        n += len({t for t in g["tax_id"].to_list() if t}) > 1
    return n


def main() -> None:
    print("| Entities | Records | Precision | Recall | F1 | Tax-ID violations | Seconds |")
    print("|---|---|---|---|---|---|---|")
    for n, seed in [(1000, 2), (1000, 3), (5000, 2), (20000, 2)]:
        df = generate(n, seed=seed)
        t = time.perf_counter()
        out, _ = resolve(df)
        secs = time.perf_counter() - t
        p, r, f = pairwise_prf(out)
        print(f"| {n} (seed {seed}) | {df.height} | {p:.3f} | {r:.3f} | {f:.3f} | {violations(out)} | {secs:.1f} |")


if __name__ == "__main__":
    main()

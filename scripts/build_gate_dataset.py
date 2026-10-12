"""Build the dense-neighbourhood dataset for the registry-ID study (docs/PROTOCOL_GATE.md).

Source: the UK Companies House free company data snapshot (all live companies). Every company name string
(the current name and up to ten previous names) is normalised with a simple lower-case, alphanumeric-only rule
and the whole population is sorted by it. K random, non-overlapping, contiguous slices of the sorted list are
taken. A company belongs to a slice if ANY of its name strings falls inside it; it then contributes ALL of its
name strings (so its name history is intact) while every lookalike neighbour inside the slice is present at its
full density. Companies that fall in more than one slice are dropped from all of them.

The company number is the answer key and the "registry ID" the pipeline may use. The registered office address
is attached only to the current-name record (a previous name has no known historical address).

    python scripts/build_gate_dataset.py --parquet data/companies_house/companies.parquet \
        --out data/gate_records.jsonl --slices 60 --width 800 --seed 0
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import polars as pl

PREV = [f"PreviousName_{i}_CompanyName" for i in range(1, 11)]


def simple_norm(col: pl.Expr) -> pl.Expr:
    return col.str.to_lowercase().str.replace_all(r"[^a-z0-9]+", " ").str.strip_chars()


def name_table(df: pl.DataFrame) -> pl.DataFrame:
    """One row per (company, name string): kind is 'current' or 'previous'."""
    parts = [
        df.select(
            "CompanyNumber", pl.col("CompanyName").alias("name"), pl.lit("current").alias("kind")
        )
    ]
    for c in PREV:
        parts.append(
            df.filter(pl.col(c).is_not_null() & (pl.col(c) != "")).select(
                "CompanyNumber", pl.col(c).alias("name"), pl.lit("previous").alias("kind")
            )
        )
    long = pl.concat(parts).with_columns(simple_norm(pl.col("name")).alias("norm"))
    return long.filter(pl.col("norm") != "").sort(["norm", "CompanyNumber", "kind"])


def choose_slices(n_strings: int, k: int, width: int, seed: int) -> list[tuple[int, int]]:
    rng = random.Random(seed)
    chosen: list[tuple[int, int]] = []
    while len(chosen) < k:
        start = rng.randrange(0, n_strings - width)
        if all(start + width <= s or e <= start for s, e in chosen):
            chosen.append((start, start + width))
    return sorted(chosen)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--slices", type=int, default=60)
    ap.add_argument("--width", type=int, default=800)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--exclude-from", type=Path, default=None,
        help="records file whose companies (entity_id) are dropped, to build slices disjoint from an earlier set",
    )  # fmt: skip
    args = ap.parse_args()

    df = pl.read_parquet(args.parquet)
    long = name_table(df).with_row_index("rank")
    slices = choose_slices(long.height, args.slices, args.width, args.seed)
    rank_to_slice = pl.DataFrame(
        {"s": list(range(len(slices))), "lo": [a for a, _ in slices], "hi": [b for _, b in slices]}
    )
    in_slice = (
        long.join(rank_to_slice, how="cross")
        .filter((pl.col("rank") >= pl.col("lo")) & (pl.col("rank") < pl.col("hi")))
        .select("CompanyNumber", pl.col("s").alias("slice"))
        .unique()
    )
    multi = (
        in_slice.group_by("CompanyNumber")
        .agg(pl.col("slice").n_unique().alias("n"))
        .filter(pl.col("n") > 1)
    )
    dropped = multi.height
    members = in_slice.join(multi.select("CompanyNumber"), on="CompanyNumber", how="anti")
    if args.exclude_from is not None:
        used = {
            json.loads(x)["entity_id"]
            for x in args.exclude_from.read_text(encoding="utf-8").splitlines()
        }
        before = members["CompanyNumber"].n_unique()
        members = members.filter(~pl.col("CompanyNumber").is_in(list(used)))
        print(f"excluded {before - members['CompanyNumber'].n_unique()} companies already used in {args.exclude_from}")
    addr = df.select(
        "CompanyNumber",
        pl.concat_str(
            [
                pl.col("RegAddress_AddressLine1").fill_null(""),
                pl.col("RegAddress_PostTown").fill_null(""),
            ],
            separator=" ",
        )
        .str.strip_chars()
        .alias("address"),
        pl.col("RegAddress_PostCode").fill_null("").alias("zip"),
    )
    rec = (
        long.join(members, on="CompanyNumber")
        .join(addr, on="CompanyNumber")
        .unique(subset=["CompanyNumber", "name"], keep="first", maintain_order=True)
        .with_columns(
            pl.when(pl.col("kind") == "current")
            .then(pl.col("address"))
            .otherwise(pl.lit(""))
            .alias("address"),
            pl.when(pl.col("kind") == "current")
            .then(pl.col("zip"))
            .otherwise(pl.lit(""))
            .alias("zip"),
        )
        .sort(["slice", "CompanyNumber", "kind", "name"])
    )
    split_rng = random.Random(args.seed + 1)
    order = list(range(len(slices)))
    split_rng.shuffle(order)
    half = len(order) // 2
    split_of = {s: ("dev" if i < half else "heldout") for i, s in enumerate(order)}
    rows = rec.to_dicts()
    with args.out.open("w", encoding="utf-8") as fh:
        for rid, r in enumerate(rows):
            fh.write(
                json.dumps(
                    {
                        "rid": rid,
                        "name": r["name"],
                        "entity_id": r["CompanyNumber"],
                        "slice": int(r["slice"]),
                        "split": split_of[int(r["slice"])],
                        "kind": r["kind"],
                        "address": r["address"],
                        "zip": r["zip"],
                    }
                )
                + "\n"
            )
    print(
        f"population name strings {long.height}; slices {len(slices)} of width {args.width}; companies in more than one slice (dropped) {dropped}"
    )
    for s in ("dev", "heldout"):
        sub = [r for r in rows if split_of[int(r["slice"])] == s]
        ents = {r["CompanyNumber"] for r in sub}
        print(
            f"{s}: {len(sub)} records, {len(ents)} companies, {sum(1 for r in sub if r['kind'] == 'previous')} previous-name records"
        )


if __name__ == "__main__":
    main()

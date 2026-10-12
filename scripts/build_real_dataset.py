"""Build name-only records from enriched USAspending profiles (see docs/PROTOCOL_REAL.md).

One record per distinct name string per UEI (the profile's name plus its alternate names). The UEI is the
answer key (`entity_id`) and is never a matcher input. Entities are split by a hash of the UEI so no entity
appears in both splits.

    python scripts/build_real_dataset.py --profiles data/profiles_2024-01.jsonl --out data/real_records.jsonl

For a fresh held-out month (docs/PROTOCOL_BLOCKING.md), drop every entity seen in an earlier month and put
the rest in one split:

    python scripts/build_real_dataset.py --profiles data/profiles_2024-07.jsonl --out data/heldout_2024-07.jsonl         --exclude-from data/profiles_2024-01.jsonl --split-name heldout
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def split_of(uei: str) -> str:
    return "dev" if hashlib.sha256(uei.encode()).digest()[0] % 2 == 0 else "test"


def build(
    profile_rows: list[dict[str, object]],
    exclude: set[str] | None = None,
    split_name: str | None = None,
    max_names: int | None = None,
) -> list[dict[str, object]]:
    names: dict[str, set[str]] = {}
    for row in profile_rows:
        prof = row.get("profile")
        uei = row.get("uei") or (prof.get("uei") if isinstance(prof, dict) else None)
        if not isinstance(prof, dict) or not isinstance(uei, str) or not uei:
            continue
        if exclude and uei in exclude:
            continue
        found = {
            n
            for n in [prof.get("name"), *(prof.get("alternate_names") or [])]
            if isinstance(n, str) and n.strip()
        }
        names.setdefault(uei, set()).update(found)
    if (
        max_names is not None
    ):  # pass-through / aggregate registrants whose alias list is not name variants
        names = {u: n for u, n in names.items() if len(n) <= max_names}
    out: list[dict[str, object]] = []
    for uei in sorted(names):
        for name in sorted(names[uei]):
            out.append(
                {
                    "name": name,
                    "entity_id": uei,
                    "split": split_name or split_of(uei),
                    "address": "",
                    "zip": None,
                    "tax_id": None,
                }
            )
    for rid, rec in enumerate(out):
        rec["rid"] = rid
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument(
        "--exclude-from", type=Path, default=None, help="profiles file whose UEIs are dropped"
    )
    ap.add_argument("--split-name", default=None, help="put every record in this single split")
    ap.add_argument(
        "--max-names", type=int, default=None, help="drop entities with more name strings than this"
    )
    args = ap.parse_args()
    rows = [json.loads(line) for line in args.profiles.read_text(encoding="utf-8").splitlines()]
    exclude: set[str] | None = None
    if args.exclude_from is not None:
        earlier = [
            json.loads(line) for line in args.exclude_from.read_text(encoding="utf-8").splitlines()
        ]
        exclude = {str(r["uei"]) for r in earlier if r.get("uei")}
    records = build(rows, exclude, args.split_name, args.max_names)
    args.out.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    for s in sorted({str(r["split"]) for r in records}):
        part = [r for r in records if r["split"] == s]
        print(f"{s}: {len(part)} records, {len({r['entity_id'] for r in part})} entities")


if __name__ == "__main__":
    main()

"""Build name-only records from enriched USAspending profiles (see docs/PROTOCOL_REAL.md).

One record per distinct name string per UEI (the profile's name plus its alternate names). The UEI is the
answer key (`entity_id`) and is never a matcher input. Entities are split by a hash of the UEI so no entity
appears in both splits.

    python scripts/build_real_dataset.py --profiles data/profiles_2024-01.jsonl --out data/real_records.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def split_of(uei: str) -> str:
    return "dev" if hashlib.sha256(uei.encode()).digest()[0] % 2 == 0 else "test"


def build(profile_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    names: dict[str, set[str]] = {}
    for row in profile_rows:
        prof = row.get("profile")
        uei = row.get("uei")
        if not isinstance(prof, dict) or not isinstance(uei, str) or not uei:
            continue
        found = {
            n
            for n in [prof.get("name"), *(prof.get("alternate_names") or [])]
            if isinstance(n, str) and n.strip()
        }
        names.setdefault(uei, set()).update(found)
    out: list[dict[str, object]] = []
    for uei in sorted(names):
        for name in sorted(names[uei]):
            out.append(
                {
                    "name": name,
                    "entity_id": uei,
                    "split": split_of(uei),
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
    args = ap.parse_args()
    rows = [json.loads(line) for line in args.profiles.read_text(encoding="utf-8").splitlines()]
    records = build(rows)
    args.out.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    for s in ("dev", "test"):
        part = [r for r in records if r["split"] == s]
        print(f"{s}: {len(part)} records, {len({r['entity_id'] for r in part})} entities")


if __name__ == "__main__":
    main()

"""Add each recipient's registry profile (parent links, alternate names) to a fetched record file.

Reads the JSONL written by fetch_usaspending.py, looks up one profile per distinct recipient_id, and
writes <out> with the profile fields attached. Resumable: already-fetched profiles are cached in
<out>.cache.jsonl, so a dropped connection costs nothing.

    python scripts/enrich_profiles.py --records data/usaspending_2024-01.jsonl --out data/profiles_2024-01.jsonl
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BASE = "https://api.usaspending.gov/api/v2/recipient/"


def get(recipient_id: str, tries: int = 5) -> dict[str, Any] | None:
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(BASE + recipient_id + "/", timeout=60) as resp:
                out: dict[str, Any] = json.loads(resp.read())
                return out
        except urllib.error.HTTPError as err:
            if err.code == 404:
                return None
            time.sleep(2 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"profile request failed after retries: {recipient_id}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    records = [json.loads(line) for line in args.records.read_text(encoding="utf-8").splitlines()]
    ids = sorted({r["recipient_id"] for r in records if r["recipient_id"]})
    cache_path = args.out.with_suffix(".cache.jsonl")
    cache: dict[str, dict[str, Any] | None] = {}
    if cache_path.exists():
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            cache[row["id"]] = row["profile"]
    failed: list[str] = []
    with cache_path.open("a", encoding="utf-8") as fh:
        for k, rid in enumerate(ids):
            if rid in cache:
                continue
            try:
                prof = get(rid)
            except RuntimeError:
                failed.append(rid)  # retried once after the loop; never cached, so a rerun retries too
                continue
            keep = None
            if prof is not None:
                keep = {
                    "uei": prof.get("uei"),
                    "duns": prof.get("duns"),
                    "name": prof.get("name"),
                    "alternate_names": prof.get("alternate_names") or [],
                    "parent_uei": prof.get("parent_uei"),
                    "parent_duns": prof.get("parent_duns"),
                    "parent_name": prof.get("parent_name"),
                    "parents": prof.get("parents") or [],
                }
            cache[rid] = keep
            fh.write(json.dumps({"id": rid, "profile": keep}) + "\n")
            fh.flush()
            if k % 50 == 0:
                print(f"{k}/{len(ids)} profiles", flush=True)
        for rid in failed:  # one more attempt after a pause, in case the failure was transient
            time.sleep(10)
            try:
                prof = get(rid)
            except RuntimeError:
                continue
            keep = None if prof is None else {
                "uei": prof.get("uei"),
                "duns": prof.get("duns"),
                "name": prof.get("name"),
                "alternate_names": prof.get("alternate_names") or [],
                "parent_uei": prof.get("parent_uei"),
                "parent_duns": prof.get("parent_duns"),
                "parent_name": prof.get("parent_name"),
                "parents": prof.get("parents") or [],
            }  # fmt: skip
            cache[rid] = keep
            fh.write(json.dumps({"id": rid, "profile": keep}) + "\n")
            fh.flush()
    still_failed = [rid for rid in failed if rid not in cache]
    if failed:
        print(f"{len(failed)} profile requests failed once; {len(still_failed)} still missing and left empty")
    with args.out.open("w", encoding="utf-8") as out:
        for r in records:
            out.write(json.dumps({**r, "profile": cache.get(r["recipient_id"])}) + "\n")
    print(f"wrote {len(records)} records, {len(ids)} profiles to {args.out}")


if __name__ == "__main__":
    main()

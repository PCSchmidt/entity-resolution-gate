"""Download the full list of DoD contract recipients for a fiscal year (the sampling frame).

The API ranks recipients by obligated amount and pages all the way to the end, so the result is the whole
population, not a prefix. One row per recipient: name, registry code, recipient id, amount.

    python scripts/fetch_recipient_frame.py --out data/frame_fy2024.jsonl

Pages are cached as they arrive, so an interrupted run resumes. Rows without a recipient id (redacted or
aggregate) are skipped and counted; the script fails if the same recipient id appears twice.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

URL = "https://api.usaspending.gov/api/v2/search/spending_by_category/recipient/"


def post(body: dict[str, Any], tries: int = 6) -> dict[str, Any]:
    data = json.dumps(body).encode()
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                URL, data=data, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                out: dict[str, Any] = json.loads(resp.read())
                return out
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("USAspending request failed after retries")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--start", default="2023-10-01")
    ap.add_argument("--end", default="2024-09-30")
    ap.add_argument("--agency", default="Department of Defense")
    args = ap.parse_args()
    filters = {
        "award_type_codes": ["A", "B", "C", "D"],
        "time_period": [{"start_date": args.start, "end_date": args.end}],
        "agencies": [{"type": "awarding", "tier": "toptier", "name": args.agency}],
    }
    cache = args.out.with_suffix(".pages.jsonl")  # one line per page, so a dropped run resumes
    args.out.parent.mkdir(parents=True, exist_ok=True)
    pages: list[list[dict[str, Any]]] = []
    if cache.exists():
        pages = [
            json.loads(line)
            for line in cache.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    page = len(pages) + 1
    with cache.open("a", encoding="utf-8") as fh:
        while True:
            res = post({"filters": filters, "limit": 100, "page": page})
            batch = res.get("results", [])
            if not batch:
                break
            pages.append(batch)
            fh.write(json.dumps(batch) + "\n")
            fh.flush()
            if page % 25 == 0:
                print(f"page {page}: {sum(len(b) for b in pages)} rows", flush=True)
            if not res["page_metadata"].get("hasNext") and len(batch) < 100:
                break
            page += 1
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    no_id = 0
    for batch in pages:
        for r in batch:
            rid = r.get("recipient_id")
            if not rid:
                no_id += 1  # redacted or aggregate rows have no recipient to sample
                continue
            if rid in seen:
                raise RuntimeError(f"duplicate recipient id {rid}")
            seen.add(rid)
            rows.append(r)
    args.out.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    print(
        f"wrote {len(rows)} recipients ({no_id} rows without a recipient id skipped) over {len(pages)} pages to {args.out}"
    )


if __name__ == "__main__":
    main()

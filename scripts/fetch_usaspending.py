"""Download recipient records from the public USAspending API (no key needed).

Each award carries the recipient name as reported on that award, the recipient's UEI (the registry
identifier, used ONLY as the answer key, never as a matcher input) and the recipient address. One
output row per distinct (name, address, UEI) triple, with the number of awards behind it.

    python scripts/fetch_usaspending.py --out data/usaspending_2024-01.jsonl --start 2024-01-01 --end 2024-01-31

A date range is read completely (sorted by recipient name, pages until none remain), so the sample is a
census of that window's awards, not a draw biased toward the largest recipients.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
FIELDS = [
    "Recipient Name",
    "Recipient UEI",
    "Recipient DUNS Number",
    "recipient_id",
    "Recipient Location",
]


def post(body: dict[str, Any], tries: int = 6) -> dict[str, Any]:
    data = json.dumps(body).encode()
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                URL, data=data, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                out: dict[str, Any] = json.loads(resp.read())
                return out
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("USAspending request failed after retries")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--start", type=date.fromisoformat, required=True)
    ap.add_argument("--end", type=date.fromisoformat, required=True)
    ap.add_argument(
        "--max-pages", type=int, default=500
    )  # the API caps a result set at 50,000 rows
    ap.add_argument("--agency", default="Department of Defense")
    args = ap.parse_args()

    counts: Counter[tuple[str, ...]] = Counter()
    for page in range(1, args.max_pages + 1):
        body = {
            "filters": {
                "award_type_codes": ["A", "B", "C", "D"],
                "time_period": [
                    {"start_date": args.start.isoformat(), "end_date": args.end.isoformat()}
                ],
                "agencies": [{"type": "awarding", "tier": "toptier", "name": args.agency}],
            },
            "fields": FIELDS,
            "sort": "Recipient Name",
            "order": "asc",
            "limit": 100,
            "page": page,
        }
        res = post(body)
        for r in res["results"]:
            loc = r.get("Recipient Location") or {}
            key = (
                r.get("Recipient Name") or "",
                r.get("Recipient UEI") or "",
                r.get("Recipient DUNS Number") or "",
                r.get("recipient_id") or "",
                loc.get("address_line1") or "",
                loc.get("city_name") or "",
                loc.get("zip5") or "",
            )
            counts[key] += 1
        if page % 20 == 0:
            print(
                f"page {page}: {sum(counts.values())} awards, {len(counts)} distinct records",
                flush=True,
            )
        if not res["page_metadata"].get("hasNext"):
            break

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for (name, uei, duns, rid, addr, city, zip5), n in counts.items():
            fh.write(
                json.dumps(
                    {
                        "name": name,
                        "uei": uei,
                        "duns": duns,
                        "recipient_id": rid,
                        "address": addr,
                        "city": city,
                        "zip5": zip5,
                        "awards": n,
                    }
                )
                + "\n"
            )
    print(f"wrote {len(counts)} records to {args.out}")


if __name__ == "__main__":
    main()

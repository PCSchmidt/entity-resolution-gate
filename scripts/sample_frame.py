"""Draw a simple random sample of recipients from the downloaded frame (docs/PROTOCOL_SAMPLE.md).

Recipients already used by the pilot are removed first, so nothing in the new study was seen by any matcher.

    python scripts/sample_frame.py --frame data/frame_fy2024.jsonl --n 3000 --seed 0 \
        --exclude data/profiles_2024-01.jsonl data/profiles_2024-07.jsonl --out data/sample_ids.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", type=Path, required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--exclude", type=Path, nargs="*", default=[])
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    frame = [
        json.loads(line)
        for line in args.frame.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    pilot_ids: set[str] = set()
    for path in args.exclude:
        for line in path.read_text(encoding="utf-8").splitlines():
            rid = json.loads(line).get("recipient_id")
            if rid:
                pilot_ids.add(rid)
    eligible = sorted(
        (r for r in frame if r.get("recipient_id") and r["recipient_id"] not in pilot_ids),
        key=lambda r: r["recipient_id"],
    )
    rng = random.Random(args.seed)
    chosen = rng.sample(eligible, min(args.n, len(eligible)))
    chosen.sort(key=lambda r: r["recipient_id"])
    args.out.write_text(
        "\n".join(
            json.dumps({"recipient_id": r["recipient_id"], "name": r.get("name")}) for r in chosen
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"frame {len(frame)} | excluded as pilot {len(frame) - len(eligible)} | eligible {len(eligible)} | sampled {len(chosen)}"
    )


if __name__ == "__main__":
    main()

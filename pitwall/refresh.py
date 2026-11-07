"""Refresh all live data:  python -m pitwall.refresh"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone

from pitwall.config import DATA_DIR, current_season
from pitwall.ingest import jolpica, openf1


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Pull fresh F1 data from Jolpica and OpenF1.")
    parser.add_argument("--skip-openf1", action="store_true")
    parser.add_argument("--skip-jolpica", action="store_true")
    args = parser.parse_args()

    counts: dict = {}
    if not args.skip_jolpica:
        counts["jolpica"] = jolpica.ingest()
    if not args.skip_openf1:
        counts["openf1"] = openf1.ingest()

    meta = {
        "refreshed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "season": current_season(),
        "updated": counts,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "meta.json").write_text(json.dumps(meta, indent=2))
    logging.info("refresh complete: %s", json.dumps(counts))


if __name__ == "__main__":
    main()

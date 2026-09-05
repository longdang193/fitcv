"""Bounded, rerun-safe backfill from legacy FitCV Run tables."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fitcv_cp.sqlite_store import (
    RUN_HISTORY_MIGRATION_ID,
    backfill_legacy_run_history,
    get_run_history_migration_status,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill legacy local_pipeline_runs and local_pipeline_run_events into canonical Run history."
    )
    parser.add_argument("--database", "--db", dest="database", required=True, type=Path, help="SQLite database path.")
    parser.add_argument("--batch-size", type=int, default=100, help="Maximum new source rows per table in one invocation.")
    parser.add_argument("--migration-id", default=RUN_HISTORY_MIGRATION_ID, help="Stable migration identity.")
    parser.add_argument("--dry-run", action="store_true", help="Report planned dispositions without writing SQLite state.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = backfill_legacy_run_history(
            args.database,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            migration_id=args.migration_id,
        )
        status = get_run_history_migration_status(args.database, migration_id=args.migration_id)
    except Exception as exc:
        print(f"backfill_failed error={type(exc).__name__} detail={exc}", file=sys.stderr)
        return 2
    print(json.dumps({"summary": summary, "status": status}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

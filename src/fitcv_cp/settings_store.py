"""@meta
name: settings_store
type: module
domain: runtime
ownership: infrastructure
responsibility:
  - Module metadata placeholder for src.fitcv_cp.settings_store.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

import datetime
import hashlib
import json
import logging
import os
import sqlite3
import shutil
from pathlib import Path
from typing import Any

from fitcv.persistence import get_local_sqlite_path
from fitcv_cp.backend_runtime import get_backend_runtime
from fitcv_cp.settings_schema import (
    canonical_settings_key,
    coerce_value,
    editable_settings_keys,
    merge_and_validate_settings,
)

logger = logging.getLogger(__name__)


class SettingsRevisionConflict(RuntimeError):
    pass


def settings_revision(active: dict[str, Any]) -> str:
    payload = json.dumps(active, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _local_sqlite_path() -> Path:
    runtime = get_backend_runtime()
    if runtime is not None and str(runtime.sqlite_path or "").strip():
        raw = str(runtime.sqlite_path).strip()
    else:
        raw = get_local_sqlite_path()
    return Path(raw)


def _ensure_local_pipeline_settings_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pipeline_settings (
            setting_key TEXT NOT NULL,
            setting_value_json TEXT NOT NULL,
            updated_by TEXT,
            updated_at TEXT NOT NULL
        )
        """
    )


def _is_recoverable_sqlite_error(exc: sqlite3.Error) -> bool:
    message = str(exc).lower()
    return (
        "disk i/o error" in message
        or "database is locked" in message
        or "file is not a database" in message
    )

def _rotate_local_sqlite_family(db_path: Path, *, reason: str) -> Path | None:
    if not db_path.exists():
        return None
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_dir = db_path.parent / f"{db_path.stem}.corrupt.{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    moved = False
    for suffix in ("", "-wal", "-shm"):
        source = Path(f"{db_path}{suffix}")
        if not source.exists():
            continue
        target = backup_dir / source.name
        try:
            shutil.move(str(source), str(target))
            moved = True
        except OSError as move_exc:
            logger.warning("Failed to rotate sqlite file %s: %s", source, move_exc)
    if moved:
        logger.warning(
            "Rotated local settings sqlite files due to recoverable sqlite failure (%s). backup_dir=%s",
            reason,
            backup_dir,
        )
        return backup_dir
    return None


def _load_local_settings_rows() -> list[sqlite3.Row]:
    db_path = _local_sqlite_path()
    if not db_path.exists():
        return []
    for attempt in (1, 2):
        try:
            with sqlite3.connect(db_path, timeout=30) as conn:
                conn.row_factory = sqlite3.Row
                _ensure_local_pipeline_settings_table(conn)
                rows = conn.execute(
                    """
                    SELECT setting_key, setting_value_json
                    FROM pipeline_settings
                    ORDER BY updated_at DESC, rowid DESC
                    """
                ).fetchall()
            return rows
        except sqlite3.Error as exc:
            if attempt == 1 and _is_recoverable_sqlite_error(exc):
                _rotate_local_sqlite_family(db_path, reason=str(exc))
                return []
            raise
    return []

def _delete_local_settings_rows(rows: list[tuple[str, str]]) -> None:
    if not rows:
        return
    db_path = _local_sqlite_path()
    if not db_path.exists():
        return
    with sqlite3.connect(db_path, timeout=30) as conn:
        _ensure_local_pipeline_settings_table(conn)
        conn.executemany(
            "DELETE FROM pipeline_settings WHERE setting_key = ? AND setting_value_json = ?",
            rows,
        )
        conn.commit()


def _decode_active_settings_rows(
    rows: list[sqlite3.Row],
) -> tuple[dict[str, Any], list[tuple[str, str]]]:
    ordered_rows = sorted(
        enumerate(rows),
        key=lambda item: (
            0 if canonical_settings_key(str(item[1]["setting_key"])) == str(item[1]["setting_key"]) else 1,
            item[0],
        ),
    )
    seen_valid: set[str] = set()
    invalid_rows: list[tuple[str, str]] = []
    result: dict[str, Any] = {}
    for _, row in ordered_rows:
        original_key = str(row["setting_key"])
        canonical_key = canonical_settings_key(original_key)
        if canonical_key in seen_valid:
            continue
        raw_value_json = str(row["setting_value_json"])
        try:
            raw = json.loads(raw_value_json)
            result[canonical_key] = coerce_value(canonical_key, raw)
            seen_valid.add(canonical_key)
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            invalid_rows.append((original_key, raw_value_json))
            logger.info("Removing stale invalid setting key=%s: %s", original_key, exc)
    return result, invalid_rows


def _load_active_settings_from_connection(
    conn: sqlite3.Connection,
) -> tuple[dict[str, Any], list[tuple[str, str]]]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT setting_key, setting_value_json
        FROM pipeline_settings
        ORDER BY updated_at DESC, rowid DESC
        """
    ).fetchall()
    return _decode_active_settings_rows(rows)


def _normalize_bookmark_key(
    *,
    job_id: str | None,
    url: str | None,
    title: str | None,
    company: str | None,
    location: str | None,
) -> str:
    if job_id and str(job_id).strip():
        return f"job_id:{str(job_id).strip()}"
    if url and str(url).strip():
        return f"url:{str(url).strip()}"
    fallback_parts = [
        str(title or "").strip().lower(),
        str(company or "").strip().lower(),
        str(location or "").strip().lower(),
    ]
    fallback = "|".join(fallback_parts)
    if fallback.strip("|"):
        return f"fallback:{fallback}"
    raise ValueError("bookmark identity requires job_id, url, or title/company/location fallback")














def save_setting(
    key: str,
    value: Any,
    *,
    updated_by: str,
) -> None:
    mutate_settings_atomically(changes={key: value}, updated_by=updated_by)


def save_settings_group(
    keys_values: dict[str, Any],
    *,
    updated_by: str,
) -> None:
    mutate_settings_atomically(changes=keys_values, updated_by=updated_by)


def mutate_settings_atomically(
    *,
    changes: dict[str, Any],
    updated_by: str,
    reset_keys: list[str] | tuple[str, ...] = (),
    expected_revision: str | None = None,
) -> dict[str, Any]:
    """Serialize load, merge, validation, writes, and resets in one transaction."""
    db_path = _local_sqlite_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    canonical_changes: dict[str, Any] = {}
    for raw_key, raw_value in changes.items():
        key = canonical_settings_key(raw_key)
        if key == raw_key or key not in canonical_changes:
            canonical_changes[key] = raw_value
    canonical_resets = {canonical_settings_key(key) for key in reset_keys}

    for attempt in (1, 2):
        try:
            with sqlite3.connect(db_path, timeout=30, isolation_level=None) as conn:
                conn.execute("BEGIN IMMEDIATE")
                _ensure_local_pipeline_settings_table(conn)
                active, invalid_rows = _load_active_settings_from_connection(conn)
                if invalid_rows:
                    conn.executemany(
                        "DELETE FROM pipeline_settings WHERE setting_key = ? AND setting_value_json = ?",
                        invalid_rows,
                    )
                if expected_revision is not None and expected_revision != settings_revision(active):
                    raise SettingsRevisionConflict("Pipeline settings changed since last read")
                candidate_overrides = {
                    key: value for key, value in active.items() if key not in canonical_resets
                }
                effective = merge_and_validate_settings(
                    canonical_changes,
                    current_settings=candidate_overrides,
                )
                if canonical_resets:
                    conn.executemany(
                        "DELETE FROM pipeline_settings WHERE setting_key = ?",
                        [(key,) for key in canonical_resets],
                    )
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                rows = [
                    (key, json.dumps(effective[key]), updated_by, now)
                    for key in canonical_changes
                ]
                if rows:
                    conn.executemany(
                        """
                        INSERT INTO pipeline_settings (
                            setting_key,
                            setting_value_json,
                            updated_by,
                            updated_at
                        ) VALUES (?, ?, ?, ?)
                        """,
                        rows,
                    )
                conn.commit()
                candidate_overrides.update({key: effective[key] for key in canonical_changes})
                return candidate_overrides
        except sqlite3.Error as exc:
            if attempt == 1 and _is_recoverable_sqlite_error(exc):
                _rotate_local_sqlite_family(db_path, reason=str(exc))
                continue
            raise
    raise RuntimeError("Settings mutation failed")


def load_active_settings() -> dict[str, Any]:
    """Return the current active settings dict (latest row per key, coerced to Python types).

    Returns an empty dict if no settings have been saved yet.
    """
    rows = _load_local_settings_rows()

    result, invalid_rows_to_delete = _decode_active_settings_rows(rows)

    _delete_local_settings_rows(invalid_rows_to_delete)

    return result


def load_active_editable_settings() -> dict[str, Any]:
    """Return only schema-backed editable settings from the active settings snapshot."""
    active_settings = load_active_settings()
    editable_keys = editable_settings_keys()
    return {
        key: value
        for key, value in active_settings.items()
        if key in editable_keys
    }

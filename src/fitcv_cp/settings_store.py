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

import copy
import datetime
import hashlib
import json
import logging
import os
import sqlite3
import shutil
from pathlib import Path
from typing import Any, Callable

from fitcv.persistence import get_local_sqlite_path
from fitcv_cp.backend_runtime import get_backend_runtime
from fitcv_cp.settings_schema import (
    canonical_settings_key,
    coerce_value,
    editable_settings_keys,
    merge_and_validate_settings,
)
from fitcv_cp.retry_settings import SYSTEM_SETTING_BOUNDS, SYSTEM_SETTINGS_DEFAULTS

logger = logging.getLogger(__name__)


class SettingsRevisionConflict(RuntimeError):
    pass


LLM_TASK_IDS = (
    "enrich_extraction",
    "ranking_ai_score",
    "cv_generation_structured_write",
    "synonym_triage_recommendation",
)

CONFIGURATION_RESOURCE_DEFAULTS: dict[str, dict[str, Any]] = {
    "llm_configuration": {
        "default_model_ref": None,
        "tasks": {
            task_id: {
                "model_ref": None,
                "timeout_seconds": 120,
                "temperature": 0.2,
            }
            for task_id in LLM_TASK_IDS
        },
    },
    "system_settings": {**SYSTEM_SETTINGS_DEFAULTS},
    **{
        f"prompt:{task_id}": {
            "replacement_text": None,
            "migration_state": "clean",
        }
        for task_id in LLM_TASK_IDS
    },
}


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


def _resource_result(
    resource_name: str,
    value: dict[str, Any],
    revision: int,
    updated_at: str,
) -> dict[str, Any]:
    result = copy.deepcopy(value)
    if resource_name.startswith("prompt:"):
        result["task_id"] = resource_name.removeprefix("prompt:")
    result["revision"] = revision
    result["updated_at"] = updated_at
    return result


def _ensure_configuration_schema(conn: sqlite3.Connection) -> None:
    from fitcv_cp.sqlite_store import _configure_sqlite_connection, _ensure_control_plane_schema

    _configure_sqlite_connection(conn)
    _ensure_control_plane_schema(conn)


def _load_configuration_resource(resource_name: str) -> dict[str, Any]:
    db_path = _local_sqlite_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path, timeout=30) as conn:
        _ensure_configuration_schema(conn)
        row = conn.execute(
            """
            SELECT resource_json, revision, updated_at
            FROM configuration_resources
            WHERE resource_name = ?
            """,
            (resource_name,),
        ).fetchone()
    if row is None:
        raise KeyError(resource_name)
    return _resource_result(resource_name, json.loads(str(row[0])), int(row[1]), str(row[2]))


def _patch_configuration_resource(
    resource_name: str,
    *,
    expected_revision: int,
    update: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    db_path = _local_sqlite_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path, timeout=30, isolation_level=None) as conn:
        _ensure_configuration_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                """
                SELECT resource_json, revision
                FROM configuration_resources
                WHERE resource_name = ?
                """,
                (resource_name,),
            ).fetchone()
            if row is None:
                raise KeyError(resource_name)
            current_revision = int(row[1])
            if current_revision != expected_revision:
                raise SettingsRevisionConflict(f"{resource_name} changed since last read")
            value = update(json.loads(str(row[0])))
            revision = current_revision + 1
            updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            conn.execute(
                """
                UPDATE configuration_resources
                SET resource_json = ?, revision = ?, updated_at = ?
                WHERE resource_name = ?
                """,
                (
                    json.dumps(value, sort_keys=True, separators=(",", ":")),
                    revision,
                    updated_at,
                    resource_name,
                ),
            )
            conn.commit()
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise
    return _resource_result(resource_name, value, revision, updated_at)


def _validate_model_ref(field: str, value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a model record ID or null")
    return value.strip()


def _validate_llm_configuration(
    value: dict[str, Any],
    *,
    eligible_refs: set[str],
) -> dict[str, Any]:
    if set(value) != {"default_model_ref", "tasks"}:
        raise ValueError("llm_configuration contains unsupported fields")
    value["default_model_ref"] = _validate_model_ref(
        "default_model_ref", value["default_model_ref"]
    )
    tasks = value["tasks"]
    if not isinstance(tasks, dict) or set(tasks) != set(LLM_TASK_IDS):
        raise ValueError("tasks must contain exactly the supported task IDs")
    for task_id, task in tasks.items():
        if not isinstance(task, dict) or set(task) != {
            "model_ref",
            "timeout_seconds",
            "temperature",
        }:
            raise ValueError(f"tasks.{task_id} contains unsupported fields")
        task["model_ref"] = _validate_model_ref(f"tasks.{task_id}.model_ref", task["model_ref"])
        timeout = task["timeout_seconds"]
        if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 3600:
            raise ValueError(f"tasks.{task_id}.timeout_seconds must be between 1 and 3600")
        temperature = task["temperature"]
        if (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not 0 <= temperature <= 2
            or not float(temperature * 10).is_integer()
        ):
            raise ValueError(f"tasks.{task_id}.temperature must be between 0 and 2 in 0.1 steps")
        task["temperature"] = float(temperature)
    referenced = {
        ref
        for ref in [
            value["default_model_ref"],
            *(task["model_ref"] for task in tasks.values()),
        ]
        if ref is not None
    }
    unavailable = sorted(referenced - eligible_refs)
    if unavailable:
        raise ValueError("LLM configuration references unavailable provider models")
    if eligible_refs and value["default_model_ref"] is None:
        raise ValueError("default_model_ref is required while eligible models exist")
    return value


def load_llm_configuration() -> dict[str, Any]:
    return _load_configuration_resource("llm_configuration")


def patch_llm_configuration(
    changes: dict[str, Any],
    *,
    expected_revision: int,
) -> dict[str, Any]:
    from fitcv_cp.provider_registry import list_eligible_models

    eligible_refs = {
        str(model["model_record_id"])
        for model in list_eligible_models()
    }

    def update(current: dict[str, Any]) -> dict[str, Any]:
        candidate = copy.deepcopy(current)
        unknown = set(changes) - {"default_model_ref", "tasks"}
        if unknown:
            raise ValueError(f"unsupported LLM configuration fields: {sorted(unknown)}")
        if "default_model_ref" in changes:
            candidate["default_model_ref"] = changes["default_model_ref"]
        task_changes = changes.get("tasks", {})
        if not isinstance(task_changes, dict):
            raise ValueError("tasks must be an object")
        for task_id, task_update in task_changes.items():
            if task_id not in LLM_TASK_IDS:
                raise ValueError(f"unsupported task_id: {task_id}")
            if not isinstance(task_update, dict):
                raise ValueError(f"tasks.{task_id} must be an object")
            candidate["tasks"][task_id].update(task_update)
        return _validate_llm_configuration(candidate, eligible_refs=eligible_refs)

    return _patch_configuration_resource(
        "llm_configuration",
        expected_revision=expected_revision,
        update=update,
    )


def load_prompt_configurations() -> dict[str, dict[str, Any]]:
    return {
        task_id: _load_configuration_resource(f"prompt:{task_id}")
        for task_id in LLM_TASK_IDS
    }


def patch_prompt_configuration(
    task_id: str,
    *,
    replacement_text: str | None,
    expected_revision: int,
) -> dict[str, Any]:
    if task_id not in LLM_TASK_IDS:
        raise KeyError(task_id)

    from fitcv.config import load_prompt_task_registry
    from fitcv.prompts.loader import load_prompt_template
    from fitcv.prompts.renderer import required_template_variables

    prompt = load_prompt_task_registry()[task_id]
    default_text = load_prompt_template(Path(prompt["template_path"]))
    default_variables = required_template_variables(default_text)

    def update(current: dict[str, Any]) -> dict[str, Any]:
        if replacement_text is None:
            normalized = None
        elif not isinstance(replacement_text, str):
            raise ValueError("replacement_text must be text or null")
        else:
            normalized = replacement_text.replace("\r\n", "\n").replace("\r", "\n")
            if not normalized.strip():
                raise ValueError("replacement_text must not be empty")
            if len(normalized) > 4000:
                raise ValueError("replacement_text must not exceed 4000 characters")
            if normalized == default_text.replace("\r\n", "\n").replace("\r", "\n"):
                raise ValueError("replacement_text must differ from the current default")
            if required_template_variables(normalized) != default_variables:
                raise ValueError(
                    "replacement_text must use exactly the canonical prompt variables"
                )
        return {
            "replacement_text": normalized,
            "migration_state": "clean",
        }

    return _patch_configuration_resource(
        f"prompt:{task_id}",
        expected_revision=expected_revision,
        update=update,
    )


def migrate_prompt_configuration(
    task_id: str,
    *,
    replacement_text: str | None,
    migration_state: str,
) -> dict[str, Any]:
    if task_id not in LLM_TASK_IDS:
        raise KeyError(task_id)
    if migration_state not in {"clean", "needs_review"}:
        raise ValueError("unsupported prompt migration state")
    current = _load_configuration_resource(f"prompt:{task_id}")
    if current.get("replacement_text") is not None:
        return current
    normalized = (
        replacement_text.replace("\r\n", "\n").replace("\r", "\n")
        if replacement_text is not None
        else None
    )
    return _patch_configuration_resource(
        f"prompt:{task_id}",
        expected_revision=int(current["revision"]),
        update=lambda _current: {
            "replacement_text": normalized,
            "migration_state": migration_state,
        },
    )


def migrate_llm_configuration_references(
    *,
    default_model_ref: str | None,
    task_model_refs: dict[str, str | None],
) -> dict[str, Any]:
    current = load_llm_configuration()
    if current.get("default_model_ref") is not None and all(
        current["tasks"][task_id].get("model_ref") is not None
        for task_id in task_model_refs
    ):
        return current

    def update(resource: dict[str, Any]) -> dict[str, Any]:
        candidate = copy.deepcopy(resource)
        if candidate.get("default_model_ref") is None:
            candidate["default_model_ref"] = default_model_ref
        for task_id, model_ref in task_model_refs.items():
            if task_id not in LLM_TASK_IDS:
                raise KeyError(task_id)
            if candidate["tasks"][task_id].get("model_ref") is None:
                candidate["tasks"][task_id]["model_ref"] = model_ref
        return candidate

    return _patch_configuration_resource(
        "llm_configuration",
        expected_revision=int(current["revision"]),
        update=update,
    )




def _validate_system_settings(value: dict[str, Any]) -> dict[str, Any]:
    if set(value) != set(SYSTEM_SETTING_BOUNDS):
        raise ValueError("system_settings contains unsupported fields")
    for field, (minimum, maximum) in SYSTEM_SETTING_BOUNDS.items():
        item = value[field]
        if isinstance(item, bool) or not isinstance(item, int) or not minimum <= item <= maximum:
            raise ValueError(f"{field} must be between {minimum} and {maximum}")
    return value


def load_system_settings() -> dict[str, Any]:
    return _load_configuration_resource("system_settings")


def patch_system_settings(
    changes: dict[str, Any],
    *,
    expected_revision: int,
) -> dict[str, Any]:
    def update(current: dict[str, Any]) -> dict[str, Any]:
        unknown = set(changes) - set(SYSTEM_SETTING_BOUNDS)
        if unknown:
            raise ValueError(f"unsupported System settings fields: {sorted(unknown)}")
        candidate = {**current, **changes}
        return _validate_system_settings(candidate)

    return _patch_configuration_resource(
        "system_settings",
        expected_revision=expected_revision,
        update=update,
    )

"""Read-only access to the published FitCV analytics release."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml


class AnalyticsUnavailable(ValueError):
    """Published analytics cannot prove its identity or freshness."""


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AnalyticsUnavailable(f"unreadable:{path.name}") from exc
    if not isinstance(value, dict):
        raise AnalyticsUnavailable(f"invalid_json:{path.name}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _value_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _git_head(repo_root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def analytics_output_root(repo_root: Path) -> Path:
    configured = os.environ.get("FITCV_ANALYTICS_OUTPUT_ROOT", "").strip()
    if not configured:
        config_path = repo_root / "config" / "analytics_metrics.yaml"
        try:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise AnalyticsUnavailable("analytics_config_unavailable") from exc
        configured = str(dict(config).get("published_artifact", {}).get("path") or "").strip()
    if not configured:
        raise AnalyticsUnavailable("published_artifact_path_missing")
    root = Path(configured)
    return root if root.is_absolute() else (repo_root / root)


def load_published_analytics(repo_root: Path) -> dict[str, Any]:
    root = analytics_output_root(repo_root).resolve()
    pointer = _json(root / "CURRENT.json")
    release_ref = str(pointer.get("release") or "").strip()
    if not release_ref or Path(release_ref).is_absolute():
        raise AnalyticsUnavailable("published_release_missing")
    release = (root / release_ref).resolve()
    if root not in release.parents:
        raise AnalyticsUnavailable("published_release_outside_root")

    manifest = _json(release / "manifest.json")
    if {key: value for key, value in pointer.items() if key != "release"} != manifest:
        raise AnalyticsUnavailable("published_pointer_manifest_mismatch")
    database = release / "analytics.sqlite3"
    if not database.is_file():
        raise AnalyticsUnavailable("published_database_missing")

    analytics = _json(release / "analytics.json")
    gold = analytics.get("gold")
    material = {key: value for key, value in gold.items() if key not in {"generated_at", "ingested_at"}}
    if (
        not isinstance(gold, dict)
        or analytics.get("material_metrics_sha256") != manifest.get("material_metrics_sha256")
        or _value_digest(material) != manifest.get("material_metrics_sha256")
    ):
        raise AnalyticsUnavailable("published_metrics_digest_mismatch")
    source_bundle = _json(release / "source_bundle.json")
    if source_bundle.get("database_sha256") != manifest.get("database_sha256"):
        raise AnalyticsUnavailable("published_source_database_digest_mismatch")
    if source_bundle.get("input_fingerprint") != manifest.get("input_fingerprint"):
        raise AnalyticsUnavailable("published_input_fingerprint_mismatch")
    if source_bundle.get("source_commit") != manifest.get("source_commit"):
        raise AnalyticsUnavailable("published_source_commit_mismatch")
    expected_commit = os.environ.get("FITCV_ANALYTICS_SOURCE_COMMIT", "").strip() or _git_head(repo_root)
    if expected_commit and str(manifest.get("source_commit") or "") != expected_commit:
        raise AnalyticsUnavailable("published_source_commit_stale")
    return {
        "root": root,
        "release": release,
        "manifest": manifest,
        "source_bundle": source_bundle,
        "analytics": analytics,
    }


def unavailable_payload(reason: str) -> dict[str, Any]:
    return {
        "coverage": {
            "status": "unavailable",
            "sample_size": 0,
            "source_mix": [],
            "collection_window": {"start": None, "end": None},
            "candidate_revisions": [],
            "unavailable_reasons": [reason],
        },
        "metadata": {},
        "opportunity_landscape": [],
        "requirement_demand": [],
        "candidate_evidence_gaps": [],
    }


def _coverage(source_bundle: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    sources = dict(source_bundle.get("sources") or {})
    inventory = [row for row in sources.get("posting_inventory", []) if isinstance(row, dict)]
    eligible = [row for row in inventory if row.get("eligible") is not False]
    collected = sorted(str(row.get("collected_at")) for row in eligible if row.get("collected_at"))
    source_mix_values: set[str] = set()
    for row in eligible:
        source = str(row.get("source") or "unknown")
        try:
            source_mix_values.add(urlparse(source).hostname or source)
        except ValueError:
            source_mix_values.add(source)
    source_mix = sorted(source_mix_values)
    revisions = []
    seen: set[tuple[str, str, str]] = set()
    for row in sources.get("candidate_profile_revision", []):
        if not isinstance(row, dict):
            continue
        identity = (
            str(row.get("candidate_profile_id") or ""),
            str(row.get("candidate_profile_revision") or ""),
            str(row.get("candidate_profile_fingerprint") or ""),
        )
        if identity not in seen:
            seen.add(identity)
            revisions.append(
                {
                    "candidate_profile_id": identity[0],
                    "candidate_profile_revision": identity[1],
                    "candidate_profile_fingerprint": identity[2],
                }
            )
    return {
        "status": "available",
        "sample_size": len({str(row.get("posting_id")) for row in eligible if row.get("posting_id")}),
        "source_mix": source_mix,
        "collection_window": {
            "start": collected[0] if collected else None,
            "end": collected[-1] if collected else None,
        },
        "candidate_revisions": revisions,
        "unavailable_reasons": [],
        "source_commit": manifest.get("source_commit"),
    }


def dashboard_payload(published: dict[str, Any]) -> dict[str, Any]:
    manifest = dict(published["manifest"])
    source_bundle = dict(published["source_bundle"])
    gold = dict(published["analytics"].get("gold") or {})
    return {
        "coverage": _coverage(source_bundle, manifest),
        "metadata": {
            "release": str(published["release"].relative_to(published["root"])).replace("\\", "/"),
            "source_commit": manifest.get("source_commit"),
            "input_fingerprint": manifest.get("input_fingerprint"),
            "material_digest": manifest.get("material_metrics_sha256"),
        },
        "opportunity_landscape": list(gold.get("gold_requirement_demand") or []),
        "requirement_demand": [
            row for row in gold.get("gold_semantic_metric") or []
            if isinstance(row, dict) and row.get("metric_id") == "skill_demand"
        ],
        "candidate_evidence_gaps": list(gold.get("gold_candidate_gap") or []),
    }


def trace_payload(published: dict[str, Any], posting_id: str) -> dict[str, Any] | None:
    source_bundle = dict(published["source_bundle"])
    sources = dict(source_bundle.get("sources") or {})
    posting = next(
        (row for row in sources.get("posting_inventory", []) if isinstance(row, dict) and str(row.get("posting_id")) == posting_id),
        None,
    )
    if posting is None:
        return None
    requirements = [
        row for row in sources.get("posting_requirement", [])
        if isinstance(row, dict) and str(row.get("posting_id")) == posting_id
    ]
    gaps = [
        row for row in sources.get("candidate_gap", [])
        if isinstance(row, dict) and str(row.get("posting_id")) == posting_id
    ]
    return {
        "coverage": _coverage(source_bundle, dict(published["manifest"])),
        "posting": posting,
        "requirements": requirements,
        "candidate_evidence_gaps": gaps,
    }

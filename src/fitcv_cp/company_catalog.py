from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

import yaml

from fitcv.job_sources import (
    JobSourceError,
    build_trusted_provider_config,
    validate_trusted_provider_config,
)

_TOP_LEVEL_KEYS = {"schema_version", "catalog_source", "catalog_revision", "companies"}
_RECORD_KEYS = {
    "catalog_id", "company_name", "careers_url", "provider_id", "provider_label",
    "trackable", "discovery_only", "verification",
}
_VERIFICATION_KEYS = {"status", "checked_at", "evidence_ref"}
_PROVIDER_LABELS = {
    "greenhouse": "Greenhouse",
    "ashby": "Ashby",
    "lever": "Lever",
    "personio": "Personio",
    "workday": "Workday",
    "gem": "Gem",
    "wellfound": "Wellfound",
}
_PROVIDER_IDS = set(_PROVIDER_LABELS)
_VERIFICATION_STATES = {"verified", "quarantined", "discovery_only"}


def _default_catalog_path() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(str(frozen_root)).resolve() / "config" / "scan_catalog.yaml"
    return Path(__file__).resolve().parents[2] / "config" / "scan_catalog.yaml"


@dataclass(frozen=True)
class CompanyCatalogRecord:
    catalog_id: str
    company_name: str
    careers_url: str
    provider_id: str
    provider_label: str
    provider_config: Mapping[str, Any] | None
    catalog_source: str
    catalog_revision: str
    trackable: bool
    discovery_only: bool
    verification_status: str = "verified"
    checked_at: str | None = None
    evidence_ref: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "catalog_id": self.catalog_id,
            "company_name": self.company_name,
            "careers_url": self.careers_url,
            "provider_id": self.provider_id,
            "provider_label": self.provider_label,
            "provider_config": dict(self.provider_config) if self.provider_config is not None else None,
            "catalog_source": self.catalog_source,
            "catalog_revision": self.catalog_revision,
            "trackable": self.trackable,
            "discovery_only": self.discovery_only,
            "verification_status": self.verification_status,
            "checked_at": self.checked_at,
            "evidence_ref": self.evidence_ref,
        }


def _canonical_url(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("catalog_record_url_invalid")
    parsed = urlsplit(value.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("catalog_record_url_invalid")
    if parsed.port is not None or parsed.query or parsed.fragment or "//" in parsed.path:
        raise ValueError("catalog_record_url_invalid")
    path = parsed.path.rstrip("/")
    canonical = urlunsplit(("https", parsed.hostname.lower(), path, "", ""))
    if value.strip() != canonical:
        raise ValueError("catalog_record_url_not_canonical")
    return canonical


def _validate_verification(value: object) -> tuple[str, str | None, str | None]:
    if not isinstance(value, Mapping) or set(value) != _VERIFICATION_KEYS:
        raise ValueError("catalog_verification_invalid")
    status = value["status"]
    checked_at = value["checked_at"]
    evidence_ref = value["evidence_ref"]
    if status not in _VERIFICATION_STATES:
        raise ValueError("catalog_verification_state_invalid")
    if checked_at is not None and (not isinstance(checked_at, str) or not checked_at.strip()):
        raise ValueError("catalog_verification_checked_at_invalid")
    if evidence_ref is not None and (not isinstance(evidence_ref, str) or not evidence_ref.strip()):
        raise ValueError("catalog_verification_evidence_invalid")
    return str(status), checked_at, evidence_ref


def _from_yaml_record(record: Mapping[str, Any], *, source: str, revision: str) -> CompanyCatalogRecord:
    if not isinstance(record, Mapping) or set(record) != _RECORD_KEYS:
        raise ValueError("catalog_record_keys_invalid")
    values = {key: record[key] for key in _RECORD_KEYS}
    for key in ("catalog_id", "company_name", "provider_id", "provider_label"):
        if not isinstance(values[key], str) or not values[key].strip():
            raise ValueError("catalog_record_string_invalid")
    provider_id = values["provider_id"]
    if provider_id not in _PROVIDER_IDS or values["provider_label"] != _PROVIDER_LABELS[provider_id]:
        raise ValueError("catalog_record_provider_invalid")
    if not values["catalog_id"].startswith("company-"):
        raise ValueError("catalog_record_id_invalid")
    careers_url = _canonical_url(values["careers_url"])
    if not isinstance(values["trackable"], bool) or not isinstance(values["discovery_only"], bool):
        raise ValueError("catalog_record_flags_invalid")
    status, checked_at, evidence_ref = _validate_verification(values["verification"])
    if provider_id == "wellfound":
        if status != "discovery_only" or values["trackable"] or not values["discovery_only"]:
            raise ValueError("catalog_record_wellfound_invalid")
        config = None
    elif status == "verified":
        if not values["trackable"] or values["discovery_only"]:
            raise ValueError("catalog_record_trackable_invalid")
        try:
            config = build_trusted_provider_config(provider_id=provider_id, careers_url=careers_url)
            validate_trusted_provider_config(config)
        except (JobSourceError, TypeError, ValueError) as exc:
            raise ValueError("catalog_record_provider_config_invalid") from exc
    else:
        if values["trackable"]:
            raise ValueError("catalog_record_quarantine_invalid")
        config = None
    return CompanyCatalogRecord(
        catalog_id=values["catalog_id"],
        company_name=values["company_name"],
        careers_url=careers_url,
        provider_id=provider_id,
        provider_label=values["provider_label"],
        provider_config=MappingProxyType(config) if config is not None else None,
        catalog_source=source,
        catalog_revision=revision,
        trackable=values["trackable"],
        discovery_only=values["discovery_only"],
        verification_status=status,
        checked_at=checked_at,
        evidence_ref=evidence_ref,
    )


def load_catalog(path: str | Path | None = None) -> tuple[CompanyCatalogRecord, ...]:
    catalog_path = Path(path) if path is not None else _default_catalog_path()
    try:
        document = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError("catalog_file_missing") from exc
    if not isinstance(document, Mapping) or set(document) != _TOP_LEVEL_KEYS:
        raise ValueError("catalog_top_level_invalid")
    if document["schema_version"] != 1 or document["catalog_source"] != "bundled":
        raise ValueError("catalog_provenance_invalid")
    revision = document["catalog_revision"]
    if not isinstance(revision, str) or not revision.strip():
        raise ValueError("catalog_revision_invalid")
    companies = document["companies"]
    if not isinstance(companies, list):
        raise ValueError("catalog_companies_invalid")
    records = tuple(_from_yaml_record(item, source="bundled", revision=revision) for item in companies)
    return validate_catalog(records)


def load_catalog_revision(path: str | Path | None = None) -> str:
    catalog_path = Path(path) if path is not None else _default_catalog_path()
    document = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping) or set(document) != _TOP_LEVEL_KEYS:
        raise ValueError("catalog_top_level_invalid")
    revision = document["catalog_revision"]
    if not isinstance(revision, str) or not revision.strip():
        raise ValueError("catalog_revision_invalid")
    return revision


def validate_catalog(records: tuple[CompanyCatalogRecord, ...] | list[CompanyCatalogRecord]) -> tuple[CompanyCatalogRecord, ...]:
    normalized: list[CompanyCatalogRecord] = []
    for record in records:
        if isinstance(record, CompanyCatalogRecord):
            normalized.append(record)
            continue
        if not isinstance(record, Mapping):
            raise ValueError("catalog_record_invalid")
        required = {
            "catalog_id", "company_name", "careers_url", "provider_id", "provider_label",
            "provider_config", "catalog_source", "catalog_revision", "trackable", "discovery_only",
        }
        if not required.issubset(record):
            raise ValueError("catalog_record_keys_invalid")
        try:
            careers_url = _canonical_url(record["careers_url"])
            provider_id = str(record["provider_id"])
            provider_config = record["provider_config"]
            if (
                record["catalog_source"] != "bundled"
                or not isinstance(record["catalog_revision"], str)
                or record["catalog_revision"] != BUNDLED_CATALOG_REVISION
            ):
                raise ValueError("catalog_record_provenance_invalid")
            if provider_id == "wellfound":
                if provider_config is not None or record["trackable"] or not record["discovery_only"]:
                    raise ValueError("catalog_record_discovery_only_invalid")
            else:
                validate_trusted_provider_config(provider_config)
            normalized.append(CompanyCatalogRecord(
                catalog_id=str(record["catalog_id"]),
                company_name=str(record["company_name"]),
                careers_url=careers_url,
                provider_id=provider_id,
                provider_label=str(record["provider_label"]),
                provider_config=MappingProxyType(dict(provider_config)) if provider_config is not None else None,
                catalog_source="bundled",
                catalog_revision=str(record["catalog_revision"]),
                trackable=record["trackable"],
                discovery_only=record["discovery_only"],
                verification_status=str(record.get("verification_status", "discovery_only" if provider_id == "wellfound" else "verified")),
                checked_at=record.get("checked_at"),
                evidence_ref=record.get("evidence_ref"),
            ))
        except (TypeError, ValueError, JobSourceError) as exc:
            if isinstance(exc, ValueError) and str(exc).startswith("catalog_"):
                raise
            raise ValueError("catalog_record_invalid") from exc
    ids = [record.catalog_id for record in normalized]
    urls = [record.careers_url for record in normalized]
    if len(ids) != len(set(ids)) or len(urls) != len(set(urls)):
        raise ValueError("catalog_record_duplicate_identity")
    return tuple(normalized)


BUNDLED_COMPANY_CATALOG = load_catalog()
BUNDLED_CATALOG_REVISION = load_catalog_revision()

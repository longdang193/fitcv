from __future__ import annotations

import datetime
from enum import Enum
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PublishedWindow(str, Enum):
    ANY = "any"
    PAST_12_HOURS = "past_12_hours"
    PAST_24_HOURS = "past_24_hours"
    PAST_7_DAYS = "past_7_days"
    PAST_30_DAYS = "past_30_days"
    PAST_180_DAYS = "past_180_days"


class ScanExecutionStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanLifecycle(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ScanCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inspect: bool
    cancel: bool
    run_again: bool
    download: bool
    archive: bool
    unarchive: bool
    delete: bool
    use_for_run: bool


class TrackedCompanyResource(BaseModel):
    model_config = ConfigDict(extra="allow")

    company_id: str
    company_name: str
    careers_url: str
    provider_id: str
    provider_label: str | None = None
    row_revision: int = 1
    created_at: datetime.datetime
    updated_at: datetime.datetime


class TrackedCompanyWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(min_length=1, max_length=120)
    careers_url: str

    @field_validator("company_name")
    @classmethod
    def normalize_company_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("company name is required")
        return normalized

    @field_validator("careers_url")
    @classmethod
    def validate_careers_url(cls, value: str) -> str:
        parsed = urlsplit(value.strip())
        if (
            parsed.scheme.lower() != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("use a public HTTPS URL without credentials, query, or fragment")
        return urlunsplit(("https", parsed.netloc.lower(), parsed.path or "/", "", ""))


def _ordered_trimmed(values: list[str], *, max_items: int, max_length: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = raw.strip()
        if not value or value in seen:
            continue
        if len(value) > max_length:
            raise ValueError(f"value exceeds {max_length} characters")
        seen.add(value)
        result.append(value)
    if len(result) > max_items:
        raise ValueError(f"list exceeds {max_items} items")
    return result


class ScanCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scan_name: str | None = Field(default=None, max_length=120)
    company_ids: list[str]
    job_titles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    published_window: PublishedWindow = PublishedWindow.ANY
    total_rows: int = Field(default=50, ge=1, le=200)

    @field_validator("scan_name", mode="before")
    @classmethod
    def normalize_scan_name(cls, value: Any) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None

    @field_validator("company_ids")
    @classmethod
    def normalize_company_ids(cls, value: list[str]) -> list[str]:
        normalized = _ordered_trimmed(value, max_items=500, max_length=200)
        if not normalized:
            raise ValueError("at least one tracked company is required")
        return normalized

    @field_validator("job_titles")
    @classmethod
    def normalize_job_titles(cls, value: list[str]) -> list[str]:
        return _ordered_trimmed(value, max_items=50, max_length=120)

    @field_validator("locations")
    @classmethod
    def normalize_locations(cls, value: list[str]) -> list[str]:
        return _ordered_trimmed(value, max_items=50, max_length=200)


class ScanResource(BaseModel):
    model_config = ConfigDict(extra="allow")

    scan_id: str
    scan_name: str
    execution_status: ScanExecutionStatus
    lifecycle: ScanLifecycle
    row_revision: int
    created_at: datetime.datetime
    started_at: datetime.datetime | None = None
    finished_at: datetime.datetime | None = None
    company_count: int = 0
    output_record_count: int | None = None
    capabilities: ScanCapabilities
    warnings: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("warnings")
    @classmethod
    def bound_warnings(cls, value: list[str]) -> list[str]:
        return [str(item)[:500] for item in value]


class ScanLifecycleItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scan_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)

    @field_validator("scan_id")
    @classmethod
    def normalize_scan_id(cls, value: str) -> str:
        return value.strip()


class ScanLifecycleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ScanLifecycleItem] = Field(min_length=1, max_length=500)

    @field_validator("items")
    @classmethod
    def reject_duplicate_ids(cls, value: list[ScanLifecycleItem]) -> list[ScanLifecycleItem]:
        ids = [item.scan_id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate scan IDs are not allowed")
        return value


class ScanDeletePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scan_ids: list[str] = Field(min_length=1, max_length=500)

    @field_validator("scan_ids")
    @classmethod
    def normalize_scan_ids(cls, value: list[str]) -> list[str]:
        normalized = _ordered_trimmed(value, max_items=500, max_length=200)
        if len(normalized) != len(value):
            raise ValueError("scan IDs must be non-empty and unique")
        return normalized


class ScanDeleteRequest(ScanDeletePreviewRequest):
    preview_revision: str = Field(min_length=1)


class ScanRunAgainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scan_name: str | None = Field(default=None, max_length=120)
    expected_revision: int | None = Field(default=None, ge=1)

    @field_validator("scan_name", mode="before")
    @classmethod
    def normalize_replacement_name(cls, value: Any) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None


_WINDOW_DELTAS = {
    PublishedWindow.PAST_12_HOURS: datetime.timedelta(hours=12),
    PublishedWindow.PAST_24_HOURS: datetime.timedelta(hours=24),
    PublishedWindow.PAST_7_DAYS: datetime.timedelta(days=7),
    PublishedWindow.PAST_30_DAYS: datetime.timedelta(days=30),
    PublishedWindow.PAST_180_DAYS: datetime.timedelta(days=180),
}


def resolve_publication_cutoff(
    window: PublishedWindow | str,
    created_at: datetime.datetime,
) -> datetime.datetime | None:
    resolved_window = PublishedWindow(window)
    if resolved_window is PublishedWindow.ANY:
        return None
    if created_at.tzinfo is None:
        raise ValueError("created_at must be timezone-aware")
    return created_at.astimezone(datetime.timezone.utc) - _WINDOW_DELTAS[resolved_window]


_TERMINAL_STATUSES = {
    ScanExecutionStatus.SUCCEEDED,
    ScanExecutionStatus.FAILED,
    ScanExecutionStatus.CANCELLED,
}


def derive_scan_capabilities(
    *,
    execution_status: ScanExecutionStatus | str,
    lifecycle: ScanLifecycle | str,
    output_manifest_exists: bool = False,
    output_integrity_valid: bool = False,
    output_record_count: int | None = None,
    cancellation_requested: bool = False,
    referenced_by_run: bool = False,
) -> ScanCapabilities:
    status = ScanExecutionStatus(execution_status)
    resolved_lifecycle = ScanLifecycle(lifecycle)
    terminal = status in _TERMINAL_STATUSES
    active = resolved_lifecycle is ScanLifecycle.ACTIVE
    succeeded = status is ScanExecutionStatus.SUCCEEDED
    return ScanCapabilities(
        inspect=True,
        cancel=active and status in {ScanExecutionStatus.QUEUED, ScanExecutionStatus.RUNNING} and not cancellation_requested,
        run_again=terminal,
        download=succeeded and output_manifest_exists,
        archive=active and terminal,
        unarchive=not active and terminal,
        delete=not active and terminal and not referenced_by_run,
        use_for_run=active and succeeded and output_integrity_valid and bool(output_record_count),
    )


_ALLOWED_TRANSITIONS = {
    ScanExecutionStatus.QUEUED: {ScanExecutionStatus.RUNNING, ScanExecutionStatus.CANCELLING, ScanExecutionStatus.FAILED},
    ScanExecutionStatus.RUNNING: {ScanExecutionStatus.CANCELLING, ScanExecutionStatus.SUCCEEDED, ScanExecutionStatus.FAILED},
    ScanExecutionStatus.CANCELLING: {ScanExecutionStatus.CANCELLED, ScanExecutionStatus.FAILED},
    ScanExecutionStatus.SUCCEEDED: set(),
    ScanExecutionStatus.FAILED: set(),
    ScanExecutionStatus.CANCELLED: set(),
}


def validate_scan_transition(
    current: ScanExecutionStatus | str,
    target: ScanExecutionStatus | str,
) -> ScanExecutionStatus:
    current_status = ScanExecutionStatus(current)
    target_status = ScanExecutionStatus(target)
    if target_status not in _ALLOWED_TRANSITIONS[current_status]:
        raise ValueError(f"invalid scan transition: {current_status.value} to {target_status.value}")
    return target_status

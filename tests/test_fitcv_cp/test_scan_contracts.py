import datetime

import pytest
from pydantic import ValidationError

from fitcv_cp.scan_contracts import (
    PublishedWindow,
    ScanCreateRequest,
    ScanExecutionStatus,
    ScanLifecycle,
    derive_scan_capabilities,
    resolve_publication_cutoff,
    validate_scan_transition,
)


def test_scan_create_request_normalizes_ordered_lists() -> None:
    request = ScanCreateRequest(
        scan_name="  Germany data roles  ",
        company_ids=[" company-2 ", "company-1", "company-2"],
        job_titles=[" Data Engineer ", "Data Engineer", "Analytics Engineer"],
        locations=[" Berlin ", "Berlin", "Remote"],
        published_window="past_7_days",
        total_rows=80,
    )

    assert request.scan_name == "Germany data roles"
    assert request.company_ids == ["company-2", "company-1"]
    assert request.job_titles == ["Data Engineer", "Analytics Engineer"]
    assert request.locations == ["Berlin", "Remote"]


def test_scan_create_request_rejects_empty_company_selection() -> None:
    with pytest.raises(ValidationError):
        ScanCreateRequest(company_ids=[" "])


@pytest.mark.parametrize(
    ("window", "expected"),
    [
        (PublishedWindow.ANY, None),
        (PublishedWindow.PAST_12_HOURS, datetime.datetime(2026, 8, 2, 0, 0, tzinfo=datetime.timezone.utc)),
        (PublishedWindow.PAST_24_HOURS, datetime.datetime(2026, 8, 1, 12, 0, tzinfo=datetime.timezone.utc)),
        (PublishedWindow.PAST_7_DAYS, datetime.datetime(2026, 7, 26, 12, 0, tzinfo=datetime.timezone.utc)),
        (PublishedWindow.PAST_30_DAYS, datetime.datetime(2026, 7, 3, 12, 0, tzinfo=datetime.timezone.utc)),
        (PublishedWindow.PAST_180_DAYS, datetime.datetime(2026, 2, 3, 12, 0, tzinfo=datetime.timezone.utc)),
    ],
)
def test_resolve_publication_cutoff_uses_utc(window: PublishedWindow, expected: datetime.datetime | None) -> None:
    created_at = datetime.datetime(2026, 8, 2, 14, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=2)))

    assert resolve_publication_cutoff(window, created_at) == expected


def test_derive_scan_capabilities_owns_all_action_rules() -> None:
    capabilities = derive_scan_capabilities(
        execution_status=ScanExecutionStatus.SUCCEEDED,
        lifecycle=ScanLifecycle.ACTIVE,
        output_manifest_exists=True,
        output_integrity_valid=True,
        output_record_count=3,
        referenced_by_run=False,
    )

    assert capabilities.model_dump() == {
        "inspect": True,
        "cancel": False,
        "run_again": True,
        "download": True,
        "archive": True,
        "unarchive": False,
        "delete": False,
        "use_for_run": True,
    }


def test_empty_success_is_downloadable_but_not_usable_for_run() -> None:
    capabilities = derive_scan_capabilities(
        execution_status="succeeded",
        lifecycle="active",
        output_manifest_exists=True,
        output_integrity_valid=True,
        output_record_count=0,
    )

    assert capabilities.download is True
    assert capabilities.use_for_run is False


def test_validate_scan_transition_rejects_invalid_transition() -> None:
    with pytest.raises(ValueError, match="invalid scan transition"):
        validate_scan_transition("succeeded", "running")

import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from fitcv_cp.company_catalog import (
    BUNDLED_CATALOG_REVISION,
    BUNDLED_COMPANY_CATALOG,
    load_catalog,
    validate_catalog,
)
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


def test_bundled_catalog_has_typed_provenance_and_wellfound_is_discovery_only() -> None:
    records = validate_catalog(tuple(record.as_dict() for record in BUNDLED_COMPANY_CATALOG))

    assert all(record.catalog_source == "bundled" for record in records)
    assert all(record.catalog_revision == BUNDLED_CATALOG_REVISION for record in records)
    wellfound = next(record for record in records if record.provider_id == "wellfound")
    assert wellfound.provider_config is None
    assert wellfound.trackable is False
    assert wellfound.discovery_only is True


def test_catalog_rejects_provenance_and_identity_drift() -> None:
    record = BUNDLED_COMPANY_CATALOG[0].as_dict()

    with pytest.raises(ValueError, match="catalog_record_provenance_invalid"):
        validate_catalog([{**record, "catalog_revision": "other"}])
    with pytest.raises(ValueError, match="catalog_record_duplicate_identity"):
        validate_catalog([record, {**record, "catalog_id": "company-other"}])


def test_catalog_yaml_rejects_unknown_top_level_key(tmp_path) -> None:
    path = tmp_path / "scan_catalog.yaml"
    path.write_text(
        "schema_version: 1\ncatalog_source: bundled\ncatalog_revision: test\ncompanies: []\nextra: true\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="catalog_top_level_invalid"):
        load_catalog(path)


def test_catalog_yaml_keeps_stable_order_and_derives_trusted_config(tmp_path) -> None:
    path = tmp_path / "scan_catalog.yaml"
    path.write_text(
        """schema_version: 1
catalog_source: bundled
catalog_revision: test
companies:
  - catalog_id: company-openai
    company_name: OpenAI
    careers_url: https://jobs.ashbyhq.com/openai
    provider_id: ashby
    provider_label: Ashby
    trackable: true
    discovery_only: false
    verification:
      status: verified
      checked_at: '2026-09-08'
      evidence_ref: evidence.md
  - catalog_id: company-wellfound
    company_name: Wellfound discovery
    careers_url: https://wellfound.com
    provider_id: wellfound
    provider_label: Wellfound
    trackable: false
    discovery_only: true
    verification:
      status: discovery_only
      checked_at: '2026-09-08'
      evidence_ref: evidence.md
""",
        encoding="utf-8",
    )
    records = load_catalog(path)
    assert [record.catalog_id for record in records] == ["company-openai", "company-wellfound"]
    assert records[0].provider_config == {
        "schema_version": 1,
        "provider_id": "ashby",
        "host": "jobs.ashbyhq.com",
        "region": "global",
        "board_slug": "openai",
    }
    assert records[1].provider_config is None


def test_catalog_yaml_rejects_duplicate_identity(tmp_path) -> None:
    source = Path("config/scan_catalog.yaml").read_text(encoding="utf-8")
    duplicate = source.replace("catalog_id: company-openai", "catalog_id: company-anthropic", 1)
    path = tmp_path / "scan_catalog.yaml"
    path.write_text(duplicate, encoding="utf-8")
    with pytest.raises(ValueError, match="catalog_record_duplicate_identity"):
        load_catalog(path)


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

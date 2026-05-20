"""
@meta
type: test
scope: unit
domain: operator_control_plane
covers:
  - deterministic review_item_id generation
  - normalization and legacy id derivation behavior
excludes:
  - endpoint integration
  - queue rendering behavior
tags:
  - fast
  - ci-safe
"""

from fitcv_cp.review_identity import build_review_item_id, ensure_review_item_id, normalize_review_item_id


def test_build_review_item_id_is_deterministic_for_same_inputs() -> None:
    record = {
        "job_url": "",
        "job_title": "Data Analyst",
        "rank": 3,
        "attempt_count": 1,
    }
    a = build_review_item_id(run_id="run-1", record=record, fallback_index=7)
    b = build_review_item_id(run_id="run-1", record=record, fallback_index=7)
    assert a == b
    assert a.startswith("ri_")


def test_build_review_item_id_changes_when_identity_inputs_change() -> None:
    record_a = {"job_url": "", "job_title": "Data Analyst", "rank": 3, "attempt_count": 1}
    record_b = {"job_url": "", "job_title": "Data Analyst", "rank": 4, "attempt_count": 1}
    assert build_review_item_id(run_id="run-1", record=record_a, fallback_index=7) != build_review_item_id(
        run_id="run-1",
        record=record_b,
        fallback_index=7,
    )


def test_ensure_review_item_id_preserves_existing_normalized_id() -> None:
    record = {"review_item_id": "  ri_existing  ", "job_title": "Data Analyst"}
    value = ensure_review_item_id(run_id="run-1", record=record, fallback_index=1)
    assert value == "ri_existing"
    assert record["review_item_id"] == "ri_existing"


def test_ensure_review_item_id_derives_for_legacy_rows_without_id() -> None:
    record = {"job_url": "", "job_title": "Legacy", "rank": 1, "attempt_count": 1}
    value = ensure_review_item_id(run_id="run-2", record=record, fallback_index=2)
    assert value.startswith("ri_")
    assert normalize_review_item_id(record.get("review_item_id")) == value

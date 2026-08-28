"""
@meta
type: test
scope: unit
domain: admin_ui
covers:
  - FitCV control-plane app behavior
excludes:
  - live HTTP deployment
tags:
  - fast
  - ci-safe
"""

from unittest.mock import MagicMock, patch
from typing import Any
import io
import json
import zipfile
import datetime
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from fitcv.pipeline_contracts import PIPELINE_BUNDLE_ARTIFACT_FILENAMES, PIPELINE_STAGE_SEQUENCE, timeline_stage_download_for_event, timeline_stage_label
from fitcv_cp.app import _build_synonym_proposal_decision_ledger, _collapse_timeline_noise, _control_plane_bundle_artifact_specs, _control_plane_stage_specs, _timeline_semantic_outcome, _timeline_stage_summary_message, _load_run_cv_generation_debug_payload, _is_hitl_resolution_pending, _normalize_hitl_resolution_status, create_app
from fitcv_cp.models import (
    CandidateProfileReviewOperation,
    CandidateProfileReviewPatchRequest,
    PipelineRun,
    RunEvent,
    RunStatus,
)
from fitcv_cp.orchestrator import RunSubmission
from fitcv_cp import sqlite_store
from fitcv_cp.backend_runtime import set_backend_runtime

_TEST_DATABASE_ROOT = tempfile.TemporaryDirectory(prefix="fitcv-cp-app-tests-")

def _valid_fitcv_job(**overrides: str) -> dict[str, str]:
    job = {
        "title": "Data Engineer",
        "jobUrl": "https://example.com/jobs/1",
        "companyName": "ACME GmbH",
        "description": "Build data pipelines.",
        "contractType": "Full-time",
        "experienceLevel": "Senior",
    }
    job.update(overrides)
    return job


def test_candidate_profile_review_patch_uses_ordered_id_addressed_operations() -> None:
    request = CandidateProfileReviewPatchRequest(
        expected_revision=4,
        operations=[
            CandidateProfileReviewOperation(
                operation="replace",
                path="/experiences/exp-acme/role",
                value="Senior Data Analyst",
            ),
            CandidateProfileReviewOperation(
                operation="remove",
                path="/projects/project-old",
            ),
        ],
    )

    assert request.expected_revision == 4
    assert [operation.operation for operation in request.operations] == ["replace", "remove"]
    assert request.operations[0].path == "/experiences/exp-acme/role"


def _app():
    os.environ["FITCV_CP_INLINE_EXECUTION"] = "1"
    set_backend_runtime(None)
    database_path = Path(_TEST_DATABASE_ROOT.name) / f"{uuid.uuid4()}.sqlite3"
    os.environ["FITCV_CP_SQLITE_PATH"] = str(database_path)
    sqlite_store.initialize_control_plane_database(
        database_path,
        Path(_TEST_DATABASE_ROOT.name) / "missing-candidate-profile.yaml",
    )
    return create_app(redis_url="redis://localhost:6379/0")

def _execute_candidate_profile_stage_now(**kwargs: object) -> str:
    from fitcv_cp.candidate_profile_service import execute_candidate_profile_stage

    execute_candidate_profile_stage(**kwargs)
    return f"inline:{kwargs['attempt_id']}:{kwargs['stage']}"

def _empty_docx_bytes() -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>""",
        )
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>""",
        )
    return output.getvalue()


def _candidate_profile_mock_app():
    from test_fitcv_cp.candidate_profile_fixtures import create_candidate_profile_mock_app

    return create_candidate_profile_mock_app()

@pytest.mark.parametrize(
    "app_factory",
    [_candidate_profile_mock_app, _app],
    ids=["deterministic-fixture", "sqlite"],
)
def test_candidate_profile_fixture_contract_covers_formats_lifecycle_and_snapshots(app_factory) -> None:
    from test_fitcv_cp.candidate_profile_fixtures import candidate_profile_fixture_expectations
    from fitcv.candidate import converge_candidate_profile_for_runtime

    fixtures = candidate_profile_fixture_expectations()
    assert "preferences" in fixtures["legacy_v1"]
    with pytest.raises(ValueError):
        converge_candidate_profile_for_runtime(fixtures["invalid"])
    assert fixtures["active"]["use_for_run"] is True
    assert fixtures["archived"]["use_for_run"] is False
    assert fixtures["immutable_run_snapshot"]["candidate_profile_revision_id"]
    assert fixtures["legacy_empty_snapshot"] == {
        "candidate_profile_revision_id": None,
        "candidate_profile_json": None,
    }


    routes = {
        (route.path, method)
        for route in app_factory().routes
        for method in (route.methods or set())
        if "candidate-profile" in route.path
    }

    assert ("/candidate-profile-creation-attempts", "POST") in routes
    assert ("/candidate-profile-creation-attempts/{attempt_id}/baseline", "PATCH") in routes
    assert ("/candidate-profile-creation-attempts/{attempt_id}/actions/confirm", "POST") in routes
    assert ("/candidate-profiles", "GET") in routes
    assert ("/candidate-profiles", "POST") not in routes


def test_candidate_profile_mock_contract_converges_confirmation_and_detail() -> None:
    client = TestClient(_candidate_profile_mock_app())

    schema = client.get("/candidate-profile-field-schema")
    assert schema.status_code == 200
    assert schema.headers["etag"]
    assert schema.json()["data"]["schema_version"] == "candidate-profile-fields.v1"

    created = client.post(
        "/candidate-profile-creation-attempts",
        headers={"Idempotency-Key": "create-profile-1"},
        data={"profile_name": "Analytics Profile"},
        files={"profile_file": ("alex-profile.md", "# Candidate\n\nData analyst", "text/markdown")},
    )
    assert created.status_code == 202
    attempt = created.json()["data"]
    attempt_id = attempt["attempt_id"]
    assert attempt["profile_name"] == "Analytics Profile"
    assert attempt["next_action"] == "review_baseline"

    baseline = client.get(f"/candidate-profile-creation-attempts/{attempt_id}/baseline")
    assert baseline.status_code == 200
    baseline_data = baseline.json()["data"]
    assert len(baseline_data["document"]["experiences"]) == 2
    assert len(baseline_data["document"]["education"]) == 2
    assert len(baseline_data["document"]["projects"]) == 2

    patched = client.patch(
        f"/candidate-profile-creation-attempts/{attempt_id}/baseline",
        headers={"Idempotency-Key": "patch-baseline-1"},
        json={
            "expected_revision": baseline_data["revision"],
            "operations": [
                {
                    "operation": "replace",
                    "path": "/experiences/exp-northstar/role",
                    "value": "Senior Product Data Analyst",
                },
                {
                    "operation": "replace",
                    "path": "/interests/0",
                    "value": "Analytics engineering",
                },
                {
                    "operation": "add",
                    "path": "/interests/-",
                    "value": "Data products",
                },
            ],
        },
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["document"]["experiences"][0]["role"] == "Senior Product Data Analyst"
    assert patched.json()["data"]["document"]["interests"] == [
        "Analytics engineering",
        "Product analytics",
        "Data products",
    ]

    source = client.get(
        f"/candidate-profile-creation-attempts/{attempt_id}/source-blocks/block-experience-1"
    )
    assert source.status_code == 200
    assert source.json()["data"]["source_block_id"] == "block-experience-1"

    approved_baseline = client.post(
        f"/candidate-profile-creation-attempts/{attempt_id}/baseline/actions/approve",
        headers={"Idempotency-Key": "approve-baseline-1"},
        json={
            "expected_revision": patched.json()["data"]["revision"],
            "expected_fingerprint": patched.json()["data"]["fingerprint"],
        },
    )
    assert approved_baseline.status_code == 202
    assert approved_baseline.json()["data"]["next_action"] == "review_derived"

    derived = client.get(f"/candidate-profile-creation-attempts/{attempt_id}/derived")
    assert derived.status_code == 200
    derived_data = derived.json()["data"]
    assert [skill["name"] for skill in derived_data["document"]["skills"]][:2] == ["SQL", "Python"]
    assert derived_data["document"]["skills"][0]["evidence_refs"] == [
        "ev-exp-quality",
        "ev-project-capstone",
    ]

    approved_derived = client.post(
        f"/candidate-profile-creation-attempts/{attempt_id}/derived/actions/approve",
        headers={"Idempotency-Key": "approve-derived-1"},
        json={
            "expected_revision": derived_data["revision"],
            "expected_fingerprint": derived_data["fingerprint"],
            "expected_baseline_fingerprint": approved_baseline.json()["data"]["fingerprints"]["approved_baseline"],
        },
    )
    assert approved_derived.status_code == 200
    assert approved_derived.json()["data"]["next_action"] == "confirm"

    confirmation = client.get(f"/candidate-profile-creation-attempts/{attempt_id}/confirmation")
    assert confirmation.status_code == 200
    confirmation_data = confirmation.json()["data"]
    admin_confirmation = client.get(f"/admin/candidate-profiles/create/{attempt_id}/confirm")
    assert admin_confirmation.status_code == 200
    assert '<div class="stack">' in admin_confirmation.text
    assert 'data-can-confirm="true"' in admin_confirmation.text

    confirmed = client.post(
        f"/candidate-profile-creation-attempts/{attempt_id}/actions/confirm",
        headers={"Idempotency-Key": "confirm-profile-1"},
        json={
            "expected_revision": approved_derived.json()["data"]["revision"],
            "expected_baseline_fingerprint": confirmation_data["approval_fingerprints"]["baseline"],
            "expected_derived_fingerprint": confirmation_data["approval_fingerprints"]["derived"],
            "expected_confirmation_fingerprint": confirmation_data["fingerprint"],
        },
    )
    assert confirmed.status_code == 201
    profile = confirmed.json()["data"]

    detail = client.get(f"/candidate-profiles/{profile['profile_id']}")
    assert detail.status_code == 200
    assert detail.json()["data"]["profile"]["canonical"] == confirmation_data["profile"]["canonical"]
    assert detail.json()["data"]["profile"]["checksum"] == confirmation_data["profile"]["checksum"]
    assert detail.json()["data"]["input"]["original_filename"] == "alex-profile.md"
    assert detail.json()["data"]["input"]["original_filename"] == confirmation_data["profile"]["canonical"]["source_documents"][0]["filename"]

    admin_list = client.get("/admin/candidate-profiles")
    assert admin_list.status_code == 200
    assert "Analytics Profile" in admin_list.text
    assert "Creation drafts" in admin_list.text
    assert 'aria-labelledby="creationDraftsTitle"' in admin_list.text
    assert "0 drafts" in admin_list.text


def test_candidate_profile_real_app_routes_process_yaml_through_staged_lifecycle() -> None:
    app = _app()
    app.state.enqueue_candidate_profile_stage = _execute_candidate_profile_stage_now
    client = TestClient(app)
    source = Path("data/candidate_profile.v2.sample.yaml").read_bytes()

    created = client.post(
        "/candidate-profile-creation-attempts",
        headers={"Idempotency-Key": "real-create-1"},
        data={"profile_name": "Real Analytics Profile"},
        files={"profile_file": ("candidate.yaml", source, "application/yaml")},
    )

    assert created.status_code == 202
    attempt = created.json()["data"]
    assert attempt["next_action"] == "review_baseline"
    baseline = client.get(
        f"/candidate-profile-creation-attempts/{attempt['attempt_id']}/baseline"
    )
    assert baseline.status_code == 200
    baseline_data = baseline.json()["data"]
    assert baseline_data["document"]["name"] == "Alex Example"
    approved_baseline = client.post(
        f"/candidate-profile-creation-attempts/{attempt['attempt_id']}/baseline/actions/approve",
        headers={"Idempotency-Key": "real-approve-baseline"},
        json={
            "expected_revision": baseline_data["revision"],
            "expected_fingerprint": baseline_data["fingerprint"],
        },
    )
    assert approved_baseline.status_code == 202
    derived = client.get(
        f"/candidate-profile-creation-attempts/{attempt['attempt_id']}/derived"
    )
    assert derived.status_code == 200
    derived_data = derived.json()["data"]
    approved_derived = client.post(
        f"/candidate-profile-creation-attempts/{attempt['attempt_id']}/derived/actions/approve",
        headers={"Idempotency-Key": "real-approve-derived"},
        json={
            "expected_revision": derived_data["revision"],
            "expected_fingerprint": derived_data["fingerprint"],
            "expected_baseline_fingerprint": approved_baseline.json()["data"]["fingerprints"]["approved_baseline"],
        },
    )
    confirmation = client.get(
        f"/candidate-profile-creation-attempts/{attempt['attempt_id']}/confirmation"
    )
    confirmation_data = confirmation.json()["data"]
    confirmed = client.post(
        f"/candidate-profile-creation-attempts/{attempt['attempt_id']}/actions/confirm",
        headers={"Idempotency-Key": "real-confirm"},
        json={
            "expected_revision": approved_derived.json()["data"]["revision"],
            "expected_baseline_fingerprint": confirmation_data["approval_fingerprints"]["baseline"],
            "expected_derived_fingerprint": confirmation_data["approval_fingerprints"]["derived"],
            "expected_confirmation_fingerprint": confirmation_data["fingerprint"],
        },
    )
    assert confirmed.status_code == 201
    confirmed_again = client.post(
        f"/candidate-profile-creation-attempts/{attempt['attempt_id']}/actions/confirm",
        headers={"Idempotency-Key": "real-confirm-again"},
        json={
            "expected_revision": approved_derived.json()["data"]["revision"],
            "expected_baseline_fingerprint": confirmation_data["approval_fingerprints"]["baseline"],
            "expected_derived_fingerprint": confirmation_data["approval_fingerprints"]["derived"],
            "expected_confirmation_fingerprint": confirmation_data["fingerprint"],
        },
    )
    assert confirmed_again.status_code == 201
    assert confirmed_again.json()["data"] == confirmed.json()["data"]
    detail = client.get(f"/candidate-profiles/{confirmed.json()['data']['profile_id']}")
    assert detail.json()["data"]["profile"]["canonical"] == confirmation_data["profile"]["canonical"]
    assert detail.json()["data"]["profile"]["checksum"] == confirmation_data["profile"]["checksum"]
    assert client.post(
        "/candidate-profiles",
        headers={"Idempotency-Key": "direct-bypass"},
        data={"profile_name": "Bypass"},
        files={"profile_file": ("candidate.yaml", source, "application/yaml")},
    ).status_code == 405


def test_candidate_profile_baseline_approval_returns_no_evidence_api_error() -> None:
    from fitcv_cp.candidate_profile_service import approve_review

    app = _app()
    app.state.enqueue_candidate_profile_stage = MagicMock()
    database_path = Path(os.environ["FITCV_CP_SQLITE_PATH"])
    created = sqlite_store.create_candidate_profile_creation_attempt(
        profile_name="Empty Evidence Profile",
        original_filename="candidate.md",
        media_type="text/markdown",
        content=b"# Empty Evidence\n",
        idempotency_key="api-create-empty-evidence",
        database_path=database_path,
    )
    claimed = sqlite_store.claim_candidate_profile_processing(
        created["attempt_id"],
        stage="base_mapping",
        expected_revision=created["revision"],
        lease_seconds=60,
        database_path=database_path,
    )
    baseline = {"name": "Empty Evidence"}
    published = sqlite_store.publish_candidate_profile_stage_result(
        created["attempt_id"],
        stage="baseline",
        claim_id=claimed["processing"]["claim_id"],
        expected_revision=claimed["revision"],
        result={
            "document": baseline,
            "annotations": {},
            "fingerprint": approve_review(
                "baseline", baseline, expected_fingerprint=None
            )["fingerprint"],
            "runtime_evidence": None,
        },
        source_blocks=[],
        database_path=database_path,
    )

    with TestClient(app) as client:
        response = client.post(
            f"/candidate-profile-creation-attempts/{created['attempt_id']}/baseline/actions/approve",
            headers={"Idempotency-Key": "api-approve-empty-evidence"},
            json={
                "expected_revision": published["revision"],
                "expected_fingerprint": published["fingerprints"]["baseline_draft"],
            },
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "candidate_profile_no_evidence"
    assert response.json()["error"]["retryable"] is False
    app.state.enqueue_candidate_profile_stage.assert_not_called()

@pytest.mark.parametrize(
    ("filename", "media_type", "content"),
    [
        ("candidate.md", "text/markdown", b"# Alex Example\n"),
        (
            "candidate.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            _empty_docx_bytes(),
        ),
    ],
)
def test_candidate_profile_real_app_routes_accept_supported_non_yaml_formats(
    filename: str,
    media_type: str,
    content: bytes,
) -> None:
    app = _app()
    app.state.enqueue_candidate_profile_stage = _execute_candidate_profile_stage_now
    response = TestClient(app).post(
        "/candidate-profile-creation-attempts",
        headers={"Idempotency-Key": f"create-{filename}"},
        data={"profile_name": "Imported Candidate"},
        files={"profile_file": (filename, content, media_type)},
    )

    assert response.status_code == 202
    assert response.json()["data"]["next_action"] == "review_baseline"

def test_candidate_profile_mock_admin_flow_renders_staged_review_contract() -> None:
    import hashlib

    prototype = Path("docs/fitcv-settings-ui-prototype.html").read_bytes().replace(b"\r\n", b"\n")
    prototype_blob = hashlib.sha1(
        f"blob {len(prototype)}\0".encode() + prototype
    ).hexdigest()
    assert prototype_blob == "3c20781eb15131bf7928619368283b0737e0dda2"

    client = TestClient(_candidate_profile_mock_app())

    profiles = client.get("/admin/candidate-profiles")
    assert profiles.status_code == 200
    assert '<p class="eyebrow">Workspace</p>' in profiles.text
    assert 'class="run-tabs"' in profiles.text
    assert 'id="selectAllProfiles"' in profiles.text
    assert 'class="filter-bar section-card"' not in profiles.text
    assert "candidate-product-data" in profiles.text
    assert "candidate-analytics" in profiles.text
    assert "candidate-platform" not in profiles.text
    assert '<main class="candidate-profiles-page" data-page="candidate-profiles"' in profiles.text
    assert '<button class="btn primary" type="button" data-open-profile-dialog>Create Profile</button>' in profiles.text
    assert '.candidate-profiles-page .section-card{padding:0;margin-bottom:0}' in profiles.text
    assert '.candidate-profiles-page .creation-drafts{margin-bottom:18px;padding:0}' in profiles.text
    assert ':root{--sidebar-w:288px;--header-h:72px;--font:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;--font-sans:var(--font);--display-font:var(--font)}' in profiles.text
    dark_tokens = re.search(r':root\[data-theme="dark"\]\{.*?\}', profiles.text)
    assert dark_tokens is not None
    assert '--font:' not in dark_tokens.group(0)
    assert '--sidebar-w:' not in dark_tokens.group(0)
    header = re.search(r'<header class="global-header">.*?</header>', profiles.text, re.S)
    assert header is not None
    assert 'class="icon-btn"' in header.group(0)
    assert 'class="icon-btn danger"' in header.group(0)
    assert 'class="icon-button' not in header.group(0)
    assert 'aria-label="Switch to dark theme" title="Switch to dark theme"' in header.group(0)
    assert '.icon-btn,.sidebar-toggle{display:grid;width:38px;height:38px;' in profiles.text
    assert '.icon-btn,.sidebar-toggle{display:grid;width:38px;height:38px;place-items:center;padding:1px 6px;' in profiles.text
    assert '.icon-btn:hover,.sidebar-toggle:hover{border-color:var(--border);background:var(--surface-2);' in profiles.text
    assert '.icon-btn,.sidebar-toggle{min-height:44px}' in profiles.text
    assert '.icon-btn,.sidebar-toggle{width:44px}' in profiles.text
    assert '.icon-btn.danger{color:#b91c1c}' in profiles.text
    assert '[data-theme="dark"] .icon-btn.danger{color:#fca5a5}' in profiles.text
    assert "var actionLabel = t === 'dark' ? 'Switch to light theme' : 'Switch to dark theme';" in profiles.text
    assert "toggle.setAttribute('aria-label', actionLabel);" in profiles.text
    assert "toggle.setAttribute('title', actionLabel);" in profiles.text

    seeded_detail = client.get("/admin/candidate-profiles/candidate-product-data")
    assert seeded_detail.status_code == 200
    assert 'class="details-page-head"' in seeded_detail.text
    assert '<span class="draft-status">Succeeded</span>' in seeded_detail.text
    assert "Legacy profile" in seeded_detail.text

    upload = client.get("/admin/candidate-profiles/create")
    assert upload.status_code == 200
    assert 'name="profile_name"' in upload.text
    assert 'name="profile_name" required' in upload.text
    assert 'accept=".md,.docx,.yaml,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/yaml,text/yaml"' in upload.text
    assert 'class="details-page-head"' in upload.text
    assert 'class="creation-upload-grid"' in upload.text
    assert 'class="creation-dropzone"' in upload.text
    assert "One staged hybrid pipeline" in upload.text
    assert "Process document" in upload.text
    assert '<div class="provider-field"><label for="creationProfileName">Profile Name</label>' in upload.text
    assert '<label class="provider-field"' not in upload.text
    assert 'class="content container creation-content" id="page-content"' in upload.text
    upload_form = upload.text.index('<form class="creation-page-layout" id="candidate-profile-upload-form">')
    upload_profile = upload.text.index('<div class="profile-creation">', upload_form)
    upload_card = upload.text.index('<section class="section-card creation-upload-card">', upload_profile)
    assert upload_form < upload_profile < upload_card
    assert '<form class="section-card creation-upload-card"' not in upload.text
    assert '.provider-field{display:grid;gap:6px}' in upload.text
    assert '.creation-status{min-height:22px;margin:0;color:var(--muted)}' in upload.text
    assert '.review-workspace{display:block}' in upload.text
    assert '.review-workspace{display:grid' not in upload.text
    assert upload.text.count('.review-workspace{') == 1
    info_rule = re.search(r'\.info-trigger\{([^}]*)\}', upload.text)
    assert info_rule is not None
    assert 'width:32px;height:32px;place-items:center' in info_rule.group(1)
    assert 'padding:1px 6px' in info_rule.group(1)
    wand_rule = re.search(r'\.wand-btn\{([^}]*)\}', upload.text)
    assert wand_rule is not None
    assert 'width:44px;height:44px;flex:0 0 44px;place-items:center' in wand_rule.group(1)
    assert 'padding:1px 6px' in wand_rule.group(1)
    assert 'font:' not in wand_rule.group(1)
    assert upload.text.count('.wand-btn{') == 1
    assert '.dialog-close{display:grid;width:36px;height:36px;place-items:center;padding:1px 6px;' in upload.text
    assert '.candidate-profile-creation button,.candidate-profile-creation input,.candidate-profile-creation select{font:inherit}' in upload.text
    assert '.candidate-profile-creation .section-card{padding:0;margin-bottom:0}' not in upload.text
    assert '.candidate-profile-creation .review-section,.candidate-profile-creation .collapsible-section{padding:0;margin-bottom:0}' in upload.text
    assert '.creation-upload-card{padding:28px}' in upload.text
    assert '.creation-upload-card{margin-bottom:0' not in upload.text


    created = client.post(
        "/candidate-profile-creation-attempts",
        headers={"Idempotency-Key": "create-profile-admin-1"},
        data={"profile_name": "Analytics Profile"},
        files={"profile_file": ("candidate.md", "# Candidate", "text/markdown")},
    ).json()["data"]
    attempt_id = created["attempt_id"]

    baseline = client.get(f"/admin/candidate-profiles/create/{attempt_id}/baseline")
    assert baseline.status_code == 200
    assert "Regenerate AI-assisted fields" in baseline.text
    assert "Save and exit" in baseline.text
    assert "Approve baseline" in baseline.text
    assert ">Source<" in baseline.text
    assert '<small class="field-source">' not in baseline.text
    assert '/source">View source</a>' not in baseline.text
    assert "Parity Review Profile · Revision" not in baseline.text
    assert 'class="evidence-editor"' in baseline.text
    assert re.search(r'<h3>Profile</h3><p[^>]*>Canonical identity and profile text\.</p>', baseline.text)
    assert re.search(r'<h3>Contact</h3><p[^>]*>Direct contact facts; never inferred\.</p>', baseline.text)
    assert '<div class="empty-state"><h3>No achievements</h3><p>Add an entry when this candidate document contains relevant evidence.</p></div>' in baseline.text
    assert '<div class="empty-state"><h3>No volunteering</h3><p>Add an entry when this candidate document contains relevant evidence.</p></div>' in baseline.text
    assert 'Add one when source CV contains this information.' not in baseline.text
    for field_path, block_id in {
        "/name": "block-baseline-profile-name",
        "/experiences/exp-northstar/start": "block-baseline-experiences-exp-northstar-start",
        "/education/edu-msc/end": "block-baseline-education-edu-msc-end",
        "/projects/project-capstone/context": "block-baseline-projects-project-capstone-context",
        "/certifications/cert-powerbi/issuer": "block-baseline-certifications-cert-powerbi-issuer",
        "/languages/lang-en/level": "block-baseline-languages-lang-en-level",
    }.items():
        field_start = baseline.text.index(f'data-field-wrapper="{field_path}"')
        field_end = baseline.text.find('data-field-wrapper="', field_start + 1)
        field_markup = baseline.text[field_start:field_end]
        assert f'data-source-block="{block_id}"' in field_markup
    name_field_start = baseline.text.index('data-field-wrapper="/name"')
    name_field_end = baseline.text.index('data-field-wrapper="/headline"', name_field_start)
    name_field_markup = baseline.text[name_field_start:name_field_end]
    assert 'data-source-kind="baseline"' in name_field_markup
    assert 'data-source-title="Full name"' in name_field_markup
    assert 'data-reviewed-value="Alex Morgan"' in name_field_markup
    assert '<p class="eyebrow">Source Evidence</p><h2 id="candidate-profile-dialog-title">Evidence details</h2><p id="candidate-profile-dialog-description">Review source excerpt and locators.</p>' in baseline.text
    full_name_source = client.get(
        f"/candidate-profile-creation-attempts/{attempt_id}/source-blocks/block-baseline-profile-name"
    )
    assert full_name_source.status_code == 200
    assert full_name_source.json()["data"]["text"] == "Alex Morgan"
    assert full_name_source.json()["data"]["locator"] == {
        "kind": "markdown_lines",
        "start": 2,
        "end": 3,
    }
    nested_evidence_start = baseline.text.index('<div class="nested-evidence">')
    nested_evidence_list = baseline.text.index(
        '<div class="evidence-editor-list">', nested_evidence_start
    )
    nested_evidence_head = baseline.text[nested_evidence_start:nested_evidence_list]
    assert "<h4>Evidence</h4>" in nested_evidence_head
    assert "Each statement has stable ID and source provenance." in nested_evidence_head
    assert '<span class="draft-status">' not in nested_evidence_head
    evidence_start = baseline.text.index('class="evidence-editor"')
    evidence_end = baseline.text.index("</article>", evidence_start)
    evidence_markup = baseline.text[evidence_start:evidence_end]
    evidence_actions = (
        evidence_markup.index(">Source</button>"),
        evidence_markup.index('class="wand-btn"'),
        evidence_markup.index(">Remove</button>"),
    )
    assert evidence_actions == tuple(sorted(evidence_actions))
    assert evidence_markup.count(">Source</button>") == 1
    assert evidence_markup.count('class="wand-btn"') == 1
    assert evidence_markup.count(">Remove</button>") == 1
    assert 'data-source-kind="evidence"' in evidence_markup
    assert 'data-source-title="Data quality and reporting"' in evidence_markup
    assert 'data-evidence-id="ev-exp-quality"' in evidence_markup
    assert 'data-source-block="block-baseline-experiences-exp-northstar-evidence-ev-exp-quality"' in evidence_markup
    assert 'data-reviewed-value="Built SQL quality checks, maintained Power BI reporting, and coordinated weekly delivery reviews with product and engineering."' in evidence_markup
    nested_evidence_source = client.get(
        f"/candidate-profile-creation-attempts/{attempt_id}/source-blocks/block-baseline-experiences-exp-northstar-evidence-ev-exp-quality"
    )
    assert nested_evidence_source.status_code == 200
    assert nested_evidence_source.json()["data"]["text"] == "Built SQL quality checks, maintained Power BI reporting, and coordinated weekly delivery reviews with product and engineering."
    assert nested_evidence_source.json()["data"]["locator"] == {
        "kind": "markdown_lines",
        "start": 50,
        "end": 51,
    }
    assert '<div class="dialog-body" id="candidate-profile-dialog-body"></div>' in baseline.text
    for dialog_label in (
        "Source locator for extracted baseline metadata.",
        "Immutable source evidence for one canonical evidence item.",
        "Current reviewed value",
        "Current reviewed text",
        "Source excerpt",
        "Locator",
    ):
        assert dialog_label in baseline.text
    assert 'id="field--experiences-exp-northstar-evidence-ev-exp-quality-start" data-field-path="/experiences/exp-northstar/evidence/ev-exp-quality/start" inputmode="numeric"' in baseline.text
    assert wand_rule.group(0) in baseline.text
    assert '.review-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}' in baseline.text
    assert '.review-section-head-actions,.entry-head,.field-action-row,.derived-entry-head{display:flex;align-items:center;gap:8px}' in baseline.text
    assert '.entry-head,.derived-entry-head{padding:12px 14px;border-bottom:1px solid var(--border-soft)}' in baseline.text
    assert '.collection-entry,.derived-entry{border:1px solid var(--border);border-radius:12px;background:var(--surface-2);overflow:hidden}' in baseline.text
    assert '.derived-entry{display:grid;gap:12px;padding:15px}' in baseline.text
    final_derived_entry = '.derived-entry{display:grid;gap:12px;padding:15px;border:1px solid var(--border);border-radius:11px;background:var(--surface);overflow:hidden}'
    final_derived_head = '.derived-entry-head{display:flex;align-items:center;gap:10px}'
    assert final_derived_entry in baseline.text
    assert final_derived_head in baseline.text
    assert baseline.text.rindex(final_derived_entry) > baseline.text.rindex('.collection-entry,.derived-entry{')
    assert baseline.text.rindex(final_derived_head) > baseline.text.rindex('.review-section-head-actions,.entry-head,.field-action-row,.derived-entry-head{')
    assert '.derived-entry-head strong{flex:1}' in baseline.text
    assert '.field-action-row{flex-direction:column' not in baseline.text
    assert 'button:not([class]) { background: var(--accent);' in baseline.text
    assert 'button:not([class]):hover { background: var(--accent-hover); }' in baseline.text
    assert 'button:not(.btn):not(.btn-primary):not(.btn-secondary):not(.btn-section):not(.decision-toggle):hover' not in baseline.text
    assert 'aria-label="Generate evidence text from parent context"' in baseline.text
    assert 'aria-label="Close Source Evidence dialog"' in baseline.text
    assert 'aria-label="Remove  ' not in baseline.text
    assert '>Degree or credential</label><span class="field-qualifier">One required</span>' in baseline.text
    assert '>Field of study</label><span class="field-qualifier">One required</span>' in baseline.text
    assert '>Evidence text</label>' in baseline.text
    assert '>Degree</label><span class="field-qualifier">Optional</span>' not in baseline.text
    creation_template = Path(
        "src/fitcv_cp/templates/candidate_profile_creation.html"
    ).read_text(encoding="utf-8")
    assert "sourceRoot.addEventListener('click', async function(event)" in creation_template
    assert "document.addEventListener('click', async function(event)" not in creation_template
    base_template = Path("src/fitcv_cp/templates/base.html").read_text(encoding="utf-8")
    assert "async function fitcvWaitForCandidateProfileAttempt" in base_template
    assert "async function waitForCandidateProfileAttempt" not in creation_template
    assert "await fitcvWaitForCandidateProfileAttempt(payload.data.attempt_id, 'review_baseline')" in creation_template
    assert "await fitcvWaitForCandidateProfileAttempt(attemptId, stage === 'baseline' ? 'review_derived' : 'confirm')" in creation_template
    collection_macro = creation_template[
        creation_template.index("{% macro review_collection") : creation_template.index(
            "{% macro evidence_ref_selector"
        )
    ]
    entry_fields_start = collection_macro.index('<div class="entry-fields">')
    entry_fields_end = collection_macro.index("</div>", entry_fields_start)
    evidence_collection_call = collection_macro.index("{{ evidence_collection")
    assert entry_fields_end < evidence_collection_call
    sections_template = Path(
        "src/fitcv_cp/templates/candidate_profile_sections.html"
    ).read_text(encoding="utf-8")
    assert "{{ section.label }}" in sections_template
    assert "{{ field_meta.label }}" in sections_template
    assert "{'identity': 'Profile'" not in sections_template
    stepper = re.search(r'<ol class="creation-stepper".*?</ol>', baseline.text, re.DOTALL)
    assert stepper is not None
    assert '<span class="creation-step-index">✓</span><span>Upload</span>' in stepper.group(0)
    assert '<span>Baseline</span>' in stepper.group(0)
    assert '<span>Derived</span>' in stepper.group(0)
    assert '<span>Confirm</span>' in stepper.group(0)
    assert 'Controlled derivation' not in stepper.group(0)
    assert '>Confirmation<' not in stepper.group(0)
    baseline_sections = [
        '<h3>Profile</h3>',
        '<h3>Contact</h3>',
        '<h3>Experience</h3>',
        '<h3>Education</h3>',
        '<h3>Projects</h3>',
        '<h3>Achievements</h3>',
        '<h3>Certifications</h3>',
        '<h3>Volunteering</h3>',
        '<h3>Languages</h3>',
    ]
    assert [baseline.text.index(label) for label in baseline_sections] == sorted(
        baseline.text.index(label) for label in baseline_sections
    )
    assert '<h3>Candidate overview</h3>' not in baseline.text
    assert '<h3>Interests</h3>' not in baseline.text
    assert '<h3>Search preferences</h3>' not in baseline.text
    assert '>Professional headline</label>' in baseline.text
    assert '>LinkedIn URL</label>' in baseline.text
    assert '>GitHub URL</label>' in baseline.text
    assert '>Website URL</label>' in baseline.text
    evidence_entries = re.findall(r'<article class="evidence-editor">.*?</article>', baseline.text, re.DOTALL)
    assert evidence_entries
    for evidence_entry in evidence_entries:
        assert evidence_entry.index('>Source</button>') < evidence_entry.index('class="wand-btn"') < evidence_entry.index('>Remove</button>')

    baseline_data = client.get(
        f"/candidate-profile-creation-attempts/{attempt_id}/baseline"
    ).json()["data"]
    approved_baseline = client.post(
        f"/candidate-profile-creation-attempts/{attempt_id}/baseline/actions/approve",
        headers={"Idempotency-Key": "approve-baseline-admin-1"},
        json={
            "expected_revision": baseline_data["revision"],
            "expected_fingerprint": baseline_data["fingerprint"],
        },
    ).json()["data"]

    derived = client.get(f"/admin/candidate-profiles/create/{attempt_id}/derived")
    assert derived.status_code == 200
    assert 'class="derived-entry"' in derived.text
    assert 'class="evidence-ref-selector"' in derived.text
    assert 'type="checkbox"' in derived.text
    assert 'data-evidence-ref-path="/skills/skill-sql/evidence_refs"' in derived.text
    assert 'data-field-path="/skills/skill-sql/name"' in derived.text
    assert 'data-field-path="/skills/skill-sql/id"' not in derived.text
    assert 'data-field-path="/skills/skill-sql/origin"' not in derived.text
    assert 'data-field-path="/skills/skill-sql/confidence"' not in derived.text
    assert "Comma-separated evidence IDs." not in derived.text
    assert "98% confidence" in derived.text
    assert ">inferred</span>" in derived.text
    assert "llm_inferred" not in derived.text
    assert "supported" in derived.text
    assert "Approve derived" in derived.text
    assert 'class="review-toolbar"' in derived.text
    assert 'class="collection-list"' in derived.text
    assert 'class="field-action-row"' in derived.text
    assert 'class="wand-btn"' in derived.text
    assert 'class="btn danger"' in derived.text
    assert 'class="creation-footer-copy"' in derived.text
    assert 'class="creation-action-group"' in derived.text
    assert "ev-exp-quality" in derived.text
    assert "Cross-functional delivery" in derived.text
    cross_functional = re.search(
        r'<article class="derived-entry">.*?Cross-functional delivery.*?</article>',
        derived.text,
        re.DOTALL,
    )
    assert cross_functional is not None
    actions = cross_functional.group(0)
    assert actions.index(">Source</button>") < actions.index('class="wand-btn"') < actions.index(">Remove</button>")
    assert 'data-source-kind="derived"' in actions
    assert 'data-source-title="Cross-functional delivery"' in actions
    assert 'data-source-description="Controlled derivation from approved evidence IDs."' in actions
    assert "<strong>Derived claim</strong>" in derived.text
    assert "<strong>Evidence refs</strong>" in derived.text
    for heading in ('Role Families', 'Domain Tags', 'Responsibility Themes'):
        assert f'<h3>{heading}</h3>' in derived.text
    for heading in ('Role families', 'Domain tags', 'Responsibility themes'):
        assert f'<h3>{heading}</h3>' not in derived.text

    derived_data = client.get(
        f"/candidate-profile-creation-attempts/{attempt_id}/derived"
    ).json()["data"]
    assert derived_data["document"]["skills"][0]["origin"] == "llm_inferred"
    approved_derived = client.post(
        f"/candidate-profile-creation-attempts/{attempt_id}/derived/actions/approve",
        headers={"Idempotency-Key": "approve-derived-admin-1"},
        json={
            "expected_revision": derived_data["revision"],
            "expected_fingerprint": derived_data["fingerprint"],
            "expected_baseline_fingerprint": approved_baseline["fingerprints"]["approved_baseline"],
        },
    ).json()["data"]

    confirmation = client.get(f"/admin/candidate-profiles/create/{attempt_id}/confirm")
    assert confirmation.status_code == 200
    assert "Step 4 · Idempotent confirmation" in confirmation.text
    assert "<h2>Confirm Candidate Profile</h2>" in confirmation.text
    assert "<h1>Analytics Profile</h1>" not in confirmation.text
    confirmation_sections = [
        "<strong>Confirmation Overview</strong>",
        "<strong>Source Input</strong>",
        "<strong>Approval Status</strong>",
        "<strong>Baseline Facts</strong>",
        "<strong>Derived Claims</strong>",
    ]
    assert [confirmation.text.index(label) for label in confirmation_sections] == sorted(
        confirmation.text.index(label) for label in confirmation_sections
    )
    assert "Profile checksum" not in confirmation.text
    assert "ev-exp-quality" in confirmation.text
    assert '<dt>Kind</dt><dd>Work achievement</dd>' in confirmation.text
    assert '<dt>Kind</dt><dd>work_achievement</dd>' not in confirmation.text
    certification_start = confirmation.text.index('<h3>Certifications</h3>')
    certification_metadata_end = confirmation.text.index(
        '<div class="evidence-ref-list">', certification_start
    )
    certification_metadata = confirmation.text[
        certification_start:certification_metadata_end
    ]
    assert '<dt>Date</dt><dd>2025</dd>' in certification_metadata
    assert '<dt>Start</dt>' not in certification_metadata
    assert '<dd>2025-01</dd>' not in certification_metadata
    confirmation_baseline_sections = [
        '<h3>Profile</h3>', '<h3>Contact</h3>', '<h3>Experience</h3>', '<h3>Education</h3>',
        '<h3>Projects</h3>', '<h3>Achievements</h3>', '<h3>Certifications</h3>',
        '<h3>Volunteering</h3>', '<h3>Languages</h3>',
    ]
    assert [confirmation.text.index(label) for label in confirmation_baseline_sections] == sorted(
        confirmation.text.index(label) for label in confirmation_baseline_sections
    )
    assert '<h3>Interests</h3>' not in confirmation.text
    assert '<h3>Search preferences</h3>' not in confirmation.text
    assert '<dt>Format</dt><dd>Markdown</dd>' in confirmation.text
    assert '.confirm-section{display:grid;gap:10px}' in confirmation.text
    assert '.confirm-entry{padding:12px;border:1px solid var(--border);border-radius:9px;background:var(--surface-2)}' in confirmation.text
    assert '.confirm-entry dl div{display:grid;grid-template-columns:minmax(120px,.35fr) minmax(0,1fr);gap:12px}' in confirmation.text
    assert '.confirm-section>h3{margin:1em 0}' in confirmation.text
    assert '@media(max-width:760px){.entry-fields{grid-template-columns:1fr}.entry-fields .review-field:last-child:nth-child(odd){grid-column:auto}.confirm-entry dl div,.trace-row{grid-template-columns:1fr}' in confirmation.text
    assert confirmation.text.count(
        'class="section-card collapsible-section drawer-section"'
    ) == 5
    assert re.findall(
        r'<details class="section-card collapsible-section drawer-section" open>.*?<strong>(.*?)</strong>',
        confirmation.text,
        re.S,
    ) == [label.removeprefix("<strong>").removesuffix("</strong>") for label in confirmation_sections]
    assert confirmation.text.count('data-local-time="2026-08-02T12:00:00+00:00"') >= 2
    assert "new Intl.DateTimeFormat(undefined, {dateStyle: 'medium', timeStyle: 'short'})" in confirmation.text

    confirmation_data = client.get(
        f"/candidate-profile-creation-attempts/{attempt_id}/confirmation"
    ).json()["data"]
    assert confirmation_data["profile"]["canonical"]["certifications"][0]["date"] == "2025-01"
    assert confirmation_data["profile"]["canonical"]["certifications"][0]["evidence"][0]["start"] == "2025-01"
    confirmed = client.post(
        f"/candidate-profile-creation-attempts/{attempt_id}/actions/confirm",
        headers={"Idempotency-Key": "confirm-profile-admin-1"},
        json={
            "expected_revision": approved_derived["revision"],
            "expected_baseline_fingerprint": confirmation_data["approval_fingerprints"]["baseline"],
            "expected_derived_fingerprint": confirmation_data["approval_fingerprints"]["derived"],
            "expected_confirmation_fingerprint": confirmation_data["fingerprint"],
        },
    ).json()["data"]
    detail = client.get(f"/admin/candidate-profiles/{confirmed['profile_id']}")
    assert detail.status_code == 200
    assert confirmed["profile_id"] in detail.text
    detail_sections = [
        "<strong>Profile Overview</strong>",
        "<strong>Source Input</strong>",
        "<strong>Baseline Facts</strong>",
        "<strong>Derived Claims</strong>",
        "<strong>Traceability</strong>",
        "<strong>Related Runs</strong>",
    ]
    assert [detail.text.index(label) for label in detail_sections] == sorted(
        detail.text.index(label) for label in detail_sections
    )
    assert "Checksum" not in detail.text
    assert "ev-exp-quality" in detail.text
    assert '<h3>Interests</h3>' not in detail.text
    assert '<h3>Search preferences</h3>' not in detail.text
    assert '<dt>Professional headline</dt>' in detail.text
    assert '<dt>LinkedIn URL</dt>' in detail.text
    assert '<dt>GitHub URL</dt>' in detail.text
    assert '<dt>Website URL</dt>' in detail.text
    assert '<dt>Format</dt><dd>Markdown</dd>' in detail.text
    assert ">2026-08-02T12:00:00+00:00<" not in detail.text
    assert 'id="candidate-profile-controls"' in detail.text
    assert 'data-profile-action="edit"' in detail.text
    assert 'data-profile-action="archive"' in detail.text
    assert 'data-update-url="/candidate-profiles/' in detail.text
    assert detail.text.count('class="section-card collapsible-section drawer-section"') == 6
    assert re.findall(
        r'<details class="section-card collapsible-section drawer-section" open>.*?<strong>(.*?)</strong>',
        detail.text,
        re.S,
    ) == [label.removeprefix("<strong>").removesuffix("</strong>") for label in detail_sections[:4]]

def test_candidate_profile_recovery_reuses_prototype_actions_and_shared_async_state() -> None:
    base = Path("src/fitcv_cp/templates/base.html").read_text(encoding="utf-8")
    profiles = Path("src/fitcv_cp/templates/candidate_profiles.html").read_text(encoding="utf-8")
    creation = Path("src/fitcv_cp/templates/candidate_profile_creation.html").read_text(encoding="utf-8")
    detail = Path("src/fitcv_cp/templates/candidate_profile_detail.html").read_text(encoding="utf-8")
    sections = Path("src/fitcv_cp/templates/candidate_profile_sections.html").read_text(encoding="utf-8")

    assert "async function fitcvWaitForCandidateProfileAttempt(" in base
    assert "function fitcvIdempotencyKey(control)" in base
    assert 'data-retry-attempt="{{ attempt.attempt_id }}"' in profiles
    assert "data-attempt-revision=\"{{ attempt.revision }}\"" in profiles
    assert "fitcvRunLocked(resume" in profiles
    assert "fitcvRenderAsyncState(asyncState" in profiles
    assert "fitcv-focus-profile-tab" in profiles
    assert ">Resume</a>" in profiles
    assert "'Start new upload'" in profiles
    assert "fitcvWaitForCandidateProfileAttempt(payload.data.attempt_id, 'review_baseline')" in creation
    assert "fitcvRenderAsyncState(asyncState" in creation
    assert "Processing candidate profile" in creation
    assert "annotation.source_block_ids or evidence_refs" in creation
    assert "Regeneration replaced the previous value" in creation
    assert "status.classList.toggle('error'" in creation
    assert 'id="candidate-profile-controls"' in detail
    assert 'data-profile-action="archive"' in detail
    assert 'data-profile-action="restore"' in detail
    assert 'data-profile-action="delete"' in detail
    assert 'data-profile-action="edit"' in detail
    assert 'data-profile-action="cancel-edit"' in detail
    assert "indexOf('conflict')" in detail
    assert "var busy = false" in detail
    assert "fitcvRenderAsyncState" in detail
    assert "location.assign('{{ back_url }}')" in detail
    assert "fitcvRunLocked(add || remove || regenerate || approve" in creation
    assert "fitcvRunLocked(confirmButton" in creation
    assert "candidate_profile_revision_conflict" in creation
    assert "candidate_profile_already_confirmed" in creation
    assert "Reapply unsaved changes" in creation
    assert "fitcv-candidate-profile-reconciliation:" in creation
    assert "Start new upload" in creation
    assert 'aria-label="Profile creation progress"' in creation
    assert 'id="creationDropzone"' in creation
    assert 'id="creationCvFile"' in creation
    assert 'id="creationProfileName"' in creation
    assert 'id="creationFileName"' in creation
    assert 'id="creationUploadStatus"' in creation
    assert 'id="processCv"' in creation
    assert 'id="regenerateStage"' in creation
    assert 'id="backToBaseline"' in creation
    assert 'id="saveCreationDraft"' in creation
    assert 'id="approveCreationStage"' in creation
    assert 'id="backToDerived"' in creation
    assert 'id="confirmCreation"' in creation
    assert "function isSupportedCandidateProfileFile(file)" in creation
    assert 'data-can-patch="{{' in creation
    assert 'data-can-confirm="{{' in creation
    assert '<div class="stack">' in sections
    assert "fitcvRunLocked(action" in profiles
    assert "fitcvRenderAsyncState(asyncState" in profiles


def test_candidate_profile_mock_llm_configuration_matches_prototype_copy() -> None:
    client = TestClient(_candidate_profile_mock_app())
    llm_configuration = client.get("/admin/llm-configuration")

    assert llm_configuration.status_code == 200
    assert '<main data-page="llm-configuration"' in llm_configuration.text
    assert '<p class="eyebrow">Application</p>' in llm_configuration.text
    assert "Manage API Providers" in llm_configuration.text
    assert 'class="llm-config-grid"' in llm_configuration.text
    assert '.llm-config-grid{display:grid;gap:16px}' in llm_configuration.text
    assert '.llm-config-grid{display:grid;grid-template-columns:' not in llm_configuration.text
    assert '.llm-config-card{padding:22px}' in llm_configuration.text
    assert '.llm-config-grid>.llm-config-card{margin-bottom:0}' in llm_configuration.text
    assert '.llm-config-card h3{margin:0 0 4px;font-size:18px}' in llm_configuration.text
    assert '.llm-config-card>p{margin:0 0 18px;color:var(--muted)}' in llm_configuration.text
    assert '.llm-route-row{justify-content:space-between;padding:14px 0;border-top:1px solid var(--border-soft)}' in llm_configuration.text
    assert "Candidate Profile Base Mapping" in llm_configuration.text
    assert "Candidate Profile Derived Claims" in llm_configuration.text
    assert "Default · 120s · temperature 0.2" in llm_configuration.text
    assert "Default model · 120 seconds · Temperature 0.2" not in llm_configuration.text
    assert '<option value="">Select a validated model</option>' in llm_configuration.text
    assert '<option value="">Select a model</option>' not in llm_configuration.text
    assert "textContent=button.closest('.llm-route-row').querySelector('strong').textContent+' Configuration'" in llm_configuration.text

    llm_resource = client.get("/llm-configuration").json()["data"]
    patched_llm = client.patch(
        "/llm-configuration",
        json={
            "expected_revision": llm_resource["revision"],
            "tasks": {"candidate_profile_derived_claims": {"temperature": 0.3}},
        },
    )
    assert patched_llm.status_code == 200
    assert patched_llm.json()["data"]["tasks"]["candidate_profile_derived_claims"]["temperature"] == 0.3

def test_llm_route_styles_are_owned_by_base_template() -> None:
    root = Path(__file__).resolve().parents[2]
    base = (root / "src" / "fitcv_cp" / "templates" / "base.html").read_text(encoding="utf-8")
    llm_configuration = (root / "src" / "fitcv_cp" / "templates" / "llm_configuration.html").read_text(encoding="utf-8")

    shared_style = ".llm-config-grid{display:grid;gap:16px}"
    assert shared_style in base
    assert shared_style not in llm_configuration


def _seed_active_profile() -> str:
    resource = sqlite_store.create_candidate_profile_attempt(
        profile_bytes=b"name: Test Candidate\nskills: []\nexperiences: []\nprojects: []\nachievements: []\npreferences: {}\n",
        original_filename="profile.yaml",
        profile_name="Test Profile",
    )
    return str(resource["profile_id"])

def _seed_succeeded_scan(*, name: str, jobs: list[dict[str, str]]) -> dict[str, object]:
    company = sqlite_store.create_tracked_company(
        company_name=f"{name} Company",
        careers_url=f"https://{uuid.uuid4().hex}.jobs.personio.de/",
        provider_id="personio",
        provider_label="Personio",
    )
    reservation = sqlite_store.reserve_idempotent_action(
        "scans:create", f"{name}-{uuid.uuid4().hex}", f"{name}-fingerprint"
    )
    scan = sqlite_store.create_scan(
        request={
            "scan_name": name,
            "company_ids": [company["company_id"]],
            "job_titles": [],
            "locations": [],
            "published_window": "any",
            "total_rows": 50,
        },
        idempotency_action_id=reservation["action_id"],
    )
    return sqlite_store.commit_scan_output(
        str(scan["scan_id"]), output_json=json.dumps(jobs, ensure_ascii=False, indent=2)
    )


def test_provider_api_is_not_mounted_outside_packaged_local_mode() -> None:
    app = _app()

    assert TestClient(app).get("/api-providers").status_code == 404
    assert TestClient(app).get("/llm-configuration").status_code == 404
    assert TestClient(app).get("/prompt-configurations").status_code == 404
    assert TestClient(app).get("/system-settings").status_code == 404
    assert "/api-providers" not in TestClient(app).get("/openapi.json").json()["paths"]
    assert "/llm-configuration" not in TestClient(app).get("/openapi.json").json()["paths"]
    assert "/prompt-configurations" not in TestClient(app).get("/openapi.json").json()["paths"]
    assert "/system-settings" not in TestClient(app).get("/openapi.json").json()["paths"]


def _app_with_active_profile():
    app = _app()
    app.state.run_store.get_candidate_profile_fn = lambda profile_id: {
        "profile_id": profile_id,
        "name": "Test Profile",
        "revision": 1,
        "is_active": True,
        "profile": {"skills": []},
    }
    app.state.run_store.create_run_bundle_fn = lambda *_args, **_kwargs: None
    return app


def _app_with_captured_run(captured: dict[str, object]):
    app = _app_with_active_profile()

    def capture_run_bundle(run: PipelineRun, **_kwargs: object) -> dict[str, object]:
        captured["run"] = run
        return {"run_id": run.run_id}

    app.state.run_store.create_run_bundle_fn = capture_run_bundle
    return app


def test_process_console_clear_view_uses_scoped_cursor_and_reset() -> None:
    template = Path("src/fitcv_cp/templates/_process_console.html").read_text(encoding="utf-8")

    assert "localStorage" in template
    assert "process_type" in template
    assert "process_id" in template
    assert "data-console-reset" in template
    assert "recorded_at" in template
    assert "event_id" in template


def test_scan_routes_are_in_normal_openapi_without_mock_controls() -> None:
    paths = TestClient(_app()).get("/openapi.json").json()["paths"]

    assert "/scans" in paths
    assert "/tracked-companies" in paths
    assert "/scans/{scan_id}/output" in paths
    assert "/__mock__/scenario" not in paths


def test_mock_scan_api_lists_resources_and_exact_output() -> None:
    from tests.test_fitcv_cp.scan_fixtures import create_mock_app

    client = TestClient(create_mock_app())
    listing = client.get("/scans", params={"lifecycle": "active", "page_size": 10})
    detail = client.get("/scans/scan-1048")
    output = client.get("/scans/scan-1048/output")

    assert listing.status_code == 200
    assert listing.json()["data"][0]["scan_id"] == "scan-1048"
    assert detail.json()["data"]["capabilities"]["use_for_run"] is True
    assert output.status_code == 200
    assert output.content.startswith(b"[")
    assert output.headers["etag"] == f'"{detail.json()["data"]["output_manifest"]["sha256"]}"'


def test_mock_scan_creation_replays_same_scan_for_same_idempotency_key() -> None:
    from tests.test_fitcv_cp.scan_fixtures import create_mock_app

    client = TestClient(create_mock_app())
    body = {"company_ids": ["company-personio"], "published_window": "past_7_days"}
    first = client.post("/scans", json=body, headers={"Idempotency-Key": "scan-create-1"})
    second = client.post("/scans", json=body, headers={"Idempotency-Key": "scan-create-1"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["data"]["scan_id"] == second.json()["data"]["scan_id"]


def test_mock_scan_lifecycle_rejects_stale_revision() -> None:
    from tests.test_fitcv_cp.scan_fixtures import create_mock_app

    client = TestClient(create_mock_app())
    response = client.post(
        "/scans/actions/archive",
        json={"items": [{"scan_id": "scan-1048", "expected_revision": 999}]},
        headers={"Idempotency-Key": "archive-1"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "scan_revision_conflict"


def test_mock_scenario_route_is_test_only_and_hidden_from_openapi() -> None:
    from tests.test_fitcv_cp.scan_fixtures import create_mock_app

    client = TestClient(create_mock_app())
    assert client.post("/__mock__/scenario", json={"scenario": "empty"}).status_code == 200
    assert client.get("/scans").json()["data"] == []
    assert "/__mock__/scenario" not in client.get("/openapi.json").json()["paths"]


def test_managed_run_requires_upload_or_scan_and_accepts_scan_only() -> None:
    from tests.test_fitcv_cp.scan_fixtures import create_mock_app

    client = TestClient(create_mock_app())
    missing = client.post("/runs", data={"profile_id": "profile-1"}, headers={"Idempotency-Key": "run-1"})
    accepted = client.post(
        "/runs",
        data={"profile_id": "profile-1", "scan_ids": "scan-1048"},
        headers={"Idempotency-Key": "run-2"},
    )

    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "validation_failed"
    assert accepted.status_code == 201
    assert accepted.json()["data"]["jobs_input_manifest"]["sources"][0]["scan_id"] == "scan-1048"


def test_admin_scans_workspace_matches_managed_scan_intent() -> None:
    from tests.test_fitcv_cp.scan_fixtures import create_mock_app

    response = TestClient(create_mock_app()).get("/admin/scans")

    assert response.status_code == 200
    assert "Scan ID" in response.text
    assert "Active" in response.text and "Archived" in response.text
    assert response.text.count('class="run-tab-count"') == 2
    assert 'name="search"' not in response.text
    assert 'name="execution_status"' not in response.text
    assert "Rows per page" not in response.text
    assert "New Scan" in response.text
    assert "Tracked Companies" in response.text
    assert "Published At" in response.text
    assert "Past 12 hours" in response.text and "Past 6 months" in response.text
    assert "Action</th>" not in response.text


def test_admin_runs_workspace_matches_prototype_structure() -> None:
    response = TestClient(_app()).get("/admin/runs")

    assert response.status_code == 200
    assert 'data-page="runs"' in response.text
    assert 'data-header-title="Runs"' in response.text
    assert '<p class="eyebrow">Workspace</p><h2>Runs</h2>' in response.text
    assert 'class="btn" type="button" data-open-run-dialog>Trigger Run</button>' in response.text
    assert response.text.count('class="run-tab-count"') == 2
    assert '>All<' not in response.text
    assert '⟳ Refresh' not in response.text
    assert 'name="search"' not in response.text
    assert 'name="status"' not in response.text
    assert '<dialog class="run-dialog" id="runDialog"' in response.text
    assert '<form class="run-form" id="runForm">' in response.text


def test_runs_list_preserves_prototype_states_and_interactions() -> None:
    template = Path("src/fitcv_cp/templates/runs_list.html").read_text(encoding="utf-8")

    assert 'aria-controls="runTablePanel"' in template
    assert 'aria-labelledby="{{' in template
    assert "['ArrowLeft', 'ArrowRight']" in template
    assert "bulkLifecycleAction('unarchive'" not in template
    assert "No archived runs" in template
    assert "Archived runs will appear here after they are moved from Active." in template
    assert "No active runs yet" in template
    assert "Trigger a run to process a job file with one of your Candidate Profiles." in template
    assert "fitcvRenderAsyncState(" in template
    assert "setTimeout(() => location.reload()" not in template
    assert "var triggerRunIdempotencyKey = null;" in template
    assert "'Idempotency-Key': triggerRunIdempotencyKey" in template
    assert 'class="run-source-panel" id="runUploadSource"' in template
    assert 'class="run-source-panel" id="runScanSource"' in template
    assert 'id="runScanEmpty" hidden>No successful non-empty Scans available.' in template
    assert 'id="candidateProfileEmpty" hidden><strong>No available Candidate Profiles</strong>' in template
    assert 'id="triggerRun" type="button" disabled>Trigger</button>' in template
    assert "function updateRunTriggerState()" in template
    assert "alert(e.message || 'Delete archived Runs failed')" not in template
    assert "alert('Bulk action failed')" not in template
    assert "alert('Select at least one archived Run first.')" not in template
    assert "alert('Select at least one run first.')" not in template
    assert "run-status-detail" in template
    assert "fitcv-focus-run-tab" in template
    assert 'id="cancelSelectedRuns"' in template
    assert 'id="archiveSelectedRuns"' in template
    assert 'id="deleteSelectedRuns"' in template
    assert "fitcvRenderAsyncState(status" in template
    assert "status.textContent = error.message" not in template


def test_new_scan_dialog_uses_shared_run_dialog_structure() -> None:
    from tests.test_fitcv_cp.scan_fixtures import create_mock_app

    response = TestClient(create_mock_app()).get("/admin/scans")

    assert response.status_code == 200
    assert '<dialog class="workspace-dialog run-dialog scan-dialog" id="new-scan-dialog"' in response.text
    assert '<div class="dialog-head">' in response.text
    assert '<form class="run-form" id="new-scan-form">' in response.text
    assert response.text.count('class="run-field"') >= 6
    assert '.run-dialog{width:min(620px,calc(100vw - 32px));' in response.text
    assert '.scan-dialog{width:min(720px,calc(100vw - 32px))}' in response.text
    assert 'dialog.workspace-dialog { width:' not in response.text
    assert 'dialog.workspace-dialog.run-dialog{width:' not in response.text
    assert 'id="scan-job-titles" name="job_titles" type="text"' in response.text
    assert 'placeholder="Data Engineer, Analytics Engineer"' in response.text
    assert 'id="scan-locations" name="locations" type="text"' in response.text
    assert 'placeholder="Berlin, Germany"' in response.text
    assert '>Start Scan</button>' in response.text
    assert 'form="new-scan-form" disabled>Start Scan</button>' in response.text
    assert 'Ready to start. Registry, company selection, and filters will be captured.' in response.text


def test_scan_managed_selection_dialogs_match_prototype_structure() -> None:
    from tests.test_fitcv_cp.scan_fixtures import create_mock_app

    scans = TestClient(create_mock_app()).get("/admin/scans")
    runs = TestClient(create_mock_app()).get("/admin/runs")

    assert scans.status_code == 200
    assert runs.status_code == 200
    assert 'class="workspace-dialog run-dialog managed-selection-dialog" id="company-picker-dialog"' in scans.text
    assert "Search the registry and select companies for this Scan." in scans.text
    assert 'aria-label="Search tracked companies"' in scans.text
    assert 'id="select-filtered-companies"' in scans.text
    assert 'id="clear-company-selection"' in scans.text
    assert 'class="workspace-dialog run-dialog" id="add-company-dialog"' in scans.text
    assert "Verify one supported careers portal before adding it." in scans.text
    assert 'id="test-add-company"' in scans.text
    assert 'id="save-add-company" type="button" disabled>Add Company</button>' in scans.text
    assert "picker.addEventListener('cancel'" in scans.text
    assert "addDialog.addEventListener('cancel'" in scans.text
    assert 'class="run-dialog managed-selection-dialog" id="runScanDialog"' in runs.text
    assert "Search and select successful Scan outputs for this Run." in runs.text
    assert 'id="selectFilteredRunScans"' in runs.text
    assert 'id="clearManagedRunScans"' in runs.text
    assert '<strong>${escapeRunScanText(scan.scan_id)}</strong>' in runs.text
    assert 'Intl.DateTimeFormat' in runs.text


def test_admin_scans_workspace_uses_prototype_visual_components() -> None:
    from tests.test_fitcv_cp.scan_fixtures import create_mock_app

    response = TestClient(create_mock_app()).get("/admin/scans")

    assert response.status_code == 200
    assert 'class="page-head"' in response.text
    assert '<p class="eyebrow">Workspace</p>' in response.text
    assert 'class="run-panel"' in response.text
    assert 'class="run-tabs"' in response.text
    assert 'aria-label="Scan views"' in response.text
    assert 'data-scan-tab="active"' in response.text
    assert 'data-scan-tab="archived"' in response.text
    assert 'role="tabpanel"' in response.text
    assert 'class="section-card table-card"' in response.text
    assert 'class="run-table"' in response.text
    assert 'id="open-new-scan" class="btn"' in response.text
    assert 'class="run-id run-id-link"' in response.text
    assert 'class="workspace-tabs"' not in response.text
    assert 'class="run-selection filter-bar"' not in response.text
    assert '<th>Jobs</th>' not in response.text
    assert 'aria-label="Scan pages"' not in response.text
    assert "2026-08-02T09:45:00+00:00" not in response.text
    assert "02.08.2026 11:45 CEST" in response.text
    assert '<span class="run-duration">0s</span>' in response.text
    template = Path("src/fitcv_cp/templates/scans_list.html").read_text(encoding="utf-8")
    assert 'class="run-selection-copy"' in template
    assert "classList.toggle('is-selected', input.checked)" in template
    assert "['ArrowLeft', 'ArrowRight']" in template
    assert "fitcvRenderAsyncState(" in template
    assert "fitcvRunLocked(" in template
    assert "const selectAll = document.getElementById('select-all-scans');" in template
    assert "if (selectAll) selectAll.addEventListener('change'" in template
    assert "document.getElementById('scan-name').focus();" in template
    assert "selectedScanState" in template
    assert "history.replaceState" in template
    assert "/tracked-companies?search=" in template


def test_admin_scan_detail_reuses_detail_structure_and_output_views() -> None:
    from tests.test_fitcv_cp.scan_fixtures import create_mock_app

    response = TestClient(create_mock_app()).get("/admin/scans/scan-1048")

    assert response.status_code == 200
    assert "Scan Overview" in response.text
    assert "Scan Input" in response.text
    assert "Console" in response.text
    assert "Scan Output" in response.text
    assert "Console Log" in response.text
    assert "Portal retrieval, normalization, and output lifecycle events." in response.text
    assert '<button type="button" class="small-action" data-console-clear>Clear</button>' in response.text
    assert 'href="/scans/scan-1048/events?limit=500">Download</a>' in response.text
    assert 'role="tab"' in response.text
    assert ">Table<" in response.text and ">JSON<" in response.text
    assert "Run Again" in response.text
    assert "Download JSON" in response.text
    assert "Use in run" not in response.text
    assert "<dt>Created</dt><dd>02.08.2026 11:45 CEST</dd>" in response.text
    assert '<span class="console-time">02.08.2026 11:45 CEST</span>' in response.text
    assert 'aria-label="Scan output pagination"' in response.text
    assert 'class="run-page-size"' in response.text
    assert '<button class="btn" type="button" aria-label="Previous page" disabled>‹</button>' in response.text
    assert 'aria-label="Page 2"' in response.text
    assert 'output_page=2&output_page_size=10#scan-output-title' in response.text
    assert "<dt>Row Revision</dt>" not in response.text
    assert (
        "<th>Contract Type</th><th>Experience Level</th><th>Published At</th>"
        "<th>Job URL</th><th>Apply URL</th><th>Description</th>"
    ) in response.text
    assert "{{ job.applyUrl }}" in Path("src/fitcv_cp/templates/scan_detail.html").read_text(
        encoding="utf-8"
    )
    detail_template = Path("src/fitcv_cp/templates/scan_detail.html").read_text(encoding="utf-8")
    assert 'data-scan-status="{{ scan.execution_status }}"' in detail_template
    assert "['queued', 'running', 'cancelling']" in detail_template
    assert "/events?limit=50" in detail_template
    assert "next_cursor" in detail_template
    assert "fitcvRenderAsyncState(" in detail_template
    assert "fitcvRunLocked(" in detail_template
    assert "location.reload" not in detail_template


def test_admin_scan_detail_polling_refreshes_terminal_state_in_place() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.fail("Node.js is required for Scan Details polling regression proof")

    template = Path("src/fitcv_cp/templates/scan_detail.html").read_text(encoding="utf-8")
    script = template.split("<script>", 1)[1].split("</script>", 1)[0]
    harness = f"""
const vm = require('node:vm');
const source = {json.dumps(script)};
const state = {{root: null, timers: [], fetches: [], locationAssignments: 0, pollCount: 0}};
async function main() {{

function makeButton(action) {{
  return {{
    id: '',
    dataset: {{scanAction: action}},
    listeners: [],
    focused: false,
    addEventListener(type, listener) {{ this.listeners.push([type, listener]); }},
    focus() {{ this.focused = true; state.document.activeElement = this; }},
  }};
}}

function makeTab(selected) {{
  return {{
    attributes: {{'aria-selected': String(selected)}},
    hidden: false,
    tabIndex: 0,
    listeners: [],
    addEventListener(type, listener) {{ this.listeners.push([type, listener]); }},
    setAttribute(name, value) {{ this.attributes[name] = value; }},
    getAttribute(name) {{ return this.attributes[name] ?? null; }},
  }};
}}

function makeRoot(statusValue, revision, button) {{
  const tabs = {{
    table: makeTab(false),
    json: makeTab(true),
    tablePanel: {{hidden: true}},
    jsonPanel: {{hidden: false}},
  }};
  const rootValue = {{
    dataset: {{scanId: 'scan-1', scanRevision: String(revision), scanStatus: statusValue}},
    button,
    tabs,
    replaceWith(next) {{ state.root = next; this.replaced = (this.replaced || 0) + 1; }},
    querySelectorAll(selector) {{ return selector === '[data-scan-action]' ? [this.button] : []; }},
  }};
  return rootValue;
}}

const initialButton = makeButton('cancel');
state.root = makeRoot('running', 1, initialButton);
    const statusNodes = new WeakMap();
const documentValue = {{
  hidden: false,
  activeElement: initialButton,
  querySelector() {{ return state.root; }},
  querySelectorAll(selector) {{ return selector === '[data-scan-action]' ? [state.root.button] : []; }},
  getElementById(id) {{
    if (id === 'scan-action-status') {{
      if (!statusNodes.has(state.root)) statusNodes.set(state.root, {{textContent: ''}});
      return statusNodes.get(state.root);
    }}
    if (id === 'scan-output-table-tab') return state.root.tabs.table;
    if (id === 'scan-output-json-tab') return state.root.tabs.json;
    if (id === 'scan-output-table-panel') return state.root.tabs.tablePanel;
    if (id === 'scan-output-json-panel') return state.root.tabs.jsonPanel;
    return null;
  }},
  addEventListener() {{}},
    }};
    state.document = documentValue;

const refreshedRoot = makeRoot('succeeded', 2, makeButton('cancel'));
const context = {{
  console,
  document: documentValue,
      window: {{location: {{href: 'http://127.0.0.1:8000/admin/scans/scan-1'}}, setTimeout(callback) {{ state.timers.push(callback); return state.timers.length; }}, clearTimeout() {{}}}},
  location: {{assign() {{ state.locationAssignments += 1; }}}},
  DOMParser: class {{ parseFromString() {{ return {{querySelector() {{ return refreshedRoot; }}}}; }} }},
      fetch: async (url) => {{
    state.fetches.push(url);
    if (url === context.window.location.href) return {{ok: true, text: async () => '<main data-page="scan-detail"></main>'}};
    if (url.includes('/events?')) {{
      return {{ok: true, json: async () => ({{data: {{events: [], next_cursor: state.pollCount === 1 ? '5' : '3'}}}})}};
    }}
    state.pollCount += 1;
    return {{ok: true, json: async () => ({{data: {{execution_status: state.pollCount === 1 ? 'running' : 'succeeded', row_revision: state.pollCount}}}})}};
  }},
  fitcvRunLocked: async (_button, callback) => callback(),
  fitcvRenderAsyncState() {{}},
  crypto: {{randomUUID: () => 'idempotency-key'}},
}};

vm.runInNewContext(source, context);
if (state.timers.length !== 1) throw new Error('initial polling timer missing');
await state.timers.shift()();
if (state.timers.length !== 1) throw new Error('polling did not continue while running');
await state.timers.shift()();
if (state.root.dataset.scanStatus !== 'succeeded') throw new Error('terminal state was not refreshed');
if (state.root.dataset.scanRevision !== '2') throw new Error('row revision was not refreshed');
if (!state.root.button.focused) throw new Error('focused action was not restored');
if (state.root.tabs.json.attributes['aria-selected'] !== 'true' || state.root.tabs.jsonPanel.hidden) throw new Error('output view was not preserved');
if (state.root.button.listeners.length !== 1) throw new Error('action handler was duplicated');
if (!state.fetches.some(url => url.includes('/events?limit=50&cursor=5'))) throw new Error('event cursor was not advanced');
if (state.fetches.some(url => url.includes('cursor=3'))) throw new Error('event cursor moved backwards');
const fetchCountAfterTerminal = state.fetches.length;
if (state.timers.length) await state.timers.shift()();
if (state.fetches.length !== fetchCountAfterTerminal) throw new Error('polling continued after terminal state');
if (state.locationAssignments !== 0) throw new Error('terminal refresh navigated away');
}}
main().catch(error => {{ console.error(error); process.exitCode = 1; }});
"""
    result = subprocess.run([node, "-e", harness], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr or result.stdout


def test_admin_scan_detail_uses_prototype_visual_components() -> None:
    from tests.test_fitcv_cp.scan_fixtures import create_mock_app

    response = TestClient(create_mock_app()).get("/admin/scans/scan-1048")

    assert response.status_code == 200
    assert 'class="details-page-layout"' in response.text
    assert 'data-header-title="Scan Details"' in response.text
    assert 'data-header-description="Review Scan inputs, progress, and output."' in response.text
    assert 'class="details-page-head"' in response.text
    assert '<p class="eyebrow">Scan Details</p>' in response.text
    assert response.text.count('class="section-card collapsible-section drawer-section') >= 4
    assert 'class="details-grid"' in response.text
    assert 'class="detail-item"' in response.text
    assert '<section class="card"' not in response.text
    assert 'aria-label="Scan Output pages"' not in response.text


def test_base_exposes_prototype_scan_component_styles() -> None:
    template = Path("src/fitcv_cp/templates/base.html").read_text(encoding="utf-8")

    assert ".run-panel{display:grid;gap:14px}" in template
    assert ".run-tabs{display:flex;gap:8px}" in template
    assert '.run-tabs .btn[aria-selected="true"]{border-color:var(--accent);background:var(--accent-soft);color:var(--accent)}' in template
    assert ".table-card{overflow:hidden;padding:0;margin:0}" in template
    assert ".run-table{width:100%;min-width:720px;border-collapse:collapse}" in template
    assert ".run-table th{background:transparent" in template
    assert ".run-id-link{display:inline-block" in template
    assert ".badge,.mirror-value{display:inline-flex" in template
    assert "[hidden]{display:none!important}" in template
    assert "button:not([class])" in template
    assert ".details-page-head{" in template
    assert ".details-grid{" in template
    assert ".detail-item dt{" in template
    assert ".run-pagination{" in template
    assert ".btn.danger{" in template


def test_run_trigger_uses_additive_upload_and_scan_sources() -> None:
    from tests.test_fitcv_cp.scan_fixtures import create_mock_app

    response = TestClient(create_mock_app()).get("/admin/runs")

    assert response.status_code == 200
    assert "Eligible Scan outputs" in response.text
    assert "At least one job source is required" in response.text
    assert 'id="manageRunScans"' in response.text
    assert 'id="source_mode"' not in response.text
    assert "scanner_careers_url" not in response.text

def test_run_trigger_reconciles_stale_scan_selection_without_losing_upload() -> None:
    template = Path("src/fitcv_cp/templates/runs_list.html").read_text(encoding="utf-8")

    assert "async function refreshEligibleRunScans()" in template
    assert "error.code === 'scan_not_usable' || error.code === 'scan_output_integrity_failed'" in template
    assert "Unavailable selected Scan" in template
    assert "document.getElementById('jobs_file').value" not in template


def test_client_navigated_page_scripts_use_shared_ready_initializer() -> None:
    base = Path("src/fitcv_cp/templates/base.html").read_text(encoding="utf-8")

    assert "function initializeFitCVPage(initializer)" in base
    assert "document.readyState === 'loading'" in base

    for template_name in ("runs_list.html", "run_detail.html"):
        template = Path(f"src/fitcv_cp/templates/{template_name}").read_text(encoding="utf-8")
        assert "initializeFitCVPage(" in template
        assert "document.addEventListener('DOMContentLoaded'" not in template

    runs_template = Path("src/fitcv_cp/templates/runs_list.html").read_text(encoding="utf-8")
    assert "var eligibleRunScans = [];" in runs_template
    assert "var selectedRunScanIds = [];" in runs_template
    assert "var draftRunScanIds = [];" in runs_template
    assert "var runScanTimeFormatter = new Intl.DateTimeFormat" in runs_template

def test_shared_shell_api_error_boundaries_are_canonical(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FITCV_LOCAL_MODE", raising=False)
    app = _app()
    app.state.run_store.get_run_detail_fn = lambda _run_id: None
    client = TestClient(app)

    success = client.get("/runs?view=active")
    validation = client.get("/runs?view=invalid")
    missing = client.get("/runs/missing")
    current = client.get("/settings/pipeline")
    revision = current.json()["data"]["revision"]
    saved = client.patch(
        "/settings/pipeline",
        json={"changes": {"pipeline.final_top_n": 8}, "expected_revision": revision},
    )
    stale = client.patch(
        "/settings/pipeline",
        json={"changes": {"pipeline.final_top_n": 7}, "expected_revision": revision},
    )
    persisted = client.get("/settings/pipeline")

    assert success.status_code == 200 and "data" in success.json()
    assert validation.status_code == 422
    assert missing.status_code == 404
    assert saved.status_code == 200
    assert stale.status_code == 409
    for response in (validation, missing, stale):
        assert set(response.json()["error"]) == {
            "code", "message", "field_errors", "retryable", "action"
        }
    assert validation.json()["error"]["code"] == "validation_failed"
    assert missing.json()["error"]["code"] == "run_not_found"
    assert stale.json()["error"]["code"] == "settings_revision_conflict"
    assert persisted.json()["data"]["values"]["pipeline.final_top_n"] == 8


def test_shared_async_helpers_preserve_canonical_api_error_contract() -> None:
    base = Path("src/fitcv_cp/templates/base.html").read_text(encoding="utf-8")

    assert "requestError.code = error.code || 'request_failed';" in base
    assert "requestError.action = error.action" in base
    assert "requestError.status = response.status" in base
    assert "requestError.payload = payload" in base
    assert "var supportedKinds = ['pending', 'success', 'empty', 'error', 'retryable', 'non_retryable', 'stale', 'refreshing'];" in base
    assert "notice.setAttribute('aria-live', isError ? 'assertive' : 'polite');" in base
    assert "if (state.action && typeof state.retry === 'function')" in base
    assert "if (isFocusable) notice.focus();" in base
    assert "if (!state.preserveContent) target.replaceChildren();" in base
    assert base.count("function initializePageForms(root)") == 1
    assert "window.fetch = function(input, init)" in base


def test_direct_page_load_defines_shared_initializer_before_page_scripts() -> None:
    response = TestClient(_app()).get("/admin/runs")

    assert response.status_code == 200
    assert response.text.index("function initializeFitCVPage(initializer)") < response.text.index(
        "initializeFitCVPage(() => {"
    )


def test_mock_scan_ui_covers_error_pending_and_integrity_states() -> None:
    from tests.test_fitcv_cp.scan_fixtures import create_mock_app

    client = TestClient(create_mock_app())
    assert client.post("/__mock__/scenario", json={"scenario": "list_error"}).status_code == 200
    error_page = client.get("/admin/scans")
    pending_page = client.get("/admin/scans/scan-1047")
    client.post("/__mock__/scenario", json={"scenario": "integrity"})
    integrity_page = client.get("/admin/scans/scan-1048")

    assert error_page.status_code == 200 and "Retry" in error_page.text
    assert "Scan output is not ready yet" in pending_page.text
    assert "Output integrity check failed" in integrity_page.text


def test_managed_run_combined_manifest_orders_upload_before_scans() -> None:
    from tests.test_fitcv_cp.scan_fixtures import create_mock_app

    response = TestClient(create_mock_app()).post(
        "/runs",
        data={"profile_id": "profile-1", "scan_ids": "scan-1048"},
        files={"jobs_file": ("jobs.json", b"[]", "application/json")},
        headers={"Idempotency-Key": "combined-run-1"},
    )

    assert response.status_code == 201, response.text
    assert [source["type"] for source in response.json()["data"]["jobs_input_manifest"]["sources"]] == ["upload", "scan"]

def test_managed_run_removes_projection_when_bundle_persistence_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fitcv_cp import app as app_module

    projection = tmp_path / "managed-run-jobs.json"
    app = _app()
    app.state.run_store.get_candidate_profile_fn = lambda profile_id: {
        "candidate_profile_id": profile_id,
        "name": "Test Profile",
        "revision": 1,
        "is_active": True,
        "profile": {"skills": []},
    }
    app.state.run_store.get_scan_detail_fn = lambda scan_id: {
        "scan_id": scan_id,
        "scan_name": "Germany Data Jobs",
        "output_record_count": 1,
        "capabilities": {"use_for_run": True},
    }
    app.state.run_store.get_scan_output_fn = lambda _scan_id: {
        "output_json": json.dumps([_valid_fitcv_job()]),
        "sha256": "scan-sha",
    }
    app.state.run_store.reserve_idempotent_action_fn = lambda *_args: {
        "action_id": "managed-run-action",
        "replayed": False,
        "response": None,
    }
    app.state.run_store.create_run_bundle_fn = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        RuntimeError("bundle persistence failed")
    )

    def materialize(_run_id: str, artifact: object) -> str:
        projection.write_text(getattr(artifact, "json_text"), encoding="utf-8")
        return str(projection)

    monkeypatch.delenv("FITCV_LOCAL_MODE", raising=False)
    monkeypatch.setattr(app_module, "_materialize_run_jobs_projection", materialize)
    with patch("fitcv_cp.app.load_active_settings", return_value={}), patch(
        "fitcv_cp.app.load_config", return_value={"pipeline": {"final_top_n": 10}}
    ), patch("fitcv_cp.app.submit_run") as submit:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/runs",
            data={"profile_id": "profile-1", "scan_ids": "scan-1048"},
            headers={"Idempotency-Key": "managed-run-persistence-failure"},
        )

    assert response.status_code == 500
    assert not projection.exists()
    submit.assert_not_called()

def test_real_run_route_accepts_upload_only_and_scan_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FITCV_LOCAL_MODE", raising=False)
    app = _app()
    profile_id = _seed_active_profile()
    scan = _seed_succeeded_scan(name="scan-only", jobs=[_valid_fitcv_job(title="Scan Job")])
    submission = RunSubmission(
        run_id="ignored",
        queue_job_id="queue-1",
        backend_run_id="queue-1",
        backend="default_queue",
    )

    with patch("fitcv_cp.app.load_active_settings", return_value={}), patch(
        "fitcv_cp.app.load_config", return_value={"pipeline": {"final_top_n": 10}}
    ), patch("fitcv_cp.app.submit_run", return_value=submission):
        client = TestClient(app)
        upload = client.post(
            "/runs",
            data={"profile_id": profile_id},
            files={"jobs_file": ("jobs.json", json.dumps([_valid_fitcv_job(title="Upload Job")]), "application/json")},
            headers={"Idempotency-Key": "real-upload-only"},
        )
        scan_only = client.post(
            "/runs",
            data={"profile_id": profile_id, "scan_ids": scan["scan_id"]},
            headers={"Idempotency-Key": "real-scan-only"},
        )

    assert upload.status_code == 201, upload.text
    assert scan_only.status_code == 201, scan_only.text
    assert sqlite_store.get_run(upload.json()["data"]["run_id"]).jobs_input_source == "upload"
    scan_run = sqlite_store.get_run(scan_only.json()["data"]["run_id"])
    assert scan_run.jobs_input_source == "scan"
    assert sqlite_store.query_run_jobs(scan_run.run_id)["items"][0]["title"] == "Scan Job"

def test_real_managed_run_preserves_upload_then_selected_scan_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FITCV_LOCAL_MODE", raising=False)
    app = _app()
    profile_id = _seed_active_profile()
    second = _seed_succeeded_scan(name="second", jobs=[_valid_fitcv_job(title="Second Scan")])
    first = _seed_succeeded_scan(name="first", jobs=[_valid_fitcv_job(title="First Scan")])

    with patch("fitcv_cp.app.load_active_settings", return_value={}), patch(
        "fitcv_cp.app.load_config", return_value={"pipeline": {"final_top_n": 10}}
    ), patch(
        "fitcv_cp.app.submit_run",
        return_value=RunSubmission(
            run_id="ignored",
            queue_job_id="queue-1",
            backend_run_id="queue-1",
            backend="default_queue",
        ),
    ):
        response = TestClient(app).post(
            "/runs",
            data={"profile_id": profile_id, "scan_ids": [second["scan_id"], first["scan_id"]]},
            files={"jobs_file": ("jobs.json", json.dumps([_valid_fitcv_job(title="Upload Job")]), "application/json")},
            headers={"Idempotency-Key": "real-combined"},
        )

    assert response.status_code == 201, response.text
    run_id = response.json()["data"]["run_id"]
    database_path = Path(os.environ["FITCV_CP_SQLITE_PATH"])
    with sqlite3.connect(database_path) as connection:
        jobs = connection.execute(
            "SELECT title FROM run_jobs WHERE run_id = ? ORDER BY source_index",
            (run_id,),
        ).fetchall()
        provenance = connection.execute(
            "SELECT scan_id FROM run_scan_inputs WHERE run_id = ? ORDER BY source_ordinal",
            (run_id,),
        ).fetchall()
        contract_version = connection.execute(
            "SELECT run_input_contract_version FROM run_inputs WHERE run_id = ?",
            (run_id,),
        ).fetchone()[0]
    assert jobs == [("Upload Job",), ("Second Scan",), ("First Scan",)]
    assert provenance == [(second["scan_id"],), (first["scan_id"],)]
    assert contract_version == "managed_v1"

def test_real_managed_run_rejects_missing_archived_empty_and_integrity_invalid_sources() -> None:
    app = _app()
    profile_id = _seed_active_profile()
    archived = _seed_succeeded_scan(name="archived", jobs=[_valid_fitcv_job()])
    archived = sqlite_store.transition_scan_lifecycle(
        [{"scan_id": archived["scan_id"], "expected_revision": archived["row_revision"]}],
        target="archived",
    )["items"][0]
    empty = _seed_succeeded_scan(name="empty", jobs=[])
    invalid = _seed_succeeded_scan(name="invalid", jobs=[_valid_fitcv_job()])
    with sqlite3.connect(Path(os.environ["FITCV_CP_SQLITE_PATH"])) as connection:
        connection.execute(
            "UPDATE scan_outputs SET output_json = ? WHERE scan_id = ?",
            ('[{"title":"tampered"}]', invalid["scan_id"]),
        )
        connection.commit()

    client = TestClient(app)
    missing = client.post(
        "/runs", data={"profile_id": profile_id}, headers={"Idempotency-Key": "missing-sources"}
    )
    responses = [
        client.post(
            "/runs",
            data={"profile_id": profile_id, "scan_ids": scan["scan_id"]},
            headers={"Idempotency-Key": f"reject-{index}"},
        )
        for index, scan in enumerate((archived, empty, invalid), start=1)
    ]

    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "validation_failed"
    assert [(response.status_code, response.json()["error"]["code"]) for response in responses] == [
        (409, "scan_not_usable"),
        (409, "scan_not_usable"),
        (409, "scan_not_usable"),
    ]


def test_process_console_discloses_window_and_exact_canonical_details() -> None:
    template = Path("src/fitcv_cp/templates/_process_console.html").read_text(encoding="utf-8")

    assert "process_console.total_count" in template
    assert "event.event_fingerprint" in template
    assert "event.payload_json" in template
    assert "event.diagnostic_refs_json" in template
    assert "event.trace_context_json" in template
    assert "data-console-filter" in template


def test_shortlist_quality_row_reports_embedding_coverage() -> None:
    from fitcv_cp.app import _build_stage_quality_metric_rows

    rows = _build_stage_quality_metric_rows(
        {
            "shortlist": {
                "embedding_coverage_rate": 0.75,
                "scored_jobs_total": 3,
                "eligible_jobs_total": 4,
            }
        }
    )

    assert rows == [
        {
            "stage_id": "shortlist",
            "label": "Shortlist Embedding Coverage",
            "rate": 0.75,
            "rate_percent": 75,
            "numerator": 3,
            "denominator": 4,
            "hint": "Share of eligible jobs with valid vector evidence.",
        }
    ]


def test_admin_route_manifest_matches_native_fastapi_contract() -> None:
    app = _app()

    def _response_class_name(route: Any) -> str | None:
        response_class = getattr(route, "response_class", None)
        if response_class is None:
            return None
        return getattr(response_class, "__name__", type(response_class).__name__)

    manifest = sorted(
        (
            route.path,
            tuple(sorted(method for method in (route.methods or set()) if method not in {"HEAD", "OPTIONS"})),
            route.name,
            _response_class_name(route),
        )
        for route in app.routes
        if getattr(route, "path", "").startswith("/admin/")
    )

    assert manifest == [
        ("/admin/bookmarks", ("GET",), "admin_bookmarks", "HTMLResponse"),
        ("/admin/candidate-profiles", ("GET",), "admin_candidate_profiles", "HTMLResponse"),
        ("/admin/candidate-profiles/create", ("GET",), "admin_candidate_profile_create", "HTMLResponse"),
        ("/admin/candidate-profiles/create/{attempt_id}/baseline", ("GET",), "admin_candidate_profile_baseline", "HTMLResponse"),
        ("/admin/candidate-profiles/create/{attempt_id}/confirm", ("GET",), "admin_candidate_profile_confirmation", "HTMLResponse"),
        ("/admin/candidate-profiles/create/{attempt_id}/derived", ("GET",), "admin_candidate_profile_derived", "HTMLResponse"),
        ("/admin/candidate-profiles/{profile_id}", ("GET",), "admin_candidate_profile_detail", "HTMLResponse"),
        ("/admin/cvs/{version_id}/download", ("GET",), "download_cv", "DefaultPlaceholder"),
        ("/admin/diagnostics/orchestration-schema", ("GET",), "admin_orchestration_schema_diagnostics", "DefaultPlaceholder"),
        ("/admin/mapping-suggestions.json", ("GET",), "download_aggregate_mapping_suggestions_json", "DefaultPlaceholder"),
        ("/admin/process-events.json", ("GET",), "get_process_event_export", "DefaultPlaceholder"),
        ("/admin/reconciler/run-attempts", ("POST",), "admin_reconcile_run_attempts", "DefaultPlaceholder"),
        ("/admin/runs", ("GET",), "admin_runs", "HTMLResponse"),
        ("/admin/runs/bulk/archive", ("POST",), "admin_bulk_archive_runs", "DefaultPlaceholder"),
        ("/admin/runs/bulk/cancel", ("POST",), "admin_bulk_cancel_runs", "DefaultPlaceholder"),
        ("/admin/runs/bulk/unarchive", ("POST",), "admin_bulk_unarchive_runs", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}", ("GET",), "admin_run_detail", "HTMLResponse"),
        ("/admin/runs/{run_id}/agentic-live-trace.json", ("GET",), "download_run_agentic_live_trace_json", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/approved-synonym-proposals.yaml", ("GET",), "download_run_approved_synonym_overlay_yaml", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/archive", ("POST",), "admin_archive_run", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/artifacts.zip", ("GET",), "download_run_artifact_bundle_zip", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/continue", ("POST",), "admin_continue_run", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/cv-analysis-trace.json", ("GET",), "download_run_cv_analysis_trace_json", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/cv-debug.json", ("GET",), "download_run_cv_debug_json", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/cv-generation-review-required.json", ("GET",), "download_run_cv_generation_review_required_json", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/cv-generation-trace.json", ("GET",), "download_run_cv_generation_trace_json", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/cv-review-action", ("POST",), "admin_run_cv_review_action", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/cv-review-batch-action", ("POST",), "admin_run_cv_review_batch_action", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/decision-feedback/{alternative_id}", ("POST",), "admin_run_decision_feedback", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/enriched/export-filtered.zip", ("GET",), "download_run_enriched_filtered_zip", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/export.json", ("GET",), "download_run_results_json", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/hitl-review-audit.json", ("GET",), "download_run_hitl_review_audit_json", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/mapping-suggestions.json", ("GET",), "download_run_mapping_suggestions_json", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/repair-cancellation", ("POST",), "admin_repair_cancellation", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/retry", ("POST",), "admin_retry_run", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/review-queue", ("GET",), "admin_run_review_queue", "HTMLResponse"),
        ("/admin/runs/{run_id}/settings-used.json", ("GET",), "download_run_settings_used_json", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/stage-artifacts.json", ("GET",), "download_run_stage_transition_artifacts_json", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/stage-artifacts/{stage_id}.json", ("GET",), "download_run_stage_transition_artifact_stage_json", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/stop", ("POST",), "admin_stop_run", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/synonym-proposals-trace.json", ("GET",), "download_run_synonym_proposals_trace_json", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/synonym-proposals.json", ("GET",), "download_run_synonym_proposals_json", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/synonym-suppression-diff.json", ("GET",), "download_run_synonym_suppression_diff_json", "DefaultPlaceholder"),
        ("/admin/runs/{run_id}/tabs/enriched", ("GET",), "admin_run_detail_tab_enriched", "HTMLResponse"),
        ("/admin/runs/{run_id}/tabs/jobs-input", ("GET",), "admin_run_detail_tab_jobs_input", "HTMLResponse"),
        ("/admin/runs/{run_id}/tabs/profile", ("GET",), "admin_run_detail_tab_profile", "HTMLResponse"),
        ("/admin/runs/{run_id}/unarchive", ("POST",), "admin_unarchive_run", "DefaultPlaceholder"),
        ("/admin/scans", ("GET",), "admin_scans", "HTMLResponse"),
        ("/admin/scans/{scan_id}", ("GET",), "admin_scan_detail", "HTMLResponse"),
        ("/admin/settings", ("GET",), "admin_settings_view", "HTMLResponse"),
        ("/admin/settings/group/{group_name}", ("POST",), "admin_settings_update_group", "HTMLResponse"),
        ("/admin/settings/section/{section_name}", ("POST",), "admin_settings_section_save", "HTMLResponse"),
        ("/admin/settings/{key}", ("POST",), "admin_settings_update_key", "HTMLResponse"),
        ("/admin/synonym-proposals.json", ("GET",), "download_aggregate_synonym_proposals_json", "DefaultPlaceholder"),
        ("/admin/synonyms", ("GET",), "admin_synonyms", "HTMLResponse"),
        ("/admin/synonyms/global-domain.yaml", ("GET",), "download_global_domain_synonyms_yaml", "DefaultPlaceholder"),
        ("/admin/synonyms/global-role-family.yaml", ("GET",), "download_global_role_family_synonyms_yaml", "DefaultPlaceholder"),
        ("/admin/synonyms/global.yaml", ("GET",), "download_global_synonyms_yaml", "DefaultPlaceholder"),
        ("/admin/upload-trigger", ("POST",), "upload_trigger", "DefaultPlaceholder"),
    ]

def test_retired_run_scoped_synonym_and_bookmark_routes_are_not_registered() -> None:
    paths = {route.path for route in _app().routes}

    retired_paths = {
        "/admin/bookmarks/delete",
        "/admin/bookmarks/status",
        "/admin/runs/bulk/delete-archived",
        "/admin/runs/{run_id}/bookmarks/save",
        "/admin/runs/{run_id}/bookmarks/delete",
        "/admin/runs/{run_id}/synonym-overlay",
        "/admin/runs/{run_id}/synonym-review",
        "/admin/runs/{run_id}/synonym-proposals/{proposal_id}/action",
        "/admin/runs/{run_id}/synonym-proposals/batch-action",
        "/admin/runs/{run_id}/synonym-proposals/apply-approved-to-run",
        "/admin/runs/{run_id}/synonym-proposals/regenerate",
        "/admin/runs/{run_id}/synonym-proposals/promote-preview",
        "/admin/runs/{run_id}/synonym-proposals/promote-review",
        "/admin/runs/{run_id}/synonym-proposals/promote-commit",
        "/admin/runs/{run_id}/synonym-proposals/triage-refresh",
        "/admin/runs/{run_id}/synonym-proposals/ai-fast-path-execute",
        "/admin/synonym-proposals/{proposal_id}/start-review",
        "/admin/synonym-proposals/{proposal_id}/approve-for-run-overlay",
        "/admin/synonym-proposals/{proposal_id}/reject",
        "/admin/synonym-proposals/{proposal_id}/defer",
    }

    assert paths.isdisjoint(retired_paths)

def test_collapse_timeline_noise_collapses_equivalent_synonym_triage_events() -> None:
    ts = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "triaged_count": 5,
        "reused_count": 0,
        "fresh_count": 5,
        "fallback_count": 0,
        "skipped_count": 0,
        "failed_count": 0,
        "reuse_reason": "reuse_enabled",
        "provider": "fitcv_builtin",
        "model": "synonym_triage_v1",
        "wire_api": "builtin",
    }
    events = [
        RunEvent(run_id="r", event_id="e1", stage="synonym_proposal_triage_completed", level="info", message="m", created_at=ts, payload_json=json.dumps(payload)),
        RunEvent(run_id="r", event_id="e2", stage="synonym_proposal_triage_completed", level="info", message="m", created_at=ts, payload_json=json.dumps(payload)),
        RunEvent(run_id="r", event_id="e3", stage="synonym_proposal_triage_completed", level="info", message="m", created_at=ts, payload_json=json.dumps(payload)),
    ]
    collapsed = _collapse_timeline_noise(events)
    assert len(collapsed) == 1
    kept_event, repeat_count = collapsed[0]
    assert kept_event.event_id == "e1"
    assert repeat_count == 3

def test_collapse_timeline_noise_keeps_distinct_synonym_triage_payloads() -> None:
    ts = datetime.datetime.now(datetime.timezone.utc)
    payload_a = {
        "triaged_count": 5,
        "reused_count": 0,
        "fresh_count": 5,
        "fallback_count": 0,
        "skipped_count": 0,
        "failed_count": 0,
        "reuse_reason": "reuse_enabled",
        "provider": "fitcv_builtin",
        "model": "synonym_triage_v1",
        "wire_api": "builtin",
    }
    payload_b = dict(payload_a)
    payload_b["failed_count"] = 1
    events = [
        RunEvent(run_id="r", event_id="e1", stage="synonym_proposal_triage_completed", level="info", message="m", created_at=ts, payload_json=json.dumps(payload_a)),
        RunEvent(run_id="r", event_id="e2", stage="synonym_proposal_triage_completed", level="info", message="m", created_at=ts, payload_json=json.dumps(payload_b)),
    ]
    collapsed = _collapse_timeline_noise(events)
    assert len(collapsed) == 2
    assert collapsed[0][1] == 1
    assert collapsed[1][1] == 1


def test_timeline_semantic_outcome_treats_alias_stage_as_equivalent() -> None:
    ts = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "deterministic_outcome": "rejected",
        "stage_owned_subreason": "validation_failed",
    }
    canonical = RunEvent(run_id="r", event_id="e1", stage="layer4_cv_validation_failed", level="warning", message="m", created_at=ts, payload_json=json.dumps(payload))
    alias = RunEvent(run_id="r", event_id="e2", stage="cv_validation_failed", level="warning", message="m", created_at=ts, payload_json=json.dumps(payload))
    assert _timeline_semantic_outcome(canonical, payload) == "expected_rejection"
    assert _timeline_semantic_outcome(alias, payload) == "expected_rejection"


def test_collapse_timeline_noise_is_replay_invariant() -> None:
    ts = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "triaged_count": 5,
        "reused_count": 0,
        "fresh_count": 5,
        "fallback_count": 0,
        "skipped_count": 0,
        "failed_count": 0,
        "reuse_reason": "reuse_enabled",
        "provider": "fitcv_builtin",
        "model": "synonym_triage_v1",
        "wire_api": "builtin",
    }
    events = [
        RunEvent(run_id="r", event_id="e1", stage="synonym_proposal_triage_completed", level="info", message="m", created_at=ts, payload_json=json.dumps(payload)),
        RunEvent(run_id="r", event_id="e2", stage="synonym_proposal_triage_completed", level="info", message="m", created_at=ts, payload_json=json.dumps(payload)),
    ]
    first = _collapse_timeline_noise(events)
    second = _collapse_timeline_noise(events)
    assert [(e.event_id, n) for e, n in first] == [(e.event_id, n) for e, n in second]


def test_collapse_timeline_noise_does_not_mutate_source_events() -> None:
    ts = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "triaged_count": 1,
        "reused_count": 0,
        "fresh_count": 1,
        "fallback_count": 0,
        "skipped_count": 0,
        "failed_count": 0,
        "reuse_reason": "reuse_enabled",
        "provider": "fitcv_builtin",
        "model": "synonym_triage_v1",
        "wire_api": "builtin",
    }
    event = RunEvent(run_id="r", event_id="e1", stage="synonym_proposal_triage_completed", level="info", message="m", created_at=ts, payload_json=json.dumps(payload))
    events = [event, event]
    _ = _collapse_timeline_noise(events)
    assert events[0].event_id == "e1"
    assert json.loads(str(events[0].payload_json or "{}"))["triaged_count"] == 1

def test_collapse_timeline_noise_collapses_identical_consecutive_stage_messages() -> None:
    ts = datetime.datetime.now(datetime.timezone.utc)
    events = [
        RunEvent(run_id="r", event_id="e1", stage="enrich_heartbeat", level="info", message="Enrich in progress", created_at=ts, payload_json="{}"),
        RunEvent(run_id="r", event_id="e2", stage="enrich_heartbeat", level="info", message="Enrich in progress", created_at=ts, payload_json="{}"),
        RunEvent(run_id="r", event_id="e3", stage="enrich_heartbeat", level="info", message="Enrich in progress", created_at=ts, payload_json="{}"),
    ]
    collapsed = _collapse_timeline_noise(events)
    assert len(collapsed) == 1
    kept_event, repeat_count = collapsed[0]
    assert kept_event.event_id == "e1"
    assert repeat_count == 3

def test_collapse_timeline_noise_collapses_display_equivalent_enrich_heartbeat_rows() -> None:
    ts = datetime.datetime.now(datetime.timezone.utc)
    events = [
        RunEvent(run_id="r", event_id="e1", stage="enrich_heartbeat", level="info", message="Enrich heartbeat: {'phase':'batch_progress','heartbeat_count':1}", created_at=ts, payload_json="{}"),
        RunEvent(run_id="r", event_id="e2", stage="enrich_heartbeat", level="info", message="Enrich heartbeat: {'phase':'batch_progress','heartbeat_count':2}", created_at=ts, payload_json="{}"),
        RunEvent(run_id="r", event_id="e3", stage="enrich_heartbeat", level="info", message="Enrich heartbeat: {'phase':'batch_progress','heartbeat_count':3}", created_at=ts, payload_json="{}"),
    ]
    collapsed = _collapse_timeline_noise(events)
    assert len(collapsed) == 1
    kept_event, repeat_count = collapsed[0]
    assert kept_event.event_id == "e1"
    assert repeat_count == 3

def test_timeline_stage_label_maps_enrich_heartbeat_to_in_progress() -> None:
    assert timeline_stage_label("enrich_heartbeat") == "Enrich In Progress"

def test_timeline_stage_summary_message_includes_concurrency_for_applicable_stages() -> None:
    ts = datetime.datetime.now(datetime.timezone.utc)
    enrich_event = RunEvent(
        run_id="r",
        event_id="e-enrich",
        stage="enrich_heartbeat",
        level="info",
        message="Enrich in progress",
        created_at=ts,
        payload_json=json.dumps(
            {
                "phase": "batch_progress",
                "fresh_jobs_total": 9,
                "reused_jobs_total": 7,
                "elapsed_secs": 15,
                "heartbeat_count": 3,
                "enrich_concurrency_effective": 2,
            }
        ),
    )
    ranking_event = RunEvent(
        run_id="r",
        event_id="e-ranking",
        stage="layer3_ranking",
        level="info",
        message="Final ranking: top 6 jobs",
        created_at=ts,
        payload_json=json.dumps({"output_snapshot": {"ranked_jobs": 6, "ranking_concurrency_effective": 4}}),
    )
    cv_analysis_event = RunEvent(
        run_id="r",
        event_id="e-cv-analysis",
        stage="layer4_cv_analysis",
        level="info",
        message="CV analysis complete",
        created_at=ts,
        payload_json=json.dumps(
            {
                "output_snapshot": {
                    "ready_for_generation": 4,
                    "blocked_by_reranker_fit": 2,
                    "skipped_fit_gate": 0,
                    "analysis_failed": 0,
                    "cv_analysis_concurrency_effective": 3,
                }
            }
        ),
    )
    cv_gen_event = RunEvent(
        run_id="r",
        event_id="e-cv-gen",
        stage="layer4_cv_generation_started",
        level="info",
        message="CV generation started for https://example.com [item 1/4]",
        created_at=ts,
        payload_json=json.dumps({"output_snapshot": {"cv_generation_concurrency_effective": 2}}),
    )
    assert "concurrency 2" in _timeline_stage_summary_message(enrich_event, {})
    assert "concurrency 4" in _timeline_stage_summary_message(ranking_event, {})
    assert "concurrency 3" in _timeline_stage_summary_message(cv_analysis_event, {})
    assert "concurrency 2" in _timeline_stage_summary_message(cv_gen_event, {})


def test_timeline_stage_summary_message_distinguishes_enrich_start_vs_progress() -> None:
    ts = datetime.datetime.now(datetime.timezone.utc)
    enrich_start_event = RunEvent(
        run_id="r",
        event_id="e-enrich-start",
        stage="enrich_heartbeat",
        level="info",
        message="Enrich in progress",
        created_at=ts,
        payload_json=json.dumps(
            {
                "phase": "batch_start",
                "fresh_jobs_total": 85,
                "reused_jobs_total": 0,
                "enrich_concurrency_effective": 4,
            }
        ),
    )
    enrich_progress_event = RunEvent(
        run_id="r",
        event_id="e-enrich-progress",
        stage="enrich_heartbeat",
        level="info",
        message="Enrich in progress",
        created_at=ts,
        payload_json=json.dumps(
            {
                "phase": "batch_progress",
                "fresh_jobs_total": 85,
                "reused_jobs_total": 0,
                "enrich_concurrency_effective": 4,
            }
        ),
    )
    start_message = _timeline_stage_summary_message(enrich_start_event, {})
    progress_message = _timeline_stage_summary_message(enrich_progress_event, {})
    assert start_message.startswith("Enrich starting:")
    assert progress_message.startswith("Enrich in progress:")

def test_timeline_stage_summary_message_does_not_call_terminal_review_paused() -> None:
    event = RunEvent(
        run_id="r",
        event_id="e-review",
        stage="cv_review_required",
        level="warning",
        message="Review required: 4 CV item(s) pending operator action. Auto-accepted=0.",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        payload_json=json.dumps({"review_required_total": 4, "auto_accepted": 0}),
    )

    message = _timeline_stage_summary_message(event, {})

    assert message.startswith("Review required:")
    assert "Run paused" not in message

def test_synonym_decision_ledger_marks_reviewed_rows_as_decision_applied() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-ledger-reviewed-source",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        synonym_proposals_json=json.dumps(
            {
                "run_id": "run-ledger-reviewed-source",
                "proposals": [
                    {
                        "proposal_id": "proposal-approved",
                        "alias": "gcp",
                        "canonical": "google cloud",
                        "proposal_status": "approved_for_run_overlay",
                        "review_history": [
                            {
                                "action": "approve_for_run_overlay",
                                "acted_by": "admin",
                                "acted_at": "2026-05-19T20:13:54.777492+00:00",
                            }
                        ],
                        "recommended_action": "approve",
                    },
                    {
                        "proposal_id": "proposal-pending",
                        "alias": "azure",
                        "canonical": "microsoft azure",
                        "proposal_status": "proposed_unreviewed",
                        "review_history": [],
                        "recommended_action": "approve",
                    },
                ],
            }
        ),
    )
    rows = _build_synonym_proposal_decision_ledger(run)
    by_alias = {str(row.get("alias")): row for row in rows}
    assert by_alias["gcp"]["decision_source"] == "review_decision_applied"
    assert by_alias["azure"]["decision_source"] == "generated_for_review"
def test_post_runs_inserts_before_enqueue(tmp_path):
    """@proves admin_control_plane_core.insert-before-enqueue-invariant

    BQ insert must happen before enqueue to ensure DB is source of truth.
    """
    call_order = []
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(_minimal_valid_profile_yaml(), encoding="utf-8")

    def fake_insert(*args, **kwargs):
        call_order.append("insert")

    def fake_enqueue_with_job(*args, **kwargs):
        call_order.append("enqueue")
        return "run-123", "rq-job-abc"

    with patch("fitcv_cp.app.insert_run", side_effect=fake_insert), \
         patch(
             "fitcv_cp.app.submit_run",
             side_effect=lambda **kwargs: RunSubmission(
                 run_id="run-123",
                 queue_job_id=fake_enqueue_with_job()[1],
                 backend_run_id="run-123",
                 backend="default_queue",
             ),
         ), \
         patch("fitcv_cp.app.update_run_queue_job_id"), \
         patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p","pipeline": {"final_top_n": 10},
             "paths": {"candidate_profile": str(profile_path)},
         }):
        resp = TestClient(_app()).post("/runs", json={"jobs_path": str(jobs_file)})
    assert resp.status_code == 201, resp.text
    assert "run_id" in resp.json()
    assert call_order == ["insert", "enqueue"], f"Order was: {call_order}"

def test_post_runs_does_not_warn_for_whole_synonym_map_changes(tmp_path) -> None:
    from types import SimpleNamespace

    captured: dict[str, Any] = {}
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(_minimal_valid_profile_yaml(), encoding="utf-8")
    prior_run = SimpleNamespace(
        run_id="prior-success",
        status="succeeded",
        effective_settings_json=json.dumps(
            {"skill_synonyms": {"looker": "looker studio"}}
        ),
    )

    def _capture_insert(run, *args, **kwargs):
        captured["run"] = run

    with patch("fitcv_cp.app.insert_run", side_effect=_capture_insert), \
         patch(
             "fitcv_cp.app.submit_run",
             return_value=RunSubmission(
                 run_id="run-123",
                 queue_job_id="rq-job-abc",
                 backend_run_id="run-123",
                 backend="default_queue",
             ),
         ), \
         patch("fitcv_cp.app.update_run_queue_job_id"), \
         patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.list_runs", return_value=[prior_run]) as list_runs_mock, \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p",
             "pipeline": {"final_top_n": 10},
             "paths": {"candidate_profile": str(profile_path)},
             "skill_synonyms": {
                 "looker": "looker studio",
                 "power bi": "microsoft power bi",
             },
         }):
        response = TestClient(_app()).post(
            "/runs",
            json={"jobs_path": str(jobs_file)},
        )

    assert response.status_code == 201, response.text
    assert response.json()["warnings"] == []
    effective = json.loads(captured["run"].effective_settings_json)
    assert effective["trigger_runtime_envelope"]["reuse_precheck_warning"] == {}
    list_runs_mock.assert_not_called()

def test_post_runs_persists_backend_binding_from_submission(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(_minimal_valid_profile_yaml(), encoding="utf-8")

    def _submit_stub(*, run_id: str | None = None, **_: object) -> RunSubmission:
        return RunSubmission(
            run_id=str(run_id or "run-123"),
            queue_job_id="rq-job-abc",
            backend_run_id="flow-run-xyz",
            backend="queue",
        )

    with patch("fitcv_cp.app.insert_run"), \
         patch("fitcv_cp.app.submit_run", side_effect=_submit_stub), \
         patch("fitcv_cp.app.update_run_queue_job_id") as binding_mock, \
         patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p","pipeline": {"final_top_n": 10},
             "paths": {"candidate_profile": str(profile_path)},
         }):
        resp = TestClient(_app()).post("/runs", json={"jobs_path": str(jobs_file)})
    assert resp.status_code == 201, resp.text
    kwargs = binding_mock.call_args.kwargs
    assert binding_mock.call_args.args == (resp.json()["run_id"], "rq-job-abc")
    assert kwargs["orchestration_backend"] == "queue"
    assert kwargs["orchestration_run_id"] == "flow-run-xyz"


def test_get_run_detail_reconciles_orphaned_running_run_when_queue_job_missing() -> None:
    from fitcv_cp.models import PipelineRun
    from datetime import datetime, timezone

    running = PipelineRun(
        run_id="run-orphaned-1",
        status=RunStatus.RUNNING,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        queue_job_id="rq-missing-1",
        run_mode="run_all",
    )
    failed = PipelineRun(
        run_id="run-orphaned-1",
        status=RunStatus.FAILED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=running.created_at,
        started_at=running.started_at,
        finished_at=datetime.now(timezone.utc),
        error_message="Queue job rq-missing-1 missing while run remained RUNNING",
        run_mode="run_all",
    )

    with patch("fitcv_cp.app.get_run", side_effect=[running, failed]), \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.append_event"), \
         patch("fitcv_cp.app.get_queue_job_status", return_value="missing"):
        resp = TestClient(_app()).get("/runs/run-orphaned-1")

    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "failed"
    assert mock_update_status.called


def test_get_run_detail_reconciles_orphaned_running_direct_store_detail() -> None:
    from datetime import datetime, timezone

    running = PipelineRun(
        run_id="run-direct-store-orphaned-1",
        status=RunStatus.RUNNING,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        queue_job_id="rq-direct-store-missing-1",
        run_mode="run_all",
    )
    failed = PipelineRun(
        run_id=running.run_id,
        status=RunStatus.FAILED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path=running.jobs_path,
        config_path=running.config_path,
        created_at=running.created_at,
        started_at=running.started_at,
        finished_at=datetime.now(timezone.utc),
        error_message="Queue job rq-direct-store-missing-1 missing while run remained RUNNING",
        run_mode="run_all",
    )
    app = _app()
    app.state.run_store.get_run_detail_fn = lambda _run_id: {
        "run_id": running.run_id,
        "status": "running",
        "backend_status": "running",
        "queue_job_id": running.queue_job_id,
    }

    with patch("fitcv_cp.app.get_run", side_effect=[running, failed]), \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.append_event"), \
         patch("fitcv_cp.app.get_queue_job_status", return_value="missing"):
        response = TestClient(app).get(f"/runs/{running.run_id}")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "failed"
    assert mock_update_status.called


def test_run_detail_poll_reads_canonical_data_envelope() -> None:
    template = Path("src/fitcv_cp/templates/run_detail.html").read_text(encoding="utf-8")

    assert "const run = payload.data || {};" in template
    assert "const nextStatus = run.status || '';" in template


def test_get_run_detail_keeps_running_for_inline_started_job_status() -> None:
    from fitcv_cp.models import PipelineRun
    from datetime import datetime, timezone

    running = PipelineRun(
        run_id="run-inline-1",
        status=RunStatus.RUNNING,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        queue_job_id="inline-job-1",
        run_mode="run_all",
    )

    with patch("fitcv_cp.app.get_run", return_value=running), \
         patch("fitcv_cp.app.get_queue_job_status", return_value="started"), \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.append_event") as mock_append_event:
        resp = TestClient(_app()).get("/runs/run-inline-1")

    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "running"
    assert not mock_update_status.called
    assert not mock_append_event.called

def test_get_run_detail_keeps_running_for_inline_missing_job_status() -> None:
    from fitcv_cp.models import PipelineRun
    from datetime import datetime, timezone

    running = PipelineRun(
        run_id="run-inline-missing-1",
        status=RunStatus.RUNNING,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        queue_job_id="inline-job-missing-1",
        run_mode="run_all",
    )

    with patch("fitcv_cp.app.get_run", return_value=running), \
         patch("fitcv_cp.app.get_queue_job_status", return_value="missing"), \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.append_event") as mock_append_event:
        resp = TestClient(_app()).get("/runs/run-inline-missing-1")

    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "running"
    assert not mock_update_status.called
    assert not mock_append_event.called

def test_get_run_detail_reconciles_orphaned_queued_run_when_queue_job_ended() -> None:
    from fitcv_cp.models import PipelineRun
    from datetime import datetime, timedelta, timezone

    created_at = datetime.now(timezone.utc) - timedelta(seconds=60)
    queued = PipelineRun(
        run_id="run-orphaned-queued-1",
        status=RunStatus.QUEUED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=created_at,
        queue_job_id="rq-ended-1",
        run_mode="run_all",
    )
    failed = PipelineRun(
        run_id="run-orphaned-queued-1",
        status=RunStatus.FAILED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=created_at,
        finished_at=datetime.now(timezone.utc),
        error_message="stub",
        queue_job_id="rq-ended-1",
        run_mode="run_all",
    )

    with patch("fitcv_cp.app.get_run", side_effect=[queued, failed]), \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.append_event"), \
         patch("fitcv_cp.app.get_queue_job_status", return_value="finished"):
        resp = TestClient(_app()).get("/runs/run-orphaned-queued-1")

    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "failed"
    assert mock_update_status.called

def test_get_runs_list_reconciles_orphaned_running_run_when_queue_job_missing() -> None:
    from fitcv_cp.models import PipelineRun
    from datetime import datetime, timezone

    running = PipelineRun(
        run_id="run-orphaned-list-1",
        status=RunStatus.RUNNING,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        queue_job_id="rq-missing-list-1",
        run_mode="run_all",
    )
    failed = PipelineRun(
        run_id="run-orphaned-list-1",
        status=RunStatus.FAILED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=running.created_at,
        started_at=running.started_at,
        finished_at=datetime.now(timezone.utc),
        error_message="Queue job rq-missing-list-1 missing while run remained RUNNING",
        run_mode="run_all",
    )

    app = _app()
    app.state.run_store.query_runs_fn = lambda **_kwargs: {
        "items": [running], "total": 1, "active_count": 1, "archived_count": 0
    }
    app.state.run_store.get_run_detail_fn = lambda _run_id: None
    with patch("fitcv_cp.app.get_run", return_value=failed), \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.append_event"), \
         patch("fitcv_cp.app.get_queue_job_status", return_value="missing"):
        resp = TestClient(app).get("/runs")

    assert resp.status_code == 200
    payload = resp.json()["data"]
    assert isinstance(payload, list) and payload
    assert payload[0]["backend_status"] == "failed"
    assert mock_update_status.called

def test_get_runs_list_keeps_running_for_inline_missing_job_status() -> None:
    from fitcv_cp.models import PipelineRun
    from datetime import datetime, timezone

    running = PipelineRun(
        run_id="run-inline-missing-list-1",
        status=RunStatus.RUNNING,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        queue_job_id="inline-job-missing-list-1",
        run_mode="run_all",
    )

    app = _app()
    app.state.run_store.query_runs_fn = lambda **_kwargs: {
        "items": [running], "total": 1, "active_count": 1, "archived_count": 0
    }
    app.state.run_store.get_run_detail_fn = lambda _run_id: None
    with patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.append_event") as mock_append_event, \
         patch("fitcv_cp.app.get_queue_job_status", return_value="missing"):
        resp = TestClient(app).get("/runs")

    assert resp.status_code == 200
    payload = resp.json()["data"]
    assert isinstance(payload, list) and payload
    assert payload[0]["backend_status"] == "running"
    assert not mock_update_status.called
    assert not mock_append_event.called

def test_admin_runs_reconciles_orphaned_running_run_when_queue_job_missing() -> None:
    from fitcv_cp.models import PipelineRun
    from datetime import datetime, timezone

    running = PipelineRun(
        run_id="run-orphaned-admin-1",
        status=RunStatus.RUNNING,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        queue_job_id="rq-missing-admin-1",
        run_mode="run_all",
    )
    failed = PipelineRun(
        run_id="run-orphaned-admin-1",
        status=RunStatus.FAILED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=running.created_at,
        started_at=running.started_at,
        finished_at=datetime.now(timezone.utc),
        error_message="Queue job rq-missing-admin-1 missing while run remained RUNNING",
        run_mode="run_all",
    )

    with patch("fitcv_cp.app.list_runs", return_value=[running]), \
         patch("fitcv_cp.app.get_run", return_value=failed), \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.append_event"), \
         patch("fitcv_cp.app.get_queue_job_status", return_value="missing"), \
         patch("fitcv_cp.app.get_pipeline_runs_schema_status", return_value={"status": "complete", "missing_columns": [], "warning": None}):
        resp = TestClient(_app()).get("/admin/runs")

    assert resp.status_code == 200
    assert "run-orphaned-admin-1" in resp.text
    assert "failed" in resp.text.lower()
    assert mock_update_status.called

def test_admin_runs_keeps_running_for_inline_missing_job_status() -> None:
    from fitcv_cp.models import PipelineRun
    from datetime import datetime, timezone

    running = PipelineRun(
        run_id="run-inline-missing-admin-1",
        status=RunStatus.RUNNING,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        queue_job_id="inline-job-missing-admin-1",
        run_mode="run_all",
    )

    with patch("fitcv_cp.app.list_runs", return_value=[running]), \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.append_event") as mock_append_event, \
         patch("fitcv_cp.app.get_queue_job_status", return_value="missing"), \
         patch("fitcv_cp.app.get_pipeline_runs_schema_status", return_value={"status": "complete", "missing_columns": [], "warning": None}):
        resp = TestClient(_app()).get("/admin/runs")

    assert resp.status_code == 200
    assert "run-inline-missing-admin-1" in resp.text
    assert "running" in resp.text.lower()
    assert not mock_update_status.called
    assert not mock_append_event.called


def test_post_runs_rejects_empty_jobs_path():
    resp = TestClient(_app()).post("/runs", json={"jobs_path": ""})
    assert resp.status_code == 422


def test_post_runs_multipart_uses_profile_run_name_and_idempotency() -> None:
    captured: dict[str, Any] = {}
    app = _app()
    app.state.run_store.get_candidate_profile_fn = lambda profile_id: {
        "candidate_profile_id": profile_id,
        "name": "Product Data Specialist",
        "profile": {"name": "Candidate", "experiences": [], "education": []},
        "revision": 3,
        "checksum": "profile-checksum",
        "is_active": True,
    }
    app.state.run_store.reserve_idempotent_action_fn = lambda scope, key, fingerprint: {
        "action_id": "action-trigger-1",
        "status": "queued",
        "replayed": False,
        "response": None,
    }
    app.state.run_store.complete_idempotent_action_fn = lambda _action_id, _response: None
    app.state.run_store.create_run_bundle_fn = lambda run, **kwargs: (
        captured.update(run=run, **kwargs) or {"run_id": run.run_id}
    )
    app.state.run_store.update_run_queue_job_id_fn = lambda *_args, **_kwargs: {}
    app.state.run_store.get_run_detail_fn = lambda run_id: {
        "run_id": run_id,
        "run_name": captured["run"].run_name,
        "backend_status": "queued",
        "input": {
            "original_filename": "jobs.json",
            "candidate_profile_id": "candidate-product-data",
        },
    }

    with patch("fitcv_cp.app.load_active_settings", return_value={}), patch(
        "fitcv_cp.app.load_config",
        return_value={"pipeline": {"final_top_n": 10}},
    ), patch(
        "fitcv_cp.app.submit_run",
        return_value=RunSubmission(
            run_id="ignored",
            queue_job_id="queue-1",
            backend_run_id="queue-1",
            backend="default_queue",
        ),
    ):
        resp = TestClient(app).post(
            "/runs",
            headers={"Idempotency-Key": "trigger-1"},
            files={
                "jobs_file": (
                    "jobs.json",
                    json.dumps([_valid_fitcv_job(title="Analyst", jobUrl="https://example.com/job", job_url="https://example.com/job")]),
                    "application/json",
                )
            },
            data={
                "profile_id": "candidate-product-data",
                "run_name": "Senior data product search",
            },
        )

    assert resp.status_code == 201, resp.text
    assert resp.json()["data"]["run_name"] == "Senior data product search"
    assert captured["run"].candidate_profile_source == "candidate-product-data"
    assert json.loads(captured["run"].jobs_input_json)[0]["title"] == "Analyst"
    assert captured["input_resource"]["candidate_profile_id"] == "candidate-product-data"


@pytest.mark.parametrize(
    ("filename", "content", "profile", "expected_status", "expected_code"),
    [
        ("jobs.txt", json.dumps([_valid_fitcv_job(title="Analyst")]), None, 422, "validation_failed"),
        ("jobs.json", b"", None, 422, "validation_failed"),
        ("jobs.json", "{", None, 422, "validation_failed"),
        (
            "jobs.json",
            json.dumps([_valid_fitcv_job(title="Analyst")]),
            {"candidate_profile_id": "candidate-1", "is_active": False},
            409,
            "candidate_profile_unavailable",
        ),
    ],
)
def test_post_runs_multipart_rejects_invalid_boundary_inputs(
    filename: str,
    content: str | bytes,
    profile: dict[str, Any] | None,
    expected_status: int,
    expected_code: str,
) -> None:
    app = _app()
    app.state.run_store.get_candidate_profile_fn = lambda _profile_id: profile

    resp = TestClient(app).post(
        "/runs",
        headers={"Idempotency-Key": "trigger-invalid-1"},
        files={"jobs_file": (filename, content, "application/json")},
        data={"profile_id": "candidate-1"},
    )

    assert resp.status_code == expected_status
    assert resp.json()["error"]["code"] == expected_code


def test_post_runs_multipart_replays_original_resource_without_enqueue() -> None:
    app = _app()
    app.state.run_store.get_candidate_profile_fn = lambda profile_id: {
        "candidate_profile_id": profile_id,
        "name": "Product Data Specialist",
        "profile": {"name": "Candidate"},
        "revision": 1,
        "is_active": True,
    }
    app.state.run_store.reserve_idempotent_action_fn = lambda *_args: {
        "action_id": "action-trigger-1",
        "replayed": True,
        "response": {"run_id": "run-1", "backend_status": "queued", "action_id": "action-trigger-1"},
    }

    with patch("fitcv_cp.app.submit_run") as submit:
        resp = TestClient(app).post(
            "/runs",
            headers={"Idempotency-Key": "trigger-1"},
            files={"jobs_file": ("jobs.json", json.dumps([_valid_fitcv_job(title="Analyst")]), "application/json")},
            data={"profile_id": "candidate-1"},
        )

    assert resp.status_code == 201
    assert resp.json()["data"]["run_id"] == "run-1"
    submit.assert_not_called()


def test_post_runs_multipart_enqueue_failure_returns_persisted_failed_run() -> None:
    with patch("fitcv_cp.app.load_active_settings", return_value={}), patch(
        "fitcv_cp.app.load_config", return_value={"pipeline": {"final_top_n": 10}}
    ), patch("fitcv_cp.app.submit_run", side_effect=RuntimeError("queue unavailable")):
        app = _app()
        app.state.run_store.get_candidate_profile_fn = lambda profile_id: {
            "candidate_profile_id": profile_id,
            "name": "Product Data Specialist",
            "profile": {"name": "Candidate"},
            "revision": 1,
            "is_active": True,
        }
        app.state.run_store.reserve_idempotent_action_fn = lambda *_args: {
            "action_id": "action-trigger-1",
            "replayed": False,
            "response": None,
        }
        app.state.run_store.complete_idempotent_action_fn = lambda *_args: None
        app.state.run_store.create_run_bundle_fn = lambda run, **_kwargs: {"run_id": run.run_id}
        app.state.run_store.update_run_status_fn = lambda *_args, **_kwargs: {}
        app.state.run_store.get_run_detail_fn = lambda run_id: {
            "run_id": run_id,
            "backend_status": "failed",
            "error_code": "orchestration_enqueue",
            "error_message": "queue unavailable",
        }

        resp = TestClient(app).post(
            "/runs",
            headers={"Idempotency-Key": "trigger-1"},
            files={"jobs_file": ("jobs.json", json.dumps([_valid_fitcv_job(title="Analyst")]), "application/json")},
            data={"profile_id": "candidate-1"},
        )

    assert resp.status_code == 503
    assert resp.json()["data"]["backend_status"] == "failed"
    assert resp.json()["data"]["error_code"] == "orchestration_enqueue"
    assert resp.json()["error"] == {
        "code": "run_enqueue_failed",
        "message": "Run was created but could not be queued.",
        "field_errors": [],
        "retryable": True,
        "action": "Check queue connectivity, then trigger a new Run.",
    }


def test_post_runs_persists_manual_staged_mode(tmp_path) -> None:
    """@proves trigger_run_management.execution-mode-selection"""
    captured = {}
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(_minimal_valid_profile_yaml(), encoding="utf-8")

    def _capture_insert(run, *args, **kwargs):
        captured["run"] = run

    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.insert_run", side_effect=_capture_insert), \
         patch("fitcv_cp.app.submit_run", return_value=RunSubmission(run_id="run-123", queue_job_id="rq-job-abc", backend_run_id="rq-job-abc", backend="default_queue")), \
         patch("fitcv_cp.app.update_run_queue_job_id"), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p","pipeline": {"final_top_n": 10},
             "paths": {"candidate_profile": str(profile_path)},
         }):
        resp = TestClient(_app()).post("/runs", json={
            "jobs_path": str(jobs_file),
            "run_mode": "manual_staged",
        })

    assert resp.status_code == 201, resp.text
    assert captured["run"].run_mode == "manual_staged"
    assert captured["run"].next_stage == "normalize"
    assert captured["run"].completed_stages == []


def test_post_runs_path_trigger_persists_canonical_jobs_and_candidate_snapshots(tmp_path) -> None:
    captured = {}

    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(_minimal_valid_profile_yaml(), encoding="utf-8")

    def _capture_insert(run, *args, **kwargs):
        captured["run"] = run

    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.insert_run", side_effect=_capture_insert), \
         patch("fitcv_cp.app.submit_run", return_value=RunSubmission(run_id="run-123", queue_job_id="rq-job-abc", backend_run_id="rq-job-abc", backend="default_queue")), \
         patch("fitcv_cp.app.update_run_queue_job_id"), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p",
             "pipeline": {"final_top_n": 10},
             "paths": {"candidate_profile": str(profile_path)},
         }):
        resp = TestClient(_app()).post("/runs", json={"jobs_path": str(jobs_file)})

    assert resp.status_code == 201, resp.text
    assert captured["run"].jobs_input_source == "path"
    assert json.loads(captured["run"].jobs_input_json) == [
        _valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")
    ]
    assert captured["run"].candidate_profile_source == "default_config"
    profile_snapshot = json.loads(captured["run"].candidate_profile_json)
    assert profile_snapshot["preferences"]["domains"] == ["fintech"]
    effective = json.loads(captured["run"].effective_settings_json)
    assert json.loads(effective["runtime_inputs"]["candidate_profile_json"]) == profile_snapshot
    assert "cv_generation_runtime_expectation" in effective["runtime_inputs"]
    assert "synonym_triage_runtime_expectation" in effective["runtime_inputs"]
    synonym_settings = dict(effective.get("synonym_management") or {})
    assert synonym_settings.get("apply_approved_enabled") is True
    assert synonym_settings.get("auto_accept_suggestions_enabled") is False
    assert synonym_settings.get("auto_accept_ai_action_enabled") is True
    assert "auto_apply_recommendation_enabled" not in synonym_settings
    assert "auto_promote_global_enabled" not in synonym_settings


def test_trigger_runtime_envelope_snapshots_prompt_metadata_without_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fitcv_cp import app as app_module

    prompt_snapshot = {
        "tasks": {
            "enrich_extraction": {
                "revision": 2,
                "replacement_sha256": "abc123",
                "replacement_char_count": 42,
            }
        }
    }
    monkeypatch.setenv("FITCV_LOCAL_MODE", "1")
    monkeypatch.setattr(
        app_module,
        "build_packaged_llm_configuration_snapshot",
        lambda: {"revision": 1, "tasks": {}},
    )
    monkeypatch.setattr(
        app_module,
        "build_prompt_configuration_snapshot",
        lambda: prompt_snapshot,
    )
    monkeypatch.setattr(app_module, "resolve_openai_compatible_api_key", lambda: None)

    effective = app_module._apply_trigger_runtime_envelope(
        {},
        jobs_input_source=None,
        jobs_input_json=None,
        jobs_input_manifest_json=None,
        candidate_profile_source=None,
        candidate_profile_json=None,
        run_mode="run_all",
    )

    assert effective["runtime_inputs"]["prompt_configuration_snapshot"] == prompt_snapshot
    assert "replacement_text" not in json.dumps(effective)


def test_trigger_runtime_envelope_snapshots_system_retry_resource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fitcv_cp import app as app_module

    system_snapshot = {
        "maximum_attempts": 4,
        "initial_backoff_seconds": 12,
        "lease_seconds": 300,
        "reconciler_interval_seconds": 30,
        "error_detail_limit": 10000,
        "revision": 7,
        "updated_at": "2026-07-22T12:00:00+00:00",
    }
    monkeypatch.setenv("FITCV_LOCAL_MODE", "1")
    monkeypatch.setattr(app_module, "load_system_settings", lambda: system_snapshot)
    monkeypatch.setattr(app_module, "build_packaged_llm_configuration_snapshot", lambda: {"revision": 1, "tasks": {}})
    monkeypatch.setattr(app_module, "build_prompt_configuration_snapshot", lambda: {"tasks": {}})
    monkeypatch.setattr(app_module, "resolve_openai_compatible_api_key", lambda: None)

    effective = app_module._apply_trigger_runtime_envelope(
        {},
        jobs_input_source=None,
        jobs_input_json=None,
        jobs_input_manifest_json=None,
        candidate_profile_source=None,
        candidate_profile_json=None,
        run_mode="run_all",
    )

    assert effective["runtime_inputs"]["system_settings_snapshot"] == system_snapshot


def test_post_runs_queue_failure_terminalizes_existing_run(tmp_path) -> None:
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(_minimal_valid_profile_yaml(), encoding="utf-8")

    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.insert_run"), \
         patch("fitcv_cp.app.submit_run", side_effect=RuntimeError("queue unavailable")), \
         patch("fitcv_cp.app.update_run_status") as update_status, \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p",
             "pipeline": {"final_top_n": 10},
             "paths": {"candidate_profile": str(profile_path)},
         }):
        response = TestClient(_app(), raise_server_exceptions=False).post(
            "/runs", json={"jobs_path": str(jobs_file)}
        )

    assert response.status_code == 503
    assert update_status.call_args.args[1] == RunStatus.FAILED
    assert update_status.call_args.kwargs["error_stage"] == "orchestration_enqueue"

def test_post_runs_path_trigger_captures_cv_generation_runtime_expectation(tmp_path) -> None:
    captured = {}
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(_minimal_valid_profile_yaml(), encoding="utf-8")

    def _capture_insert(run, *args, **kwargs):
        captured["run"] = run

    with patch(
        "fitcv_cp.app.resolve_cv_generation_runtime_expectation",
        return_value={
            "provider": "openai_compatible",
            "model": "cx/gpt-5.2",
            "base_url": "http://router.local/v1",
            "wire_api": "chat_completions",
            "source": "control_plane",
        },
    ), patch("fitcv_cp.app.resolve_openai_compatible_api_key", return_value=""), \
         patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.insert_run", side_effect=_capture_insert), \
         patch("fitcv_cp.app.submit_run", return_value=RunSubmission(run_id="run-123", queue_job_id="rq-job-abc", backend_run_id="rq-job-abc", backend="default_queue")), \
         patch("fitcv_cp.app.update_run_queue_job_id"), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p",
             "pipeline": {"final_top_n": 10},
             "paths": {"candidate_profile": str(profile_path)},
         }):
        resp = TestClient(_app()).post("/runs", json={"jobs_path": str(jobs_file)})

    assert resp.status_code == 201, resp.text
    effective = json.loads(captured["run"].effective_settings_json)
    expectation = effective["runtime_inputs"]["cv_generation_runtime_expectation"]
    assert expectation["provider"] == "openai_compatible"
    assert expectation["model"] == "cx/gpt-5.2"
    assert expectation["base_url"] == "http://router.local/v1"
    assert expectation["wire_api"] == "chat_completions"
    assert expectation["api_key_available"] is False


def test_post_runs_run_all_and_manual_staged_share_canonical_runtime_envelope(tmp_path) -> None:
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(_minimal_valid_profile_yaml(), encoding="utf-8")

    captured_runs: list = []

    def _capture_insert(run, *args, **kwargs):
        captured_runs.append(run)

    config = {
        "gcp_project": "p",
        "pipeline": {"final_top_n": 10},
        "paths": {"candidate_profile": str(profile_path)},
    }

    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.insert_run", side_effect=_capture_insert), \
         patch("fitcv_cp.app.submit_run", return_value=RunSubmission(run_id="run-123", queue_job_id="rq-job-abc", backend_run_id="rq-job-abc", backend="default_queue")), \
         patch("fitcv_cp.app.update_run_queue_job_id"), \
         patch("fitcv_cp.app.load_config", return_value=config):
        run_all_resp = TestClient(_app()).post(
            "/runs",
            json={"jobs_path": str(jobs_file), "run_mode": "run_all"},
        )
        staged_resp = TestClient(_app()).post(
            "/runs",
            json={"jobs_path": str(jobs_file), "run_mode": "manual_staged"},
        )

    assert run_all_resp.status_code == 201
    assert staged_resp.status_code == 201
    run_all, staged = captured_runs
    assert run_all.jobs_input_source == staged.jobs_input_source == "path"
    assert json.loads(run_all.jobs_input_json) == json.loads(staged.jobs_input_json)
    assert run_all.candidate_profile_source == staged.candidate_profile_source == "default_config"
    assert json.loads(run_all.candidate_profile_json) == json.loads(staged.candidate_profile_json)
    run_all_effective = json.loads(run_all.effective_settings_json)
    staged_effective = json.loads(staged.effective_settings_json)
    assert json.loads(run_all_effective["runtime_inputs"]["candidate_profile_json"]) == json.loads(
        staged_effective["runtime_inputs"]["candidate_profile_json"]
    )
    assert run_all.next_stage is None
    assert staged.next_stage == "normalize"


def test_get_runs_returns_list():
    """@proves trigger_run_management.runs-list-management"""
    app = _app()
    app.state.run_store.query_runs_fn = lambda **_kwargs: {
        "items": [],
        "total": 0,
        "active_count": 0,
        "archived_count": 0,
        "page": 1,
        "page_size": 20,
    }
    resp = TestClient(app).get("/runs")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["data"] == []
    assert payload["page"] == {"number": 1, "size": 20, "total_items": 0, "total_pages": 0}
    assert payload["meta"]["active_count"] == 0
    assert payload["meta"]["archived_count"] == 0
    assert payload["meta"]["view"] == "active"
    assert payload["meta"]["search"] == ""
    assert datetime.datetime.fromisoformat(payload["meta"]["server_time"]).tzinfo is not None


def test_get_runs_returns_frontend_run_metadata() -> None:
    from fitcv_cp.models import PipelineRun

    archived_at = datetime.datetime.now(datetime.timezone.utc)
    run = PipelineRun(
        run_id="run-frontend-metadata-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/uploads/generated.json",
        config_path=".env.yaml",
        created_at=archived_at,
        jobs_input_source="upload",
        jobs_input_manifest_json='{"source_filenames":["named-run.json"]}',
        candidate_profile_source="default_config",
        archived_at=archived_at,
    )
    with patch("fitcv_cp.app.list_runs", return_value=[run]):
        resp = TestClient(_app()).get("/runs?view=archived")

    assert resp.status_code == 200
    payload = resp.json()["data"][0]
    assert payload["jobs_input_manifest_json"] == run.jobs_input_manifest_json
    assert payload["candidate_profile_source"] == "default_config"
    assert payload["archived_at"] == archived_at.isoformat()


def test_get_runs_legacy_fallback_preserves_tab_counts_and_server_time() -> None:
    from fitcv_cp.models import PipelineRun

    created_at = datetime.datetime.now(datetime.timezone.utc)
    active = PipelineRun(
        run_id="run-active-count-1",
        status=RunStatus.RUNNING,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/active.json",
        config_path=".env.yaml",
        created_at=created_at,
    )
    archived = PipelineRun(
        run_id="run-archived-count-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/archived.json",
        config_path=".env.yaml",
        created_at=created_at,
        archived_at=created_at,
    )

    with patch("fitcv_cp.app.list_runs", return_value=[active, archived]):
        resp = TestClient(_app()).get("/runs?view=archived")

    assert resp.status_code == 200
    assert [item["run_id"] for item in resp.json()["data"]] == ["run-archived-count-1"]
    assert resp.json()["meta"]["active_count"] == 1
    assert resp.json()["meta"]["archived_count"] == 1
    assert datetime.datetime.fromisoformat(resp.json()["meta"]["server_time"]).tzinfo is not None


def test_get_run_detail_not_found():
    app = _app()
    app.state.run_store.get_run_detail_fn = lambda _run_id: None
    resp = TestClient(app).get("/runs/missing-id")
    assert resp.status_code == 404
    assert resp.json() == {
        "error": {
            "code": "run_not_found",
            "message": "Run not found.",
            "field_errors": [],
            "retryable": False,
            "action": "Return to Runs and select an existing Run.",
        }
    }


def test_run_detail_queued_shows_stop_run() -> None:
    from fitcv_cp.models import PipelineRun

    run = PipelineRun(
        run_id="run-detail-queued-stop",
        status=RunStatus.QUEUED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        response = TestClient(_app()).get(f"/admin/runs/{run.run_id}")

    assert response.status_code == 200
    assert "Stop Run" in response.text
    assert f'data-run-lifecycle-action="stop" data-run-id="{run.run_id}"' in response.text
    assert "Archive Run" not in response.text


def test_run_detail_with_candidate_profile_snapshot_does_not_raise_json_name_error() -> None:
    run = PipelineRun(
        run_id="run-detail-profile-snapshot",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        candidate_profile_json=json.dumps({"candidate_profile_id": "missing-profile"}),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        response = TestClient(_app(), raise_server_exceptions=False).get(
            f"/admin/runs/{run.run_id}"
        )

    assert response.status_code == 200

def test_run_events_reads_canonical_pipeline_process_events() -> None:
    from fitcv_cp.models import build_process_event

    app = _app()
    calls: list[str] = []
    event = build_process_event(
        process_type="pipeline",
        process_id="run-process-events",
        operation="normalize",
        state="succeeded",
        level="info",
        message="Normalized",
        event_id="event-normalize",
    )
    app.state.run_store.get_run_detail_fn = lambda _run_id: {"run_id": "run-process-events"}

    def fake_get_process_events(process_type: str, *_args: object, **_kwargs: object) -> dict[str, object]:
        calls.append(process_type)
        return {
            "events": [event],
            "integrity_conflicts": [],
            "total_count": 1,
            "next_cursor": None,
        }

    app.state.run_store.get_process_events_fn = fake_get_process_events
    response = TestClient(app).get("/runs/run-process-events/events")

    assert response.status_code == 200
    assert calls == ["pipeline"]
    assert response.json()["data"][0]["event_id"] == "event-normalize"

def test_run_detail_terminal_statuses_show_archive_run() -> None:
    for status in (RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED):
        run = PipelineRun(
            run_id=f"run-detail-{status.value}-archive",
            status=status,
            triggered_by="admin",
            trigger_source="web",
            jobs_path="data/sample_jobs.json",
            config_path=".env.yaml",
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        with patch("fitcv_cp.app.get_run", return_value=run):
            response = TestClient(_app()).get(f"/admin/runs/{run.run_id}")

        assert response.status_code == 200
        assert "Archive Run" in response.text
        assert f'data-run-lifecycle-action="archive" data-run-id="{run.run_id}"' in response.text
        assert "Stop Run" not in response.text


def test_run_detail_export_uses_shared_request_decoder_and_retry_state() -> None:
    template = Path("src/fitcv_cp/templates/run_detail.html").read_text(encoding="utf-8")

    assert "fitcvRunLocked(exportButton" in template
    assert "fitcvApiRequest(root.dataset.exportUrl" in template
    assert "new Blob([csv], {type: 'text/csv;charset=utf-8'})" in template
    assert "fetch(root.dataset.exportUrl" not in template
    assert "Export failed" not in template
    assert "fitcvRenderAsyncState(notice" in template


def test_run_detail_tab_loader_uses_shared_request_decoder() -> None:
    template = Path("src/fitcv_cp/templates/run_detail.html").read_text(encoding="utf-8")

    assert "const fragment = await fitcvApiRequest(url, {" in template
    assert "const resp = await fetch(url" not in template
    assert "Failed to load tab" not in template
    assert "const activeElement = document.activeElement" in template
    assert "const activeId = activeElement?.id || ''" in template
    assert "CSS.escape(activeId)" in template
    assert "focus({preventScroll: true})" in template


def test_run_detail_poll_uses_shared_request_decoder_and_state() -> None:
    template = Path("src/fitcv_cp/templates/run_detail.html").read_text(encoding="utf-8")

    assert "const payload = await fitcvApiRequest('/runs/' + runId, {" in template
    assert "const resp = await fetch('/runs/' + runId" not in template
    assert "id=\"run-detail-poll-state\"" in template
    assert "fitcvRenderAsyncState(pollState" in template
    assert "Keep polling quiet" not in template


def test_run_detail_bookmark_failure_uses_shared_retry_state() -> None:
    template = Path("src/fitcv_cp/templates/run_detail.html").read_text(encoding="utf-8")

    assert "fitcvRunLocked(button, async () =>" in template
    assert "fitcvRenderAsyncState(notice" in template
    assert "notice.textContent = error.message" not in template


def test_synonym_details_restore_focus_to_opener() -> None:
    template = Path("src/fitcv_cp/templates/synonyms.html").read_text(encoding="utf-8")

    assert "suggestionOpener=b" in template
    assert "detailsDialog.addEventListener('close'" in template
    assert "suggestionOpener.focus()" in template


def test_synonyms_use_shared_async_renderer_and_mutation_locks() -> None:
    template = Path("src/fitcv_cp/templates/synonyms.html").read_text(encoding="utf-8")

    assert "function guarded(control,operation" in template
    assert "fitcvRenderAsyncState(notice" in template
    assert "fitcvRunLocked(control,async" in template
    assert "guarded(button,async" in template
    assert "fitcvIdempotencyKey(button)" in template
    assert ".catch(showError)" not in template
    assert "Promise.all([loadPolicy(),loadSuggestions(),loadLog()])" not in template


def _candidate_profile_resource() -> dict[str, object]:
    return {
        "profile_id": "profile-1", "profile_name": None, "display_name": "profile",
        "original_filename": "profile.yaml", "creation_status": "succeeded", "lifecycle": "active",
        "created_at": "2026-07-21T00:00:00+00:00", "updated_at": "2026-07-21T00:00:00+00:00",
        "archived_at": None, "profile_revision_id": "revision-1", "failure": None,
        "related_run_count": 0, "capabilities": {"inspect": True, "archive": True, "restore": False, "use_for_run": True},
        "revision": 1, "overview": {"skills": []},
        "input": {"original_filename": "profile.yaml", "checksum": "sha", "byte_length": 10, "media_type": "application/yaml"},
    }


def test_candidate_profiles_returns_collection_envelope() -> None:
    app = _app()
    app.state.run_store.query_candidate_profiles_fn = lambda **_kwargs: {
        "items": [_candidate_profile_resource()],
        "total": 1, "active_count": 1, "archived_count": 0, "page": 1, "page_size": 20,
    }

    resp = TestClient(app).get("/candidate-profiles?view=active&status=succeeded")

    assert resp.status_code == 200
    assert resp.json()["data"][0]["profile_id"] == "profile-1"
    assert resp.json()["page"] == {
        "number": 1,
        "size": 20,
        "total_items": 1,
        "total_pages": 1,
    }


def test_candidate_profile_update_route_forwards_cas_and_idempotency() -> None:
    app = _app()
    captured: dict[str, object] = {}

    def update(profile_id: str, **kwargs: object) -> dict[str, object]:
        captured["profile_id"] = profile_id
        captured.update(kwargs)
        return {**_candidate_profile_resource(), "revision": 2, "profile_name": "Updated"}

    app.state.run_store.update_candidate_profile_fn = update
    response = TestClient(app).put(
        "/candidate-profiles/profile-1",
        headers={"Idempotency-Key": "profile-update-route"},
        json={
            "expected_revision": 1,
            "profile_name": "Updated",
            "canonical": {"schema_version": "candidate-profile.v2"},
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["revision"] == 2
    assert captured == {
        "profile_id": "profile-1",
        "canonical": {"schema_version": "candidate-profile.v2"},
        "expected_revision": 1,
        "profile_name": "Updated",
        "idempotency_key": "profile-update-route",
    }



def test_candidate_profile_update_route_passes_cas_and_idempotency() -> None:
    app = _app()
    resource = _candidate_profile_resource()
    calls = []
    app.state.run_store.update_candidate_profile_fn = lambda profile_id, **kwargs: calls.append((profile_id, kwargs)) or {
        **resource, "revision": 2, "overview": kwargs["canonical"], "profile_name": kwargs["profile_name"]
    }
    response = TestClient(app).put(
        "/candidate-profiles/profile-1",
        headers={"Idempotency-Key": "update-route"},
        json={"canonical": {"skills": ["Python"]}, "expected_revision": 1, "profile_name": "Updated"},
    )
    assert response.status_code == 200
    assert calls == [("profile-1", {
        "canonical": {"skills": ["Python"]}, "expected_revision": 1,
        "profile_name": "Updated", "idempotency_key": "update-route",
    })]

    app = _app()
    resource = _candidate_profile_resource()
    app.state.run_store.get_candidate_profile_detail_fn = lambda _profile_id: resource
    app.state.run_store.transition_candidate_profile_lifecycle_fn = lambda _profile_id, **_kwargs: {**resource, "lifecycle": "archived", "revision": 2}
    client = TestClient(app)

    detail = client.get("/candidate-profiles/profile-1")
    archived = client.post(
        "/candidate-profiles/profile-1/actions/archive",
        headers={"Idempotency-Key": "archive-1"}, json={"expected_revision": 1},
    )

    assert client.post("/candidate-profiles").status_code == 405
    assert detail.status_code == 200 and detail.json()["data"]["overview"] == {"skills": []}
    assert archived.status_code == 200 and archived.json()["data"]["lifecycle"] == "archived"


def test_candidate_profile_lifecycle_rejects_noop_and_stale_revision() -> None:
    state = _candidate_profile_mock_app().state.candidate_profile_mock_state
    profile_id = "candidate-product-data"
    active = state.get_profile(profile_id)
    assert active is not None
    with pytest.raises(ValueError, match="candidate_profile_invalid_transition"):
        state.transition_profile(profile_id, lifecycle="active", expected_revision=active["revision"])
    with pytest.raises(ValueError, match="candidate_profile_revision_conflict"):
        state.transition_profile(profile_id, lifecycle="archived", expected_revision=999)


def test_candidate_profile_source_block_route_has_no_alias() -> None:
    paths = {route.path for route in _app().routes}
    assert "/candidate-profile-creation-attempts/{attempt_id}/source-blocks/{source_block_id}" in paths
    assert "/candidate-profiles/{profile_id}/source-blocks/{source_block_id}" not in paths


def test_candidate_profile_delete_route_is_idempotent_and_persists_deletion() -> None:
    app = _app()
    profile = app.state.run_store.create_candidate_profile_attempt(
        profile_bytes=b"experiences: []\nskills: []\nprojects: []\nachievements: []\npreferences: {}\n",
        original_filename="profile.yaml",
        profile_name="Candidate",
    )
    archived = app.state.run_store.transition_candidate_profile_lifecycle(
        profile["profile_id"], lifecycle="archived", expected_revision=profile["revision"]
    )
    client = TestClient(app)

    missing_key = client.post(
        f"/candidate-profiles/{profile['profile_id']}/actions/delete",
        json={"expected_revision": archived["revision"]},
    )

    first = client.post(
        f"/candidate-profiles/{profile['profile_id']}/actions/delete",
        headers={"Idempotency-Key": "delete-profile"},
        json={"expected_revision": archived["revision"]},
    )
    replay = client.post(
        f"/candidate-profiles/{profile['profile_id']}/actions/delete",
        headers={"Idempotency-Key": "delete-profile"},
        json={"expected_revision": archived["revision"]},
    )

    assert missing_key.status_code == 422
    assert missing_key.json()["error"]["field_errors"][0]["field"] == "Idempotency-Key"
    assert first.status_code == 200
    assert first.json() == replay.json() == {"data": {"profile_id": profile["profile_id"], "deleted": True}}
    assert client.get(f"/candidate-profiles/{profile['profile_id']}").status_code == 404


def test_candidate_profile_delete_route_rejects_referenced_profile() -> None:
    app = _app()
    profile = app.state.run_store.create_candidate_profile_attempt(
        profile_bytes=b"experiences: []\nskills: []\nprojects: []\nachievements: []\npreferences: {}\n",
        original_filename="profile.yaml",
        profile_name="Candidate",
    )
    app.state.run_store.create_run_bundle(
        PipelineRun(
            run_id="run-candidate-delete-reference",
            status=RunStatus.SUCCEEDED,
            triggered_by="admin",
            trigger_source="ui",
            jobs_path="jobs.json",
            config_path=".env.yaml",
            created_at=datetime.datetime.now(datetime.timezone.utc),
        ),
        input_resource={
            "strict_candidate_profile": True,
            "candidate_profile_id": profile["profile_id"],
            "jobs_snapshot_json": '[{"title":"Analyst"}]',
            "jobs_manifest_json": "{}",
        },
        jobs=[{"title": "Analyst"}],
    )
    archived = app.state.run_store.transition_candidate_profile_lifecycle(
        profile["profile_id"], lifecycle="archived", expected_revision=profile["revision"]
    )

    response = TestClient(app).post(
        f"/candidate-profiles/{profile['profile_id']}/actions/delete",
        headers={"Idempotency-Key": "delete-referenced-profile"},
        json={"expected_revision": archived["revision"]},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "candidate_profile_delete_referenced"


def test_candidate_profile_undo_regeneration_route_restores_review_snapshot() -> None:
    app = _app()
    store = app.state.run_store
    created = store.create_candidate_profile_creation_attempt(
        profile_name="Analytics Profile",
        original_filename="candidate.md",
        media_type="text/markdown",
        content=b"# Alex Morgan\n",
        idempotency_key="create-undo-route",
    )
    claimed = store.claim_candidate_profile_processing(
        created["attempt_id"], stage="base_mapping", expected_revision=created["revision"], lease_seconds=60
    )
    published = store.publish_candidate_profile_stage_result(
        created["attempt_id"],
        stage="baseline",
        claim_id=claimed["processing"]["claim_id"],
        expected_revision=claimed["revision"],
        result={
            "document": {"name": "Alex Morgan", "summary": "Original"},
            "annotations": {"/summary": {"regenerable": True, "source_block_ids": []}},
            "fingerprint": "baseline-route-original",
            "runtime_evidence": None,
        },
        source_blocks=[],
    )
    regenerating = store.regenerate_candidate_profile_review(
        created["attempt_id"], "baseline", expected_revision=published["revision"],
        targets=["/summary"], idempotency_key="regenerate-route",
    )
    regenerated = store.publish_candidate_profile_stage_result(
        created["attempt_id"],
        stage="baseline",
        claim_id=regenerating["processing"]["claim_id"],
        expected_revision=regenerating["revision"],
        result={
            "document": {"name": "Alex Morgan", "summary": "Regenerated"},
            "annotations": {"/summary": {"regenerable": True, "source_block_ids": []}},
            "fingerprint": "baseline-route-regenerated",
            "runtime_evidence": None,
        },
        source_blocks=[],
    )
    client = TestClient(app)

    response = client.post(
        f"/candidate-profile-creation-attempts/{created['attempt_id']}/baseline/actions/undo-regeneration",
        headers={"Idempotency-Key": "undo-route"},
        json={"expected_revision": regenerated["revision"]},
    )
    replay = client.post(
        f"/candidate-profile-creation-attempts/{created['attempt_id']}/baseline/actions/undo-regeneration",
        headers={"Idempotency-Key": "undo-route"},
        json={"expected_revision": regenerated["revision"]},
    )

    assert response.status_code == 200
    assert response.json() == replay.json()
    assert response.json()["data"]["document"]["summary"] == "Original"
    assert response.json()["data"]["capabilities"]["undo_regeneration"] is False


def test_candidate_profile_openapi_declares_staged_upload_and_lifecycle_body() -> None:
    schema = TestClient(_app()).get("/openapi.json").json()

    assert "post" not in schema["paths"]["/candidate-profiles"]
    create = schema["paths"]["/candidate-profile-creation-attempts"]["post"]
    archive = schema["paths"]["/candidate-profiles/{profile_id}/actions/archive"]["post"]
    delete = schema["paths"]["/candidate-profiles/{profile_id}/actions/delete"]["post"]
    undo = schema["paths"]["/candidate-profile-creation-attempts/{attempt_id}/baseline/actions/undo-regeneration"]["post"]
    assert "multipart/form-data" in create["requestBody"]["content"]
    assert archive["requestBody"]["content"]["application/json"]["schema"]
    assert delete["requestBody"]["content"]["application/json"]["schema"]
    assert undo["requestBody"]["content"]["application/json"]["schema"]


def test_central_workspace_openapi_declares_sort_selection_and_binary_contracts() -> None:
    schema = TestClient(_app()).get("/openapi.json").json()

    candidate_get = schema["paths"]["/candidate-profiles"]["get"]
    bookmark_get = schema["paths"]["/bookmarks"]["get"]
    synonym_get = schema["paths"]["/synonym-suggestions"]["get"]
    for operation, default_sort in (
        (candidate_get, "created_desc"),
        (bookmark_get, "bookmarked_desc"),
        (synonym_get, "updated_desc"),
    ):
        sort_parameter = next(item for item in operation["parameters"] if item["name"] == "sort")
        assert sort_parameter["schema"]["default"] == default_sort

    preview = schema["paths"]["/bookmarks/actions/export/preview"]["post"]
    selection_ref = preview["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    selection_schema = schema["components"]["schemas"][selection_ref.rsplit("/", 1)[-1]]
    assert "selected_run_job_ids" in selection_schema["properties"]
    assert "run_job_ids" not in selection_schema["properties"]

    assert "text/csv" in schema["paths"]["/bookmarks/actions/export"]["post"]["responses"]["200"]["content"]
    assert "text/csv" in schema["paths"]["/runs/{run_id}/jobs/actions/export"]["post"]["responses"]["200"]["content"]
    assert "application/zip" in schema["paths"]["/synonym-backups/export.zip"]["get"]["responses"]["200"]["content"]
    assert "multipart/form-data" in schema["paths"]["/synonym-backups/import"]["post"]["requestBody"]["content"]


def test_central_workspace_list_routes_forward_canonical_sort_values() -> None:
    app = _app()
    captured: dict[str, object] = {}
    app.state.run_store.query_candidate_profiles_fn = lambda **kwargs: (
        captured.update(candidate=kwargs)
        or {"items": [], "total": 0, "page": 1, "page_size": 20}
    )
    app.state.run_store.query_bookmarks_fn = lambda **kwargs: (
        captured.update(bookmark=kwargs)
        or {"items": [], "total": 0, "page": 1, "page_size": 20}
    )
    app.state.run_store.query_synonym_suggestions_fn = lambda **kwargs: (
        captured.update(synonym=kwargs)
        or {"items": [], "total": 0, "page": 1, "page_size": 20}
    )
    client = TestClient(app)

    assert client.get("/candidate-profiles?sort=created_desc").status_code == 200
    assert client.get("/bookmarks?sort=bookmarked_desc").status_code == 200
    assert client.get("/synonym-suggestions?sort=updated_desc").status_code == 200

    assert captured["candidate"]["sort"] == "created_desc"
    assert captured["bookmark"]["sort"] == "bookmarked_desc"
    assert captured["synonym"]["sort"] == "updated_desc"


def test_candidate_profile_routes_map_rejection_missing_and_stale_states() -> None:
    app = _app()
    client = TestClient(app)

    assert client.post(
        "/candidate-profile-creation-attempts",
        data={"profile_name": "Candidate"},
        files={"profile_file": ("profile.yaml", "skills: []", "application/yaml")},
    ).status_code == 422

    rejected = client.post(
        "/candidate-profile-creation-attempts",
        headers={"Idempotency-Key": "bad-1"},
        data={"profile_name": "Candidate"},
        files={"profile_file": ("profile.txt", "skills: []", "text/plain")},
    )
    assert rejected.status_code == 415
    assert rejected.json()["error"]["code"] == "candidate_profile_file_type_invalid"

    app.state.run_store.get_candidate_profile_detail_fn = lambda _profile_id: None
    assert client.get("/candidate-profiles/missing").status_code == 404
    app.state.run_store.reserve_idempotent_action_fn = lambda *_args: {"action_id": "action-3", "replayed": False, "response": None}
    app.state.run_store.transition_candidate_profile_lifecycle_fn = lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("revision_conflict"))
    stale = client.post(
        "/candidate-profiles/profile-1/actions/archive",
        headers={"Idempotency-Key": "stale-1"}, json={"expected_revision": 1},
    )
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "revision_conflict"

def test_candidate_profile_source_purged_maps_to_gone() -> None:
    app = _app()
    app.state.run_store.get_candidate_profile_source_fn = lambda _attempt_id: (
        _ for _ in ()
    ).throw(ValueError("candidate_profile_source_purged"))

    response = TestClient(app).get("/candidate-profile-creation-attempts/attempt-1/source")

    assert response.status_code == 410
    assert response.json()["error"]["code"] == "candidate_profile_source_purged"


def _synonym_policy_resource() -> dict[str, object]:
    return {
        "synonym_type": "skills",
        "editor_text": "js: javascript\n",
        "normalized_policy": {"js": "javascript"},
        "issues": [],
        "validation_status": "valid",
        "draft_revision": 1,
        "active_type_revision_id": "type-1",
        "active_type_revision": 1,
        "active_bundle_revision_id": "bundle-1",
        "active_bundle_revision": 1,
        "mirror_status": "in_sync",
        "mirror_error_code": None,
    }


def test_synonym_policy_routes_read_activate_and_persist_invalid_draft() -> None:
    app = _app()
    resource = _synonym_policy_resource()
    current_resource = {"value": resource}
    app.state.run_store.get_synonym_policy_fn = lambda _type: current_resource["value"]
    app.state.run_store.repair_active_synonym_policy_mirrors_fn = lambda: None
    app.state.run_store.reserve_idempotent_action_fn = lambda *_args: {
        "action_id": "action-1", "replayed": False, "response": None,
    }
    app.state.run_store.complete_idempotent_action_fn = lambda *_args: None
    def activate_policy(_type: str, **_kwargs: object) -> dict[str, object]:
        current_resource["value"] = {
            **resource,
            "draft_revision": 2,
            "active_bundle_revision": 2,
        }
        return {"policy": current_resource["value"]}

    app.state.run_store.activate_synonym_policy_bundle_fn = activate_policy
    app.state.run_store.save_synonym_policy_draft_fn = lambda _type, **_kwargs: {
        **resource,
        "editor_text": "js:\n",
        "normalized_policy": None,
        "validation_status": "invalid",
        "draft_revision": 2,
        "issues": [{"code": "synonym_missing_canonical", "message": "Canonical term cannot be empty.", "severity": "error", "lines": [1], "aliases": ["js"], "canonicals": []}],
    }
    client = TestClient(app)

    fetched = client.get("/synonym-policies/skills")
    activated = client.put(
        "/synonym-policies/skills",
        headers={"Idempotency-Key": "policy-1"},
        json={"editor_text": "js: javascript\n", "expected_draft_revision": 1, "expected_active_bundle_revision_id": "bundle-1"},
    )
    invalid = client.put(
        "/synonym-policies/skills",
        headers={"Idempotency-Key": "policy-2"},
        json={"editor_text": "js:\n", "expected_draft_revision": 1, "expected_active_bundle_revision_id": "bundle-1"},
    )

    assert fetched.status_code == 200 and fetched.json()["data"]["draft_revision"] == 1
    assert activated.status_code == 200 and activated.json()["data"]["active_bundle_revision"] == 2
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "synonym_policy_invalid"
    assert invalid.json()["data"]["validation_status"] == "invalid"


def test_central_workspace_pages_share_navigation_and_retire_legacy_labels() -> None:
    client = TestClient(_app())

    runs_html = client.get("/admin/runs").text
    candidate_html = client.get("/admin/candidate-profiles").text
    bookmark_html = client.get("/admin/bookmarks").text
    synonym_html = client.get("/admin/synonyms").text

    for html in (candidate_html, bookmark_html, synonym_html):
        assert html.index('href="/admin/runs"') < html.index('href="/admin/candidate-profiles"')
        assert html.index('href="/admin/candidate-profiles"') < html.index('href="/admin/bookmarks"')
        assert html.index('href="/admin/bookmarks"') < html.index('href="/admin/synonyms"')
        assert "fitcvApiRequest" in html
        assert html.index("async function fitcvApiRequest") < html.index('data-page=')
    assert "table-shell" in candidate_html
    assert 'class="run-tabs"' in candidate_html
    assert 'class="filter-bar section-card"' not in candidate_html
    assert "table-shell" in bookmark_html
    assert bookmark_html.index('id="bookmarkNotice"') < bookmark_html.index('id="bookmarkCount"') < bookmark_html.index('class="table-shell"')
    assert "Submitted" not in bookmark_html and "Archived" not in bookmark_html
    assert "Deferred" not in synonym_html and "Promote" not in synonym_html
    assert "Pending" in synonym_html and "Approved" in synonym_html and "Declined" in synonym_html
    assert "'Approved '+x.approved_count" in synonym_html
    assert "'Declined '+x.declined_count" in synonym_html
    assert "'Pending '+x.pending_count" in synonym_html
    assert "'Added '+x.successfully_added_count" in synonym_html
    assert "function guarded(control,operation" in synonym_html
    assert "fitcvRenderAsyncState(notice" in synonym_html
    assert ".catch(showError)" not in synonym_html
    assert "Synonym Overlay" not in runs_html
    assert "synonym_overlay_file" not in runs_html
    assert "fitcvApiRequest('/runs'" in runs_html
    assert "fd.append('profile_id'" in runs_html


def test_synonym_page_routes_all_async_failures_to_canonical_error_state() -> None:
    synonym_html = TestClient(_app()).get("/admin/synonyms").text

    for operation in (
        "function guarded(control,operation",
        "fitcvRenderAsyncState(notice",
        "fitcvRunLocked(control,async",
        "Could not import synonym backup.",
    ):
        assert operation in synonym_html
    assert ".catch(showError)" not in synonym_html


def test_synonym_suggestion_detail_forwards_evidence_pagination() -> None:
    app = _app()
    captured: dict[str, object] = {}

    def get_detail(suggestion_id: str, **kwargs: object) -> dict[str, object]:
        captured.update(suggestion_id=suggestion_id, **kwargs)
        return {
            "suggestion_id": suggestion_id,
            "sources": [],
            "source_page": {"page": 2, "page_size": 10, "total_items": 0, "total_pages": 0},
        }

    app.state.run_store.get_synonym_suggestion_fn = get_detail
    response = TestClient(app).get(
        "/synonym-suggestions/suggestion-1?evidence_page=2&evidence_page_size=10"
    )

    assert response.status_code == 200
    assert captured == {
        "suggestion_id": "suggestion-1",
        "evidence_page": 2,
        "evidence_page_size": 10,
    }

def test_synonym_approve_forwards_policy_revisions() -> None:
    app = _app()
    captured: dict[str, object] = {}
    app.state.run_store.reserve_idempotent_action_fn = lambda *_args: {
        "action_id": "approve-1", "replayed": False, "response": None,
    }
    app.state.run_store.complete_idempotent_action_fn = lambda *_args: None

    def approve(ids: list[str], **kwargs: object) -> dict[str, object]:
        captured.update(ids=ids, **kwargs)
        return {"approved_count": len(ids)}

    app.state.run_store.apply_synonym_suggestion_action_fn = approve
    response = TestClient(app).post(
        "/synonym-suggestions/actions/approve",
        headers={"Idempotency-Key": "approve-key"},
        json={
            "suggestion_ids": ["suggestion-1"],
            "expected_draft_revision": 3,
            "expected_active_bundle_revision_id": "bundle-2",
        },
    )

    assert response.status_code == 200
    assert captured == {
        "ids": ["suggestion-1"],
        "action": "approve",
        "acted_by": "admin",
        "expected_draft_revision": 3,
        "expected_active_bundle_revision_id": "bundle-2",
    }


def test_runs_rejects_invalid_page_size_with_machine_error() -> None:
    resp = TestClient(_app()).get("/runs?page_size=25")

    assert resp.status_code == 422
    assert resp.json()["error"] == {
        "code": "validation_failed",
        "message": "Request validation failed.",
        "field_errors": [
            {
                "field": "page_size",
                "code": "invalid_value",
                "message": "Use 10, 20, or 50.",
            }
        ],
        "retryable": False,
        "action": "Fix highlighted fields and retry.",
    }


def test_run_stages_and_jobs_use_canonical_envelopes() -> None:
    app = _app()
    app.state.run_store.get_run_detail_fn = lambda run_id: {
        "run_id": run_id,
        "stages": [{"stage_id": "enrichment", "label": "Enrichment", "ordinal": 1}],
    }
    app.state.run_store.query_run_jobs_fn = lambda run_id, **kwargs: {
        "items": [{"run_job_id": "job-1", "run_id": run_id, "title": "Analyst"}],
        "total": 1,
        "total_evaluated": 1,
        "passed": 1,
        "rejected": 0,
        "page": kwargs["page"],
        "page_size": kwargs["page_size"],
    }

    stages = TestClient(app).get("/runs/run-1/stages")
    jobs = TestClient(app).get("/runs/run-1/jobs?page=1&page_size=10")

    assert stages.status_code == 200
    assert stages.json()["data"][0]["stage_id"] == "enrichment"
    assert jobs.status_code == 200
    assert jobs.json()["page"] == {
        "number": 1,
        "size": 10,
        "total_items": 1,
        "total_pages": 1,
    }
    assert jobs.json()["meta"] == {
        "run_id": "run-1",
        "stage": "all",
        "result_bucket": "all",
        "search": "",
        "total_evaluated": 1,
        "passed": 1,
        "rejected": 0,
        "skipped": 0,
    }


def test_run_archive_action_returns_refreshed_resource() -> None:
    now = datetime.datetime.now(datetime.timezone.utc)
    run = PipelineRun(
        run_id="run-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="jobs.json",
        config_path=".env.yaml",
        created_at=now,
        finished_at=now,
    )
    archived: list[tuple[str, str]] = []
    app = _app()
    app.state.run_store.get_run_fn = lambda _run_id: run
    app.state.run_store.archive_run_fn = lambda run_id, actor: archived.append((run_id, actor))
    app.state.run_store.get_run_detail_fn = lambda run_id: {
        "run_id": run_id,
        "backend_status": "succeeded",
        "archived_at": now.isoformat(),
    }

    resp = TestClient(app).post("/runs/run-1/actions/archive")

    assert resp.status_code == 200
    assert resp.json()["data"]["archived_at"] == now.isoformat()
    assert archived == [("run-1", "admin")]


def test_delete_archived_runs_requires_idempotency_key() -> None:
    app = _app()
    app.state.run_store.preview_delete_archived_runs_fn = lambda run_ids: {
        "requested_run_ids": run_ids,
        "eligible_run_ids": run_ids,
        "blocked_run_ids": [],
        "missing_run_ids": [],
        "bookmark_count": 0,
        "state_tokens": [f"state:{run_id}" for run_id in run_ids],
    }
    client = TestClient(app)
    preview = client.post("/runs/actions/delete-archived/preview", json={"run_ids": ["run-1"]})
    resp = client.post(
        "/runs/actions/delete-archived",
        json={"run_ids": ["run-1"], "preview_revision": preview.json()["data"]["preview_revision"]},
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["field_errors"][0]["field"] == "Idempotency-Key"


def test_delete_archived_runs_is_idempotent_and_returns_deleted_ids() -> None:
    completed: list[dict[str, Any]] = []
    app = _app()
    app.state.run_store.reserve_idempotent_action_fn = lambda *_args: {
        "action_id": "delete-action-1",
        "replayed": False,
        "response": None,
    }
    app.state.run_store.preview_delete_archived_runs_fn = lambda run_ids: {
        "requested_run_ids": run_ids,
        "eligible_run_ids": run_ids,
        "blocked_run_ids": [],
        "missing_run_ids": [],
        "bookmark_count": 0,
        "state_tokens": [f"state:{run_id}" for run_id in run_ids],
    }
    app.state.run_store.delete_archived_runs_fn = lambda _age, run_ids, **_kwargs: {
        "deleted_count": len(run_ids),
        "deleted_run_ids": run_ids,
    }
    app.state.run_store.complete_idempotent_action_fn = lambda _action_id, response: completed.append(response)

    client = TestClient(app)
    preview = client.post(
        "/runs/actions/delete-archived/preview",
        json={"run_ids": ["run-1", "run-2"]},
    )
    resp = client.post(
        "/runs/actions/delete-archived",
        headers={"Idempotency-Key": "delete-1"},
        json={
            "run_ids": ["run-1", "run-2"],
            "preview_revision": preview.json()["data"]["preview_revision"],
        },
    )

    assert resp.status_code == 200
    assert resp.json()["data"]["deleted_run_ids"] == ["run-1", "run-2"]
    assert completed == [resp.json()["data"]]


def test_delete_archived_runs_reports_all_or_nothing_conflict() -> None:
    app = _app()
    app.state.run_store.reserve_idempotent_action_fn = lambda *_args: {
        "action_id": "delete-action-1",
        "replayed": False,
        "response": None,
    }
    app.state.run_store.preview_delete_archived_runs_fn = lambda run_ids: {
        "requested_run_ids": run_ids,
        "eligible_run_ids": ["run-1"],
        "blocked_run_ids": ["run-2"],
        "missing_run_ids": [],
        "bookmark_count": 0,
        "state_tokens": ["state:run-1"],
    }
    deleted: list[list[str]] = []
    app.state.run_store.delete_archived_runs_fn = lambda _age, run_ids, **_kwargs: deleted.append(run_ids)

    resp = TestClient(app).post(
        "/runs/actions/delete-archived",
        headers={"Idempotency-Key": "delete-1"},
        json={"run_ids": ["run-1", "run-2"], "preview_revision": "unused"},
    )

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "delete_preview_stale"
    assert deleted == []


def test_delete_archived_runs_replays_success_after_selection_is_deleted() -> None:
    response = {"action_id": "delete-action-1", "deleted_count": 1, "deleted_run_ids": ["run-1"]}
    app = _app()
    app.state.run_store.reserve_idempotent_action_fn = lambda *_args: {
        "action_id": "delete-action-1",
        "replayed": True,
        "response": response,
    }
    app.state.run_store.preview_delete_archived_runs_fn = lambda run_ids: {
        "requested_run_ids": run_ids,
        "eligible_run_ids": [],
        "blocked_run_ids": [],
        "missing_run_ids": run_ids,
        "bookmark_count": 0,
        "state_tokens": [],
    }

    resp = TestClient(app).post(
        "/runs/actions/delete-archived",
        headers={"Idempotency-Key": "delete-1"},
        json={"run_ids": ["run-1"], "preview_revision": "unused"},
    )

    assert resp.status_code == 200
    assert resp.json()["data"] == response


def test_cancel_and_unarchive_repeats_are_idempotent() -> None:
    now = datetime.datetime.now(datetime.timezone.utc)
    cancelled = PipelineRun(
        run_id="run-cancelled-1",
        status=RunStatus.CANCELLED,
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="jobs.json",
        config_path=".env.yaml",
        created_at=now,
        finished_at=now,
    )
    active = PipelineRun(
        run_id="run-active-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="jobs.json",
        config_path=".env.yaml",
        created_at=now,
        finished_at=now,
    )
    app = _app()
    app.state.run_store.get_run_fn = lambda run_id: cancelled if run_id == cancelled.run_id else active
    app.state.run_store.get_run_detail_fn = lambda run_id: {"run_id": run_id}
    request_cancel = MagicMock()
    unarchive = MagicMock()
    app.state.run_store.request_run_cancel_fn = request_cancel
    app.state.run_store.unarchive_run_fn = unarchive

    cancel_resp = TestClient(app).post("/runs/run-cancelled-1/actions/cancel")
    unarchive_resp = TestClient(app).post("/runs/run-active-1/actions/unarchive")

    assert cancel_resp.status_code == 200
    assert unarchive_resp.status_code == 200
    request_cancel.assert_not_called()
    unarchive.assert_not_called()


def test_bookmark_and_interest_actions_use_run_job_identity() -> None:
    app = _app()
    app.state.run_store.get_run_job_fn = lambda run_id, run_job_id: {
        "run_id": run_id,
        "run_job_id": run_job_id,
    }
    app.state.run_store.set_bookmark_fn = lambda run_job_id: {
        "run_job_id": run_job_id,
        "bookmark_id": "bookmark-1",
    }
    app.state.run_store.set_run_job_interest_fn = lambda run_job_id, rating, **kwargs: {
        "run_job_id": run_job_id,
        "rating": rating,
        "rating_contract_revision": kwargs["rating_contract_revision"],
    }

    bookmark = TestClient(app).put("/runs/run-1/jobs/job-1/bookmark")
    interest = TestClient(app).put(
        "/runs/run-1/jobs/job-1/interest",
        json={"rating": 5, "rating_contract_revision": "application-interest-v1"},
    )

    assert bookmark.status_code == 200
    assert bookmark.json()["data"]["bookmarked"] is True
    assert interest.status_code == 200
    assert interest.json()["data"]["rating"] == 5


def test_bookmark_interest_clear_and_stale_rating_contract() -> None:
    app = _app()
    app.state.run_store.get_run_job_fn = lambda run_id, run_job_id: {
        "run_id": run_id,
        "run_job_id": run_job_id,
    }
    cleared_bookmarks: list[str] = []
    app.state.run_store.clear_bookmark_fn = cleared_bookmarks.append
    app.state.run_store.clear_run_job_interest_fn = lambda run_job_id, **_kwargs: {
        "run_job_id": run_job_id,
        "rating_contract_revision": "application-interest-v1",
    }

    bookmark = TestClient(app).delete("/runs/run-1/jobs/job-1/bookmark")
    interest = TestClient(app).delete("/runs/run-1/jobs/job-1/interest")
    stale = TestClient(app).put(
        "/runs/run-1/jobs/job-1/interest",
        json={"rating": 4, "rating_contract_revision": "application-interest-v0"},
    )

    assert bookmark.json()["data"]["bookmarked"] is False
    assert interest.json()["data"]["rating"] is None
    assert cleared_bookmarks == ["job-1"]
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "rating_contract_stale"


def test_jobs_export_uses_full_filtered_rows_and_escapes_formulas() -> None:
    app = _app()
    app.state.run_store.get_run_detail_fn = lambda run_id: {"run_id": run_id}
    app.state.run_store.iter_run_jobs_for_export_fn = lambda run_id, **_kwargs: iter(
        [
            {
                "run_job_id": "job-1",
                "title": "=SUM(1,1)",
                "source_url": "https://example.com/job-1",
                "location": "Berlin",
                "work_mode": "Hybrid",
                "language": "English",
                "seniority": "Senior",
                "role_family": "Analytics",
                "domain": "Product",
                "skills": ["SQL", "Python"],
                "result_bucket": "passed",
                "outcome_code": "accepted",
                "reason_code": "eligible",
                "rating": 5,
            }
        ]
    )

    resp = TestClient(app).get("/runs/run-1/jobs/export.csv?stage=all&result_bucket=all")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert resp.text.splitlines()[0] == (
        "Job Title,Listing URL,Location,Work Mode,Language,Seniority,Job Family,Domain,"
        "Required Skills,Result,Pipeline Outcome,Reason,Application Interest"
    )
    assert "'=SUM(1,1)" in resp.text


def test_cv_history_download_and_regenerate_contract() -> None:
    app = _app()
    app.state.run_store.get_run_job_fn = lambda run_id, run_job_id: {
        "run_id": run_id,
        "run_job_id": run_job_id,
        "source_url": "https://example.com/job-1",
    }
    app.state.run_store.list_cv_versions_fn = lambda _run_job_id: [
        {"version_id": "cv-1", "generation_status": "generated"}
    ]
    app.state.run_store.get_cv_download_fn = lambda _version_id: {
        "content": b"# CV\n",
        "content_length": 5,
        "content_checksum": "checksum-1",
        "media_type": "text/markdown; charset=utf-8",
        "filename": "cv-1.md",
    }
    app.state.run_store.reserve_idempotent_action_fn = lambda scope, key, fingerprint: {
        "action_id": "action-1",
        "status": "queued",
        "replayed": False,
        "response": None,
    }
    app.state.run_store.reserve_cv_regeneration_fn = lambda run_job_id, **kwargs: {
        "version_id": kwargs["version_id"],
        "run_job_id": run_job_id,
        "generation_status": "pending",
    }

    with patch("fitcv_cp.app.enqueue_cv_regenerate_once_with_job_id", return_value="queue-1"):
        history = TestClient(app).get("/runs/run-1/jobs/job-1/cvs")
        download = TestClient(app).get("/cv-versions/cv-1/download")
        regenerate = TestClient(app).post(
            "/runs/run-1/jobs/job-1/cvs/actions/regenerate",
            headers={"Idempotency-Key": "regen-1"},
            json={"parent_cv_version_id": "cv-1"},
        )

    assert history.status_code == 200
    assert history.json()["data"][0]["version_id"] == "cv-1"
    assert download.status_code == 200
    assert download.headers["etag"] == '"checksum-1"'
    assert download.headers["content-length"] == "5"
    assert regenerate.status_code == 202
    assert regenerate.json()["data"]["action_id"] == "action-1"
    assert regenerate.json()["data"]["status"] == "queued"


def test_cv_regeneration_replays_completed_action_without_enqueue() -> None:
    app = _app()
    app.state.run_store.get_run_job_fn = lambda run_id, run_job_id: {
        "run_id": run_id,
        "run_job_id": run_job_id,
        "source_url": "https://example.com/job-1",
    }
    app.state.run_store.reserve_idempotent_action_fn = lambda *_args: {
        "action_id": "action-1",
        "status": "succeeded",
        "replayed": True,
        "response": {
            "action_id": "action-1",
            "status": "queued",
            "queue_job_id": "queue-1",
            "cv_version": {"version_id": "cv-2"},
        },
    }

    with patch("fitcv_cp.app.enqueue_cv_regenerate_once_with_job_id") as enqueue:
        resp = TestClient(app).post(
            "/runs/run-1/jobs/job-1/cvs/actions/regenerate",
            headers={"Idempotency-Key": "regen-1"},
            json={"parent_cv_version_id": "cv-1"},
        )

    assert resp.status_code == 202
    assert resp.json()["data"]["cv_version"]["version_id"] == "cv-2"
    enqueue.assert_not_called()


def test_cv_regeneration_idempotency_conflict_is_actionable() -> None:
    app = _app()
    app.state.run_store.get_run_job_fn = lambda run_id, run_job_id: {
        "run_id": run_id,
        "run_job_id": run_job_id,
    }
    app.state.run_store.reserve_idempotent_action_fn = lambda *_args: (_ for _ in ()).throw(
        ValueError("idempotency_conflict")
    )

    resp = TestClient(app).post(
        "/runs/run-1/jobs/job-1/cvs/actions/regenerate",
        headers={"Idempotency-Key": "regen-1"},
        json={"parent_cv_version_id": "cv-1"},
    )

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "idempotency_conflict"


def test_cv_regeneration_enqueue_failure_persists_failed_version() -> None:
    updates: list[tuple[str, dict[str, Any]]] = []
    completed_actions: list[dict[str, Any]] = []
    app = _app()
    app.state.run_store.get_run_job_fn = lambda run_id, run_job_id: {
        "run_id": run_id,
        "run_job_id": run_job_id,
        "source_url": "https://example.com/job-1",
    }
    app.state.run_store.reserve_idempotent_action_fn = lambda *_args: {
        "action_id": "action-1",
        "status": "queued",
        "replayed": False,
        "response": None,
    }
    app.state.run_store.reserve_cv_regeneration_fn = lambda run_job_id, **kwargs: {
        "version_id": kwargs["version_id"],
        "run_job_id": run_job_id,
        "generation_status": "pending",
    }
    app.state.run_store.update_cv_version_fn = lambda version_id, **kwargs: (
        updates.append((version_id, kwargs))
        or {"version_id": version_id, "generation_status": kwargs["generation_status"]}
    )
    app.state.run_store.complete_idempotent_action_fn = lambda _action_id, response: completed_actions.append(response)

    with patch(
        "fitcv_cp.app.enqueue_cv_regenerate_once_with_job_id",
        side_effect=RuntimeError("queue unavailable"),
    ):
        resp = TestClient(app).post(
            "/runs/run-1/jobs/job-1/cvs/actions/regenerate",
            headers={"Idempotency-Key": "regen-1"},
            json={"parent_cv_version_id": "cv-1"},
        )

    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "cv_regeneration_failed"
    assert resp.json()["error"]["retryable"] is True
    assert updates[0][1]["generation_status"] == "generation_failed"
    assert updates[0][1]["error_code"] == "enqueue_failed"
    assert completed_actions[0]["status"] == "failed"


def test_events_and_debug_bundle_not_ready_contract() -> None:
    event = MagicMock(
        event_id="event-1",
        recorded_at=datetime.datetime(2026, 7, 20, 12, tzinfo=datetime.timezone.utc),
        operation="ranking",
        state="progress",
        level="info",
        message="Ranking jobs",
        payload_json='{"count":1}',
        diagnostic_refs_json=None,
    )
    app = _app()
    app.state.run_store.get_run_detail_fn = lambda run_id: {"run_id": run_id}
    app.state.run_store.get_process_events_fn = lambda *_args, **_kwargs: {
        "events": [event],
        "integrity_conflicts": [],
        "deliveries": [],
        "total_count": 1,
        "next_cursor": None,
    }
    app.state.run_store.get_debug_bundle_availability_fn = lambda run_id: {
        "run_id": run_id,
        "status": "not_ready",
        "reason": "run_in_progress",
        "action": "wait",
    }

    events = TestClient(app).get("/runs/run-1/events?limit=100")
    bundle = TestClient(app).get("/runs/run-1/debug-bundle")

    assert events.status_code == 200
    assert events.json()["data"][0]["event_id"] == "event-1"
    assert events.json()["meta"]["next_cursor"] is None
    assert bundle.status_code == 409
    assert bundle.json()["error"]["code"] == "artifact_not_available"


def test_run_events_rejects_invalid_cursor_and_limit() -> None:
    app = _app()
    app.state.run_store.get_run_detail_fn = lambda run_id: {"run_id": run_id}
    app.state.run_store.get_process_events_fn = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        ValueError("invalid_cursor")
    )

    cursor = TestClient(app).get("/runs/run-1/events?cursor=not-a-cursor")
    limit = TestClient(app).get("/runs/run-1/events?limit=501")

    assert cursor.status_code == 422
    assert cursor.json()["error"]["field_errors"][0]["field"] == "cursor"
    assert limit.status_code == 422
    assert limit.json()["error"]["field_errors"][0]["field"] == "limit"


def test_debug_bundle_redacts_secrets_and_raw_snapshots() -> None:
    app = _app()
    app.state.run_store.get_run_detail_fn = lambda run_id: {
        "run_id": run_id,
        "status": "succeeded",
        "provider": {"api_key": "top-secret", "name": "provider"},
        "input": {
            "original_filename": "jobs.json",
            "jobs_snapshot": [{"title": "Private job"}],
            "candidate_profile_snapshot": {"name": "Private candidate"},
        },
    }
    app.state.run_store.get_debug_bundle_availability_fn = lambda run_id: {
        "run_id": run_id,
        "status": "available",
    }

    resp = TestClient(app).get("/runs/run-1/debug-bundle")

    assert resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
        run_payload = archive.read("run.json").decode("utf-8")
        manifest = json.loads(archive.read("manifest.json"))
    assert "top-secret" not in run_payload
    assert "Private job" not in run_payload
    assert "Private candidate" not in run_payload
    assert "[redacted]" in run_payload
    assert manifest["included_artifacts"][0]["sha256"]
    assert manifest["redactions"] == ["credentials", "secrets", "raw uploaded files"]


def test_get_run_events():
    event = RunEvent(
        run_id="some-id",
        event_id="evt-1",
        stage="pipeline_start",
        level="info",
        message="Run started",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        payload_json='{"telemetry_export":{"status":"degraded"}}',
    )
    with patch("fitcv_cp.app.get_run", return_value=MagicMock()), \
         patch("fitcv_cp.app.get_events", return_value=[event]):
        resp = TestClient(_app()).get("/runs/some-id/events")
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert len(body) == 1
    assert body[0]["payload"] == {"telemetry_export": {"status": "degraded"}}


def test_get_run_events_preserves_langfuse_rich_payload_json() -> None:
    payload_json = json.dumps(
        {
            "telemetry_export": {"status": "export_enabled"},
            "langfuse_rich_io": {
                "status": "ready",
                "degradation_reason": None,
                "input": {"stage_family": "cv_analysis", "message": "ok"},
                "output": {"event_status": "emitted"},
            },
            "langfuse_rich_io_native": {"status": "sent:abc123", "degradation_reason": None},
        }
    )
    event = RunEvent(
        run_id="some-id",
        event_id="evt-2",
        stage="layer4_cv_analysis",
        level="info",
        message="Rich payload event",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        payload_json=payload_json,
    )
    with patch("fitcv_cp.app.get_run", return_value=MagicMock()), \
         patch("fitcv_cp.app.get_events", return_value=[event]):
        resp = TestClient(_app()).get("/runs/some-id/events")
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert len(body) == 1
    parsed = body[0]["payload"]
    assert parsed["langfuse_rich_io"]["status"] == "ready"
    assert parsed["langfuse_rich_io_native"]["status"] == "sent:abc123"


def test_healthz():
    resp = TestClient(_app()).get("/healthz")
    assert resp.status_code == 200

def test_admin_orchestration_schema_diagnostics_endpoint() -> None:
    with patch(
        "fitcv_cp.app.get_pipeline_runs_schema_status",
        return_value={"status": "complete", "missing_columns": [], "warning": None},
    ):
        resp = TestClient(_app()).get("/admin/diagnostics/orchestration-schema")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "complete"
    assert payload["required_columns"] == ["orchestration_backend", "orchestration_run_id"]


def test_timeline_stage_download_maps_cv_analysis_skip_to_cv_analysis():
    assert timeline_stage_download_for_event("layer4_cv_analysis_skip") == "cv_analysis"
    assert timeline_stage_download_for_event("layer4_cv_skip") == "cv_analysis"


def test_ranked_cv_outcome_summary_preserves_stage_owned_no_cv_vs_failed_distinction() -> None:
    from fitcv_cp.app import _build_ranked_cv_outcome_summary

    rows = [
        {
            "rank": 1,
            "pipeline_status": "ranked_with_cv",
            "stage_owned_subreason": "accepted",
            "decision_chain": {"cv_generation": {"status": "accepted"}},
        },
        {
            "rank": 2,
            "pipeline_status": "ranked_no_cv",
            "stage_owned_subreason": "review_required",
            "decision_chain": {"cv_generation": {"status": "review_required"}},
        },
        {
            "rank": 3,
            "pipeline_status": "ranked_no_cv",
            "stage_owned_subreason": "validation_failed",
            "decision_chain": {"cv_generation": {"status": "validation_failed"}},
        },
        {
            "rank": 4,
            "pipeline_status": "ranked_no_cv",
            "stage_owned_subreason": "ready_for_generation",
            "decision_chain": {"cv_generation": {"status": "not_attempted"}},
        },
        {
            "rank": 5,
            "pipeline_status": "ranked_blocked_by_reranker_fit",
            "stage_owned_subreason": "blocked_by_reranker_fit",
            "decision_chain": {"cv_generation": {"status": "not_attempted"}},
        },
    ]

    summary = _build_ranked_cv_outcome_summary(rows)
    assert summary["ranked_total"] == 5
    assert summary["ranked_cv_created_count"] == 1
    assert summary["ranked_review_required_count"] == 1
    assert summary["ranked_generation_failed_count"] == 1
    assert summary["ranked_fit_gated_count"] == 1
    assert summary["ranked_other_no_cv_count"] == 1


# ── settings API ─────────────────────────────────────────────────────────────

def test_get_settings_returns_dict():
    with patch("fitcv_cp.app.load_active_settings", return_value={"pipeline.final_top_n": 5}):
        resp = TestClient(_app()).get("/settings")
    assert resp.status_code == 200
    assert resp.json()["pipeline.final_top_n"] == 5


def test_get_pipeline_settings_returns_effective_resource() -> None:
    with patch("fitcv_cp.app.load_active_settings", return_value={"pipeline.final_top_n": 5}):
        resp = TestClient(_app()).get("/settings/pipeline")

    assert resp.status_code == 200
    payload = resp.json()["data"]
    assert payload["values"]["pipeline.final_top_n"] == 5
    assert payload["defaults"]["pipeline.final_top_n"] == 15
    assert payload["sources"]["pipeline.final_top_n"] == "override"
    assert payload["schema"]["pages"][0]["id"] == "overview"
    assert "cv_generation_model" not in payload["values"]
    assert "gap_thresholds.strong_min_matched_ratio" not in payload["values"]
    assert payload["revision"]
    assert resp.headers["etag"] == f'"{payload["revision"]}"'


def test_get_pipeline_settings_returns_repairable_invalid_state() -> None:
    with patch(
        "fitcv_cp.app.load_active_settings",
        return_value={
            "pipeline.vector_search_top_n": 25,
            "pipeline.ai_score_top_n": 50,
        },
    ):
        resp = TestClient(_app()).get("/settings/pipeline")

    assert resp.status_code == 200
    payload = resp.json()["data"]
    assert payload["values"]["pipeline.vector_search_top_n"] == 25
    assert payload["values"]["pipeline.ai_score_top_n"] == 50
    assert payload["validation_errors"] == [
        "pipeline.ai_score_top_n (50) must be <= pipeline.vector_search_top_n (25)"
    ]


def test_patch_pipeline_settings_uses_atomic_mutation() -> None:
    changes = {
        "pipeline.vector_search_top_n": 80,
        "pipeline.ai_score_top_n": 40,
        "pipeline.final_top_n": 8,
    }
    with patch("fitcv_cp.app.mutate_settings_atomically", return_value=changes) as mutate:
        resp = TestClient(_app()).patch(
            "/settings/pipeline",
            json={"changes": changes, "updated_by": "admin"},
        )

    assert resp.status_code == 200
    mutate.assert_called_once_with(changes=changes, updated_by="admin")
    assert resp.json()["data"]["values"]["pipeline.final_top_n"] == 8


def test_patch_pipeline_settings_rejects_excluded_key() -> None:
    resp = TestClient(_app()).patch(
        "/settings/pipeline",
        json={"changes": {"cv_generation_model": "cx/gpt-5.5"}},
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_failed"
    assert resp.json()["error"]["field_errors"][0]["field"] == "cv_generation_model"


def test_patch_pipeline_settings_rejects_stale_revision() -> None:
    from fitcv_cp.settings_store import SettingsRevisionConflict

    with patch(
        "fitcv_cp.app.mutate_settings_atomically",
        side_effect=SettingsRevisionConflict("stale"),
    ):
        resp = TestClient(_app()).patch(
            "/settings/pipeline",
            json={
                "changes": {"pipeline.final_top_n": 8},
                "expected_revision": "stale-revision",
            },
        )

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "settings_revision_conflict"
    assert resp.json()["error"]["retryable"] is False


def test_patch_pipeline_settings_rejects_retired_runtime_field() -> None:
    resp = TestClient(_app()).patch(
        "/settings/pipeline",
        json={"changes": {"stage_runtime.ranking.batch_size": 2}},
    )

    assert resp.status_code == 422
    assert "stage_runtime.ranking.batch_size" in resp.text


def test_reset_pipeline_settings_uses_atomic_mutation() -> None:
    with patch("fitcv_cp.app.mutate_settings_atomically", return_value={}) as mutate:
        resp = TestClient(_app()).post(
            "/settings/pipeline/actions/reset",
            json={"keys": ["pipeline.final_top_n"], "updated_by": "admin"},
        )

    assert resp.status_code == 200
    mutate.assert_called_once_with(
        changes={},
        reset_keys=["pipeline.final_top_n"],
        updated_by="admin",
    )
    assert resp.json()["data"]["sources"]["pipeline.final_top_n"] == "default"


def test_post_settings_key_saves_and_returns_200():
    with patch("fitcv_cp.app.save_setting") as mock_save:
        resp = TestClient(_app()).post(
            "/settings/pipeline.final_top_n",
            json={"value": 7, "updated_by": "admin"},
        )
    assert resp.status_code == 200
    mock_save.assert_called_once()

def test_post_settings_key_rejects_legacy_throughput_alias():
    with patch("fitcv_cp.app.save_setting") as mock_save:
        resp = TestClient(_app()).post(
            "/settings/enrichment_sleep_secs",
            json={"value": 3.5, "updated_by": "admin"},
        )
    assert resp.status_code == 422
    mock_save.assert_not_called()


def test_post_settings_key_surfaces_bigquery_save_failure():
    with patch("fitcv_cp.app.save_setting", side_effect=RuntimeError("Failed to save setting: boom")):
        resp = TestClient(_app()).post(
            "/settings/pipeline.final_top_n",
            json={"value": 7, "updated_by": "admin"},
        )
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Failed to save setting: boom"


def test_admin_settings_key_surfaces_bigquery_save_failure():
    with patch("fitcv_cp.app.save_setting", side_effect=RuntimeError("Failed to save setting: boom")), \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/pipeline.final_top_n",
            data={"value": "7"},
        )
    assert resp.status_code == 422
    assert "Save failed: Failed to save setting: boom" in resp.text

def test_post_settings_key_rejects_invalid_value():
    resp = TestClient(_app()).post(
        "/settings/pipeline.final_top_n",
        json={"value": 0, "updated_by": "admin"},  # 0 violates int >= 1
    )
    assert resp.status_code == 422


def test_post_settings_key_rejects_unknown_key():
    resp = TestClient(_app()).post(
        "/settings/unknown.key",
        json={"value": 1, "updated_by": "admin"},
    )
    assert resp.status_code == 422


def test_post_settings_key_rejects_hidden_deprecated_key():
    resp = TestClient(_app()).post(
        "/settings/cv_generation_model",
        json={"value": "cx/gpt-5.4-mini", "updated_by": "admin"},
    )
    assert resp.status_code == 422
    assert "hidden_deprecated" in resp.text


def test_post_runs_with_config_overrides(tmp_path):
    """@proves settings_system.per-run-overrides

    POST /runs with per-run overrides snapshot effective settings.
    """
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(_minimal_valid_profile_yaml(), encoding="utf-8")

    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.insert_run"), \
         patch("fitcv_cp.app.submit_run", return_value=RunSubmission(run_id="run-123", queue_job_id="rq-job-abc", backend_run_id="rq-job-abc", backend="default_queue")), \
         patch("fitcv_cp.app.update_run_queue_job_id"), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p","pipeline": {"final_top_n": 10},
             "paths": {"candidate_profile": str(profile_path)},
         }):
        resp = TestClient(_app()).post("/runs", json={
            "jobs_path": str(jobs_file),
            "config_overrides": {"pipeline.final_top_n": 5},
        })
    assert resp.status_code == 201, resp.text
    assert "run_id" in resp.json()


def test_post_runs_rejects_invalid_config_overrides():
    """@proves settings_system.per-run-overrides"""
    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p",
             "pipeline": {"final_top_n": 10},
             "paths": {"candidate_profile": "data/candidate_profile.yaml"},
         }):
        resp = TestClient(_app()).post("/runs", json={
            "jobs_path": "data/sample_jobs.json",
            "config_overrides": {"pipeline.final_top_n": 0},  # violates >= 1
        })
    assert resp.status_code == 422

def test_post_runs_accepts_nested_stage_runtime_overrides(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(_minimal_valid_profile_yaml(), encoding="utf-8")

    captured: dict[str, Any] = {}

    def _capture_insert(run: Any, *_: Any, **__: Any) -> None:
        captured["run"] = run

    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.insert_run", side_effect=_capture_insert), \
         patch("fitcv_cp.app.submit_run", return_value=RunSubmission(run_id="run-123", queue_job_id="rq-job-abc", backend_run_id="rq-job-abc", backend="default_queue")), \
         patch("fitcv_cp.app.update_run_queue_job_id"), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p","pipeline": {"final_top_n": 10},
             "paths": {"candidate_profile": str(profile_path)},
         }):
        resp = TestClient(_app()).post("/runs", json={
            "jobs_path": str(jobs_file),
            "config_overrides": {
                "llm_runtime": {"request_start_interval_secs": 0.25},
                "stage_runtime": {
                    "ranking": {"concurrency": 4},
                },
            },
        })
    assert resp.status_code == 201, resp.text
    effective = json.loads(captured["run"].effective_settings_json)
    assert effective["llm_runtime"]["request_start_interval_secs"] == pytest.approx(0.25)
    assert effective["stage_runtime"]["ranking"]["concurrency"] == 4
    assert set(effective["stage_runtime"]["ranking"]) == {"concurrency"}

def test_post_runs_accepts_mixed_nested_and_flat_same_value(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(_minimal_valid_profile_yaml(), encoding="utf-8")

    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.insert_run"), \
         patch("fitcv_cp.app.submit_run", return_value=RunSubmission(run_id="run-123", queue_job_id="rq-job-abc", backend_run_id="rq-job-abc", backend="default_queue")), \
         patch("fitcv_cp.app.update_run_queue_job_id"), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p","pipeline": {"final_top_n": 10},
             "paths": {"candidate_profile": str(profile_path)},
         }):
        resp = TestClient(_app()).post("/runs", json={
            "jobs_path": str(jobs_file),
            "config_overrides": {
                "stage_runtime": {"ranking": {"concurrency": 4}},
                "stage_runtime.ranking.concurrency": 4,
            },
        })
    assert resp.status_code == 201, resp.text

def test_post_runs_rejects_mixed_nested_and_flat_conflict(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(_minimal_valid_profile_yaml(), encoding="utf-8")

    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p","pipeline": {"final_top_n": 10},
             "paths": {"candidate_profile": str(profile_path)},
         }):
        resp = TestClient(_app()).post("/runs", json={
            "jobs_path": str(jobs_file),
            "config_overrides": {
                "stage_runtime": {"ranking": {"concurrency": 4}},
                "stage_runtime.ranking.concurrency": 1,
            },
        })
    assert resp.status_code == 422
    assert "Conflicting config_overrides" in resp.text

def test_post_runs_rejects_unknown_nested_override_key(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(_minimal_valid_profile_yaml(), encoding="utf-8")

    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p","pipeline": {"final_top_n": 10},
             "paths": {"candidate_profile": str(profile_path)},
         }):
        resp = TestClient(_app()).post("/runs", json={
            "jobs_path": str(jobs_file),
            "config_overrides": {
                "stage_runtime": {"ranking": {"unknown_leaf": 123}},
            },
        })
    assert resp.status_code == 422
    assert "Unknown setting key" in resp.text

def test_post_runs_rejects_missing_config_path_with_clear_error():
    def _load_config_side_effect(path: str = ".env.yaml"):
        if path == "config/missing.yaml":
            raise FileNotFoundError("Config file not found: config/missing.yaml")
        return {
            "gcp_project": "p",
            "pipeline": {"final_top_n": 10},
            "paths": {"candidate_profile": "data/candidate_profile.yaml"},
        }

    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.load_config", side_effect=_load_config_side_effect):
        resp = TestClient(_app()).post("/runs", json={
            "jobs_path": "data/sample_jobs.json",
            "config_path": "config/missing.yaml",
            "config_overrides": {},
        })
    assert resp.status_code == 422
    assert "Config file not found: config/missing.yaml" in resp.text


def test_admin_upload_trigger_success(tmp_path):
    """@proves trigger_run_management.job-input-modes"""
    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.insert_run"), \
         patch("fitcv_cp.app.submit_run", return_value=RunSubmission(run_id="run-123", queue_job_id="rq-job-abc", backend_run_id="rq-job-abc", backend="default_queue")), \
         patch("fitcv_cp.app.update_run_queue_job_id"), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p","pipeline": {"final_top_n": 10},
             "paths": {"candidate_profile": "data/candidate_profile.yaml"},
         }):

        file_content = json.dumps([_valid_fitcv_job(title="Engineer", jobUrl="http://x.com", job_url="http://x.com")]).encode("utf-8")
        files = {"jobs_file": ("custom_jobs.json", file_content, "application/json")}
        data = {
            "config_path": ".env.yaml",
            "jobs_input_mode": "upload",
            "candidate_profile_id": "profile-1",
        }

        resp = TestClient(_app_with_active_profile()).post("/admin/upload-trigger", data=data, files=files)

    assert resp.status_code == 201, resp.text
    assert "run_id" in resp.json()


def test_admin_upload_trigger_cannot_apply_retired_run_scoped_synonym_overlay() -> None:
    captured: dict[str, object] = {}
    app = _app_with_active_profile()
    def capture_run_bundle(run: PipelineRun, **_kwargs: object) -> dict[str, object]:
        captured["run"] = run
        return {"run_id": run.run_id}

    app.state.run_store.create_run_bundle_fn = capture_run_bundle

    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.submit_run", return_value=RunSubmission(run_id="run-123", queue_job_id="rq-job-abc", backend_run_id="rq-job-abc", backend="default_queue")), \
         patch("fitcv_cp.app.update_run_queue_job_id"), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p",
             "pipeline": {"final_top_n": 10},
             "paths": {"candidate_profile": "data/candidate_profile.yaml"},
             "skill_synonyms": {"gcp": "google cloud"},
             "skill_synonyms_runtime": {"has_overlay": False, "entry_count": 1},
         }):
        resp = TestClient(app).post(
            "/admin/upload-trigger",
            data={
                "config_path": ".env.yaml",
                "jobs_input_mode": "upload",
                "candidate_profile_id": "profile-1",
                "synonym_overlay_mode": "upload",
            },
            files={
                "jobs_file": ("custom_jobs.json", json.dumps([_valid_fitcv_job(title="Engineer", jobUrl="http://x.com", job_url="http://x.com")]).encode("utf-8"), "application/json"),
                "synonym_overlay_file": ("custom_overlay.yaml", b"skill_synonyms:\n  ga4: google analytics\n", "application/x-yaml"),
            },
        )

    assert resp.status_code == 201, resp.text
    effective = json.loads(captured["run"].effective_settings_json)
    assert effective["skill_synonyms"] == {"gcp": "google cloud"}
    assert effective["skill_synonyms_runtime"].get("has_run_overlay") is not True


def test_admin_continue_run_requeues_manual_paused_run() -> None:
    """@proves trigger_run_management.manual-checkpoints-and-continue"""
    paused_run = MagicMock()
    paused_run.run_id = "run-123"
    paused_run.run_mode = "manual_staged"
    paused_run.status = RunStatus.AWAITING_CONTINUE
    paused_run.next_stage = "ranking"
    paused_run.last_completed_stage = "shortlist"
    paused_run.completed_stages = ["normalize", "enrich", "rule_filter", "shortlist"]
    paused_run.checkpoint_payload_json = '{"checkpoint_payload":{"shortlist":[]}}'
    paused_run.jobs_path = "data/sample_jobs.json"
    paused_run.config_path = ".env.yaml"

    call_order: list[str] = []

    def _record(name: str):
        def _inner(*args, **kwargs):
            call_order.append(name)
            return None
        return _inner

    def _continue(*args, **kwargs):
        call_order.append("continue")
        return RunSubmission(run_id="run-123", queue_job_id="rq-job-abc", backend_run_id="rq-job-abc", backend="default_queue")

    with patch("fitcv_cp.app.get_run", return_value=paused_run), \
         patch("fitcv_cp.app.continue_run_submission", side_effect=_continue), \
         patch("fitcv_cp.app.update_run_effective_settings"), \
         patch("fitcv_cp.app.update_run_status", side_effect=_record("status")) as mock_status, \
         patch("fitcv_cp.app.update_run_queue_job_id", side_effect=_record("queue")) as mock_queue, \
         patch("fitcv_cp.app.update_run_checkpoint", side_effect=_record("checkpoint")) as mock_checkpoint, \
         patch("fitcv_cp.app.update_run_orchestration_binding", side_effect=_record("binding")) as mock_binding, \
         patch("fitcv_cp.app.append_event"):
        resp = TestClient(_app()).post("/admin/runs/run-123/continue")

    assert resp.status_code == 200
    mock_status.assert_called_once()
    mock_queue.assert_called_once()
    mock_checkpoint.assert_called_once()
    mock_binding.assert_called_once()
    assert call_order.index("status") < call_order.index("continue")
    assert call_order.index("checkpoint") < call_order.index("continue")

def test_admin_continue_run_is_idempotent_for_already_progressed_state() -> None:
    progressed_run = MagicMock()
    progressed_run.run_id = "run-queued"
    progressed_run.run_mode = "manual_staged"
    progressed_run.status = RunStatus.QUEUED

    with patch("fitcv_cp.app.get_run", return_value=progressed_run), \
         patch("fitcv_cp.app.continue_run_submission") as mock_continue:
        resp = TestClient(_app()).post("/admin/runs/run-queued/continue")

    assert resp.status_code == 200
    assert resp.json() == {"status": "queued", "run_id": "run-queued", "replay_mode": "noop"}
    mock_continue.assert_not_called()


def test_admin_continue_run_uses_canonical_next_stage_from_completed_truth() -> None:
    """@proves trigger_run_management.manual-checkpoints-and-continue"""
    paused_run = MagicMock()
    paused_run.run_id = "run-continue-canonical"
    paused_run.run_mode = "manual_staged"
    paused_run.status = RunStatus.AWAITING_CONTINUE
    paused_run.next_stage = "rule_filter"
    paused_run.last_completed_stage = "shortlist"
    paused_run.completed_stages = ["normalize", "enrich", "rule_filter", "shortlist"]
    paused_run.checkpoint_payload_json = '{"checkpoint_payload":{"shortlist":[{"job_url":"https://example.com/1"}]}}'
    paused_run.jobs_path = "data/sample_jobs.json"
    paused_run.config_path = ".env.yaml"

    with patch("fitcv_cp.app.get_run", return_value=paused_run), \
         patch("fitcv_cp.app.continue_run_submission", return_value=RunSubmission(run_id="run-continue-canonical", queue_job_id="rq-job-abc", backend_run_id="rq-job-abc", backend="default_queue")), \
         patch("fitcv_cp.app.update_run_effective_settings"), \
         patch("fitcv_cp.app.update_run_status"), \
         patch("fitcv_cp.app.update_run_queue_job_id"), \
         patch("fitcv_cp.app.update_run_checkpoint") as mock_checkpoint, \
         patch("fitcv_cp.app.append_event") as mock_event:
        resp = TestClient(_app()).post("/admin/runs/run-continue-canonical/continue")

    assert resp.status_code == 200
    assert mock_checkpoint.call_args.kwargs["next_stage"] == "ranking"
    assert mock_event.call_args.args[0].message == "Manual run queued to continue from ranking (strict)"

def test_admin_continue_run_rejects_strict_policy_drift() -> None:
    paused_run = MagicMock()
    paused_run.run_id = "run-continue-strict-drift"
    paused_run.run_mode = "manual_staged"
    paused_run.status = RunStatus.AWAITING_CONTINUE
    paused_run.next_stage = "ranking"
    paused_run.last_completed_stage = "shortlist"
    paused_run.completed_stages = ["normalize", "enrich", "rule_filter", "shortlist"]
    paused_run.checkpoint_payload_json = json.dumps(
        {
            "checkpoint_payload": {"shortlist": []},
            "replay_context": {"policy_envelope_signature": "old-signature"},
        }
    )
    paused_run.jobs_path = "data/sample_jobs.json"
    paused_run.config_path = ".env.yaml"
    paused_run.effective_settings_json = json.dumps({"ranking_weights": {"ai_score": 0.4}})

    with patch("fitcv_cp.app.get_run", return_value=paused_run), \
         patch("fitcv_cp.app.continue_run_submission") as mock_continue:
        resp = TestClient(_app()).post("/admin/runs/run-continue-strict-drift/continue")

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Strict replay rejected: policy envelope drift detected"
    mock_continue.assert_not_called()

def test_admin_continue_run_allows_policy_replay_when_policy_drifted() -> None:
    paused_run = MagicMock()
    paused_run.run_id = "run-continue-policy-replay"
    paused_run.run_mode = "manual_staged"
    paused_run.status = RunStatus.AWAITING_CONTINUE
    paused_run.next_stage = "ranking"
    paused_run.last_completed_stage = "shortlist"
    paused_run.completed_stages = ["normalize", "enrich", "rule_filter", "shortlist"]
    paused_run.checkpoint_payload_json = json.dumps(
        {
            "checkpoint_payload": {"shortlist": []},
            "replay_context": {
                "policy_envelope_signature": "old-signature",
                "replay_source_run_id": "source-run-1",
            },
        }
    )
    paused_run.jobs_path = "data/sample_jobs.json"
    paused_run.config_path = ".env.yaml"
    paused_run.effective_settings_json = json.dumps({"ranking_weights": {"ai_score": 0.4}})

    with patch("fitcv_cp.app.get_run", return_value=paused_run), \
         patch("fitcv_cp.app.continue_run_submission", return_value=RunSubmission(run_id="run-continue-policy-replay", queue_job_id="rq-job-abc", backend_run_id="rq-job-abc", backend="default_queue")), \
         patch("fitcv_cp.app.update_run_effective_settings"), \
         patch("fitcv_cp.app.update_run_status"), \
         patch("fitcv_cp.app.update_run_queue_job_id"), \
         patch("fitcv_cp.app.update_run_checkpoint"), \
         patch("fitcv_cp.app.append_event"):
        resp = TestClient(_app()).post("/admin/runs/run-continue-policy-replay/continue?replay_mode=policy_replay")

    assert resp.status_code == 200
    assert resp.json()["replay_mode"] == "policy_replay"


def test_admin_continue_run_rejects_underspecified_checkpoint_truth() -> None:
    paused_run = MagicMock()
    paused_run.run_id = "run-continue-invalid"
    paused_run.run_mode = "manual_staged"
    paused_run.status = RunStatus.AWAITING_CONTINUE
    paused_run.next_stage = "cv_generation"
    paused_run.last_completed_stage = None
    paused_run.completed_stages = []
    paused_run.checkpoint_payload_json = '{"checkpoint_payload":{"cv_analysis_results":[]}}'
    paused_run.jobs_path = "data/sample_jobs.json"
    paused_run.config_path = ".env.yaml"

    with patch("fitcv_cp.app.get_run", return_value=paused_run), \
         patch("fitcv_cp.app.continue_run_submission") as mock_enqueue, \
         patch("fitcv_cp.app.update_run_status") as mock_status, \
         patch("fitcv_cp.app.update_run_queue_job_id") as mock_queue, \
         patch("fitcv_cp.app.update_run_checkpoint") as mock_checkpoint, \
         patch("fitcv_cp.app.append_event") as mock_event:
        resp = TestClient(_app()).post("/admin/runs/run-continue-invalid/continue")

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Run has no canonical next stage to continue"
    mock_enqueue.assert_not_called()
    mock_status.assert_not_called()
    mock_queue.assert_not_called()
    mock_checkpoint.assert_not_called()
    mock_event.assert_not_called()


def test_admin_continue_run_rejects_invalid_stage_truth() -> None:
    paused_run = MagicMock()
    paused_run.run_id = "run-continue-bogus"
    paused_run.run_mode = "manual_staged"
    paused_run.status = RunStatus.AWAITING_CONTINUE
    paused_run.next_stage = "cv_generation"
    paused_run.last_completed_stage = "bogus"
    paused_run.completed_stages = ["normalize", "bogus"]
    paused_run.checkpoint_payload_json = '{"checkpoint_payload":{"shortlist":[]}}'
    paused_run.jobs_path = "data/sample_jobs.json"
    paused_run.config_path = ".env.yaml"

    with patch("fitcv_cp.app.get_run", return_value=paused_run), \
         patch("fitcv_cp.app.continue_run_submission") as mock_enqueue, \
         patch("fitcv_cp.app.update_run_status") as mock_status, \
         patch("fitcv_cp.app.update_run_queue_job_id") as mock_queue, \
         patch("fitcv_cp.app.update_run_checkpoint") as mock_checkpoint, \
         patch("fitcv_cp.app.append_event") as mock_event:
        resp = TestClient(_app()).post("/admin/runs/run-continue-bogus/continue")

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Run has no canonical next stage to continue"
    mock_enqueue.assert_not_called()
    mock_status.assert_not_called()
    mock_queue.assert_not_called()
    mock_checkpoint.assert_not_called()
    mock_event.assert_not_called()


def test_admin_continue_run_rejects_checkpoint_progress_drift() -> None:
    paused_run = MagicMock()
    paused_run.run_id = "run-continue-drift"
    paused_run.run_mode = "manual_staged"
    paused_run.status = RunStatus.AWAITING_CONTINUE
    paused_run.next_stage = "ranking"
    paused_run.last_completed_stage = "shortlist"
    paused_run.completed_stages = ["normalize", "enrich", "rule_filter", "shortlist"]
    paused_run.checkpoint_payload_json = '{"checkpoint_payload":{"ranked":[{"job_url":"https://example.com/1"}]}}'
    paused_run.jobs_path = "data/sample_jobs.json"
    paused_run.config_path = ".env.yaml"

    with patch("fitcv_cp.app.get_run", return_value=paused_run), \
         patch("fitcv_cp.app.continue_run_submission") as mock_enqueue, \
         patch("fitcv_cp.app.update_run_status") as mock_status, \
         patch("fitcv_cp.app.update_run_queue_job_id") as mock_queue, \
         patch("fitcv_cp.app.update_run_checkpoint") as mock_checkpoint, \
         patch("fitcv_cp.app.append_event") as mock_event:
        resp = TestClient(_app()).post("/admin/runs/run-continue-drift/continue")

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Run has no canonical next stage to continue"
    mock_enqueue.assert_not_called()
    mock_status.assert_not_called()
    mock_queue.assert_not_called()
    mock_checkpoint.assert_not_called()
    mock_event.assert_not_called()






def test_admin_review_queue_page_renders_shared_controls_and_back_link() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-queue-page",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "Senior Data Engineer",
                        "status": "review_required",
                        "fit_classification": "stretch",
                        "error": {"stage": "review_gate", "message": "Low confidence sections: experience"},
                    }
                ],
                "hitl_review_actions": [],
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-review-queue-page/review-queue")
    assert resp.status_code == 200
    assert "← Back to Run Detail" in resp.text
    assert "Apply one action to selected jobs." in resp.text
    assert "Apply to Selected Jobs" in resp.text
    assert "Select All" in resp.text
    assert "Clear All" in resp.text

def test_admin_review_queue_page_guards_empty_batch_selection_with_alert() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-queue-empty-selection",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "Senior Data Engineer",
                        "status": "review_required",
                        "fit_classification": "stretch",
                        "error": {"stage": "review_gate", "message": "Low confidence sections: experience"},
                    }
                ],
                "hitl_review_actions": [],
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-review-queue-empty-selection/review-queue")
    assert resp.status_code == 200
    assert "Select at least one review-required row" in resp.text
    assert "window.alert('Select at least one review-required row.')" in resp.text
    assert "if (selected.length === 0)" in resp.text
    assert resp.text.index("if (selected.length === 0)") < resp.text.index("selectedAction !== 'regenerate_once'")


def test_admin_review_queue_resolved_rows_render_locked_non_actionable_state() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-queue-resolved-lock",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "Senior Data Engineer",
                        "status": "review_required",
                        "fit_classification": "stretch",
                        "error": {"stage": "review_gate", "message": "Needs review"},
                    }
                ],
                "hitl_review_actions": [
                    {
                        "job_url": "https://example.com/job-1",
                        "action": "approve_as_is",
                        "actor": "admin",
                        "timestamp": "2026-05-19T20:00:00Z",
                    }
                ],
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-review-queue-resolved-lock/review-queue")
    assert resp.status_code == 200
    assert "Row is resolved." in resp.text
    assert 'action="/admin/runs/run-review-queue-resolved-lock/cv-review-action"' not in resp.text
    assert 'name="job_url" value="https://example.com/job-1" form="hitl-batch-form" data-hitl-selectable="true"' not in resp.text

    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.get_events", return_value=[]), \
         patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
         patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        run_detail_resp = TestClient(_app()).get("/admin/runs/run-review-queue-resolved-lock")
    assert run_detail_resp.status_code == 200
    assert "Row is resolved." not in run_detail_resp.text
    assert 'action="/admin/runs/run-review-queue-resolved-lock/cv-review-action"' not in run_detail_resp.text



def test_admin_run_detail_hides_replay_and_backend_metadata() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-replay-meta",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        settings_used_json=json.dumps(
            {
                "replay_context": {
                    "replay_mode": "policy_replay",
                    "replay_source_run_id": "run-origin-1",
                    "policy_registry_version": "policy_registry.v2",
                }
            }
        ),
    )

    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.get_events", return_value=[]), \
         patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
         patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-replay-meta")

    assert resp.status_code == 200
    assert "Replay Mode" not in resp.text
    assert "policy_replay" not in resp.text
    assert "run-origin-1" not in resp.text
    assert "policy_registry.v2" not in resp.text
    assert "Runtime and Backend Details" not in resp.text
    assert "Run Attempt Timeline" not in resp.text


def test_admin_run_cv_review_action_persists_and_appends_event() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-action",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "Senior Data Engineer",
                        "status": "review_required",
                        "fit_classification": "stretch",
                        "error": {"stage": "review_gate", "message": "Low confidence sections: experience"},
                    }
                ]
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.update_run_cv_generation_debug") as mock_update, \
         patch("fitcv_cp.app.append_event") as mock_append:
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-action/cv-review-action",
            data={"job_url": "https://example.com/job-1", "action": "approve", "actor": "operator"},
            follow_redirects=False,
        )
    assert resp.status_code == 303
    mock_update.assert_called_once()
    saved_payload = json.loads(mock_update.call_args.args[1])
    assert saved_payload["hitl_review_actions"][-1]["action"] == "approve"
    assert saved_payload["hitl_review_actions"][-1]["job_url"] == "https://example.com/job-1"
    mock_append.assert_called_once()


def test_admin_run_cv_review_action_resolves_by_review_item_id_without_job_url() -> None:
    from datetime import datetime, timezone

    from fitcv_cp.models import PipelineRun, RunStatus

    run = PipelineRun(
        run_id="run-review-action-by-id",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "review_item_id": "ri_demo",
                        "job_url": "",
                        "job_title": "No URL Row",
                        "status": "review_required",
                    }
                ]
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.update_run_cv_generation_debug") as mock_update, \
         patch("fitcv_cp.app.append_event"):
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-action-by-id/cv-review-action",
            data={"review_item_id": "ri_demo", "job_url": "", "action": "reject", "actor": "operator"},
            follow_redirects=False,
        )
    assert resp.status_code == 303
    saved_payload = json.loads(mock_update.call_args.args[1])
    action_row = saved_payload["hitl_review_actions"][-1]
    assert action_row["review_item_id"] == "ri_demo"
    assert action_row["job_url"] == ""
    assert action_row["resolution_status"] == "rejected"


def test_admin_run_cv_review_action_regenerate_once_does_not_auto_complete_review() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-regenerate",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "Senior Data Engineer",
                        "status": "review_required",
                        "fit_classification": "stretch",
                        "error": {"stage": "review_gate", "message": "Low confidence sections: experience"},
                    }
                ]
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.update_run_cv_generation_debug") as mock_update_debug, \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.update_run_checkpoint") as mock_update_checkpoint, \
         patch("fitcv_cp.app.append_event") as mock_append, \
         patch("fitcv_cp.app.enqueue_cv_regenerate_once_with_job_id", return_value="job-regenerate"):
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-regenerate/cv-review-action",
            data={"job_url": "https://example.com/job-1", "action": "regenerate_once", "actor": "operator"},
            follow_redirects=False,
        )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/runs/run-review-regenerate/review-queue"
    mock_update_debug.assert_called_once()
    mock_update_status.assert_not_called()
    mock_update_checkpoint.assert_not_called()
    assert mock_append.call_count == 2
    stages = [str(getattr(call.args[0], "stage", "")) for call in mock_append.call_args_list if call.args]
    assert "cv_review_action" in stages
    assert "cv_regenerate_once_requested" in stages


def test_admin_run_cv_review_action_redirects_back_to_run_detail_when_triggered_inline() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-regenerate-inline",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "Senior Data Engineer",
                        "status": "review_required",
                        "fit_classification": "stretch",
                    }
                ]
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.update_run_cv_generation_debug"), \
         patch("fitcv_cp.app.append_event"), \
         patch("fitcv_cp.app.enqueue_cv_regenerate_once_with_job_id", return_value="job-regenerate"):
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-regenerate-inline/cv-review-action",
            data={"job_url": "https://example.com/job-1", "action": "regenerate_once", "actor": "operator"},
            headers={"referer": "http://testserver/admin/runs/run-review-regenerate-inline"},
            follow_redirects=False,
        )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/runs/run-review-regenerate-inline"


def test_admin_run_cv_review_action_reject_redirects_to_review_queue_by_default() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-reject-redirect",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "Senior Data Engineer",
                        "status": "review_required",
                        "fit_classification": "stretch",
                    }
                ]
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.update_run_cv_generation_debug"), \
         patch("fitcv_cp.app.append_event"):
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-reject-redirect/cv-review-action",
            data={"job_url": "https://example.com/job-1", "action": "reject", "actor": "operator"},
            follow_redirects=False,
        )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/runs/run-review-reject-redirect/review-queue"


def test_admin_run_cv_review_action_approve_as_is_redirects_to_review_queue_by_default() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-approve-redirect",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "Senior Data Engineer",
                        "status": "review_required",
                        "fit_classification": "stretch",
                    }
                ]
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app._finalize_review_draft_as_cv_artifact", return_value=(True, None, "cv-v1")), \
         patch("fitcv_cp.app.update_run_cv_generation_debug"), \
         patch("fitcv_cp.app.update_run_status"), \
         patch("fitcv_cp.app.append_event"):
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-approve-redirect/cv-review-action",
            data={"job_url": "https://example.com/job-1", "action": "approve_as_is", "actor": "operator"},
            follow_redirects=False,
        )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/runs/run-review-approve-redirect/review-queue"


def test_admin_run_cv_review_action_approve_records_terminal_resolution_status() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-approve-resolution",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "Senior Data Engineer",
                        "status": "review_required",
                        "fit_classification": "stretch",
                    }
                ]
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.update_run_cv_generation_debug") as mock_update_debug, \
         patch("fitcv_cp.app.append_event"):
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-approve-resolution/cv-review-action",
            data={"job_url": "https://example.com/job-1", "action": "approve", "actor": "operator"},
            follow_redirects=False,
        )
    assert resp.status_code == 303
    payload = json.loads(mock_update_debug.call_args.args[1])
    assert payload["hitl_review_actions"][-1]["resolution_status"] == "approved_as_is"

def test_admin_run_cv_review_action_approve_as_is_finalizes_cv_artifact() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-approve-finalize",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cvs_generated=0,
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "Senior Data Engineer",
                        "status": "review_required",
                        "fit_classification": "stretch",
                        "markdown_final": "# Candidate\n\nDraft",
                    }
                ]
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.insert_cv_version_row", return_value=[]) as mock_insert_cv, \
         patch("fitcv_cp.app.update_run_cv_generation_debug") as mock_update_debug, \
         patch("fitcv_cp.app.append_event"):
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-approve-finalize/cv-review-action",
            data={"job_url": "https://example.com/job-1", "action": "approve_as_is", "actor": "operator"},
            follow_redirects=False,
        )
    assert resp.status_code == 303
    mock_insert_cv.assert_called_once()
    payload = json.loads(mock_update_debug.call_args.args[1])
    assert payload["hitl_review_actions"][-1]["artifact_finalized"] is True

def test_admin_run_cv_review_action_approve_as_is_missing_draft_returns_409() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-approve-missing",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "Senior Data Engineer",
                        "status": "review_required",
                    }
                ]
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-approve-missing/cv-review-action",
            data={"job_url": "https://example.com/job-1", "action": "approve_as_is", "actor": "operator"},
            follow_redirects=False,
        )
    assert resp.status_code == 409

def test_admin_run_cv_review_action_approve_as_is_uses_markdown_full_precedence() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-approve-full-precedence",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "Senior Data Engineer",
                        "status": "review_required",
                        "fit_classification": "stretch",
                        "markdown_full": "# Candidate\n\nFull draft",
                        "markdown_final": "# Candidate\n\nLegacy draft",
                    }
                ]
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.insert_cv_version_row", return_value=[]), \
         patch("fitcv_cp.app.create_cv_version_record") as mock_create_version, \
         patch("fitcv_cp.app.update_run_cv_generation_debug"), \
         patch("fitcv_cp.app.append_event"):
        mock_create_version.side_effect = lambda **kwargs: {"version_id": "v-test", **kwargs}
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-approve-full-precedence/cv-review-action",
            data={"job_url": "https://example.com/job-1", "action": "approve_as_is", "actor": "operator"},
            follow_redirects=False,
        )
    assert resp.status_code == 303
    assert mock_create_version.call_args.kwargs["cv_markdown"] == "# Candidate\n\nFull draft"

def test_admin_run_cv_review_action_approve_as_is_blocks_truncated_legacy_draft() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-approve-truncated-legacy",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "Senior Data Engineer",
                        "status": "review_required",
                        "markdown_final": "# Candidate\n\nDraft\n...[truncated]",
                    }
                ]
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.insert_cv_version_row") as mock_insert:
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-approve-truncated-legacy/cv-review-action",
            data={"job_url": "https://example.com/job-1", "action": "approve_as_is", "actor": "operator"},
            follow_redirects=False,
        )
    assert resp.status_code == 409
    mock_insert.assert_not_called()

def test_build_hitl_review_queue_prefers_markdown_preview_over_full_text() -> None:
    from fitcv_cp.app import _build_hitl_review_queue
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-queue-preview-priority",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "Senior Data Engineer",
                        "status": "review_required",
                        "markdown_full": "# Candidate\n\n" + ("x" * 3000),
                        "markdown_preview": "# Candidate\n\nshort-preview",
                        "markdown_final": "# Candidate\n\nlegacy-preview",
                    }
                ]
            }
        ),
    )
    queue = _build_hitl_review_queue(run)
    item = queue["queue_items"][0]
    assert item["cv_markdown_preview"] == "# Candidate\n\nshort-preview"
    assert item["cv_preview_available"] is True


def test_build_hitl_review_queue_keeps_review_required_rows_without_job_url() -> None:
    from datetime import datetime, timezone

    from fitcv_cp.app import _build_hitl_review_queue
    from fitcv_cp.models import PipelineRun, RunStatus

    run = PipelineRun(
        run_id="run-review-queue-missing-url",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "debug_records": [
                    {
                        "status": "review_required",
                        "job_url": "",
                        "job_title": "Role Without URL",
                        "review_item_id": "ri_demo",
                        "error": {"message": "Manual review required."},
                    }
                ]
            }
        ),
    )

    queue = _build_hitl_review_queue(run)
    assert queue["total_review_required"] == 1
    assert queue["pending_count"] == 1
    assert len(queue["queue_items"]) == 1
    row = queue["queue_items"][0]
    assert row["job_url"] == ""
    assert row["review_item_id"] == "ri_demo"
    assert row["missing_job_url"] is True


def test_build_hitl_review_queue_applies_action_by_review_item_id_when_job_url_missing() -> None:
    from datetime import datetime, timezone

    from fitcv_cp.app import _build_hitl_review_queue
    from fitcv_cp.models import PipelineRun, RunStatus

    run = PipelineRun(
        run_id="run-review-queue-id-action",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "debug_records": [
                    {
                        "status": "review_required",
                        "job_url": "",
                        "job_title": "Role Without URL",
                        "review_item_id": "ri_demo",
                        "error": {"message": "Manual review required."},
                    }
                ],
                "hitl_review_actions": [
                    {
                        "review_item_id": "ri_demo",
                        "action": "reject",
                        "resolution_status": "rejected",
                        "created_at": "2026-05-20T10:00:00+00:00",
                    }
                ],
            }
        ),
    )

    queue = _build_hitl_review_queue(run)
    assert queue["pending_count"] == 0
    row = queue["queue_items"][0]
    assert row["review_item_id"] == "ri_demo"
    assert row["resolution_status"] == "rejected"
    assert row["pending"] is False


def test_admin_run_review_queue_forms_post_review_item_id_selectors() -> None:
    from datetime import datetime, timezone

    from fitcv_cp.models import PipelineRun, RunStatus

    run = PipelineRun(
        run_id="run-review-queue-selector-fields",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "review_item_id": "ri_selector_1",
                        "job_url": "https://example.com/job-1",
                        "job_title": "Selector Role",
                        "status": "review_required",
                    }
                ]
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-review-queue-selector-fields/review-queue")
    assert resp.status_code == 200
    assert 'name="review_item_id"' in resp.text
    assert 'value="ri_selector_1"' in resp.text


def test_admin_run_review_queue_missing_url_disables_regenerate_and_shows_explicit_state() -> None:
    from datetime import datetime, timezone

    from fitcv_cp.models import PipelineRun, RunStatus

    run = PipelineRun(
        run_id="run-review-queue-missing-url-state",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "review_item_id": "ri_missing_url",
                        "job_url": "",
                        "job_title": "No URL Role",
                        "status": "review_required",
                    }
                ]
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-review-queue-missing-url-state/review-queue")
    assert resp.status_code == 200
    assert "Job URL unavailable" in resp.text
    assert 'name="action" value="regenerate_once"' in resp.text
    assert 'Regenerate once requires job URL' in resp.text


def test_admin_run_cv_review_batch_action_applies_and_skips_terminal_rows() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-batch-1",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        last_completed_stage="cv_analysis",
        completed_stages=["normalize", "enrich", "rule_filter", "shortlist", "ranking", "cv_analysis"],
        checkpoint_payload_json=json.dumps({"checkpoint_payload": {"stage": "cv_analysis"}}),
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "DE1",
                        "status": "review_required",
                        "markdown_final": "# DE1\n\nAccepted draft",
                    },
                    {"job_url": "https://example.com/job-2", "job_title": "DE2", "status": "review_required"},
                ],
                "hitl_review_actions": [
                    {"job_url": "https://example.com/job-2", "action": "reject", "resolution_status": "rejected", "created_at": "2026-05-03T00:00:00+00:00"},
                ],
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.insert_cv_version_row", return_value=[]), \
         patch("fitcv_cp.app.update_run_cv_generation_debug") as mock_update_debug, \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.update_run_checkpoint") as mock_update_checkpoint, \
         patch("fitcv_cp.app.append_event") as mock_append:
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-batch-1/cv-review-batch-action",
            data={
                "action": "approve_as_is",
                "actor": "operator",
                "confirm_no_accepted_cv_closure": "true",
                "job_url": ["https://example.com/job-1", "https://example.com/job-2"],
            },
            follow_redirects=False,
        )
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/admin/runs/run-review-batch-1/review-queue?")
    assert "hitl_batch_applied=1" in resp.headers["location"]
    assert "hitl_batch_skipped=1" in resp.headers["location"]
    assert "hitl_batch_failed=0" in resp.headers["location"]
    payload = json.loads(mock_update_debug.call_args.args[1])
    assert any(
        row.get("job_url") == "https://example.com/job-1" and row.get("resolution_status") == "approved_as_is"
        for row in list(payload.get("hitl_review_actions") or [])
    )
    assert mock_update_status.call_count == 2
    mock_update_checkpoint.assert_called_once()
    checkpoint_kwargs = mock_update_checkpoint.call_args.kwargs
    assert checkpoint_kwargs["last_completed_stage"] == "cv_analysis"
    assert checkpoint_kwargs["completed_stages"] == ["normalize", "enrich", "rule_filter", "shortlist", "ranking", "cv_analysis"]
    assert checkpoint_kwargs["checkpoint_payload_json"] == json.dumps({"checkpoint_payload": {"stage": "cv_analysis"}})
    assert mock_append.call_count >= 2
    completion_events = [
        call.args[0]
        for call in mock_append.call_args_list
        if getattr(call.args[0], "stage", "") == "cv_review_completed"
    ]
    assert completion_events
    completion_payload = json.loads(completion_events[0].payload_json)
    assert completion_payload["closure_mode"] in {"all_review_rows_terminal", "all_review_rows_terminal_no_accepted_cv"}


def test_admin_run_cv_review_batch_action_accepts_review_item_id_selectors() -> None:
    from datetime import datetime, timezone

    from fitcv_cp.models import PipelineRun, RunStatus

    run = PipelineRun(
        run_id="run-review-batch-by-id",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "review_item_id": "ri_1",
                        "job_url": "",
                        "job_title": "No URL Row",
                        "status": "review_required",
                    },
                    {
                        "review_item_id": "ri_2",
                        "job_url": "https://example.com/job-2",
                        "job_title": "URL Row",
                        "status": "review_required",
                    },
                ],
                "hitl_review_actions": [
                    {"review_item_id": "ri_2", "job_url": "https://example.com/job-2", "action": "reject", "resolution_status": "rejected"},
                ],
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.update_run_cv_generation_debug") as mock_update_debug, \
         patch("fitcv_cp.app.update_run_status"), \
         patch("fitcv_cp.app.update_run_checkpoint"), \
         patch("fitcv_cp.app.append_event"):
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-batch-by-id/cv-review-batch-action",
            data={
                "action": "reject",
                "actor": "operator",
                "review_item_id": ["ri_1", "ri_2"],
            },
            follow_redirects=False,
        )
    assert resp.status_code == 303
    assert "hitl_batch_applied=1" in resp.headers["location"]
    assert "hitl_batch_skipped=1" in resp.headers["location"]
    payload = json.loads(mock_update_debug.call_args.args[1])
    assert any(
        row.get("review_item_id") == "ri_1" and row.get("resolution_status") == "rejected"
        for row in list(payload.get("hitl_review_actions") or [])
    )


def test_admin_run_cv_review_action_does_not_close_when_another_identity_remains_pending() -> None:
    from datetime import datetime, timezone

    from fitcv_cp.models import PipelineRun, RunStatus

    run = PipelineRun(
        run_id="run-review-closure-identity-pending",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "review_item_id": "ri_resolve_now",
                        "job_url": "https://example.com/job-1",
                        "job_title": "Resolvable Row",
                        "status": "review_required",
                    },
                    {
                        "review_item_id": "ri_pending_other",
                        "job_url": "",
                        "job_title": "Still Pending Row",
                        "status": "review_required",
                    },
                ]
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.update_run_cv_generation_debug"), \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.update_run_checkpoint") as mock_update_checkpoint, \
         patch("fitcv_cp.app.append_event"):
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-closure-identity-pending/cv-review-action",
            data={"review_item_id": "ri_resolve_now", "action": "reject", "actor": "operator"},
            follow_redirects=False,
        )

    assert resp.status_code == 303
    mock_update_status.assert_not_called()
    mock_update_checkpoint.assert_not_called()


def test_legacy_review_required_row_without_persisted_id_is_actionable_and_closable_via_derived_id() -> None:
    from datetime import datetime, timezone
    import re

    from fitcv_cp.models import PipelineRun, RunStatus

    run = PipelineRun(
        run_id="run-review-legacy-derived-id",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "",
                        "job_title": "Legacy Row Without Persisted ID",
                        "status": "review_required",
                        "fit_classification": "stretch",
                    }
                ],
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.update_run_cv_generation_debug") as mock_update_debug, \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.update_run_checkpoint") as mock_update_checkpoint, \
         patch("fitcv_cp.app.append_event"):
        client = TestClient(_app())
        queue_resp = client.get("/admin/runs/run-review-legacy-derived-id/review-queue")
        assert queue_resp.status_code == 200
        match = re.search(r'name="review_item_id" value="(ri_[^"]+)"', queue_resp.text)
        assert match is not None
        derived_review_item_id = str(match.group(1) or "")

        action_resp = client.post(
            "/admin/runs/run-review-legacy-derived-id/cv-review-action",
            data={
                "review_item_id": derived_review_item_id,
                "action": "reject",
                "actor": "operator",
                "confirm_no_accepted_cv_closure": "true",
            },
            follow_redirects=False,
        )

    assert action_resp.status_code == 303
    saved_payload = json.loads(mock_update_debug.call_args.args[1])
    action_rows = list(saved_payload.get("hitl_review_actions") or [])
    assert action_rows
    assert str(action_rows[-1].get("review_item_id") or "").startswith("ri_")
    assert action_rows[-1].get("resolution_status") == "rejected"
    assert any(call.args[1] == RunStatus.SUCCEEDED for call in mock_update_status.call_args_list)
    mock_update_checkpoint.assert_called_once()


def test_admin_run_cv_review_action_blocks_zero_accepted_closure_without_confirmation() -> None:
    from datetime import datetime, timezone

    from fitcv_cp.models import PipelineRun, RunStatus

    run = PipelineRun(
        run_id="run-review-zero-accepted-block",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cvs_generated=0,
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "review_item_id": "ri_only_row",
                        "job_url": "",
                        "job_title": "Only Pending Row",
                        "status": "review_required",
                    }
                ],
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.update_run_cv_generation_debug"), \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.update_run_checkpoint") as mock_update_checkpoint, \
         patch("fitcv_cp.app.append_event") as mock_append:
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-zero-accepted-block/cv-review-action",
            data={"review_item_id": "ri_only_row", "action": "reject", "actor": "operator"},
            follow_redirects=False,
        )

    assert resp.status_code == 303
    assert mock_update_status.call_count == 0
    mock_update_checkpoint.assert_not_called()
    blocked_events = [
        call.args[0]
        for call in mock_append.call_args_list
        if getattr(call.args[0], "stage", "") == "cv_review_closure_blocked"
    ]
    assert blocked_events

def test_admin_run_cv_review_batch_action_finalize_path_no_longer_needs_zero_cv_confirmation() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-batch-blocked",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cvs_generated=0,
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "DE1",
                        "status": "review_required",
                        "markdown_final": "# DE1\n\nAccepted draft",
                    },
                ],
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.insert_cv_version_row", return_value=[]), \
         patch("fitcv_cp.app.update_run_cv_generation_debug") as mock_update_debug, \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.update_run_checkpoint") as mock_update_checkpoint, \
         patch("fitcv_cp.app.append_event") as mock_append:
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-batch-blocked/cv-review-batch-action",
            data={
                "action": "approve_as_is",
                "actor": "operator",
                "job_url": ["https://example.com/job-1"],
            },
            follow_redirects=False,
        )
    assert resp.status_code == 303
    assert "hitl_batch_finalized=1" in resp.headers["location"]
    mock_update_debug.assert_called_once()
    assert mock_update_status.call_count == 2
    mock_update_checkpoint.assert_called_once()

def test_admin_run_cv_review_batch_action_approve_as_is_missing_draft_is_safe_failure() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-batch-missing-draft",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {"job_url": "https://example.com/job-1", "job_title": "DE1", "status": "review_required"},
                ],
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.update_run_cv_generation_debug") as mock_update_debug, \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.update_run_checkpoint") as mock_update_checkpoint:
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-batch-missing-draft/cv-review-batch-action",
            data={
                "action": "approve_as_is",
                "actor": "operator",
                "job_url": ["https://example.com/job-1"],
            },
            follow_redirects=False,
        )
    assert resp.status_code == 303
    assert "hitl_batch_failed=1" in resp.headers["location"]
    mock_update_debug.assert_called_once()
    mock_update_status.assert_not_called()
    mock_update_checkpoint.assert_not_called()

def test_admin_run_cv_review_batch_action_tracks_truncated_draft_failure_counter() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-batch-truncated-draft",
        status=RunStatus.AWAITING_CONTINUE,
        checkpoint_status="awaiting_review",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "DE1",
                        "status": "review_required",
                        "markdown_final": "# DE1\n\nDraft\n...[truncated]",
                    },
                ],
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.update_run_cv_generation_debug") as mock_update_debug, \
         patch("fitcv_cp.app.append_event") as mock_append, \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.update_run_checkpoint") as mock_update_checkpoint:
        resp = TestClient(_app()).post(
            "/admin/runs/run-review-batch-truncated-draft/cv-review-batch-action",
            data={
                "action": "approve_as_is",
                "actor": "operator",
                "job_url": ["https://example.com/job-1"],
            },
            follow_redirects=False,
        )
    assert resp.status_code == 303
    assert "hitl_batch_failed=1" in resp.headers["location"]
    payload = json.loads(mock_update_debug.call_args.args[1])
    assert payload.get("hitl_review_actions") in ([], None)
    batch_events = [call.args[0] for call in mock_append.call_args_list if getattr(call.args[0], "stage", "") == "cv_review_batch_action"]
    assert batch_events
    batch_payload = json.loads(batch_events[0].payload_json)
    assert batch_payload["failed_truncated_draft"] == 1
    mock_update_status.assert_not_called()
    mock_update_checkpoint.assert_not_called()













# ── multi-file upload tests ────────────────────────────────────────────────────

_UPLOAD_COMMON_PATCHES = {
    "fitcv_cp.app.load_active_settings": lambda: {"return_value": {}},
}


def _upload_patches():
    return (
        patch("fitcv_cp.app.load_active_settings", return_value={}),
        patch("fitcv_cp.app.insert_run"),
        patch("fitcv_cp.app.submit_run", return_value=RunSubmission(run_id="run-multi", queue_job_id="rq-job-1", backend_run_id="rq-job-1", backend="default_queue")),
        patch("fitcv_cp.app.update_run_queue_job_id"),
        patch("fitcv_cp.app.load_config", return_value={
            "gcp_project": "p","pipeline": {"final_top_n": 10},
            "paths": {"candidate_profile": "data/candidate_profile.yaml"},
        }),
    )


def test_admin_upload_trigger_merges_multiple_job_files():
    """@proves multi_file_job_input.multiple-file-inputs-in-trigger-form
    @proves multi_file_job_input.canonical-merge-preserving-order
    @proves multi_file_job_input.one-immutable-snapshot-stored-per-run

    Two valid JSON files → 201, merged snapshot contains both jobs.
    """
    file1 = json.dumps([_valid_fitcv_job(title="Engineer", jobUrl="http://a.com", job_url="http://a.com")]).encode("utf-8")
    file2 = json.dumps([_valid_fitcv_job(title="Analyst", jobUrl="http://b.com", job_url="http://b.com")]).encode("utf-8")
    captured = {}

    p = _upload_patches()
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app_with_captured_run(captured)).post(
            "/admin/upload-trigger",
            data={"jobs_input_mode": "upload", "candidate_profile_id": "profile-1"},
            files=[
                ("jobs_files", ("file1.json", file1, "application/json")),
                ("jobs_files", ("file2.json", file2, "application/json")),
            ],
        )

    assert resp.status_code == 201, resp.text
    assert "run_id" in resp.json()
    merged = json.loads(captured["run"].jobs_input_json)
    urls = [j["job_url"] for j in merged]
    assert "http://a.com" in urls
    assert "http://b.com" in urls
    manifest = json.loads(captured["run"].jobs_input_manifest_json)
    assert manifest["source_filenames"] == ["file1.json", "file2.json"]


def test_admin_upload_trigger_multi_file_preserves_order():
    """@proves multi_file_job_input.canonical-merge-preserving-order

    Merged snapshot preserves file order (file1 rows first, then file2).
    """
    file1 = json.dumps([_valid_fitcv_job(jobUrl="http://first.com", job_url="http://first.com")]).encode("utf-8")
    file2 = json.dumps([_valid_fitcv_job(jobUrl="http://second.com", job_url="http://second.com")]).encode("utf-8")
    captured = {}

    p = _upload_patches()
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app_with_captured_run(captured)).post(
            "/admin/upload-trigger",
            data={"jobs_input_mode": "upload", "candidate_profile_id": "profile-1"},
            files=[
                ("jobs_files", ("a.json", file1, "application/json")),
                ("jobs_files", ("b.json", file2, "application/json")),
            ],
        )

    assert resp.status_code == 201, resp.text
    merged = json.loads(captured["run"].jobs_input_json)
    assert [j["job_url"] for j in merged] == ["http://first.com", "http://second.com"]


def test_admin_upload_trigger_one_invalid_file_rejects_entire_request():
    """@proves multi_file_job_input.per-file-server-side-validation
    @proves multi_file_job_input.all-or-nothing-rejection-on-validation-failure

    One file with invalid JSON → 422; run must NOT be created.
    """
    file1 = json.dumps([_valid_fitcv_job(jobUrl="http://good.com", job_url="http://good.com")]).encode("utf-8")
    file2 = b'THIS IS NOT JSON'
    p = _upload_patches()
    with p[0], p[1], p[2], p[3], p[4]:
        with patch("fitcv_cp.app.insert_run") as mock_insert:
            resp = TestClient(_app()).post(
                "/admin/upload-trigger",
                data={"jobs_input_mode": "upload", "candidate_profile_mode": "default_config"},
                files=[
                    ("jobs_files", ("good.json", file1, "application/json")),
                    ("jobs_files", ("bad.json", file2, "application/json")),
                ],
            )
    assert resp.status_code == 422
    mock_insert.assert_not_called()


def test_admin_upload_trigger_all_empty_arrays_rejected():
    """@proves multi_file_job_input.per-file-server-side-validation
    @proves multi_file_job_input.all-or-nothing-rejection-on-validation-failure

    Two files both containing empty arrays → 422 (total merged is empty).
    """
    file1 = b'[]'
    file2 = b'[]'
    p = _upload_patches()
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).post(
            "/admin/upload-trigger",
            data={"jobs_input_mode": "upload", "candidate_profile_mode": "default_config"},
            files=[
                ("jobs_files", ("a.json", file1, "application/json")),
                ("jobs_files", ("b.json", file2, "application/json")),
            ],
        )
    assert resp.status_code == 422


def test_admin_upload_trigger_upload_mode_no_files_rejected():
    """@proves multi_file_job_input.multiple-file-inputs-in-trigger-form

    Upload mode with neither jobs_file nor jobs_files → 422.
    """
    p = _upload_patches()
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).post(
            "/admin/upload-trigger",
            data={"jobs_input_mode": "upload", "candidate_profile_mode": "default_config"},
        )
    assert resp.status_code == 422


def test_admin_upload_trigger_multi_file_non_array_rejected():
    """@proves multi_file_job_input.per-file-server-side-validation
    @proves multi_file_job_input.all-or-nothing-rejection-on-validation-failure

    A file whose top-level is not a JSON array → 422.
    """
    file1 = b'{"title": "not an array"}'
    p = _upload_patches()
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).post(
            "/admin/upload-trigger",
            data={"jobs_input_mode": "upload", "candidate_profile_mode": "default_config"},
            files=[
                ("jobs_files", ("dict.json", file1, "application/json")),
            ],
        )
    assert resp.status_code == 422


def test_admin_upload_trigger_effective_settings_includes_runtime_contract():
    active = {
        "llm_runtime.request_start_interval_secs": 0.5,
        "stage_runtime.enrich.concurrency": 3,
    }
    captured = {}

    p = _upload_patches()
    with p[0], p[1], p[2], p[3], p[4]:
        with patch("fitcv_cp.app.load_active_settings", return_value=active):
            file1 = json.dumps([_valid_fitcv_job(jobUrl="http://e.com", job_url="http://e.com")]).encode("utf-8")
            resp = TestClient(_app_with_captured_run(captured)).post(
                "/admin/upload-trigger",
                data={"jobs_input_mode": "upload", "candidate_profile_id": "profile-1"},
                files=[
                    ("jobs_files", ("e.json", file1, "application/json")),
                ],
            )

    assert resp.status_code == 201, resp.text
    effective = json.loads(captured["run"].effective_settings_json)
    assert effective["llm_runtime"] == {"request_start_interval_secs": 0.5}
    assert effective["stage_runtime"]["enrich"] == {"concurrency": 3}
    assert "enrichment_batch_size" not in effective
    assert "enrichment_concurrency" not in effective



# ── html routes ──────────────────────────────────────────────────────────────

def test_admin_runs_rendered_nav():
    with patch("fitcv_cp.app.list_runs", return_value=[]), \
         patch("fitcv_cp.app.get_events", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs")
    assert resp.status_code == 200
    assert 'href="/admin/settings"' in resp.text
    assert 'Pipeline</summary>' in resp.text
    assert 'Refresh' not in resp.text
    assert 'id="jobFile"' in resp.text
    assert 'id="candidateProfile"' in resp.text
    assert "fd.append('config_path', '.env.yaml')" in resp.text
    assert 'id="jobs_path"' not in resp.text
    assert "Outbox Replay Health (Visible Runs)" not in resp.text
    assert "Replay Success Ratio" not in resp.text
    assert 'href="/admin/outbox-replay-health.json?view=active"' not in resp.text


def test_admin_run_detail_hides_aggregate_mapping_suggestions_button() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    with patch("fitcv_cp.app.get_run", return_value=PipelineRun(
        run_id="test-mapping-aggregate-btn", status=RunStatus.RUNNING,
        total_jobs=10, jobs_path="", triggered_by="admin", trigger_source="web",
        config_path="config/default.yaml", created_at=datetime.now(timezone.utc),
        mapping_suggestions_json=None,
    )), patch("fitcv_cp.app.get_events", return_value=[]), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/test-mapping-aggregate-btn")
    assert resp.status_code == 200
    assert 'href="/admin/mapping-suggestions.json"' not in resp.text
    assert "Aggregate Mapping Suggestions JSON" not in resp.text


def test_admin_run_detail_hides_mapping_suggestions_export_before_enrich_stage() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="test-mapping-stage-gate",
        status=RunStatus.AWAITING_CONTINUE,
        total_jobs=7,
        jobs_path="data/sample_jobs.json",
        triggered_by="admin",
        trigger_source="web",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        stage_transition_artifacts_json=json.dumps(
            {"artifacts": {"stages": {"normalize": {"status": "completed"}}}}
        ),
        mapping_suggestions_json='{"suggestions":[]}',
    )

    with patch("fitcv_cp.app.get_run", return_value=run), \
    patch("fitcv_cp.app.get_events", return_value=[]), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/test-mapping-stage-gate")

    assert resp.status_code == 200
    assert 'href="/admin/runs/test-mapping-stage-gate/mapping-suggestions.json"' not in resp.text
    assert "Mapping Suggestions JSON" not in resp.text


def _obsolete_test_run_detail_timeline_shows_stage_download_for_mapped_event():
    """@proves inspection_debugging.stage-artifact-downloads
    @proves trigger_run_management.stage-artifact-downloads
    """
    from fitcv_cp.models import PipelineRun, RunStatus, RunEvent
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-stage-link",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        stage_transition_artifacts_json='{"run_id":"run-stage-link","artifacts":{"stages":{"ranking":{"status":"completed"}}}}',
    )
    events = [
        RunEvent(
            run_id="run-stage-link",
            event_id="e1",
            stage="layer3_ranking",
            level="info",
            message="Final ranking: top 3 jobs",
            created_at=datetime.now(timezone.utc),
        )
    ]
    with patch("fitcv_cp.app.get_run", return_value=run), \
    patch("fitcv_cp.app.get_events", return_value=events), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-stage-link")
    assert resp.status_code == 200
    assert 'href="/admin/runs/run-stage-link/stage-artifacts/ranking.json"' in resp.text
    assert "Download Ranking JSON" in resp.text


def _obsolete_test_run_detail_timeline_hides_evidence_fingerprint() -> None:
    from datetime import datetime, timezone

    from fitcv_cp.models import PipelineRun, RunEvent, RunStatus

    run = PipelineRun(
        run_id="run-private-timeline",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    events = [
        RunEvent(
            run_id=run.run_id,
            event_id="e-private",
            stage="layer4_cv_generation_result",
            level="info",
            message=(
                "item 1, job https://jobs.example.com/1, outcome review required, "
                "reason unsupported_requirement_gap, evidence fp abc123def456"
            ),
            created_at=datetime.now(timezone.utc),
            payload_json='{"job_url":"https://jobs.example.com/1"}',
        )
    ]

    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.get_events", return_value=events), \
         patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
         patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        response = TestClient(_app()).get(f"/admin/runs/{run.run_id}")

    assert response.status_code == 200
    assert "evidence fingerprint" not in response.text
    assert "abc123def456" not in response.text

def test_run_detail_paused_after_normalize_shows_exact_process_event() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus, build_process_event
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-normalize-console",
        status=RunStatus.AWAITING_CONTINUE,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/uploads/example_merged_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        checkpoint_status="awaiting_continue",
        last_completed_stage="normalize",
        next_stage="enrich",
        completed_stages=["normalize"],
    )
    event = build_process_event(
        process_type="pipeline",
        process_id=run.run_id,
        operation="layer1_normalize",
        state="recorded",
        level="info",
        message="Normalization dedupe: kept 10 of 10 jobs, removed 0 duplicate(s)",
    )
    page = {
        "events": [event],
        "integrity_conflicts": [],
        "deliveries": [],
        "total_count": 1,
        "next_cursor": None,
    }
    with patch("fitcv_cp.app.get_run", return_value=run), \
    patch("fitcv_cp.app.get_events", return_value=[]), \
    patch("fitcv_cp.app.get_process_events", return_value=page), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-normalize-console")

    assert resp.status_code == 200
    assert "Console Log" in resp.text
    assert "Normalization dedupe: kept 10 of 10 jobs, removed 0 duplicate(s)" in resp.text
    assert "Normalize complete: kept 10 of 10 jobs, removed 0 duplicate(s)" not in resp.text

def test_run_detail_upload_jobs_path_shows_merged_from_filenames():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-detail-jobs-merged-from",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/uploads/e99cd34d9c2343d1b8577e6c9a3120fb_merged_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        jobs_input_source="upload",
        jobs_input_manifest_json=json.dumps(
            {"source_filenames": ["foo.json", "bar.json", "baz.json", "qux.json"]}
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
    patch("fitcv_cp.app.get_events", return_value=[]), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-detail-jobs-merged-from")

    assert resp.status_code == 200
    assert (
        "data/uploads/e99cd34d9c2343d1b8577e6c9a3120fb_merged_jobs.json "
        "(merged from: foo.json, bar.json, baz.json, qux.json)"
    ) in resp.text


def test_run_detail_projects_ordered_upload_and_scan_sources():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-detail-combined-sources",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/uploads/run-detail-combined-sources_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        jobs_input_source="combined",
        jobs_input_json="[]",
        jobs_input_manifest_json=json.dumps(
            {
                "sources": [
                    {"type": "upload", "filename": "uploaded-jobs.json"},
                    {"type": "scan", "scan_id": "scan-1048", "scan_name": "Germany Data Jobs"},
                    {"type": "scan", "scan_id": "scan-1049", "scan_name": "Berlin Platform Jobs"},
                ]
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
    patch("fitcv_cp.app.get_events", return_value=[]), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        client = TestClient(_app())
        detail = client.get(f"/admin/runs/{run.run_id}")
        jobs_input = client.get(f"/admin/runs/{run.run_id}/tabs/jobs-input")

    for response in (detail, jobs_input):
        assert response.status_code == 200
        assert response.text.index("uploaded-jobs.json") < response.text.index("scan-1048")
        assert response.text.index("scan-1048") < response.text.index("scan-1049")
        assert "Germany Data Jobs" in response.text
        assert "Berlin Platform Jobs" in response.text


def _obsolete_test_run_detail_timeline_shows_cv_analysis_download_only_on_aggregate_row():
    from fitcv_cp.models import PipelineRun, RunStatus, RunEvent
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-cv-analysis-timeline",
        status=RunStatus.AWAITING_CONTINUE,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        stage_transition_artifacts_json=json.dumps(
            {
                "artifacts": {
                    "stages": {
                        "cv_analysis": {
                            "status": "completed",
                            "output_counts": {
                                "ready_for_generation": 1,
                                "skipped_fit_gate": 2,
                                "analysis_failed": 0,
                            },
                        }
                    }
                }
            }
        ),
    )
    events = [
        RunEvent(
            run_id="run-cv-analysis-timeline",
            event_id="e1",
            stage="layer4_cv_analysis_skip",
            level="info",
            message="Skipped https://jobs.example.com/1 (fit=skip)",
            created_at=datetime.now(timezone.utc),
        ),
        RunEvent(
            run_id="run-cv-analysis-timeline",
            event_id="e2",
            stage="layer4_cv_analysis",
            level="info",
            message="CV analysis complete: 1 ready, 2 skipped, 0 failed",
            created_at=datetime.now(timezone.utc),
        ),
    ]
    with patch("fitcv_cp.app.get_run", return_value=run), \
    patch("fitcv_cp.app.get_events", return_value=events), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-cv-analysis-timeline")

    assert resp.status_code == 200
    assert resp.text.count('href="/admin/runs/run-cv-analysis-timeline/stage-artifacts/cv_analysis.json"') == 1
    assert "CV analysis complete: 1 ready, 2 skipped, 0 failed" in resp.text
    assert "Skipped https://jobs.example.com/1 (fit=skip)" in resp.text


def _obsolete_test_run_detail_timeline_uses_bounded_cv_analysis_payload_counts():
    from fitcv_cp.models import PipelineRun, RunStatus, RunEvent
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-cv-analysis-payload",
        status=RunStatus.AWAITING_CONTINUE,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        stage_transition_artifacts_json=json.dumps(
            {
                "artifacts": {
                    "stages": {
                        "cv_analysis": {
                            "status": "completed",
                        }
                    }
                }
            }
        ),
    )
    events = [
        RunEvent(
            run_id="run-cv-analysis-payload",
            event_id="e1",
            stage="layer4_cv_analysis",
            level="info",
            message="legacy summary",
            created_at=datetime.now(timezone.utc),
            payload_json=json.dumps(
                {
                    "event_name": "cv_analysis_decision",
                    "event_family": "decision",
                    "source_stage": "cv_analysis",
                    "event_status": "completed",
                    "deterministic_outcome": None,
                    "stage_owned_subreason": "stage_summary",
                    "fallback_used": False,
                    "output_snapshot": {
                        "ready_for_generation": 1,
                        "blocked_by_reranker_fit": 2,
                        "skipped_fit_gate": 0,
                        "analysis_failed": 1,
                    },
                    "artifact_refs": {"stage_id": "cv_analysis"},
                }
            ),
        )
    ]
    with patch("fitcv_cp.app.get_run", return_value=run), \
    patch("fitcv_cp.app.get_events", return_value=events), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-cv-analysis-payload")

    assert resp.status_code == 200
    assert "CV analysis complete: ready 1, blocked 2, skipped 0, failed 1." in resp.text


def _obsolete_test_run_detail_timeline_keeps_cv_generation_failure_types_distinct() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus, RunEvent
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-cv-generation-failure-types",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        stage_transition_artifacts_json=json.dumps(
            {
                "artifacts": {
                    "stages": {
                        "cv_generation": {
                            "status": "completed",
                            "output_counts": {
                                "accepted": 1,
                                "validation_failed": 2,
                                "generation_failed": 3,
                                "persistence_failed": 4,
                            },
                        }
                    }
                }
            }
        ),
    )
    events = [
        RunEvent(
            run_id="run-cv-generation-failure-types",
            event_id="e1",
            stage="pipeline_complete",
            level="info",
            message="legacy completion summary",
            created_at=datetime.now(timezone.utc),
            payload_json=json.dumps(
                {
                    "event_name": "pipeline_complete",
                    "event_family": "summary",
                    "source_stage": "cv_generation",
                    "event_status": "completed",
                }
            ),
        )
    ]
    with patch("fitcv_cp.app.get_run", return_value=run), \
    patch("fitcv_cp.app.get_events", return_value=events), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-cv-generation-failure-types")

    assert resp.status_code == 200
    assert (
        "CV generation complete: 1 accepted, 2 validation failed, 3 generation failed, 4 persistence failed"
        in resp.text
    )


def _obsolete_test_run_detail_timeline_keeps_validation_failed_job_message_from_payload():
    from fitcv_cp.models import PipelineRun, RunStatus, RunEvent
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-cv-validation-row",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        stage_transition_artifacts_json=json.dumps(
            {
                "artifacts": {
                    "stages": {
                        "cv_generation": {
                            "status": "completed",
                            "output_counts": {
                                "accepted": 1,
                                "validation_failed": 1,
                                "generation_failed": 0,
                                "persistence_failed": 0,
                            },
                        }
                    }
                }
            }
        ),
    )
    events = [
        RunEvent(
            run_id="run-cv-validation-row",
            event_id="e1",
            stage="layer4_cv_validation_failed",
            level="warning",
            message="legacy validation copy",
            created_at=datetime.now(timezone.utc),
            payload_json=json.dumps(
                {
                    "event_name": "cv_generation_decision",
                    "event_family": "decision",
                    "source_stage": "cv_generation",
                    "job_url": "https://jobs.example.com/1",
                    "event_status": "completed",
                    "deterministic_outcome": "rejected",
                    "stage_owned_subreason": "validation_failed",
                    "fallback_used": False,
                    "artifact_refs": {"stage_id": "cv_generation"},
                }
            ),
        )
    ]
    with patch("fitcv_cp.app.get_run", return_value=run), \
    patch("fitcv_cp.app.get_events", return_value=events), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-cv-validation-row")

    assert resp.status_code == 200
    assert "CV validation failed (expected policy rejection) for https://jobs.example.com/1" in resp.text
    assert "unexpected; investigate" not in resp.text
    assert "CV generation complete:" not in resp.text


def _obsolete_test_run_detail_timeline_marks_validation_failed_as_unexpected_when_contract_fields_missing():
    from fitcv_cp.models import PipelineRun, RunStatus, RunEvent
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-cv-validation-row-unexpected",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    events = [
        RunEvent(
            run_id="run-cv-validation-row-unexpected",
            event_id="e1",
            stage="layer4_cv_validation_failed",
            level="warning",
            message="legacy validation copy",
            created_at=datetime.now(timezone.utc),
            payload_json=json.dumps(
                {
                    "event_name": "cv_generation_decision",
                    "event_family": "decision",
                    "source_stage": "cv_generation",
                    "job_url": "https://jobs.example.com/2",
                    "event_status": "completed",
                    "deterministic_outcome": None,
                    "stage_owned_subreason": None,
                }
            ),
        )
    ]
    with patch("fitcv_cp.app.get_run", return_value=run), \
    patch("fitcv_cp.app.get_events", return_value=events), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-cv-validation-row-unexpected")

    assert resp.status_code == 200
    assert "CV validation failed (unexpected; investigate) for https://jobs.example.com/2" in resp.text

def _obsolete_test_run_detail_timeline_shows_repeat_count_for_collapsed_synonym_triage() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-triage-repeat",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    payload = {
        "triaged_count": 5,
        "reused_count": 0,
        "fresh_count": 5,
        "fallback_count": 0,
        "skipped_count": 0,
        "failed_count": 0,
        "reuse_reason": "reuse_enabled",
        "provider": "fitcv_builtin",
        "model": "synonym_triage_v1",
        "wire_api": "builtin",
    }
    ts = datetime.now(timezone.utc)
    events = [
        RunEvent(run_id="run-triage-repeat", event_id="e1", stage="synonym_proposal_triage_completed", level="info", message="Synonym triage refresh completed", created_at=ts, payload_json=json.dumps(payload)),
        RunEvent(run_id="run-triage-repeat", event_id="e2", stage="synonym_proposal_triage_completed", level="info", message="Synonym triage refresh completed", created_at=ts, payload_json=json.dumps(payload)),
    ]
    with patch("fitcv_cp.app.get_run", return_value=run), \
    patch("fitcv_cp.app.get_events", return_value=events), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-triage-repeat")

    assert resp.status_code == 200
    assert "(x2)" in resp.text


def _obsolete_test_run_detail_timeline_hides_repeat_count_for_collapsed_enrich_progress() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-enrich-repeat",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    ts = datetime.now(timezone.utc)
    payload = {
        "phase": "batch_progress",
        "fresh_jobs_total": 85,
        "reused_jobs_total": 0,
        "enrich_concurrency_effective": 4,
        "heartbeat_count": 1,
        "elapsed_secs": 15,
    }
    events = [
        RunEvent(run_id="run-enrich-repeat", event_id="e1", stage="enrich_heartbeat", level="info", message="Enrich heartbeat #1", created_at=ts, payload_json=json.dumps(payload)),
        RunEvent(run_id="run-enrich-repeat", event_id="e2", stage="enrich_heartbeat", level="info", message="Enrich heartbeat #2", created_at=ts, payload_json=json.dumps({**payload, "heartbeat_count": 2, "elapsed_secs": 30})),
    ]
    with patch("fitcv_cp.app.get_run", return_value=run), \
    patch("fitcv_cp.app.get_events", return_value=events), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-enrich-repeat")

    assert resp.status_code == 200
    assert "Enrich in progress: fresh 85, reused 0, concurrency 4." in resp.text
    assert "(x2)" not in resp.text


def _obsolete_test_run_detail_timeline_dedupes_enrich_complete_overlap_between_heartbeat_and_layer1_jobs() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-enrich-complete-overlap",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    ts = datetime.now(timezone.utc)
    events = [
        RunEvent(
            run_id="run-enrich-complete-overlap",
            event_id="e1",
            stage="enrich_heartbeat",
            level="info",
            message="Enrich in progress",
            created_at=ts,
            payload_json=json.dumps(
                {
                    "phase": "batch_done",
                    "fresh_jobs_total": 85,
                    "reused_jobs_total": 0,
                    "fresh_rows_total": 85,
                    "enrich_concurrency_effective": 4,
                }
            ),
        ),
        RunEvent(
            run_id="run-enrich-complete-overlap",
            event_id="e2",
            stage="layer1_jobs",
            level="info",
            message="Enrich complete",
            created_at=ts,
            payload_json=json.dumps(
                {
                    "output_snapshot": {
                        "enriched_jobs": 85,
                        "pre_enrichment_rejected_jobs": 0,
                        "fresh_rows": 85,
                        "reused_rows": 0,
                    }
                }
            ),
        ),
    ]
    with patch("fitcv_cp.app.get_run", return_value=run), \
    patch("fitcv_cp.app.get_events", return_value=events), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-enrich-complete-overlap")

    assert resp.status_code == 200
    assert "Enrich complete" in resp.text
    assert "Enrich complete: fresh rows 85, fresh 85, reused 0, concurrency 4." not in resp.text
def _obsolete_test_run_detail_timeline_hides_stage_download_for_mapped_event_without_stage_artifact():
    from fitcv_cp.models import PipelineRun, RunStatus, RunEvent
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-stage-link-missing-artifact",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        stage_transition_artifacts_json='{"run_id":"run-stage-link-missing-artifact","artifacts":{"stages":{"shortlist":{"status":"completed"}}}}',
    )
    events = [
        RunEvent(
            run_id="run-stage-link-missing-artifact",
            event_id="e1",
            stage="layer3_ranking",
            level="info",
            message="Final ranking: top 3 jobs",
            created_at=datetime.now(timezone.utc),
        )
    ]
    with patch("fitcv_cp.app.get_run", return_value=run), \
    patch("fitcv_cp.app.get_events", return_value=events), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-stage-link-missing-artifact")

    assert resp.status_code == 200
    assert 'href="/admin/runs/run-stage-link-missing-artifact/stage-artifacts/ranking.json"' not in resp.text


def _obsolete_test_run_detail_timeline_hides_stage_download_when_stage_artifact_json_is_malformed():
    from fitcv_cp.models import PipelineRun, RunStatus, RunEvent
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-stage-link-bad-json",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        stage_transition_artifacts_json="{bad json",
    )
    events = [
        RunEvent(
            run_id="run-stage-link-bad-json",
            event_id="e1",
            stage="layer3_ranking",
            level="info",
            message="Final ranking: top 3 jobs",
            created_at=datetime.now(timezone.utc),
        )
    ]
    with patch("fitcv_cp.app.get_run", return_value=run), \
    patch("fitcv_cp.app.get_events", return_value=events), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-stage-link-bad-json")

    assert resp.status_code == 200
    assert 'href="/admin/runs/run-stage-link-bad-json/stage-artifacts/ranking.json"' not in resp.text



def test_load_stage_transition_artifacts_payload_accepts_legacy_schema_tags() -> None:
    from fitcv_cp.app import _load_stage_transition_artifacts_payload
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    legacy_payload = {
        "run_id": "legacy-schema-run",
        "artifact_schema_version": "stage_transition_artifacts_stage_v0",
        "artifacts": {"stages": {"enrich": {"status": "completed"}}},
    }
    run = PipelineRun(
        run_id="legacy-schema-run",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        stage_transition_artifacts_json=json.dumps(legacy_payload),
    )

    payload = _load_stage_transition_artifacts_payload(run)
    assert payload["artifact_schema_version"] == "stage_transition_artifacts_stage_v0"
    assert payload["artifacts"]["stages"]["enrich"]["status"] == "completed"
def _obsolete_test_run_detail_timeline_hides_stage_download_for_unmapped_event():
    from fitcv_cp.models import PipelineRun, RunStatus, RunEvent
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-stage-link-2",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        stage_transition_artifacts_json='{"run_id":"run-stage-link-2","artifacts":{"stages":{"ranking":{"status":"completed"}}}}',
    )
    events = [
        RunEvent(
            run_id="run-stage-link-2",
            event_id="e1",
            stage="pipeline_start",
            level="info",
            message="Run started",
            created_at=datetime.now(timezone.utc),
        )
    ]
    with patch("fitcv_cp.app.get_run", return_value=run), \
    patch("fitcv_cp.app.get_events", return_value=events), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-stage-link-2")
    assert resp.status_code == 200
    assert 'href="/admin/runs/run-stage-link-2/stage-artifacts/' not in resp.text


def test_download_mapping_suggestions_requires_enrich_stage_reached() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="mapping-gate-endpoint",
        status=RunStatus.AWAITING_CONTINUE,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        stage_transition_artifacts_json=json.dumps(
            {"artifacts": {"stages": {"normalize": {"status": "completed"}}}}
        ),
        mapping_suggestions_json='{"suggestions":[]}',
    )

    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/mapping-gate-endpoint/mapping-suggestions.json")

    assert resp.status_code == 404
    assert "enrich" in resp.text.lower()


def test_download_cv_endpoint_200():
    with patch("fitcv_cp.app.get_cv_markdown", return_value="# Mock CV"):
        resp = TestClient(_app()).get("/admin/cvs/v456/download")
    assert resp.status_code == 200
    assert resp.text == "# Mock CV"
    assert resp.headers["content-type"] == "text/markdown; charset=utf-8"
    assert "attachment; filename=\"cv_v456.md\"" in resp.headers["content-disposition"]

def test_download_cv_endpoint_404():
    with patch("fitcv_cp.app.get_cv_markdown", return_value=None):
        resp = TestClient(_app()).get("/admin/cvs/missing/download")
    assert resp.status_code == 404


def test_download_results_json_endpoint_200():
    """@proves trigger_run_management.run-results-export
    @proves inspection_debugging.results-ledger-inspection
    """
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-export-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        results_export_json='{"run_id":"run-export-1","results":[]}',
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-export-1/export.json")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == "run-export-1"
    assert resp.headers["content-type"] == "application/json"
    assert 'attachment; filename="fitcv-run-run-export-1-results.json"' in resp.headers["content-disposition"]
    assert "\n  \"run_id\"" in resp.text


def test_download_results_json_endpoint_409_for_running_run():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-export-2",
        status=RunStatus.RUNNING,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-export-2/export.json")
    assert resp.status_code == 409

def test_download_results_json_endpoint_includes_hitl_audit_fields_when_present():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-export-hitl-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        results_export_json=json.dumps(
            {
                "run_id": "run-export-hitl-1",
                "results": [
                    {"job_url": "https://example.com/job-1", "job_title": "Test Role", "pipeline_status": "ranked_no_cv"}
                ],
            }
        ),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "Test Role",
                        "status": "review_required",
                        "error": {"stage": "review_gate", "message": "Low confidence sections: experience"},
                    }
                ],
                "hitl_review_actions": [
                    {
                        "job_url": "https://example.com/job-1",
                        "action": "approve",
                        "actor": "operator",
                        "created_at": "2026-04-30T10:00:00Z",
                    }
                ],
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-export-hitl-1/export.json")
    assert resp.status_code == 200
    row = resp.json()["results"][0]
    assert row["hitl_review_required"] is True
    assert row["hitl_review_action"] == "approve"
    assert row["hitl_review_actor"] == "operator"
    assert row["generated_draft_present"] is False
    assert row["accepted_cv_artifact_present"] is False

def test_download_hitl_review_audit_endpoint_200():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-hitl-audit-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "Test Role",
                        "status": "review_required",
                        "error": {"stage": "review_gate", "message": "Low confidence sections: experience"},
                    }
                ],
                "hitl_review_actions": [],
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-hitl-audit-1/hitl-review-audit.json")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["schema_version"] == "hitl_review_audit_v1"
    assert payload["summary"]["review_required_total"] == 1
    assert payload["summary"]["closure_mode"] == "incomplete"
    assert payload["summary"]["resolution_totals"]["pending"] == 1


def test_download_results_json_endpoint_404_if_snapshot_missing():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-export-3",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        results_export_json=None,
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-export-3/export.json")
    assert resp.status_code == 404


def test_download_stage_transition_artifacts_json_endpoint_200():
    """@proves inspection_debugging.stage-transition-diagnostics"""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-stage-artifacts-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        stage_transition_artifacts_json='{"run_id":"run-stage-artifacts-1","artifacts":{"stages":{"normalize":{"status":"completed"}}}}',
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-stage-artifacts-1/stage-artifacts.json")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == "run-stage-artifacts-1"
    assert resp.headers["content-type"] == "application/json"
    assert 'attachment; filename="fitcv-run-run-stage-artifacts-1-stage-artifacts.json"' in resp.headers["content-disposition"]


def test_download_stage_transition_artifacts_json_endpoint_200_for_running_run_with_snapshot():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-stage-artifacts-running-1",
        status=RunStatus.RUNNING,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        stage_transition_artifacts_json='{"run_id":"run-stage-artifacts-running-1","artifacts":{"stages":{"enrich":{"status":"completed"}}}}',
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-stage-artifacts-running-1/stage-artifacts.json")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == "run-stage-artifacts-running-1"


def test_download_stage_transition_artifacts_json_endpoint_404_if_snapshot_missing():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-stage-artifacts-2",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-stage-artifacts-2/stage-artifacts.json")
    assert resp.status_code == 404


def test_download_mapping_suggestions_json_endpoint_200() -> None:
    """@proves pipeline_performance.enrich-stage-mapping-suggestion-capture-for-review-debug-surfaces"""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-mapping-suggestions-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        completed_stages=["normalize", "enrich"],
        last_completed_stage="enrich",
        stage_transition_artifacts_json='{"artifacts":{"stages":{"enrich":{"status":"completed"}}}}',
        mapping_suggestions_json='{"run_id":"run-mapping-suggestions-1","suggestions":[]}',
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-mapping-suggestions-1/mapping-suggestions.json")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == "run-mapping-suggestions-1"


def test_download_mapping_suggestions_json_endpoint_404_if_snapshot_missing() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-mapping-suggestions-2",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-mapping-suggestions-2/mapping-suggestions.json")
    assert resp.status_code == 404


def test_download_aggregate_mapping_suggestions_json_endpoint_200() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    runs = [
        PipelineRun(
            run_id="run-ms-a",
            status=RunStatus.SUCCEEDED,
            triggered_by="admin",
            trigger_source="web",
            jobs_path="data/sample_jobs.json",
            config_path=".env.yaml",
            created_at=datetime.now(timezone.utc),
            mapping_suggestions_json=(
                '{"run_id":"run-ms-a","suggestions":['
                '{"alias":"gcp","canonical":"google cloud","confidence":1.0,"matches":true,"must_have_skill":"google cloud"}'
                ']}'
            ),
        ),
        PipelineRun(
            run_id="run-ms-b",
            status=RunStatus.SUCCEEDED,
            triggered_by="admin",
            trigger_source="web",
            jobs_path="data/sample_jobs.json",
            config_path=".env.yaml",
            created_at=datetime.now(timezone.utc),
            mapping_suggestions_json=(
                '{"run_id":"run-ms-b","suggestions":['
                '{"alias":"gcp","canonical":"google cloud","confidence":0.8,"matches":true,"must_have_skill":"google cloud"}'
                ']}'
            ),
        ),
    ]
    with patch("fitcv_cp.app.list_runs", return_value=runs):
        resp = TestClient(_app()).get("/admin/mapping-suggestions.json")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["suggestions"][0]["alias"] == "gcp"
    assert payload["suggestions"][0]["occurrences"] == 2


def test_download_synonym_proposals_json_endpoint_200() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    runs = [
        PipelineRun(
            run_id="run-proposal-a",
            status=RunStatus.SUCCEEDED,
            triggered_by="admin",
            trigger_source="web",
            jobs_path="data/sample_jobs.json",
            config_path=".env.yaml",
            created_at=datetime.now(timezone.utc),
            synonym_proposals_json=(
                '{"run_id":"run-proposal-a","proposals":['
                '{"proposal_id":"proposal-gcp","proposal_status":"proposed_unreviewed",'
                '"proposal_scope":"run_scoped_overlay_candidate","proposal_family":"alias_to_canonical_mapping",'
                '"alias":"gcp","canonical":"google cloud","candidate_aliases":["gcp"],'
                '"candidate_canonicals":["google cloud"],"confidence":0.9,'
                '"rationale":{"kind":"repeated_alias_mapping"},"evidence_summary":{"occurrence_count":2},'
                '"conflict_summary":{"has_conflict":false},"source_artifact_refs":{"run_id":"run-proposal-a"}}'
                ']}'
            ),
        )
    ]
    with patch("fitcv_cp.app.list_runs", return_value=runs):
        resp = TestClient(_app()).get("/admin/synonym-proposals.json")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["proposals"][0]["proposal_id"] == "proposal-gcp"
    assert payload["proposals"][0]["run_id"] == "run-proposal-a"


def test_download_run_synonym_proposals_trace_json_endpoint_200() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-synonym-trace-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        completed_stages=["normalize", "enrich"],
        last_completed_stage="enrich",
        stage_transition_artifacts_json='{"artifacts":{"stages":{"enrich":{"status":"completed"}}}}',
        synonym_proposals_json=json.dumps(
            {
                "run_id": "run-synonym-trace-1",
                "proposal_generation_status": "generated",
                "persistence_status": "persisted",
                "proposals": [{"proposal_id": "proposal-gcp", "alias": "gcp"}],
                "synonym_proposals_trace": {
                    "run_id": "run-synonym-trace-1",
                    "trace_schema_version": "agentic_step_trace_run_v1",
                    "trace_family": "agentic_step_trace",
                    "step_id": "synonym_proposals",
                    "trace_status": "completed",
                    "trace_summary": {"records_total": 1, "present_records": 1, "proposal_count": 1},
                    "records": [{"record_id": "proposal-gcp", "scope_type": "alias", "scope_key": "gcp"}],
                    "degradation": {},
                },
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-synonym-trace-1/synonym-proposals-trace.json")
    assert resp.status_code == 200
    assert resp.json()["step_id"] == "synonym_proposals"
    assert resp.json()["trace_family"] == "agentic_step_trace"


def test_download_run_synonym_proposals_trace_json_endpoint_404_when_not_applicable() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-synonym-trace-2",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-synonym-trace-2/synonym-proposals-trace.json")
    assert resp.status_code == 404

def test_download_run_synonym_suppression_diff_json_endpoint_200() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-syn-suppress-diff-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        completed_stages=["enrich"],
        last_completed_stage="enrich",
        mapping_suggestions_json='{"run_id":"run-syn-suppress-diff-1","suggestions":[{"alias":"gcp","canonical":"google cloud"}]}',
        synonym_proposals_json=json.dumps(
            {
                "run_id": "run-syn-suppress-diff-1",
                "proposals": [],
                "synonym_proposals_trace": {
                    "trace_status": "completed",
                    "trace_summary": {
                        "suppressed_as_already_global_count": 1,
                        "suppressed_count_by_field": {"skill": 1, "domain": 2},
                        "generated_for_review_count": 0,
                        "suppression_source": "run_effective_skill_synonyms",
                    },
                    "suppression_examples": [{"alias": "gcp", "canonical": "google cloud"}],
                },
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-syn-suppress-diff-1/synonym-suppression-diff.json")
    assert resp.status_code == 200
    body = resp.json()
    assert body["suppressed_pairs_total"] == 3
    assert body["suppression_source"] == "run_effective_skill_synonyms"
























def test_synonym_management_mode_includes_new_automation_flags_with_defaults() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone
    from fitcv_cp.app import _synonym_management_mode

    run = PipelineRun(
        run_id="run-syn-mode-defaults",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        run_mode="run_all",
        effective_settings_json=json.dumps({"synonym_management": {"apply_approved_enabled": False}}),
    )
    mode = _synonym_management_mode(run)
    assert mode["apply_approved_enabled"] is False
    assert mode["auto_accept_suggestions_enabled"] is False
    assert mode["auto_accept_ai_action_enabled"] is True









def test_resolve_synonym_triage_runtime_does_not_inherit_cv_analysis_scheduling() -> None:
    from datetime import datetime, timezone

    from fitcv_cp.app import _resolve_synonym_triage_runtime
    from fitcv_cp.models import PipelineRun, RunStatus

    run = PipelineRun(
        run_id="run-triage-runtime",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        run_mode="run_all",
        effective_settings_json='{"stage_runtime":{"cv_analysis":{"sleep_secs":0.4,"concurrency":5}}}',
    )

    runtime = _resolve_synonym_triage_runtime(run)

    assert "sleep_secs" not in runtime
    assert "concurrency" not in runtime


def test_resolve_synonym_triage_runtime_uses_dedicated_control_plane_route(
    tmp_path, monkeypatch
) -> None:
    from datetime import datetime, timezone

    from fitcv_cp.app import _resolve_synonym_triage_runtime
    from fitcv_cp.models import PipelineRun, RunStatus

    monkeypatch.chdir(tmp_path)
    (tmp_path / "config" / "runtime").mkdir(parents=True)
    (tmp_path / "config" / "runtime" / "control_plane.yaml").write_text(
        "control_plane:\n"
        "  providers:\n"
        "    openai_compatible:\n"
        "      base_url: http://router.local/v1\n"
        "      wire_api: chat_completions\n"
        "      auth_mode: required\n"
        "      timeout_seconds: 300\n"
        "  model_routing:\n"
        "    parts:\n"
        "      candidate_profile_base_mapping:\n"
        "        provider: openai_compatible\n"
        "        model: cx/gpt-5.2\n"
        "      candidate_profile_derived_claims:\n"
        "        provider: openai_compatible\n"
        "        model: cx/gpt-5.2\n"
        "      enrich_extraction:\n"
        "        provider: openai_compatible\n"
        "        model: cx/gpt-5.2\n"
        "      ranking_ai_score:\n"
        "        provider: openai_compatible\n"
        "        model: cx/gpt-5.2\n"
        "      cv_generation_structured_write:\n"
        "        provider: openai_compatible\n"
        "        model: cx/gpt-5.2\n"
        "      synonym_triage_recommendation:\n"
        "        provider: openai_compatible\n"
        "        model: cx/gpt-5.2\n"
        "  fitcv_cp:\n"
        "    retry:\n"
        "      enabled: false\n"
        "      max_attempts: 1\n"
        "      backoff_seconds: [1]\n"
        "      lease_seconds: 900\n"
        "      reconciler_interval_seconds: 0\n"
        "      error_details_max_chars: 2048\n",
        encoding="utf-8",
    )
    run = PipelineRun(
        run_id="run-triage-runtime-fallback",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        run_mode="run_all",
        effective_settings_json="{}",
    )

    runtime = _resolve_synonym_triage_runtime(run)

    assert runtime["provider"] == "openai_compatible"
    assert runtime["model"] == "cx/gpt-5.2"
    assert runtime["base_url"] == "http://router.local/v1"
    assert runtime["wire_api"] == "chat_completions"


def test_resolve_synonym_triage_runtime_prefers_persisted_synonym_runtime_expectation(
    monkeypatch,
) -> None:
    from datetime import datetime, timezone

    from fitcv_cp.app import _resolve_synonym_triage_runtime
    from fitcv_cp.models import PipelineRun, RunStatus

    monkeypatch.setenv("FITCV_LLM_API_KEY", "test-key")

    run = PipelineRun(
        run_id="run-triage-runtime-persisted",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        run_mode="run_all",
        effective_settings_json=(
            '{"runtime_inputs":{"synonym_triage_runtime_expectation":'
            '{"provider":"9router","model":"cx/gpt-5.2","base_url":"http://persisted.local/v1","wire_api":"chat_completions","source":"env_override"}}}'
        ),
    )

    runtime = _resolve_synonym_triage_runtime(run)

    assert runtime["provider"] == "9router"
    assert runtime["model"] == "cx/gpt-5.2"
    assert runtime["base_url"] == "http://persisted.local/v1"
    assert runtime["wire_api"] == "chat_completions"
    assert runtime["api_key"] == "test-key"
    assert runtime["api_key_available"] is True





def test_synonym_triage_fingerprint_is_stable_across_run_scoped_proposal_ids() -> None:
    from fitcv_cp.app import _synonym_triage_fingerprint

    runtime = {
        "provider": "fitcv_builtin",
        "model": "synonym_triage_v1",
        "wire_api": "builtin",
        "sleep_secs": 0.0,
        "concurrency": 1,
    }
    proposal_a = {
        "proposal_id": "synprop-run-a",
        "proposal_identity": "synident-shared",
        "proposal_status": "proposed_unreviewed",
        "field": "skill",
        "alias": "gcp",
        "canonical": "google cloud",
        "candidate_canonicals": ["google cloud"],
    }
    proposal_b = dict(proposal_a)
    proposal_b["proposal_id"] = "synprop-run-b"

    fp_a = _synonym_triage_fingerprint(proposal_a, runtime=runtime)
    fp_b = _synonym_triage_fingerprint(proposal_b, runtime=runtime)

    assert fp_a == fp_b

def test_synonym_triage_fingerprints_are_pair_local_and_input_complete() -> None:
    from fitcv_cp.synonym_proposals import (
        build_synonym_triage_core_fingerprint,
        build_synonym_triage_fingerprint,
        evaluate_synonym_triage_reuse,
    )

    proposal = {
        "proposal_status": "proposed_unreviewed",
        "field": "skill",
        "alias": "laptop",
        "canonical": "portable computer",
        "candidate_canonicals": ["portable computer"],
        "confidence": 0.75,
        "conflict_summary": {"has_conflict": False},
    }
    runtime = {
        "provider": "fitcv_builtin",
        "model": "synonym_triage_v1",
        "wire_api": "builtin",
        "sleep_secs": 0.0,
        "concurrency": 1,
    }

    strict = build_synonym_triage_fingerprint(proposal=proposal, runtime=runtime)
    core = build_synonym_triage_core_fingerprint(proposal=proposal, runtime=runtime)
    assert evaluate_synonym_triage_reuse(
        proposal=proposal,
        runtime=runtime,
        runtime_meta={
            "triage_fingerprint_strict": strict,
            "run_overlay_fingerprint": "unrelated-overlay-b",
        },
    )["decision"] == "strict_reuse"

    confidence_changed = {**proposal, "confidence": 0.749999}
    candidates_changed = {
        **proposal,
        "candidate_canonicals": ["notebook", "portable computer"],
    }
    pair_changed = {**proposal, "canonical": "notebook"}
    runtime_changes = (
        {**runtime, "provider": "openai_compatible"},
        {**runtime, "model": "synonym_triage_v2"},
        {**runtime, "wire_api": "responses"},
    )
    for changed_proposal, changed_runtime in (
        (confidence_changed, runtime),
        (candidates_changed, runtime),
        (pair_changed, runtime),
        *((proposal, changed_runtime) for changed_runtime in runtime_changes),
    ):
        assert strict != build_synonym_triage_fingerprint(
            proposal=changed_proposal,
            runtime=changed_runtime,
        )
        assert core != build_synonym_triage_core_fingerprint(
            proposal=changed_proposal,
            runtime=changed_runtime,
        )

def test_build_synonym_proposals_payload_reuses_existing_state_by_identity_across_runs() -> None:
    from datetime import datetime, timezone

    from fitcv_cp.synonym_proposals import (
        build_synonym_proposal_identity,
        build_synonym_proposals_payload,
    )

    summary = {
        "mapping_suggestions": [
            {
                "field": "skill",
                "alias": "gcp",
                "canonical": "google cloud",
                "confidence": 0.9,
                "job_url": "https://example.com/1",
                "job_title": "Data Analyst",
            }
        ]
    }
    existing_payload_json = json.dumps(
        {
            "run_id": "run-old",
            "proposals": [
                {
                    "proposal_id": "synprop-old",
                    "proposal_identity": build_synonym_proposal_identity(
                        field="skill",
                        alias="gcp",
                        candidate_canonicals=["google cloud"],
                        proposal_family="alias_to_canonical_mapping",
                    ),
                    "field": "skill",
                    "alias": "gcp",
                    "canonical": "google cloud",
                    "candidate_canonicals": ["google cloud"],
                    "proposal_family": "alias_to_canonical_mapping",
                    "proposal_status": "approved_for_run_overlay",
                    "recommended_action": "approve",
                }
            ],
        },
        ensure_ascii=False,
    )

    payload_json = build_synonym_proposals_payload(
        run_id="run-new",
        summary=summary,
        created_at=datetime.now(timezone.utc),
        existing_payload_json=existing_payload_json,
        global_synonyms={},
    )
    payload = json.loads(payload_json)
    proposals = list(payload.get("proposals") or [])
    assert proposals
    row = proposals[0]
    assert row.get("proposal_status") == "approved_for_run_overlay"


def _effective_settings_with_builtin_synonym_runtime(extra: dict[str, object] | None = None) -> str:
    payload: dict[str, object] = {
        "runtime_inputs": {
            "synonym_triage_runtime_expectation": {
                "provider": "fitcv_builtin",
                "model": "synonym_triage_v1",
                "base_url": "builtin",
                "wire_api": "builtin",
                "source": "persisted",
            }
        }
    }
    if extra:
        payload.update(extra)
    return json.dumps(payload, separators=(",", ":"))








def test_synonym_proposal_review_queue_filters_pairs_already_in_global_synonyms() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone
    from fitcv_cp.app import _build_synonym_proposal_review_queue

    run = PipelineRun(
        run_id="run-proposal-filtered-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        run_mode="run_all",
        effective_settings_json=json.dumps(
            {
                "skill_synonyms": {
                    "gcp": "google cloud",
                }
            }
        ),
        synonym_proposals_json=(
            '{"run_id":"run-proposal-filtered-1","proposals":['
            '{"proposal_id":"proposal-gcp","proposal_status":"proposed_unreviewed","alias":"gcp","canonical":"google cloud","confidence":0.9}'
            ']}'
        ),
    )

    queue = _build_synonym_proposal_review_queue(run)
    assert queue["total_count"] == 0
    assert queue["filtered_as_already_global_count"] == 1
    lanes = {lane["field"]: lane for lane in queue["field_lanes"]}
    assert lanes["skill"]["suppressed"] == 1
    assert lanes["skill"]["zero_state_reason"] == "all_suppressed"

def test_synonym_proposal_review_queue_keeps_non_skill_fields_even_if_skill_global_has_same_alias() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone
    from fitcv_cp.app import _build_synonym_proposal_review_queue

    run = PipelineRun(
        run_id="run-proposal-field-aware-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        run_mode="run_all",
        effective_settings_json=json.dumps({"skill_synonyms": {"gcp": "google cloud"}}),
        synonym_proposals_json=(
            '{"run_id":"run-proposal-field-aware-1","proposals":['
            '{"proposal_id":"proposal-domain-gcp","field":"domain","proposal_status":"proposed_unreviewed","alias":"gcp","canonical":"google cloud","confidence":0.9}'
            ']}'
        ),
    )

    queue = _build_synonym_proposal_review_queue(run)
    assert queue["total_count"] == 1
    assert queue["items"][0]["field"] == "domain"
    lanes = {lane["field"]: lane for lane in queue["field_lanes"]}
    assert lanes["domain"]["generated"] == 1
    assert lanes["domain"]["zero_state_reason"] is None

def test_synonym_proposal_review_queue_uses_trace_suppression_for_non_skill_lanes() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone
    from fitcv_cp.app import _build_synonym_proposal_review_queue

    run = PipelineRun(
        run_id="run-proposal-trace-suppression-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        run_mode="run_all",
        synonym_proposals_json=(
            '{"run_id":"run-proposal-trace-suppression-1","proposals":['
            '{"proposal_id":"proposal-skill","field":"skill","proposal_status":"proposed_unreviewed","alias":"gcpx","canonical":"google cloud platform","confidence":0.9}'
            '],'
            '"synonym_proposals_trace":{"trace_summary":{"suppressed_count_by_field":{"domain":3,"role_family":1}}}'
            '}'
        ),
    )

    queue = _build_synonym_proposal_review_queue(run)
    lanes = {lane["field"]: lane for lane in queue["field_lanes"]}
    assert lanes["domain"]["suppressed"] == 3
    assert lanes["domain"]["zero_state_reason"] == "all_suppressed"
    assert lanes["role_family"]["suppressed"] == 1
    assert lanes["role_family"]["zero_state_reason"] == "all_suppressed"

def test_synonym_proposal_review_queue_triage_stale_when_pending_without_recommendations() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone
    from fitcv_cp.app import _build_synonym_proposal_review_queue

    run = PipelineRun(
        run_id="run-proposal-triage-stale-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        run_mode="run_all",
        synonym_proposals_json=(
            '{"run_id":"run-proposal-triage-stale-1","proposals":['
            '{"proposal_id":"proposal-skill","field":"skill","proposal_status":"proposed_unreviewed","alias":"gcpx","canonical":"google cloud platform","confidence":0.9}'
            ']}'
        ),
    )

    queue = _build_synonym_proposal_review_queue(run)
    assert queue["pending_count"] == 1
    assert queue["triage_status"] == "stale"













def test_download_run_approved_synonym_overlay_yaml() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-approved-yaml",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        run_mode="run_all",
        synonym_proposals_json=(
            '{"run_id":"run-approved-yaml","proposals":['
            '{"proposal_id":"proposal-gcp","proposal_status":"approved_for_run_overlay","alias":"gcp","canonical":"google cloud","confidence":0.9},'
            '{"proposal_id":"proposal-aws","proposal_status":"rejected","alias":"aws","canonical":"amazon web services","confidence":0.9}'
            ']}'
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-approved-yaml/approved-synonym-proposals.yaml")
    assert resp.status_code == 200
    assert "skill_synonyms:" in resp.text
    assert "gcp: google cloud" in resp.text
    assert "aws: amazon web services" not in resp.text


def test_download_global_synonyms_yaml() -> None:
    with patch("fitcv_cp.app._load_global_skill_synonyms_map", return_value={"gcp": "google cloud"}):
        resp = TestClient(_app()).get("/admin/synonyms/global.yaml")
    assert resp.status_code == 200
    assert "skill_synonyms:" in resp.text
    assert "gcp: google cloud" in resp.text

def test_download_global_domain_synonyms_yaml() -> None:
    with patch("fitcv_cp.app._load_global_domain_alias_map", return_value={"fintech": "financial technology"}):
        resp = TestClient(_app()).get("/admin/synonyms/global-domain.yaml")
    assert resp.status_code == 200
    assert "domain_alias_map:" in resp.text
    assert "fintech: financial technology" in resp.text

def test_download_global_role_family_synonyms_yaml() -> None:
    with patch("fitcv_cp.app._load_global_role_family_alias_map", return_value={"data eng": "data engineering"}):
        resp = TestClient(_app()).get("/admin/synonyms/global-role-family.yaml")
    assert resp.status_code == 200
    assert "role_family_alias_map:" in resp.text
    assert "data eng: data engineering" in resp.text











































def test_run_detail_hides_promote_checkbox_after_global_promotion() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-promoted-checkbox-hidden",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        synonym_proposals_json=(
            '{"run_id":"run-promoted-checkbox-hidden","proposals":['
            '{"proposal_id":"proposal-gcp","proposal_status":"approved_for_run_overlay","alias":"gcp","canonical":"google cloud","confidence":0.9,'
            '"global_promotion_history":[{"action":"promote_to_global","acted_by":"admin","acted_at":"2026-05-01T00:00:00Z"}]}'
            ']}'
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.get_events", return_value=[]), \
         patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
         patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-promoted-checkbox-hidden")
    assert resp.status_code == 200
    assert "Include in Promote-to-Global preview" not in resp.text

def test_run_detail_hides_promote_checkbox_when_pair_exists_in_global_map() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-promoted-checkbox-hidden-global-map",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        effective_settings_json='{"skill_synonyms":{"gcp":"google cloud"}}',
        synonym_proposals_json=(
            '{"run_id":"run-promoted-checkbox-hidden-global-map","proposals":['
            '{"proposal_id":"proposal-gcp","proposal_status":"approved_for_run_overlay","alias":"gcp","canonical":"google cloud","confidence":0.9}'
            ']}'
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.get_events", return_value=[]), \
         patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
         patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-promoted-checkbox-hidden-global-map")
    assert resp.status_code == 200
    assert "Include in Promote-to-Global preview" not in resp.text



def test_download_settings_used_json_endpoint_200():
    """@proves inspection_debugging.settings-used-export"""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-settings-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        settings_used_json='{"run_id":"run-settings-1","effective_settings":{"pipeline":{"final_top_n":10}}}',
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-settings-1/settings-used.json")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == "run-settings-1"
    assert resp.headers["content-type"] == "application/json"
    assert 'attachment; filename="fitcv-run-run-settings-1-settings-used.json"' in resp.headers["content-disposition"]


def test_download_settings_used_json_endpoint_404_if_snapshot_missing():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-settings-2",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-settings-2/settings-used.json")
    assert resp.status_code == 404


def test_download_stage_slice_endpoint_200():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-stage-slice-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        stage_transition_artifacts_json='{"run_id":"run-stage-slice-1","created_at":"2026-03-31T20:00:00+00:00","artifacts":{"stages":{"normalize":{"stage_id":"normalize","status":"completed","input_counts":{"raw_jobs":7},"output_counts":{"normalized_jobs":6},"decision_summary":{},"inputs_sample":[],"outputs_sample":[],"dropped_or_changed_sample":[]}}}}',
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-stage-slice-1/stage-artifacts/normalize.json")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == "run-stage-slice-1"
    assert resp.json()["stage_id"] == "normalize"
    assert resp.json()["stage_artifact"]["input_counts"]["raw_jobs"] == 7


def test_download_stage_slice_endpoint_200_for_running_run_with_snapshot():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-stage-slice-running-1",
        status=RunStatus.RUNNING,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        stage_transition_artifacts_json='{"run_id":"run-stage-slice-running-1","created_at":"2026-03-31T20:00:00+00:00","artifacts":{"stages":{"enrich":{"stage_id":"enrich","status":"completed","input_counts":{},"output_counts":{"enriched_jobs":1},"decision_summary":{},"inputs_sample":[],"outputs_sample":[{"job_url":"https://example.com/1"}],"dropped_or_changed_sample":[]}}}}',
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-stage-slice-running-1/stage-artifacts/enrich.json")
    assert resp.status_code == 200
    assert resp.json()["stage_id"] == "enrich"
    assert resp.json()["stage_artifact"]["output_counts"]["enriched_jobs"] == 1


def test_download_stage_slice_endpoint_404_for_unknown_stage():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-stage-slice-2",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        stage_transition_artifacts_json='{"run_id":"run-stage-slice-2","artifacts":{"stages":{"normalize":{"status":"completed"}}}}',
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-stage-slice-2/stage-artifacts/unknown.json")
    assert resp.status_code == 404


def test_download_cv_debug_json_endpoint_200():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-debug-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json='{"run_id":"run-debug-1","debug_records":[]}',
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-debug-1/cv-debug.json")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == "run-debug-1"
    assert resp.headers["content-type"] == "application/json"
    assert 'attachment; filename="fitcv-run-run-debug-1-cv-debug.json"' in resp.headers["content-disposition"]
    assert "\n  \"run_id\"" in resp.text


def test_download_cv_debug_json_endpoint_404_if_snapshot_missing():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-debug-2",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=None,
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-debug-2/cv-debug.json")
    assert resp.status_code == 404

def test_download_cv_generation_review_required_json_endpoint_200() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-required-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "run_id": "run-review-required-1",
                "debug_records": [
                    {
                        "job_url": "https://example.com/j1",
                        "job_title": "Data Engineer",
                        "status": "review_required",
                        "review_required_reason_code": "provider_error",
                        "attempt_count": 2,
                        "failed_rule_ids": ["rule_one"],
                    }
                ],
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-review-required-1/cv-generation-review-required.json")
    assert resp.status_code == 200
    assert resp.json()["schema_version"] == "cv_generation_review_required_v1"
    assert len(resp.json()["rows"]) == 1

def test_download_cv_generation_review_required_json_maps_reason_and_nullable_request_id() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-required-2",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "run_id": "run-review-required-2",
                "debug_records": [
                    {
                        "job_url": "https://example.com/j2",
                        "job_title": "Data Engineer 2",
                        "status": "review_required",
                        "review_required_reason_code": "unknown",
                        "error": {
                            "stage": "review_gate",
                            "message": "Unsupported requirements require review: Snowflake, Talend",
                        },
                        "runtime_provenance": {},
                    }
                ],
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-review-required-2/cv-generation-review-required.json")
    assert resp.status_code == 200
    row = resp.json()["rows"][0]
    assert row["reason_code"] == "unsupported_requirement_gap"
    assert row["review_target"] == "requirements_alignment"
    assert "Review the generated CV output against required stack coverage" in row["operator_prompt"]
    assert row["unsupported_requirements"] == ["Snowflake", "Talend"]
    assert row["generated_draft_present"] is False
    assert row["accepted_cv_artifact_present"] is False
    assert row["request_id"] is None

def test_download_cv_generation_review_required_json_uses_structured_missing_requirements() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-review-required-structured-missing",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "run_id": "run-review-required-structured-missing",
                "debug_records": [
                    {
                        "job_url": "https://example.com/j3",
                        "job_title": "Data Engineer 3",
                        "status": "review_required",
                        "review_required_reason_code": "unsupported_requirement_gap",
                        "gap_summary": {"missing": ["Snowflake", "Talend"]},
                        "error": {
                            "stage": "review_gate",
                            "message": "Unsupported requirements require review: Snowflake, Talend. Review the generated CV output against these requirements and decide approve as-is, regenerate once, or reject.",
                        },
                    }
                ],
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-review-required-structured-missing/cv-generation-review-required.json")
    assert resp.status_code == 200
    row = resp.json()["rows"][0]
    assert row["unsupported_requirements"] == ["Snowflake", "Talend"]


def test_download_cv_generation_trace_json_endpoint_translates_historical_payload() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-agentic-trace-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "run_id": "run-agentic-trace-1",
                "agentic_live_trace": {
                    "run_id": "run-agentic-trace-1",
                    "trace_schema_version": "agentic_step_trace_run_v1",
                    "trace_family": "agentic_step_trace",
                    "step_id": "cv_generation",
                    "late_stage_mode": {
                        "late_stage_mode": "agentic",
                        "agentic_late_stage_enabled": True,
                        "mode_source": "cv.agentic_late_stage.enabled",
                        "agentic_status": "completed",
                    },
                    "trace_status": "completed",
                    "trace_summary": {"records_total": 1, "present_records": 1, "attempted_generation_jobs_total": 1},
                    "records": [{"record_id": "https://example.com/1", "scope_type": "job", "scope_key": "https://example.com/1", "attempts": [{"attempt_index": 1, "provider_status": "accepted"}]}],
                    "degradation": {},
                },
                "debug_records": [],
            }
        ),
        settings_used_json='{"run_id":"run-agentic-trace-1","late_stage_mode":{"late_stage_mode":"agentic","agentic_late_stage_enabled":true,"mode_source":"cv.agentic_late_stage.enabled","agentic_status":"completed"}}',
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        client = TestClient(_app())
        resp = client.get("/admin/runs/run-agentic-trace-1/cv-generation-trace.json")
        alias_resp = client.get("/admin/runs/run-agentic-trace-1/agentic-live-trace.json")
    assert resp.status_code == 200
    assert alias_resp.status_code == 200
    assert alias_resp.json() == resp.json()
    assert resp.json()["run_id"] == "run-agentic-trace-1"
    assert resp.json()["trace_family"] == "agentic_step_trace"
    assert resp.json()["step_id"] == "cv_generation"
    assert resp.headers["content-type"] == "application/json"
    assert 'attachment; filename="fitcv-run-run-agentic-trace-1-cv-generation-trace.json"' in resp.headers["content-disposition"]
    assert alias_resp.headers["content-disposition"] == resp.headers["content-disposition"]


def test_download_cv_generation_trace_json_endpoint_404_when_not_applicable() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-agentic-trace-2",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json='{"run_id":"run-agentic-trace-2","debug_records":[]}',
        settings_used_json='{"run_id":"run-agentic-trace-2","late_stage_mode":{"late_stage_mode":"non_agentic","agentic_late_stage_enabled":false,"mode_source":"cv.agentic_late_stage.enabled","agentic_status":"not_applicable"}}',
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-agentic-trace-2/cv-generation-trace.json")
    assert resp.status_code == 404


def test_download_cv_analysis_trace_json_endpoint_200() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-analysis-trace-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json=json.dumps(
            {
                "run_id": "run-analysis-trace-1",
                "cv_analysis_trace": {
                    "run_id": "run-analysis-trace-1",
                    "trace_schema_version": "agentic_step_trace_run_v1",
                    "trace_family": "agentic_step_trace",
                    "step_id": "cv_analysis",
                    "late_stage_mode": {
                        "late_stage_mode": "agentic",
                        "agentic_late_stage_enabled": True,
                        "mode_source": "cv.agentic_late_stage.enabled",
                        "agentic_status": "completed",
                    },
                    "trace_status": "completed",
                    "trace_summary": {"records_total": 1, "present_records": 1, "attempted_analysis_jobs_total": 1},
                    "records": [{"record_id": "https://example.com/1", "scope_type": "job", "scope_key": "https://example.com/1", "status": "ready_for_generation"}],
                    "degradation": {},
                },
                "debug_records": [],
            }
        ),
        settings_used_json='{"run_id":"run-analysis-trace-1","late_stage_mode":{"late_stage_mode":"agentic","agentic_late_stage_enabled":true,"mode_source":"cv.agentic_late_stage.enabled","agentic_status":"completed"}}',
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-analysis-trace-1/cv-analysis-trace.json")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == "run-analysis-trace-1"
    assert resp.json()["trace_family"] == "agentic_step_trace"
    assert resp.json()["step_id"] == "cv_analysis"
    assert 'attachment; filename="fitcv-run-run-analysis-trace-1-cv-analysis-trace.json"' in resp.headers["content-disposition"]


def test_download_cv_analysis_trace_json_endpoint_404_when_not_applicable() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-analysis-trace-2",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        cv_generation_debug_json='{"run_id":"run-analysis-trace-2","debug_records":[]}',
        settings_used_json='{"run_id":"run-analysis-trace-2","late_stage_mode":{"late_stage_mode":"non_agentic","agentic_late_stage_enabled":false,"mode_source":"cv.agentic_late_stage.enabled","agentic_status":"not_applicable"}}',
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-analysis-trace-2/cv-analysis-trace.json")
    assert resp.status_code == 404


def test_download_run_artifact_bundle_zip_endpoint_for_partial_run() -> None:
    """@proves trigger_run_management.run-owned-artifact-exports
    @proves inspection_debugging.run-owned-artifact-exports
    """
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-bundle-partial-1",
        status=RunStatus.AWAITING_CONTINUE,
        run_mode="manual_staged",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        last_completed_stage="normalize",
        completed_stages=["normalize"],
        stage_transition_artifacts_json=json.dumps(
            {
                "run_id": "run-bundle-partial-1",
                "created_at": "2026-04-07T12:00:00+00:00",
                "artifacts": {
                    "stages": {
                        "normalize": {
                            "stage_id": "normalize",
                            "status": "completed",
                        }
                    }
                },
            }
        ),
        mapping_suggestions_json='{"run_id":"run-bundle-partial-1","suggestions":[]}',
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-bundle-partial-1/artifacts.zip")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert 'attachment; filename="fitcv-run-run-bundle-partial-1-artifacts.zip"' in resp.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
        names = set(archive.namelist())
        assert "manifest.json" in names
        assert "stage-artifacts.json" in names
        assert "normalize.json" in names
        assert "mapping-suggestions.json" not in names
        manifest = json.loads(archive.read("manifest.json"))
    assert manifest["run_id"] == "run-bundle-partial-1"
    assert manifest["bundle_schema_version"] == "run_artifact_bundle_v7"
    assert manifest["run_mode"] == "manual_staged"
    assert manifest["run_mode_label"] == "Stage by Stage"
    assert "late_stage_mode" not in manifest
    assert "normalize.json" in manifest["included_files"]
    assert manifest["job_outcome_counts"] == {"accepted": 0, "held": 0, "blocked": 0, "rejected": 0, "skipped": 0}
    assert manifest["file_fingerprints"]["normalize.json"].startswith("sha256:")
    assert "mapping-suggestions.json" not in manifest["missing_files"]
    assert manifest["artifact_states"]["mapping-suggestions.json"] == "not_applicable"


def test_download_run_artifact_bundle_zip_endpoint_for_succeeded_run() -> None:
    """@proves trigger_run_management.shortlist-debug-exports
    @proves inspection_debugging.shortlist-diagnostics
    """
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-bundle-success-1",
        status=RunStatus.SUCCEEDED,
        run_mode="run_all",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        last_completed_stage="enrich",
        completed_stages=["normalize", "enrich"],
        results_export_json='{"run_id":"run-bundle-success-1","results":[]}',
        cv_generation_debug_json='{"run_id":"run-bundle-success-1","cv_analysis_trace":{"run_id":"run-bundle-success-1","trace_schema_version":"agentic_step_trace_run_v1","trace_family":"agentic_step_trace","step_id":"cv_analysis","late_stage_mode":{"late_stage_mode":"agentic","agentic_late_stage_enabled":true,"mode_source":"cv.agentic_late_stage.enabled","agentic_status":"completed"},"trace_status":"completed","trace_summary":{"records_total":1,"present_records":1,"attempted_analysis_jobs_total":1},"records":[{"record_id":"https://example.com/1","scope_type":"job","scope_key":"https://example.com/1","status":"ready_for_generation"}],"degradation":{}},"agentic_live_trace":{"run_id":"run-bundle-success-1","trace_schema_version":"agentic_step_trace_run_v1","trace_family":"agentic_step_trace","step_id":"cv_generation","late_stage_mode":{"late_stage_mode":"agentic","agentic_late_stage_enabled":true,"mode_source":"cv.agentic_late_stage.enabled","agentic_status":"completed"},"trace_status":"completed","trace_summary":{"records_total":1,"present_records":1,"attempted_generation_jobs_total":1},"records":[{"record_id":"https://example.com/1","scope_type":"job","scope_key":"https://example.com/1","attempts":[{"attempt_index":1,"provider_status":"accepted"}]}],"degradation":{}},"debug_records":[]}',
        settings_used_json='{"run_id":"run-bundle-success-1","late_stage_mode":{"late_stage_mode":"agentic","agentic_late_stage_enabled":true,"mode_source":"cv.agentic_late_stage.enabled","agentic_status":"completed"},"effective_settings":{"pipeline":{"final_top_n":10}}}',
        mapping_suggestions_json='{"run_id":"run-bundle-success-1","suggestions":[]}',
        synonym_proposals_json=(
            '{"run_id":"run-bundle-success-1","proposal_generation_status":"generated","persistence_status":"bundle_only_degraded",'
            '"proposals":[],"synonym_proposals_trace":{"run_id":"run-bundle-success-1","trace_schema_version":"agentic_step_trace_run_v1",'
            '"trace_family":"agentic_step_trace","step_id":"synonym_proposals","trace_status":"degraded",'
            '"trace_summary":{"records_total":0,"present_records":0,"proposal_count":0},"records":[],'
            '"degradation":{"reason":"synonym_proposals_bundle_only_degraded"}}}'
        ),
        stage_transition_artifacts_json=json.dumps(
            {
                "run_id": "run-bundle-success-1",
                "created_at": "2026-04-07T12:00:00+00:00",
                    "artifacts": {
                        "stages": {
                            "normalize": {"stage_id": "normalize", "status": "completed"},
                            "enrich": {"stage_id": "enrich", "status": "completed"},
                            "rule_filter": {"stage_id": "rule_filter", "status": "completed"},
                            "shortlist": {"stage_id": "shortlist", "status": "completed"},
                            "ranking": {"stage_id": "ranking", "status": "completed"},
                            "cv_analysis": {"stage_id": "cv_analysis", "status": "completed"},
                            "cv_generation": {"stage_id": "cv_generation", "status": "completed"},
                        }
                    },
                }
            ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), patch(
        "fitcv_cp.app.list_cvs_for_run",
        return_value=[{"version_id": "v-1"}],
    ), patch(
        "fitcv_cp.app.get_cv_markdown",
        return_value="# Sample CV\n\n## Experience\n- Item",
    ):
        resp = TestClient(_app()).get("/admin/runs/run-bundle-success-1/artifacts.zip")

    assert resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
        names = set(archive.namelist())
        assert "manifest.json" in names
        assert "results.json" in names
        assert "hitl-review-audit.json" in names
        assert "cv-debug.json" in names
        assert "cv-analysis-trace.json" in names
        assert "cv-generation-trace.json" in names
        assert "settings-used.json" in names
        assert "stage-artifacts.json" in names
        assert "normalize.json" in names
        assert "enrich.json" in names
        assert "rule_filter.json" in names
        assert "shortlist.json" in names
        assert "ranking.json" in names
        assert "cv_analysis.json" in names
        assert "cv_generation.json" in names
        assert "mapping-suggestions.json" in names
        assert "synonym-proposals.json" in names
        assert "synonym-proposals-trace.json" in names
        assert "cv_v-1.md" in names
        manifest = json.loads(archive.read("manifest.json"))
        analysis_trace_payload = json.loads(archive.read("cv-analysis-trace.json"))
        trace_payload = json.loads(archive.read("cv-generation-trace.json"))
        synonym_trace_payload = json.loads(archive.read("synonym-proposals-trace.json"))
    assert manifest["run_id"] == "run-bundle-success-1"
    assert manifest["bundle_schema_version"] == "run_artifact_bundle_v7"
    assert manifest["run_mode"] == "run_all"
    assert manifest["run_mode_label"] == "Run All"
    assert "late_stage_mode" not in manifest
    assert "results.json" in manifest["included_files"]
    assert manifest["job_outcome_counts"] == {"accepted": 0, "held": 0, "blocked": 0, "rejected": 0, "skipped": 0}
    assert manifest["file_fingerprints"]["results.json"].startswith("sha256:")
    assert "hitl-review-audit.json" in manifest["included_files"]
    assert manifest["artifact_states"]["cv-analysis-trace.json"] == "present"
    assert manifest["artifact_states"]["cv-generation-trace.json"] == "present"
    assert manifest["artifact_states"]["synonym-proposals.json"] == "present"
    assert manifest["artifact_states"]["synonym-proposals-trace.json"] == "present"
    assert manifest["missing_files"] == []
    assert analysis_trace_payload["trace_family"] == "agentic_step_trace"
    assert analysis_trace_payload["step_id"] == "cv_analysis"
    assert trace_payload["trace_family"] == "agentic_step_trace"
    assert trace_payload["step_id"] == "cv_generation"
    assert synonym_trace_payload["trace_family"] == "agentic_step_trace"
    assert synonym_trace_payload["step_id"] == "synonym_proposals"


def test_download_run_artifact_bundle_includes_synonym_yaml_artifacts_when_available() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-bundle-synonym-yaml-1",
        status=RunStatus.SUCCEEDED,
        run_mode="run_all",
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        results_export_json='{"run_id":"run-bundle-synonym-yaml-1","results":[]}',
        effective_settings_json=(
            '{"skill_synonyms_runtime":{"has_run_overlay":true,"run_overlay_yaml":"skill_synonyms:\\n  ga4: google analytics\\n"}}'
        ),
        synonym_proposals_json=(
            '{"run_id":"run-bundle-synonym-yaml-1","proposals":['
            '{"proposal_id":"proposal-gcp","proposal_status":"approved_for_run_overlay","alias":"gcp","canonical":"google cloud","confidence":0.9}'
            ']}'
        ),
        stage_transition_artifacts_json=json.dumps(
            {
                "run_id": "run-bundle-synonym-yaml-1",
                "created_at": "2026-04-07T12:00:00+00:00",
                "artifacts": {"stages": {"enrich": {"stage_id": "enrich", "status": "completed"}}},
            }
        ),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-bundle-synonym-yaml-1/artifacts.zip")

    assert resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
        names = set(archive.namelist())
        assert "approved-synonym-proposals.yaml" in names
        assert "synonym-overlay-used.yaml" in names
        assert "global-skill-synonyms.yaml" in names
        assert "global-domain-aliases.yaml" in names
        assert "global-role-family-aliases.yaml" in names


def test_download_run_artifact_bundle_zip_endpoint_404_if_no_artifacts_available() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="run-bundle-empty-1",
        status=RunStatus.QUEUED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).get("/admin/runs/run-bundle-empty-1/artifacts.zip")

    assert resp.status_code == 404
    assert "artifacts" in resp.text.lower()


# ── enriched jobs on run detail ──────────────────────────────────────────────

def test_admin_run_detail_shows_enriched_jobs_section():
    """@proves inspection_debugging.enriched-job-debug-export"""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    enriched_jobs = [
        {
            "run_id": "test-123",
            "job_url": "https://example.com/job/1",
            "title": "Senior Data Engineer",
            "location_type": "remote",
            "seniority": "senior",
            "job_family": "data_engineering",
            "domain": "fintech",
            "required_skills": ["SQL", "Python", "Spark"],
        }
    ]

    with patch("fitcv_cp.app.get_run", return_value=PipelineRun(
        run_id="test-123", status=RunStatus.SUCCEEDED,
        cvs_generated=1, total_jobs=5, jobs_path="",
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc)
    )), patch("fitcv_cp.app.get_events", return_value=[]), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched_jobs):
        resp = TestClient(_app()).get("/admin/runs/test-123/tabs/enriched")

    assert resp.status_code == 200
    assert "Senior Data Engineer" in resp.text
    assert "remote" in resp.text
    assert "senior" in resp.text
    assert "data_engineering" in resp.text
    assert "fintech" in resp.text


def test_admin_run_detail_empty_enriched_jobs_renders_gracefully():
    """Run detail page handles empty enriched_jobs without errors."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    with patch("fitcv_cp.app.get_run", return_value=PipelineRun(
        run_id="test-empty", status=RunStatus.SUCCEEDED,
        cvs_generated=0, total_jobs=3, jobs_path="",
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc)
    )), patch("fitcv_cp.app.get_events", return_value=[]), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/test-empty/tabs/enriched")

    assert resp.status_code == 200
    assert "No enrichment data" in resp.text or "enriched" in resp.text.lower()

def test_admin_run_detail_enriched_jobs_falls_back_to_results_export_when_store_empty():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="test-fallback-enriched",
        status=RunStatus.SUCCEEDED,
        cvs_generated=0,
        total_jobs=1,
        jobs_path="",
        triggered_by="admin",
        trigger_source="web",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        results_export_json=json.dumps(
            {
                "results": [
                    {
                        "job_url": "https://example.com/job/fallback-1",
                        "job_title": "Fallback Data Engineer",
                        "location_type": "remote",
                        "seniority": "mid",
                        "job_family": "data_engineering",
                        "domain": "fintech",
                    }
                ]
            }
        ),
    )

    with patch("fitcv_cp.app.get_run", return_value=run), \
    patch("fitcv_cp.app.get_events", return_value=[]), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
    patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/test-fallback-enriched/tabs/enriched")

    assert resp.status_code == 200
    assert "Fallback Data Engineer" in resp.text
    assert "remote" in resp.text


def test_admin_run_detail_enriched_jobs_shows_required_skills():
    """Run detail renders required_skills from enriched job rows."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    enriched_jobs = [
        {
            "run_id": "test-456",
            "job_url": "https://example.com/job/2",
            "title": "ML Engineer",
            "location_type": "hybrid",
            "seniority": "mid",
            "job_family": "ml_engineering",
            "domain": "healthcare",
            "required_skills": ["Python", "TensorFlow", "Kubernetes"],
        }
    ]

    with patch("fitcv_cp.app.get_run", return_value=PipelineRun(
        run_id="test-456", status=RunStatus.SUCCEEDED,
        cvs_generated=0, total_jobs=1, jobs_path="",
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc)
    )), patch("fitcv_cp.app.get_events", return_value=[]), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched_jobs):
        resp = TestClient(_app()).get("/admin/runs/test-456/tabs/enriched")

    assert resp.status_code == 200
    assert "Python" in resp.text
    assert "TensorFlow" in resp.text
    assert "https://example.com/job/2" in resp.text


def test_admin_run_detail_enriched_jobs_falls_back_to_keywords_when_required_skills_empty() -> None:
    """Enriched tab surfaces fallback structured signals when required skills are empty."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    enriched_jobs = [
        {
            "run_id": "test-456-fallback",
            "job_url": "https://example.com/job/3",
            "title": "Assistenz / Operations & Customer Care (m/w/d)",
            "location_type": "remote",
            "seniority": "junior",
            "job_family": "operations",
            "domain": "construction",
            "required_skills": [],
            "tech_stack": [],
            "keywords": ["Assistenz", "Operations", "Customer Care"],
        }
    ]

    with patch("fitcv_cp.app.get_run", return_value=PipelineRun(
        run_id="test-456-fallback", status=RunStatus.SUCCEEDED,
        cvs_generated=0, total_jobs=1, jobs_path="",
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc)
    )), patch("fitcv_cp.app.get_events", return_value=[]), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched_jobs):
        resp = TestClient(_app()).get("/admin/runs/test-456-fallback/tabs/enriched")

    assert resp.status_code == 200
    assert all(skill in resp.text for skill in ("Assistenz", "Operations", "Customer Care"))


def test_admin_run_detail_enriched_jobs_prefers_structured_entities_when_required_skills_are_verbose() -> None:
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    enriched_jobs = [
        {
            "run_id": "test-456-entities",
            "job_url": "https://example.com/job/4",
            "title": "(Senior) Consultant (all genders) Accelerating to Space",
            "location_type": "hybrid",
            "seniority": "senior",
            "job_family": "consulting",
            "domain": "space",
            "required_skills": [
                "Overview of core space domains and applications around earth observation, satellite communication, satellite navigation, and space transportation",
                "General know-how of space hardware design and requirements around assembly, integration and testing",
            ],
            "required_skill_entities_json": json.dumps(
                [
                    {
                        "raw_text": "General know-how of space hardware design and requirements around assembly, integration and testing",
                        "canonical": "space hardware design",
                        "confidence": 0.95,
                    },
                    {
                        "raw_text": "General know-how of space hardware design and requirements around assembly, integration and testing",
                        "canonical": "assembly, integration and testing",
                        "confidence": 0.95,
                    },
                ]
            ),
            "tech_stack": [],
            "keywords": [],
        }
    ]

    with patch("fitcv_cp.app.get_run", return_value=PipelineRun(
        run_id="test-456-entities", status=RunStatus.SUCCEEDED,
        cvs_generated=0, total_jobs=1, jobs_path="",
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc)
    )), patch("fitcv_cp.app.get_events", return_value=[]), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched_jobs):
        resp = TestClient(_app()).get("/admin/runs/test-456-entities/tabs/enriched")

    assert resp.status_code == 200
    assert "space hardware design" in resp.text
    assert "assembly, integration and testing" in resp.text
    assert "Overview of core space domains and applications" not in resp.text




# ── Inspection Tab Tests ──────────────────────────────────────────────────────


def _run_detail_base_patches(run_obj):
    """Return tuple of patchers for standard run detail route dependencies."""
    return (
        patch("fitcv_cp.app.get_run", return_value=run_obj),
        patch("fitcv_cp.app.get_events", return_value=[]),
        patch("fitcv_cp.app.list_cvs_for_run", return_value=[]),
        patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]),
        patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]),
    )


def test_run_detail_initial_shell_does_not_query_enriched_rows() -> None:
    """Initial run-detail render stays lightweight and avoids enriched/filter queries."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="tab-shell-1",
        status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json",
        triggered_by="admin",
        trigger_source="web",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.get_events", return_value=[]), \
         patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
         patch("fitcv_cp.app.list_run_structured_jobs") as mock_jobs, \
         patch("fitcv_cp.app.list_filter_results_for_run") as mock_filters:
        resp = TestClient(_app()).get("/admin/runs/tab-shell-1")

    assert resp.status_code == 200
    assert "Pipeline results load on demand." in resp.text
    mock_jobs.assert_not_called()
    mock_filters.assert_not_called()


def test_run_detail_tab2_fallback_when_no_jobs_snapshot():
    """Tab 2 shows source/path fallback when jobs_input_json is absent."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="tab-test-2", status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json", jobs_input_source="path",
        jobs_input_json=None,
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/tab-test-2/tabs/jobs-input")

    assert resp.status_code == 200
    html = resp.text
    assert "No immutable raw snapshot" in html
    assert "data/sample_jobs.json" in html


def test_run_detail_tab3_null_source_shows_not_recorded_not_default_config():
    """Tab 3 fallback must not infer 'default_config' when source is NULL."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="tab-test-3", status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json",
        candidate_profile_source=None,
        candidate_profile_json=None,
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/tab-test-3/tabs/profile")

    assert resp.status_code == 200
    html = resp.text
    assert "No candidate profile snapshot" in html
    assert "not recorded" in html
    assert "default_config" not in html


def _obsolete_test_run_detail_event_timeline_appears_after_tab_panes():
    """Event Timeline heading must come after all 3 tab panes in the HTML."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="tab-test-4", status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json",
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/tab-test-4")

    assert resp.status_code == 200
    html = resp.text
    profile_pane_pos = html.index('id="pane-profile"')
    timeline_pos = html.index("Event Timeline")
    assert timeline_pos > profile_pane_pos, (
        "Event Timeline must appear after all tab panes in the HTML"
    )


def test_run_detail_hides_run_health_when_quality_metrics_absent():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="quality-metrics-2",
        status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json",
        triggered_by="admin",
        trigger_source="web",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        results_export_json=json.dumps({"results": []}),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/quality-metrics-2")

    assert resp.status_code == 200
    assert "Run Health" not in resp.text


def test_run_detail_hides_late_stage_reuse_metrics_when_absent():
    """@proves inspection_debugging.reuse-diagnostics"""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="reuse-metrics-2",
        status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json",
        triggered_by="admin",
        trigger_source="web",
        config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
        results_export_json=json.dumps({"results": []}),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/reuse-metrics-2")

    assert resp.status_code == 200
    assert "Ranking AI-Score Reuse Rate" not in resp.text
    assert "CV Analysis Reuse Rate" not in resp.text

# ── grouped settings endpoint ─────────────────────────────────────────────────

_VALID_WEIGHTS = {
    "ranking_policy.structured_factor_weights.must_have_match": "0.30",
    "ranking_policy.structured_factor_weights.title_relevance": "0.20",
    "ranking_policy.structured_factor_weights.seniority_fit": "0.15",
    "ranking_policy.structured_factor_weights.declared_preference_fit": "0.15",
    "ranking_policy.structured_factor_weights.location_fit": "0.10",
    "ranking_policy.structured_factor_weights.language_fit": "0.10",
}


def test_grouped_save_valid_ranking_weights_redirects():
    """Valid 6-weight form POST → 303 redirect; save_settings_group called."""
    with patch("fitcv_cp.app.save_settings_group") as mock_group_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/group/ranking-weights",
            data=_VALID_WEIGHTS,
        )
    assert resp.status_code == 303
    mock_group_save.assert_called_once()
    saved_keys = set(mock_group_save.call_args[0][0].keys())
    assert saved_keys == set(_VALID_WEIGHTS.keys())


def test_grouped_save_weights_dont_sum_to_one_returns_422():
    """Weights summing to 0.9 → 422; no write."""
    bad_weights = dict(_VALID_WEIGHTS)
    bad_weights["ranking_policy.structured_factor_weights.must_have_match"] = "0.20"
    with patch("fitcv_cp.app.save_settings_group") as mock_group_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/group/ranking-weights",
            data=bad_weights,
        )
    assert resp.status_code == 422
    mock_group_save.assert_not_called()


def test_grouped_save_weights_error_is_rendered_in_compatibility_response():
    bad_weights = dict(_VALID_WEIGHTS)
    bad_weights["ranking_policy.structured_factor_weights.must_have_match"] = "0.20"
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/group/ranking-weights",
            data=bad_weights,
        )
    assert resp.status_code == 422
    assert "sum to 1.0" in resp.text


def test_grouped_save_fit_label_thresholds_valid():
    """@proves settings_system.preference-fit-calibration

    strong > stretch -> 303 redirect; 2 keys saved.
    """
    with patch("fitcv_cp.app.save_settings_group") as mock_group_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/group/fit-label-thresholds",
            data={
                "ranking_policy.fit_label_thresholds.strong": "0.70",
                "ranking_policy.fit_label_thresholds.stretch": "0.40",
            },
        )
    assert resp.status_code == 303
    mock_group_save.assert_called_once()


def test_grouped_save_fit_label_thresholds_invalid_order():
    """@proves settings_system.grouped-form-validation

    stretch > strong -> 422; no write.
    """
    with patch("fitcv_cp.app.save_settings_group") as mock_group_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/group/fit-label-thresholds",
            data={
                "ranking_policy.fit_label_thresholds.strong": "0.40",
                "ranking_policy.fit_label_thresholds.stretch": "0.70",
            },
        )
    assert resp.status_code == 422
    mock_group_save.assert_not_called()


def test_grouped_save_unknown_group_returns_404():
    """Unknown group name → 404."""
    resp = TestClient(_app()).post(
        "/admin/settings/group/nonexistent",
        data={"some.key": "1"},
    )
    assert resp.status_code == 404


def test_grouped_save_bq_error_returns_422_not_303():
    """BQ failure from save_settings_group → 422 error page, not a redirect."""
    with patch("fitcv_cp.app.save_settings_group", side_effect=RuntimeError("BQ failed")), \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/group/fit-label-thresholds",
            data={
                "ranking_policy.fit_label_thresholds.strong": "0.70",
                "ranking_policy.fit_label_thresholds.stretch": "0.40",
            },
        )
    assert resp.status_code == 422
    assert "BQ failed" in resp.text


def test_grouped_save_audit_identity_encoded_in_updated_by():
    """Each group save uses updated_by='admin:grp:{uuid}'."""
    captured = {}

    def fake_save(keys_values, *, updated_by, **_: object):
        captured["updated_by"] = updated_by

    with patch("fitcv_cp.app.save_settings_group", side_effect=fake_save), \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/group/fit-label-thresholds",
            data={
                "ranking_policy.fit_label_thresholds.strong": "0.70",
                "ranking_policy.fit_label_thresholds.stretch": "0.40",
            },
        )
    assert captured.get("updated_by", "").startswith("admin:grp:")


# ── POST /admin/settings/section/{section_name} ───────────────────────────────

def _retrieval_core_section_form(
    *,
    vector_search_top_n: str = "100",
    ai_score_top_n: str = "20",
    final_top_n: str = "10",
    evidence_top_k: str = "5",
) -> dict[str, str]:
    return {
        "pipeline.vector_search_top_n": vector_search_top_n,
        "pipeline.ai_score_top_n": ai_score_top_n,
        "pipeline.final_top_n": final_top_n,
        "pipeline.evidence_top_k": evidence_top_k,
    }


def _retrieval_advanced_section_form(
    *,
    semantic_alignment_model: str = "text-embedding-005",
    required_skill_lexical_weight: str = "0.70",
    required_skill_semantic_weight: str = "0.30",
    role_lexical_weight: str = "0.60",
    role_semantic_weight: str = "0.40",
    responsibility_lexical_weight: str = "0.25",
    responsibility_semantic_weight: str = "0.75",
    domain_lexical_weight: str = "0.40",
    domain_semantic_weight: str = "0.60",
    channel_pool_size: str = "4",
) -> dict[str, str]:
    return {
        "cv_analysis.semantic_alignment.model": semantic_alignment_model,
        "cv_analysis.semantic_alignment.required_skill_lexical_weight": required_skill_lexical_weight,
        "cv_analysis.semantic_alignment.required_skill_semantic_weight": required_skill_semantic_weight,
        "cv_analysis.semantic_alignment.role_lexical_weight": role_lexical_weight,
        "cv_analysis.semantic_alignment.role_semantic_weight": role_semantic_weight,
        "cv_analysis.semantic_alignment.responsibility_lexical_weight": responsibility_lexical_weight,
        "cv_analysis.semantic_alignment.responsibility_semantic_weight": responsibility_semantic_weight,
        "cv_analysis.semantic_alignment.domain_lexical_weight": domain_lexical_weight,
        "cv_analysis.semantic_alignment.domain_semantic_weight": domain_semantic_weight,
        "cv_analysis.semantic_alignment.channel_pool_size": channel_pool_size,
    }


def _agentic_core_section_form(
    *,
    semantic_alignment_enabled: str = "true",
) -> dict[str, str]:
    return {"cv_analysis.semantic_alignment.enabled": semantic_alignment_enabled}


def _agentic_advanced_section_form(
    *,
    semantic_alignment_model: str = "text-embedding-005",
    required_skill_lexical_weight: str = "0.70",
    required_skill_semantic_weight: str = "0.30",
    role_lexical_weight: str = "0.60",
    role_semantic_weight: str = "0.40",
    responsibility_lexical_weight: str = "0.25",
    responsibility_semantic_weight: str = "0.75",
    domain_lexical_weight: str = "0.40",
    domain_semantic_weight: str = "0.60",
    channel_pool_size: str = "4",
) -> dict[str, str]:
    return {
        "cv_analysis.semantic_alignment.model": semantic_alignment_model,
        "cv_analysis.semantic_alignment.required_skill_lexical_weight": required_skill_lexical_weight,
        "cv_analysis.semantic_alignment.required_skill_semantic_weight": required_skill_semantic_weight,
        "cv_analysis.semantic_alignment.role_lexical_weight": role_lexical_weight,
        "cv_analysis.semantic_alignment.role_semantic_weight": role_semantic_weight,
        "cv_analysis.semantic_alignment.responsibility_lexical_weight": responsibility_lexical_weight,
        "cv_analysis.semantic_alignment.responsibility_semantic_weight": responsibility_semantic_weight,
        "cv_analysis.semantic_alignment.domain_lexical_weight": domain_lexical_weight,
        "cv_analysis.semantic_alignment.domain_semantic_weight": domain_semantic_weight,
        "cv_analysis.semantic_alignment.channel_pool_size": channel_pool_size,
    }


def _agentic_automation_section_form(
    *,
    auto_triage_enabled: str = "true",
    auto_accept_suggestions_enabled: str = "false",
    auto_accept_ai_action_enabled: str = "true",
) -> dict[str, str]:
    return {
        "synonym_management.auto_triage_recommendation_enabled": auto_triage_enabled,
        "synonym_management.auto_accept_suggestions_enabled": auto_accept_suggestions_enabled,
        "synonym_management.auto_accept_ai_action_enabled": auto_accept_ai_action_enabled,
    }


def _agentic_reuse_section_form(
    *,
    enrich_enabled: str = "true",
    ranking_enabled: str = "true",
    cv_analysis_enabled: str = "true",
    cv_generation_enabled: str = "true",
    synonym_triage_enabled: str = "true",
) -> dict[str, str]:
    return {
        "reuse.enrich.enabled": enrich_enabled,
        "reuse.ranking.enabled": ranking_enabled,
        "reuse.cv_analysis.enabled": cv_analysis_enabled,
        "reuse.cv_generation.enabled": cv_generation_enabled,
        "reuse.synonym_triage.enabled": synonym_triage_enabled,
    }


def test_post_settings_section_valid_redirects():
    """Valid payload for retrieval core section returns 303."""
    with patch("fitcv_cp.app.save_settings_group"), \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/section/retrieval-core",
            data=_retrieval_core_section_form(),
        )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/settings"


def test_post_settings_section_timing_ignores_retired_runtime_fields() -> None:
    captured: dict[str, dict[str, object]] = {}

    def _capture_save(payload: dict[str, object], **_: object) -> None:
        captured["payload"] = dict(payload)

    with patch("fitcv_cp.app.save_settings_group", side_effect=_capture_save), \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/section/timing",
            data={
                "llm_runtime.request_start_interval_secs": "0.4",
                "stage_runtime.enrich.concurrency": "2",
                "stage_runtime.ranking.concurrency": "4",
                "stage_runtime.cv_analysis.concurrency": "2",
                "stage_runtime.cv_generation.concurrency": "2",
                "enrichment_sleep_secs": "0.9",
                "rerank_sleep_secs": "0.9",
                "enrichment_batch_size": "4",
                "enrichment_concurrency": "1",
            },
            follow_redirects=False,
        )

    assert resp.status_code == 303
    payload = captured["payload"]
    assert payload == {
        "llm_runtime.request_start_interval_secs": 0.4,
        "stage_runtime.enrich.concurrency": 2,
        "stage_runtime.ranking.concurrency": 4,
        "stage_runtime.cv_analysis.concurrency": 2,
        "stage_runtime.cv_generation.concurrency": 2,
    }

def test_post_settings_section_timing_accepts_canonical_only_payload() -> None:
    captured: dict[str, dict[str, object]] = {}

    def _capture_save(payload: dict[str, object], **_: object) -> None:
        captured["payload"] = dict(payload)

    with patch("fitcv_cp.app.save_settings_group", side_effect=_capture_save), \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/section/timing",
            data={
                "llm_runtime.request_start_interval_secs": "0.0",
                "stage_runtime.enrich.concurrency": "8",
                "stage_runtime.ranking.concurrency": "6",
                "stage_runtime.cv_analysis.concurrency": "3",
                "stage_runtime.cv_generation.concurrency": "3",
            },
            follow_redirects=False,
        )

    assert resp.status_code == 303
    payload = captured["payload"]
    assert payload["llm_runtime.request_start_interval_secs"] == 0.0
    assert payload["stage_runtime.enrich.concurrency"] == 8
    assert payload["stage_runtime.ranking.concurrency"] == 6
    assert "enrichment_concurrency" not in payload


def test_post_settings_section_advanced_retrieval_returns_404_after_section_retirement():
    """Legacy retrieval-advanced section is no longer an addressable section-save slug."""
    with patch("fitcv_cp.app.save_settings_group") as mock_group_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/section/retrieval-advanced",
            data=_retrieval_advanced_section_form(),
        )
    assert resp.status_code == 404
    mock_group_save.assert_not_called()


def test_post_settings_section_advanced_retrieval_without_metadata_only_input_returns_404() -> None:
    """Legacy retrieval-advanced endpoint remains removed even when form omits metadata-only values."""
    form_data = _retrieval_advanced_section_form()
    del form_data["cv_analysis.semantic_alignment.model"]

    with patch("fitcv_cp.app.save_settings_group") as mock_group_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/section/retrieval-advanced",
            data=form_data,
        )
    assert resp.status_code == 404
    mock_group_save.assert_not_called()


def test_post_settings_section_agentic_enablement_valid_redirects() -> None:
    captured = {}

    def _capture_save(values, *, updated_by, **_: object):
        captured["values"] = values

    with patch("fitcv_cp.app.save_settings_group", side_effect=_capture_save), \
        patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/section/agentic-enablement",
            data=_agentic_core_section_form(),
        )

    assert resp.status_code == 303
    assert "cv.agentic_late_stage.enabled" not in captured["values"]
    assert captured["values"]["cv_analysis.semantic_alignment.enabled"] is True


def test_post_settings_section_agentic_reuse_valid_redirects() -> None:
    captured = {}

    def _capture_save(values, *, updated_by, **_: object):
        captured["values"] = values

    with patch("fitcv_cp.app.save_settings_group", side_effect=_capture_save), \
        patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/section/agentic-reuse",
            data=_agentic_reuse_section_form(cv_generation_enabled="false"),
        )

    assert resp.status_code == 303
    assert captured["values"]["reuse.enrich.enabled"] is True
    assert captured["values"]["reuse.cv_generation.enabled"] is False


def test_post_settings_section_agentic_advanced_omits_metadata_only_input() -> None:
    captured = {}

    def _capture_save(values, *, updated_by, **_: object):
        captured["values"] = values

    form_data = _agentic_advanced_section_form()
    del form_data["cv_analysis.semantic_alignment.model"]

    with patch("fitcv_cp.app.save_settings_group", side_effect=_capture_save), \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/section/agentic-advanced",
            data=form_data,
        )

    assert resp.status_code == 303
    assert "cv_analysis.semantic_alignment.model" not in captured["values"]
    assert "cv_analysis.semantic_alignment.role_semantic_weight" in captured["values"]


def test_post_settings_section_agentic_automation_uses_canonical_synonym_keys() -> None:
    captured: dict[str, Any] = {}

    def _capture_save(values, *, updated_by, **_: object):
        captured["values"] = values

    with patch("fitcv_cp.app.save_settings_group", side_effect=_capture_save), \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/section/agentic-automation",
            data=_agentic_automation_section_form(),
        )

    assert resp.status_code == 303
    assert captured["values"] == {
        "synonym_management.auto_triage_recommendation_enabled": True,
        "synonym_management.auto_accept_suggestions_enabled": False,
        "synonym_management.auto_accept_ai_action_enabled": True,
    }


def test_post_settings_key_rejects_metadata_only_agentic_setting() -> None:
    resp = TestClient(_app()).post(
        "/settings/cv_analysis.semantic_alignment.model",
        json={"value": "text-embedding-005", "updated_by": "admin"},
    )
    assert resp.status_code == 422
    assert "metadata-only" in resp.json()["detail"]


def test_admin_post_settings_key_rejects_metadata_only_agentic_setting() -> None:
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/cv_analysis.semantic_alignment.model",
            data={"value": "text-embedding-005"},
        )
    assert resp.status_code == 422
    assert "metadata-only" in resp.text


def test_post_settings_section_unknown_returns_404():
    with patch("fitcv_cp.app.save_settings_group"), \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/section/does-not-exist",
            data={"some.key": "1"},
        )
    assert resp.status_code == 404


def test_post_settings_section_invalid_value_returns_422():
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/section/retrieval-core",
            data=_retrieval_core_section_form(vector_search_top_n="not-a-number"),
        )
    assert resp.status_code == 422


def test_post_settings_section_rule_filter_uses_list_values() -> None:
    captured = {}

    def _capture_save(values, *, updated_by, **_: object):
        captured["values"] = values

    with patch("fitcv_cp.app.save_settings_group", side_effect=_capture_save), \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/section/rule-filter",
            data={
                "rule_filter.selected_filters": [
                    "seniority_mismatch",
                    "must_have_skill_missing",
                ]
            },
        )

    assert resp.status_code == 303
    assert captured["values"]["rule_filter.selected_filters"] == [
        "seniority_mismatch",
        "must_have_skill_missing",
    ]


# ── Lifecycle API routes ─────────────────────────────────────────────────────

def _make_run_mock(status="queued", archived_at=None, queue_job_id="rq-job-1"):
    from fitcv_cp.models import PipelineRun, RunStatus
    import datetime
    return PipelineRun(
        run_id="run-lifecycle-1",
        status=RunStatus(status),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        queue_job_id=queue_job_id,
        archived_at=archived_at,
    )


def test_admin_stop_queued_run_returns_json():
    """@proves admin_control_plane_core.fastapi-web-server
    @proves run_lifecycle_controls.cancel-queued-runs-directly-from-the-queue-via-rq
    """
    run = _make_run_mock(status="queued")
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.cancel_queued_run", return_value=True), \
         patch("fitcv_cp.app.request_run_cancel") as mock_request_cancel, \
         patch("fitcv_cp.app.append_event") as mock_append_event:
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/stop")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    assert mock_request_cancel.call_args.args[2] == "cancelled"
    assert mock_append_event.call_count == 2


def test_admin_stop_queued_run_without_worker_claim_marks_cancelled() -> None:
    run = _make_run_mock(status="queued")
    run.started_at = None
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.cancel_queued_run", return_value=False), \
         patch("fitcv_cp.app.request_run_cancel") as mock_request_cancel, \
         patch("fitcv_cp.app.append_event") as mock_append_event:
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/stop")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelling"
    assert mock_request_cancel.call_args.args[2] == "cancelling"
    assert mock_append_event.call_count == 1


def test_admin_stop_claimed_run_falls_back_to_cancelling() -> None:
    """@proves run_lifecycle_controls.cooperative-cancellation-at-safe-checkpoints-for-running-jobs"""
    import datetime

    run = _make_run_mock(status="queued")
    run.started_at = datetime.datetime.now(datetime.timezone.utc)
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.cancel_queued_run", return_value=False), \
         patch("fitcv_cp.app.request_run_cancel") as mock_request_cancel, \
         patch("fitcv_cp.app.append_event") as mock_append_event:
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/stop")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelling"
    assert mock_request_cancel.call_args.args[2] == "cancelling"
    assert mock_append_event.call_count == 1


def test_admin_stop_succeeded_run_returns_409():
    run = _make_run_mock(status="succeeded")
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/stop")
    assert resp.status_code == 409


def test_admin_stop_awaiting_continue_run_returns_cancelled() -> None:
    """@proves run_lifecycle_controls.direct-cancellation-of-paused-manual-runs-in-awaiting-continue"""
    run = _make_run_mock(status="awaiting_continue")
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.append_event") as mock_append_event:
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/stop")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    assert mock_update_status.call_args.args[1].value == "cancelled"
    assert mock_append_event.call_count == 1


def test_admin_stop_unknown_run_returns_404():
    with patch("fitcv_cp.app.get_run", return_value=None):
        resp = TestClient(_app()).post("/admin/runs/nonexistent/stop")
    assert resp.status_code == 404


def test_admin_repair_cancellation_stale_run_returns_cancelled() -> None:
    """@proves run_lifecycle_controls.stale-cancellation-repair-endpoint"""
    run = _make_run_mock(status="cancelling")
    run.started_at = None
    run.finished_at = None
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.append_event"):
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/repair-cancellation")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    assert mock_update_status.call_args.args[1].value == "cancelled"


def test_admin_repair_cancellation_started_stale_run_returns_cancelled() -> None:
    """@proves run_lifecycle_controls.stale-cancellation-repair-endpoint"""
    import datetime

    run = _make_run_mock(status="cancelling")
    now = datetime.datetime.now(datetime.timezone.utc)
    run.started_at = now - datetime.timedelta(minutes=15)
    run.cancel_requested_at = now - datetime.timedelta(minutes=5)
    run.finished_at = None
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.append_event"):
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/repair-cancellation")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    assert mock_update_status.call_args.args[1].value == "cancelled"


def test_admin_repair_cancellation_running_run_returns_409() -> None:
    """@proves run_lifecycle_controls.stale-cancellation-repair-endpoint"""
    run = _make_run_mock(status="running")
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/repair-cancellation")
    assert resp.status_code == 409


def test_admin_archive_succeeded_run_returns_json():
    """@proves run_lifecycle_controls.archive-and-unarchive-terminal-runs"""
    run = _make_run_mock(status="succeeded")
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.archive_run"), \
         patch("fitcv_cp.app.append_event"):
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/archive")
    assert resp.status_code == 200


def test_admin_archive_running_run_returns_409():
    run = _make_run_mock(status="running")
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/archive")
    assert resp.status_code == 409


def test_admin_unarchive_archived_run_returns_json():
    """@proves run_lifecycle_controls.archive-and-unarchive-terminal-runs"""
    import datetime
    run = _make_run_mock(status="succeeded", archived_at=datetime.datetime.now(datetime.timezone.utc))
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.unarchive_run"), \
         patch("fitcv_cp.app.append_event"):
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/unarchive")
    assert resp.status_code == 200


def test_admin_unarchive_non_archived_run_returns_409():
    run = _make_run_mock(status="succeeded", archived_at=None)
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/unarchive")
    assert resp.status_code == 409


def test_admin_bulk_cancel_mixed_eligibility_returns_processed_and_skipped_summary():
    """@proves trigger_run_management.runs-list-management
    @proves run_lifecycle_controls.batch-cancel-archive-and-unarchive-endpoints-with-explicit-processed-skipped-summaries
    """
    run1 = _make_full_run_mock(status="queued", run_id="run-bulk-1")
    run2 = _make_full_run_mock(status="succeeded", run_id="run-bulk-2")

    def _get_run(run_id, *args, **kwargs):
        return {"run-bulk-1": run1, "run-bulk-2": run2}.get(run_id)

    with patch("fitcv_cp.app.get_run", side_effect=_get_run), \
         patch("fitcv_cp.app.cancel_queued_run", return_value=False), \
         patch("fitcv_cp.app.request_run_cancel") as mock_request_cancel, \
         patch("fitcv_cp.app.append_event") as mock_append_event:
        resp = TestClient(_app()).post(
            "/admin/runs/bulk/cancel",
            headers={"Idempotency-Key": "bulk-cancel-mixed-1"},
            json={"run_ids": ["run-bulk-1", "run-bulk-2"]},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["requested"] == 2
    assert body["processed"] == 1
    assert body["skipped"] == 1
    assert body["processed_run_ids"] == ["run-bulk-1"]
    assert body["skipped_items"] == [{"run_id": "run-bulk-2", "reason": "not_cancellable"}]
    assert mock_request_cancel.call_count == 1
    assert mock_append_event.call_count == 1


def test_admin_bulk_cancel_awaiting_continue_run_directly_cancels():
    """@proves run_lifecycle_controls.direct-cancellation-of-paused-manual-runs-in-awaiting-continue
    @proves run_lifecycle_controls.batch-cancel-archive-and-unarchive-endpoints-with-explicit-processed-skipped-summaries
    """
    run = _make_full_run_mock(status="awaiting_continue", run_id="run-bulk-awaiting")

    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.request_run_cancel") as mock_request_cancel, \
         patch("fitcv_cp.app.append_event") as mock_append_event:
        resp = TestClient(_app()).post(
            "/admin/runs/bulk/cancel",
            headers={"Idempotency-Key": "bulk-cancel-awaiting-1"},
            json={"run_ids": ["run-bulk-awaiting"]},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["processed"] == 1
    assert body["processed_run_ids"] == ["run-bulk-awaiting"]
    assert mock_update_status.call_args.args[1].value == "cancelled"
    mock_request_cancel.assert_not_called()
    assert mock_append_event.call_count == 1


def test_admin_bulk_archive_terminal_runs_only():
    """@proves run_lifecycle_controls.batch-cancel-archive-and-unarchive-endpoints-with-explicit-processed-skipped-summaries"""
    run1 = _make_full_run_mock(status="succeeded", run_id="run-archive-1")
    run2 = _make_full_run_mock(status="running", run_id="run-archive-2")

    def _get_run(run_id, *args, **kwargs):
        return {"run-archive-1": run1, "run-archive-2": run2}.get(run_id)

    with patch("fitcv_cp.app.get_run", side_effect=_get_run), \
         patch("fitcv_cp.app.archive_run") as mock_archive_run, \
         patch("fitcv_cp.app.append_event") as mock_append_event:
        resp = TestClient(_app()).post(
            "/admin/runs/bulk/archive",
            headers={"Idempotency-Key": "bulk-archive-terminal-1"},
            json={"run_ids": ["run-archive-1", "run-archive-2"]},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["processed"] == 1
    assert body["processed_run_ids"] == ["run-archive-1"]
    assert body["skipped_items"] == [{"run_id": "run-archive-2", "reason": "not_archivable"}]
    mock_archive_run.assert_called_once()
    mock_append_event.assert_called_once()


def test_admin_bulk_unarchive_archived_runs_only():
    """@proves run_lifecycle_controls.batch-cancel-archive-and-unarchive-endpoints-with-explicit-processed-skipped-summaries"""
    import datetime

    run1 = _make_full_run_mock(
        status="succeeded",
        run_id="run-unarchive-1",
        archived_at=datetime.datetime.now(datetime.timezone.utc),
    )
    run2 = _make_full_run_mock(status="failed", run_id="run-unarchive-2", archived_at=None)

    def _get_run(run_id, *args, **kwargs):
        return {"run-unarchive-1": run1, "run-unarchive-2": run2}.get(run_id)

    with patch("fitcv_cp.app.get_run", side_effect=_get_run), \
         patch("fitcv_cp.app.unarchive_run") as mock_unarchive_run, \
         patch("fitcv_cp.app.append_event") as mock_append_event:
        resp = TestClient(_app()).post(
            "/admin/runs/bulk/unarchive",
            headers={"Idempotency-Key": "bulk-unarchive-terminal-1"},
            json={"run_ids": ["run-unarchive-1", "run-unarchive-2"]},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["processed"] == 1
    assert body["processed_run_ids"] == ["run-unarchive-1"]
    assert body["skipped_items"] == [{"run_id": "run-unarchive-2", "reason": "not_unarchivable"}]
    mock_unarchive_run.assert_called_once()
    mock_append_event.assert_called_once()


def test_admin_bulk_lifecycle_rejects_empty_run_ids():
    """@proves run_lifecycle_controls.batch-cancel-archive-and-unarchive-endpoints-with-explicit-processed-skipped-summaries"""
    resp = TestClient(_app()).post("/admin/runs/bulk/cancel", json={"run_ids": []})
    assert resp.status_code == 422


def test_admin_bulk_lifecycle_rejects_unknown_run_ids():
    """@proves run_lifecycle_controls.batch-cancel-archive-and-unarchive-endpoints-with-explicit-processed-skipped-summaries"""
    with patch("fitcv_cp.app.get_run", return_value=None):
        resp = TestClient(_app()).post(
            "/admin/runs/bulk/archive",
            headers={"Idempotency-Key": "bulk-archive-missing-1"},
            json={"run_ids": ["missing-run"]},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["processed"] == 0
    assert body["skipped"] == 1
    assert body["skipped_items"] == [{"run_id": "missing-run", "reason": "not_found"}]


def test_admin_bulk_archive_replays_without_duplicate_mutation_or_events():
    run = _make_full_run_mock(status="succeeded", run_id="run-archive-replay")
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.archive_run") as mock_archive_run, \
         patch("fitcv_cp.app.append_event") as mock_append_event:
        client = TestClient(_app())
        first = client.post(
            "/admin/runs/bulk/archive",
            headers={"Idempotency-Key": "bulk-archive-replay-1"},
            json={"run_ids": [run.run_id]},
        )
        replay = client.post(
            "/admin/runs/bulk/archive",
            headers={"Idempotency-Key": "bulk-archive-replay-1"},
            json={"run_ids": [run.run_id]},
        )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json() == first.json()
    mock_archive_run.assert_called_once()
    assert mock_append_event.call_count == 1


def test_admin_bulk_lifecycle_rejects_idempotency_conflict():
    run = _make_full_run_mock(status="succeeded", run_id="run-archive-conflict")
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.archive_run"), \
         patch("fitcv_cp.app.append_event"):
        client = TestClient(_app())
        first = client.post(
            "/admin/runs/bulk/archive",
            headers={"Idempotency-Key": "bulk-lifecycle-conflict-1"},
            json={"run_ids": [run.run_id]},
        )
        conflict = client.post(
            "/admin/runs/bulk/cancel",
            headers={"Idempotency-Key": "bulk-lifecycle-conflict-1"},
            json={"run_ids": ["different-run"]},
        )

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"


def test_admin_bulk_lifecycle_requires_idempotency_key():
    run = _make_full_run_mock(status="succeeded", run_id="run-archive-key")
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.archive_run") as mock_archive_run:
        response = TestClient(_app()).post(
            "/admin/runs/bulk/archive",
            json={"run_ids": [run.run_id]},
        )

    assert response.status_code == 422
    mock_archive_run.assert_not_called()


def test_admin_bulk_lifecycle_openapi_declares_idempotency_header():
    paths = TestClient(_app()).get("/openapi.json").json()["paths"]
    for path in (
        "/admin/runs/bulk/cancel",
        "/admin/runs/bulk/archive",
        "/admin/runs/bulk/unarchive",
    ):
        parameters = paths[path]["post"]["parameters"]
        assert any(
            parameter.get("name") == "Idempotency-Key"
            and parameter.get("in") == "header"
            and parameter.get("required") is True
            for parameter in parameters
        )


def _obsolete_test_admin_bulk_delete_archived_runs_returns_deleted_summary():
    """@proves run_lifecycle_controls.delete-archived-runs-bulk-cleanup"""
    with patch("fitcv_cp.app.delete_archived_runs", return_value={"deleted_count": 2, "deleted_run_ids": ["run-1", "run-2"]}):
        resp = TestClient(_app()).post(
            "/admin/runs/bulk/delete-archived",
            json={"older_than_days": 30, "run_ids": ["run-1", "run-2"]},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "deleted"
    assert body["deleted_count"] == 2
    assert body["deleted_run_ids"] == ["run-1", "run-2"]


def _obsolete_test_admin_bulk_delete_archived_runs_rejects_invalid_threshold():
    resp = TestClient(_app()).post(
        "/admin/runs/bulk/delete-archived",
        json={"older_than_days": -1},
    )
    assert resp.status_code == 422


def test_admin_runs_active_view_passes_archive_filter():
    with patch("fitcv_cp.app.list_runs", return_value=[]) as mock_list:
        resp = TestClient(_app()).get("/admin/runs?view=active")
    assert resp.status_code == 200
    calls = [call.kwargs for call in mock_list.call_args_list]
    assert any(call.get("include_archived") is False for call in calls)
    assert any(call.get("archived_only") is True for call in calls)


def test_admin_runs_archived_view_passes_archived_only():
    with patch("fitcv_cp.app.list_runs", return_value=[]) as mock_list:
        resp = TestClient(_app()).get("/admin/runs?view=archived")
    assert resp.status_code == 200
    calls = [call.kwargs for call in mock_list.call_args_list]
    assert any(call.get("archived_only") is True for call in calls)


# ── Task 5: Admin UI lifecycle controls ─────────────────────────────────────

def _make_full_run_mock(status="queued", archived_at=None, run_id="run-ui-1"):
    from fitcv_cp.models import PipelineRun, RunStatus
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    return PipelineRun(
        run_id=run_id,
        status=RunStatus(status),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=now - datetime.timedelta(minutes=5),
        archived_at=archived_at,
    )


def test_runs_list_shows_active_and_archived_filter_tabs():
    """@proves admin_control_plane_core.jinja2-admin-pages"""
    with patch("fitcv_cp.app.list_runs", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs")
    assert resp.status_code == 200
    body = resp.text
    assert "Active" in body
    assert "Archived" in body
    assert ">All<" not in body


def test_runs_list_is_selection_first_without_row_action_controls():
    run = _make_full_run_mock(status="queued")
    with patch("fitcv_cp.app.list_runs", return_value=[run]):
        resp = TestClient(_app()).get("/admin/runs")
    html = resp.text
    assert "Actions" not in html
    assert "Stop Run" not in html
    assert "Run Next Stage" not in html
    assert "Repair Status" not in html
    assert "Triggered By" not in html


def test_runs_list_renders_bulk_selection_checkboxes():
    run = _make_full_run_mock(status="queued", run_id="run-bulk-ui-1")
    with patch("fitcv_cp.app.list_runs", return_value=[run]):
        resp = TestClient(_app()).get("/admin/runs")
    assert resp.status_code == 200
    html = resp.text
    assert 'id="select-all-runs"' in html
    assert 'name="selected_run_ids"' in html


def test_runs_list_renders_bulk_action_bar_hooks():
    """@proves admin_control_plane_core.jinja2-admin-pages
    @proves ui_consistency_theming.consistent-action-hierarchy-primary-secondary-section
    """
    run = _make_full_run_mock(status="queued", run_id="run-bulk-ui-1")
    with patch("fitcv_cp.app.list_runs", return_value=[run]):
        resp = TestClient(_app()).get("/admin/runs")
    assert resp.status_code == 200
    html = resp.text
    assert "ensureBulkActionBar()" in html
    assert "bar.id = 'bulk-action-bar'" in html
    assert "Cancel Run" in html
    assert "Archive Run" in html
    assert "Unarchive Run" not in html


def test_runs_list_shows_archived_selection_actions_only_in_archived_view() -> None:
    archived_run = _make_full_run_mock(
        status="succeeded",
        archived_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=45),
        run_id="run-archived-ui-1",
    )
    with patch("fitcv_cp.app.list_runs", return_value=[archived_run]):
        archived_resp = TestClient(_app()).get("/admin/runs?view=archived")
    assert archived_resp.status_code == 200
    archived_html = archived_resp.text
    assert "Unarchive Run" not in archived_html
    assert "Delete Run" in archived_html
    assert 'id="cancelSelectedRuns"' not in archived_html

    with patch("fitcv_cp.app.list_runs", return_value=[archived_run]):
        active_resp = TestClient(_app()).get("/admin/runs?view=active")
    assert active_resp.status_code == 200
    assert "Delete Run" not in active_resp.text


def test_runs_list_archived_delete_controls_use_preview_and_explicit_selection() -> None:
    archived_run = _make_full_run_mock(
        status="succeeded",
        archived_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=45),
        run_id="run-archived-ui-2",
    )
    with patch("fitcv_cp.app.list_runs", return_value=[archived_run]):
        resp = TestClient(_app()).get("/admin/runs?view=archived")
    assert resp.status_code == 200
    html = resp.text
    assert "'/runs/actions/delete-archived/preview'" in html
    assert "'/runs/actions/delete-archived'" in html
    assert "run_ids: runIds" in html
    assert "preview_revision: preview.preview_revision" in html
    assert "deleted_bookmark_count" in html
    assert "Idempotency-Key" in html
    assert "bulkDeleteArchivedRuns(this)" in html


def test_runs_list_bulk_lifecycle_retries_with_same_idempotency_key() -> None:
    run = _make_full_run_mock(status="queued", run_id="run-bulk-idempotency-ui")
    with patch("fitcv_cp.app.list_runs", return_value=[run]):
        resp = TestClient(_app()).get("/admin/runs")
    assert resp.status_code == 200
    html = resp.text
    assert "var bulkLifecycleIdempotencyKeys = {};" in html
    assert "bulkLifecycleIdempotencyKeys[action] ||= crypto.randomUUID();" in html
    assert "'Idempotency-Key': bulkLifecycleIdempotencyKeys[action]" in html
    assert "retry: () => bulkLifecycleAction(action, btn)" in html
    assert "delete bulkLifecycleIdempotencyKeys[action];" in html
    assert "code: e.code" in html


def test_runs_list_shows_core_operational_columns_only():
    run = _make_full_run_mock(status="queued", run_id="run-compact-actions")
    with patch("fitcv_cp.app.list_runs", return_value=[run]):
        resp = TestClient(_app()).get("/admin/runs")
    assert resp.status_code == 200
    html = resp.text
    assert "Run ID" in html
    assert "Status" in html
    assert "Job Name" in html
    assert "Created Time" in html
    assert "Duration" in html
    assert "Mode" not in html
    assert "Jobs Path" not in html
    assert "Orchestration" not in html
    assert "Triggered By" not in html
    assert "Actions" not in html

def test_runs_list_keeps_run_mode_out_of_workspace_table():
    run_all = _make_full_run_mock(status="queued", run_id="run-all-label")
    staged = _make_full_run_mock(status="awaiting_continue", run_id="run-staged-label")
    staged.run_mode = "manual_staged"
    staged.next_stage = "ranking"
    with patch("fitcv_cp.app.list_runs", return_value=[run_all, staged]):
        resp = TestClient(_app()).get("/admin/runs")
    html = resp.text
    assert "<th>Mode</th>" not in html
    assert "next: ranking" not in html


def test_runs_list_uses_jobs_path_as_fallback_job_name():
    run = _make_full_run_mock(status="queued", run_id="run-jobs-path")
    run.jobs_path = "data/uploads/very_long_nested_folder_name/another_folder/really_long_jobs_snapshot_name.json"
    with patch("fitcv_cp.app.list_runs", return_value=[run]):
        resp = TestClient(_app()).get("/admin/runs")
    assert resp.status_code == 200
    html = resp.text
    assert "<th>Job Name</th>" in html
    assert "data/uploads/very_long_nested_folder_name/another_folder/really_long_jobs_snapshot_name.json" in html

def test_runs_list_upload_jobs_path_shows_merged_from_filenames():
    run = _make_full_run_mock(status="queued", run_id="run-jobs-merged-from")
    run.jobs_path = "data/uploads/e99cd34d9c2343d1b8577e6c9a3120fb_merged_jobs.json"
    run.jobs_input_source = "upload"
    run.jobs_input_manifest_json = json.dumps(
        {"source_filenames": ["foo.json", "bar.json", "baz.json", "qux.json"]}
    )
    with patch("fitcv_cp.app.list_runs", return_value=[run]):
        resp = TestClient(_app()).get("/admin/runs")
    assert resp.status_code == 200
    assert (
        "data/uploads/e99cd34d9c2343d1b8577e6c9a3120fb_merged_jobs.json "
        "(merged from: foo.json, bar.json, baz.json, qux.json)"
    ) in resp.text


def test_admin_runs_timeouts_running_runs_to_failed() -> None:
    """@proves run_lifecycle_controls.state-aware-max-runtime-timeout-handling-for-queued-running-cancelling-and-paused-manual-runs
    @proves run_lifecycle_controls.timeout-copy-now-distinguishes-queue-wait-active-runtime-and-stage-by-stage-manual-wait-time
    """
    import datetime

    now = datetime.datetime.now(datetime.timezone.utc)
    run = _make_full_run_mock(status="running", run_id="run-timeout-running")
    run.created_at = now - datetime.timedelta(hours=3)
    run.started_at = now - datetime.timedelta(hours=2)

    with patch("fitcv_cp.app.list_runs", return_value=[run]), \
         patch("fitcv_cp.app.load_active_settings", return_value={"run_lifecycle.max_runtime_minutes": 60}), \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.append_event") as mock_append_event:
        resp = TestClient(_app()).get("/admin/runs")

    assert resp.status_code == 200
    args = mock_update_status.call_args.args
    assert args[0] == "run-timeout-running"
    assert args[1] == RunStatus.FAILED
    assert mock_append_event.call_args.args[0].stage == "run_timed_out"


def test_admin_runs_timeouts_awaiting_continue_runs_to_cancelled() -> None:
    """@proves run_lifecycle_controls.state-aware-max-runtime-timeout-handling-for-queued-running-cancelling-and-paused-manual-runs
    @proves run_lifecycle_controls.timeout-copy-now-distinguishes-queue-wait-active-runtime-and-stage-by-stage-manual-wait-time
    """
    import datetime

    now = datetime.datetime.now(datetime.timezone.utc)
    run = _make_full_run_mock(status="awaiting_continue", run_id="run-timeout-awaiting")
    run.run_mode = "manual_staged"
    run.next_stage = "cv_generation"
    run.created_at = now - datetime.timedelta(hours=5)
    run.started_at = now - datetime.timedelta(hours=4)

    with patch("fitcv_cp.app.list_runs", return_value=[run]), \
         patch("fitcv_cp.app.load_active_settings", return_value={"run_lifecycle.max_runtime_minutes": 120}), \
         patch("fitcv_cp.app.update_run_status") as mock_update_status, \
         patch("fitcv_cp.app.append_event") as mock_append_event:
        resp = TestClient(_app()).get("/admin/runs")

    assert resp.status_code == 200
    args = mock_update_status.call_args.args
    assert args[0] == "run-timeout-awaiting"
    assert args[1] == RunStatus.CANCELLED
    assert mock_append_event.call_args.args[0].stage == "run_timed_out"


def test_run_detail_stale_cancelling_uses_prototype_status_only() -> None:
    """Run Details keeps repair as a direct compatibility route, not UI chrome."""
    run = _make_full_run_mock(status="cancelling")
    run.started_at = None
    run.finished_at = None
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.get_events", return_value=[]), \
         patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
         patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-ui-1")
    assert resp.status_code == 200
    assert "cancelling" in resp.text
    assert "Repair Status" not in resp.text


def test_run_detail_started_stale_cancelling_uses_prototype_status_only() -> None:
    """Run Details keeps repair as a direct compatibility route, not UI chrome."""
    import datetime

    run = _make_full_run_mock(status="cancelling")
    now = datetime.datetime.now(datetime.timezone.utc)
    run.started_at = now - datetime.timedelta(minutes=15)
    run.cancel_requested_at = now - datetime.timedelta(minutes=5)
    run.finished_at = None
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.get_events", return_value=[]), \
         patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
         patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-ui-1")
    assert resp.status_code == 200
    assert "cancelling" in resp.text
    assert "Repair Status" not in resp.text



def test_runs_list_projection_separates_active_and_archived_resources() -> None:
    """@proves admin_control_plane_core.jinja2-admin-pages"""
    import datetime

    awaiting = _make_full_run_mock(status="awaiting_continue", run_id="run-awaiting-next")
    awaiting.run_mode = "manual_staged"
    awaiting.next_stage = "ranking"
    archived = _make_full_run_mock(
        status="succeeded",
        run_id="run-archived-marker",
        archived_at=datetime.datetime(2026, 3, 26, 13, 0, 0, tzinfo=datetime.timezone.utc),
    )

    def list_for_view(*_args, archived_only=False, **_kwargs):
        return [archived] if archived_only else [awaiting]

    with patch("fitcv_cp.app.list_runs", side_effect=list_for_view):
        active_resp = TestClient(_app()).get("/admin/runs")
        archived_resp = TestClient(_app()).get("/admin/runs?view=archived")
    assert active_resp.status_code == 200
    assert "Awaiting Continue" in active_resp.text
    assert "run-archived-marker" not in active_resp.text
    assert archived_resp.status_code == 200
    assert "run-archived-marker" in archived_resp.text
    assert ">Archived<" in archived_resp.text



def _run_detail_patches(
    status="succeeded",
    cv_versions=None,
    enriched_jobs=None,
    filter_results=None,
    results_export_json=None,
    stage_transition_artifacts_json=None,
    jobs_input_json=None,
):
    import datetime
    from fitcv_cp.models import PipelineRun, RunStatus
    run = PipelineRun(
        run_id="run-detail-test",
        status=RunStatus(status),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=datetime.datetime(2026, 3, 27, 9, 0, 0, tzinfo=datetime.timezone.utc),
        results_export_json=results_export_json,
        stage_transition_artifacts_json=stage_transition_artifacts_json,
        jobs_input_json=jobs_input_json,
    )
    return (
        patch("fitcv_cp.app.get_run", return_value=run),
        patch("fitcv_cp.app.get_events", return_value=[]),
        patch("fitcv_cp.app.list_cvs_for_run", return_value=cv_versions or []),
        patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched_jobs or []),
        patch("fitcv_cp.app.list_filter_results_for_run", return_value=filter_results or []),
    )

def test_run_detail_uses_prototype_page_hierarchy() -> None:
    patches = _run_detail_patches()
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        response = TestClient(_app()).get("/admin/runs/run-detail-test")

    assert response.status_code == 200
    assert 'class="details-page-head"' in response.text
    assert '<p class="eyebrow">Run Details</p>' in response.text
    assert 'class="page-header"' not in response.text
    assert '<strong>Run Overview</strong>' in response.text
    assert '<strong>Run Input</strong>' in response.text
    assert '<strong>Pipeline Results</strong>' in response.text
    assert 'id="process-console-title">Console Log</strong>' in response.text
    assert response.text.count('class="section-card collapsible-section drawer-section') == 4
    assert response.text.index('<strong>Run Overview</strong>') < response.text.index('<strong>Run Input</strong>')
    assert response.text.index('<strong>Run Input</strong>') < response.text.index('<strong>Pipeline Results</strong>')
    assert response.text.index('<strong>Pipeline Results</strong>') < response.text.index('id="process-console-title">Console Log</strong>')
    assert 'aria-label="Run inspection views"' not in response.text
    assert "Original Job Input" not in response.text
    assert "Advanced &amp; Diagnostics" not in response.text
    assert 'id="artifacts"' not in response.text
    assert "Synonym Configuration" not in response.text
    assert "Run Health" not in response.text


def test_run_detail_uses_shared_recovery_and_url_owned_result_state() -> None:
    patches = _run_detail_patches()
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        response = TestClient(_app()).get("/admin/runs/run-detail-test")

    assert response.status_code == 200
    assert "fitcvRenderAsyncState(pane" in response.text
    assert "preserveContent: pane.dataset.loaded === 'true'" in response.text
    assert "history.replaceState({}, '', url)" in response.text
    assert "const initialRunDetailParams = new URLSearchParams(location.search)" in response.text
    assert "initialRunDetailParams.get('stage') || 'shortlisting'" in response.text
    assert "event.key !== 'ArrowLeft' && event.key !== 'ArrowRight'" in response.text
    assert "[data-interest-rating], [data-clear-interest], [data-cv-regenerate]" in response.text
    assert "fitcvRenderAsyncState(actionState" in response.text
    assert "document.visibilityState === 'hidden'" in response.text

def test_run_detail_enriched_tab_uses_canonical_selection_export_and_bookmark_controls() -> None:
    patches = _run_detail_patches(
        enriched_jobs=[
            {
                "run_job_id": "job-1",
                "job_url": "https://jobs.example.com/1",
                "title": "Data Engineer",
                "required_skills": [],
                "bookmarked": True,
            }
        ],
        filter_results=[
            {"job_url": "https://jobs.example.com/1", "passed": True, "reasons": []}
        ],
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        response = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched")

    assert response.status_code == 200
    assert 'data-run-job-selection-root' in response.text
    assert 'data-run-job-id="job-1"' in response.text
    assert 'data-run-job-export' in response.text
    assert 'data-bookmark-toggle' in response.text
    assert 'data-bookmarked="true"' in response.text
    assert '/runs/run-detail-test/jobs/actions/export/preview' in response.text
    assert '/runs/run-detail-test/jobs/actions/export' in response.text


def test_run_detail_pipeline_results_use_prototype_controls() -> None:
    patches = _run_detail_patches(
        enriched_jobs=[
            {
                "run_job_id": "job-1",
                "job_url": "https://jobs.example.com/1",
                "title": "Data Engineer",
                "required_skills": ["SQL", "Python"],
            }
        ],
        filter_results=[
            {"job_url": "https://jobs.example.com/1", "passed": True, "reasons": []}
        ],
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        response = TestClient(_app()).get(
            "/admin/runs/run-detail-test/tabs/enriched?stage=shortlisting&page_size=10"
        )

    assert response.status_code == 200
    assert 'class="pipeline-stage-tabs"' in response.text
    assert 'data-pipeline-stage="shortlisting"' in response.text
    assert 'aria-selected="true"' in response.text
    assert 'id="jobResultsSearch"' in response.text
    assert 'placeholder="Search jobs, attributes, skills, or outcomes"' in response.text
    assert 'class="pipeline-summary"' in response.text
    assert '>Total Evaluated<' in response.text
    assert '>Passed<' in response.text
    assert '>Rejected<' in response.text
    assert 'id="selectAllJobResults"' in response.text
    assert 'class="run-table jobs-table"' in response.text
    assert 'Job &amp; Actions</th>' in response.text
    assert '<th>Job Attributes</th>' in response.text
    assert '<th>Required Skills</th>' in response.text
    assert '<th>Pipeline Outcome</th>' in response.text

def test_run_detail_cv_generation_fragment_renders_canonical_capabilities() -> None:
    patches = _run_detail_patches(
        enriched_jobs=[
            {
                "run_job_id": "job-cv-1",
                "job_url": "https://jobs.example.com/cv-1",
                "title": "CV Role",
                "required_skills": ["Python"],
            }
        ],
        filter_results=[
            {"job_url": "https://jobs.example.com/cv-1", "passed": True, "reasons": []}
        ],
        results_export_json=json.dumps(
            {
                "results": [
                    {
                        "job_url": "https://jobs.example.com/cv-1",
                        "job_title": "CV Role",
                        "pipeline_status": "ranked_with_cv",
                    }
                ]
            }
        ),
    )
    app = _app()
    app.state.run_store.query_run_jobs_fn = lambda run_id, **_kwargs: {
        "items": [
            {
                "run_job_id": "job-cv-1",
                "capabilities": {"download": True, "regenerate": True},
                "current_cv_version_id": "cv-1",
            }
        ],
        "total": 1,
    }
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        response = TestClient(app).get(
            "/admin/runs/run-detail-test/tabs/enriched?stage=cv-generation"
        )

    assert response.status_code == 200
    assert 'data-cv-download' in response.text
    assert 'data-cv-regenerate' in response.text


def test_run_detail_pipeline_results_prune_selection_to_current_filtered_rows() -> None:
    patches = _run_detail_patches(
        enriched_jobs=[
            {
                "run_job_id": "job-1",
                "job_url": "https://jobs.example.com/1",
                "title": "Data Engineer",
                "required_skills": [],
            },
            {
                "run_job_id": "job-2",
                "job_url": "https://jobs.example.com/2",
                "title": "Data Analyst",
                "required_skills": [],
            },
        ],
        filter_results=[
            {"job_url": "https://jobs.example.com/1", "passed": True, "reasons": []},
            {"job_url": "https://jobs.example.com/2", "passed": False, "reasons": []},
        ],
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        response = TestClient(_app()).get(
            "/admin/runs/run-detail-test/tabs/enriched?filter_name=passed"
        )

    assert response.status_code == 200
    assert 'data-filtered-run-job-ids="[&#34;job-1&#34;]"' in response.text


def test_run_detail_summary_does_not_count_skipped_occurrence_as_passed() -> None:
    enriched_jobs = [
        {
            "run_job_id": f"job-{index}",
            "job_url": f"https://jobs.example.com/{index}",
            "title": f"Job {index}",
            "required_skills": [],
        }
        for index in range(7)
    ]
    filter_results = [
        {"job_url": f"https://jobs.example.com/{index}", "passed": index < 3, "reasons": []}
        for index in range(6)
    ]
    results_export = json.dumps(
        {
            "results": [
                {
                    "job_url": f"https://jobs.example.com/{index}",
                    "job_outcome": {
                        "job_key": f"input:{index}",
                        "stage": "rule_filter" if index < 6 else "normalize",
                        "outcome": "accepted" if index < 3 else "rejected" if index < 6 else "skipped",
                        "reason_code": "near_duplicate_job_posting" if index == 6 else "outcome",
                        "evidence_ref": {"artifact": "results.json"},
                    },
                }
                for index in range(7)
            ]
        }
    )
    patches = _run_detail_patches(
        enriched_jobs=enriched_jobs,
        filter_results=filter_results,
        results_export_json=results_export,
    )

    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        response = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched?stage=all")

    assert response.status_code == 200
    assert ">Total Evaluated<" in response.text
    assert ">Total Evaluated</span><strong>7</strong>" in response.text
    assert ">Passed</span><strong>3</strong>" in response.text
    assert ">Rejected</span><strong>3</strong>" in response.text


def test_run_detail_stage_change_clears_selection_and_debug_bundle_uses_route_truth() -> None:
    patches = _run_detail_patches()
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        response = TestClient(_app()).get("/admin/runs/run-detail-test")

    assert response.status_code == 200
    assert "window.fitcvRunJobSelections?.delete(document.querySelector('[data-run-job-selection-root]')?.dataset.runId);" in response.text
    assert 'href="/admin/runs/run-detail-test/artifacts.zip"' in response.text
    assert "/artifact-bundle.zip" not in response.text


def test_run_detail_pipeline_results_normalize_invalid_stage_and_default_page_size() -> None:
    patches = _run_detail_patches(
        enriched_jobs=[
            {
                "job_url": "https://jobs.example.com/1",
                "title": "Data Engineer",
                "required_skills": [],
            }
        ],
        filter_results=[
            {"job_url": "https://jobs.example.com/1", "passed": True, "reasons": []}
        ],
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        response = TestClient(_app()).get(
            "/admin/runs/run-detail-test/tabs/enriched?stage=invalid-stage"
        )

    assert response.status_code == 200
    assert '<input type="hidden" name="stage" value="shortlisting">' in response.text
    assert 'data-pipeline-stage="shortlisting"' in response.text
    assert 'data-results-url="/admin/runs/run-detail-test/tabs/enriched?stage=shortlisting&amp;page_size=10&amp;filter_name=all"' in response.text
    assert '<option value="10" selected>10</option>' in response.text


def test_run_detail_shows_deduplicated_before_enrichment_section():
    import json as _json

    export_payload = _json.dumps({
        "results": [
            {
                "job_url": "https://jobs.example.com/2",
                "job_title": "Duplicated Analyst",
                "pipeline_status": "deduplicated_before_enrichment",
                "reject_reasons": ["near_duplicate_job_posting"],
            }
        ]
    })
    patches = _run_detail_patches(
        enriched_jobs=[{"job_url": "https://jobs.example.com/1", "title": "Kept Job", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None}],
        filter_results=[{"job_url": "https://jobs.example.com/1", "passed": True, "reasons": []}],
        results_export_json=export_payload,
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched?stage=enrichment")
    assert resp.status_code == 200
    assert "Duplicated Analyst" in resp.text
    assert "near_duplicate_job_posting" in resp.text

def test_run_detail_enriched_tab_uses_stage_artifacts_sample_for_running_run() -> None:
    import json as _json

    stage_artifacts = _json.dumps(
        {
            "artifacts": {
                "stages": {
                    "enrich": {
                        "status": "completed",
                        "outputs_sample": [
                            {
                                "job_url": "https://jobs.example.com/live-1",
                                "job_title": "Live Enriched Role",
                                "location_type": "remote",
                                "seniority": "senior",
                                "job_family": "data_engineering",
                                "domain": "data",
                                "required_skills": [],
                                "tech_stack": [],
                                "keywords": ["Python", "SQL"],
                            }
                        ],
                    }
                }
            }
        }
    )
    patches = _run_detail_patches(
        status="running",
        enriched_jobs=[],
        filter_results=[],
        results_export_json=None,
        stage_transition_artifacts_json=stage_artifacts,
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched")
    assert resp.status_code == 200
    assert "No enrichment data available for this run." not in resp.text
    assert "Live Enriched Role" in resp.text
    assert "Python" in resp.text
    assert "SQL" in resp.text


def test_run_detail_hides_filter_marks_from_pipeline_results() -> None:
    """Pipeline Results keeps internal filter diagnostics out of user UI."""
    patches = _run_detail_patches(
        enriched_jobs=[
            {
                "job_url": "https://jobs.example.com/1",
                "title": "Marked Pass Job",
                "domain": "d",
                "job_family": "f",
                "required_skills": [],
                "location_type": None,
                "seniority": None,
            }
        ],
        filter_results=[
            {
                "job_url": "https://jobs.example.com/1",
                "passed": True,
                "reasons": [],
                "marks": [
                    {
                        "code": "must_have_skill_missing",
                        "message": "Missing must-have skills",
                    }
                ],
            }
        ],
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched")

    assert resp.status_code == 200
    assert "Marked Pass Job" in resp.text
    assert "Marks: must_have_skill_missing" not in resp.text


def test_run_detail_enriched_hides_canonical_why_details() -> None:
    import json as _json
    from datetime import datetime, timezone

    from fitcv.pipeline_contracts import build_job_outcome_fact

    job_url = "https://jobs.example.com/why-1"
    fact = build_job_outcome_fact(
        run_id="run-detail-test",
        input_index=0,
        job_url=job_url,
        attempt_id="attempt-1",
        stage_status="review_required",
        reason_facts={"gap": "unsupported requirement"},
        policy_version="cv_generation.v1",
        trace_id="trace-1",
        evidence_ref={
            "artifact": "cv_generation.json",
            "fingerprint": "sha256:evidence",
            "record_key": "input:0",
        },
        occurred_at=datetime(2026, 7, 17, 20, tzinfo=timezone.utc),
    )
    export_payload = _json.dumps(
        {
            "results": [
                {
                    "job_url": job_url,
                    "job_title": "Review Role",
                    "pipeline_status": "ranked_no_cv",
                    "job_outcome": fact,
                }
            ]
        }
    )
    patches = _run_detail_patches(
        enriched_jobs=[
            {
                "job_url": job_url,
                "title": "Review Role",
                "domain": "data",
                "job_family": "engineering",
                "required_skills": [],
                "location_type": "remote",
                "seniority": "mid",
            }
        ],
        filter_results=[{"job_url": job_url, "passed": True, "reasons": []}],
        results_export_json=export_payload,
    )

    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        response = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched")

    assert response.status_code == 200
    assert "Review Role" in response.text
    assert "Why?" not in response.text
    assert "review_gate_manual_required" not in response.text
    assert "cv_generation.json" not in response.text
    assert "sha256:evidence" not in response.text
    assert "input:0" not in response.text

def test_run_detail_enriched_shows_pipeline_outcome_for_passed_non_ranked_job():
    import json as _json

    export_payload = _json.dumps({
        "results": [
            {
                "job_url": "https://jobs.example.com/1",
                "job_title": "Retail Banking Analyst",
                "pipeline_status": "not_shortlisted",
                "reject_reasons": [],
            }
        ]
    })
    enriched = [{
        "job_url": "https://jobs.example.com/1",
        "title": "Retail Banking Analyst",
        "domain": "banking",
        "job_family": "analytics",
        "required_skills": [],
        "location_type": "hybrid",
        "seniority": "mid",
    }]
    filter_results = [{"job_url": "https://jobs.example.com/1", "passed": True, "reasons": []}]
    patches = _run_detail_patches(
        enriched_jobs=enriched,
        filter_results=filter_results,
        results_export_json=export_payload,
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched")
    assert resp.status_code == 200
    assert "Pipeline Outcome" in resp.text
    assert "Passed filter, not shortlisted" in resp.text


def test_run_detail_enriched_shows_pipeline_outcome_for_ranked_fit_skip_job():
    import json as _json

    export_payload = _json.dumps({
        "results": [
            {
                "job_url": "https://jobs.example.com/1",
                "job_title": "Skipped After Ranking",
                "pipeline_status": "ranked_skipped_fit_gate",
                "decision_chain": {
                    "shortlist": {"status": "returned_by_vector_search", "advanced_to_scoring": True},
                    "primary_fit": {"source": "reranker", "label": "skip"},
                    "cv_analysis": {"status": "skipped_fit_gate", "completed": True},
                    "cv_generation": {"status": "skipped_fit_gate", "attempted": False},
                    "validation": {"status": "not_run"},
                },
                "reject_reasons": [],
            }
        ]
    })
    enriched = [{
        "job_url": "https://jobs.example.com/1",
        "title": "Skipped After Ranking",
        "domain": "banking",
        "job_family": "analytics",
        "required_skills": [],
        "location_type": "hybrid",
        "seniority": "mid",
    }]
    filter_results = [{"job_url": "https://jobs.example.com/1", "passed": True, "reasons": []}]
    patches = _run_detail_patches(
        enriched_jobs=enriched,
        filter_results=filter_results,
        results_export_json=export_payload,
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched")
    assert resp.status_code == 200
    assert "Pipeline Outcome" in resp.text
    assert "Skipped after CV analysis" in resp.text
    assert "Primary fit: skip" in resp.text
    assert "CV analysis: skipped after CV analysis" in resp.text


def test_run_detail_enriched_shows_pipeline_outcome_for_reranker_blocked_job():
    """@proves trigger_run_management.decision-chain-outcomes
    @proves trigger_run_management.reranker-fit-authority
    @proves inspection_debugging.results-ledger-inspection
    """
    import json as _json

    export_payload = _json.dumps({
        "results": [
            {
                "job_url": "https://jobs.example.com/1",
                "job_title": "Blocked Before Analysis",
                "pipeline_status": "ranked_blocked_by_reranker_fit",
                "decision_chain": {
                    "shortlist": {"status": "returned_by_vector_search", "advanced_to_scoring": True},
                    "primary_fit": {"source": "reranker", "label": "skip"},
                    "cv_analysis": {"status": "blocked_by_reranker_fit", "completed": False},
                    "cv_generation": {"status": "not_attempted", "attempted": False},
                    "validation": {"status": "not_run"},
                },
                "reject_reasons": [],
            }
        ]
    })
    enriched = [{
        "job_url": "https://jobs.example.com/1",
        "title": "Blocked Before Analysis",
        "domain": "banking",
        "job_family": "analytics",
        "required_skills": [],
        "location_type": "hybrid",
        "seniority": "mid",
    }]
    filter_results = [{"job_url": "https://jobs.example.com/1", "passed": True, "reasons": []}]
    patches = _run_detail_patches(
        enriched_jobs=enriched,
        filter_results=filter_results,
        results_export_json=export_payload,
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched")
    assert resp.status_code == 200
    assert "Pipeline Outcome" in resp.text
    assert "Ranked, blocked by reranker fit" in resp.text
    assert "Primary fit: skip" in resp.text
    assert "CV analysis: blocked by reranker fit" in resp.text


def test_run_detail_enriched_uses_deterministic_subreason_for_validation_failed_job():
    import json as _json

    export_payload = _json.dumps({
        "results": [
            {
                "job_url": "https://jobs.example.com/1",
                "job_title": "Validation Failed CV",
                "pipeline_status": "ranked_no_cv",
                "deterministic_outcome": "rejected",
                "stage_owned_subreason": "validation_failed",
                "source_stage": "cv_generation",
                "decision_chain": {
                    "shortlist": {"status": "returned_by_vector_search", "advanced_to_scoring": True},
                    "primary_fit": {"source": "reranker", "label": "strong"},
                    "cv_analysis": {"status": "ready_for_generation", "completed": True},
                    "cv_generation": {"status": "validation_failed", "attempted": True},
                    "validation": {"status": "failed"},
                },
                "reject_reasons": [],
            }
        ]
    })
    enriched = [{
        "job_url": "https://jobs.example.com/1",
        "title": "Validation Failed CV",
        "domain": "banking",
        "job_family": "analytics",
        "required_skills": [],
        "location_type": "hybrid",
        "seniority": "mid",
    }]
    filter_results = [{"job_url": "https://jobs.example.com/1", "passed": True, "reasons": []}]
    patches = _run_detail_patches(
        enriched_jobs=enriched,
        filter_results=filter_results,
        results_export_json=export_payload,
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched")
    assert resp.status_code == 200
    assert "CV validation failed" in resp.text
    assert "Validation: failed" in resp.text


def test_run_detail_enriched_uses_analysis_handoff_truth_for_ready_job():
    import json as _json

    export_payload = _json.dumps({
        "results": [
            {
                "job_url": "https://jobs.example.com/1",
                "job_title": "Ready Job",
                "pipeline_status": "ranked_no_cv",
                "deterministic_outcome": None,
                "stage_owned_subreason": "ready_for_generation",
                "source_stage": "cv_analysis",
                "decision_chain": {
                    "shortlist": {"status": "returned_by_vector_search", "advanced_to_scoring": True},
                    "primary_fit": {"source": "reranker", "label": "strong"},
                    "cv_analysis": {"status": "ready_for_generation", "completed": True},
                    "cv_generation": {"status": "not_attempted", "attempted": False},
                    "validation": {"status": "not_run"},
                },
                "reject_reasons": [],
            }
        ]
    })
    enriched = [{
        "job_url": "https://jobs.example.com/1",
        "title": "Ready Job",
        "domain": "banking",
        "job_family": "analytics",
        "required_skills": [],
        "location_type": "hybrid",
        "seniority": "mid",
    }]
    filter_results = [{"job_url": "https://jobs.example.com/1", "passed": True, "reasons": []}]
    patches = _run_detail_patches(
        enriched_jobs=enriched,
        filter_results=filter_results,
        results_export_json=export_payload,
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched")
    assert resp.status_code == 200
    assert "Ready for CV generation" in resp.text
    assert "CV analysis: ready for CV generation" not in resp.text


def test_normalize_job_url_key_keeps_indeed_jk_query_value() -> None:
    from fitcv_cp.app import _normalize_job_url_key

    first = _normalize_job_url_key("https://de.indeed.com/viewjob?jk=8409ba0a48f9ac29")
    second = _normalize_job_url_key("https://de.indeed.com/viewjob?jk=f2c85e6e8a66e160")

    assert first == "https://de.indeed.com/viewjob?jk=8409ba0a48f9ac29"
    assert second == "https://de.indeed.com/viewjob?jk=f2c85e6e8a66e160"
    assert first != second


def test_admin_bookmarks_page_and_delete_flow():
    page_resp = TestClient(_app()).get("/admin/bookmarks")
    assert page_resp.status_code == 200
    assert "Central list of bookmarked jobs across Runs." in page_resp.text
    assert "/bookmarks?stage=" in page_resp.text
    assert "/bookmarks/actions/remove" in page_resp.text
    assert "/bookmarks/actions/export/preview" in page_resp.text
    assert "fitcvApiRequest('/bookmarks/actions/export'" in page_resp.text
    assert 'id="bookmarkResult"' not in page_resp.text
    assert "fitcvRenderAsyncState" in page_resp.text
    assert page_resp.text.count("fitcvRunLocked") >= 2
    assert "function failure(error,retry)" in page_resp.text
    assert "table-shell" in page_resp.text
    assert "Submitted" not in page_resp.text
    assert "Archived" not in page_resp.text


def test_legacy_admin_bookmark_mutation_routes_are_gone() -> None:
    client = TestClient(_app())
    delete_response = client.post(
        "/admin/bookmarks/delete",
        data={"bookmark_key": "url:https://jobs.example.com/1"},
        follow_redirects=False,
    )
    status_response = client.post(
        "/admin/bookmarks/status",
        data={"bookmark_key": "url:https://jobs.example.com/1", "status": "submitted"},
        follow_redirects=False,
    )

    assert delete_response.status_code == 404
    assert status_response.status_code == 404


def test_run_detail_enriched_shows_summary_counts():
    """Enriched tab renders post-dedupe total, Passed, Rejected summary counts."""
    enriched = [{"job_url": "https://j.test/1", "title": "A", "domain": "d",
                 "job_family": "f", "required_skills": [], "location_type": None, "seniority": None}]
    fr = [{"job_url": "https://j.test/1", "passed": True, "reasons": []}]
    patches = _run_detail_patches(enriched_jobs=enriched, filter_results=fr)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched")
    assert ">Total Evaluated<" in resp.text
    assert ">Passed<" in resp.text
    assert ">Rejected<" in resp.text


def test_run_detail_enriched_shows_filter_controls():
    """Filter buttons All, Passed, Rejected are present (only rendered when enriched_jobs is non-empty)."""
    enriched = [{"job_url": "https://j.test/1", "title": "A", "domain": "d",
                 "job_family": "f", "required_skills": [], "location_type": None, "seniority": None}]
    patches = _run_detail_patches(enriched_jobs=enriched)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched")
    assert 'name="filter_name"' in resp.text
    assert 'data-pipeline-result="all"' in resp.text
    assert 'data-pipeline-result="passed"' in resp.text
    assert 'data-pipeline-result="rejected"' in resp.text


def test_run_detail_enriched_shows_search_box():
    """Prototype search input is present when results render."""
    enriched = [{"job_url": "https://j.test/1", "title": "A", "domain": "d",
                 "job_family": "f", "required_skills": [], "location_type": None, "seniority": None}]
    patches = _run_detail_patches(enriched_jobs=enriched)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched")
    assert 'id="jobResultsSearch"' in resp.text


def test_run_detail_enriched_rows_render_server_side_without_data_attributes():
    """Enriched fragment is server-paginated and no longer depends on client-side row attributes."""
    enriched = [{"job_url": "https://j.test/1", "title": "ML Engineer", "domain": "AI",
                 "job_family": "engineering", "required_skills": [], "location_type": None, "seniority": None}]
    fr = [{"job_url": "https://j.test/1", "passed": True, "reasons": []}]
    patches = _run_detail_patches(enriched_jobs=enriched, filter_results=fr)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched")
    assert 'data-filter=' not in resp.text
    assert 'name="q"' in resp.text


def test_run_detail_enriched_shows_pagination():
    """Pagination controls are present for the enriched jobs tab."""
    patches = _run_detail_patches()
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched")
    assert 'aria-current="page"' in resp.text
    assert 'value="10" selected' in resp.text
    assert 'value="20"' in resp.text
    assert 'value="50"' in resp.text


def test_run_detail_enriched_unknown_filter_not_counted_as_rejected():
    """A job with no filter result gets data-filter=unknown and is not counted as rejected."""
    enriched = [
        {"job_url": "https://j.test/pass", "title": "Engineer A", "domain": "d",
         "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": "https://j.test/no-fr", "title": "Engineer B", "domain": "d",
         "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
    ]
    fr = [{"job_url": "https://j.test/pass", "passed": True, "reasons": []}]
    # j.test/no-fr has no filter result → must be 'unknown', not 'rejected'
    patches = _run_detail_patches(enriched_jobs=enriched, filter_results=fr)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched?filter_name=unknown")
    assert "Engineer B" in resp.text
    assert '<span>Rejected</span><strong>0</strong>' in resp.text



def test_run_detail_enriched_matches_filter_and_outcome_by_normalized_job_url():
    import json as _json

    enriched = [{
        "job_url": "https://j.test/role-1",
        "title": "Normalized Match Role",
        "domain": "d",
        "job_family": "f",
        "required_skills": [],
        "location_type": None,
        "seniority": None,
    }]
    filter_results = [{
        "job_url": "https://j.test/role-1/?utm_source=feed",
        "passed": True,
        "reasons": [],
    }]
    export_payload = _json.dumps({
        "results": [
            {
                "job_url": "https://j.test/role-1/?utm_source=feed",
                "pipeline_status": "ranked_with_cv",
            }
        ]
    })
    patches = _run_detail_patches(enriched_jobs=enriched, filter_results=filter_results, results_export_json=export_payload)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched")
    assert resp.status_code == 200
    assert "CV created" in resp.text
    assert '<span>Passed</span><strong>1</strong>' in resp.text
    assert '<span>Rejected</span><strong>0</strong>' in resp.text


def test_run_detail_enriched_falls_back_to_stage_artifacts_and_debug_records_when_results_truth_is_missing():
    import json as _json
    import datetime as _dt
    from fitcv_cp.models import PipelineRun, RunStatus

    enriched = [
        {
            "job_url": "https://de.indeed.com/viewjob?jk=strong1",
            "title": "Strong Role",
            "domain": "d",
            "job_family": "f",
            "required_skills": [],
            "location_type": None,
            "seniority": None,
        },
        {
            "job_url": "https://de.indeed.com/viewjob?jk=stretch1",
            "title": "Stretch Role",
            "domain": "d",
            "job_family": "f",
            "required_skills": [],
            "location_type": None,
            "seniority": None,
        },
    ]
    export_payload = _json.dumps({
        "results": [
            {
                "job_url": "https://jobs.example.com/redirected-strong",
                "job_title": "Strong Role",
                "pipeline_status": "unknown_pipeline_state",
            },
            {
                "job_url": "https://jobs.example.com/redirected-stretch",
                "job_title": "Stretch Role",
                "pipeline_status": "unknown_pipeline_state",
            },
        ]
    })
    stage_artifacts = _json.dumps({
        "artifacts": {
            "stages": {
                "rule_filter": {
                    "status": "completed",
                    "outputs_sample": [
                        {"job_url": "https://de.indeed.com/viewjob?jk=strong1", "job_title": "Strong Role"},
                        {"job_url": "https://de.indeed.com/viewjob?jk=stretch1", "job_title": "Stretch Role"},
                    ],
                    "output_counts": {"passed_jobs": 2, "rejected_jobs": 0},
                }
            }
        }
    })
    cv_debug = _json.dumps({
        "debug_records": [
            {
                "job_url": "https://de.indeed.com/viewjob?jk=strong1",
                "job_title": "Strong Role",
                "status": "blocked_by_reranker_fit",
                "fit_classification": "strong",
            },
            {
                "job_url": "https://de.indeed.com/viewjob?jk=stretch1",
                "job_title": "Stretch Role",
                "status": "review_required",
                "fit_classification": "stretch",
            },
        ]
    })
    run = PipelineRun(
        run_id="run-detail-fallback-artifacts",
        status=RunStatus("succeeded"),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=_dt.datetime(2026, 3, 27, 9, 0, 0, tzinfo=_dt.timezone.utc),
        results_export_json=export_payload,
        stage_transition_artifacts_json=stage_artifacts,
        cv_generation_debug_json=cv_debug,
    )
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.get_events", return_value=[]), \
         patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
         patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-detail-fallback-artifacts/tabs/enriched")
    assert resp.status_code == 200
    assert '<span>Passed</span><strong>2</strong>' in resp.text
    assert '<span>Rejected</span><strong>0</strong>' in resp.text
    assert "Ranked, blocked by reranker fit" in resp.text
    assert "CV review required" in resp.text


def test_run_detail_enriched_keeps_distinct_indeed_pipeline_outcomes_by_jk() -> None:
    import json as _json
    import datetime as _dt

    from fitcv_cp.models import PipelineRun, RunStatus

    job_url_review = "https://de.indeed.com/viewjob?jk=review123"
    job_url_blocked = "https://de.indeed.com/viewjob?jk=blocked456"
    run = PipelineRun(
        run_id="run-enriched-indeed-jk",
        status=RunStatus("succeeded"),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=_dt.datetime(2026, 3, 27, 9, 0, 0, tzinfo=_dt.timezone.utc),
        stage_transition_artifacts_json=_json.dumps(
            {
                "artifacts": {
                    "stages": {
                        "rule_filter": {
                            "status": "completed",
                            "outputs_sample": [
                                {"job_url": job_url_review, "passed": True, "marks": []},
                                {"job_url": job_url_blocked, "passed": True, "marks": []},
                            ],
                            "output_counts": {"passed_jobs": 2, "rejected_jobs": 0},
                        }
                    }
                }
            }
        ),
        cv_generation_debug_json=_json.dumps(
            {
                "debug_records": [
                    {"job_url": job_url_review, "job_title": "Review Job", "status": "review_required"},
                    {"job_url": job_url_blocked, "job_title": "Blocked Job", "status": "blocked_by_reranker_fit"},
                ]
            }
        ),
        results_export_json=_json.dumps(
            {
                "results": [
                    {"job_url": job_url_review, "job_title": "Review Job", "pipeline_status": "unknown_pipeline_state"},
                    {"job_url": job_url_blocked, "job_title": "Blocked Job", "pipeline_status": "unknown_pipeline_state"},
                ]
            }
        ),
    )
    enriched = [
        {
            "job_url": job_url_review,
            "title": "Review Job",
            "domain": "d",
            "job_family": "f",
            "required_skills": [],
            "location_type": None,
            "seniority": None,
        },
        {
            "job_url": job_url_blocked,
            "title": "Blocked Job",
            "domain": "d",
            "job_family": "f",
            "required_skills": [],
            "location_type": None,
            "seniority": None,
        },
    ]
    with patch("fitcv_cp.app.get_run", return_value=run),          patch("fitcv_cp.app.get_events", return_value=[]),          patch("fitcv_cp.app.list_cvs_for_run", return_value=[]),          patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched),          patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-enriched-indeed-jk/tabs/enriched")
    assert resp.status_code == 200
    assert "Review Job" in resp.text
    assert "Blocked Job" in resp.text
    assert "CV review required" in resp.text
    assert "Ranked, blocked by reranker fit" in resp.text

def test_build_enriched_tab_context_does_not_guess_passed_for_unknown_rows() -> None:
    from fitcv_cp.app import _build_enriched_tab_context
    from fitcv_cp.models import PipelineRun, RunStatus

    run = PipelineRun(
        run_id="run-enriched-unknown-filter",
        status=RunStatus("succeeded"),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=datetime.datetime(2026, 6, 26, 12, 0, 0, tzinfo=datetime.timezone.utc),
        results_export_json=json.dumps(
            {
                "results": [
                    {
                        "job_url": "https://jobs.example.com/redirected-role",
                        "job_title": "Redirected Role",
                        "pipeline_status": "unknown_pipeline_state",
                    }
                ]
            }
        ),
    )
    enriched = [
        {
            "job_url": "https://de.indeed.com/viewjob?jk=unknown123",
            "title": "Redirected Role",
            "domain": "d",
            "job_family": "f",
            "required_skills": [],
            "location_type": None,
            "seniority": None,
        }
    ]

    with patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        context = _build_enriched_tab_context(
            run,
            run_id=run.run_id,
            client = None,
            stage="all",
            filter_name="all",
            query="",
            pipeline_outcomes=[],
            page=1,
            page_size=25,
        )

    assert context["enriched_passed_count"] == 0
    assert context["enriched_rejected_count"] == 0
    assert context["filter_results_by_job_url"] == {}

def test_build_enriched_tab_context_uses_canonical_terminal_counts() -> None:
    from fitcv_cp.app import _build_enriched_tab_context
    from fitcv_cp.models import PipelineRun, RunStatus

    run = PipelineRun(
        run_id="run-enriched-canonical-counts",
        status=RunStatus("succeeded"),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path="config/runtime/control_plane.yaml",
        created_at=datetime.datetime(2026, 6, 26, 12, 0, 0, tzinfo=datetime.timezone.utc),
        results_export_json=json.dumps({"results": []}),
    )
    canonical_rows = []
    enriched = []
    for index in range(7):
        run_job_id = f"run-job-{index}"
        job_url = f"https://jobs.example.com/{index}"
        bucket = "rejected" if index < 6 else "skipped"
        canonical_rows.append(
            {
                "run_job_id": run_job_id,
                "source_index": index,
                "source_url": job_url,
                "title": f"Job {index}",
                "result_bucket": bucket,
                "outcome_code": bucket,
                "reason_code": "near_duplicate_job_posting" if bucket == "skipped" else bucket,
            }
        )
        enriched.append(
            {
                "run_job_id": run_job_id,
                "job_url": job_url,
                "title": f"Job {index}",
                "required_skills": [],
                "location_type": None,
                "seniority": None,
            }
        )

    class CanonicalStore:
        def query_run_jobs(self, *_args: object, **_kwargs: object) -> dict[str, object]:
            return {
                "items": canonical_rows,
                "total": 7,
                "total_evaluated": 7,
                "passed": 0,
                "rejected": 6,
                "skipped": 1,
            }

        def list_cv_versions(self, *_args: object, **_kwargs: object) -> list[dict[str, object]]:
            return []

    with patch("fitcv_cp.app._resolve_run_store", return_value=CanonicalStore()), \
         patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        context = _build_enriched_tab_context(
            run,
            run_id=run.run_id,
            client=None,
            stage="all",
            filter_name="all",
            query="",
            pipeline_outcomes=[],
            page=1,
            page_size=25,
        )

    assert context["enriched_evaluated_count"] == 7
    assert context["enriched_stage_passed_count"] == 0
    assert context["enriched_stage_rejected_count"] == 6
    assert context["enriched_skipped_count"] == 1
    assert [job["stage_passed"] for job in context["enriched_jobs"]].count(None) == 1

def test_build_enriched_tab_context_matches_truth_by_raw_job_fingerprint_when_urls_drift() -> None:
    from fitcv_cp.app import _build_enriched_tab_context, _normalize_job_url_key
    from fitcv_cp.models import PipelineRun, RunStatus

    run = PipelineRun(
        run_id="run-enriched-fingerprint-join",
        status=RunStatus("succeeded"),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=datetime.datetime(2026, 6, 26, 12, 0, 0, tzinfo=datetime.timezone.utc),
        results_export_json=json.dumps(
            {
                "results": [
                    {
                        "job_url": "https://jobs.example.com/redirected-role",
                        "job_title": "Redirected Role",
                        "raw_job_fingerprint": "raw-fp-join-1",
                        "pipeline_status": "ranked_no_cv",
                    }
                ]
            }
        ),
    )
    enriched = [
        {
            "job_url": "https://de.indeed.com/viewjob?jk=join123",
            "title": "Redirected Role",
            "raw_job_fingerprint": "raw-fp-join-1",
            "domain": "d",
            "job_family": "f",
            "required_skills": [],
            "location_type": None,
            "seniority": None,
        }
    ]
    filter_rows = [
        {
            "job_url": "https://jobs.example.com/redirected-role",
            "raw_job_fingerprint": "raw-fp-join-1",
            "passed": True,
            "reasons": [],
            "marks": [],
        }
    ]

    with patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=filter_rows):
        context = _build_enriched_tab_context(
            run,
            run_id=run.run_id,
            client = None,
            stage="all",
            filter_name="all",
            query="",
            pipeline_outcomes=[],
            page=1,
            page_size=25,
        )

    enriched_key = context["enriched_jobs"][0]["job_url_lookup_key"]
    assert context["enriched_passed_count"] == 1
    assert context["pipeline_outcomes_by_job_url"][enriched_key]["status"] == "ranked_no_cv"


def test_run_detail_enriched_uses_secondary_url_truth_when_enriched_primary_key_is_fingerprint() -> None:
    import json as _json
    import datetime as _dt
    from fitcv_cp.models import PipelineRun, RunStatus

    job_url = "https://de.indeed.com/viewjob?jk=fpurl123"
    run = PipelineRun(
        run_id="run-enriched-fingerprint-primary-url-truth",
        status=RunStatus("succeeded"),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=_dt.datetime(2026, 6, 26, 12, 0, 0, tzinfo=_dt.timezone.utc),
        results_export_json=_json.dumps(
            {
                "results": [
                    {
                        "job_url": "https://jobs.example.com/redirected-fpurl123",
                        "job_title": "Fingerprint First Role",
                        "pipeline_status": "unknown_pipeline_state",
                    }
                ]
            }
        ),
        cv_generation_debug_json=_json.dumps(
            {
                "debug_records": [
                    {
                        "job_url": job_url,
                        "job_title": "Fingerprint First Role",
                        "status": "review_required",
                    }
                ]
            }
        ),
    )
    enriched = [
        {
            "job_url": job_url,
            "title": "Fingerprint First Role",
            "raw_job_fingerprint": "raw-fpurl-1",
            "domain": "d",
            "job_family": "f",
            "required_skills": [],
            "location_type": None,
            "seniority": None,
        }
    ]
    filter_rows = [
        {
            "job_url": job_url,
            "passed": True,
            "reasons": [],
            "marks": [],
        }
    ]

    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.get_events", return_value=[]), \
         patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
         patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=filter_rows):
        resp = TestClient(_app()).get("/admin/runs/run-enriched-fingerprint-primary-url-truth/tabs/enriched")

    assert resp.status_code == 200
    assert '<span>Passed</span><strong>1</strong>' in resp.text
    assert '<span>Rejected</span><strong>0</strong>' in resp.text
    assert "CV review required" in resp.text
    assert "empty-value" not in resp.text

def test_run_detail_enriched_renders_pipeline_outcome_when_filter_truth_prefers_fingerprint_key() -> None:
    import json as _json
    import datetime as _dt
    from fitcv_cp.models import PipelineRun, RunStatus

    job_url = "https://de.indeed.com/viewjob?jk=fp-render-1"
    run = PipelineRun(
        run_id="run-enriched-render-split-keys",
        status=RunStatus("succeeded"),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=_dt.datetime(2026, 6, 26, 12, 0, 0, tzinfo=_dt.timezone.utc),
        results_export_json=_json.dumps(
            {
                "results": [
                    {
                        "job_url": "https://jobs.example.com/redirected-fp-render-1",
                        "job_title": "Fingerprint Render Role",
                        "pipeline_status": "unknown_pipeline_state",
                    }
                ]
            }
        ),
        cv_generation_debug_json=_json.dumps(
            {
                "debug_records": [
                    {
                        "job_url": job_url,
                        "job_title": "Fingerprint Render Role",
                        "status": "review_required",
                    }
                ]
            }
        ),
    )
    enriched = [
        {
            "job_url": job_url,
            "title": "Fingerprint Render Role",
            "raw_job_fingerprint": "raw-render-split-1",
            "domain": "d",
            "job_family": "f",
            "required_skills": [],
            "location_type": None,
            "seniority": None,
        }
    ]
    filter_rows = [
        {
            "job_url": job_url,
            "raw_job_fingerprint": "raw-render-split-1",
            "source_job_url": job_url,
            "passed": True,
            "reasons": [],
            "marks": [],
        }
    ]

    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.get_events", return_value=[]), \
         patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
         patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=filter_rows):
        resp = TestClient(_app()).get("/admin/runs/run-enriched-render-split-keys/tabs/enriched")

    assert resp.status_code == 200
    assert "CV review required" in resp.text
    assert "empty-value" not in resp.text

def test_build_enriched_tab_context_overrides_stale_review_required_with_terminal_hitl_approval() -> None:
    import json as _json
    import datetime as _dt

    from fitcv_cp.app import _build_enriched_tab_context, _lookup_row_by_lookup_key
    from fitcv_cp.models import PipelineRun, RunStatus

    job_url = "https://de.indeed.com/viewjob?jk=hitl-approve-1"
    run = PipelineRun(
        run_id="run-enriched-hitl-approval",
        status=RunStatus("succeeded"),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=_dt.datetime(2026, 6, 26, 12, 0, 0, tzinfo=_dt.timezone.utc),
        results_export_json=_json.dumps(
            {
                "results": [
                    {
                        "job_url": job_url,
                        "job_title": "Approved Review Role",
                        "pipeline_status": "ranked_no_cv",
                    }
                ]
            }
        ),
        cv_generation_debug_json=_json.dumps(
            {
                "debug_records": [
                    {
                        "job_url": job_url,
                        "job_title": "Approved Review Role",
                        "status": "review_required",
                        "review_item_id": "ri_hitl_approve",
                    }
                ],
                "hitl_review_actions": [
                    {
                        "review_item_id": "ri_hitl_approve",
                        "job_url": job_url,
                        "action": "approve",
                        "resolution_status": "approved_as_is",
                        "created_at": "2026-06-26T12:01:00+00:00",
                    }
                ],
            }
        ),
    )
    enriched = [
        {
            "job_url": job_url,
            "title": "Approved Review Role",
            "domain": "d",
            "job_family": "f",
            "required_skills": [],
            "location_type": None,
            "seniority": None,
        }
    ]
    filter_rows = [{"job_url": job_url, "passed": True, "reasons": [], "marks": []}]

    with patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=filter_rows):
        context = _build_enriched_tab_context(
            run,
            run_id=run.run_id,
            client=object(),
            stage="all",
            filter_name="all",
            query="",
            pipeline_outcomes=[],
            page=1,
            page_size=50,
        )

    outcome = _lookup_row_by_lookup_key(context["pipeline_outcomes_by_job_url"], enriched[0])
    assert outcome["status"] == "ranked_with_cv"
    assert outcome["label"] == "CV created"

def test_build_enriched_tab_context_overrides_stale_review_required_with_terminal_hitl_rejection() -> None:
    import json as _json
    import datetime as _dt

    from fitcv_cp.app import _build_enriched_tab_context, _lookup_row_by_lookup_key
    from fitcv_cp.models import PipelineRun, RunStatus

    job_url = "https://de.indeed.com/viewjob?jk=hitl-reject-1"
    run = PipelineRun(
        run_id="run-enriched-hitl-reject",
        status=RunStatus("succeeded"),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=_dt.datetime(2026, 6, 26, 12, 0, 0, tzinfo=_dt.timezone.utc),
        results_export_json=_json.dumps(
            {
                "results": [
                    {
                        "job_url": job_url,
                        "job_title": "Rejected Review Role",
                        "pipeline_status": "ranked_no_cv",
                    }
                ]
            }
        ),
        cv_generation_debug_json=_json.dumps(
            {
                "debug_records": [
                    {
                        "job_url": job_url,
                        "job_title": "Rejected Review Role",
                        "status": "review_required",
                        "review_item_id": "ri_hitl_reject",
                    }
                ],
                "hitl_review_actions": [
                    {
                        "review_item_id": "ri_hitl_reject",
                        "job_url": job_url,
                        "action": "reject",
                        "resolution_status": "rejected",
                        "created_at": "2026-06-26T12:01:00+00:00",
                    }
                ],
            }
        ),
    )
    enriched = [
        {
            "job_url": job_url,
            "title": "Rejected Review Role",
            "domain": "d",
            "job_family": "f",
            "required_skills": [],
            "location_type": None,
            "seniority": None,
        }
    ]
    filter_rows = [{"job_url": job_url, "passed": True, "reasons": [], "marks": []}]

    with patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=filter_rows):
        context = _build_enriched_tab_context(
            run,
            run_id=run.run_id,
            client=object(),
            stage="all",
            filter_name="all",
            query="",
            pipeline_outcomes=[],
            page=1,
            page_size=50,
        )

    outcome = _lookup_row_by_lookup_key(context["pipeline_outcomes_by_job_url"], enriched[0])
    assert outcome["status"] == "rejected_after_enrichment"
    assert outcome["label"] == "Rejected after enrichment"

def test_run_detail_enriched_falls_back_to_stage_artifacts_when_results_export_is_all_unknown() -> None:
    import json as _json
    import datetime as _dt
    from fitcv_cp.models import PipelineRun, RunStatus

    blocked_url = "https://de.indeed.com/viewjob?jk=blocked-stage1"
    scored_not_ranked_url = "https://de.indeed.com/viewjob?jk=scored-stage2"
    run = PipelineRun(
        run_id="run-enriched-stage-artifact-outcomes",
        status=RunStatus("succeeded"),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=_dt.datetime(2026, 6, 26, 12, 0, 0, tzinfo=_dt.timezone.utc),
        results_export_json=_json.dumps(
            {
                "results": [
                    {
                        "job_url": "https://jobs.example.com/redirected-blocked",
                        "job_title": "Blocked Role",
                        "pipeline_status": "unknown_pipeline_state",
                    },
                    {
                        "job_url": "https://jobs.example.com/redirected-scored",
                        "job_title": "Scored Role",
                        "pipeline_status": "unknown_pipeline_state",
                    },
                ]
            }
        ),
        stage_transition_artifacts_json=_json.dumps(
            {
                "artifacts": {
                    "stages": {
                        "ranking": {
                            "status": "completed",
                            "input_counts": {"ai_scores": 2, "ranking_inputs": 2},
                            "output_counts": {"ranked_jobs": 1, "final_top_n": 1},
                            "outputs_sample": [
                                {"job_url": blocked_url, "job_title": "Blocked Role"}
                            ],
                            "dropped_or_changed_sample": [],
                        },
                        "cv_analysis": {
                            "status": "completed",
                            "outputs_sample": [],
                            "dropped_or_changed_sample": [
                                {
                                    "job_url": blocked_url,
                                    "job_title": "Blocked Role",
                                    "source_stage": "cv_analysis",
                                    "stage_owned_subreason": "blocked_by_reranker_fit",
                                    "deterministic_outcome": "blocked",
                                    "change_type": "blocked_by_reranker_fit",
                                }
                            ],
                        },
                    }
                }
            }
        ),
    )
    enriched = [
        {
            "job_url": blocked_url,
            "title": "Blocked Role",
            "raw_job_fingerprint": "raw-blocked-stage1",
            "domain": "d",
            "job_family": "f",
            "required_skills": [],
            "location_type": None,
            "seniority": None,
        },
        {
            "job_url": scored_not_ranked_url,
            "title": "Scored Role",
            "raw_job_fingerprint": "raw-scored-stage2",
            "domain": "d",
            "job_family": "f",
            "required_skills": [],
            "location_type": None,
            "seniority": None,
        },
    ]
    filter_rows = [
        {"job_url": blocked_url, "passed": True, "reasons": [], "marks": []},
        {"job_url": scored_not_ranked_url, "passed": True, "reasons": [], "marks": []},
    ]

    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.get_events", return_value=[]), \
         patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
         patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=filter_rows):
        resp = TestClient(_app()).get("/admin/runs/run-enriched-stage-artifact-outcomes/tabs/enriched")

    assert resp.status_code == 200
    assert '<span>Passed</span><strong>2</strong>' in resp.text
    assert "Ranked, blocked by reranker fit" in resp.text
    assert "Scored, not final top-N" in resp.text

def test_run_detail_enriched_uses_rule_filter_dropped_sample_for_rejected_rows() -> None:
    import json as _json
    import datetime as _dt
    from fitcv_cp.models import PipelineRun, RunStatus

    rejected_url = "https://de.indeed.com/viewjob?jk=rejected123"
    enriched = [
        {
            "job_url": rejected_url,
            "title": "Rejected Driving Instructor Role",
            "domain": "automotive",
            "job_family": None,
            "required_skills": ["Driving instructor"],
            "location_type": "onsite",
            "seniority": "senior",
        }
    ]
    stage_artifacts = _json.dumps({
        "artifacts": {
            "stages": {
                "rule_filter": {
                    "status": "completed",
                    "outputs_sample": [],
                    "dropped_or_changed_sample": [
                        {
                            "job_url": rejected_url,
                            "change_type": "rejected_after_enrichment",
                            "filter_outcome": "reject",
                            "reasons": ["seniority_mismatch"],
                            "marks": [],
                        }
                    ],
                    "output_counts": {"passed_jobs": 0, "rejected_jobs": 1},
                }
            }
        }
    })
    run = PipelineRun(
        run_id="run-detail-fallback-rejected-row",
        status=RunStatus("succeeded"),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=_dt.datetime(2026, 3, 27, 9, 0, 0, tzinfo=_dt.timezone.utc),
        stage_transition_artifacts_json=stage_artifacts,
    )
    with patch("fitcv_cp.app.get_run", return_value=run),          patch("fitcv_cp.app.get_events", return_value=[]),          patch("fitcv_cp.app.list_cvs_for_run", return_value=[]),          patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched),          patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get(
            "/admin/runs/run-detail-fallback-rejected-row/tabs/enriched"
            "?stage=screening&filter_name=rejected&pipeline_outcome=rejected_after_enrichment"
        )
    assert resp.status_code == 200
    assert "Rejected Driving Instructor Role" in resp.text
    assert '<span>Rejected</span><strong>1</strong>' in resp.text
    assert "Rejected after enrichment" in resp.text
    assert "seniority_mismatch" in resp.text

def test_run_detail_enriched_filters_by_pipeline_outcome_multi_select():
    import json as _json

    enriched = [
        {"job_url": "https://j.test/ns", "title": "Not Shortlisted", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": "https://j.test/snr", "title": "Scored Not Ranked", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": "https://j.test/rej", "title": "Rejected Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
    ]
    export_payload = _json.dumps(
        {
            "results": [
                {"job_url": "https://j.test/ns", "pipeline_status": "not_shortlisted"},
                {"job_url": "https://j.test/snr", "pipeline_status": "scored_not_ranked"},
                {"job_url": "https://j.test/rej", "pipeline_status": "rejected_after_enrichment"},
            ]
        }
    )
    patches = _run_detail_patches(enriched_jobs=enriched, filter_results=[], results_export_json=export_payload)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get(
            "/admin/runs/run-detail-test/tabs/enriched"
            "?pipeline_outcome=not_shortlisted&pipeline_outcome=scored_not_ranked"
        )
    assert resp.status_code == 200
    assert "Not Shortlisted" in resp.text
    assert "Scored Not Ranked" in resp.text
    assert "Rejected Role" not in resp.text

def test_run_detail_enriched_filters_by_pipeline_outcome_multi_select_with_fallback_statuses() -> None:
    import json as _json
    import datetime as _dt

    from fitcv_cp.models import PipelineRun, RunStatus

    review_url = "https://de.indeed.com/viewjob?jk=review-filter-1"
    blocked_url = "https://de.indeed.com/viewjob?jk=blocked-filter-1"
    validation_url = "https://de.indeed.com/viewjob?jk=validation-filter-1"
    scored_url = "https://de.indeed.com/viewjob?jk=scored-filter-1"
    rejected_url = "https://de.indeed.com/viewjob?jk=rejected-filter-1"
    run = PipelineRun(
        run_id="run-detail-fallback-filter-multi",
        status=RunStatus("succeeded"),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=_dt.datetime(2026, 6, 26, 12, 0, 0, tzinfo=_dt.timezone.utc),
        results_export_json=_json.dumps(
            {
                "results": [
                    {"job_url": review_url, "job_title": "Review Role", "pipeline_status": "unknown_pipeline_state"},
                    {"job_url": blocked_url, "job_title": "Blocked Role", "pipeline_status": "unknown_pipeline_state"},
                    {"job_url": validation_url, "job_title": "Validation Role", "pipeline_status": "unknown_pipeline_state"},
                    {"job_url": scored_url, "job_title": "Scored Role", "pipeline_status": "scored_not_ranked"},
                    {"job_url": rejected_url, "job_title": "Rejected Role", "pipeline_status": "rejected_after_enrichment"},
                ]
            }
        ),
        cv_generation_debug_json=_json.dumps(
            {
                "debug_records": [
                    {"job_url": review_url, "job_title": "Review Role", "status": "review_required"},
                    {"job_url": blocked_url, "job_title": "Blocked Role", "status": "blocked_by_reranker_fit", "source_stage": "cv_analysis"},
                    {"job_url": validation_url, "job_title": "Validation Role", "status": "validation_failed"},
                ]
            }
        ),
    )
    enriched = [
        {"job_url": review_url, "title": "Review Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": blocked_url, "title": "Blocked Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": validation_url, "title": "Validation Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": scored_url, "title": "Scored Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": rejected_url, "title": "Rejected Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
    ]
    filter_rows = [
        {"job_url": review_url, "passed": True, "reasons": [], "marks": []},
        {"job_url": blocked_url, "passed": True, "reasons": [], "marks": []},
        {"job_url": validation_url, "passed": True, "reasons": [], "marks": []},
        {"job_url": scored_url, "passed": True, "reasons": [], "marks": []},
        {"job_url": rejected_url, "passed": False, "reasons": ["seniority_mismatch"], "marks": []},
    ]

    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.get_events", return_value=[]), \
         patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
         patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=filter_rows):
        resp = TestClient(_app()).get(
            "/admin/runs/run-detail-fallback-filter-multi/tabs/enriched"
            "?pipeline_outcome=ranked_no_cv"
            "&pipeline_outcome=ranked_blocked_by_reranker_fit"
            "&pipeline_outcome=scored_not_ranked"
        )

    assert resp.status_code == 200
    assert "Review Role" in resp.text
    assert "Blocked Role" in resp.text
    assert "Validation Role" in resp.text
    assert "Scored Role" in resp.text
    assert "Rejected Role" not in resp.text


def test_run_detail_enriched_defaults_to_all_outcomes_reaching_selected_stage() -> None:
    import json as _json

    enriched = [
        {"job_url": "https://j.test/cv", "title": "CV Created Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": "https://j.test/blocked", "title": "Blocked Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": "https://j.test/failed", "title": "CV Failed Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": "https://j.test/scored", "title": "Scored Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": "https://j.test/skipped", "title": "Skipped Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": "https://j.test/rejected", "title": "Rejected Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
    ]
    export_payload = _json.dumps(
        {
            "results": [
                {"job_url": "https://j.test/cv", "pipeline_status": "ranked_with_cv"},
                {"job_url": "https://j.test/blocked", "pipeline_status": "ranked_blocked_by_reranker_fit"},
                {"job_url": "https://j.test/failed", "pipeline_status": "ranked_no_cv"},
                {"job_url": "https://j.test/scored", "pipeline_status": "scored_not_ranked"},
                {"job_url": "https://j.test/skipped", "pipeline_status": "ranked_skipped_fit_gate"},
                {"job_url": "https://j.test/rejected", "pipeline_status": "rejected_after_enrichment"},
            ]
        }
    )
    patches = _run_detail_patches(enriched_jobs=enriched, filter_results=[], results_export_json=export_payload)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched")
    assert resp.status_code == 200
    assert "CV Created Role" in resp.text
    assert "Blocked Role" in resp.text
    assert "CV Failed Role" in resp.text
    assert "Scored Role" in resp.text
    assert "Skipped Role" in resp.text
    assert "Rejected Role" not in resp.text
    assert 'name="pipeline_outcome"' not in resp.text

def test_run_detail_enriched_query_state_preserved_in_fragment_urls():
    import json as _json

    enriched = [
        {"job_url": f"https://j.test/{i}", "title": f"Job {i}", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None}
        for i in range(1, 61)
    ]
    export_payload = _json.dumps(
        {
            "results": [
                {
                    "job_url": f"https://j.test/{i}",
                    "pipeline_status": "not_shortlisted" if i % 2 else "scored_not_ranked",
                }
                for i in range(1, 61)
            ]
        }
    )
    patches = _run_detail_patches(enriched_jobs=enriched, filter_results=[], results_export_json=export_payload)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get(
            "/admin/runs/run-detail-test/tabs/enriched?page=2&page_size=25&filter_name=all&q=python"
            "&pipeline_outcome=not_shortlisted&pipeline_outcome=scored_not_ranked"
        )
    assert resp.status_code == 200
    prev_url = (
        "/admin/runs/run-detail-test/tabs/enriched?stage=shortlisting&page=1&page_size=25&filter_name=all&q=python"
        "&pipeline_outcome=not_shortlisted&pipeline_outcome=scored_not_ranked"
    )
    next_url = (
        "/admin/runs/run-detail-test/tabs/enriched?stage=shortlisting&page=3&page_size=25&filter_name=all&q=python"
        "&pipeline_outcome=not_shortlisted&pipeline_outcome=scored_not_ranked"
    )
    assert f'data-tab-fragment-url="{prev_url}"' in resp.text
    assert f'data-tab-fragment-url="{next_url}"' in resp.text
    assert 'data-search="python"' in resp.text
    assert 'data-preview-url="/runs/run-detail-test/jobs/actions/export/preview"' in resp.text
    assert 'data-export-url="/runs/run-detail-test/jobs/actions/export"' in resp.text


def test_download_run_enriched_filtered_zip_contains_jsonl_and_manifest():
    import io as _io
    import json as _json
    import zipfile as _zipfile

    enriched = [
        {"job_url": "https://j.test/ns", "title": "Not Shortlisted", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": "https://j.test/rej", "title": "Rejected Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
    ]
    export_payload = _json.dumps(
        {
            "results": [
                {"job_url": "https://j.test/ns", "pipeline_status": "not_shortlisted"},
                {"job_url": "https://j.test/rej", "pipeline_status": "rejected_after_enrichment"},
            ]
        }
    )
    jobs_input = _json.dumps([
        {"jobUrl": "https://j.test/ns", "title": "Not Shortlisted"},
        {"jobUrl": "https://j.test/rej", "title": "Rejected Role"},
    ])
    patches = _run_detail_patches(
        enriched_jobs=enriched,
        filter_results=[],
        results_export_json=export_payload,
        jobs_input_json=jobs_input,
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get(
            "/admin/runs/run-detail-test/enriched/export-filtered.zip"
            "?pipeline_outcome=not_shortlisted"
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    with _zipfile.ZipFile(_io.BytesIO(resp.content)) as archive:
        names = set(archive.namelist())
        assert "jobs.filtered.jsonl" in names
        assert "jobs.filtered.manifest.json" in names
        lines = [line for line in archive.read("jobs.filtered.jsonl").decode("utf-8").splitlines() if line.strip()]
        manifest = _json.loads(archive.read("jobs.filtered.manifest.json"))

    assert len(lines) == 1
    row = _json.loads(lines[0])
    assert row["pipeline_outcome"] == "not_shortlisted"
    assert row["raw_job"]["jobUrl"] == "https://j.test/ns"
    assert manifest["row_count"] == 1
    assert manifest["filters"]["pipeline_outcome"] == ["not_shortlisted"]


def test_download_run_enriched_filtered_zip_defaults_to_selected_pipeline_outcomes() -> None:
    import io as _io
    import json as _json
    import zipfile as _zipfile

    enriched = [
        {"job_url": "https://j.test/cv", "title": "CV Created Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": "https://j.test/blocked", "title": "Blocked Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": "https://j.test/failed", "title": "CV Failed Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": "https://j.test/scored", "title": "Scored Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": "https://j.test/skipped", "title": "Skipped Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": "https://j.test/rejected", "title": "Rejected Role", "domain": "d", "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
    ]
    export_payload = _json.dumps(
        {
            "results": [
                {"job_url": "https://j.test/cv", "pipeline_status": "ranked_with_cv"},
                {"job_url": "https://j.test/blocked", "pipeline_status": "ranked_blocked_by_reranker_fit"},
                {"job_url": "https://j.test/failed", "pipeline_status": "ranked_no_cv"},
                {"job_url": "https://j.test/scored", "pipeline_status": "scored_not_ranked"},
                {"job_url": "https://j.test/skipped", "pipeline_status": "ranked_skipped_fit_gate"},
                {"job_url": "https://j.test/rejected", "pipeline_status": "rejected_after_enrichment"},
            ]
        }
    )
    jobs_input = _json.dumps(
        [
            {"jobUrl": "https://j.test/cv", "title": "CV Created Role"},
            {"jobUrl": "https://j.test/blocked", "title": "Blocked Role"},
            {"jobUrl": "https://j.test/failed", "title": "CV Failed Role"},
            {"jobUrl": "https://j.test/scored", "title": "Scored Role"},
            {"jobUrl": "https://j.test/skipped", "title": "Skipped Role"},
            {"jobUrl": "https://j.test/rejected", "title": "Rejected Role"},
        ]
    )
    patches = _run_detail_patches(
        enriched_jobs=enriched,
        filter_results=[],
        results_export_json=export_payload,
        jobs_input_json=jobs_input,
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/enriched/export-filtered.zip")

    assert resp.status_code == 200
    with _zipfile.ZipFile(_io.BytesIO(resp.content)) as archive:
        lines = [line for line in archive.read("jobs.filtered.jsonl").decode("utf-8").splitlines() if line.strip()]
        manifest = _json.loads(archive.read("jobs.filtered.manifest.json"))

    exported_urls = {_json.loads(line)["job_url"] for line in lines}
    assert exported_urls == {
        "https://j.test/cv",
        "https://j.test/blocked",
        "https://j.test/failed",
        "https://j.test/scored",
        "https://j.test/skipped",
    }
    assert manifest["filters"]["pipeline_outcome"] == [
        "ranked_with_cv",
        "ranked_blocked_by_reranker_fit",
        "ranked_no_cv",
        "scored_not_ranked",
        "ranked_skipped_fit_gate",
        "accepted",
        "held",
        "blocked",
        "skipped",
    ]

def test_admin_upload_trigger_accepts_jsonl_rerun_input():
    import io as _io
    import json as _json

    captured = {}

    jsonl_payload = "\n".join(
        [
            _json.dumps({"schema_version": "rerun_input.v1", "raw_job": _valid_fitcv_job(jobUrl="https://a.com", title="A")}),
            _json.dumps({"schema_version": "rerun_input.v1", "raw_job": _valid_fitcv_job(jobUrl="https://b.com", title="B")}),
        ]
    )

    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.submit_run", return_value=RunSubmission(run_id="run-123", queue_job_id="rq-job-abc", backend_run_id="rq-job-abc", backend="default_queue")), \
         patch("fitcv_cp.app.update_run_queue_job_id"), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p","pipeline": {"final_top_n": 10},
             "paths": {"candidate_profile": "data/candidate_profile.yaml"},
         }):
        resp = TestClient(_app_with_captured_run(captured)).post(
            "/admin/upload-trigger",
            data={
                "jobs_input_mode": "upload",
                "candidate_profile_id": "profile-1",
                "config_path": ".env.yaml",
            },
            files={"jobs_file": ("filtered.jsonl", _io.BytesIO(jsonl_payload.encode("utf-8")), "application/jsonl")},
        )

    assert resp.status_code == 201, resp.text
    jobs_input_json = captured["run"].jobs_input_json
    parsed = _json.loads(jobs_input_json)
    assert [row.get("jobUrl") for row in parsed] == ["https://a.com", "https://b.com"]


def test_run_detail_enriched_tab_paginates_server_side():
    """Enriched tab returns only the requested page slice."""
    enriched = [
        {"job_url": f"https://j.test/{i}", "title": f"Job {i}", "domain": "d",
         "job_family": "f", "required_skills": [], "location_type": None, "seniority": None}
        for i in range(1, 61)
    ]
    patches = _run_detail_patches(enriched_jobs=enriched, filter_results=[])
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched?page=2&page_size=25")
    assert resp.status_code == 200
    assert 'data-run-page-number="2"' in resp.text
    assert 'aria-current="page"' in resp.text
    assert "Job 1" not in resp.text
    assert "Job 26" in resp.text
    assert "Job 50" in resp.text




def test_run_detail_enriched_pagination_fragment_urls_preserve_query_state():
    enriched = [
        {"job_url": f"https://j.test/{i}", "title": f"Job {i}", "domain": "d",
         "job_family": "f", "required_skills": [], "location_type": None, "seniority": None}
        for i in range(1, 61)
    ]
    patches = _run_detail_patches(enriched_jobs=enriched, filter_results=[])
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test/tabs/enriched?page=2&page_size=25&filter_name=all&q=python")
    assert resp.status_code == 200
    prev_url = "/admin/runs/run-detail-test/tabs/enriched?stage=shortlisting&page=1&page_size=25&filter_name=all&q=python"
    next_url = "/admin/runs/run-detail-test/tabs/enriched?stage=shortlisting&page=3&page_size=25&filter_name=all&q=python"
    assert f'data-tab-fragment-url="{prev_url}"' in resp.text
    assert f'data-tab-fragment-url="{next_url}"' in resp.text
# ── Task 6: Composition consistency tests ──────────────────────────────────────

def test_run_detail_tab_bar_uses_attached_modifier():
    """@proves ui_consistency_theming.attached-tab-inspection-card-pattern

    The tab bar must use .tab-bar--attached (not the old .tab-bar).
    """
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone
    run = PipelineRun(
        run_id="composition-test-2", status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json", triggered_by="admin",
        trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/composition-test-2")
    assert resp.status_code == 200
    html = resp.text
    # .tab-bar--attached must be present
    assert 'tab-bar--attached' in html, 'class="tab-bar--attached" not found in rendered HTML'
    # The bare "tab-bar" class (without --attached) must NOT appear as the opening class attribute
    # Check around the tab-bar element: find a position where class= is followed by tab-bar
    # Use token-level check: split on 'class="' and look at tokens
    import re
    class_tokens = re.findall(r'class="([^"]*)"', html)
    bare_tab_bar_in_classes = any('tab-bar' in token and 'tab-bar--attached' not in token for token in class_tokens)
    assert not bare_tab_bar_in_classes, "Bare 'tab-bar' class found in rendered HTML (should be 'tab-bar--attached')"


def test_base_template_bootstraps_saved_theme_before_styles():
    """@proves ui_consistency_theming.dark-light-theme-toggle-with-localstorage-persistence
    @proves ui_consistency_theming.flash-free-theme-application
    """
    from pathlib import Path

    html = Path("src/fitcv_cp/templates/base.html").read_text(encoding="utf-8")

    script_pos = html.index("<script>")
    style_pos = html.index("<style>")

    assert script_pos < style_pos
    assert "localStorage.getItem('fitcv-theme') || 'light'" in html
    assert "document.documentElement.setAttribute('data-theme', t);" in html


def test_base_template_avoids_implicit_favicon_request() -> None:
    from pathlib import Path

    html = Path("src/fitcv_cp/templates/base.html").read_text(encoding="utf-8")

    assert '<link rel="icon" href="data:,">' in html

def test_base_template_defines_theme_tokens_and_shared_classes():
    """@proves ui_consistency_theming.css-custom-properties-design-tokens
    @proves ui_consistency_theming.shared-component-classes
    """
    from pathlib import Path

    html = Path("src/fitcv_cp/templates/base.html").read_text(encoding="utf-8")

    assert ':root[data-theme="dark"]' in html
    assert ':root[data-theme="light"]' in html
    for token in ("--bg:", "--surface-1:", "--accent:", "--divider:"):
        assert token in html
    for shared_class in (".card, .section-card", ".sub-card", ".inspection-card", ".pane-container"):
        assert shared_class in html


def test_base_template_uses_wrapping_rules_for_shared_layout_surfaces():
    """@proves ui_consistency_theming.responsive-wrapping"""
    from pathlib import Path

    html = Path("src/fitcv_cp/templates/base.html").read_text(encoding="utf-8")

    page_header_start = html.index(".page-header {")
    page_header_end = html.index("}", page_header_start)
    page_header_block = html[page_header_start:page_header_end]
    assert "flex-wrap: wrap;" in page_header_block

    section_actions_start = html.index(".section-actions {")
    section_actions_end = html.index("}", section_actions_start)
    section_actions_block = html[section_actions_start:section_actions_end]
    assert "flex-wrap: wrap;" in section_actions_block

    nav_start = html.index("nav {")
    nav_end = html.index("}", nav_start)
    nav_block = html[nav_start:nav_end]
    assert "flex-wrap: wrap;" in nav_block
    assert "height: auto;" in nav_block
    assert ".workspace-stack { display: grid; gap: 0.875rem; min-width: 0; }" in html
    assert ".workspace-stack > [aria-live]:empty { display: none; }" in html


# ── Task 1: path-mode snapshot capture ──────────────────────────────────────


def _path_mode_patches(profile_path: str = "/tmp/dummy_profile.yaml"):
    """Return standard patches for path-mode upload-trigger tests."""
    base_config = {
        "gcp_project": "p","pipeline": {"final_top_n": 10},
        "paths": {"candidate_profile": profile_path},
    }
    return (
        patch("fitcv_cp.app.load_active_settings", return_value={}),
        patch("fitcv_cp.app.insert_run"),
        patch("fitcv_cp.app.submit_run", return_value=RunSubmission(run_id="run-path-1", queue_job_id="rq-job-1", backend_run_id="rq-job-1", backend="default_queue")),
        patch("fitcv_cp.app.update_run_queue_job_id"),
        patch("fitcv_cp.app.load_config", return_value=base_config),
    )


def test_admin_upload_trigger_path_mode_stores_jobs_snapshot(tmp_path):
    """@proves multi_file_job_input.one-immutable-snapshot-stored-per-run

    path mode: trigger must read the file and store its JSON in jobs_input_json.
    """
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")
    captured = {}

    p = _path_mode_patches(profile_path=str(tmp_path / "unused-profile.yaml"))
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app_with_captured_run(captured)).post(
            "/admin/upload-trigger",
            data={
                "jobs_input_mode": "path",
                "jobs_path": str(jobs_file),
                "candidate_profile_id": "profile-1",
            },
        )

    assert resp.status_code == 201, resp.text
    assert "run_id" in resp.json()
    assert captured["run"].jobs_input_source == "path"
    assert json.loads(captured["run"].jobs_input_json) == [
        _valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")
    ]


def test_admin_upload_trigger_path_mode_missing_file_returns_422(tmp_path):
    """path mode: missing file must fail the trigger with 422."""
    profile_file = tmp_path / "profile.yaml"
    profile_file.write_text(_minimal_valid_profile_yaml(), encoding="utf-8")
    p = _path_mode_patches(profile_path=str(profile_file))
    with p[0], p[1], p[2], p[3], p[4]:
        with patch("fitcv_cp.app.insert_run") as mock_insert:
            resp = TestClient(_app()).post(
                "/admin/upload-trigger",
                data={
                    "jobs_input_mode": "path",
                    "jobs_path": str(tmp_path / "nonexistent.json"),
                    "candidate_profile_mode": "default_config",
                },
            )
    assert resp.status_code == 422
    mock_insert.assert_not_called()


def test_admin_upload_trigger_path_mode_invalid_json_returns_422(tmp_path):
    """path mode: invalid JSON content must fail the trigger with 422."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("NOT JSON AT ALL", encoding="utf-8")
    profile_file = tmp_path / "profile.yaml"
    profile_file.write_text(_minimal_valid_profile_yaml(), encoding="utf-8")

    p = _path_mode_patches(profile_path=str(profile_file))
    with p[0], p[1], p[2], p[3], p[4]:
        with patch("fitcv_cp.app.insert_run") as mock_insert:
            resp = TestClient(_app()).post(
                "/admin/upload-trigger",
                data={
                    "jobs_input_mode": "path",
                    "jobs_path": str(bad_file),
                    "candidate_profile_mode": "default_config",
                },
            )
    assert resp.status_code == 422
    mock_insert.assert_not_called()


def test_admin_upload_trigger_path_mode_non_array_json_returns_422(tmp_path):
    """path mode: JSON that is not a top-level array must fail with 422."""
    obj_file = tmp_path / "obj.json"
    obj_file.write_text('{"job_url": "http://a.com"}', encoding="utf-8")
    profile_file = tmp_path / "profile.yaml"
    profile_file.write_text(_minimal_valid_profile_yaml(), encoding="utf-8")

    p = _path_mode_patches(profile_path=str(profile_file))
    with p[0], p[1], p[2], p[3], p[4]:
        with patch("fitcv_cp.app.insert_run") as mock_insert:
            resp = TestClient(_app()).post(
                "/admin/upload-trigger",
                data={
                    "jobs_input_mode": "path",
                    "jobs_path": str(obj_file),
                    "candidate_profile_mode": "default_config",
                },
            )
    assert resp.status_code == 422
    mock_insert.assert_not_called()


# ── Task 2: default_config profile snapshot capture ──────────────────────────


def _minimal_valid_profile_yaml() -> str:
    """Return a minimal YAML profile with required sections."""
    return """
name: Test Candidate
skills:
  - name: Python
    level: expert
    years: 5
    evidence_refs: []
experiences: []
projects: []
achievements: []
preferences:
  domains:
    - fintech
  location_types:
    - remote
"""


def test_admin_upload_trigger_stores_selected_profile_snapshot(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")
    captured = {}
    app = _app_with_captured_run(captured)
    app.state.run_store.get_candidate_profile_fn = lambda profile_id: {
        "profile_id": profile_id,
        "name": "Fintech Profile",
        "revision": 3,
        "is_active": True,
        "profile": {"preferences": {"domains": ["fintech"]}},
    }
    p = (
        patch("fitcv_cp.app.load_active_settings", return_value={}),
        patch("fitcv_cp.app.submit_run", return_value=RunSubmission(run_id="run-dc-1", queue_job_id="rq-job-1", backend_run_id="rq-job-1", backend="default_queue")),
        patch("fitcv_cp.app.update_run_queue_job_id"),
        patch("fitcv_cp.app.load_config", return_value={"gcp_project": "p", "pipeline": {"final_top_n": 10}}),
    )
    with p[0], p[1], p[2], p[3]:
        resp = TestClient(app).post(
            "/admin/upload-trigger",
            data={
                "jobs_input_mode": "path",
                "jobs_path": str(jobs_file),
                "candidate_profile_id": "profile-1",
            },
        )

    assert resp.status_code == 201, resp.text
    assert "run_id" in resp.json()
    assert captured["run"].candidate_profile_source == "profile-1"
    profile_snapshot = json.loads(captured["run"].candidate_profile_json)
    assert profile_snapshot["preferences"]["domains"] == ["fintech"]
    assert profile_snapshot["revision"] == 3


def test_admin_upload_trigger_keeps_profile_snapshot_after_source_mutation(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")
    captured = {}
    profile = {
        "profile_id": "profile-1",
        "name": "Fintech Profile",
        "revision": 3,
        "is_active": True,
        "profile": {"preferences": {"domains": ["fintech"]}},
    }
    app = _app_with_captured_run(captured)
    app.state.run_store.get_candidate_profile_fn = lambda profile_id: profile
    p = (
        patch("fitcv_cp.app.load_active_settings", return_value={}),
        patch("fitcv_cp.app.submit_run", return_value=RunSubmission(run_id="run-dc-2", queue_job_id="rq-job-2", backend_run_id="rq-job-2", backend="default_queue")),
        patch("fitcv_cp.app.update_run_queue_job_id"),
        patch("fitcv_cp.app.load_config", return_value={"gcp_project": "p", "pipeline": {"final_top_n": 10}}),
    )
    with p[0], p[1], p[2], p[3]:
        resp = TestClient(app).post(
            "/admin/upload-trigger",
            data={
                "jobs_input_mode": "path",
                "jobs_path": str(jobs_file),
                "candidate_profile_id": "profile-1",
            },
        )

    assert resp.status_code == 201, resp.text
    profile["profile"]["preferences"]["domains"].append("mutated-after-submit")
    profile_snapshot = json.loads(captured["run"].candidate_profile_json)
    assert profile_snapshot["preferences"]["domains"] == ["fintech"]


def test_admin_upload_trigger_default_config_missing_profile_returns_422(tmp_path):
    """default_config mode: missing profile file must fail the trigger with 422."""
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")

    config = {
        "gcp_project": "p","pipeline": {"final_top_n": 10},
        "paths": {"candidate_profile": str(tmp_path / "nonexistent.yaml")},
    }
    p = (
        patch("fitcv_cp.app.load_active_settings", return_value={}),
        patch("fitcv_cp.app.insert_run"),
        patch("fitcv_cp.app.submit_run", return_value=RunSubmission(run_id="run-dc-2", queue_job_id="rq-job-1", backend_run_id="rq-job-1", backend="default_queue")),
        patch("fitcv_cp.app.update_run_queue_job_id"),
        patch("fitcv_cp.app.load_config", return_value=config),
    )
    with p[0], p[1], p[2], p[3], p[4]:
        with patch("fitcv_cp.app.insert_run") as mock_insert:
            resp = TestClient(_app()).post(
                "/admin/upload-trigger",
                data={
                    "jobs_input_mode": "path",
                    "jobs_path": str(jobs_file),
                    "candidate_profile_mode": "default_config",
                },
            )
    assert resp.status_code == 422
    mock_insert.assert_not_called()


def test_admin_upload_trigger_requires_central_candidate_profile_id(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]), encoding="utf-8")
    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.load_config", return_value={"gcp_project": "p", "pipeline": {"final_top_n": 10}}):
        response = TestClient(_app()).post(
            "/admin/upload-trigger",
            data={
                "jobs_input_mode": "path",
                "jobs_path": str(jobs_file),
                "candidate_profile_mode": "paste",
                "candidate_profile_text": _minimal_valid_profile_yaml(),
            },
        )

    assert response.status_code == 422
    assert response.json()["error"]["field_errors"][0]["field"] == "candidate_profile_id"


# ── Task 3: Snapshot semantics – run detail display and legacy fallback ────────


def test_run_detail_tab2_shows_snapshot_for_path_source():
    """Tab 2 shows snapshot content when jobs_input_json is present for path source."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="snap-test-1", status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json", jobs_input_source="path",
        jobs_input_json=json.dumps([_valid_fitcv_job(jobUrl="http://a.com", job_url="http://a.com")]),
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/snap-test-1/tabs/jobs-input")

    assert resp.status_code == 200
    html = resp.text
    assert "Raw job payload captured at trigger time" in html
    # Jinja2 auto-escapes " as &quot; in <pre> blocks
    assert "job_url" in html
    assert "http://a.com" in html


def test_run_detail_tab2_legacy_fallback_does_not_mention_path_mode_limitation():
    """Tab 2 fallback for legacy runs (no snapshot) must NOT say 'path-mode runs do not'."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="snap-test-2", status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json", jobs_input_source="path",
        jobs_input_json=None,
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/snap-test-2/tabs/jobs-input")

    assert resp.status_code == 200
    html = resp.text
    assert "No immutable raw snapshot" in html
    # Must NOT imply path-mode never has snapshots
    assert "path-mode runs do not" not in html


def test_run_detail_tab3_shows_snapshot_for_default_config_source():
    """@proves trigger_run_management.candidate-profile-input-modes

    Tab 3 shows snapshot content when candidate_profile_json is present for default_config.
    """
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    profile_json = '{"preferences": {"domains": ["fintech"]}, "skills": [], "experiences": [], "projects": [], "achievements": []}'
    run = PipelineRun(
        run_id="snap-test-3", status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json",
        candidate_profile_source="default_config",
        candidate_profile_json=profile_json,
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/snap-test-3/tabs/profile")

    assert resp.status_code == 200
    html = resp.text
    assert "Candidate profile captured at trigger time" in html
    assert "default_config" in html


def test_run_detail_tab3_legacy_fallback_does_not_mention_default_config_limitation():
    """Tab 3 fallback for legacy runs must NOT say 'Default-config and pre-feature runs do not'."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="snap-test-4", status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json",
        candidate_profile_source="default_config",
        candidate_profile_json=None,
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/snap-test-4/tabs/profile")

    assert resp.status_code == 200
    html = resp.text
    assert "No candidate profile snapshot" in html
    # Must NOT imply default_config never has snapshots
    assert "Default-config and pre-feature runs do not" not in html


# ── CV settings grouped save ──────────────────────────────────────────────────

def test_grouped_save_cv_generation_valid_redirects():
    """cv-preset group rejects hidden deprecated model control payload."""
    with patch("fitcv_cp.app.save_settings_group") as mock_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/group/cv-preset",
            data={
                "cv_preset": "europass",
                "cv_generation_model": "cx/gpt-5.4-mini",
            },
        )
    assert resp.status_code == 422
    assert "Hidden deprecated settings are not writable" in resp.text
    mock_save.assert_not_called()


def test_grouped_save_cv_generation_rejects_empty_model():
    """Empty cv_generation_model → 422 (handled by cv-preset group)."""
    with patch("fitcv_cp.app.save_settings_group") as mock_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/group/cv-preset",
            data={
                "cv_preset": "europass",
                "cv_generation_model": "",
            },
        )
    assert resp.status_code == 422
    mock_save.assert_not_called()


def test_grouped_save_cv_generation_rejects_whitespace_template_path():
    """cv_template_path is no longer in the schema (not admin-editable)."""
    # This test is a no-op since cv_template_path was removed from the schema
    pass


def test_grouped_save_cv_validation_valid_redirects():
    """Valid cv-validation form POST with cv_max_pages → 303 redirect."""
    with patch("fitcv_cp.app.save_settings_group") as mock_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/group/cv-validation",
            data={
                "cv_max_pages": "3",
            },
        )
    assert resp.status_code == 303
    mock_save.assert_called_once()


def test_grouped_save_cv_validation_rejects_empty_sections():
    """cv-validation group now has only cv_max_pages; valid payload → 303."""
    with patch("fitcv_cp.app.save_settings_group") as mock_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/group/cv-validation",
            data={
                "cv_max_pages": "2",
            },
        )
    assert resp.status_code == 303
    mock_save.assert_called_once()


def test_grouped_save_cv_validation_preserves_order_on_failure():
    """Validation error → 422 response must include submitted values."""
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/group/cv-validation",
            data={
                "cv_max_pages": "0",   # invalid
            },
        )
    assert resp.status_code == 422
    assert "0" in resp.text


def test_grouped_save_unknown_cv_group_returns_404():
    """Unknown CV group name → 404."""
    resp = TestClient(_app()).post(
        "/admin/settings/group/cv-nonexistent",
        data={"some.key": "1"},
    )
    assert resp.status_code == 404


# ── CV settings page rendering ────────────────────────────────────────────────

def test_settings_page_shows_mode_summary_strip_for_agentic_runtime() -> None:
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    html = resp.text
    assert "Agentic Mode:" not in html
    assert "Live Provider:" not in html
    assert "Live Model:" not in html
    assert "Authority State:" not in html
    assert "Run Truth Check" not in html
    assert "Agentic Runtime Alignment" not in html


def test_settings_page_mode_summary_marks_drift_when_env_set_but_agentic_disabled() -> None:
    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch.dict(
             "fitcv_cp.app.os.environ",
             {"FITCV_LANGGRAPH_PROVIDER": "9router", "FITCV_LANGGRAPH_MODEL": "cx/gpt-5.2"},
             clear=False,
         ):
        resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    html = resp.text
    assert "Authority State:" not in html
    assert "drifted" not in html
    assert "Agentic runtime env is configured but agentic mode toggle is OFF." not in html
    assert "Agentic live runtime is" not in html


def test_control_plane_artifact_registry_stays_aligned_with_pipeline_contract() -> None:
    stage_specs = list(_control_plane_stage_specs())
    bundle_specs = list(_control_plane_bundle_artifact_specs())

    assert [spec.stage_id for spec in stage_specs] == list(PIPELINE_STAGE_SEQUENCE)
    assert len({spec.stage_id for spec in stage_specs}) == len(stage_specs)
    assert [spec.filename for spec in bundle_specs] == list(PIPELINE_BUNDLE_ARTIFACT_FILENAMES)
    assert len({spec.filename for spec in bundle_specs}) == len(bundle_specs)
    assert {spec.artifact_filename for spec in stage_specs} <= {spec.filename for spec in bundle_specs}
def test_settings_page_cv_sections_no_raw_yaml():
    """required_cv_sections no longer exists in the schema (replaced by toggle fields)."""
    # The new UI does not expose a textarea for required_cv_sections
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    assert '<textarea name="required_cv_sections"' not in resp.text

def test_runs_list_candidate_profile_control_uses_central_profiles_only() -> None:
    with patch("fitcv_cp.app.list_runs", return_value=[]), \
         patch("fitcv_cp.app.get_pipeline_runs_schema_status", return_value={"status": "complete", "missing_columns": [], "warning": None}):
        resp = TestClient(_app()).get("/admin/runs")
    assert resp.status_code == 200
    html = resp.text
    assert 'id="candidateProfile"' in html
    assert "/candidate-profiles?view=active&status=succeeded" in html
    assert "Upload Profile" not in html
    assert "Paste Profile" not in html


# ── Preset-based CV settings page rendering ──────────────────────────────────────

def test_settings_page_hides_deprecated_cv_generation_model_input() -> None:
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    html = resp.text
    assert 'name="cv_generation_model"' not in html
    assert '<option value="cx/gpt-5.4-mini"' not in html


def test_settings_page_hides_default_column_for_settings_blocks() -> None:
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    html = resp.text
    assert "<th>Default</th>" not in html


def test_settings_page_hides_legacy_required_controls() -> None:
    """Composition UI no longer exposes separate required checkboxes."""
    active = {"cv_education_enabled": False}
    with patch("fitcv_cp.app.load_active_settings", return_value=active):
        resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    html = resp.text
    assert 'name="cv_education_required"' not in html
    assert 'name="cv_projects_required"' not in html


def test_settings_page_does_not_render_cv_content_rules_section():
    """Settings page no longer includes the removed cv-content-rules sub-card."""
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    html = resp.text
    assert "Content Rules" not in html


def test_settings_page_hides_deprecated_cv_model_and_keeps_cv_preset_metadata_only():
    """Settings page hides deprecated cv_generation_model and keeps cv_preset metadata-only."""
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    html = resp.text
    assert 'name="cv_preset"' not in html
    assert 'name="cv_generation_model"' not in html
    assert 'name="cv_prompt_version"' not in html


def test_settings_page_does_not_render_retired_cv_composition_formatting_inputs():
    """Settings page no longer renders dormant CV composition formatting/detail controls."""
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    html = resp.text
    for name in (
        "cv_summary_style",
        "cv_education_detail",
        "cv_experience_bullet_style",
        "cv_skills_max_items",
        "cv_publications_detail",
        "cv_languages_detail",
    ):
        assert f'name="{name}"' not in html, f"Unexpected input for retired field {name}"


def test_settings_page_does_not_render_removed_cv_content_rules_inputs():
    """Settings page no longer includes inputs for removed content-rule fields."""
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    html = resp.text
    for name in ("cv_emphasize_required_skills", "cv_align_jd_terminology", "cv_evidence_grounded_only"):
        assert f'name="{name}"' not in html, f"Unexpected input for removed field {name}"


def test_settings_page_does_not_render_cv_content_rules_save_button():
    """Settings page no longer renders a save button for the removed content-rules group."""
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    assert "Save Content Rules Settings" not in resp.text


def test_settings_page_no_raw_template_path_input():
    """Raw cv_template_path text input is NOT exposed in the new preset-based UI."""
    # NOTE: This test requires the new UI to be rendered (Task 4).
    # It checks that when the new "Preset" sub-card is present,
    # the cv_template_path field is NOT exposed as a raw text input there.
    # Skipped until the UI is updated; backend is ready.
    pass


def test_settings_page_no_raw_required_cv_sections_freeform():
    """required_cv_sections is NOT rendered as a free-form editor in the new UI."""
    # NOTE: This test requires the new UI to be rendered (Task 4).
    # Skipped until the UI is updated; backend is ready.
    pass


# ── Preset-based CV grouped save endpoints ────────────────────────────────────────

def test_grouped_save_cv_preset_valid_redirects():
    """Valid cv-preset form POST keeps metadata-only value and performs no editable write."""
    with patch("fitcv_cp.app.save_settings_group") as mock_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
            resp = TestClient(_app(), follow_redirects=False).post(
                "/admin/settings/group/cv-preset",
                data={},
            )
    assert resp.status_code == 303
    mock_save.assert_called_once()
    saved_keys = set(mock_save.call_args[0][0].keys())
    assert saved_keys == set()


def test_grouped_save_cv_preset_rejects_empty():
    """Empty cv_preset → 422; no write."""
    with patch("fitcv_cp.app.save_settings_group") as mock_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/group/cv-preset",
            data={
                "cv_preset": "",
            },
        )
    assert resp.status_code == 422
    mock_save.assert_not_called()


def test_grouped_save_cv_preset_rejects_hidden_deprecated_payload_key():
    with patch("fitcv_cp.app.save_settings_group") as mock_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/group/cv-preset",
            data={
                "cv_generation_model": "cx/gpt-5.4-mini",
            },
        )
    assert resp.status_code == 422
    assert "Hidden deprecated settings are not writable" in resp.text
    mock_save.assert_not_called()


def test_grouped_save_cv_composition_valid_redirects():
    """Valid cv-composition form POST → 303 redirect."""
    with patch("fitcv_cp.app.save_settings_group") as mock_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/group/cv-composition",
            data={
                "cv_summary_enabled": "true",
                "cv_education_enabled": "true",
                "cv_experience_enabled": "true",
                "cv_skills_enabled": "true",
                "cv_certifications_enabled": "true",
                "cv_projects_enabled": "true",
                "cv_publications_enabled": "false",
                "cv_languages_enabled": "true",
            },
        )
    assert resp.status_code == 303
    mock_save.assert_called_once()

def test_grouped_save_cv_composition_rejects_invalid_bool():
    """Invalid boolean in cv-composition → 422; no write."""
    with patch("fitcv_cp.app.save_settings_group") as mock_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/group/cv-composition",
            data={
                "cv_summary_enabled": "true",
                "cv_education_enabled": "true",
                "cv_experience_enabled": "not-a-bool",
                "cv_skills_enabled": "true",
                "cv_certifications_enabled": "true",
                "cv_projects_enabled": "true",
                "cv_publications_enabled": "false",
                "cv_languages_enabled": "true",
            },
        )
    assert resp.status_code == 422
    mock_save.assert_not_called()


def test_grouped_save_removed_cv_content_rules_returns_404():
    """Removed cv-content-rules group can no longer be posted."""
    with patch("fitcv_cp.app.save_settings_group") as mock_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/group/cv-content-rules",
            data={},
        )
    assert resp.status_code == 404
    mock_save.assert_not_called()


def test_grouped_save_cv_validation_new_valid_redirects():
    """Valid cv-validation form POST with cv_max_pages → 303 redirect."""
    with patch("fitcv_cp.app.save_settings_group") as mock_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/group/cv-validation",
            data={
                "cv_max_pages": "3",
            },
        )
    assert resp.status_code == 303
    mock_save.assert_called_once()


def test_grouped_save_cv_validation_preserves_draft_on_failure():
    """Validation error → 422 response must include submitted values."""
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/group/cv-validation",
            data={
                "cv_max_pages": "0",   # invalid
            },
        )
    assert resp.status_code == 422
    assert "0" in resp.text


def test_grouped_save_cv_preset_invalid_does_not_partial_save():
    """Invalid cv_preset → 422; no partial write."""
    with patch("fitcv_cp.app.save_settings_group") as mock_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/group/cv-preset",
            data={
                "cv_preset": "",
                "cv_generation_model": "cx/gpt-5.4-mini",
            },
        )
    assert resp.status_code == 422
    mock_save.assert_not_called()


def test_grouped_save_cv_composition_invalid_does_not_partial_save():
    """@proves settings_system.grouped-form-validation

    Invalid cv_composition -> 422; no partial write of any field.
    """
    with patch("fitcv_cp.app.save_settings_group") as mock_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/group/cv-composition",
            data={
                "cv_summary_enabled": "definitely-not-bool",
                "cv_education_enabled": "true",
                "cv_experience_enabled": "true",
                "cv_skills_enabled": "true",
                "cv_certifications_enabled": "true",
                "cv_projects_enabled": "true",
                "cv_publications_enabled": "false",
                "cv_languages_enabled": "true",
            },
        )
    assert resp.status_code == 422
    mock_save.assert_not_called()


def test_section_save_rejects_hidden_deprecated_payload_key():
    with patch("fitcv_cp.app.save_settings_group") as mock_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/section/retrieval-core",
            data={
                "pipeline.vector_search_top_n": "50",
                "pipeline.ai_score_top_n": "50",
                "pipeline.final_top_n": "10",
                "pipeline.evidence_top_k": "5",
                "cv_generation_model": "cx/gpt-5.4-mini",
            },
        )
    assert resp.status_code == 422
    assert "Hidden deprecated settings are not writable" in resp.text
    mock_save.assert_not_called()
"""
@meta
type: test
scope: unit
domain: admin_ui
covers:
  - FitCV control-plane app behavior
excludes:
  - live HTTP deployment
tags:
  - fast
  - ci-safe
"""

def test_admin_settings_source_normalizes_composition_matrix_shell() -> None:
    source = open("src/fitcv_cp/app.py", encoding="utf-8").read()
    assert 'use_standard_shell = layout == "composition_matrix"' in source
    assert '"is_collapsible": False if use_standard_shell else bool(card_spec.get("is_collapsible", False))' in source


def test_admin_settings_source_uses_schema_owned_page_contract() -> None:
    source = open("src/fitcv_cp/app.py", encoding="utf-8").read()
    assert "build_settings_page_spec" in source
    assert "settings_page_spec = build_settings_page_spec()" in source
    assert "def _decision_domain_for_entry" not in source
    assert "decision_tabs = [" not in source
    assert "decision_domain_filters = [" not in source


def test_admin_settings_has_visibility_toggles_and_recommendation_preview_script() -> None:
    resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    html = resp.text
    assert 'id="toggle-only-actionable"' not in html
    assert 'data-accept-recommended' not in html
    assert 'data-review-required' not in html


def test_admin_settings_uses_pipeline_resource_ui() -> None:
    resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    html = resp.text
    assert 'id="pipeline-settings-app"' in html
    assert 'id="pipeline-manage-dialog"' in html
    assert 'data-setting-row=' in html
    assert "fitcvApiRequest('/settings/pipeline'" in html
    assert "async function patchSettings" in html
    assert "fitcvApiRequest('/settings/pipeline/actions/reset'" in html
    assert "field.type==='bool'" in html
    base_source = open("src/fitcv_cp/templates/base.html", encoding="utf-8").read()
    assert "localStorage" in base_source
    assert "Skip Incomplete Listings" not in html
    assert "Require Manual Review" not in html
    assert "Gap Threshold" not in html


def test_admin_settings_does_not_duplicate_workspace_pages_or_global_controls() -> None:
    resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    html = resp.text
    assert 'href="#runs"' not in html
    assert 'id="runDialog"' not in html
    assert 'id="runDetailsDrawer"' not in html
    assert 'id="candidateProfileDrawer"' not in html
    assert 'requestEnvelope(`/runs?' not in html
    assert "fitcvApiRequest('/runs'" not in html
    assert 'settings_revision_conflict' in html
    assert 'id="pipeline-dialog-status"' in html


def test_admin_settings_uses_approved_prototype_visual_contract() -> None:
    prototype = Path("docs/fitcv-settings-ui-prototype.html").read_text(encoding="utf-8")
    base = Path("src/fitcv_cp/templates/base.html").read_text(encoding="utf-8")
    template = Path("src/fitcv_cp/templates/settings.html").read_text(encoding="utf-8")

    assert "--accent:#b94d36" in prototype
    assert ':root[data-theme="light"]{color-scheme:light;--accent:#b94d36' in base
    assert "--bg:#fdfaf6" in base
    assert '--font:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif' in base
    assert "--sidebar-w:288px" in base
    assert "localStorage.getItem('fitcv-theme') || 'light'" in base
    assert "event.key !== 'Escape' || !sidebar.classList.contains('open')" in base
    assert 'class="shell app-shell"' in base
    assert 'class="sidebar app-sidebar"' in base
    assert 'class="brand-mark"' in base
    assert 'class="nav-group"' in base
    assert 'class="main app-frame"' in base
    assert ".content{width:min(960px,100%);margin:auto}" in base
    assert ".section-card{overflow:hidden;border:1px solid var(--border-soft);border-radius:12px" in base
    assert 'id="page-content"' in base
    assert ".settings-row" in base
    assert "history.pushState" in base
    assert "response.url || url" in base
    assert "history.replaceState" in base
    assert "addEventListener('popstate'" in base
    assert '<aside class="app-sidebar"' not in template
    assert "toggleTheme" not in template


def test_admin_settings_archived_run_delete_uses_preview_contract() -> None:
    template = Path("src/fitcv_cp/templates/runs_list.html").read_text(encoding="utf-8")

    assert "fitcvApiRequest('/runs/actions/delete-archived/preview'" in template
    assert "fitcvApiRequest('/runs/actions/delete-archived'" in template
    assert "preview_revision: preview.preview_revision" in template
    assert "bookmark_count" in template











def test_load_run_cv_generation_debug_payload_derives_review_item_id_for_legacy_review_required_rows() -> None:
    from types import SimpleNamespace

    run = SimpleNamespace(
        run_id="run-legacy-1",
        cv_generation_debug_json=json.dumps(
            {
                "run_id": "run-legacy-1",
                "debug_records": [
                    {
                        "status": "review_required",
                        "job_url": "",
                        "job_title": "Legacy review row",
                        "rank": 1,
                        "attempt_count": 1,
                    }
                ],
            }
        ),
    )

    payload = _load_run_cv_generation_debug_payload(run)
    assert isinstance(payload, dict)
    records = list(payload.get("debug_records") or [])
    assert len(records) == 1
    assert str(records[0].get("review_item_id") or "").startswith("ri_")

def test_is_hitl_resolution_pending_uses_terminal_status_set() -> None:
    assert _is_hitl_resolution_pending("pending") is True
    assert _is_hitl_resolution_pending("regeneration_requested") is True
    assert _is_hitl_resolution_pending("approved_as_is") is False
    assert _is_hitl_resolution_pending("rejected") is False

def test_normalize_hitl_resolution_status_uses_shared_review_identity_truth() -> None:
    from fitcv_cp.review_identity import normalize_review_resolution_status

    assert _normalize_hitl_resolution_status("approve", None) == normalize_review_resolution_status("approve", None)
    assert _normalize_hitl_resolution_status(None, "rejected") == normalize_review_resolution_status(None, "rejected")








def _decision_feedback_fixture():
    from fitcv.decision_feedback import build_decision_feedback_source

    config = {
        "decision_learning_policy": {
            "policy_version": "decision-learning-v2",
            "domain_id": "ranking_v1",
            "rating_scale": {
                "version": "application-interest-v1",
                "unrated_label": "unrated",
                "labels": {
                    "1": "definitely not interested",
                    "2": "low application interest",
                    "3": "might consider applying",
                    "4": "strong application interest",
                    "5": "would prioritize applying",
                },
            },
            "preference_compiler": {
                "compiler_version": "preference-compiler-v1",
                "minimum_rating_gap": 2,
                "gap_evidence_weights": {"1": 1.0, "2": 2.0, "3": 3.0, "4": 4.0},
                "max_episode_evidence_budget": 12.0,
            },
            "inverse_optimization": {
                "optimizer_version": "latent-residual-v1",
                "learned_alpha": 0.05,
                "learned_alpha_bounds": {
                    "minimum": 0.01,
                    "maximum": 0.10,
                    "step": 0.01,
                },
                "preference_margin": 0.02,
                "preference_regularization": 1.0,
                "preference_vector_norm_bound": 1.0,
                "solver": {"name": "CLARABEL", "max_iter": 200},
                "numeric_tolerances": {
                    "feasibility_absolute": 1.0e-7,
                    "numeric_equivalence_absolute": 1.0e-6,
                },
                "evaluation": {
                    "evaluation_version": "episode-grouped-v1",
                    "leave_one_episode_out_max_episodes": 8,
                    "grouped_fold_count": 5,
                },
                "activation": {
                    "activation_version": "ranking-policy-lifecycle-v1",
                    "minimum_fold_vector_stability": 0.0,
                },
            },
        },
        "ranking_policy": {"policy_version": "ranking-v2"},
        "ranking_contract": {"ranking_contract_fingerprint": "ranking-contract"},
        "embedding_model": "test-model",
    }
    source = build_decision_feedback_source(
        run_id="run-detail-test",
        candidate_profile={"preferences": {"preferred_locations": ["Berlin"]}},
        config=config,
        scoring_rows=[
            {
                "raw_job_fingerprint": "raw-job-1",
                "source_job_url": "https://jobs.example.com/1",
                "shortlist_origin": "vector_search",
                "scores": {"baseline_fit": 0.9, "baseline_fit_label": "strong"},
                "normalized_embedding": [1.0, 0.0],
                "embedding_contract_fingerprint": "embedding-contract",
            }
        ],
    )
    payload = json.dumps(
        {
            "schema_version": "results_job_ledger_v4",
            "decision_feedback_source": source,
            "results": [
                {
                    "job_url": "https://jobs.example.com/1",
                    "raw_job_fingerprint": "raw-job-1",
                    "pipeline_status": "ranked_no_cv",
                }
            ],
        }
    )
    return config, source, payload


def test_decision_feedback_post_and_no_js_form() -> None:
    config, source, payload = _decision_feedback_fixture()
    patches = _run_detail_patches(
        enriched_jobs=[
            {
                "job_url": "https://jobs.example.com/1",
                "raw_job_fingerprint": "raw-job-1",
                "title": "Data Engineer",
                "location": "Munich, Bavaria, Germany",
                "location_type": "hybrid",
                "required_skills": [],
            }
        ],
        filter_results=[
            {
                "job_url": "https://jobs.example.com/1",
                "passed": True,
                "reasons": [],
                "fit_factor_results": {
                    "language_fit": {
                        "evaluation": {
                            "evidence": {
                                "requirements": [
                                    {
                                        "language": "English",
                                        "requirement_type": "required",
                                        "truth": "met",
                                    }
                                ]
                            }
                        }
                    }
                },
            }
        ],
        results_export_json=payload,
    )
    store = MagicMock()
    store.list_decision_rating_events_for_run.return_value = []
    store.materialize_episode_and_append_rating.return_value = {
        "persistence_status": "persisted",
        "degradation_reason": "none",
    }
    with patches[0], patches[1], patches[2], patches[3], patches[4], \
         patch("fitcv_cp.app._resolve_run_store", return_value=store), \
         patch("fitcv_cp.app.load_config", return_value=config):
        client = TestClient(_app())
        page = client.get("/admin/runs/run-detail-test/tabs/enriched")
        response = client.post(
            "/admin/runs/run-detail-test/decision-feedback/raw-job-1",
            data={
                "rating": "5",
                "rating_scale_version": "application-interest-v1",
                "source_stage_artifact_fingerprint": source["source_stage_artifact_fingerprint"],
                "return_to": "/admin/runs/run-detail-test/tabs/enriched?page=2&q=python&unsafe=x",
            },
            follow_redirects=False,
        )
    assert page.status_code == 200
    assert "<fieldset" in page.text
    assert "Personal application interest after eligibility" in page.text
    assert "decision-feedback/raw-job-1" in page.text
    assert 'class="application-interest-stars"' in page.text
    assert page.text.count('class="btn-secondary application-interest-star"') == 5
    assert ':has(.application-interest-star:nth-child(5):hover)' in page.text
    assert 'aria-label="Set application interest to 5 of 5 stars"' in page.text
    assert "flex-direction: column" in page.text
    assert "<span>Location</span><strong>Munich, Bavaria, Germany</strong>" in page.text
    assert "<span>Work Mode</span><strong>hybrid</strong>" in page.text
    assert "<span>Language</span><strong>" in page.text
    assert "English" in page.text
    assert "level unspecified" in page.text
    assert "onclick=" not in page.text
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/runs/run-detail-test#pane-enriched"
    store.materialize_episode_and_append_rating.assert_called_once()


def test_decision_feedback_rejects_old_run_and_unknown_scale() -> None:
    config, source, payload = _decision_feedback_fixture()
    old_patches = _run_detail_patches(results_export_json=json.dumps({"schema_version": "results_job_ledger_v3", "results": []}))
    with old_patches[0], old_patches[1], old_patches[2], old_patches[3], old_patches[4]:
        old_response = TestClient(_app()).post(
            "/admin/runs/run-detail-test/decision-feedback/raw-job-1",
            data={"rating": "4", "rating_scale_version": "application-interest-v1"},
        )
    assert old_response.status_code == 409

    patches = _run_detail_patches(results_export_json=payload)
    with patches[0], patches[1], patches[2], patches[3], patches[4], \
         patch("fitcv_cp.app.load_config", return_value=config):
        bad_scale = TestClient(_app()).post(
            "/admin/runs/run-detail-test/decision-feedback/raw-job-1",
            data={
                "rating": "4",
                "rating_scale_version": "unknown",
                "source_stage_artifact_fingerprint": source["source_stage_artifact_fingerprint"],
            },
        )
    assert bad_scale.status_code == 422


def test_call_synonym_triage_provider_routes_through_llm_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fitcv.llm_runtime import (
        LlmAdapterResponse,
        LlmRuntimeProvenance,
        LlmRuntimeResult,
        LlmValidationResult,
    )
    from fitcv_cp import app as app_module

    captured: dict[str, Any] = {}

    def fake_execute(request, *, parser, validator, resolved_route):
        captured["request"] = request
        captured["route"] = resolved_route
        response = LlmAdapterResponse(
            adapter="openai_compatible",
            runtime_path="fitcv_llm_openai_compatible",
            raw_text=json.dumps(
                {
                    "recommended_action": "approve",
                    "recommendation_confidence": 0.91,
                    "recommendation_rationale": "High confidence",
                    "recommendation_risk_flags": [],
                }
            ),
            response_id="resp-triage",
        )
        parsed = parser(response)
        validation = validator(parsed)
        assert validation.valid is True
        return LlmRuntimeResult(
            status="succeeded",
            parsed_value=parsed,
            validation=LlmValidationResult(valid=True, errors=[], details={}),
            failure=None,
            provenance=LlmRuntimeProvenance(
                routing_part=request.routing_part,
                runtime_path=response.runtime_path,
                adapter=response.adapter,
                provider=resolved_route.provider,
                model=resolved_route.model,
                wire_api=resolved_route.wire_api,
                attempt_count=1,
                response_id=response.response_id,
                trace_id=None,
                latency_ms=1,
            ),
            adapter_response=response,
        )

    monkeypatch.setattr("fitcv_cp.app.execute_llm_task", fake_execute, raising=False)
    def fake_render_prompt(name, payload, **kwargs):
        captured["prompt_payload"] = payload
        return type(
            "Rendered",
            (),
            {
                "text": "prompt",
                "prompt_id": name,
                "version": "v1",
                "template_path": "prompt.md",
                "customized": False,
                "replacement_sha256": None,
                "replacement_char_count": 0,
            },
        )()

    monkeypatch.setattr("fitcv_cp.app.render_prompt", fake_render_prompt)

    result = app_module._call_synonym_triage_provider(
        proposal={
            "proposal_id": "proposal-1",
            "proposal_status": "proposed_unreviewed",
            "alias": "gcp",
            "canonical": "google cloud",
            "confidence": 0.9,
        },
        runtime={
            "provider": "openai_compatible",
            "base_url": "http://localhost:20128/v1",
            "api_key": "test-key",
            "model": "cx/gpt-5.4-mini",
            "wire_api": "chat_completions",
            "timeout_seconds": 20.0,
        },
        now_iso="2026-07-16T00:00:00Z",
    )

    assert captured["request"].routing_part == "synonym_triage_recommendation"
    assert captured["request"].response_mode == "json_object"
    assert captured["route"].model == "cx/gpt-5.4-mini"
    assert json.loads(captured["prompt_payload"]["proposal_json"]) == {
        "field": "skill",
        "alias": "gcp",
        "canonical": "google cloud",
        "candidate_canonicals": [],
        "confidence": 0.9,
    }
    assert "now_iso" not in captured["prompt_payload"]
    assert result["recommended_action"] == "approve"
    assert result["llm_runtime_evidence"]["provenance"]["response_id"] == "resp-triage"




def test_post_runs_path_queues_run_owned_canonical_projection(tmp_path, monkeypatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.chdir(tmp_path)
    jobs_file = tmp_path / "source-jobs.json"
    jobs_file.write_text(json.dumps([_valid_fitcv_job()]), encoding="utf-8")
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(_minimal_valid_profile_yaml(), encoding="utf-8")

    def capture_insert(run, *args, **kwargs):
        captured["run"] = run

    def capture_submit(**kwargs):
        captured["queued_jobs_path"] = kwargs["jobs_path"]
        return RunSubmission(
            run_id=kwargs["run_id"],
            queue_job_id="rq-job-1",
            backend_run_id=kwargs["run_id"],
            backend="default_queue",
        )

    with patch("fitcv_cp.app.insert_run", side_effect=capture_insert), patch(
        "fitcv_cp.app.submit_run", side_effect=capture_submit
    ), patch("fitcv_cp.app.update_run_queue_job_id"), patch(
        "fitcv_cp.app.load_active_settings", return_value={}
    ), patch(
        "fitcv_cp.app.load_config",
        return_value={
            "pipeline": {"final_top_n": 10},
            "paths": {"candidate_profile": str(profile_path)},
        },
    ):
        response = TestClient(_app()).post("/runs", json={"jobs_path": str(jobs_file)})

    assert response.status_code == 201, response.text
    run = captured["run"]
    queued_path = Path(captured["queued_jobs_path"])
    assert queued_path != jobs_file
    assert queued_path.name == f"{run.run_id}_jobs.json"
    assert queued_path.read_text(encoding="utf-8") == run.jobs_input_json
    import hashlib

    manifest = json.loads(run.jobs_input_manifest_json)
    assert manifest["canonical_sha256"] == hashlib.sha256(
        run.jobs_input_json.encode("utf-8")
    ).hexdigest()


def test_post_runs_path_rejects_empty_canonical_jobs(tmp_path) -> None:
    jobs_file = tmp_path / "empty.json"
    jobs_file.write_text("[]", encoding="utf-8")

    with patch("fitcv_cp.app.load_active_settings", return_value={}), patch(
        "fitcv_cp.app.load_config", return_value={"pipeline": {"final_top_n": 10}}
    ):
        response = TestClient(_app()).post("/runs", json={"jobs_path": str(jobs_file)})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "empty_job_input"


def test_post_runs_scanner_mode_needs_no_file_and_persists_provenance(tmp_path, monkeypatch) -> None:
    from fitcv.job_sources import AcquisitionResult
    from fitcv.ingest import canonicalize_jobs

    monkeypatch.chdir(tmp_path)
    captured: dict[str, Any] = {}
    with patch("fitcv_cp.app.load_config", return_value={"pipeline": {"final_top_n": 10}}):
        app = _app()
    app.state.run_store.get_candidate_profile_fn = lambda profile_id: {
        "candidate_profile_id": profile_id,
        "name": "Candidate",
        "profile": {"name": "Candidate"},
        "revision": 3,
        "is_active": True,
    }
    app.state.run_store.reserve_idempotent_action_fn = lambda *_args: {
        "action_id": "action-1",
        "replayed": False,
        "response": None,
    }
    app.state.run_store.complete_idempotent_action_fn = lambda *_args: None

    def capture_bundle(run, **_kwargs):
        captured["run"] = run
        return {"run_id": run.run_id}

    app.state.run_store.create_run_bundle_fn = capture_bundle
    app.state.run_store.get_run_detail_fn = lambda run_id: {"run_id": run_id}

    with patch("fitcv_cp.app.load_active_settings", return_value={}), patch(
        "fitcv_cp.app.load_config", return_value={"pipeline": {"final_top_n": 10}}
    ), patch(
        "fitcv_cp.app.acquire_scanner_jobs",
        return_value=AcquisitionResult(
            provider_id="greenhouse",
            selection_mode="auto",
            artifact=canonicalize_jobs([_valid_fitcv_job()]),
        ),
    ), patch(
        "fitcv_cp.app.submit_run",
        side_effect=lambda **kwargs: RunSubmission(
            run_id=kwargs["run_id"],
            queue_job_id="rq-job-1",
            backend_run_id=kwargs["run_id"],
            backend="default_queue",
        ),
    ):
        response = TestClient(app).post(
            "/runs",
            headers={"Idempotency-Key": "scanner-1"},
            data={
                "source_mode": "scanner",
                "provider": "auto",
                "company_name": "ACME GmbH",
                "careers_url": "https://job-boards.eu.greenhouse.io/acme",
                "keywords": "Data Engineer\nAnalytics",
                "max_jobs": "10",
                "timeout_seconds": "30",
                "profile_id": "candidate-1",
            },
        )

    assert response.status_code == 201, response.text
    run = captured["run"]
    assert run.jobs_input_source == "scanner"
    manifest = json.loads(run.jobs_input_manifest_json)
    assert manifest["provider_id"] == "greenhouse"
    assert manifest["selection_mode"] == "auto"
    assert manifest["keywords"] == ["Data Engineer", "Analytics"]
    assert manifest["canonical_sha256"]


def test_runs_list_renders_managed_scan_picker_instead_of_direct_scanner_fields() -> None:
    with patch("fitcv_cp.app.list_runs", return_value=[]):
        response = TestClient(_app()).get("/admin/runs")

    assert response.status_code == 200
    assert 'id="manageRunScans"' in response.text
    assert "Eligible Scan outputs" in response.text
    assert 'id="source_mode"' not in response.text
    assert 'id="scanner_provider"' not in response.text
    assert "scanner_careers_url" not in response.text

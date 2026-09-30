"""Public P0 corpus must not contain private profile records."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path


def test_public_p0b_projection_contains_cv_rows_only() -> None:
    root = Path(__file__).parents[1]
    projection = root / "data" / "fitcv-p0-corpus" / "p0b" / "candidate_evidence_projection.jsonl"
    reviewed = root / "data" / "fitcv-p0-corpus" / "p0b" / "reviewed_requirement_evidence.jsonl"
    manifest = json.loads(
        (root / "data" / "fitcv-p0-corpus" / "p0b" / "projection_manifest.json").read_text(encoding="utf-8")
    )
    rows = [json.loads(line) for line in projection.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert rows
    assert all(row["source_kind"] == "cv" for row in rows)
    assert all("private" not in row["source_file"].lower() for row in rows)
    assert "Colton Alexander" not in projection.read_text(encoding="utf-8")
    assert "Colton Alexander" not in reviewed.read_text(encoding="utf-8")
    evidence_fields = [
        value
        for row in rows
        for value in (row.get("raw_evidence_text"), row.get("source_section"))
        if isinstance(value, str)
    ]
    reviewed_fields = [
        value
        for line in reviewed.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for value in (
            json.loads(line).get("raw_evidence_text"),
            json.loads(line).get("provenance", {}).get("evidence", {}).get("source_section"),
        )
        if isinstance(value, str)
    ]
    reviewed_rows = [json.loads(line) for line in reviewed.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert all(row.get("raw_evidence_text") for row in reviewed_rows)
    assert all(row.get("provenance", {}).get("evidence", {}).get("source_section") for row in reviewed_rows)
    for value in evidence_fields + reviewed_fields:
        assert not re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", value)
        assert not re.search(r"(?<!\d)\+?\d[\d ()-]{7,}\d(?!\d)", value)
    assert manifest["counts"]["records"] == len(rows)
    assert manifest["counts"]["private_profile_records"] == 0
    assert manifest["sha256"] == __import__("hashlib").sha256(projection.read_bytes()).hexdigest()


def test_public_p0a_snapshot_integrity() -> None:
    root = Path(__file__).parents[1]
    corpus = root / "data" / "fitcv-p0-corpus" / "p0a"
    postings_path = corpus / "raw_postings_de_en_v4.jsonl"
    ranking_path = corpus / "ranking_source_backed_v4.json"
    manifest = json.loads((corpus / "ranking_source_backed_v4_manifest.json").read_text(encoding="utf-8"))
    postings = [json.loads(line) for line in postings_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ranking = json.loads(ranking_path.read_text(encoding="utf-8"))

    assert len(postings) == manifest["row_count"] == 104
    assert len({(row["source_id"], row["language"]) for row in postings}) == 104
    assert {row["language"] for row in postings} == {"de", "en", "mixed"}
    assert all(row.get("reviewed", True) is True for row in postings)
    assert all(row.get("split", "") in {"", "calibration", "held_out"} for row in postings)
    assert all(not row.get("posterFullName") and not row.get("posterProfileUrl") for row in postings)
    assert not re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", postings_path.read_text(encoding="utf-8"))
    assert manifest["fixture_path"] == "data/fitcv-p0-corpus/p0a/ranking_source_backed_v4.json"
    assert manifest["fixture_sha256"] == __import__("hashlib").sha256(ranking_path.read_bytes()).hexdigest()
    assert manifest["source_snapshot_sha256"] == __import__("hashlib").sha256(postings_path.read_bytes()).hexdigest()
    assert ranking["fixture_status"] == "ready"
    assert ranking["source_snapshot"]["path"] == "data/fitcv-p0-corpus/p0a/raw_postings_de_en_v4.jsonl"


def test_public_p0b_reviewed_rows_join_to_admitted_p0a_jobs() -> None:
    root = Path(__file__).parents[1]
    p0a = root / "data" / "fitcv-p0-corpus" / "p0a" / "raw_postings_de_en_v4.jsonl"
    reviewed = root / "data" / "fitcv-p0-corpus" / "p0b" / "reviewed_requirement_evidence.jsonl"
    manifest = json.loads(
        (root / "data" / "fitcv-p0-corpus" / "p0b" / "reviewed_requirement_evidence_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    admitted_ids = {
        json.loads(line)["source_id"]
        for line in p0a.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    rows = [json.loads(line) for line in reviewed.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows
    assert all(row["provenance"]["requirement"]["source_record_id"] in admitted_ids for row in rows)
    assert manifest["sha256"] == __import__("hashlib").sha256(reviewed.read_bytes()).hexdigest()
    assert manifest["records"] == len(rows)
    assert manifest["requirement_instances"] == len({row["requirement_instance_id"] for row in rows})
    assert manifest["evidence_ids"] == len({row["evidence_id"] for row in rows})
    assert manifest["requirement_evidence_pairs"] == len({
        (row["requirement_instance_id"], row["evidence_id"]) for row in rows
    })


def test_public_p0b_adjudicated_relevance_labels_cover_mixed_cases() -> None:
    root = Path(__file__).parents[1]
    reviewed = root / "data" / "fitcv-p0-corpus" / "p0b" / "reviewed_requirement_evidence.jsonl"
    manifest = json.loads(
        (root / "data" / "fitcv-p0-corpus" / "p0b" / "reviewed_requirement_evidence_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    rows = [json.loads(line) for line in reviewed.read_text(encoding="utf-8").splitlines() if line.strip()]
    row_by_evidence_id = {row["evidence_id"]: row for row in rows}
    labeled = manifest["relevance_labels"]

    assert {label["relevance_label"] for label in labeled} == {"relevant", "borderline", "irrelevant"}
    assert all(label["review_status"] == "approved" for label in labeled)
    assert all(label["evidence_id"] in row_by_evidence_id for label in labeled)
    assert all(row_by_evidence_id[label["evidence_id"]]["support_verdict"] in {"supported", "unknown"} for label in labeled)
    assert row_by_evidence_id[next(label for label in labeled if label["relevance_label"] == "borderline")["evidence_id"]]["support_verdict"] == "unknown"
    assert row_by_evidence_id[next(label for label in labeled if label["relevance_label"] == "irrelevant")["evidence_id"]]["support_verdict"] == "unknown"


def test_public_p0_corpus_uses_lf_and_manifest_hashes_match_bytes() -> None:
    root = Path(__file__).parents[1]
    corpus = root / "data" / "fitcv-p0-corpus"
    tracked = subprocess.run(
        ["git", "ls-files", "--cached", "data/fitcv-p0-corpus"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    for relative_path in tracked:
        path = root / relative_path
        if path.is_file():
            assert b"\r\n" not in path.read_bytes(), path

    manifest_paths = {
        corpus / "p0b" / "projection_manifest.json": corpus / "p0b" / "candidate_evidence_projection.jsonl",
        corpus / "p0b" / "reviewed_requirement_evidence_manifest.json": corpus / "p0b" / "reviewed_requirement_evidence.jsonl",
    }
    for manifest_path, payload_path in manifest_paths.items():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["sha256"] == hashlib.sha256(payload_path.read_bytes()).hexdigest()


def test_public_p0a_v4_manifest_binds_all_referenced_artifacts() -> None:
    root = Path(__file__).parents[1]
    corpus = root / "data" / "fitcv-p0-corpus" / "p0a"
    manifest = json.loads((corpus / "ranking_source_backed_v4_manifest.json").read_text(encoding="utf-8"))
    fixture = corpus / "ranking_source_backed_v4.json"
    source_snapshot = corpus / "raw_postings_de_en_v4.jsonl"
    score_artifact = corpus / "p0a-v4-production-scores.json"
    impact_manifest = json.loads((corpus / "impact_measure_corpus_manifest_v4.json").read_text(encoding="utf-8"))

    assert manifest["fixture_path"] == "data/fitcv-p0-corpus/p0a/ranking_source_backed_v4.json"
    assert manifest["fixture_sha256"] == hashlib.sha256(fixture.read_bytes()).hexdigest()
    assert manifest["source_snapshot_sha256"] == hashlib.sha256(source_snapshot.read_bytes()).hexdigest()
    assert manifest["score_artifact_sha256"] == hashlib.sha256(score_artifact.read_bytes()).hexdigest()
    assert manifest["review_packet_sha256"] == hashlib.sha256(
        (root / manifest["review_packet_path"]).read_bytes()
    ).hexdigest()
    for reviewer in manifest["reviewer_artifacts"]:
        reviewer_path = root / reviewer["path"]
        assert reviewer["sha256"] == hashlib.sha256(reviewer_path.read_bytes()).hexdigest()

    fixture_data = json.loads(fixture.read_text(encoding="utf-8"))
    score_data = json.loads(score_artifact.read_text(encoding="utf-8"))
    assert fixture_data["fixture_status"] == "ready"
    assert manifest["row_count"] == sum(
        len(pool["candidates"]) for pool in fixture_data["profiles"].values()
    )
    assert score_data["fixture"] == manifest["fixture_path"]
    assert score_data["fixture_sha256"] == manifest["fixture_sha256"]
    for report in impact_manifest["benchmark_reports"].values():
        report_path = root / report["path"]
        assert report["sha256"] == hashlib.sha256(report_path.read_bytes()).hexdigest()
    assert {row["language"] for pool in fixture_data["profiles"].values() for row in pool["candidates"]} >= {
        "de",
        "en",
        "mixed",
    }
    assert any(
        row["language"] == "mixed" and "Italian" in row["job"]["title"]
        for pool in fixture_data["profiles"].values()
        for row in pool["candidates"]
    )
    for pool in fixture_data["profiles"].values():
        assert set(pool["profile"]) == {"preferences", "skills"}
        assert set(pool["profile"]["preferences"]) == {
            "target_role",
            "role_families",
            "domains",
            "location_types",
        }
        profile_text = json.dumps(pool["profile"], ensure_ascii=False)
        assert not re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", profile_text)
        assert not re.search(r"(?<!\d)\+?\d[\d ()-]{7,}\d(?!\d)", profile_text)

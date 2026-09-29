"""Public P0 corpus must not contain private profile records."""

from __future__ import annotations

import hashlib
import json
import re
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
    postings_path = corpus / "raw_postings_de_en.jsonl"
    ranking_path = corpus / "ranking_source_backed.json"
    admission = json.loads((corpus / "admission_report.json").read_text(encoding="utf-8"))
    postings = [json.loads(line) for line in postings_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ranking = json.loads(ranking_path.read_text(encoding="utf-8"))

    assert len(postings) == 100
    assert len({row["job_id"] for row in postings}) == 100
    assert {row["language"] for row in postings} == {"de", "en"}
    assert all(row["reviewed"] is True for row in postings)
    assert all(row["split"] in {"calibration", "held_out"} for row in postings)
    assert all(not row.get("posterFullName") and not row.get("posterProfileUrl") for row in postings)
    assert not re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", postings_path.read_text(encoding="utf-8"))
    assert all(
        sum(1 for row in postings if row["language"] == language and row["split"] == split)
        == expected
        for language, split, expected in (
            ("de", "calibration", 40),
            ("de", "held_out", 10),
            ("en", "calibration", 40),
            ("en", "held_out", 10),
        )
    )
    assert admission["target"]["path"] == "data/fitcv-p0-corpus/p0a/raw_postings_de_en.jsonl"
    assert admission["target"]["sha256"] == __import__("hashlib").sha256(
        postings_path.read_bytes()
    ).hexdigest()
    assert ranking["corpus_source"] == "data/fitcv-p0-corpus/p0a/raw_postings_de_en.jsonl"
    assert admission["publication"]["source_files_are_admission_inputs"] is True
    assert admission["publication"]["published_files"]["raw_postings_de_en.jsonl"]["sha256"] == admission["target"]["sha256"]
    assert admission["publication"]["published_files"]["ranking_source_backed.json"]["sha256"] == __import__("hashlib").sha256(
        ranking_path.read_bytes()
    ).hexdigest()


def test_public_p0b_reviewed_rows_join_to_admitted_p0a_jobs() -> None:
    root = Path(__file__).parents[1]
    p0a = root / "data" / "fitcv-p0-corpus" / "p0a" / "raw_postings_de_en.jsonl"
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
    for path in corpus.rglob("*"):
        if path.is_file():
            assert b"\r\n" not in path.read_bytes(), path

    manifest_paths = {
        corpus / "p0b" / "projection_manifest.json": corpus / "p0b" / "candidate_evidence_projection.jsonl",
        corpus / "p0b" / "reviewed_requirement_evidence_manifest.json": corpus / "p0b" / "reviewed_requirement_evidence.jsonl",
    }
    for manifest_path, payload_path in manifest_paths.items():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["sha256"] == hashlib.sha256(payload_path.read_bytes()).hexdigest()

from __future__ import annotations

from io import BytesIO
import zipfile

import pytest
import yaml

from fitcv.candidate import canonical_candidate_checksum, validate_candidate_profile_v2
from fitcv.candidate_ingest import CandidateIngestError, ingest_candidate_source


DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _docx_bytes(*, include_unsafe_entry: bool = False) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>""",
        )
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Alex Morgan</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>SQL</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Python</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>""",
        )
        archive.writestr(
            "word/header1.xml",
            """<?xml version="1.0"?><w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>Candidate CV</w:t></w:r></w:p></w:hdr>""",
        )
        archive.writestr(
            "word/footer1.xml",
            """<?xml version="1.0"?><w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>Page footer</w:t></w:r></w:p></w:ftr>""",
        )
        if include_unsafe_entry:
            archive.writestr("../escape.xml", "unsafe")
    return output.getvalue()


def _minimal_v2_yaml() -> bytes:
    payload = {
        "schema_version": "candidate-profile.v2",
        "source_documents": [
            {
                "id": "declared_portfolio",
                "filename": "portfolio.md",
                "media_type": "text/markdown",
                "sha256": "a" * 64,
            }
        ],
        "name": "Alex Morgan",
        "contact": {},
        "experiences": [
            {
                "id": "exp_1",
                "role": "Analyst",
                "company": "Northstar",
                "source_refs": [],
                "evidence": [
                    {
                        "id": "ev_exp_1",
                        "kind": "work_achievement",
                        "text": "Automated reporting with SQL.",
                        "source_refs": [],
                    }
                ],
            }
        ],
        "education": [],
        "projects": [],
        "achievements": [],
        "certifications": [],
        "volunteering": [],
        "languages": [],
        "interests": [],
        "search_preferences": {"target_role": "Data Analyst"},
        "skills": [
            {
                "id": "skill_sql",
                "name": "SQL",
                "origin": "user",
                "confidence": 1.0,
                "support_status": "supported",
                "evidence_refs": ["ev_exp_1"],
            }
        ],
        "role_families": [],
        "domain_tags": [],
        "responsibility_themes": [],
    }
    return yaml.safe_dump(payload, sort_keys=False).encode()


def _minimal_v1_yaml() -> bytes:
    payload = {
        "name": "Alex Morgan",
        "contact": {},
        "experiences": [
            {
                "id": "exp_1",
                "role": "Analyst",
                "company": "Northstar",
                "start": "2025-01",
                "current": True,
                "bullets": [{"text": "Automated reporting with SQL.", "skills": ["SQL"]}],
            }
        ],
        "education": [],
        "projects": [],
        "achievements": [],
        "certifications": [],
        "volunteering": [],
        "languages": [],
        "interests": [],
        "preferences": {"target_role": "Data Analyst"},
        "skills": [{"name": "SQL", "evidence_refs": ["exp_1"]}],
    }
    return yaml.safe_dump(payload, sort_keys=False).encode()


def test_markdown_ingestion_is_deterministic_and_preserves_native_locators() -> None:
    content = b"# Alex Morgan\n\n- SQL reporting\n\n| Tool | Level |\n| --- | --- |\n| Python | Advanced |\n"

    first = ingest_candidate_source("candidate.md", "text/markdown", content)
    second = ingest_candidate_source("candidate.md", "text/markdown", content)

    assert first == second
    assert first.source_document["origin"] == "uploaded"
    assert first.source_document["sha256"]
    assert [block["kind"] for block in first.source_blocks] == [
        "heading",
        "list_item",
        "table_row",
        "table_row",
        "table_row",
    ]
    assert first.source_blocks[0]["locator"] == {"kind": "markdown_lines", "start": 1, "end": 1}
    assert first.profile is None


def test_docx_ingestion_reads_document_table_header_and_footer() -> None:
    result = ingest_candidate_source("candidate.docx", DOCX_MEDIA_TYPE, _docx_bytes())

    assert [block["text"] for block in result.source_blocks] == [
        "Alex Morgan",
        "SQL",
        "Python",
        "Candidate CV",
        "Page footer",
    ]
    assert [block["kind"] for block in result.source_blocks] == [
        "paragraph",
        "table_cell",
        "table_cell",
        "header",
        "footer",
    ]
    assert result.source_blocks[-1]["locator"]["part"] == "footer"
    assert result.source_blocks[-1]["locator"]["source_part"] == "word/footer1.xml"


@pytest.mark.parametrize(
    ("filename", "media_type", "content", "code"),
    [
        ("../candidate.md", "text/markdown", b"Alex", "candidate_profile_unsafe_filename"),
        ("candidate.pdf", "application/pdf", b"%PDF", "candidate_profile_unsupported_source"),
        ("candidate.md", "application/yaml", b"Alex", "candidate_profile_media_mismatch"),
        ("candidate.md", "text/markdown", b"", "candidate_profile_empty_source"),
        ("candidate.docx", DOCX_MEDIA_TYPE, b"not-a-zip", "candidate_profile_invalid_docx"),
    ],
)
def test_upload_boundary_rejects_invalid_sources(
    filename: str,
    media_type: str,
    content: bytes,
    code: str,
) -> None:
    with pytest.raises(CandidateIngestError) as error:
        ingest_candidate_source(filename, media_type, content)

    assert error.value.code == code


def test_upload_boundary_rejects_request_and_docx_expansion_limits() -> None:
    with pytest.raises(CandidateIngestError) as request_error:
        ingest_candidate_source("candidate.md", "text/markdown", b"12345", max_bytes=4)
    assert request_error.value.code == "candidate_profile_source_too_large"

    with pytest.raises(CandidateIngestError) as expansion_error:
        ingest_candidate_source(
            "candidate.docx",
            DOCX_MEDIA_TYPE,
            _docx_bytes(),
            max_docx_expanded_bytes=20,
        )
    assert expansion_error.value.code == "candidate_profile_docx_expansion_too_large"


def test_docx_ingestion_rejects_unsafe_archive_entries() -> None:
    with pytest.raises(CandidateIngestError) as error:
        ingest_candidate_source(
            "candidate.docx",
            DOCX_MEDIA_TYPE,
            _docx_bytes(include_unsafe_entry=True),
        )

    assert error.value.code == "candidate_profile_unsafe_docx"


def test_v2_yaml_preserves_declared_sources_and_injects_uploaded_traceability() -> None:
    result = ingest_candidate_source("candidate.yaml", "application/yaml", _minimal_v2_yaml())
    assert result.profile is not None

    profile = result.profile
    uploaded = profile["source_documents"][0]
    declared = profile["source_documents"][1]
    assert uploaded["origin"] == "uploaded"
    assert declared["origin"] == "declared"
    assert profile["experiences"][0]["source_refs"][0]["document_id"] == uploaded["id"]
    assert profile["experiences"][0]["evidence"][0]["source_refs"][0]["document_id"] == uploaded["id"]
    assert profile["search_preferences"] == {"target_role": "Data Analyst"}
    assert validate_candidate_profile_v2(profile) == []
    assert canonical_candidate_checksum(profile) == canonical_candidate_checksum(profile)


def test_v2_yaml_normalizes_absent_optional_sections() -> None:
    payload = yaml.safe_load(_minimal_v2_yaml())
    for key in ("contact", "interests", "volunteering", "role_families", "domain_tags", "responsibility_themes"):
        payload.pop(key)

    result = ingest_candidate_source("candidate.yaml", "application/yaml", yaml.safe_dump(payload).encode())

    assert result.profile is not None
    assert result.profile["contact"] == {}
    assert result.profile["interests"] == []
    assert result.profile["volunteering"] == []
    assert result.profile["role_families"] == []
    assert result.profile["domain_tags"] == []
    assert result.profile["responsibility_themes"] == []


def test_v1_yaml_adapts_current_dates_parent_refs_and_evidence_ids() -> None:
    result = ingest_candidate_source("candidate.yaml", "application/yaml", _minimal_v1_yaml())
    assert result.profile is not None

    profile = result.profile
    experience = profile["experiences"][0]
    evidence = experience["evidence"][0]
    assert profile["schema_version"] == "candidate-profile.v2"
    assert experience["company"] == "Northstar"
    assert "current" not in experience
    assert experience["end"] == "Present"
    assert evidence["id"].startswith("ev_exp_1_")
    assert profile["skills"][0]["evidence_refs"] == [evidence["id"]]
    assert validate_candidate_profile_v2(profile) == []


def test_yaml_rejects_dangling_evidence_refs() -> None:
    payload = yaml.safe_load(_minimal_v2_yaml())
    payload["skills"][0]["evidence_refs"] = ["ev_missing"]

    with pytest.raises(CandidateIngestError) as error:
        ingest_candidate_source(
            "candidate.yaml",
            "application/yaml",
            yaml.safe_dump(payload).encode(),
        )

    assert error.value.code == "candidate_profile_invalid_references"

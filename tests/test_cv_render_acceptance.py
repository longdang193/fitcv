"""Native rendered-artifact acceptance checks for representative CVs."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import types
from pathlib import Path
from typing import Any

import pytest

from fitcv.agentic_cv_generation import build_cv_content_plan
from fitcv.cv_generator import (
    build_empty_structured_cv,
    render_cv_markdown,
    render_cv_native_acceptance,
    _validate_pdf_against_reference,
    _validate_rendered_pdf_content,
    serialize_mycvs_v1,
    validate_mycvs_v1_markdown,
)
from fitcv.pipeline import _is_persistable_cv_generation_result
from fitcv_cp.run_artifact_contracts import accepted_cv_artifact_event_v1


CONFIG = {"cv": {"preset": "europass"}}
pytestmark = pytest.mark.render_acceptance


def _build_fixture(*, experience_count: int, bullets_per_experience: int, include_optional: bool) -> dict[str, Any]:
    document = build_empty_structured_cv(
        jd={"title": "Senior Data Analyst"},
        profile={"name": "Test Candidate"},
        config=CONFIG,
        fit_classification="strong",
    )
    sections = document["sections"]
    sections["header"].update(
        {
            "name": "Test Candidate",
            "title": "Senior Data Analyst",
            "location": None,
            "contact": {"email": None, "phone": None, "linkedin": None},
        }
    )
    sections["summary"] = {"text": "Experienced analyst delivering decision-grade reporting and automation."}
    sections["skills"] = {
        "groups": [{"label": "Core", "items": ["SQL", "Python", "Power BI", "BigQuery"]}]
    }
    sections["experience"] = [
        {
            "role": f"Data Analyst {index}",
            "company": f"Company {index}",
            "start": "2020",
            "end": "2025",
            "location": None,
            "bullets": [
                f"Built SQL reporting workflows with Power BI and measurable outcome {index}.",
                f"Automated Python data quality checks and reduced manual work {index}.",
            ][:bullets_per_experience],
        }
        for index in range(experience_count)
    ]
    sections["education"] = [
        {
            "degree": "MSc Data Science",
            "institution": "University of Berlin",
            "field": "Computer Science",
            "start": "2018",
            "end": "2020",
        }
    ]
    if include_optional:
        sections["certifications"] = [
            {"name": "Cloud Data Engineer", "issuer": "Example Institute", "year": "2024"}
        ]
        sections["projects"] = [
            {
                "name": "Analytics Platform",
                "context": "Internal platform.",
                "bullets": ["Improved reporting reliability.", "Reduced manual work."],
            }
        ]
        sections["languages"] = [
            {"name": "English", "level": "C1"},
            {"name": "German", "level": "B2"},
        ]
    return document


def _render_pdf(markdown: str, output_dir: Path, name: str) -> tuple[Path, str]:
    required_tools = ["pandoc", "xelatex", "pdfinfo", "pdftotext"]
    missing_tools = [tool for tool in required_tools if shutil.which(tool) is None]
    if missing_tools:
        pytest.fail(f"native PDF acceptance tools missing: {', '.join(missing_tools)}")

    markdown_path = output_dir / f"{name}.md"
    pdf_path = output_dir / f"{name}.pdf"
    markdown_path.write_text(markdown, encoding="utf-8", newline="\n")
    subprocess.run(
        ["pandoc", str(markdown_path), "-o", str(pdf_path), "--pdf-engine=xelatex"],
        check=True,
        capture_output=True,
        text=True,
    )
    page_info = subprocess.run(["pdfinfo", str(pdf_path)], check=True, capture_output=True, text=True).stdout
    page_count = int(re.search(r"^Pages:\s+(\d+)$", page_info, re.MULTILINE).group(1))
    extracted_text = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return pdf_path, extracted_text


@pytest.mark.parametrize(
    ("name", "experience_count", "bullets_per_experience", "include_optional"),
    [
        ("compact", 1, 2, True),
        ("education-skills", 2, 3, True),
        ("long-experience", 3, 2, False),
    ],
)
def test_representative_cv_artifacts_fit_one_page_and_retain_protected_requirements(
    tmp_path: Path,
    name: str,
    experience_count: int,
    bullets_per_experience: int,
    include_optional: bool,
) -> None:
    markdown = render_cv_markdown(
        _build_fixture(
            experience_count=experience_count,
            bullets_per_experience=bullets_per_experience,
            include_optional=include_optional,
        ),
        CONFIG,
    )
    pdf_path, extracted_text = _render_pdf(markdown, tmp_path, name)

    assert int(
        re.search(
            r"^Pages:\s+(\d+)$",
            subprocess.run(["pdfinfo", str(pdf_path)], check=True, capture_output=True, text=True).stdout,
            re.MULTILINE,
        ).group(1)
    ) == 1
    for marker in (
        "Test Candidate",
        "Summary",
        "Experience",
        "Education",
        "Skills",
        "SQL",
        "Python",
        "Power BI",
    ):
        assert marker in extracted_text
    assert re.fullmatch(r"[0-9a-f]{64}", hashlib.sha256(pdf_path.read_bytes()).hexdigest())


def test_dense_skill_list_fits_one_page(tmp_path: Path) -> None:
    document = _build_fixture(experience_count=2, bullets_per_experience=2, include_optional=True)
    document["sections"]["skills"] = {
        "groups": [
            {
                "label": "Core",
                "items": [f"Skill {index}" for index in range(32)],
            }
        ]
    }

    pdf_path, _ = _render_pdf(render_cv_markdown(document, CONFIG), tmp_path, "dense-skills")

    page_info = subprocess.run(["pdfinfo", str(pdf_path)], check=True, capture_output=True, text=True).stdout
    assert int(re.search(r"^Pages:\s+(\d+)$", page_info, re.MULTILINE).group(1)) == 1



def _bbox_xml(*headings: str) -> str:
    lines = ['Candidate', *headings]
    xml_lines = []
    for index, text in enumerate(lines):
        y = 20 + index * 20
        x_min, x_max = (247.5, 347.5) if index == 0 else (100, 200)
        xml_lines.append(
            f'<line xMin="{x_min}" yMin="{y}" xMax="{x_max}" yMax="{y + 10}">'
            f'<word xMin="{x_min}" yMin="{y}" xMax="{x_max}" yMax="{y + 10}">{text}</word>'
            '</line>'
        )
    return (
        '<doc><page width="594.96" height="841.92"><flow>'
        + ''.join(xml_lines)
        + '</flow></page></doc>'
    )


def _structured_bbox_xml(*, bullet_x: float = 33.2, wrap_variant: bool = False) -> str:
    rows = [
        ("Candidate", 247.5, 347.5, 20),
        ("Summary", 18.7, 72.2, 40),
        ("Education", 18.7, 75.0, 60),
        ("Project title", 26.5, 140.0, 80),
        ("Bullet text", bullet_x, 180.0, 100),
        ("University", 270.0, 340.0, 120),
        ("2024 - Present", 507.5, 577.0, 120),
        ("Experience", 18.7, 81.5, 140),
        ("Projects", 18.7, 64.8, 160),
        ("Certificates", 18.7, 84.8, 180),
        ("Skills", 18.7, 48.3, 200),
    ]
    xml_lines = []
    for text, x_min, x_max, y in rows:
        if wrap_variant and text == "Bullet text":
            word_starts = (x_min, x_min + 70.0, x_min + 122.0)
            words = (
                f'<word xMin="{word_starts[0]}" yMin="{y}" xMax="{word_starts[0] + 20}" yMax="{y + 10}">Bullet</word>'
                f'<word xMin="{word_starts[1]}" yMin="{y}" xMax="{word_starts[1] + 20}" yMax="{y + 10}">text</word>'
            )
        else:
            words = f'<word xMin="{x_min}" yMin="{y}" xMax="{x_max}" yMax="{y + 10}">{text}</word>'
        xml_lines.append(
            f'<line xMin="{x_min}" yMin="{y}" xMax="{x_max}" yMax="{y + 10}">{words}</line>'
        )
    return (
        '<doc><page width="594.96" height="841.92"><flow>'
        + "".join(xml_lines)
        + "</flow></page></doc>"
    )


def test_pdf_reference_validation_accepts_matching_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = tmp_path / "candidate.pdf"
    reference = tmp_path / "reference.pdf"
    candidate.write_bytes(b"candidate")
    reference.write_bytes(b"reference")
    headings = ("Summary", "Education", "Experience", "Projects", "Certificates", "Skills")
    bbox = _bbox_xml(*headings)

    def fake_run(command, **kwargs):
        if command[0] == "pdfinfo":
            return types.SimpleNamespace(
                stdout="Pages: 1\nPage size: 594.96 x 841.92 pts (A4)\nPage rot: 0\n"
            )
        if command[0] == "pdffonts":
            return types.SimpleNamespace(
                stdout=(
                    "name type encoding emb sub uni object ID\n"
                    "AAAAAA+Inter-SemiBold CID TrueType Identity-H yes yes yes 4 0\n"
                    "BAAAAA+Inter-Regular CID TrueType Identity-H yes yes yes 6 0\n"
                )
            )
        if command[0] == "pdftotext":
            return types.SimpleNamespace(stdout=bbox)
        raise AssertionError(command)

    monkeypatch.setattr("fitcv.cv_generator.subprocess.run", fake_run)
    result = _validate_pdf_against_reference(
        candidate,
        reference,
        candidate_page_info="Pages: 1\nPage size: 594.96 x 841.92 pts (A4)\nPage rot: 0\n",
        work_dir=tmp_path,
    )

    assert result["status"] == "pass"
    assert result["errors"] == []
    assert result["metrics"]["candidate_sections"] == list(headings)


def test_pdf_reference_validation_rejects_heading_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = tmp_path / "candidate.pdf"
    reference = tmp_path / "reference.pdf"
    candidate.write_bytes(b"candidate")
    reference.write_bytes(b"reference")
    headings = ("Summary", "Experience", "Education", "Projects", "Certificates", "Skills")
    reference_bbox = _bbox_xml("Summary", "Education", "Experience", "Projects", "Certificates", "Skills")
    candidate_bbox = _bbox_xml(*headings)

    def fake_run(command, **kwargs):
        if command[0] == "pdfinfo":
            return types.SimpleNamespace(
                stdout="Pages: 1\nPage size: 594.96 x 841.92 pts (A4)\nPage rot: 0\n"
            )
        if command[0] == "pdffonts":
            return types.SimpleNamespace(
                stdout=(
                    "name type encoding emb sub uni object ID\n"
                    "AAAAAA+Inter-SemiBold CID TrueType Identity-H yes yes yes 4 0\n"
                    "BAAAAA+Inter-Regular CID TrueType Identity-H yes yes yes 6 0\n"
                )
            )
        if command[0] == "pdftotext":
            return types.SimpleNamespace(stdout=candidate_bbox if str(candidate) in command else reference_bbox)
        raise AssertionError(command)

    monkeypatch.setattr("fitcv.cv_generator.subprocess.run", fake_run)
    result = _validate_pdf_against_reference(
        candidate,
        reference,
        candidate_page_info="Pages: 1\nPage size: 594.96 x 841.92 pts (A4)\nPage rot: 0\n",
        work_dir=tmp_path,
    )

    assert result["status"] == "fail"
    assert "rendered PDF section headings are out of order" in result["errors"]


def test_render_visibility_accepts_letter_spaced_pdf_extraction() -> None:
    document = _build_fixture(experience_count=1, bullets_per_experience=2, include_optional=True)

    result = _validate_rendered_pdf_content(
        "Te s t C a n d i d a t e\nSummary\nEducation\nExperience\nProjects\nCertificates\nSkills\n"
        "MSc\nData\nScience\nData\nAnalyst 0\nAnalytics\nPlatform\nCloud\nData\nEngineer\nSQL\n",
        document,
    )

    assert result["status"] == "pass"
    assert result["expected_text_errors"] == []
    assert result["record_visibility_errors"] == []


def test_pdf_reference_validation_allows_missing_optional_anchor_category(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "candidate.pdf"
    reference = tmp_path / "reference.pdf"
    candidate.write_bytes(b"candidate")
    reference.write_bytes(b"reference")
    reference_bbox = _structured_bbox_xml()
    candidate_bbox = _structured_bbox_xml().replace(
        '<line xMin="26.5" yMin="80" xMax="140.0" yMax="90"><word xMin="26.5" yMin="80" xMax="140.0" yMax="90">Project title</word></line>',
        '<line xMin="18.7" yMin="80" xMax="140.0" yMax="90"><word xMin="18.7" yMin="80" xMax="140.0" yMax="90">Project title</word></line>',
    )

    def fake_run(command, **kwargs):
        if command[0] == "pdfinfo":
            return types.SimpleNamespace(
                stdout="Pages: 1\nPage size: 594.96 x 841.92 pts (A4)\nPage rot: 0\n"
            )
        if command[0] == "pdffonts":
            return types.SimpleNamespace(
                stdout=(
                    "name type encoding sub uni object ID\n"
                    "AAAAAA+Inter-SemiBold CID TrueType Identity-H yes yes 4 0\n"
                    "BAAAAA+Inter-Regular CID TrueType Identity-H yes yes 6 0\n"
                )
            )
        if command[0] == "pdftotext":
            return types.SimpleNamespace(stdout=candidate_bbox if str(candidate) in command else reference_bbox)
        raise AssertionError(command)

    monkeypatch.setattr("fitcv.cv_generator.subprocess.run", fake_run)
    result = _validate_pdf_against_reference(
        candidate,
        reference,
        candidate_page_info="Pages: 1\nPage size: 594.96 x 841.92 pts (A4)\nPage rot: 0\n",
        work_dir=tmp_path,
    )

    assert result["status"] == "pass"
    assert result["errors"] == []

def test_pdf_reference_validation_ignores_candidate_specific_word_wrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "candidate.pdf"
    reference = tmp_path / "reference.pdf"
    candidate.write_bytes(b"candidate")
    reference.write_bytes(b"reference")
    reference_bbox = _structured_bbox_xml()
    candidate_bbox = _structured_bbox_xml(wrap_variant=True)

    def fake_run(command, **kwargs):
        if command[0] == "pdfinfo":
            return types.SimpleNamespace(
                stdout="Pages: 1\nPage size: 594.96 x 841.92 pts (A4)\nPage rot: 0\n"
            )
        if command[0] == "pdffonts":
            return types.SimpleNamespace(
                stdout=(
                    "name type encoding emb sub uni object ID\n"
                    "AAAAAA+Inter-SemiBold CID TrueType Identity-H yes yes yes 4 0\n"
                    "BAAAAA+Inter-Regular CID TrueType Identity-H yes yes yes 6 0\n"
                )
            )
        if command[0] == "pdftotext":
            return types.SimpleNamespace(stdout=candidate_bbox if str(candidate) in command else reference_bbox)
        raise AssertionError(command)

    monkeypatch.setattr("fitcv.cv_generator.subprocess.run", fake_run)
    result = _validate_pdf_against_reference(
        candidate,
        reference,
        candidate_page_info="Pages: 1\nPage size: 594.96 x 841.92 pts (A4)\nPage rot: 0\n",
        work_dir=tmp_path,
    )

    assert result["status"] == "pass"
    assert result["errors"] == []


def test_pdf_reference_validation_rejects_shifted_structural_column(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "candidate.pdf"
    reference = tmp_path / "reference.pdf"
    candidate.write_bytes(b"candidate")
    reference.write_bytes(b"reference")
    reference_bbox = _structured_bbox_xml()
    candidate_bbox = _structured_bbox_xml(bullet_x=52.0)

    def fake_run(command, **kwargs):
        if command[0] == "pdfinfo":
            return types.SimpleNamespace(
                stdout="Pages: 1\nPage size: 594.96 x 841.92 pts (A4)\nPage rot: 0\n"
            )
        if command[0] == "pdffonts":
            return types.SimpleNamespace(
                stdout=(
                    "name type encoding emb sub uni object ID\n"
                    "AAAAAA+Inter-SemiBold CID TrueType Identity-H yes yes yes 4 0\n"
                    "BAAAAA+Inter-Regular CID TrueType Identity-H yes yes yes 6 0\n"
                )
            )
        if command[0] == "pdftotext":
            return types.SimpleNamespace(stdout=candidate_bbox if str(candidate) in command else reference_bbox)
        raise AssertionError(command)

    monkeypatch.setattr("fitcv.cv_generator.subprocess.run", fake_run)
    result = _validate_pdf_against_reference(
        candidate,
        reference,
        candidate_page_info="Pages: 1\nPage size: 594.96 x 841.92 pts (A4)\nPage rot: 0\n",
        work_dir=tmp_path,
    )

    assert result["status"] == "fail"
    assert "rendered PDF column or bullet alignment differs from the reference" in result["errors"]


def test_invalid_mycvs_markdown_stops_before_pdf_conversion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("fitcv.cv_generator.shutil.which", lambda tool: f"/fake/{tool}")
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        raise AssertionError("converter must not run for invalid Markdown")

    monkeypatch.setattr("fitcv.cv_generator.subprocess.run", fake_run)
    with pytest.raises(ValueError, match="mycvs_v1 validation failed"):
        render_cv_native_acceptance(
            "---\n---\n\n# Candidate\n",
            {"cv": {"renderer": {"strategy": "mycvs_v1"}}},
            output_dir=tmp_path,
        )
    assert calls == []


def test_render_acceptance_rejects_pdf_missing_expected_records(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("fitcv.cv_generator.shutil.which", lambda tool: f"/fake/{tool}")
    document = _build_fixture(experience_count=1, bullets_per_experience=2, include_optional=True)

    def fake_run(command, **kwargs):
        if command[0] == "pandoc":
            output_path = Path(command[command.index("-o") + 1])
            output_path.write_bytes(b"fake-pdf")
            return types.SimpleNamespace(stdout="")
        if command[0] == "pdfinfo":
            return types.SimpleNamespace(stdout="Pages: 1\n")
        if command[0] == "pdftotext":
            return types.SimpleNamespace(stdout="Summary\nExperience\n")
        return types.SimpleNamespace(stdout="")

    monkeypatch.setattr("fitcv.cv_generator.subprocess.run", fake_run)
    result = render_cv_native_acceptance(document, CONFIG, output_dir=tmp_path)

    assert result["render_status"] == "fail"
    assert result["expected_text_status"] == "fail"
    assert result["record_visibility_status"] == "fail"
    assert any("Test Candidate" in error for error in result["expected_text_errors"])

def test_configured_missing_reference_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("fitcv.cv_generator.shutil.which", lambda tool: f"/fake/{tool}")
    document = build_empty_structured_cv(
        jd={"title": "Data Engineer"},
        profile={"name": "Jane Doe"},
        config={"cv": {"composition": {}}},
        fit_classification="strong",
    )
    document["sections"]["summary"] = {"text": "SQL and Python data engineering."}
    result = render_cv_native_acceptance(
        render_cv_markdown(document, {"cv": {"composition": {}}}),
        {
            "cv": {
                "renderer": {
                    "reference_pdf_path": str(tmp_path / "missing-reference.pdf")
                }
            }
        },
        output_dir=tmp_path,
    )

    assert result["render_status"] == "fail"
    assert result["page_fit_status"] == "fail"
    assert result["reference_layout_status"] == "fail"
    assert "configured reference PDF does not exist" in result["reference_layout_errors"]


def test_native_renderer_returns_final_one_page_acceptance(tmp_path: Path) -> None:
    result = render_cv_native_acceptance(
        _build_fixture(experience_count=1, bullets_per_experience=2, include_optional=True),
        CONFIG,
        output_dir=tmp_path,
    )

    assert result["renderer_status"] == "rendered"
    assert result["page_count"] == 1
    assert result["page_fit_status"] == "pass"
    assert re.fullmatch(r"[0-9a-f]{64}", result["artifact_checksum"])


def test_native_renderer_marks_overflow_as_not_fit(tmp_path: Path) -> None:
    result = render_cv_native_acceptance(
        _build_fixture(experience_count=12, bullets_per_experience=5, include_optional=True),
        CONFIG,
        output_dir=tmp_path,
    )

    assert result["renderer_status"] == "rendered"
    assert result["page_count"] > 1
    assert result["page_fit_status"] == "fail"


def test_cross_boundary_mycvs_pipeline_persists_only_accepted_one_page_artifact(tmp_path: Path) -> None:
    config = {
        "cv": {
            "preset": "mycvs",
            "renderer": {"strategy": "mycvs_v1"},
            "final_artifact_acceptance": {"enabled": True},
        }
    }
    profile = {
        "name": "Test Candidate",
        "headline": "Data Engineer",
        "revision": "profile-v1",
        "contact": {"email": "test@example.com"},
        "experiences": [
            {"id": "exp-1", "role": "Data Engineer", "company": "ACME", "start": "2020", "end": "2022"},
            {"id": "exp-2", "role": "Analyst", "company": "Beta", "start": "2018", "end": "2020"},
        ],
        "education": [{"degree": "MSc Data Science", "institution": "University of Berlin", "start": "2016", "end": "2018"}],
        "projects": [{"id": "project-1", "name": "Analytics Platform", "url": "https://github.com/example/analytics"}],
        "certifications": [{"id": "cert-1", "name": "Cloud Data Engineer", "issuer": "Example Institute", "year": "2024"}],
        "skills": [{"name": "SQL"}, {"name": "Python"}, {"name": "Power BI"}],
    }
    job = {
        "job_url": "https://example.com/jobs/data-engineer",
        "job_title": "Data Engineer",
        "required_skills": ["SQL", "Python"],
    }
    analysis = {
        "analysis_input_fingerprint": "analysis-1",
        "candidate_profile_revision": "profile-v1",
        "job_url": job["job_url"],
        "job_title": job["job_title"],
        "status": "ready_for_generation",
        "fit_classification": "strong",
        "job_snapshot": job,
        "canonical_profile": profile,
        "evidence_payload": [
            {
                "evidence_id": "ev-exp-1",
                "claim_id": "ev-exp-1",
                "text": "Built SQL pipelines for operational reporting.",
                "source_section": "experiences",
                "source_ref": "experiences/exp-1",
                "parent_id": "experience:exp-1",
                "parent_title": "Data Engineer at ACME",
            }
        ],
        "requirement_coverage": [
            {
                "requirement_instance_id": "required_skill:sql",
                "requirement": "SQL",
                "selected_support": "verified",
                "supporting_evidence_ids": ["ev-exp-1"],
            }
        ],
        "ranking_cv_handoff": {"handoff_fingerprint": "handoff-1", "candidate_profile_revision": "profile-v1"},
    }

    content_plan = build_cv_content_plan(analysis, job, config, profile)
    assert content_plan["baseline_profile_records"]["experiences"] == profile["experiences"]
    assert content_plan["selected_job_support"][0]["evidence_id"] == "ev-exp-1"
    assert content_plan["supported_job_claims"][0]["claim_id"] == "ev-exp-1"

    document = build_empty_structured_cv(jd=job, profile=profile, config=config, fit_classification="strong")
    document.update(
        {
            "job_url": job["job_url"],
            "profile_revision": "profile-v1",
            "ranking_cv_handoff": analysis["ranking_cv_handoff"],
            "composition_plan": content_plan,
        }
    )
    document["sections"].update(
        {
            "summary": {"text": "Data engineer with experience building reliable data systems and analytics workflows."},
            "experience": [
                {
                    "role": "Data Engineer",
                    "company": "ACME",
                    "start": "2020",
                    "end": "2022",
                    "overview": "Built reliable data systems for operational reporting.",
                    "bullets": [
                        "Built SQL pipelines for operational reporting.",
                        "Automated data quality checks.",
                        "Improved delivery reliability.",
                    ],
                },
                {
                    "role": "Analyst",
                    "company": "Beta",
                    "start": "2018",
                    "end": "2020",
                    "overview": "Delivered analysis for business decisions.",
                    "bullets": ["Produced recurring reports.", "Improved data accuracy."],
                },
            ],
            "education": [{"degree": "MSc Data Science", "institution": "University of Berlin", "start": "2016", "end": "2018"}],
            "projects": [
                {
                    "name": "Analytics Platform",
                    "url": "https://github.com/example/analytics",
                    "context": "Analytics platform.",
                    "overview": "Built an analytics platform for reporting.",
                    "bullets": ["Improved reporting reliability.", "Reduced manual work."],
                }
            ],
            "certifications": [{"name": "Cloud Data Engineer", "issuer": "Example Institute", "year": "2024"}],
            "skills": {"groups": [{"label": "Core", "items": ["SQL", "Python", "Power BI"]}]},
        }
    )

    markdown = serialize_mycvs_v1(document)
    validation = validate_mycvs_v1_markdown(markdown, content_plan=content_plan, expected_handoff="handoff-1")
    assert validation["valid"] is True
    visible_markdown = re.sub(r"<!--.*?-->", "", markdown, flags=re.DOTALL)
    assert "ev-exp-1" not in visible_markdown
    assert "Not provided" not in visible_markdown

    render_acceptance = render_cv_native_acceptance(document, config, output_dir=tmp_path, artifact_name="cross-boundary")
    assert render_acceptance["renderer_status"] == "rendered"
    assert render_acceptance["page_count"] == 1
    assert render_acceptance["page_fit_status"] == "pass"
    pdf_path = tmp_path / "cross-boundary.pdf"
    pdf_bytes = pdf_path.read_bytes()
    extracted_text = subprocess.run(["pdftotext", str(pdf_path), "-"], check=True, capture_output=True, text=True).stdout
    assert "Test Candidate" in extracted_text
    assert "Cloud Data Engineer" in extracted_text
    assert "Analytics Platform" in extracted_text

    generation_result = {
        "status": "review_required",
        "structured_cv_final": document,
        "markdown_final": markdown,
        "validation": validation,
        "render_acceptance": render_acceptance,
        "page_fit_status": "pass",
    }
    assert _is_persistable_cv_generation_result(generation_result, config, pdf_content=pdf_bytes)
    persisted_event = accepted_cv_artifact_event_v1(
        artifact_id="cross-boundary-cv",
        job_url=job["job_url"],
        run_id="run-1",
        run_job_id="run-job-1",
        acceptance_mode="automatic",
        accepted_at="2026-11-23T00:00:00Z",
        finalized_at="2026-11-23T00:00:00Z",
        generation_input_fingerprint=content_plan["content_fingerprint"],
        page_fit_status="pass",
        render_acceptance=render_acceptance,
    )
    assert persisted_event["render_proof_status"] == "verified"

"""Native rendered-artifact acceptance checks for representative CVs."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from fitcv.cv_generator import build_empty_structured_cv, render_cv_markdown, render_cv_native_acceptance


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

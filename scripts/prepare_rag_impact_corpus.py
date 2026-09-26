"""Build and validate the offline RAG-impact benchmark corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any


SEED = 20260925
CORPUS_VERSION = "rag-impact-corpus-v1"
PII = re.compile(r"(?:https?://|www\.)\S+|\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|(?:\+|00)\d[\d ()/-]{7,}\d|\b\d{3}[ -]\d{3}[ -]\d{4}\b", re.I)
ALLOWED = (
    "job_id", "title", "description", "location", "company_name",
    "work_mode", "contract_type", "experience_level", "job_function",
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text(value: Any) -> str:
    return str(value or "").strip()


def sanitize_job(record: dict[str, Any]) -> dict[str, str]:
    def clean(value: Any, default: str = "") -> str:
        return re.sub(r"\s+", " ", PII.sub("", _text(value))).strip() or default

    return {
        "job_id": clean(record.get("id")),
        "title": clean(record.get("title")),
        "description": clean(record.get("description")),
        "location": clean(record.get("location")),
        "company_name": clean(record.get("companyName")),
        "work_mode": clean(record.get("workType"), "unspecified"),
        "contract_type": clean(record.get("contractType"), "unspecified"),
        "experience_level": clean(record.get("experienceLevel"), "unspecified"),
        "job_function": clean(record.get("jobFunction"), "unspecified"),
    }


def _language(text: str) -> str:
    german = len(re.findall(r"\b(?:und|der|die|das|für|mit|von|dein|eine)\b", text.casefold()))
    english = len(re.findall(r"\b(?:and|the|with|for|your|you|our)\b", text.casefold()))
    return "german" if german > english else "english"


def _length_bucket(length: int) -> str:
    return "short" if length < 1800 else "medium" if length < 4000 else "long"


def _requirements(job: dict[str, str], labels: dict[str, Any]) -> list[dict[str, Any]]:
    text = f"{job['title']} {job['description']}".casefold()
    matches = [
        (requirement_id, label)
        for requirement_id, label in labels.items()
        if str(label.get("canonical_requirement", "")).casefold() in text
    ]
    if not matches:
        matches = [next(iter(labels.items()))]
    return [
        {
            "requirement_id": requirement_id,
            "canonical_requirement": label["canonical_requirement"],
            "answerable": bool(label.get("answerable")),
            "approved_evidence_ids": list(label.get("approved_evidence_ids", [])),
        }
        for requirement_id, label in matches[:3]
    ]


def _case(job: dict[str, str], split: str, index: int, labels: dict[str, Any]) -> dict[str, Any]:
    text = f"{job['title']} {job['description']}"
    requirements = _requirements(job, labels)
    required_skills = [str(item["canonical_requirement"]) for item in requirements]
    difficulty = "easy" if len(requirements) == 1 else "hard" if len(requirements) == 3 else "medium"
    return {
        **job,
        "required_skills": required_skills,
        "required_skills_canonical": required_skills,
        "required_skill_entities": [
            {"raw_text": skill, "canonical": skill} for skill in required_skills
        ],
        "scenario_id": f"{split}-{index:02d}",
        "source_job_id": job["job_id"],
        "difficulty": difficulty,
        "scenario_rationale": "deterministic source-job pairing across lexical and length strata",
        "strata": {
            "language_signal": _language(text),
            "work_mode": job["work_mode"],
            "experience_level": job["experience_level"],
            "description_length": _length_bucket(len(job["description"])),
        },
        "requirements": requirements,
        "context_difference": {
            "full_profile_evidence_count": 6,
            "fitcv_evidence_count": 3 if index % 4 else 6,
            "fitcv_uses_less_evidence": index % 4 != 0,
            "expected_generation_input_reduction": index % 4 != 0,
        },
    }


def prepare_corpus(source_path: Path, base_fixture_path: Path, seed: int = SEED) -> dict[str, Any]:
    records = json.loads(source_path.read_text(encoding="utf-8"))
    base = json.loads(base_fixture_path.read_text(encoding="utf-8"))
    if not isinstance(records, list) or len(records) != 100:
        raise ValueError("source must contain exactly 100 job records")
    jobs = [sanitize_job(record) for record in records]
    if any(not job["job_id"] for job in jobs) or len({job["job_id"] for job in jobs}) != 100:
        raise ValueError("source jobs must have unique IDs")
    rng = random.Random(seed)
    rng.shuffle(jobs)
    jobs.sort(key=lambda job: (
        job["experience_level"],
        _language(job["description"]),
        _length_bucket(len(job["description"])),
        rng.random(),
        job["job_id"],
    ))
    selected = jobs[:40]
    splits = {"development": selected[:10], "pilot": selected[10:20], "held_out": selected[20:40]}
    derived = dict(base)
    derived.update({
        "corpus_version": CORPUS_VERSION,
        "source_sha256": sha256_file(source_path),
        "profile_sha256": fingerprint(base["candidate_profile"]),
        "corpus_seed": seed,
        "jobs": {
            split: [_case(job, split, index, base["requirement_labels"]) for index, job in enumerate(items, 1)]
            for split, items in splits.items()
        },
    })
    derived["corpus_sha256"] = fingerprint(derived["jobs"])
    derived["thresholds"] = {
        **derived.get("thresholds", {}),
        "max_mean_human_quality_loss": 0.25,
        "held_out_generation_input_reduction_fraction": 0.8,
    }
    return derived


def validate_corpus(fixture: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    jobs = fixture.get("jobs")
    if not isinstance(jobs, dict):
        return ["jobs must be an object"]
    expected = {"development": 10, "pilot": 10, "held_out": 20}
    seen: set[str] = set()
    reduced = 0
    for split, count in expected.items():
        cases = jobs.get(split)
        if not isinstance(cases, list) or len(cases) != count:
            errors.append(f"jobs.{split} must contain {count} cases")
            continue
        for case in cases:
            if not isinstance(case, dict) or not set(ALLOWED).issubset(case):
                errors.append(f"{split} contains malformed case")
                continue
            scenario_id = str(case.get("scenario_id", ""))
            if scenario_id in seen:
                errors.append(f"duplicate scenario_id {scenario_id}")
            seen.add(scenario_id)
            blob = json.dumps(case, ensure_ascii=False)
            if PII.search(blob):
                errors.append(f"PII in {scenario_id}")
            if case.get("context_difference", {}).get("fitcv_uses_less_evidence"):
                reduced += 1
            for requirement in case.get("requirements", []):
                if not set(requirement.get("approved_evidence_ids", [])).issubset(_evidence_ids(fixture)):
                    errors.append(f"unknown approved evidence in {scenario_id}")
    if len(seen) != 40:
        errors.append("scenario count must be 40")
    if reduced < 10:
        errors.append("context-difference minimum is 10")
    if fixture.get("profile_sha256") != fingerprint(fixture.get("candidate_profile")):
        errors.append("profile fingerprint drift")
    if fixture.get("corpus_sha256") != fingerprint(fixture.get("jobs")):
        errors.append("corpus fingerprint drift")
    return errors


def _evidence_ids(fixture: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for section in fixture.get("candidate_profile", {}).values():
        for item in section if isinstance(section, list) else []:
            ids.update(str(evidence.get("id")) for evidence in item.get("evidence", []))
    return ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--base-fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    corpus = prepare_corpus(args.input, args.base_fixture, args.seed)
    errors = validate_corpus(corpus)
    if errors:
        raise SystemExit("\n".join(errors))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(corpus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_sha256": corpus["source_sha256"], "split_counts": {key: len(value) for key, value in corpus["jobs"].items()}, "corpus_sha256": corpus["corpus_sha256"]}, indent=2))


if __name__ == "__main__":
    main()

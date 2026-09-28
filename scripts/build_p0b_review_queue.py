"""Build a bounded, deterministic P0-B requirement review queue."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

QUEUE_FIELDS = (
    "source_id",
    "job_language",
    "requirement_text",
    "requirement_instance_id",
    "split",
    "queue_status",
    "requirement_type",
    "provenance",
)
TAXONOMY = (
    "education",
    "language",
    "citizenship",
    "availability",
    "cognitive_ability",
    "technical_exposure",
)
LANGUAGES = ("de", "en")
SPLITS = ("calibration", "held_out")
DEFAULT_MAX_ROWS = 100
HEADING_RE = re.compile(r"^[^*•\-–—\d][^\n]{0,140}(?::|[A-ZÄÖÜ][A-ZÄÖÜ\s/&,-]{3,})$")
BULLET_RE = re.compile(r"^(?:[*•]|[-–—]|\d+[.)])\s+(.*)$")
REQUIREMENT_HEADING_MARKERS = (
    "bringst du mit",
    "mitbring",
    "profil",
    "skillset",
    "skills and experience",
    "your talent",
    "what we are looking for",
    "what makes you stand out",
    "must-have",
    "nice-to-have",
    "must haves",
    "nice to haves",
    "must-haves",
    "nice-to-haves",
    "competen",
    "qualifications",
    "requirements",
    "verfügbar",
    "verfugb",
    "availability",
    "you are good at",
    "you’re good at",
    "you're good at",
    "this internship is ideal for",
    "in addition, here are the skills",
)
TYPE_MARKERS = {
    "citizenship": (
        "citizenship",
        "nationality",
        "eu citizen",
        "work authorization",
        "work permit",
        "visa",
        "staatsbürgerschaft",
        "staatsangehör",
        "aufenthalts",
        "arbeitsgenehm",
    ),
    "language": (
        "english",
        "german",
        "language",
        "fluent",
        "native",
        "deutsch",
        "englisch",
        "sprach",
        "sprachniveau",
        "c1",
        "c2",
        "b2",
    ),
    "availability": (
        "available",
        "availability",
        "hours per week",
        "starting",
        "start date",
        "duration",
        "commit",
        "verfügbarkeit",
        "monat",
        "stunden",
        "ab sofort",
        "beginn",
        "dauer",
        "deine zeit:",
    ),
    "education": (
        "degree",
        "student",
        "studying",
        "study",
        "university",
        "college",
        "bachelor",
        "master",
        "graduate",
        "education",
        "academic",
        "school",
        "studium",
        "studierst",
        "abschluss",
        "hochschul",
        "ausgebildet",
        "fachrichtung",
    ),
    "technical_exposure": (
        "sql",
        "python",
        "excel",
        "sap",
        "erp",
        "api",
        "cad",
        "plm",
        "bim",
        "adobe",
        "office",
        "technical",
        "technik",
        "technisch",
        "maschinen",
        "elektronik",
        "it-affinit",
        "programming",
        "modeling",
        "modelling",
        "software",
        "tool",
        "data analytics",
    ),
    "cognitive_ability": (
        "problem-solving",
        "problem solving",
        "critical thinking",
        "communicat",
        "team",
        "teamplayer",
        "organized",
        "organisation",
        "organization",
        "initiative",
        "independent",
        "selbstständig",
        "eigenmotivation",
        "verantwortungs",
        "strateg",
        "analytical",
        "analyt",
        "curious",
        "neugier",
        "serviceorient",
        "reliable",
        "zuverläss",
        "hands-on",
        "responsibility",
        "eigeninitiative",
        "lösungs",
        "flexib",
        "mobilität",
        "engagement",
        "interest",
        "interesse",
    ),
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        rows.append(value)
    return rows


def _p0a_sources(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    sources: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        if row.get("reviewed") is not True:
            continue
        source_id = str(row.get("source_id") or "").strip()
        language = str(row.get("language") or "").strip()
        split = str(row.get("split") or "").strip()
        if not source_id or language not in LANGUAGES or split not in SPLITS:
            continue
        key = (source_id, language)
        existing = sources.get(key)
        if existing is not None and existing.get("job_id") != row.get("job_id"):
            raise ValueError(f"conflicting P0-A source rows for {key!r}")
        sources[key] = row
    return sources


def _requirement_type(text: str) -> str | None:
    lowered = text.casefold()
    for requirement_type in TAXONOMY:
        if any(marker in lowered for marker in TYPE_MARKERS[requirement_type]):
            return requirement_type
    return None


def _is_requirement_heading(line: str) -> bool:
    lowered = line.casefold()
    return bool(HEADING_RE.fullmatch(line)) and any(
        marker in lowered for marker in REQUIREMENT_HEADING_MARKERS
    )


def _text_key(text: str) -> str:
    return " ".join(text.casefold().split())


def _source_provenance(
    *,
    source: dict[str, Any] | None,
    fallback: dict[str, Any] | None,
    source_file: str,
    source_id: str,
    source_section: str | None,
    bullet_ordinal: int | None,
) -> dict[str, Any]:
    requirement = (fallback or {}).get("provenance", {}).get("requirement", {})
    if source is not None:
        values = {
            "source_file": source_file,
            "source_record_id": source_id,
            "source_field": "description",
            "job_title": str(source.get("title") or ""),
            "source_url": str(source.get("source_job_url") or source.get("job_url") or ""),
        }
    else:
        values = {
            "source_file": str(requirement.get("source_file") or source_file),
            "source_record_id": source_id,
            "source_field": str(requirement.get("source_field") or "description"),
            "job_title": str(requirement.get("job_title") or ""),
            "source_url": str(requirement.get("source_url") or ""),
        }
    values["source_section"] = source_section
    values["source_bullet_ordinal"] = bullet_ordinal
    return values


def _derive_candidates(
    sources: dict[tuple[str, str], dict[str, Any]],
    *,
    source_file: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    candidates: list[dict[str, Any]] = []
    diagnostics = Counter()
    for (source_id, language), source in sorted(sources.items()):
        lines = str(source.get("description") or "").replace("\r", "").splitlines()
        for line_index, line in enumerate(lines):
            heading = line.strip()
            if not _is_requirement_heading(heading):
                continue
            diagnostics["requirement_sections"] += 1
            bullet_ordinal = 0
            for following in lines[line_index + 1 :]:
                text_line = following.strip()
                if text_line and HEADING_RE.fullmatch(text_line):
                    break
                match = BULLET_RE.fullmatch(text_line)
                if match is None:
                    continue
                requirement_text = match.group(1).strip()
                if len(requirement_text) < 20:
                    diagnostics["short_bullets"] += 1
                    continue
                bullet_ordinal += 1
                requirement_type = _requirement_type(requirement_text)
                if requirement_type is None:
                    diagnostics["unclassified_bullets"] += 1
                    continue
                identity = "|".join(
                    (source_id, language, str(source.get("split") or ""), heading, str(bullet_ordinal), requirement_text)
                )
                requirement_instance_id = (
                    f"req_{source_id}_candidate_{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:12]}"
                )
                candidates.append(
                    {
                        "source_id": source_id,
                        "job_language": language,
                        "requirement_text": requirement_text,
                        "requirement_instance_id": requirement_instance_id,
                        "split": str(source.get("split") or ""),
                        "queue_status": "queued",
                        "requirement_type": requirement_type,
                        "provenance": _source_provenance(
                            source=source,
                            fallback=None,
                            source_file=source_file,
                            source_id=source_id,
                            source_section=heading,
                            bullet_ordinal=bullet_ordinal,
                        ),
                    }
                )
                diagnostics["classified_bullets"] += 1
    candidates.sort(key=_queue_sort_key)
    diagnostics["candidate_instances_before_deduplication"] = len(candidates)
    return candidates, dict(sorted(diagnostics.items()))


def _queue_sort_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row["source_id"]),
        str(row["job_language"]),
        str(row["split"]),
        str(row["requirement_instance_id"]),
        _text_key(str(row["requirement_text"])),
    )


def _stratum_targets(
    sources: dict[tuple[str, str], dict[str, Any]],
    max_rows: int,
) -> dict[tuple[str, str], int]:
    counts = Counter((language, str(source.get("split") or "")) for _, language in sources for source in [sources[(_, language)]])
    total = sum(counts.values())
    if not total:
        return {}
    raw = {stratum: count * max_rows / total for stratum, count in counts.items()}
    targets = {stratum: int(value) for stratum, value in raw.items()}
    remainder = max_rows - sum(targets.values())
    for stratum in sorted(raw, key=lambda key: (-(raw[key] - targets[key]), key))[:remainder]:
        targets[stratum] += 1
    return targets


def _select_candidates(
    preserved: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    sources: dict[tuple[str, str], dict[str, Any]],
    *,
    max_rows: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(preserved) > max_rows:
        raise ValueError(f"preserved requirement instances exceed max_rows={max_rows}")
    targets = _stratum_targets(sources, max_rows)
    preserved_counts = Counter((row["job_language"], row["split"]) for row in preserved)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        grouped[(candidate["job_language"], candidate["split"])].append(candidate)

    selected: list[dict[str, Any]] = []
    strata_diagnostics: dict[str, dict[str, int]] = {}
    for stratum in sorted(grouped):
        target = targets.get(stratum, 0)
        needed = max(0, target - preserved_counts[stratum])
        chosen = grouped[stratum][:needed]
        selected.extend(chosen)
        strata_diagnostics[f"{stratum[0]}:{stratum[1]}"] = {
            "target": target,
            "preserved": preserved_counts[stratum],
            "derived_selected": len(chosen),
            "derived_available": len(grouped[stratum]),
            "shortfall": max(0, needed - len(chosen)),
        }

    remaining = max_rows - len(preserved) - len(selected)
    if remaining > 0:
        chosen_ids = {row["requirement_instance_id"] for row in selected}
        for candidate in candidates:
            if remaining == 0:
                break
            if candidate["requirement_instance_id"] in chosen_ids:
                continue
            selected.append(candidate)
            chosen_ids.add(candidate["requirement_instance_id"])
            remaining -= 1

    queue = sorted(preserved + selected, key=_queue_sort_key)
    diagnostics = {
        "strata": strata_diagnostics,
        "cap": max_rows,
        "selected_derived_candidates": len(selected),
        "unfilled_capacity": max(0, max_rows - len(queue)),
    }
    return queue, diagnostics


def build_queue(
    p0a_rows: list[dict[str, Any]],
    p0b_rows: list[dict[str, Any]],
    *,
    max_rows: int = DEFAULT_MAX_ROWS,
    p0a_source_file: str = "data/fitcv-p0-corpus/p0a/raw_postings_de_en.jsonl",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if max_rows < 1 or max_rows > DEFAULT_MAX_ROWS:
        raise ValueError(f"max_rows must be between 1 and {DEFAULT_MAX_ROWS}")

    sources = _p0a_sources(p0a_rows)
    preserved_by_id: dict[str, dict[str, Any]] = {}
    unmatched_source_ids: set[str] = set()
    for row in p0b_rows:
        if row.get("review_status") != "reviewed":
            continue
        requirement = row.get("provenance", {}).get("requirement", {})
        source_id = str(requirement.get("source_record_id") or "").strip()
        language = str(row.get("language") or "").strip()
        requirement_text = str(row.get("requirement_text") or "").strip()
        requirement_instance_id = str(row.get("requirement_instance_id") or "").strip()
        split = str(row.get("split") or "").strip()
        if not all((source_id, requirement_text, requirement_instance_id, split)):
            raise ValueError("reviewed P0-B row is missing required source or requirement fields")
        if language not in LANGUAGES or split not in SPLITS:
            raise ValueError(f"unsupported P0-B language or split: {language!r}, {split!r}")
        source = sources.get((source_id, language))
        if source is None:
            unmatched_source_ids.add(source_id)
        queue_row = {
            "source_id": source_id,
            "job_language": language,
            "requirement_text": requirement_text,
            "requirement_instance_id": requirement_instance_id,
            "split": split,
            "queue_status": "queued",
            "requirement_type": _requirement_type(requirement_text),
            "provenance": _source_provenance(
                source=source,
                fallback=row,
                source_file=p0a_source_file,
                source_id=source_id,
                source_section=None,
                bullet_ordinal=None,
            ),
        }
        if queue_row["requirement_type"] not in TAXONOMY:
            raise ValueError(f"cannot classify preserved requirement {requirement_instance_id!r}")
        previous = preserved_by_id.get(requirement_instance_id)
        if previous is not None and previous != queue_row:
            raise ValueError(f"conflicting P0-B rows for {requirement_instance_id!r}")
        preserved_by_id[requirement_instance_id] = queue_row

    preserved = sorted(preserved_by_id.values(), key=_queue_sort_key)
    candidates, extraction_diagnostics = _derive_candidates(sources, source_file=p0a_source_file)
    preserved_keys = {
        (row["source_id"], row["job_language"], _text_key(row["requirement_text"]))
        for row in preserved
    }
    candidates = [
        row
        for row in candidates
        if (row["source_id"], row["job_language"], _text_key(row["requirement_text"])) not in preserved_keys
    ]
    queue, selection_diagnostics = _select_candidates(
        preserved,
        candidates,
        sources,
        max_rows=max_rows,
    )
    assert len(queue) <= max_rows
    assert len(queue) == len({row["requirement_instance_id"] for row in queue})
    assert all(row["queue_status"] == "queued" for row in queue)
    assert all(row["requirement_type"] in TAXONOMY for row in queue)
    assert all(tuple(row) == QUEUE_FIELDS for row in queue)
    assert not any("verdict" in json.dumps(row, ensure_ascii=False) for row in queue)
    diagnostics = {
        "p0a_reviewed_jobs": len(sources),
        "p0b_preserved_reviewed_instances": len(preserved),
        "derived_candidates_available": len(candidates),
        "unmatched_p0a_source_ids": sorted(unmatched_source_ids),
        "extraction": extraction_diagnostics,
        "selection": selection_diagnostics,
    }
    return queue, diagnostics


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=False, separators=(",", ":")) + "\n"
        for row in rows
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8", newline="\n")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _manifest(
    *,
    p0a_path: Path,
    p0b_path: Path,
    output_path: Path,
    queue: list[dict[str, Any]],
    queue_sha256: str,
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "p0b.requirement_instances.v2",
        "status": "review_queue",
        "inputs": {
            "p0a_jobs": p0a_path.as_posix(),
            "p0b_reviewed_rows": p0b_path.as_posix(),
        },
        "output": output_path.as_posix(),
        "sha256": queue_sha256,
        "max_rows": DEFAULT_MAX_ROWS,
        "counts": {
            "queue_instances": len(queue),
            "preserved_reviewed_instances": diagnostics["p0b_preserved_reviewed_instances"],
            "derived_candidate_instances": diagnostics["selection"]["selected_derived_candidates"],
            "source_jobs": len({row["source_id"] for row in queue}),
            "queue_status": dict(sorted(Counter(row["queue_status"] for row in queue).items())),
            "languages": dict(sorted(Counter(row["job_language"] for row in queue).items())),
            "splits": dict(sorted(Counter(row["split"] for row in queue).items())),
            "requirement_types": dict(sorted(Counter(row["requirement_type"] for row in queue).items())),
        },
        "fields": list(QUEUE_FIELDS),
        "diagnostics": diagnostics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p0a", type=Path, default=Path("data/fitcv-p0-corpus/p0a/raw_postings_de_en.jsonl"))
    parser.add_argument("--p0b", type=Path, default=Path("data/fitcv-p0-corpus/p0b/reviewed_requirement_evidence.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("data/fitcv-p0-corpus/p0b/requirement_instances.jsonl"))
    parser.add_argument("--manifest", type=Path, default=Path("data/fitcv-p0-corpus/p0b/requirement_instances_manifest.json"))
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    args = parser.parse_args()

    p0a_rows = _read_jsonl(args.p0a)
    p0b_rows = _read_jsonl(args.p0b)
    queue, diagnostics = build_queue(
        p0a_rows,
        p0b_rows,
        max_rows=args.max_rows,
        p0a_source_file=args.p0a.as_posix(),
    )
    queue_sha256 = _write_jsonl(args.output, queue)
    manifest = _manifest(
        p0a_path=args.p0a,
        p0b_path=args.p0b,
        output_path=args.output,
        queue=queue,
        queue_sha256=queue_sha256,
        diagnostics=diagnostics,
    )
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {len(queue)} requirement instances to {args.output}")
    print(f"wrote manifest to {args.manifest}")


if __name__ == "__main__":
    main()

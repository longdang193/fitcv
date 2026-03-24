"""Gap analysis — classify skill and experience fit between a candidate and a job.

Public API
----------
compute_gap        : classify required skills into matched/partial/missing + flag risks
classify_fit       : map a gap result to a fit label (strong/stretch/skip)
store_gap_analysis : persist gap result to BigQuery (integration)
"""

import re
from datetime import datetime, timezone
from typing import Any

from fitcv.rule_filter import _canonicalise_skill


# ── config defaults ───────────────────────────────────────────────────────────

_DEFAULT_STRONG_RATIO: float = 0.80
_DEFAULT_STRETCH_RATIO: float = 0.50

# Keywords that signal a leadership/ownership requirement in the JD.
_LEADERSHIP_KEYWORDS: frozenset[str] = frozenset({
    "lead", "leading", "leadership", "owns", "ownership",
    "manage", "managing", "manager", "director", "head of",
})


# ── internal helpers ──────────────────────────────────────────────────────────

def _parse_years_minimum(years_required: Any) -> int | None:
    """Parse years_required to an integer minimum.

    Handles:
    - None / 0   → None  (unknown; no penalty)
    - int        → int
    - "3-5"      → 3     (minimum of range)
    - other str  → int() if parseable, else None
    """
    if years_required is None:
        return None
    if isinstance(years_required, (int, float)):
        val = int(years_required)
        return None if val == 0 else val
    raw = str(years_required).strip()
    match = re.match(r"^(\d+)\s*[-–]\s*\d+$", raw)
    if match:
        return int(match.group(1))
    try:
        val = int(raw)
        return None if val == 0 else val
    except ValueError:
        return None


def _compute_years_risk(
    years_required: Any,
    years_candidate: int | float | None,
) -> bool:
    """Return True only when both sides are known and candidate falls short."""
    min_required = _parse_years_minimum(years_required)
    if min_required is None or years_candidate is None:
        return False
    return int(years_candidate) < min_required


def _has_leadership_claim(candidate_evidence: list[str]) -> bool:
    """Return True when any evidence string contains a leadership keyword."""
    lowered = " ".join(candidate_evidence).lower()
    return any(kw in lowered for kw in _LEADERSHIP_KEYWORDS)


# ── gap computation ───────────────────────────────────────────────────────────

def compute_gap(
    required_skills: list[str],
    candidate_skills: list[str],
    years_required: Any,
    years_candidate: int | float | None,
    config: dict[str, Any] | None = None,
    candidate_evidence: list[str] | None = None,
) -> dict[str, Any]:
    """Classify required skills into matched / partial / missing and flag risks.

    A skill is ``partial`` when:
    - The candidate has it only via a synonym match (e.g. GCP → Google Cloud)
    - The candidate skill string is a case-insensitive substring of the required skill
      (e.g. "dbt" satisfies "dbt core")

    A skill is ``matched`` when the canonical forms are identical.

    ``overclaim_risk`` entries are added when:
    - years_candidate < years_required
    - JD leadership keywords present but candidate evidence has none

    Returns a dict with keys:
        matched, partial, missing (lists of skill strings using required_skill label)
        years_risk (bool)
        overclaim_risk (list[str])
    """
    matched: list[str] = []
    partial: list[str] = []
    missing: list[str] = []

    candidate_canonical_to_raw: dict[str, list[str]] = {}
    for s in candidate_skills:
        canon = _canonicalise_skill(s, config)
        candidate_canonical_to_raw.setdefault(canon, []).append(s.strip().lower())

    candidate_canonical_set = set(candidate_canonical_to_raw.keys())
    candidate_raw_lower = {s.strip().lower() for s in candidate_skills}

    for req in required_skills:
        req_lower = req.strip().lower()
        req_canonical = _canonicalise_skill(req, config)

        # Exact raw-string match (case-insensitive): → matched
        if req_lower in candidate_raw_lower:
            matched.append(req)
            continue

        # Synonym match: canonicals agree but raw strings differ → partial
        if req_canonical in candidate_canonical_set:
            partial.append(req)
            continue

        # Subset match: candidate raw term is contained in required term → partial
        # e.g. "dbt" satisfies "dbt core"
        subset_hit = any(
            cand_raw in req_lower
            for raw_list in candidate_canonical_to_raw.values()
            for cand_raw in raw_list
        )
        if subset_hit:
            partial.append(req)
        else:
            missing.append(req)


    years_risk = _compute_years_risk(years_required, years_candidate)

    overclaim_risk: list[str] = []
    if years_risk:
        years_min = _parse_years_minimum(years_required)
        overclaim_risk.append(
            f"years_gap: candidate has {years_candidate} years, {years_min} required"
        )

    if candidate_evidence is not None:
        # Check for leadership requirement in required skills
        all_req_text = " ".join(required_skills).lower()
        if any(kw in all_req_text for kw in _LEADERSHIP_KEYWORDS):
            if not _has_leadership_claim(candidate_evidence):
                overclaim_risk.append("leadership: JD requires leadership but no matching evidence")

    return {
        "matched": matched,
        "partial": partial,
        "missing": missing,
        "years_risk": years_risk,
        "overclaim_risk": overclaim_risk,
    }


# ── fit classification ────────────────────────────────────────────────────────

def classify_fit(
    gap: dict[str, Any],
    required_count: int,
    config: dict[str, Any] | None = None,
) -> str:
    """Map a gap result to a fit label.

    Reads thresholds from ``config["gap_thresholds"]`` with built-in defaults:
    - strong_min_matched_ratio: 0.80  (≥80% matched → strong)
    - stretch_min_matched_ratio: 0.50 (50–79% → stretch; <50% → skip)

    Returns "strong", "stretch", or "skip".
    """
    thresholds = (config or {}).get("gap_thresholds", {})
    strong_min: float = float(thresholds.get("strong_min_matched_ratio", _DEFAULT_STRONG_RATIO))
    stretch_min: float = float(thresholds.get("stretch_min_matched_ratio", _DEFAULT_STRETCH_RATIO))

    if required_count == 0:
        return "strong"

    matched_ratio = len(gap.get("matched") or []) / required_count

    if matched_ratio >= strong_min:
        return "strong"
    if matched_ratio >= stretch_min:
        return "stretch"
    return "skip"


# ── integration: store to bigquery ────────────────────────────────────────────

def store_gap_analysis(
    job_id: str,
    gap: dict[str, Any],
    config: dict[str, Any],
) -> None:
    """Insert a gap analysis row into fitcv.gap_analysis.

    Requires GOOGLE_APPLICATION_CREDENTIALS.
    Decorated with @pytest.mark.integration in tests.
    """
    from google.cloud import bigquery  # type: ignore[import-not-found]
    from google.oauth2 import service_account  # type: ignore[import-not-found]

    project = str(config["gcp_project"])
    dataset = str(config["bigquery_dataset"])
    key_path = str(config["service_account_key"])

    credentials = service_account.Credentials.from_service_account_file(key_path)
    client = bigquery.Client(project=project, credentials=credentials)
    table_ref = f"{project}.{dataset}.gap_analysis"
    now = datetime.now(tz=timezone.utc).isoformat()

    row = {
        "job_url": str(job_id),
        "matched_skills": list(gap.get("matched") or []),
        "partial_skills": list(gap.get("partial") or []),
        "missing_skills": list(gap.get("missing") or []),
        "years_risk": bool(gap.get("years_risk", False)),
        "overclaim_risk": list(gap.get("overclaim_risk") or []),
        "analysed_at": now,
    }

    errors = client.insert_rows_json(table_ref, [row])
    if errors:
        raise RuntimeError(f"BigQuery insert errors for gap_analysis: {errors}")

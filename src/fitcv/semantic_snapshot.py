"""@meta
name: semantic_snapshot
type: module
domain: runtime
ownership: feature
capabilities:
  - pipeline_performance.enrich-stage-raw-plus-canonical-semantic-companions-for-repeated-downstream-fields
responsibility:
  - Compile effective semantic policy and resolve subject semantic snapshots.
inputs:
  - Effective run configuration and normalized raw semantic fields
outputs:
  - Deterministic semantic policy, snapshots, and bounded projections
lifecycle:
  - status: active
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any, Literal

from fitcv.shortlist_runtime import build_contract_fingerprint

SEMANTIC_POLICY_SCHEMA_VERSION = "semantic_policy_v2"
SEMANTIC_SNAPSHOT_SCHEMA_VERSION = "semantic_snapshot_v1"
SEMANTIC_RESOLVER_CONTRACT_VERSION = "semantic_resolver_v2"

_SUPPORTED_POLICY_CONTRACTS = {
    ("semantic_policy_v1", "semantic_resolver_v1"),
    (SEMANTIC_POLICY_SCHEMA_VERSION, SEMANTIC_RESOLVER_CONTRACT_VERSION),
}

SubjectKind = Literal["job", "candidate", "criteria"]

_FIELD_CONTRACTS: dict[SubjectKind, dict[str, tuple[str, str]]] = {
    "job": {
        "required_skills": ("skill", "list"),
        "preferred_skills": ("skill", "list"),
        "domain": ("domain", "scalar"),
        "job_family": ("role_family", "scalar"),
    },
    "candidate": {"candidate_skills": ("skill", "list")},
    "criteria": {"must_have_skills": ("skill", "list")},
}


def _normalize_skill(value: object) -> str:
    return str(value or "").strip().lower()


def _normalize_role_text(value: object) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9_]+", " ", str(value or "").lower())).strip()


def _normalize(value: object, taxonomy: str) -> str:
    return _normalize_skill(value) if taxonomy == "skill" else _normalize_role_text(value)


def _compile_map(raw_map: object, taxonomy: str) -> dict[str, str]:
    if not isinstance(raw_map, Mapping):
        return {}
    compiled: dict[str, str] = {}
    for raw_alias, raw_canonical in raw_map.items():
        alias = _normalize(raw_alias, taxonomy)
        canonical = _normalize(raw_canonical, taxonomy)
        if not alias or not canonical:
            continue
        previous = compiled.get(alias)
        if previous is not None and previous != canonical:
            raise ValueError(f"{taxonomy} normalized alias collision: {alias}")
        compiled[alias] = canonical
    states: dict[str, int] = {}

    def visit(alias: str) -> str:
        state = states.get(alias, 0)
        if state == 1:
            raise ValueError(f"{taxonomy} synonym cycle is not supported: {alias}")
        if state == 2:
            return compiled[alias]
        states[alias] = 1
        canonical = compiled.get(alias)
        if canonical and canonical != alias and canonical in compiled:
            canonical = visit(canonical)
            compiled[alias] = canonical
        states[alias] = 2
        return compiled[alias]

    for alias in compiled:
        visit(alias)
    return dict(sorted(compiled.items()))


def compile_semantic_policy(config: Mapping[str, object]) -> dict[str, Any]:
    maps = {
        "skill": _compile_map(config.get("skill_synonyms"), "skill"),
        "domain": _compile_map(config.get("domain_alias_map"), "domain"),
        "role_family": _compile_map(config.get("role_family_alias_map"), "role_family"),
    }
    payload = {
        "schema_version": SEMANTIC_POLICY_SCHEMA_VERSION,
        "resolver_contract_version": SEMANTIC_RESOLVER_CONTRACT_VERSION,
        "maps": maps,
    }
    return {**payload, "policy_fingerprint": build_contract_fingerprint(payload)}

def _resolver_contract_version(policy: Mapping[str, Any]) -> str:
    schema_version = str(policy.get("schema_version") or "")
    resolver_version = str(policy.get("resolver_contract_version") or "")
    if (schema_version, resolver_version) not in _SUPPORTED_POLICY_CONTRACTS:
        raise ValueError(
            f"unsupported semantic policy contract: {schema_version}/{resolver_version}"
        )
    return resolver_version


def _normalized_list(values: object, taxonomy: str) -> list[str] | None:
    if not isinstance(values, (list, tuple, set, frozenset)):
        return None
    return sorted({normalized for value in values if (normalized := _normalize(value, taxonomy))})


def _resolve_value(value: str, taxonomy: str, policy: Mapping[str, Any]) -> str:
    _resolver_contract_version(policy)
    maps = policy.get("maps")
    taxonomy_map = maps.get(taxonomy) if isinstance(maps, Mapping) else None
    return str(taxonomy_map.get(value, value)) if isinstance(taxonomy_map, Mapping) else value

def resolve_semantic_value(value: object, taxonomy: str, policy: Mapping[str, Any]) -> str:
    normalized = _normalize(value, taxonomy)
    return _resolve_value(normalized, taxonomy, policy) if normalized else ""


def _list_entities(values: Iterable[str], taxonomy: str, policy: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        {"raw_value": value, "canonical_value": _resolve_value(value, taxonomy, policy)}
        for value in values
    ]


def _canonical_projection(field_value: object) -> object:
    if isinstance(field_value, list):
        return sorted({str(item["canonical_value"]) for item in field_value if isinstance(item, Mapping)})
    if isinstance(field_value, Mapping):
        return str(field_value.get("canonical_value") or "") or None
    return None


def build_semantic_snapshot(
    subject_kind: SubjectKind,
    subject_identity: str,
    raw_fields: Mapping[str, object],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    resolver_contract_version = _resolver_contract_version(policy)
    contracts = _FIELD_CONTRACTS[subject_kind]
    fields: dict[str, object] = {}
    field_completeness: dict[str, str] = {}
    incomplete_reasons: dict[str, list[str]] = {}
    raw_payload: dict[str, object] = {}
    for field, (taxonomy, cardinality) in contracts.items():
        if field not in raw_fields:
            fields[field] = [] if cardinality == "list" else None
            field_completeness[field] = "incomplete"
            incomplete_reasons[field] = ["raw_field_missing"]
            continue
        if cardinality == "list":
            values = _normalized_list(raw_fields.get(field), taxonomy)
            if values is None:
                fields[field] = []
                field_completeness[field] = "incomplete"
                incomplete_reasons[field] = ["raw_field_invalid"]
                continue
            fields[field] = _list_entities(values, taxonomy, policy)
            raw_payload[field] = values
        else:
            value = _normalize(raw_fields.get(field), taxonomy)
            fields[field] = (
                {"raw_value": value, "canonical_value": _resolve_value(value, taxonomy, policy)}
                if value
                else None
            )
            raw_payload[field] = value or None
        field_completeness[field] = "complete"
    raw_fingerprint = build_contract_fingerprint(raw_payload)
    resolver_fingerprint = build_contract_fingerprint(
        {"version": resolver_contract_version, "field_contracts": contracts}
    )
    derivation_fingerprint = build_contract_fingerprint(
        {
            "raw_semantic_source_fingerprint": raw_fingerprint,
            "policy_fingerprint": policy["policy_fingerprint"],
            "resolver_contract_fingerprint": resolver_fingerprint,
        }
    )
    semantic_values = {field: _canonical_projection(value) for field, value in fields.items()}
    return {
        "schema_version": SEMANTIC_SNAPSHOT_SCHEMA_VERSION,
        "subject_kind": subject_kind,
        "subject_identity": str(subject_identity),
        "field_completeness": field_completeness,
        "fields": fields,
        "raw_semantic_source_fingerprint": raw_fingerprint,
        "semantic_derivation_fingerprint": derivation_fingerprint,
        "semantic_value_fingerprint": build_contract_fingerprint(semantic_values),
        "resolver_contract_fingerprint": resolver_fingerprint,
        "policy_fingerprint": str(policy["policy_fingerprint"]),
        "incomplete_reasons_by_field": incomplete_reasons,
    }


def project_canonical(snapshot: Mapping[str, Any], field: str) -> object:
    fields = snapshot.get("fields")
    return _canonical_projection(fields.get(field)) if isinstance(fields, Mapping) else None


def semantic_requirements_complete(snapshot: Mapping[str, Any], fields: Iterable[str]) -> bool:
    completeness = snapshot.get("field_completeness")
    return isinstance(completeness, Mapping) and all(completeness.get(field) == "complete" for field in fields)


def project_alias_equivalence(
    snapshot: Mapping[str, Any],
    field: str,
    policy: Mapping[str, Any],
) -> dict[str, list[str]]:
    canonical = project_canonical(snapshot, field)
    canonical_values = [canonical] if isinstance(canonical, str) else list(canonical or [])
    subject_kind = snapshot.get("subject_kind")
    contracts = _FIELD_CONTRACTS.get(subject_kind) if subject_kind in _FIELD_CONTRACTS else None
    taxonomy = contracts.get(field, ("", ""))[0] if contracts else ""
    maps = policy.get("maps")
    taxonomy_map = maps.get(taxonomy) if isinstance(maps, Mapping) else {}
    result: dict[str, list[str]] = {}
    for value in canonical_values:
        aliases = {str(value)}
        if isinstance(taxonomy_map, Mapping):
            aliases.update(str(alias) for alias, target in taxonomy_map.items() if target == value)
        result[str(value)] = sorted(aliases)
    return result

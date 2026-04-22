"""
@meta
name: sync_architecture_docs
type: script
domain: docs
responsibility:
  - Refresh managed feature and stage contracts from source files.
  - Regenerate evidence-oriented lineage and discovery outputs for the Mode B architecture-doc layer.
  - Detect stale generated architecture outputs when run in check mode.
inputs:
  - docs/features/*/feature.source.yaml
  - docs/features/*/history.md
  - docs/stages/*.source.yaml
outputs:
  - docs/features/*/<feature_id>.yaml
  - docs/features/*/lineage.generated.yaml
  - docs/stages/<stage_id>.yaml
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
tags:
  - docs
  - architecture
  - ci-safe
lifecycle:
  status: active
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
import re
from typing import Any, NamedTuple, cast

import yaml


GENERATED_HEADER = "# GENERATED FILE - do not edit directly.\n"
STATUS_ORDER = ["active", "building", "planned", "deprecated", "retired"]
PYTHON_META_PATTERN = re.compile(r"^[ \t]*(?:[rubf]+)?([\"']{3})(.*?)(?:\1)", re.DOTALL | re.IGNORECASE)
TEMPLATE_ARCHITECTURE_PATTERN = re.compile(r"\{#\s*@architecture(?P<body>.*?)#\}", re.DOTALL)
HTML_ARCHITECTURE_PATTERN = re.compile(r"<!--\s*@architecture(?P<body>.*?)-->", re.DOTALL)
FEATURE_PATH_PATTERN = re.compile(r"docs/features/([a-z][a-z0-9_]*)/")
PROVES_PATTERN = re.compile(r"@proves\s+([a-z][a-z0-9_]*\.[a-z0-9]+(?:-[a-z0-9]+)*)")
CAPABILITY_PATTERN = re.compile(r"@capability\s+([a-z][a-z0-9_]*\.[a-z0-9]+(?:-[a-z0-9]+)*)")
LEGACY_GENERATED_DISCOVERY_FILES = (
    "docs/generated/features_index.yaml",
    "docs/generated/feature_dependency_graph.yaml",
    "docs/generated/feature_capabilities_index.yaml",
    "docs/generated/feature_overview.md",
    "docs/generated/features_by_status.yaml",
    "docs/generated/stages_index.yaml",
    "docs/generated/stage_overview.md",
)


class RenderedFile(NamedTuple):
    path: Path
    content: str


class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data: object) -> bool:
        return True


class EvidenceIndex(NamedTuple):
    code_by_capability: dict[str, list[str]]
    tests_by_capability: dict[str, list[str]]
    configs_by_capability: dict[str, list[str]]
    components_by_capability: dict[str, list[str]]
    specs_by_feature: dict[str, list[str]]
    plans_by_feature: dict[str, list[str]]
    docs_by_feature: dict[str, list[str]]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync architecture docs from source files.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root. Defaults to this script's repo.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report stale generated files instead of writing them.",
    )
    return parser.parse_args(argv)


def read_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dump_yaml(payload: object) -> str:
    return yaml.dump(
        payload,
        Dumper=NoAliasDumper,
        sort_keys=False,
        allow_unicode=False,
        width=1000,
    )


def relpath(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def normalize_text(content: str) -> str:
    return content.replace("\r\n", "\n").rstrip() + "\n"


def normalize_prose(value: object) -> str:
    if not isinstance(value, str):
        return ""
    lines = [line.rstrip() for line in value.replace("\r\n", "\n").split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "capability"


def feature_source_paths(repo_root: Path) -> list[Path]:
    return sorted((repo_root / "docs" / "features").glob("*/feature.source.yaml"))


def stage_source_paths(repo_root: Path) -> list[Path]:
    return sorted((repo_root / "docs" / "stages").glob("*.source.yaml"))


def markdown_source_paths(repo_root: Path) -> list[Path]:
    return sorted((repo_root / "docs" / "superpowers").rglob("*.md"))


def python_source_paths(repo_root: Path) -> list[Path]:
    paths = []
    for base in ("src", "scripts", "tests"):
        root = repo_root / base
        if root.exists():
            paths.extend(sorted(root.rglob("*.py")))
    return paths


def template_source_paths(repo_root: Path) -> list[Path]:
    root = repo_root / "src"
    if not root.exists():
        return []
    return sorted(root.rglob("*.html"))


def generated_feature_contract_path(source_path: Path) -> Path:
    return source_path.parent / f"{source_path.parent.name}.yaml"


def generated_lineage_path(source_path: Path) -> Path:
    return source_path.parent / "lineage.generated.yaml"


def generated_stage_contract_path(source_path: Path) -> Path:
    stage_id = source_path.name.replace(".source.yaml", "")
    return source_path.parent / f"{stage_id}.yaml"


def load_feature_source(source_path: Path) -> dict[str, object]:
    payload = cast(dict[str, object], read_yaml(source_path))
    payload.setdefault("invariants", [])
    payload.setdefault("depends_on", [])
    payload.setdefault("domains", [])
    return payload


def load_stage_source(source_path: Path) -> tuple[str, dict[str, object]]:
    payload = cast(dict[str, object], read_yaml(source_path))
    stage_id = cast(str, payload["stage_id"])
    body = {key: value for key, value in payload.items() if key != "stage_id"}
    return stage_id, body


def strip_shebang(content: str) -> str:
    if content.startswith("#!"):
        _first_line, _newline, rest = content.partition("\n")
        return rest
    return content


def parse_python_meta(path: Path) -> dict[str, object]:
    content = strip_shebang(read_text(path)).lstrip()
    match = PYTHON_META_PATTERN.match(content)
    if not match:
        return {}
    docstring_content = match.group(2)
    if not docstring_content.startswith("\n@meta"):
        return {}
    meta_body = docstring_content.split("\n", 1)[1]
    meta_lines = meta_body.splitlines()
    if not meta_lines or meta_lines[0].strip() != "@meta":
        return {}
    yaml_body = "\n".join(meta_lines[1:]).strip()
    if not yaml_body:
        return {}
    try:
        payload = yaml.safe_load(yaml_body)
    except yaml.YAMLError:
        return {}
    return cast(dict[str, object], payload) if isinstance(payload, dict) else {}


def parse_python_function_capabilities(path: Path) -> list[str]:
    try:
        tree = ast.parse(read_text(path), filename=str(path))
    except SyntaxError:
        return []

    capability_ids: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        docstring = ast.get_docstring(node, clean=False)
        if not docstring:
            continue
        capability_ids.update(CAPABILITY_PATTERN.findall(docstring))
    return sorted(capability_ids)


def parse_markdown_frontmatter(path: Path) -> dict[str, object]:
    content = read_text(path)
    if not content.startswith("---\n"):
        return {}
    _open, _newline, remainder = content.partition("\n")
    frontmatter, separator, _rest = remainder.partition("\n---\n")
    if not separator:
        return {}
    try:
        payload = yaml.safe_load(frontmatter)
    except yaml.YAMLError:
        return {}
    return cast(dict[str, object], payload) if isinstance(payload, dict) else {}


def parse_template_architecture(path: Path) -> dict[str, object]:
    content = read_text(path)
    for pattern in (TEMPLATE_ARCHITECTURE_PATTERN, HTML_ARCHITECTURE_PATTERN):
        match = pattern.search(content)
        if not match:
            continue
        yaml_body = match.group("body").strip()
        if not yaml_body:
            return {}
        try:
            payload = yaml.safe_load(yaml_body)
        except yaml.YAMLError:
            return {}
        return cast(dict[str, object], payload) if isinstance(payload, dict) else {}
    return {}


def metadata_capability_ids(meta: dict[str, object]) -> list[str]:
    capabilities = meta.get("capabilities", [])
    if not isinstance(capabilities, list):
        return []
    return sorted({str(item) for item in capabilities if isinstance(item, str)})


def path_bucket(path: str) -> str:
    if path.startswith("tests/"):
        return "tests"
    if path.startswith("repo_config/"):
        return "configs"
    return "code"


def feature_ids_from_markdown(path: Path, frontmatter: dict[str, object]) -> set[str]:
    feature_ids: set[str] = set()
    related_features = frontmatter.get("related_features", [])
    if isinstance(related_features, list):
        feature_ids.update(str(item) for item in related_features if isinstance(item, str))
    feature_name = frontmatter.get("feature_name")
    if isinstance(feature_name, str) and feature_name:
        feature_ids.add(feature_name)
    content = read_text(path)
    feature_ids.update(FEATURE_PATH_PATTERN.findall(content))
    return feature_ids


def sorted_unique(paths: list[str]) -> list[str]:
    return sorted(set(paths))


def build_evidence_index(repo_root: Path) -> EvidenceIndex:
    function_code_by_capability: dict[str, list[str]] = {}
    file_code_by_capability: dict[str, list[str]] = {}
    tests_by_capability: dict[str, list[str]] = {}
    configs_by_capability: dict[str, list[str]] = {}
    components_by_capability: dict[str, list[str]] = {}
    specs_by_feature: dict[str, list[str]] = {}
    plans_by_feature: dict[str, list[str]] = {}
    docs_by_feature: dict[str, list[str]] = {}

    for path in python_source_paths(repo_root):
        relative = relpath(path, repo_root)
        meta = parse_python_meta(path)
        capability_ids = metadata_capability_ids(meta)
        function_capability_ids = parse_python_function_capabilities(path)
        bucket = path_bucket(relative)
        for capability_id in function_capability_ids:
            if bucket == "tests":
                tests_by_capability.setdefault(capability_id, []).append(relative)
            elif bucket == "configs":
                configs_by_capability.setdefault(capability_id, []).append(relative)
            else:
                function_code_by_capability.setdefault(capability_id, []).append(relative)
        for capability_id in capability_ids:
            if bucket == "tests":
                tests_by_capability.setdefault(capability_id, []).append(relative)
            elif bucket == "configs":
                configs_by_capability.setdefault(capability_id, []).append(relative)
            else:
                file_code_by_capability.setdefault(capability_id, []).append(relative)
        if bucket == "tests":
            for capability_id in PROVES_PATTERN.findall(read_text(path)):
                tests_by_capability.setdefault(capability_id, []).append(relative)

    for path in template_source_paths(repo_root):
        relative = relpath(path, repo_root)
        meta = parse_template_architecture(path)
        capability_ids = metadata_capability_ids(meta)
        for capability_id in capability_ids:
            file_code_by_capability.setdefault(capability_id, []).append(relative)

    for path in markdown_source_paths(repo_root):
        relative = relpath(path, repo_root)
        frontmatter = parse_markdown_frontmatter(path)
        feature_ids = feature_ids_from_markdown(path, frontmatter)
        artifact_type = frontmatter.get("artifact_type")
        if artifact_type == "plan" or "/plans/" in relative.replace("\\", "/"):
            target_index = plans_by_feature
        elif artifact_type == "spec" or "/specs/" in relative.replace("\\", "/"):
            target_index = specs_by_feature
        else:
            continue
        for feature_id in feature_ids:
            target_index.setdefault(feature_id, []).append(relative)

    for history_path in sorted((repo_root / "docs" / "features").glob("*/history.md")):
        feature_id = history_path.parent.name
        docs_by_feature.setdefault(feature_id, []).append(relpath(history_path, repo_root))

    return EvidenceIndex(
        code_by_capability={
            key: sorted_unique(function_code_by_capability.get(key, file_code_by_capability.get(key, [])))
            for key in sorted(set(function_code_by_capability) | set(file_code_by_capability))
        },
        tests_by_capability={key: sorted_unique(value) for key, value in tests_by_capability.items()},
        configs_by_capability={key: sorted_unique(value) for key, value in configs_by_capability.items()},
        components_by_capability={key: sorted_unique(value) for key, value in components_by_capability.items()},
        specs_by_feature={key: sorted_unique(value) for key, value in specs_by_feature.items()},
        plans_by_feature={key: sorted_unique(value) for key, value in plans_by_feature.items()},
        docs_by_feature={key: sorted_unique(value) for key, value in docs_by_feature.items()},
    )


def normalize_capability(
    feature_id: str,
    capability: object,
    position: int,
) -> dict[str, object]:
    if not isinstance(capability, dict):
        raise ValueError(
            f"{feature_id} capability entry {position + 1} must be a mapping with "
            "capability_id, statement, and state."
        )

    payload = cast(dict[str, object], capability)
    capability_id = payload.get("capability_id")
    statement = payload.get("statement")
    state = payload.get("state")
    if not isinstance(capability_id, str) or not capability_id:
        raise ValueError(f"{feature_id} capability entry {position + 1} is missing capability_id.")
    if not isinstance(statement, str) or not statement:
        raise ValueError(f"{feature_id} capability entry {position + 1} is missing statement.")
    if not isinstance(state, str) or not state:
        raise ValueError(f"{feature_id} capability entry {position + 1} is missing state.")
    return {
        "capability_id": capability_id,
        "statement": normalize_prose(statement),
        "state": state,
    }


def normalize_invariant(invariant: object, position: int) -> dict[str, object]:
    if isinstance(invariant, str):
        return {
            "invariant_id": f"invariant-{position + 1}",
            "statement": invariant,
            "state": "active",
        }
    payload = cast(dict[str, object], invariant)
    return {
        "invariant_id": cast(str, payload.get("invariant_id", f"invariant-{position + 1}")),
        "statement": normalize_prose(payload.get("statement", payload.get("summary", ""))),
        "state": cast(str, payload.get("state", "active")),
    }


def normalize_stage_participation(
    source: dict[str, object],
    capability_ids: list[str],
) -> list[dict[str, object]]:
    stage_participation = source.get("stage_participation")
    if isinstance(stage_participation, list):
        normalized: list[dict[str, object]] = []
        for entry in stage_participation:
            if not isinstance(entry, dict):
                continue
            normalized.append(
                {
                    "stage_id": entry.get("stage_id"),
                    "role": entry.get("role", "supporting"),
                    "capability_ids": cast(list[str], entry.get("capability_ids", [])),
                }
            )
        return normalized
    return []


def generated_refs(feature_id: str, source: dict[str, object], evidence_index: EvidenceIndex) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    normalized["history"] = evidence_index.docs_by_feature.get(
        feature_id,
        [f"docs/features/{feature_id}/history.md"],
    )
    normalized["spec"] = evidence_index.specs_by_feature.get(feature_id, [])
    normalized["plan"] = evidence_index.plans_by_feature.get(feature_id, [])
    return normalized


def contract_payload(feature_id: str, source: dict[str, object], evidence_index: EvidenceIndex) -> dict[str, object]:
    capabilities = [
        {
            "capability_id": capability["capability_id"],
            "statement": capability["statement"],
            "state": capability["state"],
        }
        for capability in [
            normalize_capability(feature_id, raw_capability, index)
            for index, raw_capability in enumerate(cast(list[object], source.get("capabilities", [])))
        ]
    ]
    capability_ids = [capability["capability_id"] for capability in capabilities]
    return {
        "feature_id": feature_id,
        "name": source.get("name", feature_id.replace("_", " ").title()),
        "status": source.get("status", "unknown"),
        "type": source.get("type", "unknown"),
        "summary": normalize_prose(source.get("summary", "")),
        "invariants": [
            normalize_invariant(invariant, index)
            for index, invariant in enumerate(cast(list[object], source.get("invariants", [])))
        ],
        "domains": cast(list[str], source.get("domains", [])),
        "depends_on": cast(list[str], source.get("depends_on", [])),
        "capabilities": capabilities,
        "stage_participation": normalize_stage_participation(source, capability_ids),
        "refs": generated_refs(feature_id, source, evidence_index),
    }


def evidence_nodes(paths: list[str], kind: str) -> list[dict[str, object]]:
    return [{"path": path, "kind": kind} for path in paths]


def completeness_status(
    code: list[str],
    tests: list[str],
    specs: list[str],
    plans: list[str],
    configs: list[str],
    components: list[str],
) -> str:
    if code and tests:
        return "complete"
    if code or tests or specs or plans or configs or components:
        return "partial"
    return "missing_evidence"


def lineage_payload(feature_id: str, source: dict[str, object], evidence_index: EvidenceIndex) -> dict[str, object]:
    refs = generated_refs(feature_id, source, evidence_index)
    capabilities: dict[str, dict[str, object]] = {}
    for index, raw_capability in enumerate(cast(list[object], source.get("capabilities", []))):
        capability = normalize_capability(feature_id, raw_capability, index)
        capability_id = cast(str, capability["capability_id"])
        code = list(evidence_index.code_by_capability.get(capability_id, []))
        tests = list(evidence_index.tests_by_capability.get(capability_id, []))
        configs = list(evidence_index.configs_by_capability.get(capability_id, []))
        components = list(evidence_index.components_by_capability.get(capability_id, []))
        specs = list(refs.get("spec", []))
        plans = list(refs.get("plan", []))
        docs = sorted(set(refs.get("docs", []) + refs.get("history", [])))
        evidence_gaps: list[str] = []
        if not code:
            evidence_gaps.append("missing_code_evidence")
        if not tests:
            evidence_gaps.append("missing_test_evidence")
        status = completeness_status(code, tests, specs, plans, configs, components)
        capabilities[capability_id] = {
            "state": capability["state"],
            "statement": capability["statement"],
            "satisfies": [],
            "code": code,
            "tests": tests,
            "docs": docs,
            "docs_evidence": evidence_nodes(docs, "doc_ref"),
            "configs": configs,
            "config_evidence": evidence_nodes(configs, "config_ref"),
            "components": components,
            "component_evidence": evidence_nodes(components, "component_ref"),
            "specs": specs,
            "plans": plans,
            "evidence_gaps": list(evidence_gaps),
            "allowed_evidence_gaps": list(evidence_gaps),
            "lineage_exception_reason": None,
            "unresolved_evidence_gaps": [],
            "completeness_status": status,
        }

    invariants = {
        invariant["invariant_id"]: {
            "state": invariant["state"],
            "statement": invariant["statement"],
        }
        for index, invariant in enumerate(cast(list[object], source.get("invariants", [])))
        for invariant in [normalize_invariant(invariant, index)]
    }

    timeline = [{"kind": "spec", "path": path} for path in refs.get("spec", [])] + [
        {"kind": "plan", "path": path} for path in refs.get("plan", [])
    ]

    return {
        "feature_id": feature_id,
        "source": f"docs/features/{feature_id}/feature.source.yaml",
        "invariants": invariants,
        "capabilities": capabilities,
        "timeline": timeline,
    }


def render_feature_outputs(repo_root: Path, source_path: Path, evidence_index: EvidenceIndex) -> list[RenderedFile]:
    source = load_feature_source(source_path)
    feature_id = cast(str, source["feature_id"])
    return [
        RenderedFile(
            path=generated_feature_contract_path(source_path),
            content=GENERATED_HEADER + dump_yaml(contract_payload(feature_id, source, evidence_index)),
        ),
        RenderedFile(
            path=generated_lineage_path(source_path),
            content=GENERATED_HEADER + dump_yaml(lineage_payload(feature_id, source, evidence_index)),
        ),
    ]


def render_stage_outputs(source_path: Path) -> list[RenderedFile]:
    stage_id, stage_body = load_stage_source(source_path)
    return [
        RenderedFile(
            path=generated_stage_contract_path(source_path),
            content=dump_yaml({stage_id: stage_body}),
        )
    ]


def feature_records(repo_root: Path) -> list[tuple[str, dict[str, object]]]:
    records: list[tuple[str, dict[str, object]]] = []
    for source_path in feature_source_paths(repo_root):
        source = load_feature_source(source_path)
        feature_id = cast(str, source["feature_id"])
        records.append((feature_id, source))
    return sorted(records, key=lambda item: item[0])


def stage_records(repo_root: Path) -> list[tuple[str, dict[str, object]]]:
    records: list[tuple[str, dict[str, object]]] = []
    for source_path in stage_source_paths(repo_root):
        records.append(load_stage_source(source_path))
    return sorted(records, key=lambda item: item[0])


def build_architecture_dag(repo_root: Path) -> RenderedFile:
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []

    for feature_id, source in feature_records(repo_root):
        nodes.append(
            {
                "id": feature_id,
                "kind": "feature",
                "name": source.get("name", feature_id.replace("_", " ").title()),
                "path": f"docs/features/{feature_id}/{feature_id}.yaml",
                "status": source.get("status", "unknown"),
            }
        )
        for dependency in sorted(cast(list[str], source.get("depends_on", []))):
            edges.append({"from": feature_id, "to": dependency, "type": "depends_on"})
        for index, raw_capability in enumerate(cast(list[object], source.get("capabilities", []))):
            capability = normalize_capability(feature_id, raw_capability, index)
            capability_id = cast(str, capability["capability_id"])
            nodes.append(
                {
                    "id": capability_id,
                    "kind": "capability",
                    "feature_id": feature_id,
                    "state": capability["state"],
                    "path": f"docs/features/{feature_id}/lineage.generated.yaml",
                }
            )
            edges.append({"from": feature_id, "to": capability_id, "type": "owns_capability"})
        for entry in normalize_stage_participation(source, []):
            stage_id = cast(str, entry.get("stage_id", ""))
            if not stage_id:
                continue
            edges.append(
                {
                    "from": feature_id,
                    "to": stage_id,
                    "type": "participates_in",
                    "role": entry.get("role", "supporting"),
                    "capability_ids": entry.get("capability_ids", []),
                }
            )

    for stage_id, body in stage_records(repo_root):
        nodes.append(
            {
                "id": stage_id,
                "kind": "stage",
                "name": body.get("name", stage_id.replace("_", " ").title()),
                "path": f"docs/stages/{stage_id}.yaml",
            }
        )
        for dependency in sorted(cast(list[str], body.get("depends_on", []))):
            edges.append({"from": stage_id, "to": dependency, "type": "depends_on"})
        for feature_id in sorted(cast(list[str], body.get("primary_features", []))):
            edges.append({"from": stage_id, "to": feature_id, "type": "primary_feature"})
        for feature_id in sorted(cast(list[str], body.get("related_features", []))):
            edges.append({"from": stage_id, "to": feature_id, "type": "related_feature"})

    nodes.sort(key=lambda item: (cast(str, item["kind"]), cast(str, item["id"])))
    edges.sort(key=lambda item: (cast(str, item["from"]), cast(str, item["type"]), cast(str, item["to"])))
    return RenderedFile(
        repo_root / "docs" / "generated" / "architecture_dag.yaml",
        GENERATED_HEADER + dump_yaml({"nodes": nodes, "edges": edges}),
    )


def build_capability_lineage(repo_root: Path) -> RenderedFile:
    evidence_index = build_evidence_index(repo_root)
    features: dict[str, dict[str, object]] = {}
    for source_path in feature_source_paths(repo_root):
        source = load_feature_source(source_path)
        feature_id = cast(str, source["feature_id"])
        lineage = lineage_payload(feature_id, source, evidence_index)
        features[feature_id] = {
            "summary": normalize_prose(source.get("summary", "")),
            "status": source.get("status", "unknown"),
            "type": source.get("type", "unknown"),
            "capabilities": lineage["capabilities"],
        }
    return RenderedFile(
        repo_root / "docs" / "generated" / "capability_lineage.yaml",
        GENERATED_HEADER + dump_yaml({"features": features}),
    )


def collect_rendered_files(repo_root: Path) -> list[RenderedFile]:
    rendered: list[RenderedFile] = []
    evidence_index = build_evidence_index(repo_root)
    for source_path in feature_source_paths(repo_root):
        rendered.extend(render_feature_outputs(repo_root, source_path, evidence_index))
    for source_path in stage_source_paths(repo_root):
        rendered.extend(render_stage_outputs(source_path))
    rendered.extend(
        [
            build_architecture_dag(repo_root),
            build_capability_lineage(repo_root),
        ]
    )
    return rendered


def write_rendered_files(rendered_files: list[RenderedFile]) -> None:
    repo_root = rendered_files[0].path.parents[3] if rendered_files else Path.cwd()
    for relative_path in LEGACY_GENERATED_DISCOVERY_FILES:
        legacy_path = repo_root / relative_path
        if legacy_path.exists():
            legacy_path.unlink()
    for rendered in rendered_files:
        rendered.path.parent.mkdir(parents=True, exist_ok=True)
        rendered.path.write_text(normalize_text(rendered.content), encoding="utf-8")


def stale_outputs(rendered_files: list[RenderedFile]) -> list[Path]:
    stale: list[Path] = []
    repo_root = rendered_files[0].path.parents[3] if rendered_files else Path.cwd()
    for rendered in rendered_files:
        expected = normalize_text(rendered.content)
        if not rendered.path.exists():
            stale.append(rendered.path)
            continue
        actual = normalize_text(rendered.path.read_text(encoding="utf-8"))
        if actual != expected:
            stale.append(rendered.path)
    for relative_path in LEGACY_GENERATED_DISCOVERY_FILES:
        legacy_path = repo_root / relative_path
        if legacy_path.exists():
            stale.append(legacy_path)
    return stale


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    rendered_files = collect_rendered_files(repo_root)
    if args.check:
        stale = stale_outputs(rendered_files)
        if stale:
            for path in stale:
                print(f"Stale generated file: {relpath(path, repo_root)}")
            return 1
        print("Architecture docs are up to date.")
        return 0

    write_rendered_files(rendered_files)
    print("Architecture docs synchronized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
@meta
name: generate_architecture_metadata
type: script
domain: docs
responsibility:
  - Generate managed feature, stage, lineage, and discovery outputs from source metadata.
  - Rebuild the evidence-oriented architecture metadata layer for the current repo layout.
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
  - lineage
  - generator
  - ci-safe
lifecycle:
  status: active
"""

from __future__ import annotations

import argparse
import ast
from datetime import date, datetime
from pathlib import Path
import re
from typing import Any, NamedTuple, cast

import yaml


GENERATED_HEADER = "# GENERATED FILE - do not edit directly.\n"
GENERATED_HISTORY_START = "<!-- GENERATED HISTORY START -->"
GENERATED_HISTORY_END = "<!-- GENERATED HISTORY END -->"
HUMAN_HISTORY_HEADING = "## Human Notes"
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


def quote_yaml_key(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def normalize_explicit_string_keys(yaml_text: str) -> str:
    lines = yaml_text.splitlines()
    normalized: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.lstrip(" ")
        indent = line[: len(line) - len(stripped)]

        if stripped.startswith("? ") and index + 1 < len(lines):
            next_line = lines[index + 1]
            next_stripped = next_line.lstrip(" ")
            next_indent = next_line[: len(next_line) - len(next_stripped)]
            if next_indent == indent and next_stripped.startswith(": "):
                normalized.append(f"{indent}{quote_yaml_key(stripped[2:])}:")
                normalized.append(f"{indent}  {next_stripped[2:]}")
                index += 2
                continue

        normalized.append(line)
        index += 1

    trailing_newline = "\n" if yaml_text.endswith("\n") else ""
    return "\n".join(normalized) + trailing_newline


class EvidenceNode(NamedTuple):
    path: str
    confidence: str
    source: tuple[str, ...]
    symbols: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "path": self.path,
            "confidence": self.confidence,
            "source": list(self.source),
        }
        if self.symbols:
            payload["symbols"] = list(self.symbols)
        return payload


class EvidenceIndex(NamedTuple):
    code_by_capability: dict[str, list[EvidenceNode]]
    tests_by_capability: dict[str, list[EvidenceNode]]
    configs_by_capability: dict[str, list[str]]
    components_by_capability: dict[str, list[str]]
    component_evidence_by_capability: dict[str, list[dict[str, object]]]
    satisfies_by_capability: dict[str, list[str]]
    specs_by_feature: dict[str, list[str]]
    plans_by_feature: dict[str, list[str]]
    docs_by_feature: dict[str, list[str]]


class MetadataDocument(NamedTuple):
    relative_path: str
    frontmatter: dict[str, object]
    title: str
    feature_ids: set[str]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate architecture metadata from source files.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root. Defaults to this script's repo.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report stale generated files instead of writing them.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate source inputs and renderability without writing or checking generated outputs.",
    )
    return parser.parse_args(argv)


def read_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dump_yaml(payload: object) -> str:
    dumped = yaml.dump(
        payload,
        Dumper=NoAliasDumper,
        sort_keys=False,
        allow_unicode=False,
        width=1000,
    )
    return normalize_explicit_string_keys(dumped)


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


def config_source_paths(repo_root: Path) -> list[Path]:
    root = repo_root / "config"
    if not root.exists():
        return []
    return sorted(root.rglob("*.yaml"))


def component_source_paths(repo_root: Path) -> list[Path]:
    root = repo_root / "aml" / "components"
    if not root.exists():
        return []
    return sorted(root.rglob("*.yaml"))


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


def stage_capability_refs(repo_root: Path, stage_id: str) -> list[str]:
    capability_ids: list[str] = []
    for feature_id, source in feature_records(repo_root):
        for entry in normalize_stage_participation(source, []):
            if cast(str, entry.get("stage_id", "")) != stage_id:
                continue
            capability_ids.extend(cast(list[str], entry.get("capability_ids", [])))
    return sorted_unique(capability_ids)


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


def parse_python_function_capabilities(path: Path) -> list[tuple[str, str]]:
    try:
        tree = ast.parse(read_text(path), filename=str(path))
    except SyntaxError:
        return []

    capability_ids: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        docstring = ast.get_docstring(node, clean=False)
        if not docstring:
            continue
        for capability_id in CAPABILITY_PATTERN.findall(docstring):
            capability_ids.add((capability_id, node.name))
    return sorted(capability_ids)


def parse_python_function_proves(path: Path) -> list[tuple[str, str]]:
    try:
        tree = ast.parse(read_text(path), filename=str(path))
    except SyntaxError:
        return []

    proves_ids: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        docstring = ast.get_docstring(node, clean=False)
        if not docstring:
            continue
        for capability_id in PROVES_PATTERN.findall(docstring):
            proves_ids.add((capability_id, node.name))
    return sorted(proves_ids)


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


def parse_markdown_title(path: Path) -> str:
    content = read_text(path)
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


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


def parse_yaml_architecture(path: Path) -> dict[str, object]:
    metadata_lines: list[str] = []
    metadata_started = False
    for line in read_text(path).splitlines():
        stripped = line.strip()
        if not stripped:
            if metadata_started:
                break
            continue
        if not stripped.startswith("#"):
            break
        comment_body = stripped[1:]
        if comment_body.startswith(" "):
            comment_body = comment_body[1:]
        if comment_body == "@architecture":
            metadata_started = True
            continue
        if metadata_started:
            metadata_lines.append(comment_body)
    if not metadata_lines:
        return {}
    try:
        payload = yaml.safe_load("\n".join(metadata_lines))
    except yaml.YAMLError:
        return {}
    return cast(dict[str, object], payload) if isinstance(payload, dict) else {}


def metadata_capability_ids(meta: dict[str, object]) -> list[str]:
    capabilities = meta.get("capabilities", [])
    if not isinstance(capabilities, list):
        return []
    return sorted({str(item) for item in capabilities if isinstance(item, str)})


def metadata_string_list(meta: dict[str, object], key: str) -> list[str]:
    values = meta.get(key, [])
    if not isinstance(values, list):
        return []
    return sorted({str(item) for item in values if isinstance(item, str) and item})


def path_bucket(path: str) -> str:
    if path.startswith("tests/"):
        return "tests"
    if path.startswith("repo_config/") or path.startswith("config/"):
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


def markdown_documents(repo_root: Path) -> list[MetadataDocument]:
    documents: list[MetadataDocument] = []
    for path in markdown_source_paths(repo_root):
        relative = relpath(path, repo_root)
        frontmatter = parse_markdown_frontmatter(path)
        documents.append(
            MetadataDocument(
                relative_path=relative,
                frontmatter=frontmatter,
                title=parse_markdown_title(path),
                feature_ids=feature_ids_from_markdown(path, frontmatter),
            )
        )
    return documents


def sorted_unique(paths: list[str]) -> list[str]:
    return sorted(set(paths))


def capability_ref_paths(
    evidence_index: EvidenceIndex,
    capability_ids: list[str],
    *,
    family: str,
) -> list[str]:
    if family == "code":
        values = [
            node.path
            for capability_id in capability_ids
            for node in evidence_index.code_by_capability.get(capability_id, [])
        ]
        return sorted_unique(values)
    if family == "tests":
        values = [
            node.path
            for capability_id in capability_ids
            for node in evidence_index.tests_by_capability.get(capability_id, [])
        ]
        return sorted_unique(values)
    if family == "configs":
        values = [
            path
            for capability_id in capability_ids
            for path in evidence_index.configs_by_capability.get(capability_id, [])
        ]
        return sorted_unique(values)
    if family == "components":
        values = [
            path
            for capability_id in capability_ids
            for path in evidence_index.components_by_capability.get(capability_id, [])
        ]
        return sorted_unique(values)
    raise ValueError(f"Unsupported ref family: {family}")


def evidence_node(
    path: str,
    *,
    confidence: str,
    source: tuple[str, ...],
    symbols: tuple[str, ...] = (),
) -> EvidenceNode:
    return EvidenceNode(path=path, confidence=confidence, source=source, symbols=symbols)


def merge_evidence_nodes(*collections: list[EvidenceNode]) -> list[EvidenceNode]:
    merged: dict[tuple[str, str, tuple[str, ...], tuple[str, ...]], EvidenceNode] = {}
    for collection in collections:
        for node in collection:
            merged[(node.path, node.confidence, node.source, node.symbols)] = node
    return sorted(merged.values(), key=lambda node: (node.path, node.source, node.symbols))


def build_evidence_index(repo_root: Path) -> EvidenceIndex:
    function_code_by_capability: dict[str, list[EvidenceNode]] = {}
    file_code_by_capability: dict[str, list[EvidenceNode]] = {}
    tests_by_capability: dict[str, list[EvidenceNode]] = {}
    configs_by_capability: dict[str, list[str]] = {}
    components_by_capability: dict[str, list[str]] = {}
    component_evidence_by_capability: dict[str, list[dict[str, object]]] = {}
    satisfies_by_capability: dict[str, list[str]] = {}
    specs_by_feature: dict[str, list[str]] = {}
    plans_by_feature: dict[str, list[str]] = {}
    docs_by_feature: dict[str, list[str]] = {}

    for path in python_source_paths(repo_root):
        relative = relpath(path, repo_root)
        meta = parse_python_meta(path)
        capability_ids = metadata_capability_ids(meta)
        function_capability_ids = parse_python_function_capabilities(path)
        bucket = path_bucket(relative)
        for capability_id, symbol_name in function_capability_ids:
            if bucket == "tests":
                tests_by_capability.setdefault(capability_id, []).append(
                    evidence_node(
                        relative,
                        confidence="high",
                        source=("python_capability",),
                        symbols=(symbol_name,),
                    )
                )
            elif bucket == "configs":
                configs_by_capability.setdefault(capability_id, []).append(relative)
            else:
                function_code_by_capability.setdefault(capability_id, []).append(
                    evidence_node(
                        relative,
                        confidence="high",
                        source=("python_capability",),
                        symbols=(symbol_name,),
                    )
                )
        for capability_id in capability_ids:
            if bucket == "tests":
                tests_by_capability.setdefault(capability_id, []).append(
                    evidence_node(relative, confidence="high", source=("python_meta",))
                )
            elif bucket == "configs":
                configs_by_capability.setdefault(capability_id, []).append(relative)
            else:
                file_code_by_capability.setdefault(capability_id, []).append(
                    evidence_node(relative, confidence="high", source=("python_meta",))
                )
        if bucket == "tests":
            proves_markers = parse_python_function_proves(path)
            if proves_markers:
                for capability_id, symbol_name in proves_markers:
                    tests_by_capability.setdefault(capability_id, []).append(
                        evidence_node(
                            relative,
                            confidence="high",
                            source=("python_proves",),
                            symbols=(symbol_name,),
                        )
                    )
            else:
                for capability_id in PROVES_PATTERN.findall(read_text(path)):
                    tests_by_capability.setdefault(capability_id, []).append(
                        evidence_node(relative, confidence="high", source=("python_proves",))
                    )

    for path in template_source_paths(repo_root):
        relative = relpath(path, repo_root)
        meta = parse_template_architecture(path)
        capability_ids = metadata_capability_ids(meta)
        for capability_id in capability_ids:
            file_code_by_capability.setdefault(capability_id, []).append(
                evidence_node(relative, confidence="high", source=("template_architecture",))
            )

    for path in config_source_paths(repo_root):
        relative = relpath(path, repo_root)
        meta = parse_yaml_architecture(path)
        capability_ids = metadata_capability_ids(meta)
        satisfies_ids = metadata_string_list(meta, "satisfies")
        for capability_id in capability_ids:
            configs_by_capability.setdefault(capability_id, []).append(relative)
            for satisfies_id in satisfies_ids:
                satisfies_by_capability.setdefault(capability_id, []).append(satisfies_id)

    for path in component_source_paths(repo_root):
        relative = relpath(path, repo_root)
        meta = parse_yaml_architecture(path)
        capability_ids = metadata_capability_ids(meta)
        satisfies_ids = metadata_string_list(meta, "satisfies")
        for capability_id in capability_ids:
            components_by_capability.setdefault(capability_id, []).append(relative)
            component_evidence_by_capability.setdefault(capability_id, []).append(
                {
                    "path": relative,
                    "confidence": "high",
                    "source": ["yaml_architecture"],
                }
            )
            for satisfies_id in satisfies_ids:
                satisfies_by_capability.setdefault(capability_id, []).append(satisfies_id)

    for document in markdown_documents(repo_root):
        relative = document.relative_path
        feature_ids = document.feature_ids
        artifact_type = document.frontmatter.get("artifact_type")
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
            key: merge_evidence_nodes(
                file_code_by_capability.get(key, []),
                function_code_by_capability.get(key, []),
            )
            for key in sorted(set(function_code_by_capability) | set(file_code_by_capability))
        },
        tests_by_capability={key: merge_evidence_nodes(value) for key, value in tests_by_capability.items()},
        configs_by_capability={key: sorted_unique(value) for key, value in configs_by_capability.items()},
        components_by_capability={key: sorted_unique(value) for key, value in components_by_capability.items()},
        component_evidence_by_capability={
            key: sorted(value, key=lambda item: cast(str, item["path"]))
            for key, value in component_evidence_by_capability.items()
        },
        satisfies_by_capability={key: sorted_unique(value) for key, value in satisfies_by_capability.items()},
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
    capability_ids = [
        cast(str, normalize_capability(feature_id, raw_capability, index)["capability_id"])
        for index, raw_capability in enumerate(cast(list[object], source.get("capabilities", [])))
    ]
    docs = evidence_index.docs_by_feature.get(feature_id, [f"docs/features/{feature_id}/history.md"])
    return {
        "code": capability_ref_paths(evidence_index, capability_ids, family="code"),
        "tests": capability_ref_paths(evidence_index, capability_ids, family="tests"),
        "specs": evidence_index.specs_by_feature.get(feature_id, []),
        "plans": evidence_index.plans_by_feature.get(feature_id, []),
        "docs": sorted_unique(docs),
        "configs": capability_ref_paths(evidence_index, capability_ids, family="configs"),
        "components": capability_ref_paths(evidence_index, capability_ids, family="components"),
    }


def feature_freshness(repo_root: Path, feature_id: str) -> dict[str, str]:
    timeline = timeline_for_feature(repo_root, feature_id)
    if not timeline:
        return {}
    latest_entry = timeline[-1]
    return {
        "revision": len(timeline),
        "latest_change_id": str(latest_entry.get("change_id", "")),
        "last_updated_at": str(latest_entry.get("completed_at", "")),
    }


def contract_payload(
    repo_root: Path, feature_id: str, source: dict[str, object], evidence_index: EvidenceIndex
) -> dict[str, object]:
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
    payload: dict[str, object] = {
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
    payload.update(feature_freshness(repo_root, feature_id))
    return payload


def evidence_nodes(paths: list[str], source: str) -> list[dict[str, object]]:
    return [
        {
            "path": path,
            "confidence": "high",
            "source": [source],
        }
        for path in paths
    ]


def completeness_status(
    code: list[EvidenceNode],
    tests: list[EvidenceNode],
    specs: list[str],
    plans: list[str],
    configs: list[str],
    components: list[str],
) -> str:
    if code and tests:
        return "complete"
    if code or tests or specs or plans or configs or components:
        return "incomplete"
    return "incomplete"


def timeline_entry_for_plan(plan: MetadataDocument, feature_id: str) -> dict[str, object] | None:
    metadata = plan.frontmatter
    if metadata.get("status") != "completed":
        return None

    completed_at = metadata.get("completed_at")
    change_id = metadata.get("change_id")
    verification = metadata.get("verification")
    outcome = metadata.get("outcome")
    affects = metadata.get("affects")

    if isinstance(completed_at, datetime):
        completed_at_value = completed_at.isoformat()
    elif isinstance(completed_at, date):
        completed_at_value = completed_at.isoformat()
    elif isinstance(completed_at, str) and completed_at:
        completed_at_value = completed_at
    else:
        return None
    if not isinstance(change_id, str) or not change_id:
        return None
    if not isinstance(verification, list) or not all(isinstance(item, str) for item in verification):
        return None
    if not isinstance(outcome, dict):
        return None
    outcome_summary = outcome.get("summary")
    if not isinstance(outcome_summary, str) or not outcome_summary:
        return None

    capabilities: list[str] = []
    if isinstance(affects, dict):
        raw_capabilities = affects.get("capabilities", [])
        if isinstance(raw_capabilities, list) and all(isinstance(item, str) for item in raw_capabilities):
            capabilities = [item for item in raw_capabilities if item.startswith(f"{feature_id}.")]

    return {
        "completed_at": completed_at_value,
        "source_plan": plan.relative_path,
        "change_id": change_id,
        "summary": plan.title,
        "capabilities": capabilities,
        "verification": list(verification),
        "outcome": outcome_summary,
    }


def timeline_for_feature(repo_root: Path, feature_id: str) -> list[dict[str, object]]:
    timeline: list[dict[str, object]] = []
    for document in markdown_documents(repo_root):
        artifact_type = document.frontmatter.get("artifact_type")
        if not (artifact_type == "plan" or "/plans/" in document.relative_path.replace("\\", "/")):
            continue
        if feature_id not in document.feature_ids:
            continue
        entry = timeline_entry_for_plan(document, feature_id)
        if entry is not None:
            timeline.append(entry)
    timeline.sort(key=lambda item: cast(str, item["completed_at"]))
    return timeline


def extract_history_heading(text: str) -> str | None:
    stripped = text.lstrip()
    if not stripped.startswith("# "):
        return None
    heading, _, _ = stripped.partition("\n")
    return heading.strip()


def extract_existing_human_history(history_path: Path) -> tuple[str | None, str]:
    if not history_path.exists():
        return None, ""

    text = history_path.read_text(encoding="utf-8")
    heading = extract_history_heading(text)
    if GENERATED_HISTORY_START in text and GENERATED_HISTORY_END in text:
        after_end = text.split(GENERATED_HISTORY_END, 1)[1].lstrip("\n")
        if after_end.startswith(HUMAN_HISTORY_HEADING):
            body = after_end[len(HUMAN_HISTORY_HEADING) :].lstrip()
        else:
            body = after_end.strip()
        return heading, body.rstrip()

    legacy_body = text
    if heading is not None:
        legacy_body = legacy_body.split("\n", 1)[1] if "\n" in legacy_body else ""
    return heading, legacy_body.strip()


def build_generated_history_section(*, timeline: list[dict[str, object]]) -> str:
    if not timeline:
        return (
            f"{GENERATED_HISTORY_START}\n\n"
            "No completed implementation-plan metadata currently targets this feature.\n\n"
            f"{GENERATED_HISTORY_END}"
        )

    lines = [GENERATED_HISTORY_START, ""]
    current_date: str | None = None
    for item in timeline:
        completed_at = str(item.get("completed_at", ""))
        completed_date = completed_at.split("T", 1)[0] if completed_at else "unknown-date"
        if completed_date != current_date:
            if current_date is not None:
                lines.append("")
            lines.append(f"## {completed_date}")
            lines.append("")
            current_date = completed_date

        lines.append(f"### {str(item.get('summary', 'Completed change'))}")
        lines.append("")
        lines.append(f"Source plan: `{str(item.get('source_plan', ''))}`")
        lines.append("")
        capabilities = item.get("capabilities", [])
        if isinstance(capabilities, list) and capabilities:
            lines.append("Affected capabilities:")
            lines.extend(f"- `{capability}`" for capability in capabilities)
            lines.append("")
        verification = item.get("verification", [])
        if isinstance(verification, list) and verification:
            lines.append("Verification:")
            lines.extend(f"- `{entry}`" for entry in verification)
            lines.append("")
        outcome = str(item.get("outcome", "")).strip()
        if outcome and outcome != "See plan body closeout verification notes.":
            lines.append("Outcome:")
            lines.append(outcome)
            lines.append("")

    if lines[-1] == "":
        lines.pop()
    lines.append("")
    lines.append(GENERATED_HISTORY_END)
    return "\n".join(lines)


def build_feature_history(
    *,
    repo_root: Path,
    source: dict[str, object],
    existing_history_path: Path,
) -> str:
    feature_id = cast(str, source["feature_id"])
    default_heading = f"# {source.get('name', feature_id.replace('_', ' ').title())} History"
    existing_heading, existing_human_body = extract_existing_human_history(existing_history_path)
    heading = existing_heading or default_heading
    generated_section = build_generated_history_section(
        timeline=timeline_for_feature(repo_root, feature_id)
    )
    human_body = existing_human_body.strip()
    if not human_body:
        human_body = (
            "Add human narrative here only when operator context, rollout nuance, "
            "or meaning is needed beyond the generated plan history."
        )
    return (
        f"{heading}\n\n"
        f"{generated_section}\n\n"
        f"{HUMAN_HISTORY_HEADING}\n\n"
        f"{human_body.rstrip()}\n"
    )


def lineage_payload(
    repo_root: Path,
    feature_id: str,
    source: dict[str, object],
    evidence_index: EvidenceIndex,
) -> dict[str, object]:
    refs = generated_refs(feature_id, source, evidence_index)
    capabilities: dict[str, dict[str, object]] = {}
    for index, raw_capability in enumerate(cast(list[object], source.get("capabilities", []))):
        capability = normalize_capability(feature_id, raw_capability, index)
        capability_id = cast(str, capability["capability_id"])
        code = list(evidence_index.code_by_capability.get(capability_id, []))
        tests = list(evidence_index.tests_by_capability.get(capability_id, []))
        configs = list(evidence_index.configs_by_capability.get(capability_id, []))
        components = list(evidence_index.components_by_capability.get(capability_id, []))
        component_evidence = list(evidence_index.component_evidence_by_capability.get(capability_id, []))
        satisfies = list(evidence_index.satisfies_by_capability.get(capability_id, []))
        specs = list(refs.get("specs", []))
        plans = list(refs.get("plans", []))
        docs = list(refs.get("docs", []))
        evidence_gaps: list[str] = []
        if not code:
            evidence_gaps.append("missing_code_evidence")
        if not tests:
            evidence_gaps.append("missing_test_evidence")
        status = completeness_status(code, tests, specs, plans, configs, components)
        capabilities[capability_id] = {
            "state": capability["state"],
            "statement": capability["statement"],
            "satisfies": satisfies,
            "code": [node.as_dict() for node in code],
            "tests": [node.as_dict() for node in tests],
            "docs": docs,
            "docs_evidence": evidence_nodes(docs, "docs_frontmatter"),
            "configs": configs,
            "config_evidence": evidence_nodes(configs, "yaml_architecture"),
            "components": components,
            "component_evidence": component_evidence,
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

    return {
        "feature_id": feature_id,
        "source": f"docs/features/{feature_id}/feature.source.yaml",
        "invariants": invariants,
        "capabilities": capabilities,
        "timeline": timeline_for_feature(repo_root, feature_id),
    }


def render_feature_outputs(repo_root: Path, source_path: Path, evidence_index: EvidenceIndex) -> list[RenderedFile]:
    source = load_feature_source(source_path)
    feature_id = cast(str, source["feature_id"])
    return [
        RenderedFile(
            path=source_path.parent / "history.md",
            content=build_feature_history(
                repo_root=repo_root,
                source=source,
                existing_history_path=source_path.parent / "history.md",
            ),
        ),
        RenderedFile(
            path=generated_feature_contract_path(source_path),
            content=GENERATED_HEADER
            + dump_yaml(contract_payload(repo_root, feature_id, source, evidence_index)),
        ),
        RenderedFile(
            path=generated_lineage_path(source_path),
            content=GENERATED_HEADER + dump_yaml(lineage_payload(repo_root, feature_id, source, evidence_index)),
        ),
    ]


def stage_contract_payload(repo_root: Path, stage_id: str, stage_body: dict[str, object]) -> dict[str, object]:
    refs = cast(dict[str, object], stage_body.get("refs", {}))
    spec_refs = cast(list[str], refs.get("spec", [])) if isinstance(refs, dict) else []
    plan_refs = cast(list[str], refs.get("plan", [])) if isinstance(refs, dict) else []
    primary_features = cast(list[str], stage_body.get("primary_features", []))
    related_features = cast(list[str], stage_body.get("related_features", []))
    feature_refs = sorted_unique(primary_features + related_features)
    return {
        "stage_id": stage_id,
        "name": stage_body.get("name", stage_id.replace("_", " ").title()),
        "status": cast(object, stage_body.get("status", "active")),
        "purpose": normalize_prose(stage_body.get("summary", "")),
        "feature_refs": feature_refs,
        "capability_refs": stage_capability_refs(repo_root, stage_id),
        "code_refs": [],
        "test_refs": [],
        "doc_refs": sorted_unique(spec_refs + plan_refs),
        "config_refs": [],
        "component_refs": [],
        "depends_on": cast(list[str], stage_body.get("depends_on", [])),
        "inputs": cast(list[str], stage_body.get("inputs", [])),
        "outputs": cast(list[str], stage_body.get("outputs", [])),
        "invariants": cast(list[str], stage_body.get("boundaries", [])),
        "human_notes": cast(list[str], stage_body.get("keywords", [])),
    }


def render_stage_outputs(repo_root: Path, source_path: Path) -> list[RenderedFile]:
    stage_id, stage_body = load_stage_source(source_path)
    return [
        RenderedFile(
            path=generated_stage_contract_path(source_path),
            content=GENERATED_HEADER + dump_yaml(stage_contract_payload(repo_root, stage_id, stage_body)),
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
                "type": "feature",
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
                    "type": "capability",
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
                "type": "stage",
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
        lineage = lineage_payload(repo_root, feature_id, source, evidence_index)
        capability_ids = sorted(cast(dict[str, object], lineage["capabilities"]).keys())
        features[feature_id] = {
            "summary": normalize_prose(source.get("summary", "")),
            "status": source.get("status", "unknown"),
            "type": source.get("type", "unknown"),
            "lineage_file": f"docs/features/{feature_id}/lineage.generated.yaml",
            "capability_count": len(capability_ids),
            "capabilities": capability_ids,
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
        rendered.extend(render_stage_outputs(repo_root, source_path))
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
    if args.validate_only:
        print("Architecture metadata inputs validated.")
        return 0
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

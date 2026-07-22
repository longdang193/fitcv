from __future__ import annotations

import pytest

from fitcv_cp.synonym_policy_io import (
    export_synonym_backup_zip,
    inspect_synonym_backup_zip,
    load_global_synonym_map,
    parse_synonym_editor_text,
    persist_global_synonym_map,
    repair_synonym_policy_mirrors,
    replace_yaml_top_level_mapping_block,
)


@pytest.mark.parametrize(
    "module_path",
    [
        "fitcv_cp.app",
        "fitcv_cp.worker_job",
    ],
)
def test_replace_yaml_top_level_mapping_block_preserves_other_sections(module_path: str) -> None:
    module = __import__(module_path, fromlist=["_replace_yaml_top_level_mapping_block"])
    replace_block = getattr(module, "_replace_yaml_top_level_mapping_block")

    raw = (
        "# header\n"
        "domain_alias_map: {}\n"
        "domain_neighbors: {}\n"
    )
    updated = replace_block(
        raw_yaml=raw,
        key="domain_alias_map",
        mappings={"b": "x", "a": "y"},
    )
    assert updated.startswith("# header\n")
    assert "domain_neighbors: {}\n" in updated
    assert "domain_alias_map:\n" in updated
    assert "  a: y\n" in updated
    assert "  b: x\n" in updated


@pytest.mark.parametrize(
    "module_path,key",
    [
        ("fitcv_cp.app", "domain_alias_map"),
        ("fitcv_cp.app", "role_family_alias_map"),
        ("fitcv_cp.worker_job", "domain_alias_map"),
        ("fitcv_cp.worker_job", "role_family_alias_map"),
    ],
)
def test_replace_yaml_top_level_mapping_block_overwrites_existing_multiline(
    module_path: str,
    key: str,
) -> None:
    module = __import__(module_path, fromlist=["_replace_yaml_top_level_mapping_block"])
    replace_block = getattr(module, "_replace_yaml_top_level_mapping_block")

    raw = (
        "# header\n"
        f"{key}:\n"
        "  z: w\n"
        "  a: b\n"
        "\n"
        "some_other_key: 1\n"
    )
    updated = replace_block(
        raw_yaml=raw,
        key=key,
        mappings={"b": "x", "a": "y"},
    )
    assert "# header\n" in updated
    assert "some_other_key: 1\n" in updated
    assert "  z: w\n" not in updated
    assert "  a: b\n" not in updated
    assert f"{key}:\n" in updated
    assert "  a: y\n" in updated
    assert "  b: x\n" in updated


@pytest.mark.parametrize(
    "module_path",
    [
        "fitcv_cp.app",
        "fitcv_cp.worker_job",
    ],
)
def test_replace_yaml_top_level_mapping_block_appends_when_missing(module_path: str) -> None:
    module = __import__(module_path, fromlist=["_replace_yaml_top_level_mapping_block"])
    replace_block = getattr(module, "_replace_yaml_top_level_mapping_block")

    raw = "# header\nsome_other_key: 1\n"
    updated = replace_block(
        raw_yaml=raw,
        key="role_family_alias_map",
        mappings={"alias": "canonical"},
    )
    assert updated.startswith("# header\n")
    assert "some_other_key: 1\n" in updated
    assert "role_family_alias_map:\n" in updated
    assert "  alias: canonical\n" in updated

def test_shared_policy_io_persists_terminal_mappings_atomically(tmp_path) -> None:
    path = tmp_path / "skill_synonyms.yaml"
    path.write_text("skill_synonyms:\n  existing: value\n", encoding="utf-8")

    persist_global_synonym_map(
        "skill",
        {"a": "b", "b": "c"},
        path=path,
    )

    assert load_global_synonym_map("skill", path=path) == {"a": "c", "b": "c"}

def test_shared_policy_io_rejects_cycle_before_file_replacement(tmp_path) -> None:
    path = tmp_path / "domain_synonyms.yaml"
    original = "domain_alias_map:\n  existing: value\ndomain_neighbors: {}\n"
    path.write_text(original, encoding="utf-8")

    with pytest.raises(ValueError, match="cycle"):
        persist_global_synonym_map(
            "domain",
            {"a": "b", "b": "a"},
            path=path,
        )

    assert path.read_text(encoding="utf-8") == original

def test_shared_replace_preserves_other_yaml_sections() -> None:
    updated = replace_yaml_top_level_mapping_block(
        raw_yaml="domain_alias_map: {}\ndomain_neighbors:\n  data: [analytics]\n",
        key="domain_alias_map",
        mappings={"fintech": "financial services"},
    )

    assert "domain_neighbors:\n  data: [analytics]\n" in updated

def test_repair_synonym_policy_mirrors_replaces_all_owned_mappings_and_preserves_other_sections(tmp_path) -> None:
    paths = {
        "skills": tmp_path / "skill_synonyms.yaml",
        "domain": tmp_path / "domain_synonyms.yaml",
        "role_family": tmp_path / "role_family_synonyms.yaml",
    }
    paths["skills"].write_text("skill_synonyms: {}\nmetadata: keep\n", encoding="utf-8")
    paths["domain"].write_text(
        "domain_alias_map: {}\ndomain_neighbors:\n  data: [analytics]\n",
        encoding="utf-8",
    )
    paths["role_family"].write_text("role_family_alias_map: {}\n", encoding="utf-8")

    checksums = repair_synonym_policy_mirrors(
        {
            "skills": {"js": "javascript"},
            "domain": {"fintech": "financial services"},
            "role_family": {"analyst": "data analyst"},
        },
        paths=paths,
    )

    assert set(checksums) == {"skills", "domain", "role_family"}
    assert "metadata: keep\n" in paths["skills"].read_text(encoding="utf-8")
    assert "domain_neighbors:\n  data: [analytics]\n" in paths["domain"].read_text(encoding="utf-8")
    assert load_global_synonym_map("skills", path=paths["skills"]) == {"js": "javascript"}


def test_synonym_editor_parser_supports_comments_blank_lines_and_terminal_mappings() -> None:
    result = parse_synonym_editor_text(
        "skills",
        "# common aliases\njs: javascript\n\nnode: node.js\nnode.js: javascript\n",
    )

    assert result == {
        "mappings": {"js": "javascript", "node": "javascript", "node.js": "javascript"},
        "issues": [],
    }


def test_synonym_editor_parser_reports_stable_line_issues() -> None:
    result = parse_synonym_editor_text(
        "domain",
        "- analytics\n: data\nfintech:\ndata science: analytics\ndata-science: operations\n",
    )

    assert [(issue["code"], issue["lines"]) for issue in result["issues"]] == [
        ("synonym_list_syntax", [1]),
        ("synonym_empty_alias", [2]),
        ("synonym_missing_canonical", [3]),
        ("synonym_alias_conflict", [4, 5]),
    ]
    assert all(issue["severity"] == "error" for issue in result["issues"])


def test_synonym_editor_parser_reports_cycle_lines() -> None:
    result = parse_synonym_editor_text("role_family", "analyst: engineer\nengineer: analyst\n")

    assert result["mappings"] == {}
    assert result["issues"] == [
        {
            "code": "synonym_cycle",
            "message": "Canonical mappings contain a cycle.",
            "severity": "error",
            "lines": [1, 2],
            "aliases": ["analyst", "engineer"],
            "canonicals": ["analyst", "engineer"],
        }
    ]


def test_synonym_backup_zip_contains_three_canonical_yaml_files_and_manifest() -> None:
    content = export_synonym_backup_zip(
        {
            "skills": {"js": "javascript"},
            "domain": {"fintech": "financial services"},
            "role_family": {"analyst": "data analyst"},
        },
        bundle_revision_id="bundle-1",
        bundle_checksum="bundle-sha",
        type_revisions={
            "skills": {"type_revision_id": "skills-3", "revision": 3},
            "domain": {"type_revision_id": "domain-2", "revision": 2},
            "role_family": {"type_revision_id": "role-4", "revision": 4},
        },
        exported_at="2026-07-21T00:00:00+00:00",
    )

    inspected = inspect_synonym_backup_zip(content)

    assert inspected["policies"]["skills"] == {"js": "javascript"}
    assert inspected["manifest"]["bundle_revision_id"] == "bundle-1"
    assert inspected["manifest"]["type_revisions"] == {
        "domain": {"revision": 2, "type_revision_id": "domain-2"},
        "role_family": {"revision": 4, "type_revision_id": "role-4"},
        "skills": {"revision": 3, "type_revision_id": "skills-3"},
    }


def test_synonym_backup_zip_rejects_unexpected_or_traversal_members() -> None:
    import io
    import zipfile

    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("../skill_synonyms.yaml", "skill_synonyms: {}\n")

    with pytest.raises(ValueError, match="member"):
        inspect_synonym_backup_zip(stream.getvalue())

def test_synonym_backup_zip_rejects_manifest_without_type_revisions() -> None:
    import io
    import json
    import zipfile

    content = export_synonym_backup_zip(
        {"skills": {}, "domain": {}, "role_family": {}},
        bundle_revision_id="bundle-1",
        bundle_checksum="bundle-sha",
        type_revisions={
            "skills": {"type_revision_id": "skills-1", "revision": 1},
            "domain": {"type_revision_id": "domain-1", "revision": 1},
            "role_family": {"type_revision_id": "role-1", "revision": 1},
        },
        exported_at="2026-07-21T00:00:00+00:00",
    )
    with zipfile.ZipFile(io.BytesIO(content)) as source:
        members = {name: source.read(name) for name in source.namelist()}
    manifest = json.loads(members["manifest.json"])
    manifest.pop("type_revisions")
    members["manifest.json"] = json.dumps(manifest).encode("utf-8")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, value in members.items():
            archive.writestr(name, value)

    with pytest.raises(ValueError, match="manifest"):
        inspect_synonym_backup_zip(stream.getvalue())


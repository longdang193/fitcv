from __future__ import annotations

import pytest

from fitcv_cp.synonym_policy_io import (
    load_global_synonym_map,
    persist_global_synonym_map,
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


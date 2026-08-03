"""
@meta
type: test
scope: unit
domain: config
covers:
  - configuration loading and validation
excludes:
  - external service connectivity
tags:
  - fast
  - ci-safe
"""
import shutil
import uuid
import os
from pathlib import Path

import pytest
import fitcv.config as config_module

from fitcv.config import (
    apply_runtime_synonym_overlay,
    apply_runtime_skill_synonym_overlay,
    get_cv_acceptance_policy,
    get_cv_generation_structured_prompt_id,
    get_ranking_ai_score_model,
    get_ranking_prompt_id,
    get_system_initial_backoff_seconds,
    get_system_maximum_attempts,
    get_stage_runtime_concurrency,
    load_config,
    load_control_plane_config,
    parse_runtime_synonym_overlay_yaml,
    parse_skill_synonym_overlay_yaml,
    resolve_model_routing_part,
    resolve_data_backend,
)
from fitcv.persistence import get_local_sqlite_path
from fitcv_cp.backend_runtime import set_backend_runtime
from fitcv_cp.sqlite_store import initialize_control_plane_database
from fitcv_cp.store import ControlPlaneStore


def test_system_retry_accessors_read_frozen_runtime_snapshot() -> None:
    config = {
        "runtime_inputs": {
            "system_settings_snapshot": {
                "maximum_attempts": 4,
                "initial_backoff_seconds": 12,
                "revision": 7,
            }
        }
    }

    assert get_system_maximum_attempts(config) == 4
    assert get_system_initial_backoff_seconds(config) == 12


def test_system_retry_accessors_use_canonical_defaults_without_snapshot() -> None:
    assert get_system_maximum_attempts({}) == 3
    assert get_system_initial_backoff_seconds({}) == 10


def test_get_cv_acceptance_policy_defaults_when_missing() -> None:
    policy = get_cv_acceptance_policy({})
    assert policy["enabled"] is False
    assert policy["review_reason_code"] == "policy_acceptance"


def test_load_config_returns_dict() -> None:
    cfg = load_config(Path(__file__).parent.parent / ".env.yaml")
    assert isinstance(cfg, dict)
    assert "control_plane" not in cfg
    assert "pipeline" in cfg


def test_load_config_uses_local_candidate_profile_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate_path = tmp_path / "candidate_profile.yaml"
    monkeypatch.setenv("FITCV_LOCAL_CANDIDATE_PROFILE_PATH", str(candidate_path))

    cfg = load_config(Path(__file__).parent.parent / ".env.yaml")

    assert cfg["paths"]["candidate_profile"] == str(candidate_path)


def test_load_config_has_required_keys() -> None:
    cfg = load_config(Path(__file__).parent.parent / ".env.yaml")
    assert cfg["paths"]["candidate_profile"] == "data/candidate_profile.private.yaml"
    assert "bigquery_dataset" not in cfg
    assert "service_account_key" not in cfg


def test_load_config_raises_for_missing_file() -> None:
    import pytest
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/.env.yaml")


def test_load_config_allows_missing_legacy_cloud_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    isolated_root = tmp_path / "isolated" / "a" / "b" / "c" / "d"
    isolated_root.mkdir(parents=True)
    env_yaml = isolated_root / ".env.yaml"
    env_yaml.write_text("""some_key: value
""")
    cfg_dir = isolated_root / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        """cv:
  preset: europass
  generation:
    model: cx/gpt-5.4-mini
    prompt_version: v1
  composition:
    summary:
      enabled: true
  validation:
    max_pages: 2
"""
    )
    monkeypatch.delenv("GCP_PROJECT", raising=False)
    monkeypatch.delenv("FITCV_LLM_API_KEY", raising=False)

    cfg = load_config(env_yaml)

    assert cfg["cv"]["preset"] == "europass"
    assert resolve_data_backend(cfg) == "sqlite"


def test_load_config_sqlite_backend_allows_missing_cloud_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text("some_key: value\n")
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    monkeypatch.delenv("GCP_PROJECT", raising=False)
    monkeypatch.delenv("FITCV_LLM_API_KEY", raising=False)

    cfg = load_config(env_yaml)

    assert cfg["cv"]["preset"] == "europass"
    assert "gcp_project" not in cfg
    assert "bigquery_dataset" not in cfg
    assert "service_account_key" not in cfg


def test_load_config_ignores_gcp_project_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text("some_key: value\n")
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        """cv:
  preset: europass
  generation:
    model: cx/gpt-5.4-mini
    prompt_version: v1
  composition:
    summary:
      enabled: true
  content_rules:
    evidence_grounded_only: true
  validation:
    max_pages: 2
"""
    )
    monkeypatch.setenv("GCP_PROJECT", "env-project")

    cfg = load_config(env_yaml)

    assert "gcp_project" not in cfg
    assert "bigquery_dataset" not in cfg
    assert "service_account_key" not in cfg


def test_load_config_strips_bigquery_dataset_at_ingress(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "some_key: value\n"
        "bigquery_dataset: legacy_dataset\n",
        encoding="utf-8",
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        """cv:
  preset: europass
  generation:
    model: cx/gpt-5.4-mini
    prompt_version: v1
  composition:
    summary:
      enabled: true
  content_rules:
    evidence_grounded_only: true
  validation:
    max_pages: 2
"""
    )
    monkeypatch.delenv("GCP_PROJECT", raising=False)

    cfg = load_config(env_yaml)

    assert "bigquery_dataset" not in cfg
def test_get_local_sqlite_path_uses_control_plane_sqlite_path_when_env_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config" / "runtime").mkdir(parents=True)
    (tmp_path / "config" / "runtime" / "control_plane.yaml").write_text(
        "control_plane:\n"
        "  data_backend:\n"
        "    type: sqlite\n"
        "    sqlite:\n"
        f"      path: {tmp_path / 'from-config.sqlite3'}\n"
        "  providers:\n"
        "    openai_compatible:\n"
        "      base_url: https://example.test/v1\n"
        "      auth_mode: required\n"
        "      wire_api: responses\n"
        "      timeout_seconds: 30\n"
            "  model_routing:\n"
            "    parts:\n"
            "      candidate_profile_base_mapping: {provider: openai_compatible, model: m}\n"
            "      candidate_profile_derived_claims: {provider: openai_compatible, model: m}\n"
            "      enrich_extraction: {provider: openai_compatible, model: m}\n"
        "      ranking_ai_score: {provider: openai_compatible, model: m}\n"
        "      cv_generation_structured_write: {provider: openai_compatible, model: m}\n"
        "      synonym_triage_recommendation: {provider: openai_compatible, model: m}\n"
        "  fitcv_cp:\n"
        "    retry:\n"
        "      enabled: false\n"
        "      max_attempts: 1\n"
        "      backoff_seconds: [1]\n"
        "      lease_seconds: 900\n"
        "      reconciler_interval_seconds: 0\n"
        "      error_details_max_chars: 2048\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("FITCV_CP_SQLITE_PATH", raising=False)

    assert get_local_sqlite_path() == str(tmp_path / "from-config.sqlite3")


def test_load_control_plane_config_merges_narrow_local_overlay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    overlay_path = tmp_path / "local_controller_overlay.yaml"
    overlay_path.write_text(
        "version: 1\nproviders:\n  openai:\n    base_url: https://example.test/v1\n"
        "model_routing:\n  parts:\n    ranking_ai_score:\n      provider: openai\n      model: test-model\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("FITCV_LOCAL_CONTROLLER_OVERLAY_PATH", str(overlay_path))

    config = load_control_plane_config()

    assert config["providers"]["openai"]["base_url"] == "https://example.test/v1"
    assert config["providers"]["openai"]["wire_api"] == "chat_completions"
    assert config["model_routing"]["parts"]["ranking_ai_score"]["model"] == "test-model"


def test_load_control_plane_config_ignores_retired_overlay_after_local_migration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    overlay_path = tmp_path / "local_controller_overlay.yaml"
    overlay_path.write_text(
        "version: 1\nproviders:\n  openai:\n    base_url: https://example.test/v1\n"
        "model_routing:\n  parts:\n    ranking_ai_score:\n      provider: openai\n      model: test-model\n",
        encoding="utf-8",
    )
    database_path = tmp_path / "fitcv.sqlite3"
    set_backend_runtime(None)
    initialize_control_plane_database(database_path, tmp_path / "candidate_profile.yaml")
    monkeypatch.setenv("FITCV_LOCAL_MODE", "1")
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(database_path))
    monkeypatch.setenv("FITCV_LOCAL_CONTROLLER_OVERLAY_PATH", str(overlay_path))
    ControlPlaneStore().record_integration_migration(
        "packaged_local_complete_integration_v1",
        details={},
    )

    config = load_control_plane_config()

    assert config["providers"]["openai"]["base_url"] == "https://api.openai.com/v1"
    assert config["model_routing"]["parts"]["ranking_ai_score"]["model"] != "test-model"




def test_get_stage_runtime_concurrency_clamps_and_defaults() -> None:
    assert get_stage_runtime_concurrency({"stage_runtime": {"cv_generation": {"concurrency": 3}}}, stage="cv_generation") == 3
    assert get_stage_runtime_concurrency({"stage_runtime": {"cv_generation": {"concurrency": 0}}}, stage="cv_generation") == 1
    assert get_stage_runtime_concurrency({"stage_runtime": {"cv_generation": {"concurrency": "bad"}}}, stage="cv_generation") == 1

def test_llm_request_start_interval_defaults_and_rejects_invalid_values() -> None:
    accessor = getattr(config_module, "get_llm_request_start_interval_secs", None)
    assert accessor is not None
    assert accessor({}) == 0.0
    assert accessor({"llm_runtime": {"request_start_interval_secs": 1.25}}) == pytest.approx(1.25)
    assert accessor({"llm_runtime": {"request_start_interval_secs": -1}}) == 0.0
    assert accessor({"llm_runtime": {"request_start_interval_secs": float("inf")}}) == 0.0
    assert accessor({"llm_runtime": {"request_start_interval_secs": float("nan")}}) == 0.0

def test_get_stage_runtime_concurrency_prefers_canonical_stage_runtime() -> None:
    cfg = {"stage_runtime": {"enrich": {"concurrency": 4}}}
    assert get_stage_runtime_concurrency(
        cfg,
        stage="enrich",
        default=1,
    ) == 4


def test_load_config_defaults_to_repo_config_shape() -> None:
    cfg = load_config()
    assert cfg["llm_runtime"] == {"request_start_interval_secs": 0.0}
    assert cfg["stage_runtime"] == {
        "enrich": {"concurrency": 8},
        "ranking": {"concurrency": 4},
        "cv_analysis": {"concurrency": 4},
        "cv_generation": {"concurrency": 4},
    }
    for retired_key in (
        "enrichment_sleep_secs",
        "enrichment_batch_size",
        "enrichment_concurrency",
        "enrichment_max_retries",
        "rerank_sleep_secs",
    ):
        assert retired_key not in cfg
    assert "gemini_model" not in cfg
    assert "vertex_location" not in cfg
    assert cfg["paths"]["candidate_profile"] == "data/candidate_profile.private.yaml"
    assert cfg["pipeline"]["vector_search_top_n"] == 50
    assert cfg["pipeline"]["ai_score_top_n"] == 50
    assert cfg["pipeline"]["final_top_n"] == 15
    assert cfg["pipeline"]["evidence_top_k"] == 5
    assert cfg["vector_top_n"] == cfg["pipeline"]["vector_search_top_n"]
    assert cfg["rerank_top_n"] == cfg["pipeline"]["ai_score_top_n"]
    assert cfg["pipeline"]["shortlist_audit_sample_n"] == 5


@pytest.mark.parametrize("key", ["shortlist_lexical", "retrieval_strategy"])
def test_load_config_rejects_retired_shortlist_keys(tmp_path: Path, key: str) -> None:
    env_yaml = _write_minimal_eligibility_config(tmp_path)
    env_yaml.write_text(f"gcp_project: test\n{key}: legacy\n", encoding="utf-8")

    with pytest.raises(ValueError, match=key):
        load_config(env_yaml)


def test_load_config_rejects_stale_shortlist_lexical_file(tmp_path: Path) -> None:
    env_yaml = _write_minimal_eligibility_config(tmp_path)
    (tmp_path / "config" / "shortlist_lexical.yaml").write_text(
        "shortlist_lexical:\n  version: legacy\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="shortlist_lexical.yaml"):
        load_config(env_yaml)


def test_load_config_accepts_repo_root_env_yaml() -> None:
    cfg = load_config(Path(__file__).parent.parent / ".env.yaml")
    assert "gemini_model" not in cfg
    assert "vertex_location" not in cfg

def test_load_config_warns_when_legacy_compatibility_keys_present(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\n"
        "seniority_ladder:\n"
        "  - intern\n"
        "  - senior\n"
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    cfg = load_config(env_yaml)
    assert cfg["seniority"]["ladder"] == ["intern", "senior"]
    assert "Legacy compatibility keys detected in env config" in caplog.text

def test_load_config_rejects_deleted_legacy_env_path(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "config"
    (cfg_dir / "runtime").mkdir(parents=True)
    (cfg_dir / "policy").mkdir(parents=True)
    (cfg_dir / "taxonomy").mkdir(parents=True)

    root_env = tmp_path / ".env.yaml"
    root_env.write_text(
        "gcp_project: test\n"
        "vector_top_n: 50\n"
        "rerank_top_n: 40\n"
    )
    (cfg_dir / "runtime" / "pipeline.yaml").write_text(
        "pipeline:\n"
        "  vector_search_top_n: 50\n"
        "  ai_score_top_n: 40\n"
        "  final_top_n: 10\n"
        "  evidence_top_k: 5\n"
        "ai_score_model: cx/gpt-5.4-mini\n"
    )
    (cfg_dir / "policy" / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    (cfg_dir / "taxonomy" / "taxonomy.yaml").write_text("seniority:\n  ladder:\n    - intern\n")

    cfg_from_root = load_config(root_env)

    assert cfg_from_root["pipeline"]["vector_search_top_n"] == 50
    assert cfg_from_root["pipeline"]["ai_score_top_n"] == 40
    with pytest.raises(FileNotFoundError):
        load_config(cfg_dir / "env.yaml")

def test_resolve_data_backend_env_override_is_invariant(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_a = {"some_key": "value"}
    cfg_b = {"control_plane": {"data_backend": {"type": "sqlite"}}}
    assert resolve_data_backend(cfg_a) == "sqlite"
    assert resolve_data_backend(cfg_b) == "sqlite"

def test_resolve_data_backend_prefers_control_plane_over_legacy_bridge_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "config" / "runtime").mkdir(parents=True)
    (tmp_path / "config" / "runtime" / "control_plane.yaml").write_text(
        "control_plane:\n"
        "  data_backend:\n"
        "    type: sqlite\n"
    )
    monkeypatch.chdir(tmp_path)
    
    cfg = {"some_key": "value"}

    assert resolve_data_backend(cfg) == "sqlite"


def test_load_config_prefers_reorganized_config_subfolders_over_legacy_flat_files(tmp_path: Path) -> None:
    """@proves settings_system.baseline-default-hydration"""
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\n"
    )
    cfg_dir = tmp_path / "config"
    (cfg_dir / "runtime").mkdir(parents=True)
    (cfg_dir / "policy").mkdir()
    (cfg_dir / "taxonomy").mkdir()

    (cfg_dir / "runtime" / "pipeline.yaml").write_text(
        "ai_score_model: new-model\n"
        "embedding_model: new-embedding\n"
        "pipeline:\n"
        "  vector_search_top_n: 12\n"
        "  ai_score_top_n: 11\n"
        "  final_top_n: 7\n"
        "  evidence_top_k: 3\n"
    )
    (cfg_dir / "policy" / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "  content_rules:\n"
        "    evidence_grounded_only: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    (cfg_dir / "taxonomy" / "skill_synonyms.yaml").write_text(
        "skill_synonyms:\n"
        "  gcp: google cloud new\n"
    )
    (cfg_dir / "skill_synonyms.yaml").write_text(
        "skill_synonyms:\n"
        "  gcp: google cloud legacy\n"
    )
    (cfg_dir / "pipeline.yaml").write_text(
        "ai_score_model: legacy-model\n"
        "embedding_model: legacy-embedding\n"
        "pipeline:\n"
        "  vector_search_top_n: 99\n"
        "  ai_score_top_n: 98\n"
        "  final_top_n: 97\n"
        "  evidence_top_k: 9\n"
    )

    cfg = load_config(env_yaml)

    assert cfg["ai_score_model"] == "new-model"
    assert cfg["embedding_model"] == "new-embedding"
    assert cfg["pipeline"]["vector_search_top_n"] == 12
    assert cfg["skill_synonyms"]["gcp"] == "google cloud new"
    assert Path(cfg["skill_synonyms_runtime"]["base_policy_path"]).as_posix().endswith(
        "config/taxonomy/skill_synonyms.yaml"
    )


# ── Task 1: cv.yaml config layer tests ────────────────────────────────────────


def test_load_config_includes_cv_defaults() -> None:
    """@proves settings_system.cv-generation-settings"""
    cfg = load_config()
    assert cfg["cv_generation_model"] == "cx/gpt-5.4-mini"
    assert cfg["cv"]["generation"]["model"] == "cx/gpt-5.4-mini"
    assert cfg["cv"]["preset"] == "europass"
    assert cfg["cv"]["composition"]["summary"]["enabled"] is True
    assert cfg["cv"]["validation"]["max_pages"] == 2
    assert cfg["cv"]["generation"]["prompt_version"] == "v1"


def test_load_config_cv_keys_missing_raises(tmp_path: Path) -> None:
    """A config without cv.yaml keys should raise ValueError after loader validation."""
    isolated_root = tmp_path / "isolated" / "a" / "b" / "c" / "d"
    isolated_root.mkdir(parents=True)
    env_yaml = isolated_root / ".env.yaml"
    env_yaml.write_text("gcp_project: test\n")
    # No cv.yaml → missing top-level 'cv' key → ValueError
    with pytest.raises(ValueError, match="Missing top-level 'cv' key"):
        load_config(env_yaml)


def test_load_config_cv_required_sections_must_be_nonempty_list(tmp_path: Path) -> None:
    """required_cv_sections must be derivable from enabled composition sections."""
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text("gcp_project: test\n")
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    # composition with an enabled section → required_cv_sections will be non-empty
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "    experience:\n"
        "      enabled: true\n"
        "  content_rules:\n"
        "    evidence_grounded_only: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    cfg = load_config(env_yaml)
    assert "Experience" in cfg["required_cv_sections"]


def test_load_config_cv_max_pages_must_be_positive(tmp_path: Path) -> None:
    """cv.validation.max_pages must be a positive integer."""
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text("gcp_project: test\n")
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "  content_rules:\n"
        "    evidence_grounded_only: true\n"
        "  validation:\n"
        "    max_pages: 0\n"
    )
    with pytest.raises(ValueError, match="max_pages"):
        load_config(env_yaml)


def test_load_config_env_yaml_overrides_nested_cv(tmp_path: Path) -> None:
    """.env.yaml keys take precedence over nested cv values in cv.yaml."""
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: my-custom-model\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "  content_rules:\n"
        "    evidence_grounded_only: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    # cv.yaml also has generation.model — but env.yaml wins
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "  content_rules:\n"
        "    evidence_grounded_only: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    cfg = load_config(env_yaml)
    # env.yaml value wins
    assert cfg["cv_generation_model"] == "my-custom-model"
    assert cfg["cv"]["generation"]["model"] == "my-custom-model"


def test_load_config_merges_skill_synonym_overlay_paths(tmp_path: Path) -> None:
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\n"
        "skill_synonyms_overlay_paths:\n"
        "  - skill_synonyms.overlay.yaml\n"
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "skill_synonyms.yaml").write_text(
        "skill_synonyms:\n"
        "  gcp: google cloud\n"
        "  powerbi: power bi\n"
    )
    (cfg_dir / "skill_synonyms.overlay.yaml").write_text(
        "skill_synonyms:\n"
        "  gcp: gcp cloud\n"
        "  ga4: google analytics\n"
    )
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "  content_rules:\n"
        "    evidence_grounded_only: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )

    cfg = load_config(env_yaml)

    assert cfg["skill_synonyms"]["gcp"] == "gcp cloud"
    assert cfg["skill_synonyms"]["powerbi"] == "power bi"
    assert cfg["skill_synonyms"]["ga4"] == "google analytics"
    assert cfg["skill_synonyms_runtime"]["has_overlay"] is True
    assert len(cfg["skill_synonyms_runtime"]["overlay_paths"]) == 1

def test_load_config_rejects_duplicate_keys_in_skill_synonym_overlay(tmp_path: Path) -> None:
    env_yaml = _write_minimal_eligibility_config(tmp_path)
    env_yaml.write_text(
        "gcp_project: test\n"
        "skill_synonyms_overlay_paths:\n"
        "  - duplicate.overlay.yaml\n",
        encoding="utf-8",
    )
    (tmp_path / "config" / "duplicate.overlay.yaml").write_text(
        "skill_synonyms:\n"
        "  looker: looker studio\n"
        "  looker: powerbi\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"duplicate\.overlay\.yaml.*duplicate YAML key.*looker"):
        load_config(env_yaml)


def test_load_config_normalizes_role_taxonomy_structure(tmp_path: Path) -> None:
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\n"
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "taxonomy.yaml").write_text(
        "role_taxonomy:\n"
        "  canonical_roles:\n"
        "    data analyst:\n"
        "      aliases:\n"
        "        - BI Analyst\n"
        "        - Business Intelligence Analyst\n"
        "  role_families:\n"
        "    analytics:\n"
        "      roles:\n"
        "        - Data Analyst\n"
        "  role_family_neighbors:\n"
        "    analytics:\n"
        "      - data_science\n"
    )
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "  content_rules:\n"
        "    evidence_grounded_only: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )

    cfg = load_config(env_yaml)

    assert cfg["role_taxonomy"]["canonical_role_by_alias"]["bi analyst"] == "data analyst"
    assert cfg["role_taxonomy"]["canonical_role_by_alias"]["business intelligence analyst"] == "data analyst"
    assert cfg["role_taxonomy"]["role_family_by_role"]["data analyst"] == "analytics"
    assert cfg["role_taxonomy"]["role_family_neighbors"]["analytics"] == ("data_science",)

def test_load_config_normalizes_domain_and_role_family_alias_maps(tmp_path: Path) -> None:
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\n"
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "    experience:\n"
        "      enabled: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    (cfg_dir / "taxonomy.yaml").write_text(
        "domain_alias_map:\n"
        "  FinTech: Financial Services\n"
        "role_family_alias_map:\n"
        "  BI Analyst: analytics\n"
    )

    cfg = load_config(env_yaml)

    assert cfg["domain_alias_map"]["fintech"] == "financial services"
    assert cfg["role_family_alias_map"]["bi analyst"] == "analytics"

def test_load_config_normalizes_domain_and_role_family_neighbors(tmp_path: Path) -> None:
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\n"
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "    experience:\n"
        "      enabled: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    (cfg_dir / "taxonomy.yaml").write_text(
        "domain_neighbors:\n"
        "  Financial Services:\n"
        "    - FinTech\n"
        "role_family_neighbors:\n"
        "  analytics:\n"
        "    - data_science\n"
    )

    cfg = load_config(env_yaml)

    assert cfg["domain_neighbors"]["financial services"] == ("fintech",)
    assert cfg["role_family_neighbors"]["analytics"] == ("data_science",)

def test_load_config_prefers_dedicated_non_skill_synonym_files_over_taxonomy(tmp_path: Path) -> None:
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\n"
    )
    cfg_dir = tmp_path / "config"
    (cfg_dir / "taxonomy").mkdir(parents=True)
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    (cfg_dir / "taxonomy" / "taxonomy.yaml").write_text(
        "domain_alias_map:\n"
        "  FinTech: legacy domain\n"
        "role_family_alias_map:\n"
        "  BI Analyst: legacy family\n"
    )
    (cfg_dir / "taxonomy" / "domain_synonyms.yaml").write_text(
        "domain_alias_map:\n"
        "  FinTech: Financial Services\n"
    )
    (cfg_dir / "taxonomy" / "role_family_synonyms.yaml").write_text(
        "role_family_alias_map:\n"
        "  BI Analyst: analytics\n"
    )

    cfg = load_config(env_yaml)

    assert cfg["domain_alias_map"]["fintech"] == "financial services"
    assert cfg["role_family_alias_map"]["bi analyst"] == "analytics"

def test_load_config_falls_back_to_taxonomy_for_non_skill_synonym_maps(tmp_path: Path) -> None:
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\n"
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    (cfg_dir / "taxonomy.yaml").write_text(
        "domain_alias_map:\n"
        "  FinTech: Financial Services\n"
        "role_family_alias_map:\n"
        "  BI Analyst: analytics\n"
    )

    cfg = load_config(env_yaml)

    assert cfg["domain_alias_map"]["fintech"] == "financial services"
    assert cfg["role_family_alias_map"]["bi analyst"] == "analytics"

def test_load_config_rejects_synonym_duplicates_in_taxonomy_fallback_only(tmp_path: Path) -> None:
    env_yaml = _write_minimal_eligibility_config(tmp_path)
    (tmp_path / "config" / "taxonomy.yaml").write_text(
        "unrelated:\n"
        "  value: first\n"
        "  value: second\n"
        "domain_alias_map:\n"
        "  fintech: financial services\n"
        "  fintech: banking\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"taxonomy\.yaml.*duplicate YAML key.*fintech"):
        load_config(env_yaml)


def test_parse_skill_synonym_overlay_yaml_accepts_nested_skill_synonyms() -> None:
    overlay = parse_skill_synonym_overlay_yaml(
        "skill_synonyms:\n"
        "  PowerBI: power bi\n"
        "  GCP: google cloud\n"
    )

    assert overlay == {
        "powerbi": "power bi",
        "gcp": "google cloud",
    }


def test_parse_skill_synonym_overlay_yaml_rejects_invalid_mapping_values() -> None:
    with pytest.raises(ValueError, match="must be non-empty strings"):
        parse_skill_synonym_overlay_yaml(
            "skill_synonyms:\n"
            "  powerbi: ''\n"
        )

def test_parse_skill_synonym_overlay_yaml_rejects_duplicate_yaml_keys() -> None:
    with pytest.raises(ValueError, match="uploaded synonym overlay.*duplicate YAML key.*looker"):
        parse_skill_synonym_overlay_yaml(
            "skill_synonyms:\n"
            "  looker: looker studio\n"
            "  looker: powerbi\n"
        )

def test_parse_skill_synonym_overlay_yaml_rejects_normalized_alias_conflicts() -> None:
    with pytest.raises(ValueError, match="normalized synonym alias conflict: looker"):
        parse_skill_synonym_overlay_yaml(
            "skill_synonyms:\n"
            "  Looker: looker studio\n"
            "  looker: powerbi\n"
        )

def test_parse_skill_synonym_overlay_yaml_deduplicates_same_normalized_mapping() -> None:
    assert parse_skill_synonym_overlay_yaml(
        "skill_synonyms:\n"
        "  Looker: Looker Studio\n"
        "  ' looker ': looker studio\n"
    ) == {"looker": "looker studio"}

def test_parse_runtime_synonym_overlay_yaml_accepts_multi_field_sections() -> None:
    payload = parse_runtime_synonym_overlay_yaml(
        "skill_synonyms:\n"
        "  PowerBI: power bi\n"
        "domain_alias_map:\n"
        "  FinTech: Financial Services\n"
        "role_family_alias_map:\n"
        "  BI Analyst: analytics\n"
        "domain_neighbors:\n"
        "  Financial Services:\n"
        "    - Banking\n"
        "role_family_neighbors:\n"
        "  analytics:\n"
        "    - data_science\n"
    )

    assert payload["skill_synonyms"]["powerbi"] == "power bi"
    assert payload["domain_alias_map"]["fintech"] == "financial services"
    assert payload["role_family_alias_map"]["bi analyst"] == "analytics"
    assert payload["domain_neighbors"]["financial services"] == ("banking",)
    assert payload["role_family_neighbors"]["analytics"] == ("data_science",)

def test_apply_runtime_synonym_overlay_merges_multi_field_maps() -> None:
    cfg = {
        "skill_synonyms": {"gcp": "google cloud"},
        "domain_alias_map": {"fintech": "legacy"},
        "role_family_alias_map": {"bi analyst": "legacy_family"},
        "domain_neighbors": {"financial services": ("old_neighbor",)},
        "role_family_neighbors": {"analytics": ("old_family_neighbor",)},
        "skill_synonyms_runtime": {
            "base_policy_path": "config/taxonomy/skill_synonyms.yaml",
            "overlay_paths": [],
            "has_overlay": False,
            "entry_count": 1,
        },
    }

    updated = apply_runtime_synonym_overlay(
        cfg,
        {
            "skill_synonyms": {"gcp": "gcp cloud"},
            "domain_alias_map": {"fintech": "financial services"},
            "role_family_alias_map": {"bi analyst": "analytics"},
            "domain_neighbors": {"financial services": ("banking",)},
            "role_family_neighbors": {"analytics": ("data_science",)},
        },
        source="upload",
        filename="reviewed-synonyms.yaml",
        uploaded_at="2026-05-02T21:30:00Z",
    )

    assert updated["skill_synonyms"]["gcp"] == "gcp cloud"
    assert updated["domain_alias_map"]["fintech"] == "financial services"
    assert updated["role_family_alias_map"]["bi analyst"] == "analytics"
    assert updated["domain_neighbors"]["financial services"] == ("banking",)
    assert updated["role_family_neighbors"]["analytics"] == ("data_science",)
    assert updated["skill_synonyms_runtime"]["has_run_overlay"] is True
    assert updated["skill_synonyms_runtime"]["run_overlay_section_counts"]["domain_alias_map"] == 1



def test_apply_runtime_synonym_overlay_keeps_role_taxonomy_neighbors_in_sync() -> None:
    cfg = {
        "role_taxonomy": {
            "canonical_role_by_alias": {
                "data engineer": "data engineer",
                "platform engineer": "platform engineer",
            },
            "role_family_by_role": {
                "data engineer": "data_engineering",
                "platform engineer": "platform_engineering",
            },
            "role_family_neighbors": {},
        },
        "role_family_neighbors": {},
        "skill_synonyms_runtime": {},
    }

    updated = apply_runtime_synonym_overlay(
        cfg,
        {
            "role_family_neighbors": {"data_engineering": ("platform_engineering",)},
        },
        source="upload",
        filename="role-neighbors.yaml",
        uploaded_at="2026-06-25T15:10:00Z",
    )

    assert updated["role_family_neighbors"]["data_engineering"] == ("platform_engineering",)
    assert updated["role_taxonomy"]["role_family_neighbors"]["data_engineering"] == (
        "platform_engineering",
    )
def test_apply_runtime_skill_synonym_overlay_merges_entries_and_runtime_metadata() -> None:
    cfg = {
        "skill_synonyms": {
            "gcp": "google cloud",
            "powerbi": "power bi",
        },
        "skill_synonyms_runtime": {
            "base_policy_path": "config/taxonomy/skill_synonyms.yaml",
            "overlay_paths": [],
            "has_overlay": False,
            "entry_count": 2,
        },
    }

    updated = apply_runtime_skill_synonym_overlay(
        cfg,
        {
            "gcp": "gcp cloud",
            "ga4": "google analytics",
        },
        source="upload",
        filename="reviewed-skill-synonyms.yaml",
        uploaded_at="2026-04-02T21:30:00Z",
    )

    assert updated["skill_synonyms"]["gcp"] == "gcp cloud"
    assert updated["skill_synonyms"]["ga4"] == "google analytics"
    assert updated["skill_synonyms_runtime"]["has_run_overlay"] is True
    assert updated["skill_synonyms_runtime"]["run_overlay_filename"] == "reviewed-skill-synonyms.yaml"
    assert updated["skill_synonyms_runtime"]["run_overlay_entry_count"] == 2


# ── Task 1: nested preset-based cv config ─────────────────────────────────────


def test_load_config_returns_nested_cv_object() -> None:
    """load_config() must return a nested cv dict."""
    cfg = load_config()
    assert "cv" in cfg
    assert isinstance(cfg["cv"], dict)


def test_load_config_nested_cv_has_preset() -> None:
    cfg = load_config()
    assert "preset" in cfg["cv"]


def test_load_config_nested_cv_generation_has_model_and_prompt_version() -> None:
    """@proves settings_system.cv-generation-settings"""
    cfg = load_config()
    assert "generation" in cfg["cv"]
    assert "model" in cfg["cv"]["generation"]
    assert "prompt_version" in cfg["cv"]["generation"]


def test_load_config_nested_cv_validation_has_max_pages() -> None:
    cfg = load_config()
    assert "validation" in cfg["cv"]
    assert "max_pages" in cfg["cv"]["validation"]


def test_load_config_nested_cv_composition_has_sections() -> None:
    cfg = load_config()
    assert "composition" in cfg["cv"]
    assert isinstance(cfg["cv"]["composition"], dict)


def test_load_config_compatibility_projection_cv_generation_model() -> None:
    """Legacy flat key must still be projected during the migration window."""
    cfg = load_config()
    # Compatibility projection: flat key must be present for control-plane compatibility
    assert "cv_generation_model" in cfg
    # And must match the nested value
    assert cfg["cv_generation_model"] == cfg["cv"]["generation"]["model"]


def test_load_config_compatibility_projection_cv_max_pages() -> None:
    cfg = load_config()
    assert "cv_max_pages" in cfg
    assert cfg["cv_max_pages"] == cfg["cv"]["validation"]["max_pages"]


def test_load_config_compatibility_projection_prompt_version() -> None:
    cfg = load_config()
    assert "prompt_version" in cfg
    assert cfg["prompt_version"] == cfg["cv"]["generation"]["prompt_version"]


def test_load_config_compatibility_projection_required_cv_sections() -> None:
    cfg = load_config()
    assert "required_cv_sections" in cfg
    # required_cv_sections is derived from enabled composition sections
    assert isinstance(cfg["required_cv_sections"], list)
    assert len(cfg["required_cv_sections"]) > 0

def test_load_config_exposes_cv_acceptance_policy_runtime() -> None:
    cfg = load_config()
    assert "cv_acceptance_policy" in cfg
    runtime = cfg.get("cv_acceptance_policy_runtime")
    assert isinstance(runtime, dict)
    min_ratio = (((runtime.get("required_match") or {}).get("min_ratio_by_fit")) or {})
    max_missing = (((runtime.get("required_match") or {}).get("max_missing_by_fit")) or {})
    assert min_ratio.get("strong") == 0.8
    assert min_ratio.get("stretch") == 0.5
    assert max_missing.get("strong") == 0
    assert max_missing.get("stretch") == 1
    assert runtime.get("force_review_when_any_required_missing_for_fits") == ["stretch"]

def test_load_config_cv_acceptance_policy_defaults_when_env_missing(tmp_path: Path) -> None:
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text("gcp_project: test\n")
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "    experience:\n"
        "      enabled: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    cfg = load_config(env_yaml)
    runtime = cfg["cv_acceptance_policy_runtime"]
    min_ratio = runtime["required_match"]["min_ratio_by_fit"]
    max_missing = runtime["required_match"]["max_missing_by_fit"]
    assert min_ratio["strong"] == 0.8
    assert min_ratio["stretch"] == 0.5
    assert max_missing["strong"] == 0
    assert max_missing["stretch"] == 1
    assert runtime["force_review_when_any_required_missing_for_fits"] == []

def test_cv_policy_yaml_has_single_cv_acceptance_policy_declaration() -> None:
    env_yaml = (Path(__file__).parent.parent / "config" / "policy" / "cv.yaml").read_text(encoding="utf-8")
    assert env_yaml.count("\ncv_acceptance_policy:") == 1

def test_control_plane_config_does_not_expose_dead_cv_analysis_semantic_alignment_part() -> None:
    control_plane = load_control_plane_config()
    parts = (((control_plane.get("model_routing") or {}).get("parts")) or {})
    assert "cv_analysis_semantic_alignment" not in parts

def test_load_config_preserves_legacy_compatibility_projection_for_seniority_ladder(tmp_path: Path) -> None:
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\n"
        "seniority_ladder:\n"
        "  - junior\n"
        "  - senior\n",
        encoding="utf-8",
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "    experience:\n"
        "      enabled: true\n"
        "  validation:\n"
        "    max_pages: 2\n",
        encoding="utf-8",
    )

    cfg = load_config(env_yaml)
    seniority = dict(cfg.get("seniority") or {})
    assert seniority.get("ladder") == ["junior", "senior"]

def test_load_config_ignores_retired_live_smoke_surface(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\n",
        encoding="utf-8",
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "live_smoke.yaml").write_text(
        "ai_score_model: SHOULD_NOT_BE_OWNER\n",
        encoding="utf-8",
    )
    (cfg_dir / "pipeline.yaml").write_text(
        "ai_score_model: canonical-fallback\n",
        encoding="utf-8",
    )
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "    experience:\n"
        "      enabled: true\n"
        "  validation:\n"
        "    max_pages: 2\n",
        encoding="utf-8",
    )

    cfg = load_config(env_yaml)

    assert "gemini_model" not in cfg
    assert "Retired config surface detected and ignored" in caplog.text

def test_model_routing_part_owner_is_control_plane_not_pipeline_fallback() -> None:
    routing = resolve_model_routing_part("ranking_ai_score", model_fallback="fallback-only")
    assert routing["provider"] == "openai_compatible"
    assert routing["model"] == "cx/gpt-5.4-mini"

def test_model_routing_part_includes_provider_timeout_seconds() -> None:
    routing = resolve_model_routing_part("ranking_ai_score", model_fallback="fallback-only")

    assert routing["timeout_seconds"] == "300"


def test_load_config_nested_cv_validation_max_pages_positive(tmp_path: Path) -> None:
    """@proves settings_system.warning-only-cv-max-pages-validation-setting

    max_pages in the nested validation block must be a positive integer.
    """
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text("gcp_project: test\n")
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "    experience:\n"
        "      enabled: true\n"
        "  content_rules:\n"
        "    evidence_grounded_only: true\n"
        "  validation:\n"
        "    max_pages: 0\n"
    )
    with pytest.raises(ValueError, match="max_pages"):
        load_config(env_yaml)


# ── Task 2: preset registry ─────────────────────────────────────────────────────

def test_cv_presets_module_exists() -> None:
    """cv_presets.py must exist and define the preset registry."""
    from fitcv import cv_presets
    assert hasattr(cv_presets, "PRESET_REGISTRY")
    assert hasattr(cv_presets, "SUPPORTED_PRESETS")


def test_europass_is_a_supported_preset() -> None:
    from fitcv import cv_presets
    assert "europass" in cv_presets.SUPPORTED_PRESETS


def test_preset_registry_has_sections_for_europass() -> None:
    from fitcv import cv_presets
    europass = cv_presets.PRESET_REGISTRY["europass"]
    assert "sections" in europass
    sections = europass["sections"]
    expected = {"summary", "education", "experience", "skills", "certifications", "projects", "publications", "languages"}
    assert set(sections.keys()) >= expected


def test_preset_registry_defines_section_ordering() -> None:
    from fitcv import cv_presets
    europass = cv_presets.PRESET_REGISTRY["europass"]
    assert "section_order" in europass
    assert europass["section_order"][0] == "summary"


def test_preset_registry_defines_allowed_enum_values() -> None:
    from fitcv import cv_presets
    europass = cv_presets.PRESET_REGISTRY["europass"]
    assert "allowed_values" in europass
    allowed = europass["allowed_values"]
    # summary styles
    assert "summary" in allowed
    assert "concise" in allowed["summary"].get("style", [])
    # detail levels
    assert "compact" in allowed.get("detail", [])
    assert "standard" in allowed.get("detail", [])
    assert "detailed" in allowed.get("detail", [])


def test_preset_registry_maps_template_path_for_europass() -> None:
    from fitcv import cv_presets
    europass = cv_presets.PRESET_REGISTRY["europass"]
    assert "template_path" in europass
    assert isinstance(europass["template_path"], str)
    assert europass["template_path"] == "templates/cv_template.md"


def test_get_section_order_returns_europass_order() -> None:
    from fitcv import cv_presets
    order = cv_presets.get_section_order("europass")
    assert order[0] == "summary"
    assert "experience" in order


def test_validate_composition_rejects_unknown_section() -> None:
    from fitcv import cv_presets
    bad_composition = {"unknown_section": {"enabled": True}}
    result = cv_presets.validate_composition("europass", bad_composition)
    assert result["valid"] is False
    assert any("unknown_section" in err for err in result["errors"])


def test_validate_composition_accepts_valid_europass() -> None:
    """@proves settings_system.cv-composition-visibility-settings"""
    from fitcv import cv_presets
    valid_composition = {
        "summary": {"enabled": True, "style": "concise"},
        "experience": {"enabled": True, "detail": "standard"},
    }
    result = cv_presets.validate_composition("europass", valid_composition)
    assert result["valid"] is True


def test_validate_composition_rejects_bad_enum_value() -> None:
    from fitcv import cv_presets
    bad_enum = {
        "summary": {"enabled": True, "style": "invalid_style"},
    }
    result = cv_presets.validate_composition("europass", bad_enum)
    assert result["valid"] is False
    assert any("invalid_style" in err for err in result["errors"])


def test_validate_composition_rejects_unknown_preset() -> None:
    from fitcv import cv_presets
    result = cv_presets.validate_composition("unknown_preset", {"summary": {"enabled": True}})
    assert result["valid"] is False
    assert any("unknown_preset" in err for err in result["errors"])


# ── Task 6: compatibility shim guard ───────────────────────────────────────────

def test_load_config_compatibility_flat_keys_work_after_nested_migration() -> None:
    """@proves settings_system.baseline-default-hydration"""
    cfg = load_config()
    # These are the keys the control plane (settings_schema) still reads
    assert cfg["cv_generation_model"] == cfg["cv"]["generation"]["model"]
    assert cfg["prompt_version"] == cfg["cv"]["generation"]["prompt_version"]
    assert cfg["cv_max_pages"] == cfg["cv"]["validation"]["max_pages"]
    assert isinstance(cfg["required_cv_sections"], list)
    # required_cv_sections is derived from composition
    assert len(cfg["required_cv_sections"]) > 0


def test_load_config_compatibility_required_cv_sections_from_composition() -> None:
    """required_cv_sections is derived from enabled composition sections."""
    cfg = load_config()
    # projects is enabled in cv.yaml, so it should appear in required_cv_sections
    assert "Projects" in cfg["required_cv_sections"]
    # publications has enabled:false, so it should NOT appear
    assert "Publications" not in cfg["required_cv_sections"]


def test_required_cv_sections_includes_education_when_enabled() -> None:
    """Education appears in required_cv_sections when enabled:true."""
    cfg = load_config()
    assert "Education" in cfg["required_cv_sections"]


def test_required_cv_sections_includes_summary_when_enabled() -> None:
    cfg = load_config()
    assert "Summary" in cfg["required_cv_sections"]


def test_required_cv_sections_excludes_education_when_disabled(tmp_path: Path) -> None:
    """Education must NOT appear in required_cv_sections when enabled:false."""
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text("gcp_project: test\n")
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    education:\n"
        "      enabled: false\n"
        "    experience:\n"
        "      enabled: true\n"
        "  content_rules:\n"
        "    evidence_grounded_only: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    cfg = load_config(env_yaml)
    assert "Education" not in cfg["required_cv_sections"]
    assert "Experience" in cfg["required_cv_sections"]


def test_required_cv_sections_excludes_summary_when_disabled(tmp_path: Path) -> None:
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text("gcp_project: test\n")
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: false\n"
        "      style: concise\n"
        "    experience:\n"
        "      enabled: true\n"
        "  content_rules:\n"
        "    evidence_grounded_only: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    cfg = load_config(env_yaml)
    assert "Summary" not in cfg["required_cv_sections"]
    assert "Experience" in cfg["required_cv_sections"]


def test_load_config_adds_default_enrich_prompt_id() -> None:
    cfg = load_config()

    assert cfg["prompts"]["enrich"]["extraction"]["prompt_id"] == "enrich.extraction.v1"


def test_load_config_adds_default_ranking_and_cv_generation_prompt_ids() -> None:
    cfg = load_config()

    assert cfg["prompts"]["candidate_profile"]["base_mapping"]["prompt_id"] == "candidate_profile.base_mapping.v1"
    assert cfg["prompts"]["candidate_profile"]["derived_claims"]["prompt_id"] == "candidate_profile.derived_claims.v1"
    assert cfg["prompts"]["ranking"]["ai_score"]["prompt_id"] == "ranking.ai_score.v2"
    assert cfg["prompts"]["cv_generation"]["structured_write"]["prompt_id"] == "cv_generation.structured_write.v1"


def test_load_config_builds_prompts_runtime_for_all_major_stages() -> None:
    """@proves cv_system.config-owned-generation-contract"""
    cfg = load_config()

    assert cfg["prompts_runtime"]["candidate_profile"]["base_mapping"]["prompt_id"] == "candidate_profile.base_mapping.v1"
    assert cfg["prompts_runtime"]["candidate_profile"]["derived_claims"]["prompt_id"] == "candidate_profile.derived_claims.v1"
    assert cfg["prompts_runtime"]["enrich"]["extraction"]["prompt_id"] == "enrich.extraction.v1"
    assert cfg["prompts_runtime"]["ranking"]["ai_score"]["prompt_id"] == "ranking.ai_score.v2"
    assert cfg["prompts_runtime"]["cv_generation"]["structured_write"]["prompt_id"] == "cv_generation.structured_write.v1"


def test_config_accessors_resolve_centralized_prompt_ids_and_model_defaults() -> None:
    """@proves pipeline_performance.enrich-extraction-prompt-text-now-comes-from-a-centralized-prompt-registry-with-config-selected-prompt-ids"""
    cfg = load_config()

    assert get_ranking_ai_score_model(cfg) == "cx/gpt-5.4-mini"
    assert get_ranking_prompt_id(cfg) == "ranking.ai_score.v2"
    assert get_cv_generation_structured_prompt_id(cfg) == "cv_generation.structured_write.v1"


def test_load_config_exposes_only_active_cv_generation_prompt_contract() -> None:
    """@proves cv_system.config-owned-generation-contract"""
    cfg = load_config()

    assert "write" not in cfg["prompts"]["cv_generation"]
    assert "write" not in cfg["prompts_runtime"]["cv_generation"]


def test_load_config_rejects_unknown_enrich_prompt_id() -> None:
    tmp_path = Path(".worktrees/Stage-by-stage-flow/tests") / f"tmp_prompt_config_{uuid.uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=False)
    try:
        env_yaml = tmp_path / ".env.yaml"
        env_yaml.write_text("gcp_project: test\n")
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        (cfg_dir / "cv.yaml").write_text(
            "cv:\n"
            "  preset: europass\n"
            "  generation:\n"
            "    model: cx/gpt-5.4-mini\n"
            "    prompt_version: v1\n"
            "  composition:\n"
            "    summary:\n"
            "      enabled: true\n"
            "      style: concise\n"
            "    experience:\n"
            "      enabled: true\n"
            "  content_rules:\n"
            "    evidence_grounded_only: true\n"
            "  validation:\n"
            "    max_pages: 2\n"
        )
        (cfg_dir / "pipeline.yaml").write_text(
            "prompts:\n"
            "  enrich:\n"
            "    extraction:\n"
            "      prompt_id: enrich.extraction.v999\n"
        )

        with pytest.raises(ValueError, match="Unknown enrich prompt_id"):
            load_config(env_yaml)
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)

def test_load_config_ssot_overlap_warn_mode_allows_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FITCV_CONFIG_SSOT_MODE", raising=False)
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\n"
        "ai_score_model: cx/gpt-5.4-mini\n"
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "pipeline.yaml").write_text("ai_score_model: cx/gpt-5.4-mini\n")
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "    experience:\n"
        "      enabled: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    cfg = load_config(env_yaml)
    assert "gemini_model" not in cfg

def test_load_config_ssot_overlap_strict_mode_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FITCV_CONFIG_SSOT_MODE", "strict")
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\n"
        "ai_score_model: cx/gpt-5.4-mini\n"
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "pipeline.yaml").write_text("ai_score_model: cx/gpt-5.4-mini\n")
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "    experience:\n"
        "      enabled: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    with pytest.raises(ValueError, match="Config SSOT ownership overlap detected|Config SSOT overlap detected"):
        load_config(env_yaml)

def test_load_config_rejects_invalid_ssot_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FITCV_CONFIG_SSOT_MODE", "bad-mode")
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\n"
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "    experience:\n"
        "      enabled: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    with pytest.raises(ValueError, match="SSOT enforcement mode must be one of"):
        load_config(env_yaml)

def test_resolve_data_backend_supports_legacy_sqlite_mode_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert resolve_data_backend({"sqlite_mode": True}) == "sqlite"
    assert resolve_data_backend({"sqlite_mode": False}) == "sqlite"






def _write_minimal_eligibility_config(root: Path, *, include_eligibility: bool = True) -> Path:
    env_yaml = root / ".env.yaml"
    env_yaml.write_text("gcp_project: test\n", encoding="utf-8")
    policy_dir = root / "config" / "policy"
    policy_dir.mkdir(parents=True)
    runtime_dir = root / "config" / "runtime"
    runtime_dir.mkdir()
    (runtime_dir / "pipeline.yaml").write_text(
        "pipeline:\n"
        "  vector_search_top_n: 50\n"
        "  shortlist_audit_sample_n: 5\n",
        encoding="utf-8",
    )
    (policy_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: cx/gpt-5.4-mini\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "    experience:\n"
        "      enabled: true\n"
        "  validation:\n"
        "    max_pages: 2\n",
        encoding="utf-8",
    )
    if include_eligibility:
        (policy_dir / "eligibility.yaml").write_text(
            "eligibility_policy:\n"
            "  policy_version: eligibility-v1\n"
            "  factors:\n"
            "    location_fit:\n"
            "      mode: ranking_only\n"
            "      normalization:\n"
            "        exact_city: 1.0\n"
            "        exact_region: 0.8\n"
            "        exact_country: 0.6\n"
            "        remote_unrestricted: 1.0\n"
            "        no_match: 0.0\n"
            "        unknown_value: 0.5\n"
            "        not_applicable_value: 0.5\n"
            "    language_fit:\n"
            "      mode: ranking_only\n"
            "      normalization:\n"
            "        met: 1.0\n"
            "        unmet: 0.0\n"
            "        unknown_value: 0.5\n"
            "        not_applicable_value: 0.5\n"
            "        requirement_weights:\n"
            "          required: 1.0\n"
            "          preferred: 0.5\n"
            "          unspecified: 0.5\n",
            encoding="utf-8",
        )
    return env_yaml


def test_load_config_loads_canonical_eligibility_policy_and_fingerprint(tmp_path: Path) -> None:
    env_yaml = _write_minimal_eligibility_config(tmp_path)

    cfg = load_config(env_yaml)

    assert cfg["eligibility_policy"]["policy_version"] == "eligibility-v1"
    assert cfg["eligibility_policy_fingerprint"] == (
        "3f26909a8b2e0eb492c3b9026b1326b5424026a0a65cf561a59b073ff5a7d953"
    )


def test_load_config_requires_canonical_eligibility_policy_in_strict_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_yaml = _write_minimal_eligibility_config(tmp_path, include_eligibility=False)
    monkeypatch.setenv("FITCV_CONFIG_SSOT_MODE", "strict")

    with pytest.raises(FileNotFoundError, match="eligibility.yaml"):
        load_config(env_yaml)


@pytest.mark.parametrize("shadow_owner", ["environment", "ranking"])
def test_load_config_rejects_eligibility_policy_shadow(
    tmp_path: Path,
    shadow_owner: str,
) -> None:
    env_yaml = _write_minimal_eligibility_config(tmp_path)
    if shadow_owner == "environment":
        env_yaml.write_text(
            "gcp_project: test\n"
            "eligibility_policy:\n"
            "  policy_version: shadow\n",
            encoding="utf-8",
        )
    else:
        ranking_path = tmp_path / "config" / "policy" / "ranking.yaml"
        ranking_path.write_text(
            "eligibility_policy:\n"
            "  policy_version: shadow\n",
            encoding="utf-8",
        )

    with pytest.raises(ValueError, match="eligibility_policy.*canonical"):
        load_config(env_yaml)


def _write_ranking_v2_policy(tmp_path: Path, *, extra: str = "") -> Path:
    ranking_path = tmp_path / "config" / "policy" / "ranking.yaml"
    ranking_path.write_text(
        "ranking_policy:\n"
        "  policy_version: ranking-v2\n"
        "  normalizer_version: absolute-fit-v1\n"
        "  active_baseline_mode: holistic_ai_only\n"
        "  baseline_weights:\n"
        "    holistic_ai_fit: 1.0\n"
        "    structured_fit: 0.0\n"
        "  structured_factor_weights:\n"
        "    must_have_match: 0.30\n"
        "    title_relevance: 0.20\n"
        "    seniority_fit: 0.15\n"
        "    declared_preference_fit: 0.15\n"
        "    location_fit: 0.10\n"
        "    language_fit: 0.10\n"
        "  declared_preference_component_weights:\n"
        "    domain: 0.50\n"
        "    role_family: 0.30\n"
        "    work_mode: 0.20\n"
        "  missing_value_defaults:\n"
        "    holistic_ai_fit: 0.0\n"
        "    must_have_match: 0.5\n"
        "    title_relevance: 0.5\n"
        "    seniority_fit: 0.5\n"
        "    declared_preference_fit: 0.5\n"
        "    location_fit: 0.5\n"
        "    language_fit: 0.5\n"
        "  fit_label_thresholds:\n"
        "    strong: 0.70\n"
        "    stretch: 0.40\n"
        "  label_migration_gate:\n"
        "    maximum_total_label_migration_rate: 0.10\n"
        "    maximum_strong_skip_crossings: 0\n"
        + extra,
        encoding="utf-8",
    )
    return ranking_path


def test_load_config_validates_ranking_v2_and_builds_contract_context(tmp_path: Path) -> None:
    env_yaml = _write_minimal_eligibility_config(tmp_path)
    _write_ranking_v2_policy(tmp_path)

    cfg = load_config(env_yaml)

    assert cfg["ranking_policy"]["policy_version"] == "ranking-v2"
    assert cfg["ranking_contract"]["ranking_contract_fingerprint"]
    assert "language_fit" in cfg["ranking_contract"]["effective_structured_factor_weights"]
    assert "ranking_weights" not in cfg


def test_load_config_rejects_unknown_ranking_v2_keys(tmp_path: Path) -> None:
    env_yaml = _write_minimal_eligibility_config(tmp_path)
    _write_ranking_v2_policy(tmp_path, extra="  unknown_key: true\n")

    with pytest.raises(ValueError, match="Unknown ranking_policy keys"):
        load_config(env_yaml)


def _write_decision_learning_policy(root: Path) -> None:
    (root / "config" / "policy" / "decision_learning.yaml").write_text(
        "decision_learning_policy:\n"
        "  policy_version: decision-learning-v2\n"
        "  domain_id: ranking_v1\n"
        "  rating_scale:\n"
        "    version: application-interest-v1\n"
        "    unrated_label: unrated\n"
        "    labels:\n"
        "      '1': definitely not interested\n"
        "      '2': low application interest\n"
        "      '3': might consider applying\n"
        "      '4': strong application interest\n"
        "      '5': would prioritize applying\n"
        "  preference_compiler:\n"
        "    compiler_version: preference-compiler-v1\n"
        "    minimum_rating_gap: 2\n"
        "    gap_evidence_weights:\n"
        "      '1': 1.0\n"
        "      '2': 2.0\n"
        "      '3': 3.0\n"
        "      '4': 4.0\n"
        "    max_episode_evidence_budget: 12.0\n"
        "  inverse_optimization:\n"
        "    optimizer_version: latent-residual-v1\n"
        "    learned_alpha: 0.05\n"
        "    learned_alpha_bounds:\n"
        "      minimum: 0.01\n"
        "      maximum: 0.10\n"
        "      step: 0.01\n"
        "    preference_margin: 0.02\n"
        "    preference_regularization: 1.0\n"
        "    preference_vector_norm_bound: 1.0\n"
        "    solver:\n"
        "      name: CLARABEL\n"
        "      max_iter: 200\n"
        "    numeric_tolerances:\n"
        "      feasibility_absolute: 1.0e-7\n"
        "      numeric_equivalence_absolute: 1.0e-6\n"
        "    evaluation:\n"
        "      evaluation_version: episode-grouped-v1\n"
        "      leave_one_episode_out_max_episodes: 8\n"
        "      grouped_fold_count: 5\n"
        "    activation:\n"
        "      activation_version: ranking-policy-lifecycle-v1\n"
        "      minimum_fold_vector_stability: 0.0\n",
        encoding="utf-8",
    )


def test_load_config_loads_decision_learning_policy_and_fingerprint(tmp_path: Path) -> None:
    env_yaml = _write_minimal_eligibility_config(tmp_path)
    _write_decision_learning_policy(tmp_path)

    cfg = load_config(env_yaml)

    assert cfg["decision_learning_policy"]["rating_scale"]["version"] == "application-interest-v1"
    assert cfg["decision_learning_policy"]["preference_compiler"]["minimum_rating_gap"] == 2
    assert cfg["decision_learning_policy"]["inverse_optimization"]["solver"]["name"] == "CLARABEL"
    assert cfg["decision_learning_policy"]["inverse_optimization"]["learned_alpha_bounds"] == {
        "minimum": 0.01,
        "maximum": 0.10,
        "step": 0.01,
    }
    assert len(cfg["decision_learning_policy_fingerprint"]) == 64


def test_load_config_requires_decision_learning_policy_in_strict_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_yaml = _write_minimal_eligibility_config(tmp_path)
    monkeypatch.setenv("FITCV_CONFIG_SSOT_MODE", "strict")

    with pytest.raises(FileNotFoundError, match="decision_learning.yaml"):
        load_config(env_yaml)


def test_load_config_rejects_decision_learning_policy_shadow(tmp_path: Path) -> None:
    env_yaml = _write_minimal_eligibility_config(tmp_path)
    env_yaml.write_text(
        "gcp_project: test\n"
        "decision_learning_policy:\n"
        "  policy_version: shadow\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="decision_learning_policy.*canonical"):
        load_config(env_yaml)


def test_apply_runtime_synonym_overlay_recompiles_semantic_policy() -> None:
    updated = apply_runtime_synonym_overlay(
        {
            "skill_synonyms": {"gcp": "google cloud"},
            "domain_alias_map": {},
            "role_family_alias_map": {},
        },
        {"skill_synonyms": {"k8s": "kubernetes"}},
        source="test",
        filename="overlay.yaml",
        uploaded_at="2026-07-17T00:00:00Z",
    )

    assert updated["semantic_policy"]["maps"]["skill"] == {
        "gcp": "google cloud",
        "k8s": "kubernetes",
    }

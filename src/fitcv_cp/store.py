"""@meta
name: store
type: module
domain: runtime
ownership: infrastructure
responsibility:
  - Module metadata placeholder for src.fitcv_cp.store.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterator
from typing import Any, Protocol, cast

from fitcv.inverse_optimization import InverseOptimizationRequest
from fitcv_cp.backend_runtime import BackendRuntime, set_backend_runtime
from fitcv_cp import sqlite_store
from fitcv_cp.models import PipelineRun, RunEvent
from fitcv_cp.run_artifact_contracts import decode_run_attempt_payload_or_none


class RunStore(Protocol):
    def get_api_provider_revision(self, provider_id: str) -> int: ...
    def list_custom_api_providers(self) -> list[dict[str, Any]]: ...
    def get_custom_api_provider(self, provider_id: str) -> dict[str, Any] | None: ...
    def create_custom_api_provider(self, provider_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def update_custom_api_provider(self, provider_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def delete_custom_api_provider(self, provider_id: str, **kwargs: Any) -> None: ...
    def delete_custom_api_provider_bundle(self, provider_id: str, **kwargs: Any) -> None: ...
    def get_api_provider_connection(self, provider_id: str) -> dict[str, Any] | None: ...
    def save_api_provider_connection(self, provider_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def delete_api_provider_connection(self, provider_id: str, **kwargs: Any) -> None: ...
    def list_api_provider_models(self, provider_id: str) -> list[dict[str, Any]]: ...
    def get_api_provider_model(self, model_record_id: str) -> dict[str, Any] | None: ...
    def create_api_provider_model(self, model_record_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def update_api_provider_model(self, model_record_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def delete_api_provider_model(self, model_record_id: str, **kwargs: Any) -> None: ...
    def integration_migration_applied(self, migration_key: str) -> bool: ...
    def record_integration_migration(self, migration_key: str, **kwargs: Any) -> dict[str, Any]: ...
    def list_candidate_profiles(self) -> list[dict[str, Any]]: ...
    def get_candidate_profile(self, candidate_profile_id: str) -> dict[str, Any] | None: ...
    def query_candidate_profiles(self, **kwargs: Any) -> dict[str, Any]: ...
    def create_candidate_profile_attempt(self, **kwargs: Any) -> dict[str, Any]: ...
    def query_candidate_profile_creation_attempts(self, **kwargs: Any) -> dict[str, Any]: ...
    def create_candidate_profile_creation_attempt(self, **kwargs: Any) -> dict[str, Any]: ...
    def get_candidate_profile_creation_attempt(self, attempt_id: str) -> dict[str, Any] | None: ...
    def get_candidate_profile_source(self, attempt_id: str) -> dict[str, Any] | None: ...
    def get_candidate_profile_source_block(self, attempt_id: str, source_block_id: str) -> dict[str, Any] | None: ...
    def get_candidate_profile_review(self, attempt_id: str, stage: str) -> dict[str, Any] | None: ...
    def patch_candidate_profile_review(self, attempt_id: str, stage: str, **kwargs: Any) -> dict[str, Any]: ...
    def regenerate_candidate_profile_review(self, attempt_id: str, stage: str, **kwargs: Any) -> dict[str, Any]: ...
    def undo_candidate_profile_regeneration(self, attempt_id: str, stage: str, **kwargs: Any) -> dict[str, Any]: ...
    def approve_candidate_profile_review(self, attempt_id: str, stage: str, **kwargs: Any) -> dict[str, Any]: ...
    def get_candidate_profile_confirmation(self, attempt_id: str) -> dict[str, Any] | None: ...
    def confirm_candidate_profile_creation_attempt(self, attempt_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def retry_candidate_profile_creation_attempt(self, attempt_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def claim_candidate_profile_processing(self, attempt_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def publish_candidate_profile_stage_result(self, attempt_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def fail_candidate_profile_stage(self, attempt_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def reconcile_candidate_profile_attempts(self, **kwargs: Any) -> dict[str, int]: ...
    def get_candidate_profile_detail(self, profile_id: str) -> dict[str, Any] | None: ...
    def query_candidate_profile_runs(self, profile_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def transition_candidate_profile_lifecycle(self, profile_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def delete_candidate_profile(self, profile_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def update_candidate_profile(self, profile_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def get_synonym_policy(self, synonym_type: str) -> dict[str, Any]: ...
    def save_synonym_policy_draft(self, synonym_type: str, **kwargs: Any) -> dict[str, Any]: ...
    def activate_synonym_policy_bundle(self, synonym_type: str, **kwargs: Any) -> dict[str, Any]: ...
    def activate_synonym_policy_bundle_set(self, policies: dict[str, dict[str, str]], **kwargs: Any) -> dict[str, Any]: ...
    def resolve_active_synonym_bundle(self) -> dict[str, Any]: ...
    def repair_active_synonym_policy_mirrors(self) -> dict[str, Any]: ...
    def ingest_synonym_suggestions(self, suggestions: list[dict[str, Any]]) -> dict[str, Any]: ...
    def query_synonym_suggestions(self, **kwargs: Any) -> dict[str, Any]: ...
    def get_synonym_suggestion(self, suggestion_id: str) -> dict[str, Any] | None: ...
    def apply_synonym_suggestion_action(self, suggestion_ids: list[str], **kwargs: Any) -> dict[str, Any]: ...
    def query_synonym_processing_runs(self, **kwargs: Any) -> dict[str, Any]: ...
    def query_tracked_companies(self, **kwargs: Any) -> dict[str, Any]: ...
    def create_tracked_company(self, **kwargs: Any) -> dict[str, Any]: ...
    def create_scan(self, **kwargs: Any) -> dict[str, Any]: ...
    def query_scans(self, **kwargs: Any) -> dict[str, Any]: ...
    def get_scan_detail(self, scan_id: str) -> dict[str, Any] | None: ...
    def request_scan_cancel(self, scan_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def commit_scan_output(self, scan_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def get_scan_output(self, scan_id: str) -> dict[str, Any] | None: ...
    def query_scan_jobs(self, scan_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def transition_scan_lifecycle(self, items: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]: ...
    def preview_delete_archived_scans(self, scan_ids: list[str], **kwargs: Any) -> dict[str, Any]: ...
    def delete_archived_scans(self, scan_ids: list[str], **kwargs: Any) -> dict[str, Any]: ...
    def insert_run(self, run: PipelineRun) -> None: ...
    def create_run_bundle(self, run: PipelineRun, *, input_resource: dict[str, Any], jobs: list[dict[str, Any]]) -> dict[str, Any]: ...
    def query_runs(self, **kwargs: Any) -> dict[str, Any]: ...
    def list_run_stages(self, run_id: str) -> list[dict[str, Any]]: ...
    def query_run_jobs(self, run_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def get_run_job(self, run_id: str, run_job_id: str) -> dict[str, Any] | None: ...
    def iter_run_jobs_for_export(self, run_id: str, **kwargs: Any) -> Iterator[dict[str, Any]]: ...
    def get_run_detail(self, run_id: str) -> dict[str, Any] | None: ...
    def set_bookmark(self, run_job_id: str) -> dict[str, Any]: ...
    def clear_bookmark(self, run_job_id: str) -> dict[str, Any]: ...
    def list_bookmarks(self) -> list[dict[str, Any]]: ...
    def query_bookmarks(self, **kwargs: Any) -> dict[str, Any]: ...
    def resolve_job_selection(self, run_job_ids: list[str], **kwargs: Any) -> dict[str, Any]: ...
    def remove_bookmarks(self, run_job_ids: list[str], **kwargs: Any) -> dict[str, Any]: ...
    def list_selected_jobs(self, run_job_ids: list[str], **kwargs: Any) -> list[dict[str, Any]]: ...
    def set_run_job_interest(self, run_job_id: str, rating: int, **kwargs: Any) -> dict[str, Any]: ...
    def clear_run_job_interest(self, run_job_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def reserve_idempotent_action(self, scope: str, key: str, fingerprint: str) -> dict[str, Any]: ...
    def complete_idempotent_action(self, action_id: str, response: dict[str, Any]) -> None: ...
    def complete_idempotent_binary_action(self, action_id: str, content: bytes, **kwargs: Any) -> None: ...
    def update_run_queue_job_id(self, run_id: str, queue_job_id: str, **kwargs: Any) -> dict[str, str]: ...
    def update_run_orchestration_binding(
        self,
        run_id: str,
        *,
        queue_job_id: str | None,
        orchestration_backend: str | None,
        orchestration_run_id: str | None,
    ) -> dict[str, str]: ...
    def get_run(self, run_id: str) -> PipelineRun | None: ...
    def list_runs(
        self,
        *,
        limit: int = 50,
        include_archived: bool = False,
        archived_only: bool = False,
    ) -> list[PipelineRun]: ...
    def get_events(self, run_id: str) -> list[RunEvent]: ...
    def get_process_events(self, process_type: str, process_id: str, *, limit: int = 200, cursor: str | None = None) -> dict[str, Any]: ...
    def update_run_status(self, run_id: str, status: Any, **kwargs: Any) -> dict[str, str]: ...
    def update_run_checkpoint(self, run_id: str, **kwargs: Any) -> dict[str, str]: ...
    def request_run_cancel(
        self,
        run_id: str,
        requested_by: str,
        target_status: str,
    ) -> bool: ...
    def archive_run(self, run_id: str, archived_by: str) -> None: ...
    def unarchive_run(self, run_id: str) -> None: ...
    def delete_archived_runs(self, older_than_days: int | str, run_ids: list[str] | None = None, **kwargs: Any) -> dict[str, Any]: ...
    def preview_delete_archived_runs(self, run_ids: list[str]) -> dict[str, Any]: ...
    def list_cvs_for_run(self, run_id: str) -> list[dict[str, Any]]: ...
    def list_cv_versions(self, run_job_id: str) -> list[dict[str, Any]]: ...
    def reserve_cv_regeneration(self, run_job_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def update_cv_version(self, version_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def update_cv_evaluation(self, evaluation_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def insert_cv_evaluation_row(self, row: dict[str, Any]) -> dict[str, Any]: ...
    def insert_cv_review_event(self, row: dict[str, Any]) -> dict[str, Any]: ...
    def get_cv_download(self, version_id: str) -> dict[str, Any] | None: ...
    def get_cv_markdown(self, version_id: str) -> str | None: ...
    def get_debug_bundle_availability(self, run_id: str) -> dict[str, Any]: ...
    def list_run_structured_jobs(self, run_id: str) -> list[dict[str, Any]]: ...
    def list_filter_results_for_run(self, run_id: str) -> list[dict[str, Any]]: ...
    def get_pipeline_runs_schema_status(self) -> dict[str, Any]: ...
    def list_run_attempt_payloads(self, run_id: str) -> list[dict[str, Any]]: ...
    def append_event(self, event: RunEvent) -> dict[str, str]: ...
    def update_run_effective_settings(self, run_id: str, effective_settings_json: str) -> dict[str, str]: ...
    def update_run_synonym_proposals(
        self, run_id: str, synonym_proposals_json: str
    ) -> dict[str, str]: ...
    def update_run_cv_generation_debug(self, run_id: str, cv_generation_debug_json: str) -> dict[str, str]: ...
    def update_run_stage_transition_artifacts(self, run_id: str, stage_transition_artifacts_json: str) -> dict[str, str]: ...
    def materialize_episode_and_append_rating(self, episode: Any, alternatives: Any, event: Any) -> dict[str, str]: ...
    def list_decision_rating_events_for_run(self, run_id: str) -> list[Any]: ...
    def persist_inverse_training_result(self, row: dict[str, Any]) -> dict[str, Any]: ...
    def insert_ranking_policy_candidate(self, row: dict[str, Any]) -> dict[str, Any]: ...
    def persist_candidate_attempt(
        self,
        training: dict[str, Any],
        snapshot: dict[str, Any] | None = None,
        projection: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...
    def list_preference_optimization_runs(self, *, limit: int = 100) -> list[dict[str, Any]]: ...
    def get_preference_optimization_run(self, run_id: str) -> dict[str, Any]: ...
    def hide_preference_optimization_run(self, run_id: str) -> dict[str, Any]: ...
    def activate_preference_optimization_run(self, run_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def inactivate_preference_optimization_run(self, run_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def get_decision_evidence_head(self, domain_id: str) -> dict[str, Any]: ...
    def load_inverse_optimization_request(self, domain_id: str) -> InverseOptimizationRequest: ...
    def activate_ranking_policy_candidate(self, snapshot_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def reject_ranking_policy_candidate(self, snapshot_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def rollback_ranking_policy(self, domain_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def resolve_active_ranking_policy(self, domain_id: str, runtime_fingerprint: str) -> dict[str, Any] | None: ...
    def inspect_ranking_policy_lifecycle(
        self,
        domain_id: str,
        *,
        limit: int | None = None,
        runtime_contract_fingerprint: str | None = None,
    ) -> dict[str, Any]: ...
    def insert_cv_version_row(self, row: dict[str, Any]) -> list[Any]: ...


@dataclass
class ControlPlaneStore:
    backend_runtime: BackendRuntime | None = None
    get_api_provider_revision_fn: Any | None = None
    list_custom_api_providers_fn: Any | None = None
    get_custom_api_provider_fn: Any | None = None
    create_custom_api_provider_fn: Any | None = None
    update_custom_api_provider_fn: Any | None = None
    delete_custom_api_provider_fn: Any | None = None
    delete_custom_api_provider_bundle_fn: Any | None = None
    get_api_provider_connection_fn: Any | None = None
    save_api_provider_connection_fn: Any | None = None
    delete_api_provider_connection_fn: Any | None = None
    list_api_provider_models_fn: Any | None = None
    get_api_provider_model_fn: Any | None = None
    create_api_provider_model_fn: Any | None = None
    update_api_provider_model_fn: Any | None = None
    delete_api_provider_model_fn: Any | None = None
    integration_migration_applied_fn: Any | None = None
    record_integration_migration_fn: Any | None = None
    list_candidate_profiles_fn: Any | None = None
    get_candidate_profile_fn: Any | None = None
    query_candidate_profiles_fn: Any | None = None
    create_candidate_profile_attempt_fn: Any | None = None
    query_candidate_profile_creation_attempts_fn: Any | None = None
    create_candidate_profile_creation_attempt_fn: Any | None = None
    get_candidate_profile_creation_attempt_fn: Any | None = None
    get_candidate_profile_source_fn: Any | None = None
    get_candidate_profile_source_block_fn: Any | None = None
    get_candidate_profile_review_fn: Any | None = None
    patch_candidate_profile_review_fn: Any | None = None
    regenerate_candidate_profile_review_fn: Any | None = None
    undo_candidate_profile_regeneration_fn: Any | None = None
    approve_candidate_profile_review_fn: Any | None = None
    get_candidate_profile_confirmation_fn: Any | None = None
    confirm_candidate_profile_creation_attempt_fn: Any | None = None
    retry_candidate_profile_creation_attempt_fn: Any | None = None
    claim_candidate_profile_processing_fn: Any | None = None
    publish_candidate_profile_stage_result_fn: Any | None = None
    fail_candidate_profile_stage_fn: Any | None = None
    reconcile_candidate_profile_attempts_fn: Any | None = None
    get_candidate_profile_detail_fn: Any | None = None
    query_candidate_profile_runs_fn: Any | None = None
    transition_candidate_profile_lifecycle_fn: Any | None = None
    delete_candidate_profile_fn: Any | None = None
    update_candidate_profile_fn: Any | None = None
    get_synonym_policy_fn: Any | None = None
    save_synonym_policy_draft_fn: Any | None = None
    activate_synonym_policy_bundle_fn: Any | None = None
    activate_synonym_policy_bundle_set_fn: Any | None = None
    resolve_active_synonym_bundle_fn: Any | None = None
    repair_active_synonym_policy_mirrors_fn: Any | None = None
    ingest_synonym_suggestions_fn: Any | None = None
    query_synonym_suggestions_fn: Any | None = None
    get_synonym_suggestion_fn: Any | None = None
    apply_synonym_suggestion_action_fn: Any | None = None
    query_synonym_processing_runs_fn: Any | None = None
    query_tracked_companies_fn: Any | None = None
    create_tracked_company_fn: Any | None = None
    create_scan_fn: Any | None = None
    query_scans_fn: Any | None = None
    get_scan_detail_fn: Any | None = None
    request_scan_cancel_fn: Any | None = None
    commit_scan_output_fn: Any | None = None
    get_scan_output_fn: Any | None = None
    query_scan_jobs_fn: Any | None = None
    transition_scan_lifecycle_fn: Any | None = None
    preview_delete_archived_scans_fn: Any | None = None
    delete_archived_scans_fn: Any | None = None
    insert_run_fn: Any | None = None
    update_run_queue_job_id_fn: Any | None = None
    update_run_orchestration_binding_fn: Any | None = None
    get_run_fn: Any | None = None
    list_runs_fn: Any | None = None
    get_events_fn: Any | None = None
    get_process_events_fn: Any | None = None
    get_run_detail_fn: Any | None = None
    iter_run_jobs_for_export_fn: Any | None = None
    update_run_status_fn: Any | None = None
    update_run_checkpoint_fn: Any | None = None
    request_run_cancel_fn: Any | None = None
    archive_run_fn: Any | None = None
    unarchive_run_fn: Any | None = None
    delete_archived_runs_fn: Any | None = None
    preview_delete_archived_runs_fn: Any | None = None
    list_cvs_for_run_fn: Any | None = None
    list_cv_versions_fn: Any | None = None
    reserve_cv_regeneration_fn: Any | None = None
    update_cv_version_fn: Any | None = None
    update_cv_evaluation_fn: Any | None = None
    insert_cv_evaluation_row_fn: Any | None = None
    insert_cv_review_event_fn: Any | None = None
    get_cv_download_fn: Any | None = None
    get_cv_markdown_fn: Any | None = None
    get_debug_bundle_availability_fn: Any | None = None
    list_run_structured_jobs_fn: Any | None = None
    list_filter_results_for_run_fn: Any | None = None
    get_pipeline_runs_schema_status_fn: Any | None = None
    append_event_fn: Any | None = None
    update_run_effective_settings_fn: Any | None = None
    update_run_synonym_proposals_fn: Any | None = None
    update_run_cv_generation_debug_fn: Any | None = None
    update_run_stage_transition_artifacts_fn: Any | None = None
    materialize_episode_and_append_rating_fn: Any | None = None
    list_decision_rating_events_for_run_fn: Any | None = None
    persist_inverse_training_result_fn: Any | None = None
    insert_ranking_policy_candidate_fn: Any | None = None
    persist_candidate_attempt_fn: Any | None = None
    list_preference_optimization_runs_fn: Any | None = None
    get_preference_optimization_run_fn: Any | None = None
    hide_preference_optimization_run_fn: Any | None = None
    activate_preference_optimization_run_fn: Any | None = None
    inactivate_preference_optimization_run_fn: Any | None = None
    get_decision_evidence_head_fn: Any | None = None
    load_inverse_optimization_request_fn: Any | None = None
    activate_ranking_policy_candidate_fn: Any | None = None
    reject_ranking_policy_candidate_fn: Any | None = None
    rollback_ranking_policy_fn: Any | None = None
    resolve_active_ranking_policy_fn: Any | None = None
    inspect_ranking_policy_lifecycle_fn: Any | None = None
    insert_cv_version_row_fn: Any | None = None
    create_run_bundle_fn: Any | None = None
    query_runs_fn: Any | None = None
    list_run_stages_fn: Any | None = None
    query_run_jobs_fn: Any | None = None
    get_run_job_fn: Any | None = None
    set_bookmark_fn: Any | None = None
    clear_bookmark_fn: Any | None = None
    list_bookmarks_fn: Any | None = None
    query_bookmarks_fn: Any | None = None
    resolve_job_selection_fn: Any | None = None
    remove_bookmarks_fn: Any | None = None
    list_selected_jobs_fn: Any | None = None
    set_run_job_interest_fn: Any | None = None
    clear_run_job_interest_fn: Any | None = None
    reserve_idempotent_action_fn: Any | None = None
    complete_idempotent_action_fn: Any | None = None
    complete_idempotent_binary_action_fn: Any | None = None

    def __post_init__(self) -> None:
        if self.backend_runtime is not None:
            set_backend_runtime(self.backend_runtime)

    def _resolve_fn(self, override_fn: Any | None, default_fn: Any) -> Any:
        return override_fn or default_fn

    def _call(self, override_fn: Any | None, default_fn: Any, *args: Any, **kwargs: Any) -> Any:
        fn = self._resolve_fn(override_fn, default_fn)
        return fn(*args, **kwargs)

    def _call_list(self, override_fn: Any | None, default_fn: Any, *args: Any, **kwargs: Any) -> list[Any]:
        value = self._call(override_fn, default_fn, *args, **kwargs)
        if value is None:
            return []
        return list(value)

    def _call_dict(self, override_fn: Any | None, default_fn: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        value = self._call(override_fn, default_fn, *args, **kwargs)
        if value is None:
            return {}
        return dict(value)

    @staticmethod
    def _scan_backend_unavailable(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("managed Scan backend is unavailable")

    def query_tracked_companies(self, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(self.query_tracked_companies_fn, sqlite_store.query_tracked_companies, **kwargs)

    def create_tracked_company(self, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(self.create_tracked_company_fn, sqlite_store.create_tracked_company, **kwargs)

    def create_scan(self, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(self.create_scan_fn, sqlite_store.create_scan, **kwargs)

    def query_scans(self, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(self.query_scans_fn, sqlite_store.query_scans, **kwargs)

    def get_scan_detail(self, scan_id: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, self._call(self.get_scan_detail_fn, sqlite_store.get_scan_detail, scan_id))

    def request_scan_cancel(self, scan_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(self.request_scan_cancel_fn, sqlite_store.request_scan_cancel, scan_id, **kwargs)

    def commit_scan_output(self, scan_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(self.commit_scan_output_fn, sqlite_store.commit_scan_output, scan_id, **kwargs)

    def get_scan_output(self, scan_id: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, self._call(self.get_scan_output_fn, sqlite_store.get_scan_output, scan_id))

    def query_scan_jobs(self, scan_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(self.query_scan_jobs_fn, sqlite_store.query_scan_jobs, scan_id, **kwargs)

    def transition_scan_lifecycle(self, items: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(self.transition_scan_lifecycle_fn, sqlite_store.transition_scan_lifecycle, items, **kwargs)

    def preview_delete_archived_scans(self, scan_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(self.preview_delete_archived_scans_fn, sqlite_store.preview_delete_archived_scans, scan_ids, **kwargs)

    def delete_archived_scans(self, scan_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(self.delete_archived_scans_fn, sqlite_store.delete_archived_scans, scan_ids, **kwargs)

    def get_api_provider_revision(self, provider_id: str) -> int:
        return int(
            self._call(
                self.get_api_provider_revision_fn,
                sqlite_store.get_api_provider_revision,
                provider_id,
            )
        )

    def list_custom_api_providers(self) -> list[dict[str, Any]]:
        return self._call_list(
            self.list_custom_api_providers_fn,
            sqlite_store.list_custom_api_providers,
        )

    def get_custom_api_provider(self, provider_id: str) -> dict[str, Any] | None:
        return cast(
            dict[str, Any] | None,
            self._call(
                self.get_custom_api_provider_fn,
                sqlite_store.get_custom_api_provider,
                provider_id,
            ),
        )

    def create_custom_api_provider(self, provider_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.create_custom_api_provider_fn,
            sqlite_store.create_custom_api_provider,
            provider_id,
            **kwargs,
        )

    def update_custom_api_provider(self, provider_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.update_custom_api_provider_fn,
            sqlite_store.update_custom_api_provider,
            provider_id,
            **kwargs,
        )

    def delete_custom_api_provider(self, provider_id: str, **kwargs: Any) -> None:
        self._call(
            self.delete_custom_api_provider_fn,
            sqlite_store.delete_custom_api_provider,
            provider_id,
            **kwargs,
        )

    def delete_custom_api_provider_bundle(self, provider_id: str, **kwargs: Any) -> None:
        self._call(
            self.delete_custom_api_provider_bundle_fn,
            sqlite_store.delete_custom_api_provider_bundle,
            provider_id,
            **kwargs,
        )

    def get_api_provider_connection(self, provider_id: str) -> dict[str, Any] | None:
        return cast(
            dict[str, Any] | None,
            self._call(
                self.get_api_provider_connection_fn,
                sqlite_store.get_api_provider_connection,
                provider_id,
            ),
        )

    def save_api_provider_connection(self, provider_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.save_api_provider_connection_fn,
            sqlite_store.save_api_provider_connection,
            provider_id,
            **kwargs,
        )

    def delete_api_provider_connection(self, provider_id: str, **kwargs: Any) -> None:
        self._call(
            self.delete_api_provider_connection_fn,
            sqlite_store.delete_api_provider_connection,
            provider_id,
            **kwargs,
        )

    def list_api_provider_models(self, provider_id: str) -> list[dict[str, Any]]:
        return self._call_list(
            self.list_api_provider_models_fn,
            sqlite_store.list_api_provider_models,
            provider_id,
        )

    def get_api_provider_model(self, model_record_id: str) -> dict[str, Any] | None:
        return cast(
            dict[str, Any] | None,
            self._call(
                self.get_api_provider_model_fn,
                sqlite_store.get_api_provider_model,
                model_record_id,
            ),
        )

    def create_api_provider_model(self, model_record_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.create_api_provider_model_fn,
            sqlite_store.create_api_provider_model,
            model_record_id,
            **kwargs,
        )

    def update_api_provider_model(self, model_record_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.update_api_provider_model_fn,
            sqlite_store.update_api_provider_model,
            model_record_id,
            **kwargs,
        )

    def delete_api_provider_model(self, model_record_id: str, **kwargs: Any) -> None:
        self._call(
            self.delete_api_provider_model_fn,
            sqlite_store.delete_api_provider_model,
            model_record_id,
            **kwargs,
        )

    def integration_migration_applied(self, migration_key: str) -> bool:
        return bool(
            self._call(
                self.integration_migration_applied_fn,
                sqlite_store.integration_migration_applied,
                migration_key,
            )
        )

    def record_integration_migration(self, migration_key: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.record_integration_migration_fn,
            sqlite_store.record_integration_migration,
            migration_key,
            **kwargs,
        )

    def insert_run(self, run: PipelineRun) -> None:
        self._call(
            self.insert_run_fn,
            sqlite_store.insert_run,
            run,
        )

    def list_candidate_profiles(self) -> list[dict[str, Any]]:
        return self._call_list(
            self.list_candidate_profiles_fn,
            sqlite_store.list_candidate_profiles,
        )

    def get_candidate_profile(self, candidate_profile_id: str) -> dict[str, Any] | None:
        return cast(
            dict[str, Any] | None,
            self._call(
                self.get_candidate_profile_fn,
                sqlite_store.get_candidate_profile,
                candidate_profile_id,
            ),
        )

    def query_candidate_profiles(self, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.query_candidate_profiles_fn, sqlite_store.query_candidate_profiles, **kwargs
        )

    def create_candidate_profile_attempt(self, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.create_candidate_profile_attempt_fn,
            sqlite_store.create_candidate_profile_attempt,
            **kwargs,
        )

    @staticmethod
    def _required_candidate_profile_override(fn: Any | None) -> Any:
        if fn is None:
            raise RuntimeError("candidate_profile_backend_unavailable")
        return fn

    def query_candidate_profile_creation_attempts(self, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.query_candidate_profile_creation_attempts_fn,
            sqlite_store.query_candidate_profile_creation_attempts,
            **kwargs,
        )

    def create_candidate_profile_creation_attempt(self, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.create_candidate_profile_creation_attempt_fn,
            sqlite_store.create_candidate_profile_creation_attempt,
            **kwargs,
        )

    def get_candidate_profile_creation_attempt(self, attempt_id: str) -> dict[str, Any] | None:
        return cast(
            dict[str, Any] | None,
            self._call(self.get_candidate_profile_creation_attempt_fn, sqlite_store.get_candidate_profile_creation_attempt, attempt_id),
        )

    def get_candidate_profile_source(self, attempt_id: str) -> dict[str, Any] | None:
        return cast(
            dict[str, Any] | None,
            self._call(self.get_candidate_profile_source_fn, sqlite_store.get_candidate_profile_source, attempt_id),
        )

    def get_candidate_profile_source_block(self, attempt_id: str, source_block_id: str) -> dict[str, Any] | None:
        return cast(
            dict[str, Any] | None,
            self._call(self.get_candidate_profile_source_block_fn, sqlite_store.get_candidate_profile_source_block, attempt_id, source_block_id),
        )

    def get_candidate_profile_review(self, attempt_id: str, stage: str) -> dict[str, Any] | None:
        return cast(
            dict[str, Any] | None,
            self._call(self.get_candidate_profile_review_fn, sqlite_store.get_candidate_profile_review, attempt_id, stage),
        )

    def patch_candidate_profile_review(self, attempt_id: str, stage: str, **kwargs: Any) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._call(self.patch_candidate_profile_review_fn, sqlite_store.patch_candidate_profile_review, attempt_id, stage, **kwargs),
        )

    def regenerate_candidate_profile_review(self, attempt_id: str, stage: str, **kwargs: Any) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._call(self.regenerate_candidate_profile_review_fn, sqlite_store.regenerate_candidate_profile_review, attempt_id, stage, **kwargs),
        )

    def undo_candidate_profile_regeneration(self, attempt_id: str, stage: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.undo_candidate_profile_regeneration_fn,
            sqlite_store.undo_candidate_profile_regeneration,
            attempt_id,
            stage,
            **kwargs,
        )

    def approve_candidate_profile_review(self, attempt_id: str, stage: str, **kwargs: Any) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._call(self.approve_candidate_profile_review_fn, sqlite_store.approve_candidate_profile_review, attempt_id, stage, **kwargs),
        )

    def get_candidate_profile_confirmation(self, attempt_id: str) -> dict[str, Any] | None:
        return cast(
            dict[str, Any] | None,
            self._call(self.get_candidate_profile_confirmation_fn, sqlite_store.get_candidate_profile_confirmation, attempt_id),
        )

    def confirm_candidate_profile_creation_attempt(self, attempt_id: str, **kwargs: Any) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._call(self.confirm_candidate_profile_creation_attempt_fn, sqlite_store.confirm_candidate_profile_creation_attempt, attempt_id, **kwargs),
        )

    def retry_candidate_profile_creation_attempt(self, attempt_id: str, **kwargs: Any) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._call(self.retry_candidate_profile_creation_attempt_fn, sqlite_store.retry_candidate_profile_creation_attempt, attempt_id, **kwargs),
        )

    def claim_candidate_profile_processing(self, attempt_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.claim_candidate_profile_processing_fn,
            sqlite_store.claim_candidate_profile_processing,
            attempt_id,
            **kwargs,
        )

    def publish_candidate_profile_stage_result(self, attempt_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.publish_candidate_profile_stage_result_fn,
            sqlite_store.publish_candidate_profile_stage_result,
            attempt_id,
            **kwargs,
        )

    def fail_candidate_profile_stage(self, attempt_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.fail_candidate_profile_stage_fn,
            sqlite_store.fail_candidate_profile_stage,
            attempt_id,
            **kwargs,
        )

    def reconcile_candidate_profile_attempts(self, **kwargs: Any) -> dict[str, int]:
        return cast(
            dict[str, int],
            self._call(
                self.reconcile_candidate_profile_attempts_fn,
                sqlite_store.reconcile_candidate_profile_attempts,
                **kwargs,
            ),
        )

    def get_candidate_profile_detail(self, profile_id: str) -> dict[str, Any] | None:
        return cast(
            dict[str, Any] | None,
            self._call(
                self.get_candidate_profile_detail_fn,
                sqlite_store.get_candidate_profile_detail,
                profile_id,
            ),
        )

    def query_candidate_profile_runs(self, profile_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.query_candidate_profile_runs_fn,
            sqlite_store.query_candidate_profile_runs,
            profile_id,
            **kwargs,
        )

    def transition_candidate_profile_lifecycle(
        self, profile_id: str, **kwargs: Any
    ) -> dict[str, Any]:
        return self._call_dict(
            self.transition_candidate_profile_lifecycle_fn,
            sqlite_store.transition_candidate_profile_lifecycle,
            profile_id,
            **kwargs,
        )

    def delete_candidate_profile(self, profile_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.delete_candidate_profile_fn,
            sqlite_store.delete_candidate_profile,
            profile_id,
            **kwargs,
        )

    def update_candidate_profile(self, profile_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.update_candidate_profile_fn,
            sqlite_store.update_candidate_profile,
            profile_id,
            **kwargs,
        )

    def get_synonym_policy(self, synonym_type: str) -> dict[str, Any]:
        return self._call_dict(
            self.get_synonym_policy_fn, sqlite_store.get_synonym_policy, synonym_type
        )
    def save_synonym_policy_draft(self, synonym_type: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.save_synonym_policy_draft_fn,
            sqlite_store.save_synonym_policy_draft,
            synonym_type,
            **kwargs,
        )

    def activate_synonym_policy_bundle(self, synonym_type: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.activate_synonym_policy_bundle_fn,
            sqlite_store.activate_synonym_policy_bundle,
            synonym_type,
            **kwargs,
        )

    def activate_synonym_policy_bundle_set(
        self, policies: dict[str, dict[str, str]], **kwargs: Any
    ) -> dict[str, Any]:
        return self._call_dict(
            self.activate_synonym_policy_bundle_set_fn,
            sqlite_store.activate_synonym_policy_bundle_set,
            policies,
            **kwargs,
        )

    def resolve_active_synonym_bundle(self) -> dict[str, Any]:
        return self._call_dict(
            self.resolve_active_synonym_bundle_fn,
            sqlite_store.resolve_active_synonym_bundle,
        )

    def repair_active_synonym_policy_mirrors(self) -> dict[str, Any]:
        return self._call_dict(
            self.repair_active_synonym_policy_mirrors_fn,
            sqlite_store.repair_active_synonym_policy_mirrors,
        )

    def ingest_synonym_suggestions(self, suggestions: list[dict[str, Any]]) -> dict[str, Any]:
        return self._call_dict(
            self.ingest_synonym_suggestions_fn,
            sqlite_store.ingest_synonym_suggestions,
            suggestions,
        )

    def query_synonym_suggestions(self, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.query_synonym_suggestions_fn,
            sqlite_store.query_synonym_suggestions,
            **kwargs,
        )

    def get_synonym_suggestion(self, suggestion_id: str, **kwargs: Any) -> dict[str, Any] | None:
        return cast(
            dict[str, Any] | None,
            self._call(
                self.get_synonym_suggestion_fn,
                sqlite_store.get_synonym_suggestion,
                suggestion_id,
                **kwargs,
            ),
        )

    def apply_synonym_suggestion_action(
        self, suggestion_ids: list[str], **kwargs: Any
    ) -> dict[str, Any]:
        return self._call_dict(
            self.apply_synonym_suggestion_action_fn,
            sqlite_store.apply_synonym_suggestion_action,
            suggestion_ids,
            **kwargs,
        )

    def query_synonym_processing_runs(self, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.query_synonym_processing_runs_fn,
            sqlite_store.query_synonym_processing_runs,
            **kwargs,
        )

    def create_run_bundle(
        self,
        run: PipelineRun,
        *,
        input_resource: dict[str, Any],
        jobs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._call_dict(
            self.create_run_bundle_fn,
            sqlite_store.create_run_bundle,
            run,
            input_resource=input_resource,
            jobs=jobs,
        )

    def query_runs(self, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(self.query_runs_fn, sqlite_store.query_runs, **kwargs)

    def list_run_stages(self, run_id: str) -> list[dict[str, Any]]:
        return self._call_list(self.list_run_stages_fn, sqlite_store.list_run_stages, run_id)

    def query_run_jobs(self, run_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(self.query_run_jobs_fn, sqlite_store.query_run_jobs, run_id, **kwargs)

    def get_run_job(self, run_id: str, run_job_id: str) -> dict[str, Any] | None:
        return cast(
            dict[str, Any] | None,
            self._call(self.get_run_job_fn, sqlite_store.get_run_job, run_id, run_job_id),
        )

    def iter_run_jobs_for_export(self, run_id: str, **kwargs: Any) -> Iterator[dict[str, Any]]:
        return iter(
            self._call(
                self.iter_run_jobs_for_export_fn,
                sqlite_store.iter_run_jobs_for_export,
                run_id,
                **kwargs,
            )
        )

    def get_run_detail(self, run_id: str) -> dict[str, Any] | None:
        return cast(
            dict[str, Any] | None,
            self._call(self.get_run_detail_fn, sqlite_store.get_run_detail, run_id),
        )

    def set_bookmark(self, run_job_id: str) -> dict[str, Any]:
        return self._call_dict(self.set_bookmark_fn, sqlite_store.set_bookmark, run_job_id)

    def clear_bookmark(self, run_job_id: str) -> dict[str, Any]:
        return self._call_dict(self.clear_bookmark_fn, sqlite_store.clear_bookmark, run_job_id)

    def list_bookmarks(self) -> list[dict[str, Any]]:
        return self._call_list(self.list_bookmarks_fn, sqlite_store.list_bookmarks)

    def query_bookmarks(self, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(self.query_bookmarks_fn, sqlite_store.query_bookmarks, **kwargs)

    def resolve_job_selection(self, run_job_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.resolve_job_selection_fn,
            sqlite_store.resolve_job_selection,
            run_job_ids,
            **kwargs,
        )

    def remove_bookmarks(self, run_job_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.remove_bookmarks_fn,
            sqlite_store.remove_bookmarks,
            run_job_ids,
            **kwargs,
        )

    def list_selected_jobs(self, run_job_ids: list[str], **kwargs: Any) -> list[dict[str, Any]]:
        return self._call_list(
            self.list_selected_jobs_fn,
            sqlite_store.list_selected_jobs,
            run_job_ids,
            **kwargs,
        )

    def set_run_job_interest(self, run_job_id: str, rating: int, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.set_run_job_interest_fn,
            sqlite_store.set_run_job_interest,
            run_job_id,
            rating,
            **kwargs,
        )

    def clear_run_job_interest(self, run_job_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.clear_run_job_interest_fn,
            sqlite_store.clear_run_job_interest,
            run_job_id,
            **kwargs,
        )

    def reserve_idempotent_action(self, scope: str, key: str, fingerprint: str) -> dict[str, Any]:
        return self._call_dict(
            self.reserve_idempotent_action_fn,
            sqlite_store.reserve_idempotent_action,
            scope,
            key,
            fingerprint,
        )

    def complete_idempotent_action(self, action_id: str, response: dict[str, Any]) -> None:
        self._call(
            self.complete_idempotent_action_fn,
            sqlite_store.complete_idempotent_action,
            action_id,
            response,
        )

    def update_run_queue_job_id(
        self, run_id: str, queue_job_id: str, **kwargs: Any
    ) -> dict[str, str]:
        return self._call_dict(
            self.update_run_queue_job_id_fn,
            sqlite_store.update_run_queue_job_id,
            run_id,
            queue_job_id,
            **kwargs,
        )

    def update_run_orchestration_binding(
        self,
        run_id: str,
        *,
        queue_job_id: str | None,
        orchestration_backend: str | None,
        orchestration_run_id: str | None,
    ) -> dict[str, str]:
        return self._call_dict(
            self.update_run_orchestration_binding_fn,
            sqlite_store.update_run_orchestration_binding,
            run_id,
            queue_job_id=queue_job_id,
            orchestration_backend=orchestration_backend,
            orchestration_run_id=orchestration_run_id,
        )

    def get_run(self, run_id: str) -> PipelineRun | None:
        return self._call(
            self.get_run_fn,
            sqlite_store.get_run,
            run_id,
        )

    def list_runs(
        self,
        *,
        limit: int = 50,
        include_archived: bool = False,
        archived_only: bool = False,
    ) -> list[PipelineRun]:
        return self._call_list(
            self.list_runs_fn,
            sqlite_store.list_runs,
            limit=limit,
            include_archived=include_archived,
            archived_only=archived_only,
        )

    def get_events(self, run_id: str) -> list[RunEvent]:
        return self._call_list(
            self.get_events_fn,
            sqlite_store.get_events,
            run_id,
        )

    def get_process_events(
        self,
        process_type: str,
        process_id: str,
        *,
        limit: int = 200,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return self._call_dict(
            self.get_process_events_fn,
            sqlite_store.get_process_events,
            process_type,
            process_id,
            limit=limit,
            cursor=cursor,
        )

    def update_run_status(self, run_id: str, status: Any, **kwargs: Any) -> dict[str, str]:
        return self._call_dict(
            self.update_run_status_fn,
            sqlite_store.update_run_status,
            run_id,
            status,
            **kwargs,
        )

    def update_run_checkpoint(self, run_id: str, **kwargs: Any) -> dict[str, str]:
        return self._call_dict(
            self.update_run_checkpoint_fn,
            sqlite_store.update_run_checkpoint,
            run_id,
            **kwargs,
        )

    def request_run_cancel(
        self,
        run_id: str,
        requested_by: str,
        target_status: str,
    ) -> bool:
        return bool(
            self._call(
                self.request_run_cancel_fn,
                sqlite_store.request_run_cancel,
                run_id,
                requested_by,
                target_status,
                )
        )

    def archive_run(self, run_id: str, archived_by: str) -> None:
        self._call(
            self.archive_run_fn,
            sqlite_store.archive_run,
            run_id,
            archived_by,
        )

    def unarchive_run(self, run_id: str) -> None:
        self._call(
            self.unarchive_run_fn,
            sqlite_store.unarchive_run,
            run_id,
        )


    def delete_archived_runs(self, older_than_days: int | str, run_ids: list[str] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.delete_archived_runs_fn,
            sqlite_store.delete_archived_runs,
            older_than_days,
            run_ids=run_ids,
            **kwargs,
        )

    def complete_idempotent_binary_action(
        self,
        action_id: str,
        content: bytes,
        *,
        media_type: str,
        filename: str,
    ) -> None:
        self._call(
            self.complete_idempotent_binary_action_fn,
            sqlite_store.complete_idempotent_binary_action,
            action_id,
            content,
            media_type=media_type,
            filename=filename,
        )

    def preview_delete_archived_runs(self, run_ids: list[str]) -> dict[str, Any]:
        return self._call_dict(
            self.preview_delete_archived_runs_fn,
            sqlite_store.preview_delete_archived_runs,
            run_ids,
        )
    def list_cvs_for_run(self, run_id: str) -> list[dict[str, Any]]:
        return self._call_list(
            self.list_cvs_for_run_fn,
            sqlite_store.list_cvs_for_run,
            run_id,
        )

    def list_cv_versions(self, run_job_id: str) -> list[dict[str, Any]]:
        return self._call_list(
            self.list_cv_versions_fn,
            sqlite_store.list_cv_versions,
            run_job_id,
        )

    def reserve_cv_regeneration(self, run_job_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.reserve_cv_regeneration_fn,
            sqlite_store.reserve_cv_regeneration,
            run_job_id,
            **kwargs,
        )

    def update_cv_version(self, version_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.update_cv_version_fn,
            sqlite_store.update_cv_version,
            version_id,
            **kwargs,
        )

    def update_cv_evaluation(self, evaluation_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.update_cv_evaluation_fn,
            sqlite_store.update_cv_evaluation,
            evaluation_id,
            **kwargs,
        )

    def insert_cv_evaluation_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return self._call_dict(
            self.insert_cv_evaluation_row_fn,
            sqlite_store.insert_cv_evaluation_row,
            row,
        )

    def insert_cv_review_event(self, row: dict[str, Any]) -> dict[str, Any]:
        return self._call_dict(
            self.insert_cv_review_event_fn,
            sqlite_store.insert_cv_review_event,
            row,
        )

    def get_cv_download(self, version_id: str) -> dict[str, Any] | None:
        return cast(
            dict[str, Any] | None,
            self._call(self.get_cv_download_fn, sqlite_store.get_cv_download, version_id),
        )

    def get_cv_markdown(self, version_id: str) -> str | None:
        return cast(
            str | None,
            self._call(
            self.get_cv_markdown_fn,
            sqlite_store.get_cv_markdown,
            version_id,
            ),
        )

    def get_debug_bundle_availability(self, run_id: str) -> dict[str, Any]:
        return self._call_dict(
            self.get_debug_bundle_availability_fn,
            sqlite_store.get_debug_bundle_availability,
            run_id,
        )

    def list_run_structured_jobs(self, run_id: str) -> list[dict[str, Any]]:
        return self._call_list(
            self.list_run_structured_jobs_fn,
            sqlite_store.list_run_structured_jobs,
            run_id,
        )

    def list_filter_results_for_run(self, run_id: str) -> list[dict[str, Any]]:
        return self._call_list(
            self.list_filter_results_for_run_fn,
            sqlite_store.list_filter_results_for_run,
            run_id,
        )

    def get_pipeline_runs_schema_status(self) -> dict[str, Any]:
        return self._call_dict(
            self.get_pipeline_runs_schema_status_fn,
            sqlite_store.get_pipeline_runs_schema_status,
        )

    def list_run_attempt_payloads(self, run_id: str) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for event in self.get_events(run_id):
            payload = decode_run_attempt_payload_or_none(event.payload_json)
            if payload is None:
                continue
            payloads.append(payload)
        return payloads

    def append_event(self, event: RunEvent) -> dict[str, str]:
        return dict(
            self._call(
                self.append_event_fn,
                sqlite_store.append_event,
                event,
                )
        )

    def update_run_effective_settings(self, run_id: str, effective_settings_json: str) -> dict[str, str]:
        return self._call_dict(
            self.update_run_effective_settings_fn,
            sqlite_store.update_run_effective_settings,
            run_id,
            effective_settings_json,
        )

    def update_run_synonym_proposals(
        self, run_id: str, synonym_proposals_json: str
    ) -> dict[str, str]:
        return dict(
            self._call(
                self.update_run_synonym_proposals_fn,
                sqlite_store.update_run_synonym_proposals,
                run_id,
                synonym_proposals_json,
                )
        )

    def update_run_cv_generation_debug(self, run_id: str, cv_generation_debug_json: str) -> dict[str, str]:
        return self._call_dict(
            self.update_run_cv_generation_debug_fn,
            sqlite_store.update_run_cv_generation_debug,
            run_id,
            cv_generation_debug_json,
        )

    def update_run_stage_transition_artifacts(
        self,
        run_id: str,
        stage_transition_artifacts_json: str,
    ) -> dict[str, str]:
        return self._call_dict(
            self.update_run_stage_transition_artifacts_fn,
            sqlite_store.update_run_stage_transition_artifacts,
            run_id,
            stage_transition_artifacts_json,
        )

    def materialize_episode_and_append_rating(
        self,
        episode: Any,
        alternatives: Any,
        event: Any,
    ) -> dict[str, str]:
        return self._call_dict(
            self.materialize_episode_and_append_rating_fn,
            sqlite_store.materialize_episode_and_append_rating,
            episode,
            alternatives,
            event,
        )

    def list_decision_rating_events_for_run(self, run_id: str) -> list[Any]:
        return self._call_list(
            self.list_decision_rating_events_for_run_fn,
            sqlite_store.list_decision_rating_events_for_run,
            run_id,
        )

    def persist_inverse_training_result(self, row: dict[str, Any]) -> dict[str, Any]:
        return self._call_dict(
            self.persist_inverse_training_result_fn,
            sqlite_store.persist_inverse_training_result,
            row,
        )

    def insert_ranking_policy_candidate(self, row: dict[str, Any]) -> dict[str, Any]:
        return self._call_dict(
            self.insert_ranking_policy_candidate_fn,
            sqlite_store.insert_ranking_policy_candidate,
            row,
        )

    def persist_candidate_attempt(
        self,
        training: dict[str, Any],
        snapshot: dict[str, Any] | None = None,
        projection: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._call_dict(
            self.persist_candidate_attempt_fn,
            sqlite_store.persist_candidate_attempt,
            training,
            snapshot,
            projection,
        )

    def list_preference_optimization_runs(
        self, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        return self._call_list(
            self.list_preference_optimization_runs_fn,
            sqlite_store.list_preference_optimization_runs,
            limit=limit,
        )

    def get_preference_optimization_run(self, run_id: str) -> dict[str, Any]:
        return self._call_dict(
            self.get_preference_optimization_run_fn,
            sqlite_store.get_preference_optimization_run,
            run_id,
        )

    def hide_preference_optimization_run(self, run_id: str) -> dict[str, Any]:
        return self._call_dict(
            self.hide_preference_optimization_run_fn,
            sqlite_store.hide_preference_optimization_run,
            run_id,
        )

    def activate_preference_optimization_run(
        self, run_id: str, **kwargs: Any
    ) -> dict[str, Any]:
        return self._call_dict(
            self.activate_preference_optimization_run_fn,
            sqlite_store.activate_preference_optimization_run,
            run_id,
            **kwargs,
        )

    def inactivate_preference_optimization_run(
        self, run_id: str, **kwargs: Any
    ) -> dict[str, Any]:
        return self._call_dict(
            self.inactivate_preference_optimization_run_fn,
            sqlite_store.inactivate_preference_optimization_run,
            run_id,
            **kwargs,
        )

    def get_decision_evidence_head(self, domain_id: str) -> dict[str, Any]:
        return self._call_dict(
            self.get_decision_evidence_head_fn,
            sqlite_store.get_decision_evidence_head,
            domain_id,
        )

    def load_inverse_optimization_request(
        self, domain_id: str
    ) -> InverseOptimizationRequest:
        return cast(
            InverseOptimizationRequest,
            self._call(
                self.load_inverse_optimization_request_fn,
                sqlite_store.load_inverse_optimization_request,
                domain_id,
            ),
        )

    def activate_ranking_policy_candidate(self, snapshot_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.activate_ranking_policy_candidate_fn,
            sqlite_store.activate_ranking_policy_candidate,
            snapshot_id,
            **kwargs,
        )

    def reject_ranking_policy_candidate(self, snapshot_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.reject_ranking_policy_candidate_fn,
            sqlite_store.reject_ranking_policy_candidate,
            snapshot_id,
            **kwargs,
        )

    def rollback_ranking_policy(self, domain_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call_dict(
            self.rollback_ranking_policy_fn,
            sqlite_store.rollback_ranking_policy,
            domain_id,
            **kwargs,
        )

    def resolve_active_ranking_policy(
        self,
        domain_id: str,
        runtime_fingerprint: str,
    ) -> dict[str, Any] | None:
        return cast(
            dict[str, Any] | None,
            self._call(
                self.resolve_active_ranking_policy_fn,
                sqlite_store.resolve_active_ranking_policy,
                domain_id,
                runtime_fingerprint,
            ),
        )

    def inspect_ranking_policy_lifecycle(
        self,
        domain_id: str,
        *,
        limit: int | None = None,
        runtime_contract_fingerprint: str | None = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if limit is not None:
            kwargs["limit"] = limit
        if runtime_contract_fingerprint is not None:
            kwargs["runtime_contract_fingerprint"] = runtime_contract_fingerprint
        return self._call_dict(
            self.inspect_ranking_policy_lifecycle_fn,
            sqlite_store.inspect_ranking_policy_lifecycle,
            domain_id,
            **kwargs,
        )

    def insert_cv_version_row(self, row: dict[str, Any]) -> list[Any]:
        return self._call_list(
            self.insert_cv_version_row_fn,
            sqlite_store.insert_cv_version_row,
            row,
        )






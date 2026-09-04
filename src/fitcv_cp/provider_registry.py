from __future__ import annotations

import datetime
import sqlite3
import uuid
from types import MappingProxyType
from typing import Any, Callable

from fitcv.config import normalize_api_root
from fitcv_cp.local_credentials import (
    credential_account,
    delete_credential,
    get_credential,
    set_credential,
)
from fitcv_cp.settings_store import load_llm_configuration
from fitcv_cp.store import ControlPlaneStore, RunStore


PREDEFINED_PROVIDERS = MappingProxyType({
    "openai": {
        "display_name": "OpenAI",
        "compatibility": "openai",
        "base_url": "https://api.openai.com/v1",
        "default_api_type": "responses",
    },
    "anthropic": {
        "display_name": "Anthropic",
        "compatibility": "anthropic",
        "base_url": "https://api.anthropic.com",
        "default_api_type": "messages",
    },
    "deepseek": {
        "display_name": "DeepSeek",
        "compatibility": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "default_api_type": "chat_completions",
    },
    "groq": {
        "display_name": "Groq",
        "compatibility": "openai",
        "base_url": "https://api.groq.com/openai/v1",
        "default_api_type": "chat_completions",
    },
})


class ProviderRegistryError(RuntimeError):
    def __init__(self, code: str, message: str, *, http_status: int | None = None) -> None:
        self.code = code
        self.http_status = http_status
        super().__init__(message)


def _store(store: RunStore | None) -> RunStore:
    return store or ControlPlaneStore()


def _supported_api_types(compatibility: str) -> tuple[str, ...]:
    return ("messages",) if compatibility == "anthropic" else (
        "chat_completions",
        "responses",
    )


def _definition(provider_id: str, store: RunStore) -> dict[str, Any] | None:
    predefined = PREDEFINED_PROVIDERS.get(provider_id)
    if predefined is not None:
        return {
            "provider_id": provider_id,
            "kind": "predefined",
            "revision": 1,
            **predefined,
        }
    custom = store.get_custom_api_provider(provider_id)
    if custom is None:
        return None
    return {
        "provider_id": provider_id,
        "kind": "custom",
        "display_name": custom["display_name"],
        "compatibility": custom["compatibility"],
        "base_url": None,
        "default_api_type": "messages"
        if custom["compatibility"] == "anthropic"
        else "responses",
        "revision": custom["revision"],
    }


def get_provider(provider_id: str, *, store: RunStore | None = None) -> dict[str, Any]:
    registry_store = _store(store)
    definition = _definition(provider_id, registry_store)
    if definition is None:
        raise ProviderRegistryError("provider_not_found", "Provider was not found")
    connection = registry_store.get_api_provider_connection(provider_id)
    models = registry_store.list_api_provider_models(provider_id)
    try:
        credential_configured = bool(get_credential(provider_id))
    except Exception as exc:
        raise ProviderRegistryError(
            "credential_store_failed",
            "Credential store is unavailable",
        ) from exc
    compatibility = str(definition["compatibility"])
    base_url = (
        definition["base_url"]
        if definition["kind"] == "predefined"
        else connection["base_url"] if connection else None
    )
    return {
        "provider_id": provider_id,
        "kind": definition["kind"],
        "display_name": definition["display_name"],
        "compatibility": compatibility,
        "base_url": base_url,
        "base_url_editable": definition["kind"] == "custom",
        "supported_api_types": list(_supported_api_types(compatibility)),
        "api_type_fixed": compatibility == "anthropic",
        "api_type": connection["api_type"] if connection else definition["default_api_type"],
        "connection_status": connection["verification_status"] if connection else "not_configured",
        "credential_configured": credential_configured,
        "connection_revision": connection["connection_revision"] if connection else None,
        "model_count": len(models),
        "eligible_model_count": sum(
            1
            for model in models
            if connection
            and connection["verification_status"] == "verified"
            and credential_configured
            and model["validation_status"] == "validated"
            and model["validated_connection_revision"] == connection["connection_revision"]
        ),
        "revision": registry_store.get_api_provider_revision(provider_id),
        "models": models,
        "capabilities": {
            "update": definition["kind"] == "custom",
            "delete": definition["kind"] == "custom",
            "test_connection": True,
            "remove_connection": connection is not None,
            "add_model": connection is not None,
        },
    }


def list_providers(*, store: RunStore | None = None) -> list[dict[str, Any]]:
    registry_store = _store(store)
    predefined = [get_provider(provider_id, store=registry_store) for provider_id in PREDEFINED_PROVIDERS]
    custom = [
        get_provider(str(row["provider_id"]), store=registry_store)
        for row in registry_store.list_custom_api_providers()
    ]
    return predefined + custom


def list_eligible_models(*, store: RunStore | None = None) -> list[dict[str, Any]]:
    return [
        {
            "model_record_id": model["model_record_id"],
            "provider_id": provider["provider_id"],
            "provider_display_name": provider["display_name"],
            "model_id": model["model_id"],
            "api_type": provider["api_type"],
        }
        for provider in list_providers(store=store)
        for model in provider["models"]
        if provider["connection_status"] == "verified"
        and provider["credential_configured"]
        and model["validation_status"] == "validated"
        and model["validated_connection_revision"] == provider["connection_revision"]
    ]


def create_custom_provider(
    *,
    display_name: str,
    compatibility: str,
    store: RunStore | None = None,
) -> dict[str, Any]:
    name = str(display_name or "").strip()
    if not 1 <= len(name) <= 120:
        raise ProviderRegistryError("provider_invalid", "Display Name must be 1 to 120 characters")
    if compatibility not in {"openai", "anthropic"}:
        raise ProviderRegistryError("provider_invalid", "Compatibility must be openai or anthropic")
    provider_id = f"custom-{uuid.uuid4()}"
    registry_store = _store(store)
    try:
        registry_store.create_custom_api_provider(
            provider_id,
            display_name=name,
            compatibility=compatibility,
        )
    except sqlite3.IntegrityError as exc:
        raise ProviderRegistryError(
            "provider_name_conflict",
            "Display Name is already in use",
        ) from exc
    return get_provider(provider_id, store=registry_store)


def update_custom_provider(
    provider_id: str,
    *,
    display_name: str | None,
    expected_revision: int,
    store: RunStore | None = None,
) -> dict[str, Any]:
    if provider_id in PREDEFINED_PROVIDERS:
        raise ProviderRegistryError("provider_predefined", "Predefined providers cannot be changed")
    registry_store = _store(store)
    current = registry_store.get_custom_api_provider(provider_id)
    if current is None:
        raise ProviderRegistryError("provider_not_found", "Provider was not found")
    name = str(display_name if display_name is not None else current["display_name"]).strip()
    if not 1 <= len(name) <= 120:
        raise ProviderRegistryError("provider_invalid", "Display Name must be 1 to 120 characters")
    try:
        registry_store.update_custom_api_provider(
            provider_id,
            display_name=name,
            compatibility=current["compatibility"],
            expected_revision=expected_revision,
        )
    except sqlite3.IntegrityError as exc:
        raise ProviderRegistryError(
            "provider_name_conflict",
            "Display Name is already in use",
        ) from exc
    return get_provider(provider_id, store=registry_store)


def _connection_draft(
    provider: dict[str, Any],
    *,
    base_url: str | None,
    api_type: str,
) -> tuple[str, str]:
    compatibility = str(provider["compatibility"])
    supported = _supported_api_types(compatibility)
    if api_type not in supported:
        raise ProviderRegistryError("provider_api_type_invalid", "API Type is not supported")
    if provider["kind"] == "predefined":
        resolved_base_url = str(provider["base_url"])
    else:
        try:
            resolved_base_url = normalize_api_root(str(base_url or ""))
        except ValueError as exc:
            raise ProviderRegistryError("provider_base_url_invalid", "Base URL is invalid") from exc
    return resolved_base_url, api_type


def _models_url(base_url: str, compatibility: str) -> str:
    root = normalize_api_root(base_url)
    if compatibility == "anthropic" and not root.rstrip("/").endswith("/v1"):
        return f"{root}/v1/models"
    return f"{root}/models"


def validate_connection_draft(
    *,
    compatibility: str,
    base_url: str,
    api_type: str,
    api_key: str,
    timeout_seconds: float = 30,
) -> dict[str, Any]:
    import httpx

    headers = (
        {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
        if compatibility == "anthropic"
        else {"Authorization": f"Bearer {api_key}"}
    )
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get(_models_url(base_url, compatibility), headers=headers)
            response.raise_for_status()
        return {"ok": True, "failure_code": None, "http_status": response.status_code}
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        code = "provider_auth_failed" if status in {401, 403} else "provider_connection_failed"
        return {"ok": False, "failure_code": code, "http_status": status}
    except httpx.HTTPError:
        return {"ok": False, "failure_code": "provider_unavailable", "http_status": None}


def discover_provider_models(
    *,
    compatibility: str,
    base_url: str,
    api_key: str,
    timeout_seconds: float = 30,
) -> list[str]:
    import httpx

    headers = (
        {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
        if compatibility == "anthropic"
        else {"Authorization": f"Bearer {api_key}"} if api_key else {}
    )
    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.get(_models_url(base_url, compatibility), headers=headers)
        response.raise_for_status()
    payload = response.json()
    rows = payload.get("data") if isinstance(payload, dict) else None
    return sorted(
        str(row.get("id") or "").strip()
        for row in rows or []
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    )


def test_connection(
    provider_id: str,
    *,
    base_url: str | None,
    api_type: str,
    api_key: str | None,
    store: RunStore | None = None,
    validator: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    registry_store = _store(store)
    provider = get_provider(provider_id, store=registry_store)
    resolved_base_url, resolved_api_type = _connection_draft(
        provider,
        base_url=base_url,
        api_type=api_type,
    )
    submitted_key = str(api_key or "").strip()
    try:
        credential = submitted_key or get_credential(provider_id)
    except Exception as exc:
        raise ProviderRegistryError(
            "credential_store_failed",
            "Credential store is unavailable",
        ) from exc
    if not credential:
        raise ProviderRegistryError("provider_credential_required", "API key is required")
    return (validator or validate_connection_draft)(
        compatibility=provider["compatibility"],
        base_url=resolved_base_url,
        api_type=resolved_api_type,
        api_key=credential,
    )


def save_connection(
    provider_id: str,
    *,
    base_url: str | None,
    api_type: str,
    api_key: str | None,
    expected_revision: int,
    store: RunStore | None = None,
    validator: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    registry_store = _store(store)
    provider = get_provider(provider_id, store=registry_store)
    resolved_base_url, resolved_api_type = _connection_draft(
        provider,
        base_url=base_url,
        api_type=api_type,
    )
    submitted_key = str(api_key or "").strip()
    try:
        existing_key = get_credential(provider_id)
    except Exception as exc:
        raise ProviderRegistryError(
            "credential_store_failed",
            "Credential store is unavailable",
        ) from exc
    result = test_connection(
        provider_id,
        base_url=base_url,
        api_type=api_type,
        api_key=api_key,
        store=registry_store,
        validator=validator,
    )
    if not result.get("ok"):
        raise ProviderRegistryError(
            str(result.get("failure_code") or "provider_connection_failed"),
            "Provider connection test failed",
            http_status=result.get("http_status"),
        )
    if submitted_key:
        try:
            set_credential(provider_id, submitted_key)
        except Exception as exc:
            raise ProviderRegistryError(
                "credential_store_failed",
                "Credential store is unavailable",
            ) from exc
    try:
        registry_store.save_api_provider_connection(
            provider_id,
            base_url=resolved_base_url if provider["kind"] == "custom" else None,
            api_type=resolved_api_type,
            verification_status="verified",
            verified_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            credential_account=credential_account(provider_id),
            expected_revision=expected_revision,
        )
    except Exception:
        if submitted_key:
            if existing_key:
                set_credential(provider_id, existing_key)
            else:
                delete_credential(provider_id)
        raise
    return get_provider(provider_id, store=registry_store)


def _active_model_references() -> set[str]:
    configuration = load_llm_configuration()
    references = {configuration.get("default_model_ref")}
    references.update(
        task.get("model_ref")
        for task in configuration.get("tasks", {}).values()
        if isinstance(task, dict)
    )
    return {str(reference) for reference in references if reference}


def validate_model(
    *,
    compatibility: str,
    base_url: str,
    api_type: str,
    api_key: str,
    model_id: str,
    timeout_seconds: float = 30,
) -> dict[str, Any]:
    import httpx

    root = normalize_api_root(base_url)
    if compatibility == "anthropic":
        url = f"{root.rstrip('/')}/v1/messages" if not root.rstrip("/").endswith("/v1") else f"{root}/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {"model": model_id, "max_tokens": 1, "messages": [{"role": "user", "content": "OK"}]}
    else:
        endpoint = "responses" if api_type == "responses" else "chat/completions"
        url = f"{root}/{endpoint}"
        headers = {"Authorization": f"Bearer {api_key}", "content-type": "application/json"}
        payload = (
            {"model": model_id, "input": "Reply with OK.", "max_output_tokens": 1}
            if api_type == "responses"
            else {"model": model_id, "messages": [{"role": "user", "content": "Reply with OK."}], "max_tokens": 1}
        )
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        return {"ok": True, "failure_code": None, "http_status": response.status_code}
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        code = "provider_auth_failed" if status in {401, 403} else "model_test_failed"
        return {"ok": False, "failure_code": code, "http_status": status}
    except httpx.HTTPError:
        return {"ok": False, "failure_code": "provider_unavailable", "http_status": None}


def _verified_connection(provider_id: str, store: RunStore) -> tuple[dict[str, Any], str]:
    provider = get_provider(provider_id, store=store)
    connection = store.get_api_provider_connection(provider_id)
    try:
        credential = get_credential(provider_id)
    except Exception as exc:
        raise ProviderRegistryError(
            "credential_store_failed",
            "Credential store is unavailable",
        ) from exc
    if connection is None or connection["verification_status"] != "verified" or not credential:
        raise ProviderRegistryError("provider_connection_required", "Verified connection is required")
    return provider, credential


def test_model(
    provider_id: str,
    *,
    model_id: str,
    store: RunStore | None = None,
    validator: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    registry_store = _store(store)
    provider, credential = _verified_connection(provider_id, registry_store)
    normalized_model_id = str(model_id or "").strip()
    if not 1 <= len(normalized_model_id) <= 255:
        raise ProviderRegistryError("model_id_invalid", "Model ID must be 1 to 255 characters")
    connection = registry_store.get_api_provider_connection(provider_id)
    if connection is None:
        raise ProviderRegistryError("provider_connection_required", "Verified connection is required")
    return (validator or validate_model)(
        compatibility=provider["compatibility"],
        base_url=connection["base_url"] or provider["base_url"],
        api_type=connection["api_type"],
        api_key=credential,
        model_id=normalized_model_id,
    )


def add_model(
    provider_id: str,
    *,
    model_id: str,
    expected_revision: int,
    store: RunStore | None = None,
    validator: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    registry_store = _store(store)
    normalized_model_id = str(model_id or "").strip()
    connection = registry_store.get_api_provider_connection(provider_id)
    if connection is None:
        raise ProviderRegistryError("provider_connection_required", "Verified connection is required")
    result = test_model(
        provider_id,
        model_id=normalized_model_id,
        store=registry_store,
        validator=validator,
    )
    if not result.get("ok"):
        raise ProviderRegistryError(
            str(result.get("failure_code") or "model_test_failed"),
            "Model test failed",
            http_status=result.get("http_status"),
        )
    try:
        return registry_store.create_api_provider_model(
            str(uuid.uuid4()),
            provider_id=provider_id,
            model_id=normalized_model_id,
            validated_connection_revision=connection["connection_revision"],
            last_tested_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            expected_revision=expected_revision,
        )
    except sqlite3.IntegrityError as exc:
        raise ProviderRegistryError(
            "model_already_exists",
            "Model identifier already exists for this provider",
        ) from exc


def retest_model(
    provider_id: str,
    model_record_id: str,
    *,
    expected_revision: int,
    store: RunStore | None = None,
    validator: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    registry_store = _store(store)
    provider, credential = _verified_connection(provider_id, registry_store)
    model = registry_store.get_api_provider_model(model_record_id)
    connection = registry_store.get_api_provider_connection(provider_id)
    if model is None or model["provider_id"] != provider_id:
        raise ProviderRegistryError("model_not_found", "Model was not found")
    if connection is None:
        raise ProviderRegistryError("provider_connection_required", "Verified connection is required")
    result = (validator or validate_model)(
        compatibility=provider["compatibility"],
        base_url=provider["base_url"],
        api_type=connection["api_type"],
        api_key=credential,
        model_id=model["model_id"],
    )
    return registry_store.update_api_provider_model(
        model_record_id,
        validation_status="validated" if result.get("ok") else "needs_retest",
        validated_connection_revision=connection["connection_revision"] if result.get("ok") else None,
        last_tested_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        last_test_error_code=None if result.get("ok") else str(result.get("failure_code") or "model_test_failed"),
        expected_revision=expected_revision,
    )


def remove_model(
    provider_id: str,
    model_record_id: str,
    *,
    expected_revision: int,
    store: RunStore | None = None,
) -> None:
    registry_store = _store(store)
    model = registry_store.get_api_provider_model(model_record_id)
    if model is None or model["provider_id"] != provider_id:
        raise ProviderRegistryError("model_not_found", "Model was not found")
    if model_record_id in _active_model_references():
        raise ProviderRegistryError("model_in_use", "Model is referenced by LLM Configuration")
    registry_store.delete_api_provider_model(model_record_id, expected_revision=expected_revision)


def remove_connection(
    provider_id: str,
    *,
    expected_revision: int,
    store: RunStore | None = None,
) -> dict[str, Any]:
    registry_store = _store(store)
    referenced = _active_model_references()
    if any(model["model_record_id"] in referenced for model in registry_store.list_api_provider_models(provider_id)):
        raise ProviderRegistryError("model_in_use", "Provider model is referenced by LLM Configuration")
    existing_key = get_credential(provider_id)
    delete_credential(provider_id)
    try:
        registry_store.delete_api_provider_connection(
            provider_id,
            expected_revision=expected_revision,
        )
    except Exception:
        if existing_key:
            set_credential(provider_id, existing_key)
        raise
    return get_provider(provider_id, store=registry_store)


def delete_custom_provider(
    provider_id: str,
    *,
    expected_revision: int,
    store: RunStore | None = None,
) -> None:
    if provider_id in PREDEFINED_PROVIDERS:
        raise ProviderRegistryError("provider_predefined", "Predefined providers cannot be deleted")
    registry_store = _store(store)
    referenced = _active_model_references()
    if any(
        model["model_record_id"] in referenced
        for model in registry_store.list_api_provider_models(provider_id)
    ):
        raise ProviderRegistryError("model_in_use", "Provider model is referenced by LLM Configuration")
    existing_key = get_credential(provider_id)
    delete_credential(provider_id)
    try:
        registry_store.delete_custom_api_provider_bundle(
            provider_id,
            expected_revision=expected_revision,
        )
    except Exception:
        if existing_key:
            set_credential(provider_id, existing_key)
        raise

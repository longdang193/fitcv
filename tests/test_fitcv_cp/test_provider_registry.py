from pathlib import Path

import pytest

from fitcv_cp import provider_registry
from fitcv_cp.backend_runtime import set_backend_runtime
from fitcv_cp.settings_store import load_llm_configuration, patch_llm_configuration
from fitcv_cp.store import ControlPlaneStore
from fitcv_cp import sqlite_store


@pytest.fixture(autouse=True)
def _local_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    set_backend_runtime(None)
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "fitcv.sqlite3"))
    yield
    set_backend_runtime(None)


def _credential_store(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    credentials: dict[str, str] = {}
    monkeypatch.setattr(
        provider_registry,
        "set_credential",
        lambda provider_id, api_key: credentials.__setitem__(provider_id, api_key),
    )
    monkeypatch.setattr(
        provider_registry,
        "get_credential",
        lambda provider_id: credentials.get(provider_id, ""),
    )
    monkeypatch.setattr(
        provider_registry,
        "delete_credential",
        lambda provider_id: credentials.pop(provider_id, None),
    )
    return credentials


def test_registry_merges_predefined_and_custom_providers() -> None:
    created = provider_registry.create_custom_provider(
        display_name="Company Gateway",
        compatibility="anthropic",
    )

    providers = provider_registry.list_providers()

    assert [provider["provider_id"] for provider in providers[:4]] == [
        "openai",
        "anthropic",
        "deepseek",
        "groq",
    ]
    assert created["provider_id"].startswith("custom-")
    assert provider_registry.get_provider("openai")["base_url_editable"] is False
    assert provider_registry.get_provider(created["provider_id"])["base_url_editable"] is True


def test_connection_and_model_lifecycle_use_one_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credentials = _credential_store(monkeypatch)
    monkeypatch.setattr(
        provider_registry,
        "validate_connection_draft",
        lambda **_kwargs: {"ok": True, "failure_code": None, "http_status": 200},
    )
    model_validation_calls: list[dict[str, object]] = []

    def validate_model(**kwargs: object) -> dict[str, object]:
        model_validation_calls.append(kwargs)
        return {"ok": True, "failure_code": None, "http_status": 200}

    monkeypatch.setattr(provider_registry, "validate_model", validate_model)
    provider = provider_registry.create_custom_provider(
        display_name="OpenAI Gateway",
        compatibility="openai",
    )

    connected = provider_registry.save_connection(
        provider["provider_id"],
        base_url="https://gateway.example/v1",
        api_type="responses",
        api_key="credential-secret-canary",
        expected_revision=provider["revision"],
    )
    model = provider_registry.add_model(
        provider["provider_id"],
        model_id="model-alpha",
        expected_revision=connected["revision"],
    )

    assert connected["connection_status"] == "verified"
    assert connected["credential_configured"] is True
    assert credentials[provider["provider_id"]] == "credential-secret-canary"
    assert model["validation_status"] == "validated"
    assert model_validation_calls[0]["base_url"] == "https://gateway.example/v1"
    assert model_validation_calls[0]["api_type"] == "responses"

    provider_registry.save_connection(
        provider["provider_id"],
        base_url="https://gateway.example/v1",
        api_type="chat_completions",
        api_key=None,
        expected_revision=model["provider_revision"],
    )

    assert provider_registry.get_provider(provider["provider_id"])["models"][0][
        "validation_status"
    ] == "needs_retest"


def test_failed_connection_validation_does_not_persist_or_store_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credentials = _credential_store(monkeypatch)
    monkeypatch.setattr(
        provider_registry,
        "validate_connection_draft",
        lambda **_kwargs: {
            "ok": False,
            "failure_code": "provider_auth_failed",
            "http_status": 401,
        },
    )

    with pytest.raises(provider_registry.ProviderRegistryError) as exc_info:
        provider_registry.save_connection(
            "openai",
            base_url=None,
            api_type="responses",
            api_key="credential-secret-canary",
            expected_revision=provider_registry.get_provider("openai")["revision"],
        )

    assert exc_info.value.code == "provider_auth_failed"
    assert credentials == {}
    assert provider_registry.get_provider("openai")["connection_status"] == "not_configured"


def test_model_removal_uses_provider_revision_and_rejects_stale_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _credential_store(monkeypatch)
    monkeypatch.setattr(
        provider_registry,
        "validate_connection_draft",
        lambda **_kwargs: {"ok": True, "failure_code": None, "http_status": 200},
    )
    monkeypatch.setattr(
        provider_registry,
        "validate_model",
        lambda **_kwargs: {"ok": True, "failure_code": None, "http_status": 200},
    )
    provider = provider_registry.get_provider("openai")
    connected = provider_registry.save_connection(
        "openai", base_url=None, api_type="responses", api_key="secret",
        expected_revision=provider["revision"],
    )
    model = provider_registry.add_model(
        "openai", model_id="gpt-remove", expected_revision=connected["revision"]
    )

    with pytest.raises(sqlite_store.ProviderPersistenceRevisionConflict):
        provider_registry.remove_model(
            "openai", model["model_record_id"], expected_revision=model["provider_revision"] - 1
        )
    assert provider_registry.get_provider("openai")["models"]

    provider_registry.remove_model(
        "openai", model["model_record_id"], expected_revision=model["provider_revision"]
    )
    assert provider_registry.get_provider("openai")["models"] == []


def test_model_in_use_cannot_be_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    _credential_store(monkeypatch)
    monkeypatch.setattr(
        provider_registry,
        "validate_connection_draft",
        lambda **_kwargs: {"ok": True, "failure_code": None, "http_status": 200},
    )
    monkeypatch.setattr(
        provider_registry,
        "validate_model",
        lambda **_kwargs: {"ok": True, "failure_code": None, "http_status": 200},
    )
    connection = provider_registry.save_connection(
        "openai",
        base_url=None,
        api_type="responses",
        api_key="secret",
        expected_revision=provider_registry.get_provider("openai")["revision"],
    )
    model = provider_registry.add_model(
        "openai", model_id="gpt-test", expected_revision=connection["revision"]
    )
    llm = load_llm_configuration()
    patch_llm_configuration(
        {"default_model_ref": model["model_record_id"]},
        expected_revision=llm["revision"],
    )

    with pytest.raises(provider_registry.ProviderRegistryError) as exc_info:
        provider_registry.remove_model(
            "openai",
            model["model_record_id"],
            expected_revision=model["provider_revision"],
        )

    assert connection["connection_revision"] == 1
    assert exc_info.value.code == "model_in_use"


def test_connection_write_failure_restores_previous_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credentials = _credential_store(monkeypatch)
    credentials["openai"] = "old-secret"
    monkeypatch.setattr(
        provider_registry,
        "validate_connection_draft",
        lambda **_kwargs: {"ok": True, "failure_code": None, "http_status": 200},
    )
    store = ControlPlaneStore(
        save_api_provider_connection_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("write failed")
        )
    )

    with pytest.raises(RuntimeError, match="write failed"):
        provider_registry.save_connection(
            "openai",
            base_url=None,
            api_type="responses",
            api_key="new-secret",
            expected_revision=provider_registry.get_provider("openai", store=store)["revision"],
            store=store,
        )

    assert credentials["openai"] == "old-secret"


def test_custom_provider_delete_removes_metadata_models_and_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credentials = _credential_store(monkeypatch)
    monkeypatch.setattr(
        provider_registry,
        "validate_connection_draft",
        lambda **_kwargs: {"ok": True, "failure_code": None, "http_status": 200},
    )
    monkeypatch.setattr(
        provider_registry,
        "validate_model",
        lambda **_kwargs: {"ok": True, "failure_code": None, "http_status": 200},
    )
    provider = provider_registry.create_custom_provider(
        display_name="Disposable Gateway",
        compatibility="openai",
    )
    connected = provider_registry.save_connection(
        provider["provider_id"],
        base_url="https://gateway.example/v1",
        api_type="responses",
        api_key="secret",
        expected_revision=provider["revision"],
    )
    model = provider_registry.add_model(
        provider["provider_id"],
        model_id="model-alpha",
        expected_revision=connected["revision"],
    )

    provider_registry.delete_custom_provider(
        provider["provider_id"],
        expected_revision=model["provider_revision"],
    )

    assert connected["connection_revision"] == 1
    assert provider["provider_id"] not in credentials
    with pytest.raises(provider_registry.ProviderRegistryError) as exc_info:
        provider_registry.get_provider(provider["provider_id"])
    assert exc_info.value.code == "provider_not_found"

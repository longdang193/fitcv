"""
@meta
type: test
scope: unit
domain: fitcv_local_credentials
covers:
  - OS credential storage boundary
excludes:
  - live Windows Credential Manager
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import sys
import types

from fitcv_cp.local_credentials import (
    SERVICE_NAME,
    credential_is_configured,
    delete_credential,
    get_credential,
    set_credential,
)


def test_credential_round_trip_uses_stable_non_secret_names(monkeypatch) -> None:
    stored: dict[tuple[str, str], str] = {}
    keyring = types.ModuleType("keyring")
    keyring.set_password = lambda service, account, secret: stored.__setitem__((service, account), secret)
    keyring.get_password = lambda service, account: stored.get((service, account))
    keyring.delete_password = lambda service, account: stored.pop((service, account), None)
    errors = types.ModuleType("keyring.errors")
    errors.PasswordDeleteError = RuntimeError
    monkeypatch.setitem(sys.modules, "keyring", keyring)
    monkeypatch.setitem(sys.modules, "keyring.errors", errors)

    set_credential("openai", "secret-canary")

    assert stored[(SERVICE_NAME, "provider:openai")] == "secret-canary"
    assert credential_is_configured("openai") is True
    assert get_credential("openai") == "secret-canary"
    delete_credential("openai")
    assert credential_is_configured("openai") is False

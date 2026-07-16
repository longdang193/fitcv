"""@meta
name: local_credentials
type: utility
domain: fitcv_local
ownership: infrastructure
responsibility:
  - Store FitCV Local provider secrets in OS credential storage.
inputs:
  - Provider identifier and API key
outputs:
  - Credential configured state or internal runtime secret
lifecycle:
  - status: active
"""

from __future__ import annotations

import re


SERVICE_NAME = "FitCV.Local"
_PROVIDER_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _account(provider_id: str) -> str:
    normalized = str(provider_id or "").strip().lower()
    if not _PROVIDER_ID.fullmatch(normalized):
        raise ValueError("provider_id must contain only lowercase letters, numbers, _ or -")
    return f"provider:{normalized}"


def set_credential(provider_id: str, api_key: str) -> None:
    secret = str(api_key or "").strip()
    if not secret:
        raise ValueError("api_key must be non-empty")
    import keyring

    keyring.set_password(SERVICE_NAME, _account(provider_id), secret)


def delete_credential(provider_id: str) -> None:
    import keyring
    from keyring.errors import PasswordDeleteError

    try:
        keyring.delete_password(SERVICE_NAME, _account(provider_id))
    except PasswordDeleteError:
        return


def get_credential(provider_id: str) -> str:
    import keyring

    return str(keyring.get_password(SERVICE_NAME, _account(provider_id)) or "").strip()


def credential_is_configured(provider_id: str) -> bool:
    return bool(get_credential(provider_id))

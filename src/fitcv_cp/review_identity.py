"""@meta
name: review_identity
type: module
domain: admin_ui
ownership: infrastructure
responsibility:
  - Provide deterministic review item identity for review-required CV rows.
inputs:
  - run_id and cv debug record payload
outputs:
  - stable `review_item_id` value on record dict
lifecycle:
  - status: active
"""

from __future__ import annotations

import hashlib
from typing import Any


def ensure_review_item_id(*, run_id: str, record: dict[str, Any], fallback_index: int) -> str:
    """Ensure review-required record carries deterministic review_item_id.

    Existing non-empty ids are preserved to keep downstream references stable.
    """
    existing = str(record.get("review_item_id") or "").strip()
    if existing:
        return existing
    seed = "|".join(
        [
            str(run_id or "").strip(),
            str(record.get("job_url") or "").strip(),
            str(record.get("job_title") or "").strip(),
            str(record.get("rank") or "").strip(),
            str(fallback_index),
        ]
    )
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    review_item_id = f"ri_{digest}"
    record["review_item_id"] = review_item_id
    return review_item_id

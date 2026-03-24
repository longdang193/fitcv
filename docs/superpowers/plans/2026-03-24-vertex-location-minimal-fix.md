# Vertex Location Minimal Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate Vertex AI location from BigQuery location so pipeline config can keep `location: "US"` while Vertex callers use a valid regional endpoint.

**Architecture:** Add a small config helper that resolves `vertex_location` with a safe `us-central1` default. Update Vertex-powered modules to use that helper and set `vertex_location` in `config/env.yaml`.

**Tech Stack:** Python, pytest, YAML config, Vertex AI / Google GenAI SDK

---

### Task 1: Add config tests for Vertex location

**Files:**
- Modify: `tests/test_config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
def test_get_vertex_location_prefers_vertex_location() -> None:
    from fitcv.config import get_vertex_location
    assert get_vertex_location({"location": "US", "vertex_location": "us-central1"}) == "us-central1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL because `get_vertex_location` does not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
def get_vertex_location(config: dict[str, Any]) -> str:
    value = str(config.get("vertex_location", "")).strip()
    if value:
        return value
    return "us-central1"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS

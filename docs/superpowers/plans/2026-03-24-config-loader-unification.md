# Config Loader Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `fitcv.config.load_config()` the single config entry point while temporarily supporting both `.env.yaml` and `config/env.yaml`.

**Architecture:** Extend the shared config loader to resolve both config paths and normalize the runtime shape, then switch pipeline code and tests to use that shared loader. Keep the change narrow to config access and regression tests.

**Tech Stack:** Python, pytest, YAML config

---

### Task 1: Add failing config resolution tests

**Files:**
- Modify: `tests/test_config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for default and legacy path resolution**
- [ ] **Step 2: Run `python -m pytest tests/test_config.py -v` and verify failure**
- [ ] **Step 3: Implement minimal loader changes in `src/fitcv/config.py`**
- [ ] **Step 4: Run `python -m pytest tests/test_config.py -v` and verify pass**

### Task 2: Switch pipeline to shared loader

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write a failing pipeline test that expects the shared loader to be called**
- [ ] **Step 2: Run `python -m pytest tests/test_pipeline.py -v -k config` and verify failure**
- [ ] **Step 3: Replace raw YAML loading with the shared config loader**
- [ ] **Step 4: Run `python -m pytest tests/test_pipeline.py -v -k config` and verify pass**

### Task 3: Run focused regression suite

**Files:**
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Run `python -m pytest tests/test_config.py tests/test_pipeline.py tests/test_ai_score.py -v`**
- [ ] **Step 2: Review the diff for config-only changes**
- [ ] **Step 3: Commit with a focused config-unification message**

---
layer: change
artifact_type: spec
status: proposed
name: candidate-profile-private-surface
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-checkpoint-and-continue-truth
targets:
  - data/candidate_profile.yaml
  - data/candidate_profile.template.yaml
  - data/candidate_profile.private.yaml
  - .gitignore
  - repo_config/publication-config.json
  - tests/test_candidate_profile_template_contract.py
related_features: []
related_stages: []
---

# Candidate Profile Private Surface Spec

## Summary

Split candidate profile source into:

- public-safe reusable scaffold: `data/candidate_profile.template.yaml`
- local-only private data file: `data/candidate_profile.private.yaml`
- compatibility-safe legacy path: `data/candidate_profile.yaml`

## Requirements

- `candidate_profile.template.yaml` must preserve stable profile shape with placeholders only.
- `candidate_profile.private.yaml` must carry private user-owned values and remain local-only.
- `candidate_profile.yaml` must remain parseable for existing path consumers and must not contain real personal data.
- `.gitignore` must block accidental local commit of `candidate_profile.private.yaml`.
- `repo_config/publication-config.json` must explicitly forbid export of `data/candidate_profile.private.yaml`.
- Regression tests must verify file existence, YAML parse validity, required top-level scaffold keys, and absence of known private literals in template scaffold.

## Validation

- `python scripts/validate_repo_config.py`
- `pytest -q tests/test_candidate_profile_template_contract.py`
- `python scripts/validate_repo_contracts.py --fast`

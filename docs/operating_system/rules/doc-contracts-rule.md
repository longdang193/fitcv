---
name: doc-contracts-rule
description: Enforce document contract consistency for templates, lifecycle metadata, and generated surfaces.
alwaysApply: true
required_reads:
  - docs/operating_system/doc-system-lifecycle.md
tags:
  - rule
  - docs
  - metadata
---

# Document Contracts Rule

Maintain canonical document contracts.

## Requirements

- Preserve required frontmatter and lifecycle metadata.
- Keep generated surfaces derived from declared source-of-truth files.
- Update validators and generated outputs together when contracts change.
- Avoid duplicate ownership between canonical sources and generated artifacts.
- Keep file naming and lineage references aligned with active schema.

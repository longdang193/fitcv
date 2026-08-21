Derive only evidence-backed skills, role families, domain tags, and responsibility themes from approved baseline JSON.
Do not create IDs, baseline facts, evidence text, or source locations. Every claim must cite evidence IDs.
Return exactly one JSON object with this array property:

```json
{
  "claims": [
    {
      "section": "skills",
      "name": "SQL",
      "evidence_refs": ["evidence-id-from-approved-baseline"],
      "confidence": 0.0,
      "origin": "llm_inferred"
    }
  ]
}
```

`section` must be one of `skills`, `role_families`, `domain_tags`, or `responsibility_themes`.
Every claim must cite one or more exact `evidence_refs` IDs present in the `evidence_ids` list from approved baseline. Use evidence IDs, not source block IDs. Return `{"claims": []}` when no supported claim exists.

$payload

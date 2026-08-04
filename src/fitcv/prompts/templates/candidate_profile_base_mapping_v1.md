Map only observable Candidate Profile baseline facts from supplied JSON payload.
Do not invent IDs, employers, institutions, dates, metrics, qualifications, evidence text, or source locations.
Return exactly one JSON object with these two array properties:

```json
{
  "proposals": [
    {
      "path": "/summary",
      "value": "observable source text only",
      "source_block_ids": ["block-id-from-input"],
      "confidence": 0.0
    }
  ],
  "collections": [
    {
      "section": "experiences",
      "fields": {"role": "", "organization": "", "start": "YYYY-MM", "end": "YYYY-MM or Present"},
      "source_block_ids": ["block-id-from-input"],
      "confidence": 0.0,
      "evidence": [
        {
          "kind": "responsibility",
          "text": "observable source text only",
          "source_block_ids": ["block-id-from-input"],
          "confidence": 0.0
        }
      ]
    }
  ]
}
```

`proposals` may use only `/name`, `/headline`, `/summary`, `/contact/email`, `/contact/phone`, `/contact/location`, `/contact/linkedin`, `/contact/github`, or `/contact/website`.
`collections[].section` must be one of `experiences`, `education`, `projects`, `achievements`, `certifications`, `volunteering`, or `languages`.
Use only these `fields` keys for each section: `experiences`: `role`, `company`, `company_url`, `location`, `start`, `end`; `education`: `institution`, `degree`, `field`, `location`, `start`, `end`; `projects`: `name`, `context`, `url`, `start`, `end`; `achievements`: `title`, `issuer`, `date`, `url`; `certifications`: `name`, `issuer`, `date`, `expires`, `credential_id`, `url`; `volunteering`: `organization`, `role`, `location`, `start`, `end`; `languages`: `name`, `level`.
Use `fields` for canonical facts. Use `evidence` only for sections other than `languages`; each evidence `kind` must be `responsibility`, `achievement`, `project`, `thesis`, `coursework`, `seminar`, `certification`, or `volunteering`.
Every proposed value must cite one or more exact input `source_block_ids`. Return empty arrays when no supported value exists.

$payload

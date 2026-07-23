# Pipeline Settings Page Suggestions

## Scope

`Overview` owns frequent, outcome-facing controls. Every other Pipeline page owns one distinct configuration concern. A control must have one editable home; related pages may explain it, but must not duplicate it.

## Enrichment

### Candidate scope

| Label | Description |
|---|---|
| **Maximum Applications per Source** | Stop collecting after this many applications from one source. |
| **Maximum Posting Age** | Only enrich jobs posted within this many days. |

### Advanced

| Label | Description |
|---|---|
| **Skip Incomplete Listings** | Ignore jobs missing essential title, company, or description details. |

Keep shared provider request pacing and Enrichment concurrency in `Runtime & Limits`. Enrichment submits one job per executor task; its ten-row persistence buffer is internal and not configurable.

## Rules & Filters

### Eligibility rules

| Label | Description |
|---|---|
| **Seniority Match** | Exclude roles outside target seniority. |
| **Location & Work Mode** | Apply selected location and remote-work exclusions. |
| **Contract Type** | Exclude unsupported employment or contract types. |
| **Experience Level** | Exclude roles that require an unsuitable experience level. |

### Review behavior

| Label | Description |
|---|---|
| **Require Fit Context** | Exclude jobs without enough information to assess fit. |

Use one toggle per rule. Show a short applied-rule summary, not duplicate rule inputs.

## Shortlist

### No standalone controls

Shortlist is an output stage. Show an empty state:

> Shortlist uses Candidate Scope, Eligibility Rules, and Ranking. No separate configuration is needed here.

Do not render a Restore Defaults button or empty settings card.

## Ranking

### Fit labels

| Label | Description |
|---|---|
| **Strong Fit Threshold** | Minimum score needed for a Strong Fit label. |
| **Stretch Fit Threshold** | Minimum score needed for a Stretch Fit label. |

### Ranking policy

| Label | Description |
|---|---|
| **Structured Factor Weights** | Balance skills, title, seniority, preferences, location, and language. |
| **Preference Mix** | Balance domain, role-family, and work-mode preferences. |

Both weight rows open transactional dialogs. Do not repeat AI reranking pool size here; Overview owns it.

## CV Analysis

### Semantic alignment

| Label | Description |
|---|---|
| **Semantic Alignment** | Compare meaning as well as exact wording in CV and job details. |
| **Embedding Model** | Model used when semantic alignment is enabled. Read-only. |

### Matching balance

| Label | Description |
|---|---|
| **Lexical and Semantic Balance** | Set exact-word and meaning-based balance for skills, roles, responsibilities, and domains. |

Use one transactional dialog. Each lexical and semantic pair must total `1.00`. Do not repeat Evidence Items per Job; Overview owns it.

## CV Generation

### Output format

| Label | Description |
|---|---|
| **CV Preset** | Supported CV format. Read-only until more than one preset exists. |
| **Generation Model** | Model used to prepare CV content. |
| **Maximum Pages** | Maximum length of generated CV output. |

### Included sections

| Label | Description |
|---|---|
| **Summary** | Include professional summary. |
| **Experience** | Include work experience. |
| **Education** | Include education history. |
| **Skills** | Include skills section. |
| **Projects** | Include relevant projects. |
| **Certifications** | Include certifications. |
| **Publications** | Include publications when available. |
| **Languages** | Include language proficiency. |

## Runtime & Limits

### Provider request pacing

| Label | Description |
|---|---|
| **Minimum Request Start Interval (seconds)** | Minimum time between generative request starts for the same provider connection. Providers are paced independently; `0` disables pacing. |

Request pacing is global for generative provider calls. System **Initial Backoff** remains a separate retry delay.

### Stage concurrency

Use a compact stage matrix. One row per stage; show only supported controls.

| Stage | Controls |
|---|---|
| **Enrichment** | Maximum Concurrent Jobs |
| **Ranking** | Maximum Concurrent Jobs |
| **CV Analysis** | Maximum Concurrent Jobs |
| **CV Generation** | Maximum Concurrent Jobs |

Each stage submits one runnable job per executor task. CV Analysis is local and does not use provider request pacing. This page is sole owner for `llm_runtime.request_start_interval_secs` and `stage_runtime.*.concurrency`; never show retired delay or batch controls elsewhere.

## Automation & Reuse

### Reuse

| Label | Description |
|---|---|
| **Reuse Enrichment Results** | Reuse matching enrichment output. |
| **Reuse Ranking Results** | Reuse matching ranking output. |
| **Reuse CV Analysis** | Reuse matching CV analysis output. |
| **Reuse Generated CVs** | Reuse matching generated CV output. |
| **Reuse Synonym Triage** | Reuse matching synonym triage output. |

### Advanced automation

| Label | Description |
|---|---|
| **Generate Synonym Proposals** | Suggest terms for review. |
| **Apply Approved Synonyms** | Apply reviewed synonym decisions. |
| **Promote Approved Synonyms** | Add approved decisions to shared reuse. |
| **Require Manual Review** | Require human review before synonym changes take effect. |

Keep this section collapsed by default. `AI Accept Suggestions` should remain hidden until product policy explicitly permits unattended acceptance.

## Interaction Rules

- Direct valid changes persist immediately.
- Transactional weight groups save only after validation.
- Each populated page has a page-scoped **Restore Defaults** button.
- Omit empty cards and empty Advanced sections.
- Shortlist has no Restore Defaults button because it owns no controls.

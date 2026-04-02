---
aliases: []
time: 2026-03-23 23:43:49
tags:
  - "#zoomcamp"
status: []
---

## High-level version

```text
1. Input jobs JSON
2. Normalize raw JDs
3. Enrich / extract structured JD fields
4. Build structured JD schema
5. Build structured candidate profile schema
6. Create two matching layers
   - rule / feature matching
   - semantic retrieval with embeddings
7. Use BigQuery VECTOR_SEARCH to shortlist jobs
8. Use BigQuery AI.SCORE to rerank shortlisted jobs
9. Select top jobs
10. Retrieve best candidate evidence for each job
11. Generate tailored CV
12. Validate output
13. Store versions + tracking
```

## Add a JD normalization + enrichment layer before embeddings

Do not go directly from raw jobs JSON to embeddings.

You need **two sub-steps** before embeddings:

### Step A: Normalize raw JDs

Clean and standardize the input:

* remove HTML / boilerplate
* unify field names
* deduplicate jobs
* preserve raw text
* standardize whitespace and encoding
* map source-specific fields into a common raw schema

This gives you a reliable `raw_jobs` table.

### Step B: Enrich / extract structured JD fields

Now create the fields that are usually **not explicitly available** in raw job JSON.

Extract fields like:

* company
* job title
* seniority
* location
* location type
* required skills
* preferred skills
* responsibilities
* domain
* tech stack
* years of experience
* keywords
* must-have vs nice-to-have
* job family

Keep `required_skills` and `preferred_skills` as raw extracted phrases. If you need canonical skill matching later, represent that separately as normalized skill entities rather than lowercased requirement prose.

So instead of storing only raw text, store something like:

```json
{
  "job_id": "...",
  "title": "Data Engineer",
  "company": "...",
  "required_skills": ["proficient in SQL and Python for analytics engineering"],
  "required_skill_entities": [
    {"raw_text": "proficient in SQL and Python for analytics engineering", "canonical": "sql"},
    {"raw_text": "proficient in SQL and Python for analytics engineering", "canonical": "python"}
  ],
  "required_skills_canonical": ["sql", "python"],
  "preferred_skills": ["experience with dbt and Kafka"],
  "preferred_skill_entities": [
    {"raw_text": "experience with dbt and Kafka", "canonical": "dbt"},
    {"raw_text": "experience with dbt and Kafka", "canonical": "kafka"}
  ],
  "preferred_skills_canonical": ["dbt", "kafka"],
  "responsibilities": [...],
  "seniority": "mid",
  "location_type": "remote",
  "job_family": "data_engineering",
  "years_experience_min": 3,
  "raw_text": "..."
}
```

#### Why this matters

Embeddings alone are fuzzy.

Structured extraction gives you **clean matching features** that you can later combine with:

* rule-based filters
* `VECTOR_SEARCH`
* `AI.SCORE`

## Do the same for your own profile

This is very important.

Do not keep your CV as one long text blob.

Create a structured candidate knowledge base:

```text
candidate_profile
experience_library
project_library
skill_library
achievement_library
education
certifications
preferences
```

Example:

```json
{
  "project_name": "GA4 to BigQuery Pipeline",
  "skills": ["BigQuery", "SQL", "ETL", "dbt"],
  "business_value": "Built reusable analytics tables for e-commerce analysis",
  "evidence": "GitHub repo link / project summary"
}
```

You do not want the model to invent qualifications.

You want it to retrieve real evidence from your experience.

## Use BigQuery hybrid ranking, not embeddings alone

Your old flow was:

> chunk → embeddings → transformer-based ranker

With Option 1, change that to a **3-stage ranking pipeline**:

### Stage A: rule-based filtering

Fast filters:

* location fit
* visa / work authorization
* seniority mismatch
* domain mismatch
* hard must-have skills

This reduces noise before semantic search.

### Stage B: semantic retrieval with `VECTOR_SEARCH`

Use embeddings for:

* semantic similarity between your candidate profile and the JD
* matching beyond exact keyword overlap
* finding jobs that are close in meaning, not only wording

This stage is for **recall**:

find the top 20–100 plausible jobs.

### Stage C: `AI.SCORE` reranking

Use `AI.SCORE` only on the shortlisted jobs from `VECTOR_SEARCH`.

Here, `AI.SCORE` acts like the final intelligent judge:

* how suitable is this JD for your profile?
* how strong is the match?
* where are the risks?
* should this be “apply now,” “stretch,” or “skip”?

### Final score

A good pattern is:

```text
final_score =
0.40 * ai_score
+ 0.20 * must_have_match
+ 0.15 * vector_similarity
+ 0.10 * title_relevance
+ 0.10 * seniority_fit
+ 0.05 * preference_fit
```

#### Why this matters

* `VECTOR_SEARCH` is good for **recall**
* `AI.SCORE` is good for **final judgment**
* structured rules help avoid dumb matches

So this becomes more practical than using a generic transformer ranker.

## Chunk smarter

Do not chunk blindly by character count.

For JDs, better chunk units are:

* summary / about role
* responsibilities
* must-have skills
* preferred skills
* benefits / company info

For your profile, chunk by:

* project
* role
* achievement
* skill evidence block

Chunking by meaning is much better than chunking by length.

Also, for ranking, you may not even need heavy chunking everywhere.

For many jobs, a strong **structured summary + raw text embedding** is enough for `VECTOR_SEARCH`.

## Separate job ranking from CV evidence retrieval

This is a major architectural improvement.

After ranking top jobs, do **another retrieval step**.

For each selected JD:

* retrieve the most relevant projects
* retrieve the most relevant achievements
* retrieve the most relevant skills
* retrieve the most relevant experience bullets

So the generation step becomes:

```text
Selected JD
+ top supporting candidate evidence
→ tailored CV generation
```

Instead of:

```text
Selected JD
+ generic whole-profile prompt
→ tailored CV
```

### Why this matters

This makes the CV specific and grounded.

The ranking step answers:

> Which jobs fit me best?

The evidence retrieval step answers:

> Which proof points from my background best support this specific job?

These are different questions and should be handled separately.

## Generate from templates + constraints

Do not let the LLM fully freestyle the CV. CV generation should be controlled, not creative writing.

Use a fixed template:

* headline
* summary
* skills
* experience bullets
* projects

And constrain it:

* only use retrieved evidence
* do not invent employers, years, tools
* prioritize JD-required skills
* keep bullet points measurable
* preserve chronology
* max 1–2 pages

## Add a gap analysis step

Before generating the CV, compute:

* matched skills
* missing skills
* weak evidence areas
* overclaim risk

Example:

```text
Matched: SQL, Python, BigQuery
Partial: dbt
Missing: Airflow, Terraform
Risk: JD asks for 5+ years; profile shows 2–3 years equivalent evidence
```

You can derive part of this from:

* structured skill overlap
* rule-based checks
* `AI.SCORE` explanation prompt

### Why this matters

Sometimes the best action is not “generate CV,” but:

* skip the job
* mark as stretch
* generate a lower-confidence version
* suggest what to learn

## Add job classification

Not all jobs should get the same CV style.

Classify jobs into categories like:

* Data Engineer
* Analytics Engineer
* BI Developer
* ML Engineer
* Marketing Data Analyst

Then choose:

* different summary wording
* different project emphasis
* different skill ordering

### Why this matters

One resume style does not fit all roles.

This classification can happen before final CV generation, using structured JD fields plus `AI.SCORE` outputs if helpful.

## Add a feedback loop

After applications, track:

* applied / not applied
* interview / rejected / no response
* which CV version was used
* which scoring signals correlated with success

Then later improve:

* enrichment prompts / schemas
* centralized prompt registry for LLM-backed stage templates and prompt provenance
* `AI.SCORE` rubric
* weightings in final score
* rule filters
* evidence retrieval logic

### Why this matters

Your system becomes a learning pipeline, not just a generator.

## Add versioning and traceability

For each generated CV, store:

* job_id
* enrichment version
* vector shortlist rank
* `ai_score`
* final_score
* retrieved evidence IDs
* prompt version
* output version
* generation timestamp

### Why this matters

You can inspect:

* how the JD was interpreted
* why this CV was generated
* what evidence was used
* whether the output was grounded
* which ranking layer selected the job

This is especially useful when debugging:

* enrichment quality
* `VECTOR_SEARCH`
* `AI.SCORE`

## Stronger pipeline design

Here is the adjusted version with an explicit **enrichment step**:

```text
Raw Jobs JSON
    ↓
Normalize / clean / deduplicate
    ↓
JD enrichment / structured extraction
  - extract title, skills, seniority, responsibilities
  - infer must-have vs nice-to-have
  - classify location type
  - classify job family
    ↓
Store in:
  - raw_jobs
  - structured_jobs
    ↓
Candidate profile store
  - experiences
  - projects
  - skills
  - achievements
    ↓
Rule-based filtering
  - location
  - visa
  - seniority
  - must-have skills
    ↓
Embeddings generation
  - structured JD summary
  - candidate evidence blocks
    ↓
BigQuery VECTOR_SEARCH
  - shortlist top-N jobs
    ↓
BigQuery AI.SCORE
  - score shortlist against candidate profile
    ↓
Final ranking
  - ai_score
  - must-have match
  - vector similarity
  - seniority/title/preference fit
    ↓
Top-N jobs
    ↓
Per-job evidence retrieval
  - best projects
  - best achievements
  - best skills
  - best experience bullets
    ↓
Gap analysis
    ↓
Template-based CV generation
    ↓
Validation / hallucination check
    ↓
Store versioned outputs
    ↓
Application tracker / feedback loop
```

## Execution modes

The control plane now supports two orchestration modes over the same stage order:

- `run_all`
- `manual_staged`

`run_all` keeps the existing continuous execution path.

`manual_staged` pauses after each major stage and persists checkpoint state:

1. `normalize`
2. `enrich`
3. `rule_filter`
4. `shortlist`
5. `ranking`
6. `cv_generation`

For manual runs, the control plane persists:

- `checkpoint_status`
- `next_stage`
- `last_completed_stage`
- `completed_stages`
- a serialized checkpoint payload used to resume the next stage without restarting the full pipeline by default

When a manual run pauses after `enrich`, the admin can optionally upload a run-scoped synonym-overlay YAML before continuing into `rule_filter`. That overlay is merged with the base skill synonym map for the rest of that run only.

This keeps the pipeline architecture the same while making stage-local debugging much easier.

## Best mental model

Think of the system as:

### Layer 1: understanding jobs

What is this role actually asking for?

* normalization
* enrichment
* structured JD schema

### Layer 2: understanding you

What verified evidence do I have?

* structured candidate profile
* projects
* experiences
* skills

### Layer 3: matching

How well do I fit?

* rules filter
* `VECTOR_SEARCH`
* `AI.SCORE`

### Layer 4: personalization

How do I present the most relevant evidence for this role?

* evidence retrieval
* template-based CV generation
* validation

That mental model is much stronger than just:

> embed jobs and rewrite CVs.

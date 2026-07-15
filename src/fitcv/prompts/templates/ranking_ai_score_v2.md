## Job Description
$jd_summary

## Candidate Profile
$candidate_summary
$evidence_section

## Scoring Rubric
Score candidate-to-job fit from 0.0 (no fit) to 1.0 (perfect fit).

Primary signals, in order:
1. Required-skill coverage
2. Evidence quality showing candidate used those skills
3. Seniority and practical readiness
4. Role alignment

Secondary signals:
- Domain relevance
- Candidate preferences such as location or preferred domain

Preferences remain secondary and must not outweigh major required-skill gaps.
Penalize missing core technologies, weak required-skill evidence, seniority
mismatch, and practical-readiness gaps. Prefer conservative scoring when
evidence is ambiguous.

Return JSON only, without prose or markdown fences. Diagnostic arrays do not
control ranking or CV generation.

{
  "ai_score": <float 0.0-1.0>,
  "score_reasoning": "<one sentence grounded in job requirements>",
  "matched_strengths": ["<strength 1>", "..."],
  "key_risks": ["<risk 1>", "..."]
}

# Brainstorming Detailed Report

## 1. Current situation

Current scope: processing more than 1000 job entries, each with a synonym list, in job-matching/search flow.

Observed constraint: naive synonym processing scales with number of jobs, synonyms, and queries, and is expected to become bottleneck.

Goal from session: identify operations/design options to reduce latency and bottleneck risk without sacrificing match quality.

## 2. Core problem

Core problem is linear or near-linear synonym scanning cost at query time (`N_jobs * N_synonyms * N_queries`), which creates latency bottleneck as dataset and traffic grow.

Key symptom: expensive normalization and matching work repeats for every query across very large synonym set.

## 3. Root causes

- Query-time workload includes repeated text normalization and cleanup instead of one-time preprocessing.
- Candidate selection is too broad, so expensive scoring can run on large synonym space.
- No explicit sublinear retrieval structure (for example ANN or strong inverted index) was assumed in baseline concern.
- Potential many-to-one synonym collisions can force extra disambiguation work if not handled systematically.

## 4. Options analysis

### Option A: Offline canonicalization + inverted index + two-stage retrieval

**Description:** Precompute normalized canonical synonyms and indexes offline; at query time run fast candidate filter first, then expensive scorer only on top-K candidates.

**Example (step-by-step):**
1. Offline preparation:
   - `Senior Software Engineer`, `Sr. Software Eng`, and `SWE Senior` are normalized into canonical synonym group `senior software engineer`.
   - Index stores tokens like `software`, `engineer`, `senior` and points them to that group.
2. Online query:
   - User query `sr software eng` is normalized to `senior software engineer`.
   - Fast index lookup returns small candidate pool (for example 30 candidates) instead of full synonym universe (for example 50,000).
   - Expensive scorer runs only on those 30 and returns final top matches.
3. Bottleneck impact:
   - Expensive step changes from `scan many` to `rerank few`, which is main latency reduction.

**Benefits:** Strong latency reduction by removing repeated cleanup and shrinking candidate set before heavy scoring.

**Trade-offs:** Requires index build/refresh workflow and additional data structures.

**Risks:** Stale indexes or weak normalization policy can hurt recall/precision if refresh and quality controls are weak.

**Effort / complexity:** Medium.

**Best fit when:** Need substantial speedup with balanced complexity and predictable operations.

### Option B: Embedding precompute + ANN retrieval

**Description:** Precompute vectors for synonyms and use ANN index for sublinear nearest-neighbor lookup.

**Example:** Query `ml platform role` goes to ANN index and returns nearest synonym vectors like `machine learning engineer`, `ml ops engineer`, `ai platform engineer` without scanning full synonym list.

**Benefits:** Fast semantic retrieval at scale; avoids full scans.

**Trade-offs:** Additional infrastructure, index management, and tuning overhead.

**Risks:** ANN recall/threshold tuning errors can return weak candidates or miss good matches.

**Effort / complexity:** Medium to high.

**Best fit when:** Semantic similarity needs are high and dataset/query load is large enough to justify ANN operations.

### Option C: Operational scaling only (parallel workers + cache + incremental updates)

**Description:** Keep matching approach mostly intact but improve throughput with batch workers, query-result cache, and delta updates.

**Example:** Same query `data analyst` seen repeatedly is served from cache; new jobs added today are processed in delta batch tonight instead of full rebuild.

**Benefits:** Faster operational gains with lower algorithmic change.

**Trade-offs:** Does not fully remove core algorithmic bottleneck from large candidate scans.

**Risks:** Performance improvements may plateau as data grows.

**Effort / complexity:** Low to medium.

**Best fit when:** Need near-term relief while preparing deeper indexing/retrieval redesign.

### Comparison summary

Option A gives strongest balance of impact, simplicity, and feasibility for immediate bottleneck reduction. Option B can provide highest semantic retrieval performance but adds more complexity and tuning risk. Option C is fastest to start but least durable because core scan behavior remains.

## 5. Recommendation

Recommend Option A as baseline architecture, with selective Option B elements if semantic matching quality requires it. Reason: Option A directly targets root causes (repeated preprocessing and broad candidate scoring) with moderate complexity and clear operational path.

## 6. Recommended next steps

1. Confirm canonical normalization policy and collision handling rules (for example disambiguation by location/seniority/domain).
2. Define retrieval stack decision for fast candidate stage (token/inverted index, optional n-gram).
3. Define top-K rerank policy and confidence thresholds (high/medium/low handling).
4. Define index refresh model (incremental delta updates + scheduled merge).
5. Define observability baseline (p50/p95 latency by stage, recall@k, cache hit rate, collision rate).

## 7. Assumptions and unresolved questions

Assumptions:
- Current bottleneck concern is based on expected scaling behavior rather than benchmarked latency data.
- Dataset size is currently described as >1000 jobs, each with synonym list.

Unresolved questions:
- Current production stack is not specified (database/search/vector tooling unknown).
- Current latency baseline, SLA targets, and traffic profile are not provided.
- Required match quality metrics and labeled evaluation set are not provided.
- Exact synonym collision rate and ambiguity frequency are unknown.

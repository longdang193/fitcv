# Success Outcomes

FitCV succeeds for the current completion target when one trusted user can use
it as a practical assistant for deciding which jobs are worth pursuing and
preparing grounded CVs for those jobs.

FitCV starts with candidate information and jobs that the user either adds or
collects through FitCV's supported job scans.

It ends when the user has reviewed job recommendations and, for a suitable job,
reviewed or downloaded a tailored CV.

FitCV is not intended to be a general-purpose job-search engine across
arbitrary websites. Submitting applications and managing the hiring process
after that remain outside the current completion target.

## Personal Job-Search Journey

### 1. Get ready for normal use

The user can choose supported provider settings and where FitCV keeps local
data. After setup, normal use should not require Python, Docker, Git, terminal
commands, or knowledge of FitCV's internals.

### 2. Build and maintain the candidate profile

Before a normal profile-selected run, the user can create a Candidate Profile
from a supported CV or other supported profile source. The user does not need
to manually write FitCV's internal profile format.

FitCV helps organize source-supported information such as:

- work experience
- education
- projects and achievements
- certifications and other relevant experience
- skills supported by that experience
- job-search preferences where applicable

FitCV keeps information supported by the user's source material distinct from
additional suggestions it makes from that information. The user can:

- review, correct, add, or remove profile information
- see where important information came from
- review suggested skills or other conclusions separately
- reject or correct unsupported suggestions
- save an unfinished profile and resume later without starting over
- confirm the profile before FitCV uses it for job matching or CV generation

FitCV must not silently turn uncertain or unsupported information into accepted
facts about the user. Only an active, confirmed profile can be selected for a
normal profile-based run.

After confirmation, the user can update the profile as their experience,
skills, or preferences change. Each update applies to future use and must not
silently change the candidate information recorded for previous runs. The user
can keep, archive, and restore profiles as needed.

### 3. Collect or add jobs to review

The user can bring jobs into FitCV through supported job scans or supported job
inputs they already have.

They can:

- scan supported company career sites for current job postings
- choose which tracked companies to scan
- narrow a scan using supported details such as job title, location, or publication time
- review jobs collected by a Scan
- reuse useful results from an earlier successful Scan
- add supported job-posting data they already have
- combine supported job inputs where FitCV allows it

FitCV makes clear whether the selected jobs are ready to use. If a Scan or
supplied job data cannot be used, FitCV explains what happened and what the user
can do next.

### 4. Start and follow a run

The user can start the normal job-search process through the FitCV interface
using sensible defaults. FitCV shows what started, what is happening, what
needs attention, and what the user can do next.

### 5. Narrow jobs before expensive work

FitCV removes clearly unsuitable jobs before detailed analysis. The user can
understand which jobs remain, which were rejected or held, and the important
reasons. Expensive late-stage work does not run for jobs already ruled out.

### 6. Review fit and express interest

For important jobs, the user can understand:

- how well the job fits their background
- which evidence supports the fit
- which important requirements may be missing
- why FitCV recommends pursuing, considering carefully, or skipping it

The user can also record how interested they are in a reviewed job. Fit and
personal interest are separate signals:

- a strong fit with low interest can be deprioritized personally
- a weak fit with high interest remains a weak fit
- personal interest must not hide qualification problems

The user always decides whether a job is worth pursuing.

### 7. Save jobs to revisit

While reviewing job results, the user can bookmark jobs for later
consideration. Bookmarking records that the user wants to revisit a job; it
does not mean the job is suitable or that the user has decided to apply.

The user can return to a dedicated view of bookmarked jobs from earlier job
searches. That view can show useful FitCV results and application-interest
feedback, and let the user search, filter, revisit, and remove bookmarks.

Bookmarks remain available across normal FitCV sessions until the user removes
them. If a saved job can no longer be shown or used, FitCV must make that clear
rather than silently presenting a misleading bookmark.

Bookmark, FitCV fit, and application interest remain separate signals:

- fit asks whether the job suits the user's qualifications
- interest asks how much the user wants to pursue it
- bookmark asks whether the user wants to keep it for later review

Bookmarking must not silently change fit decisions, application interest, or
personalized ranking. Exporting bookmarked jobs may support the workflow, but
is not required for core product completion.

### 8. Adapt to user preferences when chosen

FitCV can use the user's saved job feedback to improve how future jobs are
prioritized.

The user decides whether to use this personalization. Giving feedback by itself
does not automatically change future recommendations.

The user can choose personalized recommendations when enough useful feedback
exists and return to FitCV's normal ordering when desired.

Personalization may change which suitable jobs appear more important to the
user, but it must not change whether a job meets the user's qualifications or
hide important qualification gaps.

If FitCV does not have enough reliable feedback to personalize results, it
explains that clearly and continues using the normal ordering.

### 9. Prepare a grounded CV

For a job the user chooses to pursue, FitCV can prepare a tailored CV when
there is enough supporting information. The CV emphasizes relevant experience
without inventing qualifications, experience, achievements, or skills.

If FitCV cannot create a trustworthy CV, it clearly explains why instead of
presenting incomplete or unsupported content as successful.

### 10. Review the result before using it

The user can review the generated CV, understand important limitations, and
obtain the useful final output without inspecting technical files or using
terminal commands. FitCV does not submit applications or take other external
action for the current completion target.

### 11. Return and continue

A returning user can reopen FitCV without repeating setup, keep candidate data,
profile revisions, and important settings, review previous runs, bookmarks, and feedback,
process another job batch, continue after a normal interruption, and understand
or recover from a failed or cancelled run when recovery is possible.

Repeated use should feel like continuing a job search with an assistant that
can become better aligned with the user's stated preferences, not managing a
software system.

## Experience Outcomes

The normal journey must be understandable, practical, and trustworthy:

- important screens expose clear next steps and preserve job, profile, and run context
- progress, waiting, success, failure, cancellation, and inability to continue reflect what actually happened
- common problems provide understandable explanations and useful recovery
- advanced settings and diagnostics remain available without dominating normal use
- the user remains responsible for job choices, CV review, downloads, and all action outside FitCV

## Product Quality Outcomes

Personal FitCV must:

- consistently narrow job lists into more useful choices
- explain important fit and prioritization decisions
- keep profile facts and generated CV content grounded in user-provided information
- keep source-supported profile information distinct from suggestions and approvals
- avoid unnecessary late-stage time and AI cost
- preserve truthful results when work fails, stops, or is cancelled
- preserve important user information, profile revisions, settings, feedback, bookmarks, and prior personalization choices across normal restarts
- preserve the candidate profile snapshot and revision used by previous runs
- keep credentials and sensitive information out of logs and downloadable diagnostics
- keep the user's data under their control

## Completion Gate

Personal FitCV is complete when representative acceptance evidence shows that the
full personal job-search journey works through the FitCV interface, not only
that individual technical components work.

Candidate Profile evidence must exercise real persisted creation, review,
confirmation, revision, lifecycle, and run-selection behavior. Mock or template
rendering alone does not satisfy the gate.

Evidence must include at least:

1. a first-time user creating a Candidate Profile from a supported source without manually writing FitCV's internal format
2. the user reviewing and correcting source-supported profile information while seeing important source references
3. suggestions remaining distinguishable from source-supported information and unsupported suggestions remaining rejectable
4. an unfinished profile being saved and resumed, while an unconfirmed profile cannot be selected for a normal run
5. a confirmed profile being used in a normal job-search run
6. a confirmed profile being updated as a new version without changing the candidate information recorded for previous runs, with archive and restore behaving clearly when used
7. first-time setup reaching a useful job-search result
8. a successful Scan collecting jobs from selected tracked companies and the user reviewing its output
9. an empty or failed Scan showing an understandable outcome and next action
10. a successful Scan output being used in a Run
11. an earlier successful Scan result being reused in a later Run
12. a mixed batch of good and poor matches being narrowed to useful jobs
13. understandable reasons for important recommendations, rejections, and holds
14. the user bookmarking and removing jobs while reviewing results
15. the user returning later to a clear bookmarked-job list from earlier searches, searching or filtering it, and continuing review
16. bookmark state remaining separate from fit decisions, application interest, and personalized ranking
17. the user recording interest feedback that remains available later
18. sufficient feedback producing a personalized-ranking option or a clear insufficient-evidence result
19. the user choosing personalized or normal ordering and returning to normal ordering when desired
20. a high-interest weak-fit job remaining visibly unsuitable rather than being promoted as qualified
21. grounded CV generation for a suitable job
22. CV generation being correctly held or refused when information is insufficient
23. a failed, cancelled, or interrupted run leaving truthful status and recovery guidance when recovery is possible
24. important user information, profile revisions, settings, bookmarks, and prior feedback remaining available after restart
25. the complete normal workflow working without terminal-first operation
26. a user-experience review finding no issue that prevents normal discovery, understanding, completion, or trust of an important journey

A completion-blocking issue is one that prevents normal personal use or makes
an important result misleading, even when underlying technical logic passes.
Supporting, maintenance, and deferred work do not block completion unless this
intent layer explicitly promotes them.

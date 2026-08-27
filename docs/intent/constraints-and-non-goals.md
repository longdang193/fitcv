# Constraints And Non-Goals

## Constraints

- the current completion target is personal use by one trusted user on a Windows computer they control
- the user must remain in control of their data, settings, credentials, backups, and when FitCV starts or stops
- personal and local use do not remove basic safety requirements: FitCV must reject invalid input where needed, protect credentials, protect local access, and keep secrets out of logs, diagnostics, and downloaded files
- FitCV should avoid expensive analysis or CV generation for jobs that earlier review has already ruled out
- user feedback may improve how future jobs are prioritized, but personal preference must not hide qualification problems or change whether a job is suitable
- later design and implementation work may add detail, but it must not make new product areas mandatory without first changing this intent

## Non-Goals

- supporting multiple users, shared-user environments, or separate user accounts for the current completion target
- operating FitCV as a public Internet service or as a service that must remain available through machine or service failures
- becoming a general-purpose job-search engine across arbitrary websites; supported FitCV job scans remain part of the product
- replacing the user's judgment with fully automatic decisions about which jobs to pursue
- submitting job applications, contacting employers, or taking other actions outside FitCV on the user's behalf
- managing the later hiring process such as interview scheduling or employer communication
- requiring advanced monitoring, large-scale operation, broader deployment support, or other production hardening before the personal product can be considered complete

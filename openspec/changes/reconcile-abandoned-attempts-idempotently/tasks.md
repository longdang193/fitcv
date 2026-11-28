# Tasks

- [x] 1.1 Add a regression test proving multiple expired attempts produce one terminal retry decision and one enqueue.
- [x] 1.2 Implement single-owner abandoned-attempt reconciliation while preserving cancellation and retry limits.
- [x] 1.3 Run focused unit and SQLite integration tests and validate the OpenSpec change.
- [x] 1.4 Resolve relative persisted jobs paths from the run configuration directory and add regression coverage.
- [ ] 1.5 Verify controlled or synthetic abandoned-inline recovery through the supported path, preserving the native persisted jobs input path and proving that uncertain ownership does not enqueue a replacement.

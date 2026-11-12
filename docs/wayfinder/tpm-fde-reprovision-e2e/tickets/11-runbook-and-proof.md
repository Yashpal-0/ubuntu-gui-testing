---
id: "11-runbook-and-proof"
title: "On-demand runbook and full-suite proof"
type: task
label: "wayfinder:task"
state: open
parent: map
assignee: null
depends_on: ["07-state-cases", "08-happy-path-cases", "09-failure-cases", "10-coverage-manifest"]
---

# On-demand runbook and full-suite proof

## Question

Write the on-demand runbook and produce one full-suite pass: exact commands, private paths, per-case YARF log and video, secret handling, and a results table.

## Notes

This is the destination proof. It is complete only when all 21 cases have a pass or a cited blocker.

Runbook: `tests/desktop-security-center/desktop-security-center-reprovision/README.md`; results table: `docs/wayfinder/tpm-fde-reprovision-e2e/results.md`.

## Status

The runbook is written: prerequisites, the exact `yarf run` invocation per case,
the fixture table, secret handling with 0600 files, how to read `output.xml`,
`log.html` and `video.webm`, and the troubleshooting list. It also states that
there is no single-invocation whole-suite command, because `--fde-config`
requires `--robot-test` and the fixture selects the clone mutation; the proof is
one clone per case with its own run directory.

The results table accounts for all 21 requested scenarios: ten passes, each
citing the run directory whose `output.xml` reports `pass="1" fail="0"`, and
eleven cited blockers — the ten unreachable snapd state kinds with source
citations, and the power-cut rollback oracle recorded in
[ticket 09](09-failure-cases.md#status). No row is a mock or a skipped run.

The only open dependency is ticket 09: the power-cut case is implemented,
registered in the plan, and currently fails because the interrupted clone
reboots before offering the recovery key. This ticket closes when that case
either passes or its blocker is recorded as final.

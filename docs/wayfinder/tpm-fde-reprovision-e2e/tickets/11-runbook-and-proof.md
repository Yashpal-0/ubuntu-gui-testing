---
id: "11-runbook-and-proof"
title: "On-demand runbook and full-suite proof"
type: task
label: "wayfinder:task"
state: closed
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

The results table accounts for all 21 requested scenarios: eleven passes, each
citing the run directory whose `output.xml` reports `pass="1" fail="0"`, and ten
cited blockers — the ten unreachable snapd state kinds, each with its source
citation. No row is a mock or a skipped run.

[Ticket 09](09-failure-cases.md#status) closed with a pass:
`tpm-repair-power-cut.robot` interrupts a confirmed repair, proves snapd rolled
the interrupted attempt back and failed it with `missing reprovision context`,
checks both recovery-key outcomes, then completes a second repair whose reboot
unlocks without a key (`artifacts/fde-jrq4rij1`, 357 s). The destination proof
is complete: every case has a pass or a cited blocker.

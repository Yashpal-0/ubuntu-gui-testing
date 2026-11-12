---
id: "10-coverage-manifest"
title: "Coverage manifest and verdicts"
type: task
label: "wayfinder:task"
state: closed
parent: map
assignee: null
depends_on: ["07-state-cases", "08-happy-path-cases", "09-failure-cases", "12-snapd-emission-paths"]
---

# Coverage manifest and verdicts

## Question

Regenerate the coverage inventory against the pins (`status`, `auto-repair-result`, `recommendation`, `kind`, `action`) and give every entry one verdict:

- `executed`;
- `recipe-known`;
- `gap(reason)`.

Map each entry to a case or a documented exclusion.

## Notes

Resolve the recovered manifest's contradictions (for example `shutdown-required` classed as hardware although T16 filmed it) and mark entries whose only recipe used canned TPM replies. No entry without a verdict.

Reference: `/tmp/tmp42m1jbm5/desktop-security-center-reprovision/tpm-fde-coverage.yaml`.

Manifest ships at `tests/desktop-security-center/desktop-security-center-reprovision/tpm-fde-coverage.yaml`.

## Input from research

Ticket `12-snapd-emission-paths` corrects two mappings (`disable-endorsement-hierarchy` → `tpm-device-disabled`; `tpm-hierarchies-owned` is pre-install only), shows `status/failed` is client-side, and lists four unreachable kinds. Regenerate from the research file, not from the recovered manifest alone.

## Resolution

`tests/desktop-security-center/desktop-security-center-reprovision/tpm-fde-coverage.yaml`
holds every entry with one verdict: 33 kinds, 11 actions, 6 statuses, 6
auto-repair results, 3 recommendations. Validated counts: 11 `executed`, 0
`recipe-known`, 48 `gap(reason)`; no entry without a verdict, and every
`executed` entry names a passing case in which it was observed. The accepted
pre-repair result alternatives are not a guarantee of the result on every run.

The contradictions the ticket listed are resolved in the file: `shutdown-required`
is `gap(ppi-action-phase)`, `unsupported-platform` and the other host-security
kinds are `gap(non-vm-only)`, `status/failed` is `gap(client-only)`, and the
kinds whose only recipe canned TPM replies or forged daemon state are
`gap(canned-reply-only)` or `gap(fabricated-response)`.

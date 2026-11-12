---
id: "06-host-state-legitimacy"
title: "Legitimacy rule for host-created states"
type: grilling
label: "wayfinder:grilling"
state: closed
parent: map
assignee: "@agent"
depends_on: []
---

# Legitimacy rule for host-created states

## Question

Which host-created states count as legitimate E2E fixtures?

## Notes

Disk, LUKS, keyslot, filesystem damage and missing files clearly do. Does editing snapd's private `state.json` to fake a repair result count?

Decide against the recovered manifest's "forged daemon state is not evidence" standard and record the rule in the map Notes.


## Input from research

Ticket `12-snapd-emission-paths` flags four `recipe-known` entries as leaning on forged state or canned replies: `shutdown-required` (T16d), `unsupported-platform` (T44), `auto-repair-result=failed-encryption-support` (T8), `invalid-tpm-response` (T37). Use these as the first test cases for the rule: which, if any, still count as real E2E evidence?
HITL: one question round with the user.

## Resolution

User agreed to the standard:

1. **Core rule**: Only mutations at device, disk, filesystem, firmware, or hardware-abstraction boundaries count as legitimate E2E fixtures. Editing snapd's private `/var/lib/snapd/state.json` or mocking internal daemon state is prohibited — snapd must derive its state and emissions from actual device facts.
2. **Excluded entries**:
   - `unsupported-platform` (T44): Excluded (relies on forged `storage-encrypted: unsupported-platform` in `state.json`).
   - `auto-repair-result=failed-encryption-support` (T8): Excluded (relies on forged `auto-repair-result` in `state.json`).
3. **Accepted entries**:
   - `shutdown-required` (T16d): Accepted here when induced via real TPM PPI transition sysfs interface (`/sys/class/tpm/tpm0/ppi/transition_action`). Superseded by [Ticket 07](07-state-cases.md): the kind is action-phase, and the recipe forged `ppi/transition_action`.
   - `invalid-tpm-response` (T37): Accepted only if induced at the TPM device boundary; otherwise excluded to preserve 100% genuine evidence.

Recorded in `docs/wayfinder/tpm-fde-reprovision-e2e/map.md` under `## Notes`.

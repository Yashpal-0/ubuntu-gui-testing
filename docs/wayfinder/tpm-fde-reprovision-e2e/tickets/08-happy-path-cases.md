---
id: "08-happy-path-cases"
title: "Five reprovision happy-path cases"
type: task
label: "wayfinder:task"
state: closed
parent: map
assignee: null
depends_on: ["01-runner-fde-seam", "02-golden-checkpoint-export", "04-gdm-login"]
---

# Five reprovision happy-path cases

## Question

Implement 5 cases and assert the full oracle for each:

1. auth `none`;
2. PIN set before the fault;
3. passphrase set before the fault;
4. PIN added after the repair and reboot;
5. passphrase added after the repair and before reboot.

## Notes

Every case asserts `running-in-vm` first and acknowledges it with Ignore and continue before the repair page. The acknowledgement is not the repair action.

Full oracle: change `Done`; `status=active`; no recommendations after reboot; new key unlocks data and save; old key rejected; auth mode as chosen; banner gone.

## Status

All five cases have passing real-VM evidence in `results.md`, each with zero
recovery-key-pattern matches in its reports and a private video:

- case 1, auth `none`: `artifacts/fde-fnircwvi` (476 s);
- case 2, pre-enrolled PIN: `artifacts/fde-ilf71dfu` (257 s);
- case 3, pre-enrolled passphrase: `artifacts/fde-2sj8zuoj` (267 s);
- case 4, PIN added after repair and reboot: `artifacts/fde-abpqgvdm` (636 s).
- case 5, passphrase added after repair and before reboot: `artifacts/fde-e2vs086r`
  (341 s).

Case 5, `tpm-passphrase-before-repair-reboot.robot`, adds a passphrase through
the application before the first repaired reboot, boots with that passphrase,
and the full oracle holds, with zero recovery-key-pattern matches and a private
video. The first two replays stopped at the Add step because the button template
never matched the 1280x800 dialog; the template is now a pixel-exact crop.

The former preparation blocker is implemented: `enroll-auth` boots the healthy
clone, enrolls and verifies authentication using real snapd, shuts down, and only
then applies `clear-tpm-state`. The source checkpoint is unchanged. Case 5 now
meets the full oracle, so this ticket is closed.

Output lands in `tests/desktop-security-center/desktop-security-center-reprovision/`, registered in `tests/desktop-security-center/plans/tpm-fde.yaml`.

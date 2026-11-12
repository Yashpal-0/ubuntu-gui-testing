---
id: "12-snapd-emission-paths"
title: "snapd emission paths and recipe legitimacy"
type: research
label: "wayfinder:research"
state: closed
parent: map
assignee: "@agent"
depends_on: []
---

# snapd emission paths and recipe legitimacy

## Question

Which of the 33 check kinds, 11 actions, 6 statuses, 6 auto-repair results and 3 recommendations does snapd `1f728a2361` actually emit to the running-system repair flow? Cite file:line.

## Notes

Resolve which `recipe-known` entries depend on canned TPM replies or forged state, and whether `shutdown-required` is really hardware-only.

Output: `research/snapd-emission-paths.md` on the throwaway `research/snapd-emission-paths` branch, which is never merged.


## Findings

[snapd-emission-paths.md](https://github.com/Yashpal-0/ubuntu-gui-testing/blob/research/snapd-emission-paths/docs/wayfinder/tpm-fde-reprovision-e2e/research/snapd-emission-paths.md) on the `research/snapd-emission-paths` branch (292 lines; 105+37 citation assertions, all re-checked).

- Four check kinds cannot reach the running-system flow: `tpm-hierarchies-owned` and `insufficient-tpm-storage` (post-install only), `missing-argument` (declared, never constructed), `addon-drivers-present` (always a warning).
- `shutdown-required` comes from PPI `StateTransitionShutdownRequired` (`secboot/efi/preinstall/checks_context.go:685-687`), not bare metal. T16d produced it by binding over `ppi/transition_action`.
- `status/failed` is client-side only: snapd defines five statuses and no `FDEStatusFailed`.
- Legitimacy flags: `shutdown-required` (T16d), `unsupported-platform` (T44), `auto-repair-result=failed-encryption-support` (T8), `invalid-tpm-response` (T37).
- Two manifest mappings are wrong: `disable-endorsement-hierarchy` yields `tpm-device-disabled`; `tpm-hierarchies-owned` is pre-install only.
AFK. No VM. Sources: `/data/External/Canonical/Work/snapd`, secboot `4924adcf6262`, recovered manifest `/tmp/tmp42m1jbm5/desktop-security-center-reprovision/tpm-fde-coverage.yaml`, T-series handoff `/tmp/handoff-tpm-fde-t-series-2026-11-10.md`.

## Resolution

snapd 1f728a2 emits only 29 of the 33 check kinds in the running-system repair flow. Four kinds are excluded (post-install only or declared-unconstructed). `shutdown-required` is emitted during PPI action-phase, not on bare metal. `status/failed` does not exist in snapd (client-only enum). Four known recipes rely on forged daemon state or canned replies, and two manifest mappings were wrong. Full findings in [snapd-emission-paths.md](https://github.com/Yashpal-0/ubuntu-gui-testing/blob/research/snapd-emission-paths/docs/wayfinder/tpm-fde-reprovision-e2e/research/snapd-emission-paths.md).

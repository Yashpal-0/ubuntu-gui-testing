---
id: "07-state-cases"
title: "Thirteen known-recipe state cases"
type: task
label: "wayfinder:task"
state: closed
parent: map
assignee: null
depends_on: ["01-runner-fde-seam", "02-golden-checkpoint-export", "04-gdm-login", "06-host-state-legitimacy"]
---

# Thirteen known-recipe state cases

## Question

Implement one case per known recipe, `auth_mode=none`, one disposable clone each, with the recipe, its cleanup and revert, and the full oracle.

## Cases

`system-not-efi`, `efi-variable-access`, `measured-boot`, `invalid-tpm-response`, `tpm-communication`, `tpm-device-disabled`, `no-suitable-pcr-bank`, `unsupported-platform`, `sys-prep-applications-present`, `weak-secure-boot-algorithms-detected`, `pre-os-secure-boot-auth-by-enrolled-digests`, `unexpected-action`, `action-failed`.

## Notes

Exclude `require-platform-reset`. Also exclude `shutdown-required`: it is PPI action-phase, not hardware-only, and the only recovered recipe (T16d) forged `ppi/transition_action`.

Every case asserts `running-in-vm` first and acknowledges it with Ignore and continue. That acknowledgement is not the repair action.

The full oracle is in the map Notes; do not weaken it per case.

Output lands in `tests/desktop-security-center/desktop-security-center-reprovision/`, registered in `tests/desktop-security-center/plans/tpm-fde.yaml`.

## Status

Three of the thirteen are implemented and passing: `sys-prep-applications-present`,
`weak-secure-boot-algorithms-detected`, `pre-os-secure-boot-auth-by-enrolled-digests`.
The weak-secure-boot replay that started after `tpm-fde.resource` last changed
(`fde-5_uhu_2y`, 13:58) timed out looking for `Disk encryption` with GNOME's
Run-a-Command dialog on screen, so it failed before the state was ever asserted;
the three state cases were rerun on the final tree before this pass claim stood.
The cleared-TPM case that exercises `running-in-vm` and `require-reprovision` is
also implemented. The other ten are not cases, and each has a source-backed
reason now instead of a failed recipe:

| kind | verdict | why, from the pinned sources |
| --- | --- | --- |
| `system-not-efi` | not reachable | `ErrSystemNotEFI` needs efivarfs to be unavailable (`check_efi.go:33-37`). The fixture boots the installed system through OVMF and its ESP, and has no BIOS boot path to reach the check without UEFI. |
| `efi-variable-access` | runtime only | Needs an efivarfs access error on a firmware variable read (`check_efi.go:33-42`, `efi.go:48-56`). Both recovered faults are runtime-only, and the firmware recreates the variables it owns. |
| `measured-boot` | firmware, no knob | `ReadEventLog` fails only when the TCG2 log is absent (`checks.go:238-241`). OVMF publishes it whenever a TPM2 is detected (`Tcg2Dxe.c:3056-3060`) and its PEI ignores `TCG2_CONFIGURATION` (`Tcg2ConfigPeim.c:4-6,44-96`). |
| `invalid-tpm-response` | fabricated only | Needs a malformed response that fails decoding or the response HMAC (`checks_context.go:497-499`). |
| `tpm-communication` | runtime only | Needs a transport-layer failure (`checks_context.go:500-502`); no running-clone fault is present at the boot-time check. |
| `tpm-device-disabled` | firmware only | The firmware must clear `shEnable` and `ehEnable` at boot (`check_tpm.go:333-343`). OVMF only disables the platform hierarchy (`PeiDxeTpmPlatformHierarchyLib.c:198-234`). |
| `no-suitable-pcr-bank` | firmware only | The active bank set is the firmware's (`Tcg2Pei.c:358-443`); the OS cannot re-allocate it, and `TCG2_CONFIGURATION` holds only the TPM device (`Tcg2ConfigNvData.h`). |
| `unsupported-platform` | not reachable | secboot's own classifier records that the host-security check fires first (`checks_context.go:506-513`). |
| `sys-prep-applications-present` | implemented | `prepare: [sysprep-app]` (`fde_host.py:1126-1180`). |
| `weak-secure-boot-algorithms-detected` | implemented | `prepare: [preos-weak-sb]` (`fde_host.py:1055-1088`). |
| `pre-os-secure-boot-auth-by-enrolled-digests` | implemented | `prepare: [preos-digest-sb]` (`fde_host.py:1096-1124`). |
| `unexpected-action` | app never sends | The app applies only an action the dialog offered (`disk_encryption_providers.dart:1127-1130`) and secboot compares it with the cached context (`checks_context.go:639-664`), so only a race can produce it. |
| `action-failed` | no state offers an action | Only a failing PPI or clear-TPM action produces it (`checks_context.go:670-678`, `:709-715`), and no boot-time state offers one. |

`plain-ovmf` remains a UEFI boot; it does not establish `system-not-efi` or
`efi-variable-access`.

Every kind in this ticket's list is therefore either a passing case or a
source-backed blocked verdict, so this ticket is closed.

## Additional unavailable-hardware case

One additional legitimate induction is implemented and passed in
`artifacts/fde-74dnlmu2` (322 s). It is outside the thirteen because the kind
is not in this ticket's list:

| item | value |
| --- | --- |
| expected kind | `no-suitable-tpm2-device` (`checks_context.go:427-429`) |
| expected actions | none; the kind has no entry in `errorKindToActions` (`checks_context.go:76-160`), so the page is repair-unavailable |
| induction | `prepare: [no-tpm]` removes `<tpm>` from the stopped clone's XML after any healthy authentication enrollment, then redefines that same UUID (`image_runner.py:278-319`); the source domain keeps its TPM |
| revert | discard the clone; the source domain and its swtpm state are untouched |
| implementation | `no-tpm` is allowed in `PREPARATIONS`; `tpm-missing-device-unavailable.robot` is registered and enters the recovery key at boot, as the cleared-TPM case does |
| why the banner appears | the unseal fails with `ErrNoTPM2Device` (`tpm2_device/device_linux.go:66-67`), which becomes `PlatformHandlerErrorUnavailable` (`tpm2/platform.go:72-75`), `PlatformDeviceUnavailableError` (`keydata.go:494-496`) and `KeyslotErrorPlatformFailure` (`activate_state.go:107-108`); `ShouldAttemptRepair` then returns `RequireReprovision` (`secboot_sb.go:250-253,278-281`) and auto-repair records it (`autorepair.go:274-292`) |
| oracle | recovery-key boot, snapd reports `require-reprovision` and `no-suitable-tpm2-device` with no fix, the UI refuses unsafe repair, repair history is unchanged and the original key still unlocks both devices |

Exact verdicts for every kind, action, status and result remain in
`tpm-fde-coverage.yaml`; the per-kind reasons are repeated in
`tests/desktop-security-center/desktop-security-center-reprovision/COVERAGE.md`.

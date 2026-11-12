# snapd emission paths and recipe legitimacy

Ticket: `12-snapd-emission-paths`. Answers two questions: which documented enum
values the running-system repair flow can actually emit, and which manifest
classifications survive inspection of the recipes that produced them.

## Method

**Pinned sources.**

- snapd `1f728a2361ba88f3c2192446df27051b5b267a48` ("tests: fix snap-delta
  spread test (#17893)"). The checkout's HEAD is `8d4d073ab3` (2026-10-23), so
  the commit is read with `git show 1f728a2361:<path>` and, for exploration,
  from the working tree after proving byte identity. Tree SHAs are equal between
  `1f728a2361` and `HEAD` for every directory this ticket cites:
  `secboot` `5343535e`, `overlord/fdestate` `e968dab4`,
  `overlord/devicestate` `bc46d618`, `daemon` `b576d2af`,
  `client` `7f21773e`. `git diff 1f728a2361 HEAD -- <those paths>` is empty.
  Citations `snapd:<path>:<line>` therefore resolve identically in both trees.
- secboot `4924adcf6262`, resolved as module
  `github.com/snapcore/secboot v0.0.0-20260925074118-4924adcf6262`, required by
  `snapd:go.mod:26`. Source read from the module cache at
  `$GOMODCACHE/github.com/snapcore/secboot@v0.0.0-20260925074118-4924adcf6262`;
  citations `secboot:<file>:<line>` are relative to `efi/preinstall/`.
- Manifest inputs: `/tmp/tmp42m1jbm5/desktop-security-center-reprovision/tpm-fde-coverage.yaml`,
  `/tmp/handoff-tpm-fde-t-series-2026-11-10.md`, and the harness underneath them:
  `~/Downloads/security-center-tpm-fde-flows/real-every-state/evidence/harness/recipes.sh`,
  `.../t-series-coverage.md`, `.../coverage.md`.

**What "running-system repair flow" means here.** The daemon serves
`GET /v2/systems/{label}` from
`runningSystemAndGadgetAndEncryptionInfoWithAction` (`snapd:overlord/devicestate/devicemgr.go:2797`).
With no action in flight it calls `secbootPostinstallCheck`
(`devicemgr.go:2862`); with an action it calls `secbootPreinstallCheckAction`
on the cached context (`devicemgr.go:2868`). The post-install path is
`PostinstallCheck` → `preinstallCheck(postInstall=true)`
(`snapd:secboot/preinstall_sb.go:143-146`), which sets
`PermitAddonDrivers` and `PostInstallChecks` and only adds `PermitVirtualMachine`
when snapd is running under test (`preinstall_sb.go:81-88`). So a kind counts as
emitted only if it can be produced with that flag set; the action phase can also
produce the action-arg and PPI-transition kinds.

Errors only reach the app when support is not available: `AvailabilityCheckErrors`
is copied into the reply only under `!encInfo.Available`
(`snapd:daemon/api_systems.go:229-231`, field at `snapd:client/systems.go:187-188`,
type at `snapd:secboot/preinstall.go:28-34`).

## 33 secboot check kinds

Emitted = can appear in `availability-check-errors` from the running-system
flow. The classifier is `classifyRunChecksError`
(`secboot:checks_context.go:390-636`); action-phase kinds come from `runAction`.

| # | Value | Emitted | Where it is produced | Reachability notes |
|---|-------|---------|----------------------|--------------------|
| 1 | internal-error | yes | `checks_context.go:405-411` (missing kernel module), `:635` (unclassified), `:893-897` (classify failure), `:921-925`, `:1013-1017` | any unclassified error; needs no hardware |
| 2 | shutdown-required | yes, action phase | `checks_context.go:685-687` on `ppi.StateTransitionShutdownRequired` | only after a POSTed PPI action; requires firmware reporting an S5 transition |
| 3 | reboot-required | yes, action phase | `checks_context.go:688-690` on `StateTransitionRebootRequired` | same, OVMF reports reboot |
| 4 | unexpected-action | yes, action phase | `checks_context.go:640-644`, `:648-652`, `:659-663`, `:700-705`, `:826-834` | stale/foreign action against the cached context |
| 5 | missing-argument | **no — never constructed** | declared only, `secboot:error_kinds.go:56-59`; no construction outside `_test.go` | `git grep MissingArgument` over non-test preinstall code returns only the declaration |
| 6 | invalid-argument | yes, action phase | `checks_context.go:724-731`, `:741-748`, `:754-761`, `:778-811` (`proceed` arg) | app sends only the offered kind, so rarely hit |
| 7 | action-failed | yes, action phase | `checks_context.go:670-678`, `:710-714`, `:766-771` | PPI request write failure, TPM2_Clear failure |
| 8 | running-in-vm | yes | `checks.go:188-197` → `checks_context.go:413-415` | fires first in any VM unless `PermitVirtualMachine` (`preinstall_sb.go:82-85`) |
| 9 | system-not-efi | yes | `secboot:check_efi.go:36-37` → `checks_context.go:416-418` | `checkSystemIsEFI` runs in both modes (`checks.go:205`) |
| 10 | efi-variable-access | yes | `checks.go:397-399`, `:435-437` return `&EFIVariableAccessError` → `checks_context.go:419-426` | plain OVMF without Secure Boot variables; also any efivarfs fault |
| 11 | no-suitable-tpm2-device | yes | `ErrNoTPM2Device`/`ErrNoPCClientTPM`, `secboot:check_tpm_intel.go:43`, `check_tpm.go:313-331` → `checks_context.go:427-429` | no TPM node, or non-PC-Client TPM |
| 12 | tpm-device-failure | yes | `checks_context.go:430-432` ← `ErrTPMFailure` at `secboot:check_tpm.go:295-299` | TPM self-test failure |
| 13 | tpm-device-disabled | yes | `secboot:check_tpm.go:340-343` (`StartupClear` shEnable/ehEnable) → `checks_context.go:433-435` | pre-install **and** post-install |
| 14 | tpm-hierarchies-owned | no | `checks_context.go:437-442`; producer `check_tpm.go:398-462` | whole block is `if flags&checkTPM2DevicePostInstall == 0` (`check_tpm.go:398`); post-install never runs it |
| 15 | tpm-device-lockout-locked-out | yes | `check_tpm.go:369` → `checks_context.go:445-464` | only when lockout auth is unset (else `ErrTPMLockoutAvailabilityNotChecked` warning, `checks_context.go`… see `checks.go:236-242`) |
| 16 | insufficient-tpm-storage | no | `checks_context.go:467-468`; produced at `check_tpm.go:446-459` | inside the same pre-install-only block |
| 17 | no-suitable-pcr-bank | yes | `checks_context.go:470-480` | mandatory PCR inconsistent with the TCG log |
| 18 | measured-boot | yes | `checks_context.go:482-485` | event log unreadable or unparseable |
| 19 | tpm-command-failed | yes | `checks_context.go:487-496` | a TPM error response |
| 20 | invalid-tpm-response | yes | `checks_context.go:497-499` | undecodable response or bad response HMAC |
| 21 | tpm-communication | yes | `checks_context.go:500-502` | transport-layer failure |
| 22 | unsupported-platform | yes, non-VM | `checks_context.go:506-513` ← `UnsupportedPlatformError`, e.g. `secboot:check_host_security_intel.go:294`, `check_host_security_amd64.go:37` | host-security block runs only when `virtMode == detectVirtNone` (`checks.go:312-349`) |
| 23 | insufficient-dma-protection | yes, non-VM | `checks.go:324` → `checks_context.go:515-517` | same gate |
| 24 | no-kernel-iommu | yes, non-VM | `checks.go:324` → `checks_context.go:519-521` | same gate |
| 25 | host-security | yes, non-VM | `checks.go:312-333` → `checks_context.go:523-531` | same gate |
| 26 | tpm-pcr-unusable | yes | `checks_context.go:533-600` (five PCR-specific branches), `:627-633` | `contact-oem` dropped for PCRs 1/3/5 (`:178-182`, `:321-338`) |
| 27 | addon-drivers-present | no — always permitted | `checks_context.go:551-554` ← `checkDriversAndAppsMeasurements` | snapd sets `PermitAddonDrivers` unconditionally (`preinstall_sb.go:81`), so it is downgraded to a warning (`checks.go:351-382`) |
| 28 | sys-prep-applications-present | yes | `checks_context.go:575-579` | no permit flag in the snapd flow, so it is an error |
| 29 | absolute-present | yes | `checks_context.go:582-583` ← `ErrAbsoluteComputraceActive` (`checks.go:409`) | needs firmware whose measurements show Absolute |
| 30 | invalid-secure-boot-mode | yes | `check_pcr7.go:380` (`ErrNoSecureBoot`); `check_pcr7.go:394` sets the deployed-mode flag that `checks.go:453` turns into `ErrNoDeployedMode` → `checks_context.go:602-619` | Secure Boot off on SB-capable firmware, or user mode |
| 31 | weak-secure-boot-algorithms-detected | yes | `checks.go:447-449` → `checks_context.go:620-622` | weak CA key or weak Authenticode digest |
| 32 | pre-os-secure-boot-auth-by-enrolled-digests | yes | `checks.go:450-452` → `checks_context.go:623-625` | pre-OS component authenticated by an enrolled digest |
| 33 | no-hardware-root-of-trust | yes, non-VM | `checks.go:323-331` → `checks_context.go:523-526` | needs BootGuard/PSB visibility |

Row-count check: 33 distinct kinds, matching
`snapd.dart:lib/src/snapd_client.dart:124-158` (which correctly omits
`ErrorKindNone`, `secboot:error_kinds.go:37`). Two kinds are unreachable in this
flow for code reasons, one is never constructed, and one is always downgraded:
`tpm-hierarchies-owned`, `insufficient-tpm-storage`, `missing-argument`,
`addon-drivers-present`. `ErrorKindNone` is not an app-visible kind.

## 11 repair actions

Values: `secboot:actions.go:36-119`; mapping kind → actions:
`secboot:checks_context.go:76-160`; filtering:
`checks_context.go:303-338` (`filterUnavailableActions`), availability probes
`:246-302`; `proceed` insertion `:928-956`, ordering `:349-387`.

| # | Value | Emitted in repair flow | Attached to | Notes |
|---|-------|------------------------|-------------|-------|
| 1 | reboot | yes | `reboot-required` (`:80-82`), `tpm-device-failure` (`:86-89`) | pseudo-action; app runs it itself |
| 2 | shutdown | conditional | `shutdown-required` (`:77-79`) | only if a PPI action reported an S5 transition |
| 3 | reboot-to-fw-settings | yes | 9 kinds, `:83-150` | always available, never probed (`:280-282`) |
| 4 | contact-oem | yes | `:83`, `:86`, `:116`, `:121`, `:129`, `:132`, `:141` | dropped for PCRs 1/3/5 (`:321-338`) |
| 5 | contact-os-vendor | yes | `no-kernel-iommu` only (`:125-128`) | non-VM |
| 6 | enable-tpm-via-firmware | conditional | `tpm-device-disabled` (`:90-94`) | dropped unless `isPPIActionAvailable` (`:252-259`, `:85-125`) |
| 7 | enable-and-clear-tpm-via-firmware | conditional | disabled / owned / lockout (`:90-108`) | same PPI probe |
| 8 | clear-tpm-via-firmware | conditional | owned / lockout / insufficient storage (`:95-115`) | same PPI probe |
| 9 | clear-tpm-simple | **no** | owned / insufficient storage (`:95-115`) | both kinds pre-install only; also dropped when lockout auth unavailable (`:281-283`) |
| 10 | clear-tpm | **no** | same | same |
| 11 | proceed | yes | `errorKindToProceedFlag` + `errorKindWithArgsToProceedFlag` (`:162-176`) | inserted only when every reported kind permits it (`:928-956`) |

Note: actions 9 and 10 can still be *offered* by an installer, just never by the
running-system repair flow, because their kinds cannot occur post-install.

## 6 storage-encryption statuses

Values: `snapd:overlord/fdestate/activate_state.go:69-86`; assembly:
`activate_state.go:155-206`.

| # | Value | Emitted | Site | Condition |
|---|-------|---------|------|-----------|
| 1 | indeterminate | yes | `activate_state.go:73`, assigned `:160`, `:172`, `:180` | no activate state, missing `unlocked.json`, or no model yet |
| 2 | active | yes | `:76`, `:201` | containers activated, no recovery key, no degraded keyslot errors |
| 3 | inactive | yes | `:79`, `:177`, `:189` | classic non-hybrid without unlock state, or zero activated containers |
| 4 | recovery | yes | `:82`, `:194` | at least one container activated with the recovery key |
| 5 | degraded | yes | `:85`, `:199` | `secboot.ActivateStateHasDegradedErrors` (`snapd:secboot/secboot_sb.go:289-316`) |
| 6 | failed | **no — not found** | declared only in `snapd.dart:lib/src/snapd_client.dart:81` | snapd defines five statuses; `FDEStatusFailed` does not exist anywhere in `overlord/fdestate` |

`failed` is a client-side model error, not a snapd value.

## 6 auto-repair-result values

Values: `snapd:overlord/fdestate/autorepair.go:55-62`; exposed at
`activate_state.go:144-152`; the record is per boot
(`autorepair.go:89-122`) and only `AttemptAutoRepairIfNeeded` writes it.

| # | Value | Emitted | Site | Condition |
|---|-------|---------|------|-----------|
| 1 | not-initialized | yes | `autorepair.go:57`, `activate_state.go:149` | no record for this boot |
| 2 | not-attempted | yes | `autorepair.go:127`, `:136`, `:141`, `:168`, `:266-290` | early returns, no repair needed, or reprovision required first |
| 3 | failed-platform-init | yes | `autorepair.go:161-165` | partial reprovision failed |
| 4 | failed-keyslots | yes | `autorepair.go:176-186` | reseal failed |
| 5 | failed-encryption-support | yes | `autorepair.go:147-157` | post-install check returned details or an error |
| 6 | success | yes | `autorepair.go:189`, recorded `:301-308` | reprovision and reseal both succeeded |

All six are emitted by the daemon. Reaching the last four needs
`runPostInstallChecks`, which is gated on a hybrid classic model of 25.10 or
later (`snapd:overlord/install/install.go:592`), set from
`snapd:overlord/devicestate/devicemgr.go:1271`.

## 3 recommendations

Values: `autorepair.go:63-71`; attached at `autorepair.go:265-292`, `:301-304`,
sourced from `snapd:secboot/secboot_sb.go:119-282`.

| # | Value | Emitted | Site | Condition |
|---|-------|---------|------|-----------|
| 1 | permit-manual | yes | `autorepair.go:281-283`; `secboot_sb.go:280` | repair needed, auto-repair impossible, a wrong secret is the only fault |
| 2 | require-reprovision | yes | `autorepair.go:265-269`, `:278-280`, `:301-304` | mismatched primary keys, or any non-success repair result |
| 3 | require-platform-reset | yes | `autorepair.go:284-286`; `secboot_sb.go:131-134` | boot-time lockout reset returned `ErrTPMLockout` |

All three are live code paths in the running-system flow.

## Recipe legitimacy

Mechanism key: **(a)** real disk/firmware/TPM state mutation, **(b)** canned TPM
reply, **(c)** forged snapd- or platform-visible state, **(d)** guest runtime
bind/namespace trick. Evidence is the harness that produced it
(`recipes.sh`, `t-series-coverage.md`, `coverage.md`), not the class name.

| Manifest entry | Class in manifest | Take / evidence | Mechanism | Verdict |
|---|---|---|---|---|
| `auto-repair-result/failed-encryption-support` | recipe-known | T8 domain change, `every-state:evidence/T8-unsupported-platform/state-post.txt:9,11` | (c) hypervisor hidden and DMI patched so the post-install check fails | **not legitimate** as a standalone induction; the manifest itself says the cause of `incompatible-role-params` was not isolated |
| `recommendation/require-platform-reset` | recipe-known | R5, `coverage.md:17,25` (SB-capable OVMF + blank varstore) | (a) real firmware/varstore change | legitimate mechanism; the causal chain to `ErrTPMLockout` is unexplained |
| `kind/system-not-efi` | recipe-known | T1: tmpfs over `/sys/firmware/efi` in snapd's namespace (`recipes.sh:30-34`) | (d) | legitimate as a fault injection; not a firmware state |
| `kind/efi-variable-access` | recipe-known | T2c: `/proc/PID/mem` bound over the SecureBoot variable (`recipes.sh:220-227`); R4 plain OVMF | (a) via R4 real firmware; (d) via T2c | legitimate (R4 carries it); T2c alone would not |
| `kind/tpm-device-disabled` | recipe-known | T40: `tpm2_hierarchycontrol -C o shEnable clear` (`recipes.sh:86-92`) | (a) real TPM state | legitimate; revert fails with 0x9A2, only a cold boot restores it (handoff:50) |
| `kind/no-suitable-pcr-bank` | recipe-known | T51: `tpm2_pcrextend 4:sha256=…` (`recipes.sh:99-103`) | (a) real TPM state | legitimate |
| `kind/measured-boot` | recipe-known | T3: `/dev/null` bound over `binary_bios_measurements` (`recipes.sh:67-72`) | (d) | legitimate only if (d) counts as an induction; the manifest's own preamble is silent on it |
| `kind/invalid-tpm-response` | recipe-known | T37: `/dev/null` bound over `/dev/tpmrm0` | (d), and the empty read is effectively a fabricated response | **weak**; closer to a canned reply than to a device fault |
| `kind/tpm-communication` | recipe-known | T38: `/proc/PID/mem` over the TPM nodes, write fails EIO (`recipes.sh:214-219`) | (d) real kernel error from a bound file | legitimate as a transport fault |
| `kind/unsupported-platform` | recipe-known | T44: hidden hypervisor CPUID + raw DMI patch | (c) forged platform identity | **not legitimate** E2E evidence |
| `kind/sys-prep-applications-present` | recipe-known | T57: custom varstore with `SysPrep0001/0002` + ESP binaries | (a) real firmware configuration | legitimate |
| `kind/weak-secure-boot-algorithms-detected` | recipe-known | T42: RSA-1024 CA enrolled in `db` | (a) real varstore change | legitimate |
| `kind/pre-os-secure-boot-auth-by-enrolled-digests` | recipe-known | T43: Authenticode SHA-256 digest in `db` | (a) | legitimate |
| `kind/action-failed` | recipe-known | T53: `ppi/request` remounted read-only (`recipes.sh:170-178`) | (d) real kernel refusal | legitimate |
| `kind/unexpected-action` | recipe-known | T52: a second check replaces snapd's cached context | (a)/(d) real API sequencing, no forged bytes | legitimate |
| `kind/shutdown-required` | needs-hardware | T16d: `'1: Shutdown'` bound over `ppi/transition_action` (`recipes.sh:179-190`) | (c) forged PPI transition | **not legitimate**; contradicts its own `needs-hardware` class |
| `action/reboot-to-fw-settings` | recipe-known | derived line offered by `tpm-device-disabled` / `no-suitable-pcr-bank` | none — the action list is computed, never observed | legitimate as a derived offer; no independent evidence |
| `action/contact-oem` | recipe-known | same, derived (`:321-338` filter) | none | same |

Also worth recording, outside the `recipe-known` set: `tpm-device-failure`
(T17, canned `TPM_RC_FAILURE`), `tpm-command-failed` (T5d, canned
`TPM_RC_INITIALIZE`) and `no-suitable-tpm2-device` (T5c/T5b, `null-tpm-device`)
were correctly excluded by the manifest; the canned-reply transcripts
(`recipes.sh:191-213`) cannot be evidence. `status/degraded`
(T9a2, forged `unlocked.json`, `recipes.sh:117-142`) and `status/active`
(T9b, same file edited to `platform-key`) are forged snapd state and are
correctly classed `no-known-recipe`/`recipe-candidate`.

**Flagged as not legitimate E2E evidence (canned replies or forged state only):**
`kind/shutdown-required` (T16d), `kind/unsupported-platform` (T44),
`auto-repair-result/failed-encryption-support` (T8 domain change), and
`kind/invalid-tpm-response` (T37) on the weaker reading that a `/dev/null` reply
is a fabricated response. The manifest's classes for these four should be
re-read as "no legitimate recipe yet", not as demonstrated states.

## Contradictions resolved

**1. `shutdown-required` and T16.** The kind is emitted only from
`ppi.StateTransitionShutdownRequired` after a PPI action
(`secboot:checks_context.go:683-693`), i.e. it is a property of the firmware's
PPI transition, not of bare metal. T16d obtained it by writing
`'1: Shutdown'` into a file bound over `/sys/class/tpm/tpm0/ppi/transition_action`
inside snapd's mount namespace (`recipes.sh:179-190`). So the value is *not*
hardware-only — a VM can report it — but no VM reaches it without forging the
PPI transition, and OVMF reports reboot. Conclusion: the `needs-hardware` class
is right about *this fixture* and wrong about *the code*; T16 is not evidence;
the honest class is "requires firmware whose PPI transition for the operation is
S5". `action/shutdown` inherits exactly the same state.

**2. `running-in-vm` "unreachable in a VM".** Wrong. It is the first kind any
VM check returns, because snapd permits a VM only under test
(`snapd:secboot/preinstall_sb.go:82-85` → `snapd:secboot/preinstallCheck` flags
`PermitVirtualMachine`) and `RunChecks` returns `ErrVirtualMachineDetected`
otherwise (`secboot:checks.go:190-197`). The manifest already corrected this at
`kind/running-in-vm`; the earlier claim is dead.

**3. `disable-endorsement-hierarchy` mapped to `tpm-hierarchies-owned`.** Wrong.
The enable check runs before the ownership check and returns `ErrTPMDisabled`
when either `shEnable` or `ehEnable` is clear
(`secboot:check_tpm.go:336-343`), so the recipe yields `tpm-device-disabled`.
Independently, ownership checks are pre-install only (`check_tpm.go:398`), so
the running-system flow can never see `tpm-hierarchies-owned` at all.

**4. `addon-drivers-present` "reported by R5".** The R5 probe read install-time
accepted errors (`snapd:overlord/fdestate/activate_state.go:92-100`), not a live
check. snapd always sets `PermitAddonDrivers`
(`snapd:secboot/preinstall_sb.go:81`), which turns the kind into a warning
(`secboot:checks.go:356-360`), so it can never appear in
`availability-check-errors`. `not-emitted` stands.

**5. `status/failed` reached through `snapd.dart`.** The Dart enum has six
values (`snapd.dart:76-83`); snapd defines five (`activate_state.go:69-86`). No
emission site exists. A defensive client enum, not a state.

**6. The manifest's own evidence bar is inconsistent.** Its preamble rejects
"takes that wrote daemon state or answered with canned TPM replies"
(`tpm-fde-coverage.yaml:6-7`), yet `recipe-known` is granted to pure bind-mount
substitutions — `system-not-efi` (tmpfs), `measured-boot` (`/dev/null`),
`invalid-tpm-response` (`/dev/null`), `tpm-communication`
(`/proc/PID/mem`) — while `tpm-device-failure` and `tpm-command-failed` are
rejected for canned replies. Both fabricate what the daemon sees. The rule that
survives evidence: **(b) and (c) never count; (a) always counts; (d) counts only
when the bound object produces a genuine kernel or device error rather than
content** (EIO, EROFS, missing path), which admits `tpm-communication`,
`action-failed`, `system-not-efi` and excludes `/dev/null`-as-response.

**7. `invalid-secure-boot-mode` unreachable through the app.** Confirmed in code:
`require-platform-reset` is produced when the boot lockout reset returns
`ErrTPMLockout` (`snapd:secboot/secboot_sb.go:131-134`), and the app shows the
repair banner only for `require-reprovision` (`tpm-fde-coverage.yaml:74-76`). The
firmware state that would yield `invalid-secure-boot-mode` therefore never
reaches a repair check. Not a snapd emission question; an app defect.

## Unresolved unknowns

- **secboot commit identity.** The directory name and `go.mod` pin the
  pseudo-version `v0.0.0-20260925074118-4924adcf6262`, whose `-4924adcf6262`
  suffix is the commit. The module cache holds no `.git`, and no network fetch
  was permitted, so the zip's origin hash was not independently verified.
- **Whether the T8 domain change is (c) or a genuine hardware fault.** The
  manifest records that the cause of `incompatible-role-params` on that boot was
  not isolated (`tpm-fde-coverage.yaml:184-187`). Until it is, both the
  `failed-encryption-support` entry and the `unsupported-platform` take rest on a
  change whose effect was not explained.
- **Legitimate route to `tpm-command-failed` / `tpm-device-failure` in a VM.**
  Canned replies are excluded; whether swtpm can be driven into a real failure
  mode or a real command error is unchecked here.
- **PPI operation support on this OVMF build** (operation 1 unimplemented, 5 and
  14 user-driven) is taken from
  `every-state:evidence/T8-unsupported-platform/state-post.txt:37-41`, not
  re-derived from firmware here.
- **App-side mapping** (which kinds the page renders, action ordering, the
  repaired flag) belongs to ticket `11-runner-surface`; this file stops at what
  the daemon emits.

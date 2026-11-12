# TPM-FDE repair coverage

Kinds and actions are taken from secboot `4924adcf6262`
(`efi/preinstall/error_kinds.go`, `errorKindToActions` in `checks_context.go`,
`actions.go`). Which of them snapd `1f728a2` actually emits to a running system
was traced in snapd's source at that commit.

The firmware reasons cite edk2 `OvmfPkg` sources (`Tcg2Pei.c`, `Tcg2Dxe.c`,
`Tcg2ConfigNvData.h`, `Tcg2ConfigPeim.c`, `PeiDxeTpmPlatformHierarchyLib.c`) as
shipped by ovmf `2025.11-3ubuntu7.3`, and libvirt `qemu_tpm.c` for the `<profile>`
handling. The clone's NVRAM was read offline with `NvramStore`; it carries
`TCG2_CONFIGURATION` as a one-byte variable.

## What makes a state reachable in the product's UI

The application shows its repair banner only when snapd reports
`require-reprovision`, which snapd records during the boot-time check. A state
therefore reaches the UI only when it exists when the machine boots.

Faults applied to a *running* clone (`apply_real_fde_fault`) change what the
on-demand check reports but do not set `require-reprovision`; several also
disappear at the next boot. They are listed as uncovered for the UI flow with
that reason rather than written as cases that cannot pass.

The same test applies to firmware state. The clone boots OVMF
`2025.11-3ubuntu7.3`, and a kind is only reachable when that firmware can be
put into the state at boot. The three firmware cases that do work mutate UEFI
NVRAM and the ESP, which the firmware reads before it measures. A state that
only a firmware build option or a firmware-only action can create is out of
reach even though the mutation would be legitimate.

## Covered

| secboot kind | snapd actions | Induction | Test |
| --- | --- | --- | --- |
| `running-in-vm` (only) | `proceed` | always true under QEMU | `tpm-clear-recovery-reprovision.robot`, `tpm-repair-cancel.robot` |
| `weak-secure-boot-algorithms-detected` | none (proceed only) | `prepare: [preos-weak-sb]` enrolls an RSA-1024 CA and dispatches a pre-OS driver signed with it via `Driver####`; shim and grub keep their vendor signatures | `tpm-weak-secure-boot-proceed.robot` |
| `pre-os-secure-boot-auth-by-enrolled-digests` | none (proceed only) | `prepare: [preos-digest-sb]` adds a SHA-256 entry for an injected pre-OS driver and dispatches it with `Driver####`; `db` keeps its CA entries | `tpm-pre-os-digest-proceed.robot` |
| `sys-prep-applications-present` | none (proceed only) | `prepare: [sysprep-app]` enrolls a CA in `db` and dispatches an application signed by it via `SysPrep0001`/`SysPrepOrder` | `tpm-sysprep-application-proceed.robot` |

The cleared-TPM case does not exercise a check kind: with the TPM cleared the
availability check itself is clean, and `require-reprovision` comes from the
failed boot-time unseal. It asserts exactly that, with `running-in-vm` as the
only reported issue.

The pre-OS cases mutate the state the firmware actually verifies at boot:
one authorizes an injected pre-OS driver by an enrolled digest, the other signs
that driver with a weak CA, while the installed chain stays signature-verified
in both. The dialog shows one issue at a time, so the cases answer every proceed
panel in turn (`Answer Repair Prompts`) instead of assuming a single one.

The SysPrep case enrolls a CA and dispatches an application signed by it through
`SysPrep0001` with `SysPrepOrder` set. The firmware launches it before the OS
boot option, secboot sees the matching PCR4 load event, and the case asserts that
real snapd reports `sys-prep-applications-present` with a proceed-only answer.

## Repair interruption

`tpm-repair-power-cut.robot` interrupts a confirmed repair instead of a check
kind. The observer polls the handler's private stage file over the guest
channel and cuts the clone's power the moment the handler replaces it, which
is after the old keyslots are renamed and the new recovery key is added, and
before the replacement TPM key is sealed. The case then proves the rollback
snapd performs on the next boot: the retried change fails with `missing
reprovision context`, the baseline keyslot names are back, the original
recovery key unlocks both devices, and the interrupted attempt's saved key
unlocks neither. A second repair has to complete and keep a working new key.
The case uses `prepare: ["clear-tpm-state"]` and `auth_mode=none`.
It passes in `artifacts/fde-jrq4rij1` (357 s); the post-cut boot wait retries
`snapd-error` and transport timeouts, while trust, authentication and
malformed-response failures still fail at once.

## Additional covered kind

| secboot kind | snapd actions | Induction | Case oracle |
| --- | --- | --- | --- |
| `no-suitable-tpm2-device` | none | `prepare: [no-tpm]` removes the stopped clone's `<tpm>` device after any healthy authentication enrollment (`image_runner.py:278-319`); the source domain keeps its TPM | the boot-time unseal fails with `ErrNoTPM2Device` (`tpm2_device/device_linux.go:66-67`) and records `KeyslotErrorPlatformFailure` (`activate_state.go:107-108`), which makes `require-reprovision` appear (`secboot_sb.go:278-281`, `autorepair.go:274-292`); recovery-key boot, the actual `no-suitable-tpm2-device` issue with no action (`checks_context.go:76-160`), unavailable-repair UI, unchanged repair history and a working original key |

This additional kind is outside ticket 07's thirteen candidates. Its case is
`tpm-missing-device-unavailable.robot`; it passed in `artifacts/fde-74dnlmu2`
(322 s).

## Uncovered, with the reason

| secboot kind | snapd actions | Why it is not a case |
| --- | --- | --- |
| `system-not-efi` | none | `ErrSystemNotEFI` is returned only when efivarfs is unavailable (`check_efi.go:33-37`). The fixture boots the installed system through OVMF and its ESP, and has no BIOS boot path to reach the check without UEFI |
| `efi-variable-access` | `contact-oem` | Needs an efivarfs access error on a firmware variable read (`check_efi.go:33-42`, `efi.go:48-56`). The recovered faults (`efivar-eio`, `mask-sysfs-efi`) are runtime-only, and the firmware recreates the variables it owns |
| `measured-boot` | none | `ReadEventLog` fails only when the TCG2 log is absent (`checks.go:238-241`). OVMF publishes it whenever a TPM2 is detected (`Tcg2Dxe.c:3056-3060`) and its PEI ignores `TCG2_CONFIGURATION` (`Tcg2ConfigPeim.c:4-6,44-96`), so no NVRAM or domain-XML change removes it |
| `tpm-command-failed` | none | Needs a TPM command error response (`checks_context.go:487-496`); no device-level recipe makes swtpm return one |
| `invalid-tpm-response` | none | Needs a malformed response that fails decoding or the response HMAC (`checks_context.go:497-499`); only a canned or `/dev/null` reply produces it |
| `tpm-communication` | none | Needs a transport-layer failure (`checks_context.go:500-502`); every available induction is a running-clone fault that cannot be present at the boot-time check |
| `tpm-device-failure` | `reboot`, `contact-oem` | `ErrTPMFailure` needs the TPM to report failure mode from its partial self-test (`check_tpm.go:285-299`, `checks_context.go:430-431`); swtpm does not |
| `tpm-device-disabled` | `enable-tpm-via-firmware`, `enable-and-clear-tpm-via-firmware`, `reboot-to-fw-settings` | The firmware must clear `shEnable` and `ehEnable` at boot (`check_tpm.go:333-343`). OVMF only disables the platform hierarchy (`PeiDxeTpmPlatformHierarchyLib.c:198-234`), and a user-space disable does not survive the reset |
| `no-suitable-pcr-bank` | `reboot-to-fw-settings`, `contact-oem` | The active bank set is the firmware's (`Tcg2Pei.c:358-443`) and the OS cannot re-allocate it because OVMF randomizes or disables the platform hierarchy. `TCG2_CONFIGURATION` stores only the TPM device selection (`Tcg2ConfigNvData.h`), so no NVRAM value changes the banks |
| `unsupported-platform` | none | The discreteness check cannot be reached; secboot's own classifier records that the host-security check fires first (`checks_context.go:506-513`) |
| `unexpected-action` | none | The app applies only an action the dialog offered (`disk_encryption_providers.dart:1127-1130`) and secboot compares it with the cached context (`checks_context.go:639-664`); only a concurrent state change between check and apply can produce it |
| `action-failed` | none | Produced only by a failing PPI or clear-TPM action (`checks_context.go:670-678`, `:709-715`). No boot-time state offers one: `tpm-device-disabled` is firmware-only and owned hierarchies are pre-install only |
| `internal-error` | none | Needs an unclassified secboot failure; every known trigger fabricates the daemon's view |
| `invalid-argument` | none | The app sends only the kind snapd offered, so the argument path is unreachable |
| `tpm-hierarchies-owned` | five clear/reboot actions | Post-install only; snapd never emits it to the running-system flow |
| `insufficient-tpm-storage` | five clear/reboot actions | Post-install only, same reason |
| `addon-drivers-present` | none (proceed only) | Always a warning in snapd, never an error, so never an issue panel |
| `missing-argument` | none | Declared in snapd, never constructed |
| `shutdown-required` | `shutdown` | Action-phase only (`checks_context.go:685-687`); the one recovered recipe (T16d) forged `ppi/transition_action`, so it is excluded as evidence |
| `reboot-required` | `reboot` | Needs a PPI-driven transition; reachable only after a repair attempt, not as a fresh state |
| `tpm-device-lockout-locked-out` | `clear-tpm-via-firmware`, `enable-and-clear-tpm-via-firmware`, `reboot-to-fw-settings` | `dictionary-lockout` is runtime only |
| `tpm-pcr-unusable` | `contact-oem` | `extend-pcr4` is runtime only |
| `insufficient-dma-protection` | `reboot-to-fw-settings`, `contact-oem` | Needs firmware DMA configuration the VM does not expose |
| `no-kernel-iommu` | `reboot-to-fw-settings`, `contact-os-vendor` | Needs a kernel built without IOMMU support |
| `host-security` | `contact-oem` | Needs a broken root of trust; not inducible under QEMU |
| `absolute-present` | `reboot-to-fw-settings`, `contact-oem` | Needs a firmware Absolute agent, which QEMU does not provide |
| `invalid-secure-boot-mode` | `reboot-to-fw-settings` | `prepare: [plain-ovmf]` induces it, but no repair is possible, so it needs a guidance-only flow of its own |
| `no-hardware-root-of-trust` | none | Firmware property; not presentable under QEMU |


## Product actions not exercised

`reboot-to-fw-settings`, `contact-oem`, and `contact-os-vendor` are guidance the
application only displays; no covered state produces them in a drivable flow.
`reboot` is exercised only as the post-repair restart, not as a `reboot-required`
issue. `shutdown` has no case.

## Running one case

The fixture source is the stopped, frozen session domain `ugt-fde-checkpoint`.
Its XML names the disk and NVRAM it boots (`tpm-fde-test2-before-e2e/` holding
`tpm-fde-sboff-base.qcow2` and `tpm-fde-sbenroll_VARS.fd`), and its swtpm state
lives under `~/.config/libvirt/qemu/swtpm/`. The runner's preflight checks the
installed binaries and encrypted devices on that domain before it clones. A
golden export exists under `~/.local/share/ugt-fde/golden/`, but the XML does
not establish that the checkpoint boots its files; any equivalence is a content
comparison, not a property of the fixture.

```bash
cd /path/to/ubuntu-gui-testing
export PATH=$PWD/.venv-yarf/bin:$PATH
export PYTHONPATH=$PWD/runner
runner/.venv/bin/python -m ubuntu_gui_testing_runner \
  --suite tests/desktop-security-center/ \
  --test desktop-security-center-reprovision.tpm-clear-recovery-reprovision \
  --robot-test "TPM clear recovery reprovision" \
  --source-domain ugt-fde-checkpoint \
  --connection-uri qemu:///session \
  --swtpm-state-dir "$HOME/.config/libvirt/qemu/swtpm" \
  --pool-name ugt-fde-canonical \
  --pool-dir "$HOME/.local/share/ugt-fde/pool-canonical" \
  --fde-config "$HOME/.local/share/ugt-fde/fixture/fde-tpm-clear.json"
```

- `--suite` is the directory handed to `yarf --platform=Vnc <suite>`
  (`base.py:330`). It must be `tests/desktop-security-center/`, the tree that
  holds the resources the cases import: Robot cannot parse a resource from
  above the directory it is given, and Yarf stages only what is inside it.
- `--test` is passed to Robot `--suite` (`base.py:339`) and is the dotted path
  of the `.robot` suite **relative to `--suite`**:
  `desktop-security-center-reprovision.<case file stem>`. Yarf prepends the
  given directory's own suite name (`yarf/main.py:377`), so the value must not
  repeat it. `repo README.md:159-162` shows the same shape for a nested suite.
- `--robot-test` is the case name handed to Robot `--test`.
- The pool is looked up by name, so `--pool-name` and `--pool-dir` must agree.
- `--fde-config` requires `--robot-test`; the runner raises otherwise
  (`image_runner.py:61-64`).
- The fixture file must not be group- or world-readable: it names the fixture
  credentials, and the runner refuses one that is (`fde.py:_require_private_file`).
- The runner copies `swtpm-state-dir/<source uuid>` per clone, so the source
  domain's swtpm state must exist under that path.
- Each case needs its own `--robot-test`; one case per disposable clone.
- Video is written to `artifacts/video.webm` when the FDE path runs with
  `--log-video`.

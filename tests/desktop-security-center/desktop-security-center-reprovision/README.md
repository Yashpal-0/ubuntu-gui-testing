# TPM-FDE reprovisioning suite

Drives the installed Security Center through snapd's real TPM-FDE repair flow in
one throwaway clone per case. snapd, polkit and the application are the real
ones; only the clone's disk, TPM and firmware state are mutated before it boots.

## What a case proves

Each repair-completing case asserts that snapd recorded a new `fde-reprovision` change
that reached `Done`; the page reports working hardware-backed encryption with no
reprovision recommendation; the clone restarts and unlocks without the recovery key; the
new key unlocks both devices and the old key is rejected; the authentication
mode is the one the case chose; the repair banner is gone.

The cancellation and unavailable-hardware cases instead check unchanged boot
identity, authentication, and repair history, with the original recovery key
still unlocking both encrypted devices.

The power-cut case asserts the interruption itself: the host cuts power as soon
as snapd's handler replaces its private stage file, so the attempt has already
renamed the old keyslots and added the new recovery key but never sealed the
replacement TPM key. On the next boot snapd retries that task, restores the old
keyslots, and fails the change with `missing reprovision context`. The case
requires exactly one new change, spawned before the cut and finished after the
new boot, the baseline keyslot names back in place, the original recovery key
unlocking both devices, the interrupted attempt's saved key unlocking nothing,
and a second repair then completing with a working new key.

A green Robot log is the only proof. A screenshot of a dialog is not.

## Prerequisites

- A stopped, consistent TPM-FDE source domain (`ugt-fde-checkpoint`) with its
  disk, NVRAM and TPM state preserved together. Inspect its XML for the actual
  source paths; the existence of a separate golden export does not prove they
  are identical. Fixture preflight independently checks the installed binaries
  and encrypted devices.
- A private fixture JSON per state, mode 0600, under
  `~/.local/share/ugt-fde/fixture/`. The fixture names secret files; the runner
  refuses one that is group- or world-readable.
- The storage pool `ugt-fde-canonical` at
  `~/.local/share/ugt-fde/pool-canonical`, large enough for one clone.

## Run one case

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

`--test` is the dotted path of the `.robot` file below `--suite`; Yarf prepends
the directory's own suite name, so never repeat it. `--fde-config` requires
`--robot-test`.

Run the whole set by repeating the command with each case's `--test`,
`--robot-test` and fixture; one clone per case, never two cases in one clone.
There is no single-invocation whole-suite run: `--fde-config` requires
`--robot-test`, and the fixture selects the clone mutation, so each case needs
its own command.

## Fixtures

`prepare` selects the clone mutation and is validated against a fixed set:

| state | `prepare` |
|---|---|
| cleared TPM, `running-in-vm` only | `["clear-tpm-state"]` |
| missing TPM, no available repair action | `["no-tpm"]` |
| Secure Boot off on SB-capable firmware | `["plain-ovmf"]` |
| `sys-prep-applications-present` | `["sysprep-app"]` |
| `weak-secure-boot-algorithms-detected` | `["preos-weak-sb"]` |
| `pre-os-secure-boot-auth-by-enrolled-digests` | `["preos-digest-sb"]` |

Keep `snapd_version`, `snapd_executable_sha256`, `data_device`, `save_device`
and `security_center_revision` unchanged when deriving a fixture; preflight
asserts them against the clone.

`tpm-missing-device-unavailable` removes only the stopped clone's TPM device,
after any healthy enrollment boot. The source domain and TPM state remain
unchanged. As in the firmware cases, snapd's own VM-testing switch permits the
virtual machine; the TPM check still observes the actual missing hardware.
The case checks snapd's empty action list, the unavailable-repair dialog, no
unsafe proceed/repair action, unchanged repair history and usable credentials.

### Authentication cases

| dotted suffix after `desktop-security-center-reprovision.` | fixture authentication | sequence |
|---|---|---|
| `tpm-clear-recovery-reprovision` | `auth_mode=none` | repair, then boot without a credential |
| `tpm-existing-pin-reprovision` | `auth_mode=pin`, `pin_file` | enroll the PIN before clearing the TPM; repair removes it |
| `tpm-existing-passphrase-reprovision` | `auth_mode=passphrase`, `passphrase_file` | enroll the passphrase before clearing the TPM; repair removes it |
| `tpm-pin-after-repair-reboot` | `auth_mode=none`, `pin_file` | repair and boot, add the PIN through the UI, then boot with it |
| `tpm-passphrase-before-repair-reboot` | `auth_mode=none`, `passphrase_file` | repair, add the passphrase through the UI, then use it for the first reboot |
| `tpm-repair-power-cut` | `auth_mode=none` | interrupt a confirmed repair with a host power cut, prove the rollback, then repair again |

The two pre-enrolled cases use `prepare: ["enroll-auth", "clear-tpm-state"]`.
The runner boots the healthy clone, enrolls the selected authentication through
real snapd, verifies it, shuts down, and only then applies the fault. The other
four cases use `prepare: ["clear-tpm-state"]`. Every secret file is mode 0600.
The post-repair cases type only their chosen PIN or passphrase at the boot prompt,
never the recovery key, and independently verify the resulting authentication mode.

The power-cut case drives libvirt only for the clone the runner created: the
observer reads the handler's stage file over the guest channel, refuses any
domain that is not that clone, and the restart requires the clone to return on
the vsock CID and VNC port Yarf already uses. It never edits snapd state, the
TPM, or the source domain.

## Secrets

- Fixture secrets live in files named by the fixture JSON, mode 0600, outside
  the repository.
- Robot logs every keyword argument and every OCR text it reads, so each window
  where a recovery key is on screen uses a quiet block from `Start Repair`
  until the key panel is gone. Quiet blocks suppress messages, not keyword
  arguments or failure status. Text lookups use `Match Text Without Echo`, and
  `Type Fixture Secret` reads credentials internally, never as Robot arguments.
  `Close All` restores the caller's log level if a case fails inside the block.
- `artifacts/` is ignored by git. It still holds OCR text and the run video, so
  treat it as private and do not upload it.
- The saved recovery key file is written inside the clone, not on the host.

The older check-key and replace-recovery-key suites still pass keys as Robot
arguments and can expose them in their logs. They are not part of this
reprovision suite, and this work does not claim to redact their artifacts.

## Reading a run

`artifacts/fde-<id>/` holds `output.xml`, `log.html` and `video.webm`. FDE runs
use a private umask; the verified run's files are mode 0600. Check the summary
line `1 test, 1 passed, 0 failed`, then the case's own
assertions in `log.html`.

The video encodes logged screenshots at 5 frames per second, not wall-clock
time. A five-minute key-expiry wait need not add any video frames. Use the Robot
timestamps to verify that wait; video duration does not prove elapsed time.

## Troubleshooting

- `Source domain 'ugt-fde-checkpoint' not found`: the checkpoint lives in
  `qemu:///session`; an inherited `XDG_CONFIG_HOME` points libvirt at the wrong
  configuration directory. Unset it and retry.
- QEMU fails to open a volume with EACCES: `--pool-name` and `--pool-dir` must
  agree, because the pool is looked up by name.
- Inspect leftover domains before cleanup; never remove an unrelated domain or
  the checkpoint. The runner owns the disposable clone it creates.

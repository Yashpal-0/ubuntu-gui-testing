---
id: "09-failure-cases"
title: "Three reprovision failure cases"
type: task
label: "wayfinder:task"
state: closed
parent: map
assignee: null
depends_on: ["01-runner-fde-seam", "02-golden-checkpoint-export", "04-gdm-login", "08-happy-path-cases"]
---

# Three reprovision failure cases

## Question

Implement 3 cases, with the exact interruption point and oracle for each:

1. **Cancel** before the change starts: assert no change, unchanged status and recommendation, key not consumed.
2. **Power cut** after the change starts and before completion: boot, inspect state, retry, verify.
3. **Key expiry**: generate, wait past 5 minutes, confirm, assert the documented "recovery key has expired" failure, regenerate, retry, verify.

## Notes

No fault injection. The power cut is host-side, not a guest action.

## Status

Case 1 is implemented (`tpm-repair-cancel.robot`): it declines the dialog and
asserts the boot id, authentication mode and repair history are unchanged, with
no `fde-reprovision` change in flight.

Case 2 started with a clone-identity-guarded asynchronous observer and no
verified end-to-end case. Review found that queued `Do` changes were incorrectly
treated as started, and snapd holds its state lock during reprovisioning, so
API polling cannot prove an in-handler power cut. A passive observer and an
independent completion-timing oracle are being implemented. Missing code is
not an external blocker, and unit tests do not establish real interruption.

The observer's arm step failed in every run with `virsh domuuid failed: error:
failed to get domain '<clone uuid>'>`. `virsh domuuid` documents a domain *name
or id* argument and cannot resolve the UUID the runner created (reproduced on
a live clone: `domuuid` fails, `domstate`/`dumpxml`/`dominfo` succeed). The
identity is now read from the fetched `dumpxml` definition, with the source
UUID still refused before any libvirt call and the observed vsock CID kept as
the second check. Unit tests cover the refusal paths; the real-VM proof is
pending a replay on the corrected runner.

The next run armed the cut on a real clone and destroyed it, then stopped at
`Wait For Power Cut To Stop The Guest` with `guest operation 'connect' failed:
guest vsock is unreachable` (`artifacts/fde-wuzp3ju_`). The cut itself had
happened; the probe could not see it. A destroyed clone keeps no vsock listener,
so the guest channel raises `FdeGuestTimeout` from its connect step, but the
keyword probed through `_request`, which turns every guest error into an
`AssertionError` before the wait sees it. The cut wait now reads the channel
directly and counts only `FdeGuestTimeout` as proof, so a helper that fails
still fails the case; the post-cut boot wait had the same dead timeout arm and
now shares the direct probe. `fde_power` is unchanged.

That replay (`artifacts/fde-6348xo9_`) proved the trigger and the probe: the
observer armed, `Confirm Repair` ran, `Cut Power When Repair Starts` cut the
clone 3.4 s in, and `Wait For Power Cut To Stop The Guest` returned in 0.0 s on
the typed timeout. It then failed in `Wait For Guest After Power Cut` after the
600 s boot budget: the case waited for the guest channel before answering the
initramfs prompt, but an interrupted attempt has already re-keyed the disk, so
the restarted clone stops at `Enter recovery key for unknown (ubuntu-data)` and
no SSH exists until that prompt is answered. The case then unlocked the clone
before it waited for the channel; the rollback oracle was still unproven.

The unlock-first replay (`artifacts/fde-_2des04r`) cut the clone 5 min 41 s in
and proved the guest channel dead, then failed after 897 s: the restarted clone
never reached the initramfs prompt. Booting the preserved disk, NVRAM and TPM
state outside the suite reproduces an early-boot reboot loop: `[  102.48015]
reboot: Restarting system` runs on the kernel restart path. No `Kernel panic -
not syncing` precedes it at emergency level, and the kernel reboots after a
panic only when a positive `panic=` timeout is set. The run kernel's own cmdline,
loaded from `ubuntu-boot:/EFI/ubuntu/grubenv`, carries `panic=-1`, so a panic did
not restart it. The reboot comes from the run kernel's own initramfs, taken from the
`pc-kernel_3755` UKI on `ubuntu-boot`: `emergency-reboot.service` starts
`After=emergency.target`, sleeps 10 s and sets `SuccessAction=reboot`, while
`emergency.service` opens a shell only when `dangerous` is on the cmdline,
which it is not — so a failed unlock lands in emergency and reboots 10 s later.
The 102 s fits systemd-ask-password's 90-second default timeout plus that
10-second sleep, which makes an unanswered unlock query likely; why no prompt
was displayed is still unknown. OVMF then starts the same boot entry
again. The display showed four distinct frames in 126 s, all firmware, and the
serial console showed nothing before the restart line. The loop also happens
with the TPM device removed,
so the preserved TPM state does not drive it. Both LUKS2 headers parse cleanly
with their keyslots and `ubuntu-fde`/`ubuntu-fde-recovery` tokens present and no
reencryption section. Port 22 never accepted a connection across 420 s of
sampling, which is expected until the disk is unlocked and says nothing about
userspace either way. Run mode is configured by `ubuntu-boot:/EFI/ubuntu/grub.cfg`
(`Snapd-Boot-Config-Edition: 3`), and that partition's `grubenv` exists and sets
`snapd_full_cmdline_args=console=ttyS0,115200n8 console=tty1 panic=-1 quiet
splash snapd.xkb="us,pc105,,"`; its `kernel.efi` symlink points at
`pc-kernel_3755.snap`, not the `pc-kernel_3672` snap the seed carries. The case
stopped there because that boot never reached the prompt.

The next unlock-first replay, `artifacts/fde-2olmq2wa`, got past the prompt:
after the cut, `Unlock Encrypted Boot` answered the recovery-key prompt in 47 s
and the clone reached the desktop. The case then failed in `Wait For Guest After
Power Cut` after 6 s because its first `GET /v2/system-volumes` got:
`cannot convert volume structure: cannot read key data for "bootstrap-key" from
"/dev/disk/by-uuid/8b925760-b511-4967-b2dd-3d19b4407eaa": named keyslot does not
contain key data yet`. That UUID is the `ubuntu-save` device. Six seconds after
unlock is early enough that the on-boot retry could still be mid-flight, so this
records a probe result, not a permanently empty keyslot; polling the endpoint on
a preserved clone to a terminal change state is the next check. The silent
reboot loop and this error are likely two outcomes of the same post-cut state.

That check settles it: a clone kept after the cut (`--keep`), unlocked with the
fixture recovery key, answers `snapshot` in 0.2 s once userspace is up, and
reports change 50, `fde-reprovision`, `Error`, `missing reprovision context`,
spawned 16:35:15 and ready 16:36:04, with `default`, `default-fallback` and
`default-recovery` back on both `system-data` and `system-save`. So snapd does
roll the interrupted attempt back and fail the change exactly as the oracle
expects; the six-second failure was the probe reading snapd's own in-flight
`snapd-error` while its retry converted the keyslots. `wait_for_guest_after_power_cut`
now retries `snapd-error` and transport timeouts but still fails at once on
trust, authentication and malformed-response failures, and
`_settled_interrupted_change` (which already documents this window) can now
reach its wait. The silent reboot loop is the other outcome of the same
interrupted state, where the prompt times out instead of being answered.

The case now passes: `artifacts/fde-jrq4rij1`, 357 s, `1 test, 1 passed, 0
failed`. It cut the clone 0.3 s after the handler replaced the stage file,
unlocked the restarted clone with the fixture recovery key in 56.8 s, tolerated
7.7 s of the retry window, asserted exactly one new `fde-reprovision` change
spawned before the cut and finished in `Error` with `missing reprovision
context`, the baseline keyslots back on both devices, the fixture recovery key
unlocking both, and the interrupted attempt's saved key unlocking neither. It
then re-ran the repair to `Done`, rebooted, unlocked without a key, and found
the repair no longer recommended with unchanged recovery credentials.

Case 3 passes (`tpm-recovery-key-expiry.robot`, `artifacts/fde-m2u9u88d`), including a real 310-second
wait, exact backend expiry assertion, rejection of the expired key on both
encrypted devices, regeneration, retry, and the full successful repair oracle.
The first run stopped at firmware boot; the next reached the actual error page
but exposed an incorrect dialog expectation in the test. The corrected replay
completed in 806 seconds with `1 test, 1 passed, 0 failed`; its reports have zero
recovery-key-pattern matches and its video is private (0600).

Output lands in `tests/desktop-security-center/desktop-security-center-reprovision/`, registered in `tests/desktop-security-center/plans/tpm-fde.yaml`.

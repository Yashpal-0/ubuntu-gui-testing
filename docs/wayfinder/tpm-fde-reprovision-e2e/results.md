# Results

One disposable clone per case, real snapd, real polkit, the installed Security
Center. A row is only `pass` when that run's `output.xml` reports
`pass="1" fail="0"`; the run directory is cited so the claim can be checked.

## All 21 requested scenarios

The ten state blockers are source-cited individually in
[ticket 07](tickets/07-state-cases.md#status). They are not mocked passes.

Every row carries either a pass with the run directory that proves it or a cited
blocker: eleven passes and ten source-cited state blockers. The power-cut case
is one of the passes ([ticket 09](tickets/09-failure-cases.md#status)). Nothing
in this table is a mock or a skipped run.

| group | case or state | preparation or missing capability | result / evidence |
|---|---|---|---|
| auth | no authentication | `clear-tpm-state` | pass: `artifacts/fde-fnircwvi` (479 s) |
| auth | PIN enrolled before fault | `enroll-auth`, `clear-tpm-state` | pass: `artifacts/fde-ilf71dfu` (320 s) |
| auth | passphrase enrolled before fault | `enroll-auth`, `clear-tpm-state` | pass: `artifacts/fde-2sj8zuoj` (267 s) |
| auth | PIN added after repair and reboot | `clear-tpm-state` | pass: `artifacts/fde-abpqgvdm` (636 s) |
| auth | passphrase added after repair, before reboot | `clear-tpm-state` | pass: `artifacts/fde-e2vs086r` (341 s, zero recovery-key pattern matches) |
| state | `system-not-efi` | installed disk has no legacy boot path; `check_efi.go:33-37` | blocked |
| state | `efi-variable-access` | available faults are runtime-only; firmware restores variables; `efi.go:48-56` | blocked |
| state | `measured-boot` | OVMF always supplies the TPM event log; `Tcg2Dxe.c:3056-3060` | blocked |
| state | `invalid-tpm-response` | malformed/HMAC-invalid replies would be fabricated; `checks_context.go:497-499` | blocked |
| state | `tpm-communication` | no boot-time transport-failure recipe; `checks_context.go:500-502` | blocked |
| state | `tpm-device-disabled` | firmware must disable both hierarchies at boot; OVMF does not; `check_tpm.go:333-343` | blocked |
| state | `no-suitable-pcr-bank` | bank selection is firmware-owned and has no fixture knob; `Tcg2Pei.c:358-443` | blocked |
| state | `unsupported-platform` | earlier host-security gate makes classifier unreachable; `checks_context.go:506-513` | blocked |
| state | `sys-prep-applications-present` | `sysprep-app` | pass: `artifacts/fde-eulq8mx4` (515 s, zero recovery-key pattern matches) |
| state | `weak-secure-boot-algorithms-detected` | `preos-weak-sb` | pass: `artifacts/fde-jmt6ti2b` (473 s, zero recovery-key pattern matches) |
| state | `pre-os-secure-boot-auth-by-enrolled-digests` | `preos-digest-sb` | pass: `artifacts/fde-kb6g12cr` (549 s, zero recovery-key pattern matches) |
| state | `unexpected-action` | app sends only offered actions; needs a concurrent state race; `checks_context.go:639-664` | blocked |
| state | `action-failed` | no reachable boot state offers the required PPI action; `checks_context.go:670-678,709-715` | blocked |
| failure | cancel before repair | `clear-tpm-state` | pass: `artifacts/fde-0gi5xi2l` (299 s with the credential assertion, zero recovery-key pattern matches) |
| failure | power loss during reprovision | passive stage observer and post-boot timing oracle | pass: `artifacts/fde-jrq4rij1` (357 s). History: the cut proof passes (`fde-6348xo9_`), and unlock now runs first, but the `fde-_2des04r` boot never reached the initramfs prompt. `fde-_2des04r` failed after 897 s. Booting the preserved disk, NVRAM and TPM state outside the suite shows an early-boot reboot loop: `[  102.48015] reboot: Restarting system` runs on the kernel restart path with no `Kernel panic - not syncing` before it, so a panic did not restart it and a guest-side process did; OVMF then runs the same entry again. The loop persists with the TPM device removed; both LUKS2 headers parse cleanly with their keyslots and tokens and no reencryption section; display frames show firmware only and no prompt appears, and 420 s of dense vsock sampling never saw port 22 accept (expected pre-unlock). The reboot is the run kernel's own initramfs `emergency-reboot.service` (`After=emergency.target`, 10 s sleep, `SuccessAction=reboot`) from the `pc-kernel_3755` UKI, and `emergency.service` opens a shell only under `dangerous`; 102 s fits a 90 s ask-password timeout plus that sleep, so the query likely went unanswered, but why no prompt appeared is unproven. Run mode is configured by `ubuntu-boot:/EFI/ubuntu/grub.cfg` (edition 3) whose `grubenv` sets the cmdline. A later replay (`fde-2olmq2wa`) answered the prompt in 47 s and reached the desktop, then failed in `Wait For Guest After Power Cut` because its first probe 6 s after unlock got `cannot convert volume structure: cannot read key data for "bootstrap-key" from "/dev/disk/by-uuid/8b925760-…" (ubuntu-save): named keyslot does not contain key data yet`; a kept clone then cleared it: once the retry finished, `snapshot` answered in 0.2 s with change 50 in `Error` (`missing reprovision context`) and the baseline keyslots restored, so the boot wait now retries only `snapd-error` and transport timeouts. The passing run cut 0.3 s after the stage file was replaced, unlocked in 56.8 s, tolerated 7.7 s of the retry window, proved the rollback, then completed a second repair to `Done` whose reboot unlocked without a key. |
| failure | generated recovery key expires | `clear-tpm-state`, real 310-second wait | pass: `artifacts/fde-m2u9u88d` (806 s) |

The additional `no-suitable-tpm2-device` case uses `prepare: [no-tpm]` to test
the no-action unavailable-repair state. It passed in `artifacts/fde-74dnlmu2`
(322 s); it does not replace any of the 21 rows above.

`fde-remiht_2` passed, but its `output.xml` still held five copies of the new
recovery key: `Ignore Virtual Machine Warning` kept probing with `Match Text`
after the key screen appeared, and a probe's timeout quotes the whole screen.
The first clean rerun, `fde-rrjxomh8`, passed after the probe fix. A subsequent
run, `fde-fnircwvi`, passed after safe pointer/button lookups, earlier quiet
blocks, and failure-safe log restoration were added. Both runs' `output.xml`,
`log.html`, and `report.html` contain zero matches of the recovery-key pattern
`[0-9]{5}(?:-[0-9]{5}){7}`. The latest run directory is mode 0700; those files
and its 177549-byte `video.webm` are mode 0600. The video can still show the
key; this is not approval to upload the artifacts.

The three older firmware-case runs were functional passes, not clean-log
evidence: each `output.xml` contained 14 recovery-key-pattern matches. Their
directories are private (0700), but the recordings and logs must not be
published. The replays `fde-kb6g12cr` (pre-OS digest), `fde-eulq8mx4`
(sysprep), and `fde-jmt6ti2b` (weak secure boot) are clean.

The successful expiry run `fde-m2u9u88d` proves the exact
`recovery key has expired` backend failure, rejection of the expired key on
both devices while the original key still works, regeneration and successful
repair, credential-free reboot, and the full final credential oracle. Its
XML/HTML reports contain zero recovery-key-pattern matches; the directory is
0700 and all reports and video are 0600. The 253402-byte video is 640×480 at
5 frames/s for 94.4 seconds; its final frame shows the healthy encryption page.
The real five-minute wait is established by the Robot timestamps, not video
length.

## Failed or pending verification

The first key-expiry run, `artifacts/fde-abjh09kk`, failed after 715 seconds in
suite setup: no recovery-key boot prompt appeared. Its recording stayed at
the TianoCore boot screen, before any repair operation. It does not exercise
the expiry or retry oracle. The diagnostic replay, `artifacts/fde-a8pt20rh`,
booted Linux and waited 310 seconds after generating the key. It failed because
the test expected an error dialog; the app instead returned to the page with
`Something went wrong` and `Start repair...`. The test now follows that actual
retry surface and retains the exact backend-expiry and credential assertions.
The corrected replay `fde-m2u9u88d` passed; no firmware fix is claimed.

The first existing-PIN run, `artifacts/fde-vkks1tdg`, enrolled the PIN through
real snapd, shut down, cleared the cloned TPM, and reached the desktop through
recovery-key boot. Preflight confirmed `auth_mode=pin`. It stopped at an
incorrect expected auto-repair result: snapd reported
`failed-encryption-support`, not `not-attempted`. Cases with authentication
enrolled before the fault now expect that exact post-install-check failure;
cases that only clear the TPM expect `not-attempted`; their repair/reboot
oracles were unchanged. The corrected PIN run, `artifacts/fde-ilf71dfu`, passed all
repair, reboot and credential assertions in 257 seconds. Its XML/HTML reports
contain zero recovery-key-pattern or plaintext PIN matches and remain 0600.
The 640×480, 5 frames/s video is 51.8 seconds and private. The pinned
`fdestate/autorepair.go:147-157` returns this result when the post-install check
rejects encryption support.

The passphrase-before-repair case has three failed attempts, all before any
repair, and none is claimed as a pass:

- `artifacts/fde-jm0pqfjl`: the Add dialog did not submit. OCR cannot read the
  45×21 white-on-green `Add` label, and Tab focus after the confirm field is not
  reliable. The test now clicks the button's pixels from a cropped template.
- `artifacts/fde-na0qbox2`: the template match never ran because one VNC
  screenshot stalled for its whole 10-second window. The match now retries three
  times. The artifact contains zero recovery-key-pattern matches.
- `artifacts/fde-os6wk8x3`: suite setup timed out at the firmware screen. A
  concurrent `cargo build` on the host drove the load average above 50 and the
  guest needed more than the 18×10 s boot budget. The artifact is incomplete and
  claims nothing; the rerun is queued behind a load gate.

`plain-ovmf` (Secure Boot guidance), the passphrase-before-repair case, the
power-cut case, and the clean replays of the three firmware cases and the
cancel case are not claimed as passing. Enum gaps are in
`tpm-fde-coverage.yaml`; auth and failure scenario work remains in tickets 08
and 09.

## What a pass proves

For each completed repair: snapd recorded a new
`fde-reprovision` change that reached `Done`; the clone restarted and unlocked
without the recovery key; the new key unlocked the data and save devices while
the old key was rejected; the authentication mode matched; the repair banner
was gone. The cancellation case instead checks that boot identity,
authentication, and repair history did not change and repair is still needed.

---
type: map
label: wayfinder:map
state: closed
---

# TPM-FDE reprovisioning end-to-end suite (local)

## Destination

A local, on-demand Robot/YARF suite in the ubuntu-gui-testing working tree that drives the installed Security Center through the real reprovision flow in throwaway clones of `tpm-fde-test2`, covering 21 cases — 5 auth-mode happy paths, 13 known-recipe state cases, 3 failure cases — each asserting the full post-boot oracle, with a regenerated coverage manifest giving every storage-encryption enum entry a verdict, and a runbook. The bundle lives in this repo under `docs/wayfinder/tpm-fde-reprovision-e2e/`; the user raises the PR, and the agent does not commit, push, or open it.

## Notes

**Pins.** snapd `2.78+g237.1f728a2` (commit `1f728a2361`, descendant of the polkit-repair commit `8265918c`); secboot `4924adcf6262`; app `d2d204dd`; snapd.dart `0.7.8`.

**Standing decisions.**
- Golden source is `tpm-fde-test2` only; each case clones it into a throwaway private pool and never mutates the source. One disposable clone per case.
- Host script mutates disk, swtpm state, UEFI NVRAM and domain XML; privileged guest commands only for runtime actions and oracles. No canned TPM replies, no forged daemon state (see the legitimacy ticket), no root proxy, real polkit, desktop user.
- Full oracle per case: change `Done`; post-repair `status=active` with no recommendations; next cold boot unlocks without the recovery key (or with the chosen auth); new key accepted; old key rejected; auth mode correct; banner gone.
- On-demand runs. Branch `test/tpm-fde-reprovision-e2e`; the user commits and raises the PR; the agent does not commit, push, or open it.
- All planning artifacts live under `docs/wayfinder/tpm-fde-reprovision-e2e/` in the repo, never `.scratch/`. The exported disk/TPM fixture stays private under `~/.local/share/ugt-fde/`.
- Implementation changes go to their normal tracked paths (`runner/`, `tests/desktop-security-center/`).
- The runner is extended (local patch); the app and snapd are not changed; the VM's snapd is not upgraded.

**Host-state legitimacy rule (Ticket 06).**
Only mutations at actual physical/virtual device boundaries (disk, partition tables, LUKS headers/keyslots, ext4 filesystem, UEFI NVRAM, swtpm state, TPM PPI sysfs) count as legitimate E2E evidence. Editing snapd's private `/var/lib/snapd/state.json` or mocking daemon state is prohibited — snapd must produce all internal state, change records, and D-Bus emissions on its own from genuine device facts.
- `shutdown-required` (T16d): accepted in Ticket 06, superseded by Ticket 07 (action-phase, and the recipe forged `ppi/transition_action`).
- Accepted: `invalid-tpm-response` (T37) only if induced at device/socket level, otherwise excluded.
- Excluded recipes: `unsupported-platform` (T44) and the forged `state.json` route to `auto-repair-result=failed-encryption-support` (T8). The latter result was subsequently observed without forgery in the three passing Secure Boot issue cases; see `results.md` and the manifest.

**Skills to consult.** `ubuntu-gui-testing-tpm-fde-reprovision`, `security-center-gui-testing-tpm-fixtures`, `record-snapd-fde-check-kinds-vm`, `induce-secboot-recovery-issues-in-vm`, `virsh-vm-gui-automation`, `yarf-run-video-recording`.

**Prior work (reference only, never evidence).** Recovered WIP: `/tmp/tmp42m1jbm5/`; runner helper: `/tmp/fde.py.fixed`; manual T1–T18 recipes: `/tmp/handoff-tpm-fde-t-series-2026-11-10.md`; scope record: `.udeng-11670/` (git-excluded).

**Risk.** The bundle now sits in tracked paths, but nothing is committed yet; the previous 507-line WIP was lost from an uncommitted tree, so the exposure remains until the user commits.

**Housekeeping.** No clone domains are left running: `virsh list --all` shows only the stopped `ugt-fde-baseline` and `ugt-fde-checkpoint`, and the previously leaked clone domain and its processes are gone.

## Decisions so far

<!-- one line per closed ticket: - [<title>](tickets/NN-slug.md): gist -->

- [snapd emission paths and recipe legitimacy](tickets/12-snapd-emission-paths.md): 4 unreachable check kinds; `shutdown-required` is PPI action-phase; `status/failed` client-side only; 4 legitimacy flags; 2 manifest mappings corrected.
- [YARF and runner extension surface](tickets/13-yarf-runner-surface.md): `--swtpm-state-dir` parsed and dropped; runner forwards suite only; mid-case power needs `DOMAIN_UUID`; 15 leak risks cataloged; seam targets `image_runner.py` and `cli.py`.
- [Runner FDE seam](tickets/01-runner-fde-seam.md): `--fde-config` and `--robot-test` wired; stopped-clone `_prepare_tpm_state` implemented; 5 YARF variables passed; 206 unit tests passing.
- [Legitimacy rule for host-created states](tickets/06-host-state-legitimacy.md): Forged daemon state (`state.json`) prohibited; device boundary mutations only; T44 and T8 excluded; T16d accepted there, later superseded by Ticket 07; T37 accepted only at TPM device boundary.
- [Golden checkpoint export wizard](tickets/02-golden-checkpoint-export.md): One-time sudo export copied 9.9 GiB disk, NVRAM, swtpm, XML to `~/.local/share/ugt-fde/` mode 0700; source remained shut off.
- [Fixture preflight and desktop access proof](tickets/03-fixture-preflight.md): All 7 assertions verified against live clone; snapd revision x2, hash matched; real polkit dialog popped on `POST /v2/systems` from Security Center.
- [GDM login and desktop bootstrap](tickets/04-gdm-login.md): GDM tile animation and single-user password field handled; `Log In To Fixture` keyword verified and desktop session established on seat0.
- [Rootless offline disk mutation](tickets/05-rootless-disk-mutation.md): `qemu-storage-daemon` NBD export + user-space `cryptsetup` opens LUKS2 via decoded 16-byte recovery key, dumps MK, mutates/reverts keyslots & tokens, written back via `qemu-img dd`.
- [Coverage manifest and verdicts](tickets/10-coverage-manifest.md): 59 entries, 11 executed, 0 recipe-known, 48 gap(reason); every `executed` entry names a passing case in which it was observed, no entry without a verdict.
- [State cases](tickets/07-state-cases.md): three state kinds pass on real VMs (`fde-eulq8mx4`, `fde-jmt6ti2b`, `fde-kb6g12cr`), the cleared-TPM `running-in-vm`/`require-reprovision` case passes, and the other ten kinds carry source-backed blocked verdicts, so every kind has a verdict.
- [Happy-path cases](tickets/08-happy-path-cases.md): all five pass on real VMs, including a passphrase added after repair (`fde-e2vs086r`); the Add-step template that broke two replays was a 61x35 crop that could not match the 1280x800 dialog and is now a pixel-exact 92x37 crop.
- [Three reprovision failure cases](tickets/09-failure-cases.md): cancel and key-expiry pass; the power cut passes end to end (`fde-jrq4rij1`, 357 s) after the post-cut boot wait learned to retry only `snapd-error` and transport timeouts; the interrupted clone's reboot loop and unanswered prompt are recorded as the other outcome of the same state.
- [On-demand runbook and full-suite proof](tickets/11-runbook-and-proof.md): the results table accounts for all 21 scenarios with eleven passes and ten source-cited state blockers; the runbook carries per-case invocation, secret handling, report reading, and the `--keep` leftover-volume trap.

## Remaining verification

- `results.md` accounts for all 21 requested scenarios and the additional missing-TPM unavailable flow; a pending row is not a pass.
- Reboot/relogin and real expiry/regenerate/retry pass. All five happy paths have clean real-VM evidence (`fde-fnircwvi`, `fde-ilf71dfu`, `fde-2sj8zuoj`, `fde-abpqgvdm`, `fde-e2vs086r`).
- The power-cut case passes end to end (`fde-jrq4rij1`, 357 s): the handler replaced its stage file, the host cut power on the typed timeout in 0.0 s, the restarted clone was unlocked with the recovery key, snapd's on-boot retry restored the baseline keyslots and failed the change with `missing reprovision context`, the interrupted attempt's key was rejected, and a second repair completed with a reboot that unlocked without a key. The post-cut boot wait retries only `snapd-error` and transport timeouts; the earlier replay failures that led there are recorded in ticket 09.
- The runbook is written (`tests/desktop-security-center/desktop-security-center-reprovision/README.md`) and the results table accounts for every requested scenario: eleven passes with run directories and ten source-cited state blockers.
- The three firmware-state recipes have clean-log replays (`fde-eulq8mx4`, `fde-jmt6ti2b`, `fde-kb6g12cr`) with no recovery-key pattern in any report; their older private XML logs contain recovery keys and are not evidence.
- Preflight checks installed identities against the private fixture. A separate golden export's existence does not prove equivalence with the actual source paths in `ugt-fde-checkpoint` XML, or establish executable build provenance.

## Out of scope

- Recipe hunting for `no-known-recipe` entries (`degraded`, `indeterminate`, `internal-error`, `tpm-device-failure`, `tpm-command-failed`, `tpm-pcr-unusable`, `not-initialized`): excluded by the user.
- `require-platform-reset` and `permit-manual` (the app always reprovisions; out of app scope).
- `shutdown-required`: excluded for lack of a legitimate recipe; it is PPI action-phase (`secboot/efi/preinstall/checks_context.go:685-687`), not hardware-only. The only recovered recipe forged PPI state.
- Hardware-only kinds remaining in the `needs-hardware` class.
- Snapd upgrade and root-proxy access.
- Agent-run CI, agent commits, pushes, and opening the PR; the user raises it.
- Security Center fake-service widget tests.

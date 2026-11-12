---
id: "02-golden-checkpoint-export"
title: "Golden checkpoint export wizard"
type: task
label: "wayfinder:task"
state: closed
parent: map
assignee: "@agent"
depends_on: []
---

# Golden checkpoint export wizard

## Question

What exactly must the one-time sudo export copy and verify from `tpm-fde-test2` so every later step runs unprivileged?

## Notes

Specify source paths for the disk, UEFI NVRAM, swtpm state and domain XML; a `0700` target under a private path; SHA-256 verification; the source left shut off and unchanged; and a metadata JSON containing paths and hashes only, never secrets. Produce the script and the one-paragraph instruction the user runs.


## Draft

Script: [export-golden.py](../wizard/export-golden.py); instructions: [README.md](../wizard/README.md).

`--check` passes against `tpm-fde-test2`: shut off, 9.9 GiB disk, 304.2 GiB free, swtpm at `/var/lib/libvirt/swtpm/0a85de37-7876-463a-b4bd-f4f05e76ae1c`. Helper copy and SHA-256 round-trip tested.

Run: `sudo ./docs/wayfinder/tpm-fde-reprovision-e2e/wizard/export-golden.py`.

Script ships at `docs/wayfinder/tpm-fde-reprovision-e2e/wizard/export-golden.py`; the fixture it produces stays private under `~/.local/share/ugt-fde/`.

Closes when the export completes, metadata.json verifies, and the source is still shut off.
HITL: the user executes the export.

## Resolution

One-time sudo export completed successfully:

1. **Export location**: `~/.local/share/ugt-fde/golden/tpm-fde-test2-20261111T144646Z/` (mode `0700`, owner `yashpal.yadav@canonical.com`).
2. **Files exported**:
   - `disks/tpm-fde-sboff-base.qcow2`: 10.6 GB, SHA-256 `394fbc917828d4c650059ea28cd4596a36744bc0c6fe072592c3defddb1df2fd`.
   - `nvram/tpm-fde-sbenroll_VARS.fd`: 540 KB, SHA-256 `fd767c2d06d7b3ade4a00896a018176c983304e01c6f477feafb5fec8ecc74b2`.
   - `swtpm/tpm2/tpm2-00.permall`: 8.3 KB, SHA-256 `071fd1701659fc01ac32cbbc3c9881d2b8bad055b50d749cf505c29273fd12d6`.
   - `swtpm/tpm2/.lock`: 0 B, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
   - `domain.xml`: 8.5 KB, SHA-256 `8d90147c3bcb15f6754dcd9fc22f9aea7b86a7c6b84e4f7962f2fe1b5df1f98e`.
3. **Verification**: `metadata.json` written and verified; source domain `tpm-fde-test2` confirmed still in `shut off` state.

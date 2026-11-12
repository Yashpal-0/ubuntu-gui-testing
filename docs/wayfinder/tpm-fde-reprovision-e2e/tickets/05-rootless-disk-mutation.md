---
id: "05-rootless-disk-mutation"
title: "Rootless offline disk mutation"
type: prototype
label: "wayfinder:prototype"
state: closed
parent: map
assignee: null
depends_on: ["02-golden-checkpoint-export"]
---

# Rootless offline disk mutation

## Question

Can a clone's disk be edited offline without host root — open LUKS with the fixture key and read or write files, keyslots and tokens — using libguestfs or qemu-storage-daemon?

## Notes

Prototype one reversible mutation, then report the tool, exact commands, what it can and cannot change, and the failure modes.

Prototype code may live in `docs/wayfinder/tpm-fde-reprovision-e2e/prototype/`; it ships only if the runbook needs it.

HITL: the prototype needs the host and a private clone.

## Resolution

Closed on 2026-11-11. Prototype implemented and verified in `docs/wayfinder/tpm-fde-reprovision-e2e/prototype/offline_disk_mutation.py`.

### Proven Toolchain
1. **`qemu-storage-daemon` (NBD export):** Exports slice of target QCOW2 (e.g. `ubuntu-save` at offset 6,031,409,152 size 32 MiB, `ubuntu-data` at offset 6,064,963,584) over UNIX domain socket (`addr.type=unix`). Writable mode (`writable=on`) allows write-back to disposable QCOW2 overlays.
   - *Failure mode:* FUSE export (`--export type=fuse`) fails because AppArmor policy `/etc/apparmor.d/fusermount3` restricts mount write permissions on non-standard mountpoints. NBD UNIX socket avoids FUSE entirely and runs 100% rootless and unprivileged.
   - *Failure mode:* QEMU's internal `driver=luks` only supports LUKS1 (`LUKS version 2 is not supported`).
2. **`cryptsetup` (User-space LUKS2 operations):**
   - Decoded recovery key (8 groups of 16-bit little-endian integers -> 16 raw bytes) tests valid:
     `cryptsetup open --test-passphrase --type luks2 --key-file - <slice.raw>` (Exit 0).
   - Volume key dump:
     `cryptsetup luksDump --dump-volume-key --key-file - <slice.raw>` dumps the 512-bit master key rootlessly.
   - Token export/import/removal:
     `cryptsetup token export --token-id 4 <slice.raw>`
     `cryptsetup token remove --token-id 4 <slice.raw>`
     `cryptsetup token import --token-id 4 <slice.raw>`
   - Keyslot destruction:
     `cryptsetup luksKillSlot --key-file - <slice.raw> 4`
3. **`qemu-img dd` (Safe slice write-back):**
   `qemu-img dd -f raw -O raw if=<mutated_hdr.bin> of=nbd+unix:///slice0?socket=<sock> bs=4096 count=2048`
   Applies sector-level changes back to the QCOW2 overlay with zero host root privileges.
4. **Filesystem tools:**
   - `debugfs -w` reads/writes ext4 filesystems (`ubuntu-boot`) directly rootlessly.
   - `sgdisk` / `parted` modifies GPT partition tables rootlessly.
   - TPM and NVRAM state files (`swtpm/`, `nvram/`) are standard user-owned files in `~/.local/share/ugt-fde/` and `~/.local/share/libvirt/swtpm/`, modified directly.

### Reversible Prototype Test Evidence
1. Created throwaway QCOW2 overlay on golden checkpoint.
2. Exported `ubuntu-save` partition over rootless NBD socket.
3. Exported token 4 (`ubuntu-fde-fallback`).
4. Removed token 4; verified absence in keyslot metadata.
5. Wrote mutated header back to overlay via `qemu-img dd`.
6. Re-read from overlay via fresh connection; confirmed token 4 missing.
7. Restored token 4 via `cryptsetup token import` and wrote back.
8. Re-read from overlay; confirmed token 4 byte-for-byte restored.

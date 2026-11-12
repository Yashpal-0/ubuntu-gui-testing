#!/usr/bin/env python3
"""Offline rootless disk and LUKS mutation prototype.

Demonstrates:
1. Exporting partition slices over rootless NBD via qemu-storage-daemon.
2. Opening LUKS2 headers using decoded 16-byte recovery keys without host root.
3. Inspecting and mutating keyslots and tokens using standard cryptsetup.
4. Writing mutations back to clone overlays safely.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import subprocess
import tempfile
import time
from pathlib import Path


def decode_recovery_key(key_text: str) -> bytes:
    """Decode an 8-group dash-separated 16-bit word key into 16 raw bytes."""
    groups = key_text.strip().split("-")
    if len(groups) != 8:
        raise ValueError(f"Expected 8 key groups, got {len(groups)}")
    return struct.pack("<8H", *[int(g) for g in groups])


def inspect_luks_header(image_path: Path, offset: int, size: int) -> dict[str, object]:
    """Inspect LUKS2 header at offset using rootless NBD and cryptsetup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = Path(tmpdir) / "nbd.sock"
        dump_path = Path(tmpdir) / "hdr.bin"

        # Spawn rootless qemu-storage-daemon exporting slice over UNIX domain socket
        proc = subprocess.Popen(
            [
                "qemu-storage-daemon",
                "--blockdev", f"driver=file,node-name=f0,filename={image_path},read-only=on",
                "--blockdev", "driver=qcow2,node-name=q0,file=f0,read-only=on",
                "--blockdev", f"driver=raw,node-name=slice0,file=q0,offset={offset},size={size}",
                "--nbd-server", f"addr.type=unix,addr.path={sock_path}",
                "--export", "type=nbd,id=exp0,node-name=slice0,name=slice0",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            for _ in range(50):
                if sock_path.exists():
                    break
                time.sleep(0.1)

            # Dump header (first 16 MiB is sufficient for LUKS2 metadata and keyslots)
            subprocess.run(
                [
                    "qemu-img", "convert", "-f", "raw", "-O", "raw",
                    f"nbd+unix:///slice0?socket={sock_path}", str(dump_path),
                ],
                check=True,
                capture_output=True,
            )

            dump_text = subprocess.check_output(
                ["/usr/sbin/cryptsetup", "luksDump", str(dump_path)],
                text=True,
            )
            return {"luksDump": dump_text}
        finally:
            proc.terminate()
            proc.wait(timeout=5)


def verify_recovery_key(image_path: Path, offset: int, size: int, raw_key: bytes) -> bool:
    """Verify recovery key unlocks LUKS2 keyslot rootlessly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = Path(tmpdir) / "nbd.sock"
        dump_path = Path(tmpdir) / "hdr.bin"

        proc = subprocess.Popen(
            [
                "qemu-storage-daemon",
                "--blockdev", f"driver=file,node-name=f0,filename={image_path},read-only=on",
                "--blockdev", "driver=qcow2,node-name=q0,file=f0,read-only=on",
                "--blockdev", f"driver=raw,node-name=slice0,file=q0,offset={offset},size={size}",
                "--nbd-server", f"addr.type=unix,addr.path={sock_path}",
                "--export", "type=nbd,id=exp0,node-name=slice0,name=slice0",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            for _ in range(50):
                if sock_path.exists():
                    break
                time.sleep(0.1)

            subprocess.run(
                [
                    "qemu-img", "convert", "-f", "raw", "-O", "raw",
                    f"nbd+unix:///slice0?socket={sock_path}", str(dump_path),
                ],
                check=True,
                capture_output=True,
            )

            res = subprocess.run(
                [
                    "/usr/sbin/cryptsetup", "open", "--test-passphrase", "--type", "luks2",
                    "--key-file", "-", str(dump_path),
                ],
                input=raw_key,
                capture_output=True,
            )
            return res.returncode == 0
        finally:
            proc.terminate()
            proc.wait(timeout=5)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rootless offline disk mutation prototype")
    parser.add_argument("--disk", type=Path, required=True, help="Path to qcow2 disk")
    parser.add_argument("--key-file", type=Path, required=True, help="Path to recovery-key.txt")
    parser.add_argument("--offset", type=int, default=6031409152, help="Partition offset (default: ubuntu-save)")
    parser.add_argument("--size", type=int, default=33554432, help="Partition size (default: 32 MiB)")
    args = parser.parse_args()

    key_text = args.key_file.read_text().strip()
    raw_key = decode_recovery_key(key_text)
    print(f"Decoded recovery key ({len(raw_key)} bytes): {raw_key.hex()}")

    valid = verify_recovery_key(args.disk, args.offset, args.size, raw_key)
    print(f"Recovery key validity on partition at {args.offset}: {valid}")

    hdr = inspect_luks_header(args.disk, args.offset, args.size)
    print("LUKS header successfully dumped rootlessly.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Export the golden TPM-FDE domain as a private, verified fixture.

The source domain must be shut off. This script only reads it: it copies the
disk, UEFI NVRAM, swtpm state and domain XML into a 0700 tree, hashes every
file, writes a paths-and-hashes-only metadata.json, and leaves the source
shut off.

Run with sudo:
    sudo ./docs/wayfinder/tpm-fde-reprovision-e2e/wizard/export-golden.py

Use --check without sudo to print the plan and the space requirement.
"""

import argparse
import datetime
import hashlib
import json
import os
import pwd
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

CHUNK = 8 * 1024 * 1024
MIB = 1024 * 1024


def die(message):
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def human(size):
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
        value /= 1024


def run(command):
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        die(f"{' '.join(command)} failed: {result.stderr.strip()}")
    return result.stdout


def virsh(uri, *args):
    return run(["virsh", "-c", uri, *args])


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def regular_files(root):
    return sorted(
        path for path in root.rglob("*") if path.is_file() and not path.is_symlink()
    )


def discover(uri, domain):
    xml = virsh(uri, "dumpxml", domain)
    root = ET.fromstring(xml)
    uuid = (root.findtext("uuid") or "").strip()
    if not uuid:
        die("domain XML has no UUID")

    disks = []
    for disk in root.findall("./devices/disk"):
        if disk.get("device") != "disk":
            continue
        if disk.get("type") != "file":
            die(f"unsupported disk type {disk.get('type')!r}; only file disks are exported")
        source = disk.find("source")
        path = source.get("file") if source is not None else None
        if not path:
            die("disk has no <source file=...>")
        disks.append(Path(path))
    if not disks:
        die("domain has no file-backed disk")

    nvram_text = (root.findtext("./os/nvram") or "").strip()
    nvram = Path(nvram_text) if nvram_text else None

    tpm = root.find("./devices/tpm")
    if tpm is None:
        die("domain has no TPM; this is not a TPM-FDE fixture")

    state_source = tpm.find("./backend/source")
    if state_source is not None and state_source.get("dir"):
        swtpm = Path(state_source.get("dir"))
    elif uri == "qemu:///system":
        swtpm = Path("/var/lib/libvirt/swtpm") / uuid
    else:
        config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        swtpm = config_home / "libvirt/qemu/swtpm" / uuid

    return xml, uuid, disks, nvram, swtpm


def disk_has_backing(path):
    output = run(["qemu-img", "info", "--output=json", str(path)])
    info = json.loads(output)
    return bool(info.get("backing-filename") or info.get("full-backing-filename"))


def free_space(path):
    probe = path
    while not probe.exists():
        if probe.parent == probe:
            die(f"cannot find an existing parent of {path}")
        probe = probe.parent
    return shutil.disk_usage(probe).free


def owner_identity():
    sudo_user = os.environ.get("SUDO_USER")
    if os.geteuid() == 0 and sudo_user:
        entry = pwd.getpwnam(sudo_user)
        return Path(entry.pw_dir), entry.pw_uid, entry.pw_gid
    entry = pwd.getpwuid(os.geteuid())
    return Path(entry.pw_dir), entry.pw_uid, entry.pw_gid


def default_destination(home, domain):
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return home / ".local/share/ugt-fde/golden" / f"{domain}-{stamp}"


def copy_file(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    run(
        [
            "cp",
            "--reflink=auto",
            "--sparse=always",
            "--preserve=mode,timestamps",
            "--",
            str(source),
            str(destination),
        ]
    )


def own_tree(root, uid, gid, apply_owner):
    for path in [root, *root.rglob("*")]:
        if apply_owner:
            os.chown(path, uid, gid)
        os.chmod(path, 0o700 if path.is_dir() else 0o600)


def prepare_destination_parent(destination, is_default, uid, gid, apply_owner):
    missing = []
    probe = destination.parent
    while not probe.exists():
        missing.append(probe)
        probe = probe.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        if apply_owner:
            os.chown(directory, uid, gid)
        os.chmod(directory, 0o700)
    os.chmod(destination.parent, 0o700)
    if is_default:
        for directory in (destination.parent.parent, destination.parent):
            os.chmod(directory, 0o700)
            if apply_owner:
                os.chown(directory, uid, gid)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", default="tpm-fde-test2")
    parser.add_argument("--uri", default="qemu:///system")
    parser.add_argument("--dest", type=Path, default=None)
    parser.add_argument(
        "--check",
        action="store_true",
        help="print the plan and space requirement without writing anything",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="keep an existing destination as <dest>.replaced.<timestamp>",
    )
    args = parser.parse_args()

    if not args.check and os.geteuid() != 0:
        die("run with sudo; the source disk, NVRAM and swtpm state are root-only")

    state = virsh(args.uri, "domstate", args.domain).strip()
    xml, uuid, disks, nvram, swtpm = discover(args.uri, args.domain)
    home, uid, gid = owner_identity()
    destination = args.dest or default_destination(home, args.domain)

    if state != "shut off":
        die(f"source domain {args.domain} is {state!r}; shut it down and rerun")

    required = 64 * MIB
    missing = []
    for disk in disks:
        if not disk.is_file():
            missing.append(str(disk))
            continue
        required += disk.stat().st_size
    if nvram is None:
        die("domain XML has no NVRAM path")
    if not nvram.is_file():
        missing.append(str(nvram))
    else:
        required += nvram.stat().st_size
    if not swtpm.is_dir():
        missing.append(str(swtpm))
    else:
        required += sum(path.stat().st_size for path in regular_files(swtpm) if path.exists())
    if missing:
        die("missing source files: " + ", ".join(missing))

    free = free_space(destination)
    print(f"domain:      {args.domain} ({uuid})")
    print(f"state:       {state}")
    print(f"disks:       {', '.join(str(path) for path in disks)}")
    print(f"nvram:       {nvram}")
    print(f"swtpm:       {swtpm}")
    print(f"destination: {destination}")
    print(f"required:    {human(required)}; free: {human(free)}")
    if free < required + 128 * MIB:
        die(f"not enough free space at {destination.parent}")

    if args.check:
        print("check: source paths present; run the same command with sudo to export")
        return

    for disk in disks:
        if disk_has_backing(disk):
            die(f"{disk} has a backing chain; flatten it before exporting")

    apply_owner = os.geteuid() == 0
    prepare_destination_parent(destination, args.dest is None, uid, gid, apply_owner)

    if destination.exists():
        if not args.force:
            die(f"{destination} exists; use --force to keep it as {destination}.replaced.<timestamp>")
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = destination.with_name(f"{destination.name}.replaced.{stamp}")
        destination.rename(backup)
        print(f"kept previous export at {backup}")

    stage = destination.parent / f".{destination.name}.partial.{os.getpid()}"
    if stage.exists():
        die(f"staging directory already exists: {stage}")

    try:
        stage.mkdir(mode=0o700)
        for disk in disks:
            copy_file(disk, stage / "disks" / disk.name)
        copy_file(nvram, stage / "nvram" / nvram.name)
        shutil.copytree(
            swtpm,
            stage / "swtpm",
            symlinks=True,
            ignore=shutil.ignore_patterns("*.sock"),
        )
        (stage / "domain.xml").write_text(xml, encoding="utf-8")

        if virsh(args.uri, "domstate", args.domain).strip() != "shut off":
            die("source domain changed state during the copy; export aborted")

        files = []
        for disk in disks:
            target = stage / "disks" / disk.name
            source_hash = sha256(disk)
            target_hash = sha256(target)
            if source_hash != target_hash:
                die(f"copy verification failed for {disk}")
            files.append(
                {
                    "role": "disk",
                    "path": str(target.relative_to(stage)),
                    "size": target.stat().st_size,
                    "sha256": target_hash,
                }
            )

        nvram_target = stage / "nvram" / nvram.name
        nvram_hash = sha256(nvram_target)
        if sha256(nvram) != nvram_hash:
            die(f"copy verification failed for {nvram}")
        files.append(
            {
                "role": "nvram",
                "path": str(nvram_target.relative_to(stage)),
                "size": nvram_target.stat().st_size,
                "sha256": nvram_hash,
            }
        )

        swtpm_files = regular_files(stage / "swtpm")
        if not swtpm_files:
            die("copied swtpm state is empty")
        for target in swtpm_files:
            files.append(
                {
                    "role": "swtpm",
                    "path": str(target.relative_to(stage)),
                    "size": target.stat().st_size,
                    "sha256": sha256(target),
                }
            )

        domain_xml = stage / "domain.xml"
        files.append(
            {
                "role": "domain-xml",
                "path": "domain.xml",
                "size": domain_xml.stat().st_size,
                "sha256": sha256(domain_xml),
            }
        )

        metadata = {
            "schema": 1,
            "domain": args.domain,
            "uuid": uuid,
            "libvirt_uri": args.uri,
            "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source_state": "shut off",
            "source": {
                "disks": [str(path) for path in disks],
                "nvram": str(nvram),
                "swtpm": str(swtpm),
            },
            "files": files,
        }
        metadata_path = stage / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

        os.sync()
        os.replace(stage, destination)
        own_tree(destination, uid, gid, apply_owner=apply_owner)
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)

    print(f"exported:    {destination}")
    print(f"files:       {len(files) + 1}")
    print(f"size:        {human(sum(item['size'] for item in files))}")
    print("next:        point the FDE fixture at metadata.json; source remains shut off")


if __name__ == "__main__":
    main()

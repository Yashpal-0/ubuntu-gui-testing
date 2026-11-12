# Ubuntu GUI Testing Runner

Test runner that manages libvirt virtual machines for GUI test execution using [YARF](https://github.com/canonical/yarf).

## Usage

### From an ISO

Boot a VM from an ISO and run the test suite:

```bash
ubuntu-gui-testing-runner \
  --suite tests/desktop-installer \
  --test resolute.entire-disk \
  --iso ~/images/ubuntu-26.04-desktop-amd64.iso
```

### From an existing domain

Clone an existing libvirt domain (using a qcow2 overlay) and run the test suite against it:

```bash
ubuntu-gui-testing-runner \
  --suite tests/firefox-example \
  --test firefox-example-basic \
  --source-domain ugt-desktop-installer-resolute.entire-disk-2026-06-01
```

### From an existing domain with source disk mounted as USB

When cloning from an existing domain, you can optionally attach a second overlay
of the same source image as a USB disk. This is useful for tests that need to
mount or unlock a secondary device.

```bash
ubuntu-gui-testing-runner \
  --suite tests/snap-tpmctl \
  --test snap-tpmctl-mount \
  --source-domain ugt-desktop-installer-resolute.entire-disk-2026-06-01 \
  --mount-source-domain /dev/sda5
```

If `--mount-source-domain` is passed without a value, the default device is
`/dev/sda`.

### Options

| Flag | Description |
| - | - |
| `--suite` | Path to the test suite (required) |
| `--test` | Name of the test to run (required) |
| `--iso` | Path to an ISO for installation |
| `--source-domain` | Existing libvirt domain to clone from |
| `--mount-source-domain [DEVICE]` | Attach a second overlay of the source domain as a USB disk and pass `DEVICE` to Robot variables |
| `--keep` | Keep the VM and resources after the run |
| `--connection-uri` | Libvirt connection URI (default: `qemu:///session`) |
| `--pool-name` | Storage pool name (default: `ubuntu-gui-testing`) |
| `--pool-dir` | Storage pool directory (default: `/pool`) |
| `--artifacts-dir` | Directory for test artifacts (default: `./artifacts`) |
| `--swtpm-state-dir` | Path to swtpm state (default: `~/.config/libvirt/qemu/swtpm`) |
| `--test-username` | Guest SSH username (default: `ubuntu`) |
| `--test-password` | Guest SSH password (default: `ubuntu`) |
| `--domain-template` | Override domain XML template |
| `--pool-template` | Override pool XML template |
| `--volume-template` | Override volume XML template |
| `--overlay-template` | Override overlay volume XML template |

Either `--iso` or `--source-domain` must be provided.

### TPM-FDE fixtures

`--fde-config PATH` names a private TPM-FDE fixture and requires
`--robot-test NAME`; one selected case runs against one disposable clone. The
fixture's `prepare` list owns every state change made before that case starts,
while the case itself drives the repair through the installed application.

| `prepare` step | State created before the case |
|---|---|
| `clear-tpm-state` | Removes the clone's TPM state so snapd asks for recovery |
| `no-tpm` | Removes the clone's TPM device so snapd reports no suitable TPM2 device |
| `plain-ovmf` | Boots SB-capable firmware with Secure Boot off |
| `sysprep-app` | Adds a signed vendor SysPrep application |
| `sysprep-weak-sb` | Adds a SysPrep application signed with a weak key |
| `sysprep-digest-sb` | Adds a SysPrep application authorized by digest |
| `preos-digest-sb` | Adds a pre-OS driver authorized by digest |
| `preos-weak-sb` | Adds a pre-OS driver signed with a weak key |
| `enroll-auth` | Enrolls the fixture's `auth_mode` PIN or passphrase |

`enroll-auth` needs one real first boot: the runner boots the clone, has snapd
replace the platform keyslots through `/v2/system-volumes`, waits for the
change, and requests a clean shutdown. Every other stopped-clone preparation
runs after that shutdown, and Yarf starts only after the clone is stopped
again. The step requires `auth_mode` `pin` or `passphrase`. A stopped-clone
fault may follow it, including `clear-tpm-state`: clearing the cloned TPM
state leaves the on-disk keyslot authentication metadata intact, so the clone
boots with its recovery key while the repair UI still sees the enrolled mode.
`plain-ovmf` also waits: enrollment boots the healthy Secure Boot domain, and
the stopped clone is redefined to plain OVMF only after shutdown.
`no-tpm` waits the same way: enrollment boots with the clone's TPM device, and
only the stopped clone is redefined without it; the source domain keeps its TPM.
The same action is available to the Robot library as the `enroll-auth` guest
operation with parameters `{"auth_mode": "pin"|"passphrase", "pin"|"passphrase":
...}`; secrets stay in the fixture and never become Robot variables.

## Development

Requires Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
cd runner
uv sync --group dev
```

### Quality checks

```bash
uv run ruff format .
uv run ruff check .
uv run mypy .
uv run pytest tests/
```

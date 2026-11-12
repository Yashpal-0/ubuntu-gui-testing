---
type: research
ticket: 13-yarf-runner-surface
label: wayfinder:research
state: closed
---

# YARF and runner extension surface

Resolves ticket `13-yarf-runner-surface` for the local wayfinder map
(`docs/wayfinder/tpm-fde-reprovision-e2e/map.md`, destination in its
Destination section, constraints in its Notes).

All citations are paths relative to the repository root
`/data/External/Canonical/Work/ubuntu-gui-testing`, unless they point into
`runner/.venv/lib/python3.14/site-packages/yarf/` (the installed YARF the runner
actually spawns; `yarf` is resolved from `PATH` at
`runner/ubuntu_gui_testing_runner/base.py:312-325` and the local venv is the one
on `PATH` per the documented invocation `PATH="$PWD/runner/.venv/bin:$PATH"`
recovered at `/tmp/tmp42m1jbm5/desktop-security-center-reprovision/README.md:66-67`).

**Citation conventions.** A bare module name (`base.py`, `image_runner.py`, …)
resolves to `runner/ubuntu_gui_testing_runner/`; a bare `test_*.py` to
`runner/tests/`; a bare `*_template.xml` to `runner/templates/`; a bare
`pyproject.toml` or `uv.lock` to `runner/`; `map.md` to
`docs/wayfinder/tpm-fde-reprovision-e2e/`; and `yarf/...` to
`runner/.venv/lib/python3.14/site-packages/`. Robot and `/tmp` paths are written
in full.

Two further bare names occur: `desktop-security-center.resource` resolves to
`tests/desktop-security-center/`, and `video_input_base.py` to
`runner/.venv/lib/python3.14/site-packages/yarf/rf_libraries/libraries/`.

## Evidence base

| Source | Role |
| --- | --- |
| `runner/ubuntu_gui_testing_runner/{base,image_runner,iso_runner,cli,__main__,constants,ssh}.py` | the runner under extension |
| `runner/templates/{image_domain_template,overlay_template,pool_template}.xml` | domain/volume shape, TPM, vsock, channels |
| `runner/.venv/.../yarf/{main.py,output/__init__.py,rf_libraries/suite_parser.py,rf_libraries/libraries/video_input_base.py,rf_libraries/libraries/vnc/__init__.py}` | YARF CLI, selection, outdir, video |
| `tests/desktop-security-center/**` | Robot suite conventions, plan registration |
| `runner/tests/*.py` | the asserted contracts for naming, spawning, TPM copy |
| `/tmp/fde.py.fixed`, `/tmp/tmp42m1jbm5/**` | **reference only, never evidence** (`docs/wayfinder/tpm-fde-reprovision-e2e/map.md`, Notes); used solely to name intended seams |
| `runner/**/__pycache__/*.pyc` (untracked WIP bytecode) | **reference only, never evidence** (`docs/wayfinder/tpm-fde-reprovision-e2e/map.md`, Notes); the fossil inventory is Appendix B |

No libvirt, VM, ssh or network call was made; every lifecycle claim below is a
static reading of the code that defines it. Anything that depends on runtime
libvirt behaviour is listed in *Unresolved unknowns*.

---

## 1. Lifecycle map

### 1.1 Object graph and entry point

- `ubuntu-gui-testing-runner` → `ubuntu_gui_testing_runner.__main__:main`
  (`runner/pyproject.toml:14-15`).
- `main()` parses args, picks `LibvirtIsoRunner` (`--iso`) or
  `LibvirtImageRunner` (`--source-domain`) and enters it as a context manager
  (`runner/ubuntu_gui_testing_runner/__main__.py:16-49`).
- `suite_name` is the **basename of the suite path** and `test_name` is the
  runner's `--test` value (`__main__.py:20-21`, `:36-37`).
- `_BaseLibvirtRunner.__init__` opens libvirt, derives names, ensures the pool,
  then calls the subclass `_setup()` inside one try block
  (`runner/ubuntu_gui_testing_runner/base.py:31-74`).
- `LibvirtImageRunner._setup` is a fixed five-step sequence:
  extract → overlay → NVRAM → define domain → copy TPM
  (`runner/ubuntu_gui_testing_runner/image_runner.py:56-61`).

### 1.2 Create

| Step | Where | What happens |
| --- | --- | --- |
| source lookup | `image_runner.py:63-72` | `conn.lookupByName(source_domain)`; no `isActive()` check |
| disk source | `image_runner.py:74-93` | first `<disk device="disk">` `<source file=...>` |
| NVRAM source | `image_runner.py:95-107` | `<os><nvram>` text, else the `source` attribute |
| TPM source dir | `image_runner.py:109-115` | `DEFAULT_SWTPM_STATE_DIR / <source uuid>` |
| overlay | `image_runner.py:148-154` | `pool.createXML()` of `overlay_template.xml` with `{backing_image}` |
| second overlay (optional) | `image_runner.py:156-166` | `--mount-source-domain` adds a USB overlay of the *same* source image |
| NVRAM copy | `image_runner.py:168-172` | `shutil.copy2()` into the pool dir, then `pool.refresh(0)` |
| domain define | `image_runner.py:189-203` | renders `image_domain_template.xml`, `conn.defineXML()` |
| TPM copy | `image_runner.py:174-187` | `shutil.copytree(source_dir, DEFAULT_SWTPM_STATE_DIR / <new uuid>)` |
| start | `base.py:229-233` | `domain.create()` only if `isActive() == 0`, after `_setup()` |

The domain is defined **stopped** (`defineXML` does not start it), and TPM state
is copied only after define because it needs the new `UUIDString()`
(`image_runner.py:180-182`). That ordering is the natural place for a
"prepare the stopped clone" hook (§3.2).

The template is `<domain type="kvm">` with `q35`, EFI pflash
(`/usr/share/OVMF/OVMF_CODE_4M.ms.fd`, secure boot + enrolled keys),
`<on_poweroff>destroy</on_poweroff>`, `<on_reboot>restart</on_reboot>`,
`<on_crash>destroy</on_crash>`
(`runner/templates/image_domain_template.xml:1-33`), user-mode networking,
guest-agent channel, TPM CRB emulator with `persistent_state="yes"`, SPICE+VNC,
and an auto-CID vsock (`:42-73`).

### 1.3 Name

- `ugt-{suite_name}-{test_name}-{YYYY-MM-DD}`, then `-2`, `-3`, … until
  `conn.lookupByName()` fails (`base.py:260-274`). Asserted by
  `runner/tests/test_domain_name.py:35-82` with example
  `ugt-desktop-installer-resolute.entire-disk-<date>`.
- Derivative names: `{domain}.qcow2`, `{domain}-usb.qcow2`,
  `{domain}-VARS.fd` (`base.py:67-69`).
- The UUID is libvirt-assigned at `defineXML` and read back immediately
  (`image_runner.py:180`); nothing writes it anywhere except the TPM dir it names
  (`image_runner.py:181`).

Consequence for this effort: `test_name` is the **suite directory** name, not the
Robot case name. It is the runner's `--test` value (`__main__.py:21`, `:37`),
which `_spawn_yarf` passes as Robot's `--suite` (`base.py:322`), so it names a
suite, not a case. The clone name therefore cannot distinguish two cases that
share one suite name on the same day (they collide into `-2`, `-3`).

### 1.4 Store

- Pool default `ubuntu-gui-testing` at `/pool` (`runner/ubuntu_gui_testing_runner/constants.py:8-9`),
  defined on demand with `setAutostart(True)` (`base.py:283-303`).
- Overlay volume: qcow2 with a backing store on the source image
  (`runner/templates/overlay_template.xml:1-11`).
- NVRAM: a raw file placed in the pool directory and registered by
  `pool.refresh(0)` (`image_runner.py:168-172`).
- TPM: `DEFAULT_SWTPM_STATE_DIR = Path.home()/".config/libvirt/qemu/swtpm"`
  (`constants.py:16`), per-domain subdirectory named by UUID
  (`image_runner.py:113`, `:181`, `:266`).
- Artifacts: `--artifacts-dir`, default `./artifacts` (`constants.py:11`;
  `base.py:52-56`), handed to YARF as `--outdir` (`base.py:316-317`).

### 1.5 Discover

There is **no discovery path**. The runner holds the `virDomain` object from
`defineXML` (`image_runner.py:200`) and uses only that. `lookupByName` is used
solely for name-collision detection (`base.py:269-274`) and for the source
domain (`image_runner.py:66`). A clone kept with `--keep` is rediscoverable only
by convention: `virsh -c qemu:///session list --all` and the `ugt-` prefix
(`base.py:261`). No manifest, lock file, or registry is written.

### 1.6 Cleanup

`close()` (`base.py:110-169`), reached from `__exit__` (`base.py:107-108`) and
from the `__init__` failure path (`base.py:72-74`):

1. `pool.refresh(0)` (`:111-112`).
2. `--keep`: graceful shutdown, then leave everything (`:114-120`).
3. Otherwise: `_destroy_domain()` (`:122-123`, definition `:222-227`), delete
   disk volume (`:125-131`), delete USB volume (`:133-140`), delete NVRAM volume
   by name (`:142-151`), `domain.undefine()` (`:153-157`), `conn.close()`
   (`:159-163`).
4. `LibvirtImageRunner.close()` runs **first** and removes the per-clone swtpm
   directory (`image_runner.py:263-274`), then calls `super().close()`.

`_shutdown_domain()` requests ACPI shutdown and falls back to `destroy()` after
`GRACEFUL_SHUTDOWN_TIMEOUT = 30` s, polling every 1 s
(`base.py:171-220`, `constants.py:20-21`).

### 1.7 Which libvirt connection

- Default `DEFAULT_CONNECTION_URI = "qemu:///session"` (`constants.py:7`),
  overridable with `--connection-uri` (`cli.py:54-59`), passed by
  `__main__.py:29`/`:44` into the base class (`base.py:38`, opened at `:276-281`).
- Session URI is therefore the default and the one the TPM path assumes; see
  leak L11.

### 1.8 How NVRAM is copied

`shutil.copy2(source_nvram, pool_dir / f"{domain}-VARS.fd")` then
`pool.refresh(0)` (`image_runner.py:168-172`), and the defined domain points
`<nvram format="raw">{nvram}</nvram>` at that copy
(`image_runner.py:191-199`; template `:13`). The template hardcodes the pflash
loader and secure-boot features (`image_domain_template.xml:6-15`), so the
varstore must match that loader; there is no loader placeholder today.

### 1.9 How swtpm state is copied

`shutil.copytree(DEFAULT_SWTPM_STATE_DIR / <source uuid>, DEFAULT_SWTPM_STATE_DIR / <new uuid>)`
(`image_runner.py:174-187`). The template declares
`<tpm model="tpm-crb"><backend type="emulator" version="2.0" persistent_state="yes"/>`
with no explicit source dir (`image_domain_template.xml:54-56`), so libvirt
derives the directory from the domain UUID — which is why the copy is keyed by
UUID and must happen after `defineXML`. `copytree` is called without `symlinks=`,
so links are followed, and no `isActive()` check protects the source
(`image_runner.py:63-72`): copying a live source yields a torn clone (L10).
The helper module `ssh.py:53-58` already demonstrates the host→guest pattern
used later for the guest channel (AF_VSOCK, port 22, paramiko).

---

## 2. Variable and test-selection contract

### 2.1 Exact argv

`_spawn_yarf` (`base.py:305-326`) builds, in order:

```
yarf --platform=Vnc <suite> --outdir <artifacts_path> -- \
     --variable CID:<vsock_cid> [--variable DEVICE:<dev>] [--variable RECOVERY_KEY:<key>] \
     --suite <test>
```

- `--platform=Vnc` is hardcoded (`base.py:314`).
- `<suite>` is the runner's `--suite` path, verbatim (`base.py:315`,
  `__main__.py:51`).
- `--outdir` is the resolved artifacts directory (`base.py:316-317`).
  `parse_arguments` splits on the first `--`
  (`runner/.venv/lib/python3.14/site-packages/yarf/main.py:187-212`)
  and `parse_robot_arguments` hands the tail to
  `RobotFramework().parse_arguments` (`yarf/main.py:165-184`).
- The subprocess is created with an argv list, no shell
  (`asyncio.create_subprocess_exec`, `base.py:325`).

`--log-video`, `--variant`, `--debug`, `--output-format` are YARF options that
must sit **before** `--` (`yarf/main.py:99-157`, `:145-149`).

### 2.2 How `--variable` reaches Robot

- `image_runner._run_yarf` builds `robot_variables`
  (`image_runner.py:225-247`): `CID` always; `DEVICE` when
  `--mount-source-domain` is set; `RECOVERY_KEY` when the source domain carries
  it in libvirt metadata (`image_runner.py:117-146`).
- YARF turns each into a Robot variable: `variables.extend(options.pop("variable"))`
  then `suite.run(variable=variables, ...)` (`yarf/main.py:371-372`, `:392-400`).
- Robot sees them as `${CID}`, `${DEVICE}`, `${RECOVERY_KEY}` — e.g.
  `tests/desktop-installer/JournalMonitor.py:27` reads `${CID}`, and
  `tests/desktop-security-center/desktop-security-center.resource:42` reads
  `${recovery_key}`.
- Secrets would appear in the child's **argv** (visible in `ps`); the recovered
  design deliberately keeps keys in files read by the Robot library instead
  (`/tmp/fde.py.fixed:1-9`, `:280-295`, reference only).

### 2.3 Environment

- `env = os.environ.copy()` and one addition: `VNC_PORT = vnc_port - 5900`
  (`base.py:323-324`). Everything else the runner has is inherited by YARF,
  including `XDG_RUNTIME_DIR` (relevant to §4) and any `YARF_LOG_VIDEO`.
- YARF's VNC library reads `VNC_HOST` (default `localhost`) and `VNC_PORT`,
  and adds 5900 (`yarf/rf_libraries/libraries/vnc/__init__.py:32-36`).
- Robot code reads the environment with `Get Environment Variable`
  (`tests/prompting/prompting-camera-cheese/prompting-camera-cheese.robot:29-30`).
- `VNC_PORT`/vsock are read **from the live domain XML** after start
  (`base.py:235-247`, extraction at `:335-350`); the port must be ≥ 5900 or the
  run aborts (`:239-243`) and the vsock CID must be present (`:245-247`).

### 2.4 Exactly one Robot test

Today the runner selects a **suite**, never a test:

- Its `--test` value is passed as Robot's `--suite` (`base.py:322`).
- YARF prefixes each `--suite` value with the root suite name
  (`suite.name + "." + s`, `yarf/main.py:375-377`) and calls
  `suite.filter(included_suites=..., included_tests=..., ...)`
  (`yarf/main.py:379-384`).
- Robot's `--test`/`--task` values are the only path to `included_tests`
  (`yarf/main.py:374`), and the runner never emits them.

Therefore: one `.robot` file with several `*** Test Cases ***` runs **all** of
them. That is why existing suites model a flow as a chain of test cases
(`tests/desktop-security-center/desktop-security-center-tpm-fde-change-passphrase/desktop-security-center-tpm-fde-change-passphrase.robot:13-40`:
`Log In`, `Open Security Center`, `Change Passphrase`, `Reboot`, …), while a
single-case flow is also legal.

To run exactly one case, `--test "<case name>"` must be forwarded after `--`
(§3.5). YARF also rejects an empty selection: `len(suite.suites) <= 0` returns
`DATA_ERROR` (`yarf/main.py:386-389`).

Note the suite path must stay the **parent directory**: YARF copies the whole
suite tree into a temp dir before running (`yarf/main.py:521-526`;
`yarf/rf_libraries/suite_parser.py:53-67`, `:92-104`), so shared resources
referenced as `${CURDIR}/../...`
`(`tests/desktop-security-center/desktop-security-center-tpm-fde-change-passphrase/desktop-security-center-tpm-fde-change-passphrase.robot:4`) resolve only
if the parent directory is the `--suite` root. This matches the reference note
at `/tmp/tmp42m1jbm5/desktop-security-center-reprovision/README.md:55-56`.

### 2.5 Artifacts and video

- Outdir comes from `--outdir` or, without it, `SNAP_USER_COMMON`/tmp +
  `yarf-outdir` (`yarf/output/__init__.py:25-46`); at startup it deletes only
  `output.xml`, `report.html`, `log.html`, `rfdebug_history.log`
  (`yarf/output/__init__.py:48-57`).
- Robot writes `output.xml` into that dir and YARF runs `rebot` to produce
  `report.html`/`log.html` (`yarf/main.py:392-403`).
- `${OUTPUT DIR}` inside Robot resolves to the same directory — used to save a
  recovery key file (`tests/desktop-installer/installer.resource:520-521`).
- Video: `--log-video` sets `YARF_LOG_VIDEO=1` in YARF's own environment
  (`yarf/main.py:145-149`, `:485-490`). At suite end, screenshots collected in a
  `TemporaryDirectory` are encoded by `ffmpeg` at **5 fps** into `video.webm` and
  embedded in the log when `YARF_LOG_VIDEO == "1"`, or on failure unless it is
  `"0"` (`yarf/rf_libraries/libraries/video_input_base.py:78-112`). Encoding
  failure is a warning, not a test failure (`:105-112`). No video file is left
  in the artifacts directory — it only exists inside `log.html`.

---

## 3. Extension points, with proposed signatures

Design rule for all of them: the runner keeps owning libvirt; Robot never
receives a secret or a libvirt handle unless §4 option B is chosen. Every
insertion point below is a single, named seam so `01-runner-fde-seam` can land
one commit per seam.

### 3.1 Private FDE fixture (`--fde-config`)

The runner needs the **host-side** projection only: validated paths, expectation
fields, and prepare steps. Secrets (login password, recovery key, PIN,
passphrase, SSH identity, known-hosts) stay in owner-only files that the Robot
library reads lazily through `FdeFixture.secret()`; they must never become
`--variable` values, because those are visible in `ps` (`base.py:320-321`).

The recovered WIP fixed the schema (bytecode fossil, reference only —
Appendix B):

| Group | Fields |
| --- | --- |
| required | `ssh_user`, `desktop_user`, `ssh_identity`, `ssh_known_hosts`, `ssh_host_alias`, `login_password_file`, `recovery_key_file`, `security_center_revision`, `snapd_version`, `snapd_executable_sha256`, `auth_mode`, `data_device`, `save_device` |
| optional | `pin_file`, `passphrase_file`, `lane`, `prepare` |
| lanes | `production`, `faultinject` |
| auth modes | `passphrase`, `pin`, `none` |
| preparations | `clear-tpm-state` |
| secret aliases | `recovery_key`→`recovery_key_file`, `login_password`→`login_password_file`, `pin`→`pin_file`, `passphrase`→`passphrase_file` |

JSON keys are kebab-case and renamed on load (`ssh-user` → `ssh_user`, …).
Validation keeps: regular file, owner is `geteuid()`, no group/other bits;
lowercase 64-hex `snapd_executable_sha256`; snap revision `0` or decimal;
dotted snapd version; absolute `data_device`/`save_device`; unknown keys
rejected; `prepare` a non-empty list drawn from `PREPARATIONS`. A raw
`recovery_key` field is rejected — only the `*_file` form loads (reference
validation shape at `/tmp/fde.py.fixed:132-155`, `:298-308`).

Proposed module `runner/ubuntu_gui_testing_runner/fde.py`:

```python
OPERATIONS: Final = frozenset({"preflight", "snapshot", "check", "fault",
    "check-key", "restart-snapd", "generate-competing-key", "reboot",
    "shutdown", "read-saved-key", "assert-auth"})
AUTH_MODES: Final = frozenset({"passphrase", "pin", "none"})
LANES: Final = frozenset({"production", "faultinject"})
PREPARATIONS: Final = frozenset({"clear-tpm-state"})

@dataclass(frozen=True)
class FdeFixture:
    path: Path
    ssh_user: str
    desktop_user: str
    ssh_identity: Path
    ssh_known_hosts: Path
    ssh_host_alias: str
    login_password_file: Path
    recovery_key_file: Path
    security_center_revision: str
    snapd_version: str
    snapd_executable_sha256: str
    auth_mode: str
    data_device: str
    save_device: str
    pin_file: Path | None
    passphrase_file: Path | None
    lane: str
    prepare: tuple[str, ...]

    @classmethod
    def load(cls, path: Path) -> "FdeFixture": ...
    def secret(self, name: str) -> str: ...
    def is_production_lane(self) -> bool: ...
```

Wiring (smallest diff, 3 files):

| File | Change |
| --- | --- |
| `cli.py` | add `--fde-config` (`type=Path`, default `None`) after the `--mount-source-domain` block (`cli.py:35-42`); recovered help: "Private TPM-FDE fixture configuration for one mutated clone" |
| `image_runner.py` | `__init__(..., fde_config: Path \| None = None)` next to `mount_source_domain` (`image_runner.py:29-41`); store `self.fde_config`, then `self.fde_fixture = FdeFixture.load(...)` |
| `__main__.py` | pass `fde_config=args.fde_config` to `LibvirtImageRunner` only (`__main__.py:34-47`) |

Two guards belong with the seam:

```python
# image_runner.py __init__, before super().__init__
if self.fde_config is not None and not kwargs.get("robot_test"):
    raise RuntimeError("An FDE configuration requires a single selected Robot case")

# after _extract_source_paths has found source_uuid / source_has_tpm
def _require_fde_baseline(self) -> None:
    if not self.source_has_tpm:
        raise RuntimeError(f"FDE source domain '{self.source_domain_name}' has no TPM device")
    if self.source_tpm_state_dir is None or not self.source_tpm_state_dir.is_dir():
        raise RuntimeError(
            f"FDE source domain '{self.source_domain_name}' has no TPM state in '{self.swtpm_state_dir}'"
        )
```

The Robot side needs the fixture **path** and the clone identity. `_run_yarf`
already assembles `robot_variables` (`image_runner.py:225-232`); for FDE it adds
five (Appendix B): `FDE_CONFIG`, `FDE_DOMAIN_UUID` (`self.domain.UUIDString()`),
`FDE_SOURCE_UUID`, `FDE_CONNECTION_URI`, `FDE_SWTPM_STATE_DIR`. Only paths and
identifiers cross; the secrets they name stay in files that the library reads
lazily (reference shape: `/tmp/tmp42m1jbm5/TpmFde.py:43-53`). Without these
variables the library cannot find the fixture, and without the library the
guest channel has no client.

### 3.2 Prepare actions on the stopped clone (`clear-tpm-state`)

Seam: `LibvirtImageRunner._setup` (`image_runner.py:56-61`), immediately after
`self._copy_tpm_state()` and before `_setup` returns — i.e. while the domain is
defined but not yet started (`base.py:229-233` is the only start site).

```python
def _setup(self) -> None:
    self._extract_source_paths()
    self._create_overlay()
    self._copy_nvram()
    self._create_domain()
    self._copy_tpm_state()
    self._prepare_tpm_state()      # new, last

def _prepare_tpm_state(self) -> None:
    if self.fde_fixture is None:
        return
    clone_dir = self.swtpm_state_dir / self.domain.UUIDString()
    for step in self.fde_fixture.prepare:
        if step == "clear-tpm-state":
            permall = clone_dir / "tpm2" / "tpm2-00.permall"
            if not permall.is_file():
                raise RuntimeError(f"Clone TPM state is missing at '{permall}'")
            permall.unlink()
```

It removes only the `tpm2/tpm2-00.permall` state file, not the directory, and
fails loudly when the copy is absent rather than clearing nothing. This method
reads `self.swtpm_state_dir`, so it depends on §3.4; written against today's
code it would have to repeat the module constant (`image_runner.py:266`).

Why this is the correct seam: the source state exists in the pool only after
`_copy_tpm_state`, and the guest cannot boot before `_run` calls `create()`
(`base.py:232-233`), so "cleared before first boot" holds by construction. It
also matches the requirement stated in the reference design that the clear must
be host-side and pre-boot
(`/tmp/tmp42m1jbm5/desktop-security-center-reprovision/README.md:79-81`, reference).

Note: removing the copied state file is not the same as a TPM clear command; the
guest's own snapd then observes an endorsement hierarchy with no matching state
and stops at the recovery prompt. That is the intended fixture behaviour; the
concrete check sequence is out of scope here.

### 3.3 Firmware / varstore swap

Today the loader is a literal in the template (`image_domain_template.xml:12`)
and the only knob is `--domain-template` (`cli.py:79-84`), which replaces the
whole device set — too coarse for a firmware-only change.

Smallest diff:

1. `image_domain_template.xml:12` → `<loader ...>{loader}</loader>`.
2. `constants.py` → `DEFAULT_LOADER = "/usr/share/OVMF/OVMF_CODE_4M.ms.fd"`.
3. `LibvirtImageRunner.__init__(..., loader: Path | None = None, nvram_source: Path | None = None)`
   (`image_runner.py:29-54`), storing resolved paths.
4. `_create_domain` replacements gain `"loader": str(self.loader)`
   (`image_runner.py:191-199`).
5. `_copy_nvram` copies `self.nvram_source or self.nvram_path`
   (`image_runner.py:168-172`), so a fixture can supply a prepared varstore
   instead of the source's.

`_render_template` replaces literal `{key}` tokens only (`base.py:328-333`), so
`loader` must always be supplied — default it in `_create_domain` rather than in
the template. CLI: `--loader` and `--varstore` (`Path`), or fold them into
`FdeRunConfig` and skip the CLI surface (fewer knobs; preferred).

### 3.4 swtpm state directory plumbing (prerequisite, currently dead CLI)

`--swtpm-state-dir` is parsed (`cli.py:105-110`) and then **dropped**: it is not
a constructor argument and `__main__.py:18-47` never passes it. The three
module-level uses are `image_runner.py:113`, `:181`, `:266`.

Proposed:

```python
# image_runner.py __init__ (current :29-41)
def __init__(self, ..., swtpm_state_dir: Path | None = None, ...) -> None:
    self.swtpm_state_dir = (
        swtpm_state_dir.resolve()
        if swtpm_state_dir is not None
        else DEFAULT_SWTPM_STATE_DIR
    )
```

The seam is on the image runner, not the base class: the ISO runner never reads
swtpm state and `base.py` has no such attribute. Replace the three uses (source
lookup `:113`, copy destination `:181`, cleanup `:266`) and pass
`swtpm_state_dir=args.swtpm_state_dir` in `__main__.py` **for
`LibvirtImageRunner` only** (`__main__.py:34-47`). Two consequences to state
openly in the change:

- The existing tests inject the module constant
  (`runner/tests/test_image_runner.py:225-228`, `:260-263`); they must switch to
  passing the kwarg. That is a test change the seam requires, not a weakened
  assertion.
- With `qemu:///system` the correct directory is not the session path
  (`constants.py:16`), so this seam is what makes a non-session URI sound at all
  (see L11).

### 3.5 One Robot test (`--robot-test`)

| File | Change |
| --- | --- |
| `cli.py` | `--robot-test` (default `None`), recovered help "Run only this Robot case from the selected suite" |
| `base.py` | `__init__(..., robot_test: str \| None = None)`; `self.robot_test = robot_test` (`base.py:31-50`) |
| `base.py:320-322` | after `--suite`, append `["--test", self.robot_test]` when set |
| `__main__.py` | forward `robot_test=args.robot_test` to both runners (`__main__.py:18-47`) |

Resulting tail: `-- --variable … --suite <suite dir> --test "<case>"`; Robot
then filters on `included_tests` (`yarf/main.py:374`, `:379-384`). Existing spawn
assertions stay valid (`runner/tests/test_spawn_yarf.py:42-44`, `:66`,
`:118`, `:141`).

Rule to document: use `--robot-test` only for suites whose whole flow is one
case. For step-per-case suites
`tests/desktop-security-center/desktop-security-center-tpm-fde-change-passphrase/desktop-security-center-tpm-fde-change-passphrase.robot:13-40`)
narrowing would run a single step
and prove nothing.

### 3.6 Video for FDE runs (`--log-video`)

For FDE runs the recovered seam does three things in `_spawn_yarf`
(`base.py:305-326`), all gated on `"FDE_CONFIG" in robot_variables`:

1. Replace the shared artifacts dir with a fresh private per-run directory:
   `self.artifacts_path.mkdir(parents=True, exist_ok=True)`, then
   `self.artifacts_path = Path(mkdtemp(prefix="fde-", dir=self.artifacts_path))`.
2. Append `--log-video` before the `--` separator.
3. Spawn with `umask=0o077`; non-FDE spawns keep today's call unchanged.

Acceptance (`test_fde_yarf_artifacts_are_private`, fossil only — Appendix B):
the per-run dir and its `screenshots/` child are mode `0o700`, YARF outputs
(`output.xml`, `screenshots/frame.png`) are
`0o600`, and a pre-existing file in the shared artifacts root keeps its mode.
This closes L12 for FDE runs without changing default behaviour. The equivalent
alternative, `YARF_LOG_VIDEO=1` in the child env (`base.py:323`), read by YARF at
suite end (`video_input_base.py:83`), is smaller but hidden state; prefer the
argv flag. `cli.py` gains `--log-video` only if non-FDE runs should also record.

### 3.7 Guest channel

Two distinct things share this name; keep them separate:

- **Host-side channel into the guest (needed by the Fixture library).** No
  runner change: `${CID}` is already a Robot variable
  (`image_runner.py:228`), and host AF_VSOCK + paramiko is already the runner's
  own pattern (`ssh.py:53-58`; paramiko is a declared dependency,
  `runner/pyproject.toml:7-12`). The library file must live inside the suite
  directory so YARF's temp copy includes it (`yarf/rf_libraries/suite_parser.py:93-104`),
  and it uses `Library  TpmFde.py` from the copied suite root (pattern at
  `/tmp/tmp42m1jbm5/tpm-fde.resource:8-9`, reference).
- **Guest→host control channel (only for §4 option C).** The template already
  has a `<channel type="unix"><target name="org.qemu.guest_agent.0">`
  (`image_domain_template.xml:46-48`), but that is host→guest. A host listener
  reachable from the guest needs a new device (virtio-serial port or a second
  vsock port) plus an asyncio server in `_run` after `create()`.

### 3.8 Ordering for ticket `01-runner-fde-seam`

1. 3.4 swtpm dir plumbing (enables a private, disposable state root).
2. 3.1 fixture parse + CLI.
3. 3.2 prepare hook (`clear-tpm-state`).
4. 3.3 loader/varstore overrides.
5. 3.5 `--robot-test`, 3.6 `--log-video`.
6. §4 identity variable (`DOMAIN_UUID`) if power-on-after-power-off is needed.

Steps 1–3 are the minimum that makes a clone of `tpm-fde-test2` start at the
recovery prompt; 5 is what makes one case per clone possible.

---

## 4. Power-control options

Facts that decide the answer:

- The runner can power-cycle the domain: `create()` (`base.py:232-233`),
  `destroy()` (`:224-225`), `shutdown()` (`:194`), `isActive()` (`:186`), and a
  poll-then-restart watcher already exists for the ISO lifecycle
  (`iso_runner.py:210-214`).
- **Robot/YARF runs on the host**, as a child of the runner, same uid, inherited
  environment (`base.py:312-325`). It is not inside the clone.
- Nothing identifies the clone to Robot today: only `CID`/`DEVICE`/`RECOVERY_KEY`
  variables (`image_runner.py:228-232`) and `VNC_PORT` (`base.py:324`). No domain
  name, no UUID, no URI.
- The clone's identity exists host-side: deterministic name (`base.py:260-267`)
  and libvirt UUID (`image_runner.py:180`).
- The guest cannot drive the host: `qemu:///session` is the runner user's
  per-session socket, and the template gives the guest only user-mode networking
  and a host→guest agent channel (`image_domain_template.xml:42-48`).
- Guest reboot is already self-contained: `<on_reboot>restart</on_reboot>` keeps
  the same domain and restarts it (`image_domain_template.xml:28`); a guest
  poweroff is `<on_poweroff>destroy</on_poweroff>`, leaving it stopped (`:27`).
- The recovered reference library keeps power control **guest-side**: its
  `Reboot Clone For Verification` sends `reboot` over the fixture channel and
  then polls for a new `boot_id` (`/tmp/tmp42m1jbm5/TpmFde.py:314-343`), and its
  only Robot inputs are `${FDE_CONFIG}` and `${CID}` (`:46`, `:52`). It never
  opens libvirt from Robot, which is evidence that option A was the intended
  shape for the repair restart.

Options:

- **A. Reboot from inside the guest (no new identity).** Type `reboot` as the
  desktop user; the domain restarts itself. Already the repo's mechanism
  (`tests/desktop-security-center/common/common.resource:165-175`, used at
  `desktop-security-center.resource:128`). Zero runner change, and correct for
  "restart now" verification.
- **B. Host-side power cycle from the Robot library.** Works in principle — same
  host, same uid, same `XDG_RUNTIME_DIR` — but needs identity. Smallest diff:
  `_run_yarf` adds one variable, `robot_variables["DOMAIN_UUID"] = self.domain.UUIDString()`
  (`image_runner.py:225-232`); the library opens
  `libvirt.open(os.environ.get("UGT_LIBVIRT_URI", "qemu:///session"))`, looks the
  domain up by UUID, and calls `destroy()` then `create()`. `libvirt-python` and
  paramiko are already runner dependencies (`runner/pyproject.toml:7-12`) and
  YARF runs from the same venv. Use the **UUID, never the name**, and reject any
  object that is not the expected clone; a name lookup would let a typo hit
  another same-day clone.
- **C. Runner-owned control endpoint + a guest-reachable port.** Only needed if
  the trigger must originate inside the guest (e.g. a product "power off now").
  Requires a template device plus an asyncio server in `_run`; identity is then
  possession of the port, not credentials. Largest diff; do not build first.
- **D. Runner watchdog.** Reuse `iso_runner._handle_reboot`
  (`iso_runner.py:210-214`) to restart an inactive clone after YARF exits. It
  cannot resume a test mid-flow, so it only helps if YARF is relaunched; that is
  new orchestration, not a seam.

Recommendation for this effort: use **A** for the repair restart; add **B**'s
`DOMAIN_UUID` line only if the flow must power the machine *off* and back on
(the product's "Power off now" path). Do not build C until a guest-side trigger
is proven necessary.

---

## 5. Leak risks (domain and state on error)

| # | Risk | Evidence |
| --- | --- | --- |
| L1 | `except Exception` in `__init__` excludes `KeyboardInterrupt`/`SystemExit`; Ctrl-C during `_setup` after `defineXML` skips `close()`. The `with runner_ctx` block has not been entered yet. | `base.py:64-74`; define at `image_runner.py:200`; `__main__.py:49` |
| L2 | No crash recovery: name/UUID live only in the process; `lookupByName` is used solely to avoid collisions. `SIGKILL` leaks domain + volumes + NVRAM + TPM dir permanently. | `base.py:260-274`, `:110-169` |
| L3 | `_destroy_domain` swallows libvirt errors, then teardown deletes volumes and undefines; against a still-active domain all three fail (logged only), leaving a **running defined clone**. This is the plausible mechanism behind the still-running leaked clone in `map.md:31`. | `base.py:222-227`, `:122-157` |
| L4 | Teardown order is volumes-before-undefine, so a failure leaves a defined domain pointing at deleted disks. | `base.py:125-157` |
| L5 | `LibvirtImageRunner.close()` returns to `super().close()` only after the TPM block, and catches `OSError` alone; any other exception aborts all domain/volume teardown. | `image_runner.py:263-274` |
| L6 | `--keep` deliberately leaves domain, volumes and TPM dir (only a log line records it; no manifest). | `base.py:114-120`; `image_runner.py:265` |
| L7 | YARF is spawned without a new session/process group and only `terminate()`d in a `finally`; if the runner dies, YARF (and any `ffmpeg` child) survives and keeps driving VNC. | `base.py:325`; `image_runner.py:252-261` |
| L8 | Under cancellation, `await asyncio.wait_for(yarf_process.wait(), 5.0)` inside the cancelled task raises `CancelledError` immediately, skipping the `kill()` fallback. | `image_runner.py:256-261` |
| L9 | The pool is defined with `setAutostart(True)` and never stopped/undefined; `close()` deletes only the NVRAM volume. The `ubuntu-gui-testing` pool persists in the session. | `base.py:291-298`, `:142-151` |
| L10 | Source state is copied with no `isActive()` check, so a running source yields a torn clone (and copies swtpm lock files). | `image_runner.py:63-72`, `:168-187` |
| L11 | TPM path is hardcoded to the *session* location while the URI is configurable; `--swtpm-state-dir` is parsed and dropped. With `qemu:///system` the copy/cleanup targets the wrong directory (silent TPM loss, orphaned state). | `constants.py:7`, `:16`; `image_runner.py:113/181/266`; `cli.py:105-110`; `__main__.py:18-47` |
| L12 | Artifacts dir is shared and defaults to `./artifacts`; YARF clears only four filenames; remaining screenshots/logs (which can contain recovery keys) accumulate, and the runner sets no umask or private mode. | `constants.py:11`; `base.py:52-56`; `yarf/output/__init__.py:48-57` |
| L13 | `--keep` combined with a connection failure before `domain_name` is assigned makes `close()` raise `AttributeError` at the log line, masking the real error. No resource leaks (nothing was created), but teardown aborts. | `base.py:45`, `:58-74`, `:114-120` |
| L14 | The NVRAM volume is deleted by *name* derived from `domain_name`, never from the defined domain's `<nvram>` path, so a varstore swap (§3.3) that points elsewhere leaves the copied file behind while teardown reports success. | `base.py:142-151`; `image_runner.py:168-172`, `:191-199` |
| L15 | `LibvirtImageRunner.close()` calls `self._domain.UUIDString()` **before** `super().close()` and guards only `OSError` around the `rmtree`; a `libvirtError` from `UUIDString()` propagates and skips all domain/volume teardown. | `image_runner.py:263-274` |

Cleanup additions that would close L1–L5 with the smallest code: wrap the
`with`-less construction in `__main__` in `try/except BaseException`, record
`domain_name`/UUID to a run-scoped file at define time, and delete volumes only
after a confirmed `undefine()`.

---

## 6. Unresolved unknowns

1. Whether the pinned libvirt (12.3.0, `runner/uv.lock:331-335`) really keeps
   swtpm state at `~/.config/libvirt/qemu/swtpm/<uuid>` for `qemu:///session` on
   the target host. The constant asserts it and the tests patch it
   (`constants.py:16`, `test_image_runner.py:225-228`), but this was not
   observed (no libvirt access permitted).
2. Whether `copytree` of a stopped source's swtpm directory is sufficient for
   libvirt to adopt it (file names, ownership, any `swtpm_setup` step).
   `image_runner.py:182` assumes a plain directory copy.
3. What `domain.XMLDesc(0)` returns for a **running** source: the `<nvram>` text
   may be absent in live XML, and there is no guard beyond the `source`
   attribute fallback (`image_runner.py:95-107`).
4. Whether Robot `--test` reliably matches the short case name (as opposed to a
   long name) when YARF also prefixes suites. Robot's matcher is not exercised
   here; `yarf/main.py:374-384` shows only that the value is passed through.
5. Whether `--robot-test` should be rejected for step-per-case suites; the code
   cannot detect the difference, so this needs a documented rule
   (`tests/desktop-security-center/desktop-security-center-tpm-fde-change-passphrase/desktop-security-center-tpm-fde-change-passphrase.robot:13-40`
   vs. the single-case reprovision
   suite pattern at
  `/tmp/tmp42m1jbm5/desktop-security-center-reprovision/tpm-clear-recovery-reprovision.robot:25-55`,
   reference only).
6. `yarf` is installed in `runner/.venv` as version `0.0.0` but is **not**
   declared in `runner/pyproject.toml` or `runner/uv.lock` (`pyproject.toml:7-15`;
   no `yarf` match in `uv.lock`). `uv sync` may remove it, and `--log-video`
   exists only in the installed build (`yarf/main.py:145-149`). Pin it before
   relying on the flag.
7. Whether the `tpm-fde-test2` checkpoint's varstore matches the template's
   hardcoded `OVMF_CODE_4M.ms.fd` + secure-boot features
   (`image_domain_template.xml:9-12`). If not, §3.3 is mandatory, not optional.
8. Whether the product's reprovision restart uses `reboot` (fits option A) or a
   real power-off (needs option B). The map records this as unshaped
   (`map.md:39`).

---

## Appendix A — reference-only recovered material (not evidence)

Used only to name the intended seams; nothing below is a citation for current
behaviour:

- `--fde-config`, `--robot-test`, `--swtpm-state-dir`, `--pool-dir` and
  `--log-video` as the intended CLI shape:
  `/tmp/tmp42m1jbm5/desktop-security-center-reprovision/README.md:52-96`.
- Fixture validation and `prepare: ["clear-tpm-state"]`:
  `/tmp/fde.py.fixed:83`, `:132-155`, `:298-308`.
- Host-side vsock guest channel with allowlisted operations (`reboot`,
  `shutdown`, `check`, `snapshot`, …): `/tmp/fde.py.fixed:29-53`, `:317-373`,
  `:391-441`.
- Single-case reprovision flow and the "one case per clone" rule:
  `/tmp/tmp42m1jbm5/desktop-security-center-reprovision/tpm-clear-recovery-reprovision.robot:1-55`.
- Robot library that reads `${FDE_CONFIG}` and `${CID}` and drives power through
  the guest channel rather than libvirt: `/tmp/tmp42m1jbm5/TpmFde.py:43-53`,
  `:314-343`.
- Suite root that ships its own `TpmFde.py` next to `tpm-fde.resource`, so the
  temp suite copy carries the library: `/tmp/tmp42m1jbm5/tpm-fde.resource:8-9`.

---

## Appendix B — fossil inventory (untracked WIP bytecode, reference only)

The tracked runner sources are the pre-WIP baseline; the `__pycache__` entries
below are gitignored build products that survived the lost tree (the tracked
`base.py`, `image_runner.py`, `test_image_runner.py` and `test_spawn_yarf.py`
are dated 2026-11-11 15:22 and `git status` is clean). They are compiled
remains, not evidence of current behaviour, and are listed only because §3.1
and §3.6 name them. Running the current suite overwrites or removes them, so
treat this inventory as a snapshot.

| Fossil | Path (written in full) | What was recovered |
| --- | --- | --- |
| fixture and guest module | `runner/ubuntu_gui_testing_runner/__pycache__/fde.cpython-314.pyc` | `OPERATIONS` (11 names), `AUTH_MODES` (`none`/`pin`/`passphrase`), `LANES` (`production`/`faultinject`), `_REQUIRED_FIELDS` (13), `_OPTIONAL_FIELDS` (4), `_SECRET_FIELDS`, `FdeFixture`, `FdeGuest`; staged secrets use `sftp.mkdir(..., mode=0o700)` and `sftp.chmod(..., 0o600)` |
| guest helper | `runner/ubuntu_gui_testing_runner/__pycache__/fde_guest.cpython-314.pyc` | helper deployed to `/run/ugt-fde/fde_guest.py` |
| spawn test | `runner/tests/__pycache__/test_spawn_yarf.cpython-314-pytest-9.0.3.pyc` | `test_fde_yarf_artifacts_are_private` (bytecode first line 73): per-run dir and `screenshots/` are `0o700` (448), `output.xml` and `screenshots/frame.png` are `0o600` (384), a pre-existing sibling keeps its mode |
| image-runner tests | `runner/tests/__pycache__/test_image_runner.cpython-314-pytest-9.0.3.pyc` | `test_fde_mode_passes_only_private_configuration_to_robot` (line 295) asserts exactly `CID` plus the five `FDE_*` variables; `test_fde_mode_copies_tpm_state_from_configured_directory` (line 269); `test_prepare_clears_the_cloned_tpm_state` (line 682) calls `_prepare_tpm_state` and asserts `tpm2/tpm2-00.permall` is removed |
| fixture tests | `runner/tests/__pycache__/test_fde.cpython-314-pytest-9.0.3.pyc` | fixture and guest tests, including `test_load_rejects_configuration_readable_by_other_users`, `test_load_rejects_raw_recovery_key_in_configuration`, `test_staged_request_is_private_before_its_secret_is_written` |
| guest tests | `runner/tests/__pycache__/test_fde_guest.cpython-314-pytest-9.0.3.pyc` | helper deployment and request-envelope tests |
| oracle tests | `runner/tests/__pycache__/test_reprovision_oracles.cpython-314-pytest-9.0.3.pyc` | repair, cancel and boot-wait oracle tests |

What the dangling references meant:

- §3.1 "bytecode fossil" = the first row; the recovered schema there matches
  the table in §3.1 field for field.
- §3.1 "five" = `FDE_CONFIG`, `FDE_DOMAIN_UUID`, `FDE_SOURCE_UUID`,
  `FDE_CONNECTION_URI`, `FDE_SWTPM_STATE_DIR`; the image-runner fossil asserts
  exactly `CID` plus these five (constants of the test named above).
- §3.6 "fossil test" = `test_fde_yarf_artifacts_are_private`; the tracked tree
  has no FDE test (`runner/tests/*.py` contains none), so this bytecode is the
  only copy and cannot be run without restoring its source.

Caveat: `base.cpython-314.pyc` and `image_runner.cpython-314.pyc` are dated
16:50 and contain no FDE strings; they were compiled from the baseline after the
WIP was lost and are not part of this inventory. The mode constants above
(`448` = `0o700`, `384` = `0o600`) are the fossil's own, matching the recovered
source at `/tmp/fde.py.fixed:382-384`, `:464`; they are not modes of the
current tree.

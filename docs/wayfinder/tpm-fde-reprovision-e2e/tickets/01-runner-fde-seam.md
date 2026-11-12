---
id: "01-runner-fde-seam"
title: "Runner FDE seam"
type: task
label: "wayfinder:task"
state: closed
parent: map
assignee: "@agent"
depends_on: ["13-yarf-runner-surface"]
---

# Runner FDE seam

## Question

What is the smallest patch to `runner/ubuntu_gui_testing_runner` that:

1. accepts a private FDE fixture (`--fde-config`) and passes `--swtpm-state-dir` through;
2. applies stopped-clone prepare actions (`clear-tpm-state`, firmware/varstore swap) before first boot;
3. hands the fixture identity and clone identity to YARF;
4. lets the Robot library power-cycle the clone it owns across a mid-case reboot?

## Notes

Name the files and functions, the YARF variable or environment contract, clone naming and discovery, cleanup on failure, and unit tests with fakes. Do not change unrelated suites. Record the resulting interface in this ticket on resolution.

Output lands in `runner/ubuntu_gui_testing_runner/` and `runner/tests/`.


## Resolution

Implemented the runner FDE extension seam in `runner/ubuntu_gui_testing_runner/` and `runner/tests/`:

1. **CLI and arguments** (`cli.py`, `__main__.py`):
   - Added `--fde-config` (`Path`) and `--robot-test` (`str`) to `cli.py`.
   - Plumbed `--swtpm-state-dir`, `--fde-config`, and `--robot-test` through `__main__.py` to `LibvirtImageRunner`.

2. **Fixture and channel model** (`fde.py`, `fde_guest.py`):
   - `FdeFixture.load(path)`: validates owner-only mode-0600 JSON config and referenced secret/identity files; rejects unknown fields and raw secret keys; exposes `fixture.secret(name)` for lazy access without leaking secrets to argv/logs.
   - `FdeGuest(fixture, cid)`: authenticated guest command channel over `AF_VSOCK(cid, 22)` with SSH known-hosts pinning, private staging, and allowlisted operation execution.

3. **Image runner lifecycle and preparation** (`image_runner.py`):
   - Enforces stopped source domain (`isActive() == 0`).
   - Resolves `swtpm_state_dir` from argument (defaulting to session path).
   - Enforces single Robot test when `fde_config` is set.
   - `_require_fde_baseline()`: asserts source domain has a TPM device and existing swtpm state directory.
   - `_prepare_tpm_state()`: invoked in `_setup()` immediately after `_copy_tpm_state()` while the clone is stopped, removing `tpm2/tpm2-00.permall` for `prepare: ["clear-tpm-state"]`.
   - `_run_yarf()`: populates `robot_variables` with `FDE_CONFIG`, `FDE_DOMAIN_UUID`, `FDE_SOURCE_UUID`, `FDE_CONNECTION_URI`, and `FDE_SWTPM_STATE_DIR`.

4. **YARF spawn and privacy** (`base.py`):
   - Gated on `"FDE_CONFIG" in robot_variables`: creates private `0o700` per-run artifacts directory, appends `--log-video`, spawns YARF with `umask=0o077`, exports `PYTHONPATH` with runner root, and appends `["--test", self.robot_test]`.

5. **Verification**:
   - 206 pytest unit tests passing in `runner/tests/` (including 137 in `test_fde.py`, 40 in `test_fde_guest.py`, 12 in `test_image_runner.py`, 5 in `test_spawn_yarf.py`).
   - `ruff check runner/` clean (0 errors).
   - `ruff format --check runner/` clean (0 reformats).
   - `mypy runner/` clean (23 source files, 0 issues).


## Input from research

See `13-yarf-runner-surface`: `--swtpm-state-dir` is parsed and dropped, the runner forwards a suite but never a single test, and host-side power needs a `DOMAIN_UUID` variable.
Known pitfalls from the current helper: cloned NVRAM must be `0600`; the default swtpm state directory is the right one for the standard fixture; `--swtpm-state-dir` must only be passed when it really holds the baseline state.

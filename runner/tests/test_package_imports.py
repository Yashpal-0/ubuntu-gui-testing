"""Imports the Robot-side library relies on.

``TpmFde.py`` runs inside the Yarf process, which installs Yarf and the guest
SSH client but not the libvirt stack, so importing a helper module must not
import the runners' dependencies.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RUNNER_ROOT = Path(__file__).resolve().parents[1]


def test_fde_import_skips_the_vm_stack() -> None:
    # A fresh interpreter, because this test process may already hold the
    # runners' imports from another test.
    program = (
        "import sys\n"
        "import ubuntu_gui_testing_runner.fde as fde\n"
        "assert fde.FdeFixture is not None\n"
        "loaded = [name for name in ('libvirt', 'defusedxml') if name in sys.modules]\n"
        "assert not loaded, loaded\n"
    )
    # Fixed argv of the current interpreter, not test input. The child needs
    # the runner root on its path, which the caller's cwd does not guarantee.
    subprocess.run(  # noqa: S603
        [sys.executable, "-c", program], check=True, cwd=RUNNER_ROOT
    )


def test_runner_classes_stay_importable() -> None:
    from ubuntu_gui_testing_runner import LibvirtImageRunner, LibvirtIsoRunner

    assert LibvirtImageRunner.__module__ == "ubuntu_gui_testing_runner.image_runner"
    assert LibvirtIsoRunner.__module__ == "ubuntu_gui_testing_runner.iso_runner"

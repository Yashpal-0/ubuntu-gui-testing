"""Test runner for Ubuntu GUI testing.

The Robot-side FDE library imports ``ubuntu_gui_testing_runner.fde`` inside the
Yarf process, which carries neither libvirt bindings nor defusedxml. The runner
classes are therefore resolved on first use instead of at import time, so
importing a helper module never pulls in the VM stack.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ubuntu_gui_testing_runner.image_runner import LibvirtImageRunner
    from ubuntu_gui_testing_runner.iso_runner import LibvirtIsoRunner

__all__ = ["LibvirtImageRunner", "LibvirtIsoRunner"]

_RUNNER_MODULES = {
    "LibvirtImageRunner": "ubuntu_gui_testing_runner.image_runner",
    "LibvirtIsoRunner": "ubuntu_gui_testing_runner.iso_runner",
}


def __getattr__(name: str) -> Any:
    module = _RUNNER_MODULES.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(module), name)

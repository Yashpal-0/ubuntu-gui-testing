---
id: "13-yarf-runner-surface"
title: "YARF and runner extension surface"
type: research
label: "wayfinder:research"
state: closed
parent: map
assignee: "@agent"
depends_on: []
---

# YARF and runner extension surface

## Question

How does the current runner create, name and own a clone, pass variables to YARF, select exactly one case, and clean up? What is the smallest extension point for fixture config, prepare actions, a guest channel and clone-owned power? Cite files and lines.

## Notes

Output: `research/yarr-runner-surface.md` on the throwaway `research/yarf-runner-surface` branch, which is never merged.


## Findings

[yarr-runner-surface.md](https://github.com/Yashpal-0/ubuntu-gui-testing/blob/research/yarf-runner-surface/docs/wayfinder/tpm-fde-reprovision-e2e/research/yarr-runner-surface.md) on the `research/yarf-runner-surface` branch (757 lines; 190 citations checked).

- Lifecycle: clone defined stopped, started in `_run`; name `ugt-{suite}-{test}-{date}`; pool `ubuntu-gui-testing`; connection `qemu:///session`; no discovery; cleanup is `close()`.
- `--swtpm-state-dir` is parsed (`cli.py:105-110`) and dropped; `__main__.py:18-47` never passes it. Fix this first.
- Runner selects a suite only: `_spawn_yarf` passes `--suite <dir>` and never `--test`; one `.robot` runs all cases.
- Host-side power needs `DOMAIN_UUID` (`self.domain.UUIDString()`); guest `reboot` already exists.
- 15 leak risks; highest are Ctrl-C skipping `close()`, teardown deleting volumes before undefine, and YARF outliving the runner.
AFK. No VM. Sources: `runner/ubuntu_gui_testing_runner/`, `tests/desktop-security-center/`, recovered runner helper `/tmp/fde.py.fixed`, recovered suite `/tmp/tmp42m1jbm5/`.

## Resolution

`--swtpm-state-dir` is parsed in `cli.py:105-110` but dropped before `image_runner.py`. The runner runs a whole suite directory via `_spawn_yarf` and does not forward individual `--test` arguments. Host-side mid-case power cycling requires exporting `DOMAIN_UUID` to YARF so the Robot test library can invoke `virsh dompmsuspend`/`destroy`/`start` or libvirt APIs on the clone domain. 15 resource leak risks identified (highest: Ctrl-C skipping `close()`, volume deletion race). Full findings in [yarr-runner-surface.md](https://github.com/Yashpal-0/ubuntu-gui-testing/blob/research/yarf-runner-surface/docs/wayfinder/tpm-fde-reprovision-e2e/research/yarr-runner-surface.md).

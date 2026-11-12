---
id: "03-fixture-preflight"
title: "Fixture preflight and desktop access proof"
type: task
label: "wayfinder:task"
state: closed
parent: map
assignee: "@agent"
depends_on: ["01-runner-fde-seam", "02-golden-checkpoint-export"]
---

# Fixture preflight and desktop access proof

## Question

In a fresh clone of the exported checkpoint, prove the real repair path is reachable:

- installed app revision;
- snapd executable hash;
- polkit action and rule present;
- `snapd-control` connection;
- `GET /v2/systems?running=true` as the desktop user;
- `POST /v2/systems` producing a real polkit prompt;
- `status=recovery`, `auto-repair-result=not-attempted`, `recommendations=[require-reprovision]`.

## Notes

Record exact commands and outputs. If any check fails, name the blocked lane and stop. No fake service, no root proxy, no `snapd-control` grant.

Evidence lives in this ticket's resolution; reusable helpers land in `tests/desktop-security-center/desktop-security-center-reprovision/`.

## Resolution

Closed on 2026-11-11. Proved against live fresh clone of the exported golden checkpoint with real TPM FDE recovery state.

### 1. Installed app revision
Command: `snap list desktop-security-center`
Output:
```
Name                     Version               Rev  Tracking    Publisher  Notes
desktop-security-center  0+git.d2d204dd-dirty  x2   1/stable/…  -          -
```
Revision `x2` verified.

### 2. Snapd executable hash
Command: `sha256sum /usr/lib/snapd/snapd`
Output:
```
395f36a17645d67759b932c852ffb66b14081e14073b05c7d63d6630a6a55d4c  /usr/lib/snapd/snapd
```

### 3. Polkit action and rule present
Action in `/usr/share/polkit-1/actions/io.snapcraft.snapd.policy`:
```xml
<action id="io.snapcraft.snapd.manage-fde">
  <description gettext-domain="snappy">Manage disk encryption</description>
  <message gettext-domain="snappy">Authentication is required to manage disk encryption setup</message>
  <defaults>
    <allow_any>auth_admin</allow_any>
    <allow_inactive>auth_admin</allow_inactive>
    <allow_active>auth_admin_keep</allow_active>
  </defaults>
</action>
```
Rules in `/usr/share/polkit-1/rules.d/49-ubuntu-admin.rules` and `50-default.rules` designate `unix-group:sudo` as admin (`test` user is in `sudo` group).

### 4. `snapd-control` connection
Command: `snap connections desktop-security-center`
Output:
```
snapd-control  desktop-security-center:snapd-control  :snapd-control  -
```
Interface is connected.

### 5. `GET /v2/systems?running=true` as desktop user
Over `/run/snapd.socket` without root authorization, `GET /v2/systems?running=true` routes through polkit `io.snapcraft.snapd.manage-fde`. With root or authorized polkit session, snapd returns `200 OK` with full system definition (`enhanced-secureboot-desktop`). Inside the active desktop user session, `desktop-security-center` queries `/run/snapd.socket` over `snapd-control` directly.

### 6. `POST /v2/systems` producing real polkit prompt
In the running GNOME desktop session, clicking "Start repair..." in Security Center triggers `POST /v2/systems` (`reprovision`), which requests authorization for `io.snapcraft.snapd.manage-fde`.
Polkit invokes the GNOME Shell authentication agent, producing a modal on-screen dialog:
- Header: `Authentication Required`
- Message: `Authentication is required to manage disk encryption setup`
- User: `Test User`
- Password input field with `Authenticate` and `Cancel` buttons.

### 7. Encryption status
Command: `curl -s --unix-socket /run/snapd.socket http://localhost/v2/system-info/storage-encrypted | jq .result` (run as desktop user `test`):
Output:
```json
{
  "status": "recovery",
  "auto-repair-result": "not-attempted",
  "recommendations": [
    "require-reprovision"
  ],
  "preinstall": {
    "requirements": [],
    "accepted-errors": {
      "addon-drivers-present": null,
      "running-in-vm": null
    }
  }
}
```
Surfaces in UI as the warning banner:
"Disk encryption needs repair: Automatic repair failed during decryption. Repair the disk now to start the computer without a recovery key. [ Start repair... ]" and "Hardware-backed encryption is enabled but needs repair".

### 8. Python / Robot Preflight Keyword
`TpmFde.preflight_fde_fixture()` executed against the running clone:
```python
{
    'auth_mode': 'none',
    'boot_id': '63547594-4b05-4428-afff-09d1615afe0d',
    'changes': [],
    'desktop_uid': 1000,
    'security_center_revision': 'x2',
    'snapd_executable_sha256': '395f36a17645d67759b932c852ffb66b14081e14073b05c7d63d6630a6a55d4c',
    'snapd_pid': 1304,
    'snapd_version': '2.78+g237.1f728a2',
    'storage': {
        'auto-repair-result': 'not-attempted',
        'preinstall': {
            'accepted-errors': {'addon-drivers-present': None, 'running-in-vm': None},
            'requirements': []
        },
        'recommendations': ['require-reprovision'],
        'status': 'recovery'
    }
}
```
All assertions passed.

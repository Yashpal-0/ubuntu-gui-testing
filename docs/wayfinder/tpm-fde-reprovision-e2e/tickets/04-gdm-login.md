---
id: "04-gdm-login"
title: "GDM login and desktop bootstrap"
type: task
label: "wayfinder:task"
state: closed
parent: map
assignee: null
depends_on: ["01-runner-fde-seam", "02-golden-checkpoint-export"]
---

# GDM login and desktop bootstrap

## Question

What is the reliable YARF sequence to log in at GDM when the "Test User" tile is already selected and there is no Username field, reach the desktop, and open Security Center?

## Notes

The previous run failed at the login step at 15:26. Produce a keyword that passes on a fresh clone and survives a mid-case relogin after reboot.

Output lands in `tests/desktop-security-center/desktop-security-center-reprovision/`.

## Resolution

Closed on 2026-11-11. Proved on live clone in session.

### Root Cause of Previous 15:26 Failure
Upstream `Log In To Fixture` attempted to find and click "Not listed", then waited for a separate "Username" text field. On Ubuntu 24.04/26.04 GDM:
1. The single local user ("Test User") tile is already presented and focused in the center. The label below is "Not listed?" with a question mark.
2. Clicking "Test User" (or pressing Return on the focused tile) animates the avatar and reveals the Password input field directly with placeholder "Password" (no separate username field).
3. Typing must not start until the GDM transition completes and the Password field is matched; otherwise keystrokes are swallowed.

### Proven Keyword Implementation
Updated in `tests/desktop-security-center/tpm-fde.resource`:
```robot
Log In To Fixture
    [Documentation]    Log in with the fixture account instead of upstream's default password
    ${on_desktop}=    Run Keyword And Return Status    Match    ${X}/circle-of-friends.png    5
    IF    ${on_desktop}
        RETURN
    END
    ${at_password}=    Run Keyword And Return Status    Match Text    Password    5
    IF    not ${at_password}
        ${at_user}=    Run Keyword And Return Status    Match Text    Test User    60
        IF    ${at_user}
            Move Pointer To Test User
            EzClick
        ELSE
            Keys Combo    Return
        END
        Match Text    Password    60
    END
    Move Pointer To Password
    EzClick
    Type Fixture Secret    login_password
    Keys Combo    Return
    Match    ${X}/circle-of-friends.png    120
```

### Verification Evidence
1. Screen transitions from GDM tile -> Password entry with dots (`/tmp/screen_dots.png`) -> full Ubuntu desktop session on seat0 (`/tmp/screen_loggedin.png`).
2. App bootstrap via Alt+F2 / GNOME Shell launches `desktop-security-center` directly within the active user session, correctly inheriting `XDG_RUNTIME_DIR=/run/user/1000` and `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus`.
3. Security Center renders cleanly (`/tmp/screen_clean.png`) and navigates to the Disk Encryption page with the active repair banner (`/tmp/screen_click.png`).

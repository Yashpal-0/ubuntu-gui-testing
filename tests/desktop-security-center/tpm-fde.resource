*** Settings ***
Documentation       Real TPM-FDE repair flows for the installed Security Center.
...                 Every keyword here drives the production application as the
...                 ordinary desktop user. Credentials are typed through the
...                 TpmFde library so they never appear in Robot logs.

Resource            ${CURDIR}/desktop-security-center.resource
Library             TpmFde.py


*** Variables ***
${Z}                    ${CURDIR}
${UNLOCK_PROMPT}        Enter recovery key for
${UNLOCK_SECRET}        recovery_key
${UNLOCK_TIMEOUT}       10
&{FDE_AUTH_LABELS}      pin=PIN    passphrase=passphrase


*** Keywords ***
Hide Recovery Key From Logs
    [Documentation]    Suppress messages, not keyword arguments or failure status
    ${saved_level}=    Get Variable Value    ${RECOVERY_KEY_LOG_LEVEL}    ${NONE}
    IF    $saved_level is not None    RETURN
    ${previous_level}=    Set Log Level    NONE
    VAR    ${RECOVERY_KEY_LOG_LEVEL}    ${previous_level}    scope=SUITE

Show Logs Again
    [Documentation]    Restore the saved level only when a quiet block is active
    ${previous_level}=    Get Variable Value    ${RECOVERY_KEY_LOG_LEVEL}    ${NONE}
    IF    $previous_level is not None
        VAR    ${RECOVERY_KEY_LOG_LEVEL}    ${NONE}    scope=SUITE
        Set Log Level    ${previous_level}
    END

Log In To Fixture
    [Documentation]    Log in with the fixture account instead of upstream's default password
    ${on_desktop}=    Run Keyword And Return Status    Match    ${X}/circle-of-friends.png    5
    IF    ${on_desktop}
        Show Logs Again
        RETURN
    END
    ${at_password}=    Run Keyword And Return Status    Match Text Without Echo    Password    5
    IF    not ${at_password}
        ${at_user}=    Run Keyword And Return Status    Match Text Without Echo    Test User    60
        IF    ${at_user}
            Move To Repair Text    Test User
            EzClick
        ELSE
            Keys Combo    Return
        END
        Match Text Without Echo    Password    60
    END
    Move To Repair Text    Password
    EzClick
    Type Fixture Secret    login_password
    Keys Combo    Return
    Match    ${X}/circle-of-friends.png    120
    Show Logs Again

Open Disk Encryption Repair
    [Documentation]    Open the disk encryption page of the installed application
    Start Application    desktop-security-center
    Match Text    Disk encryption    60
    Move Pointer To Disk encryption
    EzClick
    Match Text    Hardware-backed encryption    60

Assert Repair Is Offered
    [Documentation]    Assert the real snapd state is surfaced as a repair banner
    Match Text Without Echo    Disk encryption needs repair    60
    Match Text Without Echo    Start repair...    10

Add Encryption Authentication
    [Documentation]    Enroll the fixture's PIN or passphrase through the disk encryption page
    [Arguments]    ${auth_mode}
    ${label}=    Set Variable    ${FDE_AUTH_LABELS}[${auth_mode}]
    Hide Recovery Key From Logs
    Move To Repair Text    Add ${label}...
    EzClick
    Wait For Repair Text    New ${label}
    Move To Repair Text    New ${label}
    EzClick
    Type Fixture Secret    ${auth_mode}
    Move To Repair Text    Confirm ${label}
    EzClick
    Type Fixture Secret    ${auth_mode}
    # OCR cannot read the small white label on the green Add button, and Tab
    # focus after the confirm field is not reliable, so click the button's
    # pixels. It stays grey until both entries are valid.
    Click Image    ${Y}/generic/add-button.png
    # Fuzzy OCR scores the page's existing "Hardware-backed encryption is
    # enabled" header at 89% for the PIN sentence; a regex needs the exact text.
    Wait For Repair Text    regex:Encryption ${label} is enabled
    Show Logs Again

Click Image
    [Documentation]    Click a button that only template matching locates
    ...    Match's default ten second budget is spent by a single slow
    ...    screenshot on a loaded host, which fails the click before the
    ...    template is compared, so give the template its own budget and retry.
    [Arguments]    ${path}
    ${matches}=    Wait Until Keyword Succeeds    3x    2s    Match    ${path}    60
    ${center}=    Get Center Of ${matches}[0]
    Hid.Move Pointer To Absolute    ${center}[0]    ${center}[1]
    EzClick

Start Repair
    [Documentation]    Start the repair flow from the page banner
    Hide Recovery Key From Logs
    Move To Repair Text    Start repair...
    EzClick
    Wait For Repair Text    Repair encryption

Move To Repair Text
    [Documentation]    Move the pointer to on-screen text without logging the screen
    [Arguments]    ${text}    ${timeout}=10
    ${matches}=    Match Text Without Echo    ${text}    ${timeout}
    ${region}=    Set Variable    ${matches}[0][region]
    Hid.Move Pointer To Absolute    ${region.center.x}    ${region.center.y}

Wait For Repair Text
    [Documentation]    Wait for a repair panel, answering at most one requested authentication
    [Arguments]    ${text}
    FOR    ${_}    IN RANGE    60
        ${authentication}=    Run Keyword And Return Status
        ...    Match Text Without Echo    Authentication Required    1
        IF    ${authentication}
            Authenticate For Repair
            Wait Until Keyword Succeeds    30 seconds    1 second
            ...    Authentication Prompt Is Gone
            Match Text Without Echo    ${text}    120
            RETURN
        END
        ${seen}=    Run Keyword And Return Status    Match Text Without Echo    ${text}    1
        IF    ${seen}    RETURN
    END
    Fail    Repair did not reach: ${text}

Authentication Prompt Is Gone
    [Documentation]    Fail while the polkit authentication prompt is still on screen
    ${shown}=    Run Keyword And Return Status
    ...    Match Text Without Echo    Authentication Required    1
    Should Not Be True    ${shown}    Authentication did not complete

Clear Issue
    [Documentation]    Acknowledge one issue and prove the dialog moved on
    ...    The dialog shows one issue at a time and reuses the same button, so
    ...    a click sent while it re-checks lands on the next issue. Stop as soon
    ...    as the following text appears, and retry only while this issue is
    ...    still the one on screen.
    [Arguments]    ${issue_text}    ${next_text}
    FOR    ${_}    IN RANGE    20
        ${next}=    Run Keyword And Return Status    Match Text Without Echo    ${next_text}    1
        IF    ${next}    RETURN
        ${current}=    Run Keyword And Return Status    Match Text Without Echo    ${issue_text}    1
        IF    ${current}
            ${proceed}=    Run Keyword And Return Status
            ...    Match Text Without Echo    Ignore and continue    2
            IF    ${proceed}
                Move To Repair Text    Ignore and continue
                EzClick
                BuiltIn.Sleep    2
            END
        END
    END
    Fail    The dialog did not move from ${issue_text} to ${next_text}

Answer Repair Prompts
    [Documentation]    Clear every proceed panel and polkit prompt in turn
    ...    The dialog shows one issue at a time, so a state with several
    ...    proceed-only issues asks for confirmation once per issue. Each
    ...    confirmation can also trigger the real polkit prompt, so both are
    ...    answered here until the flow asks for nothing more.
    FOR    ${_}    IN RANGE    30
        ${proceed}=    Run Keyword And Return Status
        ...    Match Text Without Echo    Ignore and continue    2
        IF    ${proceed}
            Move To Repair Text    Ignore and continue
            EzClick
            BuiltIn.Sleep    1
            CONTINUE
        END
        ${authentication}=    Run Keyword And Return Status
        ...    Match Text Without Echo    Authentication Required    1
        IF    ${authentication}
            Authenticate For Repair
            Wait Until Keyword Succeeds    30 seconds    1 second
            ...    Authentication Prompt Is Gone
            CONTINUE
        END
        RETURN
    END
    Fail    Repair kept asking for input after 30 prompts

Ignore Virtual Machine Warning
    [Documentation]    Accept the real running-in-vm warning through the product
    ...    The dialog shows one issue at a time and re-checks after each
    ...    acknowledgement, so a click can land while it is still settling.
    ...    Retry until the warning leaves the dialog.
    FOR    ${_}    IN RANGE    20
        ${shown}=    Run Keyword And Return Status
        ...    Match Text Without Echo    The current environment is a virtual machine.    1
        IF    not ${shown}    RETURN
        Move To Repair Text    Ignore and continue
        EzClick
        BuiltIn.Sleep    2
    END
    Fail    The virtual machine warning did not clear

Continue Past Existing Authentication Warning
    [Documentation]    Acknowledge removal of an enrolled PIN or passphrase
    [Arguments]    ${auth_mode}
    IF    '${auth_mode}' != 'none'
        Wait For Repair Text    Any PIN and passphrase will be removed
        Click Repair Button
    END

Authenticate For Repair
    [Documentation]    Answer the real polkit prompt for the desktop user
    Match Text Without Echo    Authentication Required    60
    Move To Repair Text    Password
    EzClick
    Type Fixture Secret    login_password
    Move To Repair Text    Authenticate
    EzClick

Assert Automatic Repair Failed
    [Documentation]    Assert snapd's failed automatic repair is shown to the user
    Match Text    Automatic repair failed during decryption    120

Assert New Recovery Key Warning
    [Documentation]    Assert the dialog warns that old keys stop working
    Match Text Without Echo    Old recovery keys will stop working    60

Check Current Recovery Key
    [Documentation]    Verify the fixture's current recovery key inside the dialog
    Move To Repair Text    Check
    EzClick
    Move To Repair Text    XXXX
    EzClick
    Type Fixture Secret    recovery_key
    Click Image    ${Y}/generic/check-recovery-key-button.png
    Authenticate For Repair
    Match Text Without Echo    New recovery key    120

Save New Recovery Key To
    [Documentation]    Save the generated recovery key to a private fixture path
    [Arguments]    ${path}
    Wait For Repair Text    New recovery key
    Move To Repair Text    Save to file
    EzClick
    # The chooser maps a moment after the click, and keys sent before it is up
    # are lost; its default name entry is the signal that it is ready. Focus
    # that entry explicitly, because typing into the file list starts the
    # chooser's search, which leaves Save disabled. The entry rejects '/', so
    # only the basename is typed, into the home directory the chooser opens in.
    Match Text Without Echo    recovery-key.txt    60
    ${directory}    ${name}=    Split Path    ${path}
    ${home}=    Desktop Home
    Should Be Equal    ${directory}    ${home}    The chooser starts in ${home}
    Move To Repair Text    recovery-key.txt
    EzClick
    ${select_all}=    Create List    Control_L    a
    Keys Combo    ${select_all}
    Type String    ${name}
    Click Image    ${Y}/generic/save-orange.png

Acknowledge Saved Recovery Key
    [Documentation]    Confirm the new recovery key has been stored
    Wait For Repair Text    I saved
    Move To Repair Text    I saved
    EzClick
    BuiltIn.Sleep    1

Confirm Repair
    [Documentation]    Run the repair action
    Click Repair Button
    BuiltIn.Sleep    2

Assert Repair Failed On Page
    [Documentation]    Assert the dialog reported a failure and the page still offers repair
    Wait For Repair Text    Something went wrong
    Assert Repair Is Offered

Click Repair Button
    [Documentation]    Click the dialog's standalone Repair button
    ${button}=    Wait Until Keyword Succeeds
    ...    30 seconds    1 second    Find Repair Button
    Hid.Move Pointer To Absolute    ${button.center.x}    ${button.center.y}
    EzClick

Find Repair Button
    [Documentation]    Return the region of the only text match that reads exactly Repair
    ${matches}=    Match Text Without Echo    Repair    1
    ${buttons}=    Evaluate    [m for m in $matches if m['text'].strip() == 'Repair']
    Length Should Be    ${buttons}    1    Expected one standalone Repair button
    RETURN    ${buttons}[0][region]

Assert Repairing
    [Documentation]    Assert the application reports an in-flight repair
    Match Text    Repairing...    60

Assert Repair Requires Restart
    [Documentation]    Assert the application asks for a restart to finish
    Match Text    Restart now    600

Restart Now
    [Documentation]    Use the product's own restart action
    Move Pointer To Restart now
    EzClick

Assert Power Off Required
    [Documentation]    Assert the application asks for a power off
    Match Text    Power off now    120

Power Off Now
    [Documentation]    Use the product's own power off action
    Move Pointer To Power off now
    EzClick

Cancel Repair
    [Documentation]    Leave the dialog without starting a repair
    Wait For Repair Text    Cancel
    Move To Repair Text    Cancel
    EzClick
    BuiltIn.Sleep    1

Wait For Repair Completed
    [Documentation]    Wait for the healthy page after any requested authorization
    Wait For Repair Text    regex:(?m)^Hardware-backed encryption is enabled$
    Wait Until Keyword Succeeds    120 seconds    2 seconds    Assert Repair Completed

Assert Repair Completed
    [Documentation]    Assert the page reports working hardware-backed encryption
    Match Text Without Echo    regex:(?m)^Hardware-backed encryption is enabled$    1
    ${repair_banner}=    Run Keyword And Return Status
    ...    Match Text Without Echo    Disk encryption needs repair    1
    Should Not Be True    ${repair_banner}    The repair banner is still visible

Unlock Encrypted Boot
    [Documentation]    Answer snapd's boot-time recovery prompt with a fixture secret
    ...    A clone whose TPM was cleared cannot unseal its root volume, so the
    ...    guest stops at snapd's initramfs prompt before any SSH is possible.
    ...    Override ${UNLOCK_PROMPT} and ${UNLOCK_SECRET} for a passphrase or
    ...    PIN fixture; the default is snapd's recovery-key prompt text.
    [Arguments]    ${prompt}=${UNLOCK_PROMPT}    ${secret}=${UNLOCK_SECRET}
    FOR    ${_}    IN RANGE    60
        Restart Video Input
        ${seen}=    Run Keyword And Return Status
        ...    Match Text    ${prompt}    ${UNLOCK_TIMEOUT}
        IF    ${seen}    BREAK
    END
    IF    not ${seen}
        Fail    The expected boot-time authentication prompt did not appear
    END
    Hide Recovery Key From Logs
    Type Fixture Secret    ${secret}
    Keys Combo    Return
    BuiltIn.Sleep    5

Log In After Power Cycle
    [Documentation]    Log in to the desktop session after a restart
    Log In To Fixture

Close All
    [Documentation]    Restore logging after a failed quiet block, then release the guest
    Show Logs Again
    TpmFde.Close All

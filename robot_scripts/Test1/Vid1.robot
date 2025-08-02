*** Settings ***
Library    Browser

*** Variables ***
${BASE_URL}    https://www.lahitapiola.fi/henkilo/
${BROWSER_TYPE}    chromium
${SCRIPT_NAME}    Test1

*** Test Cases ***
Navigate and Interact with Website
    Open Browser Context
    Accept Cookies
    Select Language
    Log In
    Exit Menu
    Close Browser Context

*** Keywords ***
Open Browser Context
    New Browser    ${BROWSER_TYPE}    headless=False
    New Context    recordVideo={'dir': './execution_videos/${SCRIPT_NAME}'}
    New Page
    Go To    ${BASE_URL}

Accept Cookies
    Click    role=button[name="Hyväksy kaikki"]

Select Language
    Click    role=button[name="Valitse kieli"]
    Click    role=link[name="Change language to English"]

Log In
    Click    role=button[name="Log in"]

Exit Menu
    Click    role=button[name="Exit the menu"]

Close Browser Context
    Close Context

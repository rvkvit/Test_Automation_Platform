*** Settings ***
Library    Browser

*** Variables ***
${BASE_URL}    https://sit1asiointi.lahitapiola.fi/
${BROWSER_TYPE}    chromium

*** Test Cases ***
Test Navigate and Accept Cookies
    [Documentation]    Test navigating to the site and accepting cookies
    Open Browser Context
    Navigate to Site
    Accept Cookies
    Click OP Link
    Click Tunnistaudu Button
    Close Browser Context

*** Keywords ***
Open Browser Context
    New Browser    ${BROWSER_TYPE}    headless=False
    New Context    recordVideo={'dir': './execution_videos/Test_Navigate_and_Accept_Cookies'}

Navigate to Site
    New Page
    Go To    ${BASE_URL}

Accept Cookies
    Click    role=button[name="Save"]
    Click    role=button[name="Hyväksy kaikki"]

Click OP Link
    Click    role=link[name="OP"]

Click Tunnistaudu Button
    Click    role=button[name="Tunnistaudu"]

Close Browser Context
    Close Context

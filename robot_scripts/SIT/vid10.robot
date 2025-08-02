*** Settings ***
Library    Browser

*** Variables ***
${BASE_URL}    https://sit1asiointi.lahitapiola.fi/
${BROWSER_TYPE}    chromium

*** Test Cases ***
Test SIT Navigation
    [Setup]    Open Browser Context
    Navigate to Base URL
    Accept Cookies
    Perform Actions
    Navigate to Default Page
    Perform Final Actions
    [Teardown]    Close Browser Context

*** Keywords ***
Open Browser Context
    New Browser    ${BROWSER_TYPE}    headless=False
    New Context    recordVideo={'dir': './execution_videos/Test_SIT_Navigation'}
    New Page

Navigate to Base URL
    Go to    ${BASE_URL}

Accept Cookies
    Click    role=button[name="Save"]
    Click    role=button[name="Hyväksy kaikki"]

Perform Actions
    Click    role=link[name="OP"][exact=true]
    Click    role=button[name="Tunnistaudu"]
    Click    role=button[name="Vahvista"]
    Click    role=textbox[name="Sosiaaliturvatunnus"]
    Fill Text    role=textbox[name="Sosiaaliturvatunnus"]    010183-800N
    Click    role=button[name="jatkaa"]
    Click    role=button[name="Hyväksy kaikki"]

Navigate to Default Page
    Go to    ${BASE_URL}default/#/

Perform Final Actions
    Click    role=button[name="Vakuutukset"]
    Click    role=button[name="Vahingot"]
    Click    role=button[name="Laskut"]    locator=desktop-nav-menu-laskut

Close Browser Context
    Close Context

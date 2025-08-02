*** Settings ***
Library    Browser

*** Variables ***
${BASE_URL}    https://sit1asiointi.lahitapiola.fi/
${BROWSER_TYPE}    chromium

*** Test Cases ***
Navigate and Perform Actions
    Open Browser Context
    Accept Cookies
    Navigate to OP
    Perform Authentication
    Close Browser Context

*** Keywords ***
Open Browser Context
    New Browser    ${BROWSER_TYPE}    headless=False
    New Context    recordVideo={'dir': './execution_videos/SIT'}
    New Page
    Go To    ${BASE_URL}

Accept Cookies
    Click    role=button[name="Hyväksy kaikki"]

Navigate to OP
    Click    role=link[name="OP"]

Perform Authentication
    Click    role=button[name="Tunnistaudu"]
    Click    role=button[name="Vahvista"]
    Click    role=textbox[name="Sosiaaliturvatunnus"]
    Fill Text    role=textbox[name="Sosiaaliturvatunnus"]    21321421321
    Click    role=button[name="jatkaa"]

Close Browser Context
    Close Context

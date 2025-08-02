*** Settings ***
Library    Browser

*** Variables ***
${BASE_URL}    https://sit1asiointi.lahitapiola.fi/
${BROWSER_TYPE}    chromium

*** Test Cases ***
Navigate and Perform Actions
    Open Browser Context
    Accept Cookies
    Navigate to URL    ${BASE_URL}
    Click Save Button
    Click OP Link
    Click Tunnistaudu Button
    Click Vahvista Button
    Fill Sosiaaliturvatunnus    142643576879
    Click Jatkaa Button
    Close Browser Context

*** Keywords ***
Open Browser Context
    New Browser    ${BROWSER_TYPE}    headless=False
    New Context    recordVideo={'dir': './execution_videos/Navigate_and_Perform_Actions'}

Accept Cookies
    Click Element    label:has-text("RELEASE_MAY2025") >> div >> nth=3
    Click Element    label:has-text("RELEASE_MAY2025") >> div >> nth=3

Navigate to URL
    [Arguments]    ${url}
    New Page    ${url}

Click Save Button
    Click    role=button[name="Save"]

Click OP Link
    Click    role=link[name="OP"]

Click Tunnistaudu Button
    Click    role=button[name="Tunnistaudu"]

Click Vahvista Button
    Click    role=button[name="Vahvista"]

Fill Sosiaaliturvatunnus
    [Arguments]    ${value}
    Click    role=textbox[name="Sosiaaliturvatunnus"]
    Fill Text    role=textbox[name="Sosiaaliturvatunnus"]    ${value}

Click Jatkaa Button
    Click    role=button[name="jatkaa"]

Close Browser Context
    Close Context

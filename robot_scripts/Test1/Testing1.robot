*** Settings ***
Library    Browser

*** Variables ***
${BASE_URL}    https://www.lahitapiola.fi/henkilo/
${BROWSER_TYPE}    chromium
${USER_ID}    21321421


*** Test Cases ***
Test Lahitapiola Navigation
    Open Browser And Navigate    ${BASE_URL}    ${BROWSER_TYPE}
    Accept Cookies
    Navigate To Asiakkaalle
    #Login To Service
    Close Browser

*** Keywords ***
Open Browser And Navigate
    [Arguments]    ${url}    ${browser_type}
    New Browser    ${browser_type}    headless=False
    New Context    viewport={'width': 1280, 'height': 720}    recordVideo={'dir': './videos'}
    New Page
    Go To    ${url}

Accept Cookies
    Click    role=button[name="Hyväksy kaikki"]

Navigate To Asiakkaalle
    Click    role=link[name="Asiakkaalle"]

Login To Service
    Click    role=link[name="Kirjaudu verkkopalveluun"]
    Click    role=link[name="OP"][exact=True]
    Click    role=textbox[name="Käyttäjätunnus"]
    Fill Text    role=textbox[name="Käyttäjätunnus"]    ${USER_ID}
    Click    role=button[name="Jatka"]
    Click    role=button[name="Keskeytä"]

Close Browser
    Close Context
    #Close Browser
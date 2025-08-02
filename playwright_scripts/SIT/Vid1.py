import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(**playwright.devices["Desktop Chrome"])
    page = context.new_page()
    # Navigate to the target URL
    page.goto("https://sit1asiointi.lahitapiola.fi/")
    page.get_by_role("button", name="Save").click()
    page.get_by_role("link", name="OP", exact=True).click()
    page.get_by_role("button", name="Tunnistaudu").click()
    page.get_by_role("button", name="Vahvista").click()
    page.get_by_role("textbox", name="Sosiaaliturvatunnus").click()
    page.get_by_role("textbox", name="Sosiaaliturvatunnus").click()
    page.get_by_role("textbox", name="Sosiaaliturvatunnus").fill("010183-800N")
    page.get_by_role("button", name="jatkaa").click()
    # Navigate to the target URL
    page.goto("https://sit1asiointi.lahitapiola.fi/default/#/")
    page.get_by_role("button", name="Hyväksy kaikki").click()
    page.get_by_role("button", name="Etusivu").click()
    page.get_by_role("button", name="Vakuutukset").click()
    page.get_by_role("button", name="Vahingot").click()
    page.get_by_test_id("claim-details-link-LMA25002447").get_by_role("link", name="Ajoneuvovahinko Henkilöauto").click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)

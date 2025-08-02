import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(**playwright.devices["Desktop Chrome"])
    page = context.new_page()
    # Navigate to the target URL
    page.goto("https://www.lahitapiola.fi/henkilo/")
    page.get_by_role("button", name="Hyväksy kaikki").click()
    page.get_by_role("link", name="Asiakkaalle").click()
    page.locator("#hero_kirjaudu-verkkopalveluun_kirjaudu-verkkopalveluun").get_by_role("link", name="Kirjaudu verkkopalveluun").click()
    page.get_by_role("link", name="OP", exact=True).click()
    page.get_by_role("textbox", name="Käyttäjätunnus").click()
    page.get_by_role("textbox", name="Käyttäjätunnus").fill("21321421")
    page.get_by_role("button", name="Jatka").click()
    page.get_by_role("button", name="Keskeytä").click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)

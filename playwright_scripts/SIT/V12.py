import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(**playwright.devices["Desktop Chrome"])
    page = context.new_page()
    # Navigate to the target URL
    page.goto("https://sit1asiointi.lahitapiola.fi/")
    page.get_by_role("button", name="Save").click()
    page.locator("div").filter(has_text="MobiilivarmenneS-PankkiSäästö").nth(3).click()
    page.get_by_role("button", name="Keskeytä").click()
    page.get_by_role("button", name="Hyväksy kaikki").click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)

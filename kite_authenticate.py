from playwright.sync_api import sync_playwright
from urllib.parse import urlparse, parse_qs
import pyotp
import time
import os
from dotenv import load_dotenv
load_dotenv()

TOTP_SECRET = os.getenv("TOTP_SECRET")

def request_token_generator(input_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(input_url)
        page.fill("#userid", "LCK461")
        page.fill("#password", "Shahil@120")
        page.click("button[type=submit]")

        time.sleep(5)
        otp_input = page.wait_for_selector(
        "input[type='number'][maxlength='6']",
        timeout=20000
    )

        # Generate OTP at the last moment
        otp = pyotp.TOTP(TOTP_SECRET).now()

        # Focus + clear (important for number inputs)
        otp_input.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")

        # Type OTP like a human
        page.keyboard.type(otp, delay=120)

        time.sleep(10)

        # Capture request_token from redirect
        page.wait_for_url("**request_token**", timeout=30000)
        output_url = page.url

        parsed = urlparse(output_url)
        query_params = parse_qs(parsed.query)
        request_token = query_params.get('request_token', [None])[0]
        return request_token
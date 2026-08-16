"""
scraper.py
----------
Scrapes an Amazon product page using headless Selenium (to render
JS-heavy content) + BeautifulSoup (to parse the resulting HTML).

Amazon actively fights automated scraping (bot-detection, CAPTCHAs,
layout A/B tests) so this is written defensively:
  - realistic headers + a real Chrome user-agent
  - explicit waits for key elements instead of fixed sleeps
  - multiple CSS-selector fallbacks per field, since Amazon serves
    different DOM structures depending on category / region / test group
  - graceful degradation: missing fields return None rather than crashing

This is for personal/educational use against pages you're allowed to
scrape. Respect robots.txt and Amazon's Terms of Service in any
real deployment - this demo is not meant to be run at scale or in
production against Amazon.
"""

import time
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]


def _build_driver(headless: bool = True) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    options.add_argument("--window-size=1920,1080")
    # Reduce obvious automation fingerprints
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


def _first_text(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    """Try a list of CSS selectors in order, return the first match's text."""
    for sel in selectors:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            return el.get_text(strip=True)
    return None


def scrape_amazon_product(url: str, timeout: int = 15) -> dict:
    """
    Loads an Amazon product page and extracts key fields.

    Returns a dict with title, price, rating, review_count, bullets
    (feature list), and description. Any field that couldn't be found
    is None so the caller/LLM can be told "not available" rather than
    getting a crash.
    """
    driver = _build_driver(headless=True)
    try:
        driver.get(url)

        # Wait for the title element - the most reliable signal the
        # page has actually rendered (vs. still on a CAPTCHA/interstitial)
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.ID, "productTitle"))
            )
        except TimeoutException:
            # Page may still have useful content even if this specific
            # wait timed out (different layout) - continue and let the
            # selector fallbacks below do their best.
            pass

        # Small randomized pause to look less like a bot and let any
        # lazy-loaded price widgets settle.
        time.sleep(random.uniform(1.0, 2.0))

        html = driver.page_source
    finally:
        driver.quit()

    soup = BeautifulSoup(html, "html.parser")

    title = _first_text(soup, ["#productTitle"])

    price = _first_text(
        soup,
        [
            ".a-price .a-offscreen",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            "#corePrice_feature_div .a-offscreen",
        ],
    )

    rating = _first_text(soup, ["span[data-hook='rating-out-of-text']", "#acrPopover"])

    review_count = _first_text(
        soup, ["#acrCustomerReviewText", "span[data-hook='total-review-count']"]
    )

    bullets_el = soup.select_one("#feature-bullets")
    bullets = None
    if bullets_el:
        items = [li.get_text(strip=True) for li in bullets_el.select("li")]
        items = [i for i in items if i]
        if items:
            bullets = items

    description = _first_text(
        soup, ["#productDescription", "#aplus", "#bookDescription_feature_div"]
    )

    return {
        "url": url,
        "title": title,
        "price": price,
        "rating": rating,
        "review_count": review_count,
        "bullets": bullets,
        "description": description,
        "scrape_ok": title is not None,  # rough signal something real was found
    }

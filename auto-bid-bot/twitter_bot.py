"""X (Twitter) scraping + reply posting via Playwright persistent context.

X changes test-ids and DOM structure regularly. We rely primarily on
data-testid attributes (most stable) with role/aria fallbacks, and use
keyboard shortcut (Ctrl/Cmd+Enter) as a backup submit path.
"""
import os
import re
import sys
from urllib.parse import quote
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from loguru import logger

from config import (
    SESSION_DIR, HEADLESS, TWITTER_KEYWORDS,
    MAX_TWITTER_PER_RUN, DRY_RUN, TWITTER_EMAIL, TWITTER_PASSWORD, TWITTER_USERNAME,
)
from utils import random_delay, screenshot

TWITTER_PROFILE = os.path.join(SESSION_DIR, "twitter")

TWEET_SELECTORS = [
    "article[data-testid='tweet']",
    "article[role='article']",
]
TWEET_TEXT_SELECTORS = [
    "div[data-testid='tweetText']",
    "div[lang]",
]
REPLY_BUTTON_SELECTORS = [
    "button[data-testid='reply']",
    "div[role='button'][data-testid='reply']",
    "button[aria-label*='Reply' i]",
]
REPLY_BOX_SELECTORS = [
    "div[data-testid='tweetTextarea_0']",
    "div[role='textbox'][contenteditable='true']",
    "div[aria-label*='reply' i][contenteditable='true']",
]
SUBMIT_SELECTORS = [
    "button[data-testid='tweetButton']",
    "button[data-testid='tweetButtonInline']",
    "div[role='button'][data-testid='tweetButton']",
]


def _ctx(p):
    os.makedirs(TWITTER_PROFILE, exist_ok=True)
    return p.chromium.launch_persistent_context(
        TWITTER_PROFILE,
        headless=HEADLESS,
        viewport={"width": 1366, "height": 850},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
    )


def _first_match(scope, selectors):
    for sel in selectors:
        try:
            el = scope.query_selector(sel)
            if el:
                return el, sel
        except Exception:
            continue
    return None, None


def _click_button_with_text(page, texts, timeout=8000):
    """Click an X flow button by visible text. X buttons have no data-testid in /i/flow/login.
    The login modal contains 'Sign in with Google' and 'Sign in with Apple' buttons that
    must NOT be matched — we want the bottom 'Next' / 'Log in' button under the input."""
    for t in texts:
        # 1) role-based exact match
        try:
            btn = page.get_by_role("button", name=re.compile(rf"^\s*{re.escape(t)}\s*$", re.I)).first
            btn.wait_for(state="visible", timeout=timeout)
            btn.click()
            return True
        except Exception:
            pass
        # 2) locator with hasText, excluding social SSO buttons
        try:
            btn = page.locator("button", has_text=re.compile(rf"^\s*{re.escape(t)}\s*$", re.I)).filter(
                has_not_text=re.compile(r"Google|Apple", re.I)
            ).first
            btn.wait_for(state="visible", timeout=2000)
            btn.click()
            return True
        except Exception:
            continue
    return False


def _auto_login(page) -> bool:
    """Programmatic login flow. X /i/flow/login uses no data-testid:
       step 1: input[autocomplete='username'] + 'Next' button
       step 2 (sometimes): input[data-testid='ocfEnterTextTextInput'] for username/phone challenge
       step 3: input[name='password'] (autocomplete='current-password') + 'Log in'
    """
    if not TWITTER_EMAIL or not TWITTER_PASSWORD:
        logger.warning("[X] No TWITTER_EMAIL/PASSWORD set — cannot auto-login.")
        return False
    try:
        page.goto("https://x.com/i/flow/login", timeout=60000)
        random_delay(3, 5)

        # Step 1: username/email — the BOTTOM input below "or" divider.
        # Two SSO buttons (Google, Apple) sit ABOVE the input; we must not click them.
        user_input = page.locator(
            "input[autocomplete='username'], input[name='text'], input[type='text']"
        ).first
        user_input.wait_for(state="visible", timeout=20000)
        user_input.click()
        user_input.fill(TWITTER_EMAIL)
        random_delay(1, 2)
        # Press Enter first (most reliable — submits the form the input belongs to)
        page.keyboard.press("Enter")
        random_delay(1, 2)
        # If still on same step, try clicking Next button explicitly
        if page.locator("input[autocomplete='username']").count() > 0:
            _click_button_with_text(page, ["Next", "Avanti", "Siguiente", "Weiter", "Suivant"])
        random_delay(2, 4)

        # Step 2 (optional): "unusual login activity" — asks for username/phone
        try:
            challenge = page.locator(
                "input[data-testid='ocfEnterTextTextInput'], input[name='text']"
            ).first
            challenge.wait_for(state="visible", timeout=4000)
            handle = TWITTER_USERNAME or TWITTER_EMAIL.split("@")[0]
            challenge.fill(handle)
            random_delay(1, 2)
            if not _click_button_with_text(page, ["Next", "Avanti"]):
                page.keyboard.press("Enter")
            random_delay(2, 4)
        except PWTimeout:
            pass
        except Exception:
            pass

        # Step 3: password
        pwd = page.locator(
            "input[name='password'], input[autocomplete='current-password'], input[type='password']"
        ).first
        pwd.wait_for(state="visible", timeout=20000)
        pwd.click()
        pwd.fill(TWITTER_PASSWORD)
        random_delay(1, 2)
        page.keyboard.press("Enter")
        random_delay(1, 2)
        if page.locator("input[name='password']").count() > 0:
            _click_button_with_text(page, ["Log in", "Login", "Accedi", "Iniciar sesión", "Anmelden", "Se connecter"])

        # Wait for home / nav to confirm login
        try:
            page.wait_for_url(re.compile(r"https://x\.com/(home|i/timeline|\?)"), timeout=30000)
        except PWTimeout:
            try:
                page.wait_for_selector("a[data-testid='AppTabBar_Home_Link']", timeout=10000)
            except PWTimeout:
                logger.error("[X] Login did not reach home — 2FA, captcha, or wrong creds.")
                screenshot(page, "twitter_login_failed")
                return False
        logger.info("[X] Auto-login successful")
        return True
    except Exception as e:
        logger.exception(f"[X] auto-login error: {e}")
        screenshot(page, "twitter_login_exception")
        return False


def _ensure_login(page) -> bool:
    page.goto("https://x.com/home", timeout=60000)
    random_delay(2, 4)
    if "login" not in page.url and "i/flow/login" not in page.url:
        return True
    # Logged out — try auto-login first
    if TWITTER_EMAIL and TWITTER_PASSWORD:
        if _auto_login(page):
            return True
    if HEADLESS:
        logger.error("[X] Not logged in and headless. Set TWITTER_EMAIL/PASSWORD or run once with HEADLESS=false.")
        return False
    logger.warning("[X] Complete login manually in the browser window (3 min).")
    try:
        page.wait_for_url(re.compile(r"https://x\.com/home"), timeout=180000)
        return True
    except PWTimeout:
        return False


def fetch_posts(limit: int = MAX_TWITTER_PER_RUN):
    posts = []
    seen = set()
    with sync_playwright() as p:
        ctx = _ctx(p)
        page = ctx.new_page()
        if not _ensure_login(page):
            ctx.close()
            return posts

        for kw in TWITTER_KEYWORDS:
            if len(posts) >= limit:
                break
            url = f"https://x.com/search?q={quote(kw)}&src=typed_query&f=live"
            logger.info(f"[X] Searching: {kw}")
            try:
                page.goto(url, timeout=60000)
            except PWTimeout:
                continue
            random_delay(3, 6)
            for _ in range(3):
                page.mouse.wheel(0, 1500)
                random_delay(1, 2)

            articles = []
            for sel in TWEET_SELECTORS:
                articles = page.query_selector_all(sel)
                if articles:
                    break

            for a in articles:
                if len(posts) >= limit:
                    break
                try:
                    link_el = a.query_selector("a[href*='/status/']")
                    href = link_el.get_attribute("href") if link_el else ""
                    m = re.search(r"/status/(\d+)", href or "")
                    if not m:
                        continue
                    tid = m.group(1)
                    if tid in seen:
                        continue
                    text_el, _ = _first_match(a, TWEET_TEXT_SELECTORS)
                    txt = text_el.inner_text().strip() if text_el else ""
                    if not txt:
                        continue
                    seen.add(tid)
                    posts.append({
                        "post_id": tid,
                        "post_text": txt[:1000],
                        "post_url": f"https://x.com{href}",
                        "platform": "twitter",
                    })
                except Exception as e:
                    logger.debug(f"tweet parse error: {e}")
        ctx.close()
    logger.info(f"[X] Fetched {len(posts)} tweets")
    return posts


def post_twitter_reply(post_url: str, comment: str) -> bool:
    with sync_playwright() as p:
        ctx = _ctx(p)
        page = ctx.new_page()
        try:
            if not _ensure_login(page):
                return False
            page.goto(post_url, timeout=60000)
            random_delay(4, 7)

            btn, _ = _first_match(page, REPLY_BUTTON_SELECTORS)
            if btn:
                try:
                    btn.click()
                except Exception:
                    pass
                random_delay(2, 4)

            editor, sel = _first_match(page, REPLY_BOX_SELECTORS)
            if not editor:
                logger.error("[X] Reply box not found")
                screenshot(page, "twitter_no_box")
                return False
            logger.debug(f"[X] using reply box {sel}")

            editor.scroll_into_view_if_needed()
            editor.click()
            for ch in comment:
                page.keyboard.type(ch)
                page.wait_for_timeout(40)
            random_delay(2, 5)

            screenshot(page, "twitter_before_submit")

            if DRY_RUN:
                logger.info("DRY RUN: Comment ready")
                print("DRY RUN: Comment ready")
                print(f"  platform: twitter\n  url: {post_url}\n  comment: {comment}")
                return True

            submit, _ = _first_match(page, SUBMIT_SELECTORS)
            if submit and submit.is_enabled():
                submit.click()
            else:
                # Fallback: keyboard shortcut (Cmd+Enter on mac, Ctrl+Enter elsewhere)
                mod = "Meta" if sys.platform == "darwin" else "Control"
                page.keyboard.press(f"{mod}+Enter")
            random_delay(3, 6)
            logger.info("[X] Reply posted")
            return True
        except Exception as e:
            logger.exception(f"[X] post error: {e}")
            return False
        finally:
            ctx.close()

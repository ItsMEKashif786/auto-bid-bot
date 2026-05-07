"""LinkedIn scraping + comment posting via Playwright persistent context.

Selectors here are deliberately defensive — LinkedIn renames classes often,
so we try multiple selectors and fall back to role/aria/text matching.
"""
import os
import re
from urllib.parse import quote
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from loguru import logger

from config import (
    SESSION_DIR, HEADLESS, LINKEDIN_KEYWORDS,
    MAX_LINKEDIN_PER_RUN, DRY_RUN, LINKEDIN_EMAIL, LINKEDIN_PASSWORD,
)
from utils import random_delay, human_type, screenshot

LINKEDIN_PROFILE = os.path.join(SESSION_DIR, "linkedin")

# ---- Selector pools (try in order). Update only this block when LI changes UI.
# LinkedIn rotates wrapper class names every few months. Keep a wide net,
# from most-specific (preferred) down to generic containers.
POST_CARD_SELECTORS = [
    "div[data-urn^='urn:li:activity']",
    "div.feed-shared-update-v2",
    "div.fie-impression-container",
    "li.reusable-search__result-container",
    "div.search-results-container div.update-components-actor",
    "div.scaffold-finite-scroll__content > div",
    "main div.update-components-update-v2",
    "main li",
]
POST_TEXT_SELECTORS = [
    "div.feed-shared-update-v2__description",
    "div.update-components-text",
    "div.feed-shared-inline-show-more-text",
    "span.break-words",
    "div.update-components-text span[dir='ltr']",
]
POST_LINK_SELECTORS = [
    "a[href*='/feed/update/']",
    "a[href*='/posts/']",
    "a.app-aware-link[href*='activity']",
    "a[href*='urn:li:activity']",
]
COMMENT_BUTTON_SELECTORS = [
    "button[aria-label*='Comment' i]",
    "button:has-text('Comment')",
    "button.comment-button",
]
COMMENT_BOX_SELECTORS = [
    "div.ql-editor[contenteditable='true']",
    "div[role='textbox'][contenteditable='true']",
    "div[aria-label*='comment' i][contenteditable='true']",
]
SUBMIT_SELECTORS = [
    "button.comments-comment-box__submit-button",
    "button.comments-comment-box__submit-button--cr",
    "button[type='submit']:has-text('Post')",
    "button:has-text('Post'):not([disabled])",
]


def _ctx(p):
    os.makedirs(LINKEDIN_PROFILE, exist_ok=True)
    return p.chromium.launch_persistent_context(
        LINKEDIN_PROFILE,
        headless=HEADLESS,
        viewport={"width": 1366, "height": 850},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
    )


def _first_match(scope, selectors):
    """Return the first element found from a list of selectors."""
    for sel in selectors:
        try:
            el = scope.query_selector(sel)
            if el:
                return el, sel
        except Exception:
            continue
    return None, None


def _query_all_first(page, selectors):
    """Return list from the first selector that yields any matches."""
    for sel in selectors:
        try:
            els = page.query_selector_all(sel)
            if els:
                return els, sel
        except Exception:
            continue
    return [], None


def _ensure_login(page) -> bool:
    page.goto("https://www.linkedin.com/feed/", timeout=60000)
    random_delay(2, 4)
    if "login" in page.url or "checkpoint" in page.url or "uas/login" in page.url:
        if not (LINKEDIN_EMAIL and LINKEDIN_PASSWORD):
            logger.warning("LinkedIn not logged in — open browser once with HEADLESS=false to log in.")
            return False
        try:
            page.goto("https://www.linkedin.com/login")
            human_type(page, "#username", LINKEDIN_EMAIL)
            human_type(page, "#password", LINKEDIN_PASSWORD)
            page.click("button[type=submit]")
            page.wait_for_load_state("networkidle", timeout=30000)
        except PWTimeout:
            logger.warning("Login may need a manual checkpoint; complete it in the open browser.")
        # Wait for feed to load if challenge passed
        try:
            page.wait_for_url("**/feed/**", timeout=120000)
        except PWTimeout:
            return False
    return True


def _scroll_to_load(page, rounds: int = 3):
    for _ in range(rounds):
        page.mouse.wheel(0, 1800)
        random_delay(1.5, 3)


def _scrape_via_links(page, limit, seen):
    """Fallback: scan every activity link on the page, walk up to nearest
    container, and pull text. Survives most LI redesigns because it relies on
    URL patterns, not class names."""
    found = []
    anchors = page.query_selector_all(
        "a[href*='/feed/update/urn:li:activity'], a[href*='urn:li:activity']"
    )
    logger.debug(f"[LinkedIn] link-fallback found {len(anchors)} anchors")
    for a in anchors:
        if len(found) >= limit:
            break
        try:
            href = a.get_attribute("href") or ""
            m = re.search(r"urn:li:activity:\d+", href)
            if not m:
                continue
            pid = m.group(0)
            if pid in seen:
                continue
            # Walk up to find the post container with meaningful text
            container = a.evaluate_handle(
                "el => el.closest('[data-urn], div.feed-shared-update-v2, "
                "li.reusable-search__result-container, div.fie-impression-container, "
                "div.update-components-update-v2') || el.parentElement"
            ).as_element()
            if not container:
                continue
            txt = (container.inner_text() or "").strip()
            if len(txt) < 40:
                continue
            seen.add(pid)
            purl = href if href.startswith("http") else f"https://www.linkedin.com{href}"
            found.append({
                "post_id": pid,
                "post_text": txt[:1500],
                "post_url": purl,
                "platform": "linkedin",
            })
        except Exception as e:
            logger.debug(f"link-fallback parse: {e}")
    return found


def fetch_posts(limit: int = MAX_LINKEDIN_PER_RUN):
    posts = []
    seen = set()
    with sync_playwright() as p:
        ctx = _ctx(p)
        page = ctx.new_page()
        if not _ensure_login(page):
            ctx.close()
            return posts

        for kw in LINKEDIN_KEYWORDS:
            if len(posts) >= limit:
                break
            url = (
                "https://www.linkedin.com/search/results/content/"
                f"?keywords={quote(kw)}&sortBy=%22date_posted%22"
            )
            logger.info(f"[LinkedIn] Searching: {kw}")
            try:
                page.goto(url, timeout=60000)
            except PWTimeout:
                logger.warning(f"[LinkedIn] navigation timeout for {kw}")
                continue
            random_delay(3, 6)
            _scroll_to_load(page, rounds=5)

            cards, used_sel = _query_all_first(page, POST_CARD_SELECTORS)
            logger.info(f"[LinkedIn] {len(cards)} cards via {used_sel}")
            before = len(posts)
            for c in cards:
                if len(posts) >= limit:
                    break
                try:
                    pid = c.get_attribute("data-urn") or c.get_attribute("data-id") or ""
                    text_el, _ = _first_match(c, POST_TEXT_SELECTORS)
                    txt = text_el.inner_text().strip() if text_el else (c.inner_text() or "").strip()
                    link_el, _ = _first_match(c, POST_LINK_SELECTORS)
                    href = link_el.get_attribute("href") if link_el else ""
                    if not pid:
                        m = re.search(r"urn:li:activity:\d+", (href or "") + " " + (c.get_attribute("outerHTML") or ""))
                        pid = m.group(0) if m else ""
                    if not (pid and txt) or pid in seen or len(txt) < 30:
                        continue
                    seen.add(pid)
                    purl = href if href and href.startswith("http") else f"https://www.linkedin.com{href}"
                    posts.append({
                        "post_id": pid,
                        "post_text": txt[:1500],
                        "post_url": purl,
                        "platform": "linkedin",
                    })
                except Exception as e:
                    logger.debug(f"card parse error: {e}")

            # If primary card scrape produced nothing this keyword, use link fallback
            if len(posts) == before:
                logger.warning(f"[LinkedIn] 0 from cards for '{kw}', trying link-fallback")
                screenshot(page, f"linkedin_no_cards_{re.sub(r'[^a-z0-9]+', '_', kw.lower())}")
                fallback = _scrape_via_links(page, limit - len(posts), seen)
                logger.info(f"[LinkedIn] link-fallback added {len(fallback)} posts")
                posts.extend(fallback)
        ctx.close()
    logger.info(f"[LinkedIn] Fetched {len(posts)} posts")
    return posts


def post_linkedin_comment(post_url: str, comment: str) -> bool:
    with sync_playwright() as p:
        ctx = _ctx(p)
        page = ctx.new_page()
        try:
            if not _ensure_login(page):
                return False
            page.goto(post_url, timeout=60000)
            random_delay(4, 7)

            # Open comment box (may already be open on detail page)
            btn, _ = _first_match(page, COMMENT_BUTTON_SELECTORS)
            if btn:
                try:
                    btn.click()
                except Exception:
                    pass
                random_delay(2, 4)

            box, sel = _first_match(page, COMMENT_BOX_SELECTORS)
            if not box:
                logger.error("[LinkedIn] Comment box not found")
                screenshot(page, "linkedin_no_box")
                return False
            logger.debug(f"[LinkedIn] using box selector {sel}")

            box.scroll_into_view_if_needed()
            box.click()
            for ch in comment:
                page.keyboard.type(ch)
                page.wait_for_timeout(40)
            random_delay(2, 5)

            screenshot(page, "linkedin_before_submit")

            if DRY_RUN:
                logger.info("DRY RUN: Comment ready")
                print("DRY RUN: Comment ready")
                print(f"  platform: linkedin\n  url: {post_url}\n  comment: {comment}")
                return True

            submit, _ = _first_match(page, SUBMIT_SELECTORS)
            if not submit:
                logger.error("[LinkedIn] Submit button not found")
                screenshot(page, "linkedin_no_submit")
                return False
            submit.click()
            random_delay(3, 6)
            logger.info("[LinkedIn] Comment posted")
            return True
        except Exception as e:
            logger.exception(f"[LinkedIn] post error: {e}")
            return False
        finally:
            ctx.close()

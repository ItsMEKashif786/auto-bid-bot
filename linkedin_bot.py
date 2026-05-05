import asyncio
import random
from playwright.async_api import Playwright, async_playwright, expect
import os
from config import Config

class LinkedInBot:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

    async def launch_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=Config.HEADLESS)
        self.context = await self.browser.new_context(storage_state="session/linkedin_state.json")
        self.page = await self.context.new_page()

    async def login(self):
        await self.page.goto("https://www.linkedin.com/login")
        if "feed" not in self.page.url:
            await self.page.fill("#username", Config.LINKEDIN_EMAIL)
            await self.page.fill("#password", Config.LINKEDIN_PASSWORD)
            await self.page.click(".btn__primary--large")
            await self.page.wait_for_url("https://www.linkedin.com/feed/")
            await self.context.storage_state(path="session/linkedin_state.json")
        print("LinkedIn login successful.")

    async def search_posts(self):
        posts = []
        for keyword in Config.LINKEDIN_SEARCH_KEYWORDS:
            search_url = f"https://www.linkedin.com/search/results/posts/?keywords={keyword.replace(' ', '%20')}"
            await self.page.goto(search_url)
            await self.page.wait_for_selector(".scaffold-finite-scroll__content")

            for i in range(Config.LINKEDIN_MAX_POSTS_PER_RUN):
                try:
                    # Scroll to load more posts
                    await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(random.uniform(3, 8))

                    post_element = await self.page.query_selector(f"div.feed-shared-update-v2:nth-child({i + 1})")
                    if not post_element:
                        continue

                    post_id = await post_element.get_attribute("data-urn")
                    post_text = await post_element.locator(".feed-shared-update-v2__description-wrapper").text_content()
                    post_url_element = await post_element.query_selector(".feed-shared-actor__container-link")
                    post_url = await post_url_element.get_attribute("href") if post_url_element else "N/A"

                    posts.append({"post_id": post_id, "post_text": post_text.strip(), "post_url": post_url})
                except Exception as e:
                    print(f"Error extracting LinkedIn post: {e}")
                if len(posts) >= Config.LINKEDIN_MAX_POSTS_PER_RUN:
                    break
            if len(posts) >= Config.LINKEDIN_MAX_POSTS_PER_RUN:
                break
        return posts

    async def post_comment(self, post_id, post_url, comment):
        await self.page.goto(post_url)
        await asyncio.sleep(random.uniform(3, 8))
        try:
            comment_box = await self.page.query_selector(".comment-form__text-editor")
            if comment_box:
                await comment_box.click()
                await self.page.fill(".comment-form__text-editor div[contenteditable=\"true\"]", comment)
                await asyncio.sleep(random.uniform(2, 5)) # Simulate typing delay
                if Config.DRY_RUN:
                    screenshot_path = f"session/linkedin_dry_run_{post_id}.png"
                    await self.page.screenshot(path=screenshot_path)
                    print(f"DRY RUN: Comment ready for LinkedIn. Platform: LinkedIn, URL: {post_url}, Comment: {comment}")
                    print(f"Screenshot saved to {screenshot_path}")
                else:
                    await self.page.click(".comment-form__submit-button")
                    print(f"Comment posted on LinkedIn post: {post_url}")
                return True
            else:
                print(f"Could not find comment box for LinkedIn post: {post_url}")
                return False
        except Exception as e:
            print(f"Error posting comment on LinkedIn: {e}")
            return False

    async def close_browser(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

async def main():
    bot = LinkedInBot()
    await bot.launch_browser()
    await bot.login()
    posts = await bot.search_posts()
    print("Found LinkedIn posts:", posts)
    # Example of posting a comment (uncomment to test)
    # if posts:
    #     await bot.post_comment(posts[0]["post_id"], posts[0]["post_url"], "This is a test comment from my bot!")
    await bot.close_browser()

if __name__ == "__main__":
    asyncio.run(main())

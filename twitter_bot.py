import asyncio
import random
from playwright.async_api import Playwright, async_playwright, expect
import os
from config import Config

class TwitterBot:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

    async def launch_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=Config.HEADLESS)
        self.context = await self.browser.new_context(storage_state="session/twitter_state.json")
        self.page = await self.context.new_page()

    async def login(self):
        await self.page.goto("https://twitter.com/i/flow/login")
        # Check if already logged in by looking for a common element on the home feed
        try:
            await self.page.wait_for_selector("[data-testid=\"AppTabBar\"]", timeout=5000)
            print("Already logged in to X (Twitter).")
            return
        except:
            pass

        try:
            # Fill in username/email
            await self.page.fill("input[autocomplete=\"username\"]", Config.TWITTER_EMAIL)
            await self.page.click("text=Next")
            await asyncio.sleep(random.uniform(2, 5))

            # Handle potential username verification step (if prompted)
            if await self.page.query_selector("input[data-testid=\"ocfEnterText\""]"):
                print("Twitter is asking for username verification. Please check the browser manually if this persists.")
                # For now, we'll assume it's the username field and try to fill it if it appears
                # This part might need manual intervention or more robust handling depending on Twitter's flow
                # For simplicity, we'll try to proceed with the password field assuming no extra step
                await self.page.fill("input[data-testid=\"ocfEnterText\""]", "your_twitter_username") # Placeholder, user needs to set this if it comes up
                await self.page.click("text=Next")
                await asyncio.sleep(random.uniform(2, 5))

            # Fill in password
            await self.page.fill("input[autocomplete=\"current-password\"]", Config.TWITTER_PASSWORD)
            await self.page.click("data-testid=LoginForm_Login_Button")
            await self.page.wait_for_url("https://twitter.com/home", timeout=10000)
            await self.context.storage_state(path="session/twitter_state.json")
            print("X (Twitter) login successful.")
        except Exception as e:
            print(f"Error during X (Twitter) login: {e}")
            print("Please ensure your credentials are correct and try again. You might need to manually log in once to save the session state.")

    async def search_posts(self):
        posts = []
        for keyword in Config.TWITTER_SEARCH_KEYWORDS:
            search_url = f"https://twitter.com/search?q={keyword.replace(" ", "%20")}&src=typed_query"
            await self.page.goto(search_url)
            await self.page.wait_for_selector("[data-testid=\"tweet\"]")
            await asyncio.sleep(random.uniform(3, 8))

            tweet_elements = await self.page.query_selector_all("[data-testid=\"tweet\"]")
            for i, tweet_element in enumerate(tweet_elements):
                if len(posts) >= Config.TWITTER_MAX_POSTS_PER_RUN:
                    break
                try:
                    tweet_id_element = await tweet_element.query_selector("time")
                    tweet_id = await tweet_id_element.get_attribute("datetime") if tweet_id_element else "N/A"

                    tweet_text_element = await tweet_element.query_selector("[data-testid=\"tweetText\"]")
                    tweet_text = await tweet_text_element.text_content() if tweet_text_element else ""

                    tweet_url_element = await tweet_element.query_selector("a[href*=\"/status/\"]")
                    tweet_url = await tweet_url_element.get_attribute("href") if tweet_url_element else "N/A"
                    if tweet_url != "N/A":
                        tweet_url = f"https://twitter.com{tweet_url}"

                    posts.append({"tweet_id": tweet_id, "tweet_text": tweet_text.strip(), "tweet_url": tweet_url})
                except Exception as e:
                    print(f"Error extracting X (Twitter) post: {e}")
            if len(posts) >= Config.TWITTER_MAX_POSTS_PER_RUN:
                break
        return posts

    async def post_reply(self, tweet_id, tweet_url, comment):
        await self.page.goto(tweet_url)
        await asyncio.sleep(random.uniform(3, 8))
        try:
            reply_button = await self.page.wait_for_selector("[data-testid=\"replyButton\"]")
            await reply_button.click()
            await asyncio.sleep(random.uniform(2, 5))

            comment_box = await self.page.wait_for_selector("[data-testid=\"tweetTextarea_0\"]")
            await comment_box.fill(comment)
            await asyncio.sleep(random.uniform(2, 5)) # Simulate typing delay

            if Config.DRY_RUN:
                screenshot_path = f"session/twitter_dry_run_{tweet_id}.png"
                await self.page.screenshot(path=screenshot_path)
                print(f"DRY RUN: Comment ready for X (Twitter). Platform: X (Twitter), URL: {tweet_url}, Comment: {comment}")
                print(f"Screenshot saved to {screenshot_path}")
            else:
                post_button = await self.page.wait_for_selector("[data-testid=\"tweetButton\"]")
                await post_button.click()
                print(f"Reply posted on X (Twitter) post: {tweet_url}")
            return True
        except Exception as e:
            print(f"Error posting reply on X (Twitter): {e}")
            return False

    async def close_browser(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

async def main():
    bot = TwitterBot()
    await bot.launch_browser()
    await bot.login()
    posts = await bot.search_posts()
    print("Found X (Twitter) posts:", posts)
    # Example of posting a reply (uncomment to test)
    # if posts:
    #     await bot.post_reply(posts[0]["tweet_id"], posts[0]["tweet_url"], "This is a test reply from my bot!")
    await bot.close_browser()

if __name__ == "__main__":
    asyncio.run(main())

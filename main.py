import asyncio
import random
from linkedin_bot import LinkedInBot
from twitter_bot import TwitterBot
from commenter import CommentGenerator
from db import Database
from config import Config
from utils import random_delay, log_info, log_warning, log_error, log_dry_run

async def main():
    log_info("Starting Auto Bidding Bot...")

    db = Database(Config.DB_PATH)
    comment_generator = CommentGenerator()
    linkedin_bot = LinkedInBot()
    twitter_bot = TwitterBot()

    user_skills = "Python, Web Scraping, Data Analysis, Machine Learning, Cloud Computing, API Development"

    try:
        # Launch browsers and log in
        await linkedin_bot.launch_browser()
        await linkedin_bot.login()
        await twitter_bot.launch_browser()
        await twitter_bot.login()

        # Process LinkedIn posts
        log_info("Searching for LinkedIn posts...")
        linkedin_posts = await linkedin_bot.search_posts()
        log_info(f"Found {len(linkedin_posts)} LinkedIn posts.")

        linkedin_comments_today = 0 # Placeholder for daily limit tracking

        for post in linkedin_posts:
            if linkedin_comments_today >= Config.LINKEDIN_DAILY_COMMENT_LIMIT:
                log_warning(f"LinkedIn daily comment limit ({Config.LINKEDIN_DAILY_COMMENT_LIMIT}) reached. Skipping further LinkedIn posts.")
                break

            post_id = post["post_id"]
            if not db.is_processed(post_id):
                log_info(f"Processing new LinkedIn post: {post_id}")
                comment = comment_generator.generate_comment(post["post_text"], user_skills)
                if comment:
                    log_info(f"Comment generated for LinkedIn post: {post_id}")
                    if Config.DRY_RUN:
                        log_dry_run(f"Platform: LinkedIn, Post ID: {post_id}, Comment: {comment}")
                        log_info("DRY RUN: Ready to submit on LinkedIn.")
                        db.save_post(post_id, "LinkedIn")
                        log_info(f"Saved to database: {post_id}")
                        success = True # Simulate success in dry run
                    else:
                        success = await linkedin_bot.post_comment(post_id, post["post_url"], comment)
                        if success:
                            db.save_post(post_id, "LinkedIn")
                            log_info(f"Successfully commented on LinkedIn post: {post_id}")
                            linkedin_comments_today += 1
                        else:
                            log_error(f"Failed to comment on LinkedIn post: {post_id}")
                else:
                    log_warning(f"No comment generated for LinkedIn post: {post_id}")
            else:
                log_info(f"LinkedIn post {post_id} already processed. Skipping.")
            random_delay()

        # Process X (Twitter) posts
        log_info("Searching for X (Twitter) posts...")
        twitter_posts = await twitter_bot.search_posts()
        log_info(f"Found {len(twitter_posts)} X (Twitter) posts.")

        twitter_replies_today = 0 # Placeholder for daily limit tracking

        for post in twitter_posts:
            if twitter_replies_today >= Config.TWITTER_DAILY_REPLY_LIMIT:
                log_warning(f"X (Twitter) daily reply limit ({Config.TWITTER_DAILY_REPLY_LIMIT}) reached. Skipping further X posts.")
                break

            post_id = post["tweet_id"]
            if not db.is_processed(post_id):
                log_info(f"Processing new X (Twitter) post: {post_id}")
                comment = comment_generator.generate_comment(post["tweet_text"], user_skills)
                if comment:
                    log_info(f"Comment generated for X (Twitter) post: {post_id}")
                    if Config.DRY_RUN:
                        log_dry_run(f"Platform: X (Twitter), Post ID: {post_id}, Comment: {comment}")
                        log_info("DRY RUN: Ready to submit on X (Twitter).")
                        db.save_post(post_id, "Twitter")
                        log_info(f"Saved to database: {post_id}")
                        success = True # Simulate success in dry run
                    else:
                        success = await twitter_bot.post_reply(post_id, post["tweet_url"], comment)
                        if success:
                            db.save_post(post_id, "Twitter")
                            log_info(f"Successfully replied to X (Twitter) post: {post_id}")
                            twitter_replies_today += 1
                        else:
                            log_error(f"Failed to reply to X (Twitter) post: {post_id}")
                else:
                    log_warning(f"No comment generated for X (Twitter) post: {post_id}")
            else:
                log_info(f"X (Twitter) post {post_id} already processed. Skipping.")
            random_delay()

    except Exception as e:
        log_error(f"An error occurred during the main execution: {e}")
    finally:
        await linkedin_bot.close_browser()
        await twitter_bot.close_browser()
        log_info("Auto Bidding Bot finished.")

if __name__ == "__main__":
    asyncio.run(main())

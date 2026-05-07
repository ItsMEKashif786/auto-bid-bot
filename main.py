"""Orchestrator: fetch posts -> dedupe -> generate -> post -> save."""
import argparse
from loguru import logger

from config import DRY_RUN
from db import init_db, is_processed, save_post
from commenter import generate_comment
from utils import random_delay, log_dry_run
import linkedin_bot
import twitter_bot


def run(platform: str):
    init_db()
    logger.info(f"=== Auto-Bid run start | platform={platform} | DRY_RUN={DRY_RUN} ===")

    if platform == "linkedin":
        posts = linkedin_bot.fetch_posts()
        post_fn = linkedin_bot.post_linkedin_comment
    elif platform == "twitter":
        posts = twitter_bot.fetch_posts()
        post_fn = twitter_bot.post_twitter_reply
    else:
        raise SystemExit(f"Unknown platform: {platform}")

    posted = 0
    for p in posts:
        print(f"[INFO] Post fetched: {p['post_id']}")
        if is_processed(p["post_id"]):
            logger.info(f"Skip duplicate {p['post_id']}")
            print(f"[INFO] Skipped duplicate {p['post_id']}")
            continue

        comment = generate_comment(p["post_text"])
        if not comment:
            print("[WARN] No comment generated, skipping")
            continue
        print("[INFO] Comment generated")

        if DRY_RUN:
            print("[DRY RUN] Ready to submit")
            log_dry_run(platform, p["post_id"], p["post_url"], comment)

        ok = post_fn(p["post_url"], comment)
        if ok:
            save_post(p["post_id"], platform)
            posted += 1
            print("[INFO] Saved to database")
        else:
            print(f"[ERROR] Failed to post on {p['post_url']}")

        random_delay(8, 20)

    logger.info(f"=== Run done | processed={posted}/{len(posts)} ===")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", choices=["linkedin", "twitter"], default="linkedin")
    args = ap.parse_args()
    run(args.platform)

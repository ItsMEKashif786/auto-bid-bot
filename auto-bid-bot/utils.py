"""Shared helpers: logging, delays, screenshots, dry-run logging."""
import os
import json
import random
import time
from datetime import datetime
from loguru import logger

from config import LOGS_DIR

# Configure rotating log file
logger.add(
    os.path.join(LOGS_DIR, "bot.log"),
    rotation="5 MB",
    retention="10 days",
    enqueue=True,
)

DRY_RUN_LOG = os.path.join(LOGS_DIR, "dry_run.log")


def random_delay(a: float = 3, b: float = 8):
    delay = random.uniform(a, b)
    logger.debug(f"Sleeping {delay:.2f}s")
    time.sleep(delay)


def human_type(page, selector: str, text: str):
    """Type text with small random per-character delay."""
    page.click(selector)
    for ch in text:
        page.keyboard.type(ch)
        time.sleep(random.uniform(0.03, 0.12))


def screenshot(page, name: str) -> str:
    """Save a screenshot under logs/ and return its path."""
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(LOGS_DIR, f"{name}_{ts}.png")
    try:
        page.screenshot(path=path, full_page=False)
        logger.info(f"Screenshot saved: {path}")
    except Exception as e:
        logger.warning(f"Screenshot failed: {e}")
    return path


def log_dry_run(platform: str, post_id: str, post_url: str, comment: str):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "platform": platform,
        "post_id": post_id,
        "post_url": post_url,
        "generated_comment": comment,
    }
    with open(DRY_RUN_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    logger.info(f"[DRY RUN] Logged {platform} post {post_id}")

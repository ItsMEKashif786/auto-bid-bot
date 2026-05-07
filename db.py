"""SQLite deduplication store for processed posts."""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "bids.db")


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS processed_posts (
                post_id   TEXT PRIMARY KEY,
                platform  TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        c.commit()


def is_processed(post_id: str) -> bool:
    with _conn() as c:
        cur = c.execute(
            "SELECT 1 FROM processed_posts WHERE post_id = ?", (post_id,)
        )
        return cur.fetchone() is not None


def save_post(post_id: str, platform: str):
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO processed_posts (post_id, platform, timestamp) VALUES (?, ?, ?)",
            (post_id, platform, datetime.utcnow().isoformat()),
        )
        c.commit()


if __name__ == "__main__":
    init_db()
    print(f"DB initialized at {DB_PATH}")

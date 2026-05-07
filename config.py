import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

    # LinkedIn Credentials
    LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
    LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

    # X (Twitter) Credentials
    TWITTER_EMAIL = os.getenv("TWITTER_EMAIL")
    TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD")

    # Playwright Settings
    HEADLESS = os.getenv("HEADLESS", "True").lower() == "true"
    LINKEDIN_SEARCH_KEYWORDS = [
        "looking for developer",
        "need freelancer",
        "need website developer",
        "hiring developer",
    ]
    LINKEDIN_MAX_POSTS_PER_RUN = 5
    TWITTER_SEARCH_KEYWORDS = [
        "looking for developer",
        "need freelancer",
        "need website developer",
        "hiring developer",
    ]
    TWITTER_MAX_POSTS_PER_RUN = 5

    # Safety Limits
    LINKEDIN_DAILY_COMMENT_LIMIT = 15
    TWITTER_DAILY_REPLY_LIMIT = 10

    # Database
    DB_PATH = "data/bids.db"
    DRY_RUN = os.getenv("DRY_RUN", "False").lower() == "true"

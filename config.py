"""Central configuration loaded from .env."""
import os
from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


# API keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# LinkedIn credentials
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# Twitter / X credentials
TWITTER_EMAIL = os.getenv("TWITTER_EMAIL", "")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD", "")
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME", "")

# Behavior
DRY_RUN = _bool("DRY_RUN", True)
HEADLESS = _bool("HEADLESS", False)

# User profile / skills used in AI prompt
USER_SKILLS = os.getenv(
    "USER_SKILLS",
    "Full-stack web development (React, Next.js, Node.js, Python), automation, AI integrations",
)

# Search keywords
LINKEDIN_KEYWORDS = [
    "looking for developer",
    "need freelancer",
    "need website developer",
    "hiring developer",
]
TWITTER_KEYWORDS = [
    "looking for developer",
    "need freelancer",
    "hiring developer",
]

# Safety limits
MAX_LINKEDIN_PER_RUN = 5
MAX_TWITTER_PER_RUN = 5
LINKEDIN_DAILY_LIMIT = 15
TWITTER_DAILY_LIMIT = 10

# Paths
BASE_DIR = os.path.dirname(__file__)
SESSION_DIR = os.path.join(BASE_DIR, "session")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
DATA_DIR = os.path.join(BASE_DIR, "data")

for p in (SESSION_DIR, LOGS_DIR, DATA_DIR):
    os.makedirs(p, exist_ok=True)

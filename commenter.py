"""AI bid-comment generator: Groq primary, OpenRouter fallback."""
import requests
from loguru import logger

from config import GROQ_API_KEY, OPENROUTER_API_KEY, USER_SKILLS

SYSTEM_PROMPT = (
    "You write short, personalized freelance bid comments. "
    "Tone: human, friendly, confident, never salesy or generic. "
    "Length: 3 to 4 sentences. Reference one specific detail from the post. "
    "End with a soft call to action. No emojis. No hashtags."
)


def _build_user_prompt(post_text: str, skills: str) -> str:
    return (
        f"POST:\n{post_text}\n\n"
        f"MY SKILLS: {skills}\n\n"
        "Write the bid comment now."
    )


def _groq(post_text: str, skills: str) -> str | None:
    if not GROQ_API_KEY:
        return None
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.1-8b-instant",
                "temperature": 0.7,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_prompt(post_text, skills)},
                ],
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"Groq failed: {e}")
        return None


def _openrouter(post_text: str, skills: str) -> str | None:
    if not OPENROUTER_API_KEY:
        return None
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "meta-llama/llama-3.1-8b-instruct",
                "temperature": 0.7,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_prompt(post_text, skills)},
                ],
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"OpenRouter failed: {e}")
        return None


def generate_comment(post_text: str, skills: str = USER_SKILLS) -> str | None:
    out = _groq(post_text, skills) or _openrouter(post_text, skills)
    if out:
        logger.info("AI comment generated")
    else:
        logger.error("All AI providers failed")
    return out

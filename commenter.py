from openai import OpenAI
from config import Config
import random

class CommentGenerator:
    def __init__(self):
        self.groq_client = OpenAI(api_key=Config.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
        self.openrouter_client = OpenAI(api_key=Config.OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

    def generate_comment(self, post_content, user_skills):
        prompt = f"""You are an AI assistant specialized in crafting personalized and human-sounding freelance bid comments. The goal is to respond to posts where users are looking for freelancers or developers. Your comments should be 3-4 sentences long, concise, and not generic. Make sure to incorporate the user's skills naturally into the bid. Avoid sounding like a bot. \n\nPost content: {post_content}\nUser skills: {user_skills}\n\nGenerate a personalized freelance bid comment:"""

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]

        try:
            # Try Groq API first
            response = self.groq_client.chat.completions.create(
                model="llama3-8b-8192", # Or another suitable Groq model
                messages=messages,
                max_tokens=150,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Groq API failed: {e}. Falling back to OpenRouter.")
            try:
                # Fallback to OpenRouter API
                response = self.openrouter_client.chat.completions.create(
                    model="openai/gpt-3.5-turbo", # Or another suitable OpenRouter model
                    messages=messages,
                    max_tokens=150,
                    temperature=0.7,
                )
                return response.choices[0].message.content.strip()
            except Exception as e_fallback:
                print(f"OpenRouter API also failed: {e_fallback}. Cannot generate comment.")
                return ""

if __name__ == "__main__":
    generator = CommentGenerator()
    sample_post = "Looking for a Python developer to build a web scraper for e-commerce data."
    sample_skills = "Python, web scraping, data analysis, Django, Flask"
    comment = generator.generate_comment(sample_post, sample_skills)
    print("Generated Comment:", comment)

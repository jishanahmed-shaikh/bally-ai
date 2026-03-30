import os
import sys
from dotenv import load_dotenv

load_dotenv()

class ConfigurationError(Exception):
    pass

def get_config() -> dict:
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ConfigurationError(
            "GROQ_API_KEY environment variable is not set. "
            "Please copy .env.example to .env and add your Groq API key. "
            "Get your key at https://console.groq.com"
        )
    return {
        "groq_api_key": groq_api_key,
        "fastapi_url": os.getenv("FASTAPI_URL", "http://localhost:8000"),
    }

# Validate on import - will raise ConfigurationError if missing
# (called explicitly from FastAPI lifespan, not on module import)

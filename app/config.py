import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # These are api key,model name and base url for llm you can use you own
    # You can get free api keys from openrouter or nvidia https://build.nvidia.com/models
    API_KEY = os.getenv("MODEL_API_KEY")
    BASE_URL = os.getenv("MODEL_BASE_URL", "https://openrouter.ai/api/v1")
    MODEL_NAME = os.getenv("MODEL_NAME", "nvidia/nemotron-3-ultra-550b-a55b:free")

    MAX_ITERATIONS_LOW_MODE = int(os.getenv("MAX_ITERATIONS_LOW_MODE", 20))
    MAX_ITERATIONS_MEDIUM_MODE = int(os.getenv("MAX_ITERATIONS_MEDIUM_MODE", 30))
    MAX_ITERATIONS_HIGH_MODE = int(os.getenv("MAX_ITERATIONS_HIGH_MODE", 40))
    REACTIVE_AGENT_MODES = {
        "low": MAX_ITERATIONS_LOW_MODE,
        "medium": MAX_ITERATIONS_MEDIUM_MODE,
        "high": MAX_ITERATIONS_HIGH_MODE,
    }

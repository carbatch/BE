import os
from openai import AsyncOpenAI

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")
IMAGE_MODEL      = os.getenv("IMAGE_MODEL", "dall-e-3")
TIMEOUT_SECONDS  = float(os.getenv("TIMEOUT_SECONDS", "120"))

VENICE_MODEL     = os.getenv("VENICE_MODEL", "z-image-turbo")
POLLINATIONS_MODEL = os.getenv("POLLINATIONS_MODEL", "flux")

openai_client = AsyncOpenAI(
    api_key=OPENAI_API_KEY or "dummy",
    timeout=TIMEOUT_SECONDS,
)

import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
MAX_VIDEO_DURATION = int(os.getenv("MAX_VIDEO_DURATION", "10800"))
CLIP_TTL_SECONDS = int(os.getenv("CLIP_TTL_SECONDS", "3600"))
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "http://localhost:5173")
YTDLP_COOKIES_FROM_BROWSER = os.getenv("YTDLP_COOKIES_FROM_BROWSER", "")
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")

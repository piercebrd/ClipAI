import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGIN
from app.routers import health, analyze, render

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ClipAI", version="0.1.0")


@app.get("/debug/cookies")
def debug_cookies():
    """Temporary debug endpoint — remove after deployment is working."""
    raw = os.getenv("YTDLP_COOKIES", "")
    cookies_file = "/tmp/yt_cookies.txt"
    file_exists = os.path.exists(cookies_file)
    file_size = os.path.getsize(cookies_file) if file_exists else 0
    return {
        "env_var_length": len(raw),
        "env_var_has_newlines": "\n" in raw,
        "env_var_has_escaped_newlines": "\\n" in raw,
        "env_var_first_50_chars": raw[:50] if raw else "(empty)",
        "file_exists": file_exists,
        "file_size": file_size,
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(render.router)

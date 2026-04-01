import logging
import os
import shutil
import uuid
import yt_dlp

from app.config import TEMP_DIR, MAX_VIDEO_DURATION, YTDLP_COOKIES_FROM_BROWSER

logger = logging.getLogger(__name__)

COOKIES_FILE = "/tmp/yt_cookies.txt"

# Player client strategies to try in order.
# Each entry is tried until one succeeds.
PLAYER_CLIENT_STRATEGIES = [
    ["mediaconnect"],
    ["web"],
    ["android"],
    ["ios"],
]


def _write_cookies_from_env():
    """Write YTDLP_COOKIES env var content to a file for yt-dlp."""
    raw = os.getenv("YTDLP_COOKIES", "")
    if not raw:
        logger.warning("YTDLP_COOKIES env var is empty")
        return
    # Render may escape newlines as literal \n
    if "\\n" in raw and "\n" not in raw.replace("\\n", ""):
        raw = raw.replace("\\n", "\n")
    with open(COOKIES_FILE, "w") as f:
        f.write(raw)
    lines = [l for l in raw.strip().splitlines() if l and not l.startswith("#")]
    logger.info("Wrote cookies file: %s (%d cookie lines)", COOKIES_FILE, len(lines))

def _ensure_node_in_path() -> None:
    """Add Node.js to PATH if not already accessible (needed for yt-dlp EJS solver)."""
    if shutil.which("node"):
        return
    # Common nvm path on macOS
    nvm_default = os.path.expanduser("~/.nvm/versions/node")
    if os.path.isdir(nvm_default):
        try:
            versions = sorted(os.listdir(nvm_default), reverse=True)
            if versions:
                node_bin = os.path.join(nvm_default, versions[0], "bin")
                os.environ["PATH"] = node_bin + os.pathsep + os.environ.get("PATH", "")
        except OSError:
            pass


def _make_job_dir(job_id: str) -> str:
    job_dir = os.path.join(TEMP_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    return job_dir


def _cookies_opt() -> dict:
    """Return yt-dlp cookies option depending on available config."""
    _write_cookies_from_env()
    if os.path.exists(COOKIES_FILE):
        logger.info("Using cookies file: %s (size=%d)", COOKIES_FILE, os.path.getsize(COOKIES_FILE))
        return {"cookiefile": COOKIES_FILE}
    if YTDLP_COOKIES_FROM_BROWSER:
        logger.info("Using browser cookies: %s", YTDLP_COOKIES_FROM_BROWSER)
        return {"cookiesfrombrowser": (YTDLP_COOKIES_FROM_BROWSER,)}
    logger.warning("No cookies configured — YouTube may block downloads")
    return {}


def _oauth_opt() -> dict:
    """Return yt-dlp OAuth2 options if a cached token exists."""
    token_path = os.path.expanduser("~/.cache/yt-dlp/youtube-oauth2/token.json")
    if os.path.exists(token_path):
        logger.info("OAuth2 token found at %s", token_path)
        return {"username": "oauth2", "password": ""}
    return {}


def _clean_job_dir(job_dir: str) -> None:
    """Remove all downloaded files from job_dir to allow retry."""
    for fname in os.listdir(job_dir):
        fpath = os.path.join(job_dir, fname)
        try:
            os.remove(fpath)
        except OSError:
            pass


def download_video(url: str, job_id: str) -> dict:
    _ensure_node_in_path()
    """
    Download a YouTube video and extract audio.
    Retries with different player client strategies on bot-detection errors.
    Returns a dict with:
      - video_path: path to the downloaded video file
      - audio_path: path to the extracted audio (WAV)
      - duration:   duration in seconds
      - title:      video title
    """
    job_dir = _make_job_dir(job_id)
    video_path = os.path.join(job_dir, "video.mp4")

    cookies = _cookies_opt()
    oauth = _oauth_opt()

    last_error = None

    for strategy in PLAYER_CLIENT_STRATEGIES:
        logger.info("Trying player_client=%s for %s", strategy, url)
        _clean_job_dir(job_dir)

        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
            "outtmpl": video_path,
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "match_filter": _duration_filter,
            **cookies,
            **oauth,
            "extractor_args": {"youtube": {"player_client": strategy}},
            "js_runtimes": {"node": {}, "deno": {}},
            # Extract audio as WAV for Whisper
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "0",
                }
            ],
            "postprocessor_args": ["-ar", "16000", "-ac", "1"],
            "keepvideo": True,
            "paths": {"home": job_dir},
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                duration = info.get("duration", 0)
                title = info.get("title", "video")

            audio_path = _find_audio_file(job_dir)

            logger.info("Download succeeded with player_client=%s", strategy)
            return {
                "video_path": video_path,
                "audio_path": audio_path,
                "duration": duration,
                "title": title,
            }
        except yt_dlp.utils.DownloadError as e:
            last_error = e
            error_msg = str(e).lower()
            if "sign in" in error_msg or "bot" in error_msg or "confirm" in error_msg:
                logger.warning(
                    "Bot detection with player_client=%s, trying next strategy...",
                    strategy,
                )
                continue
            # Non-bot error — don't retry with other clients
            raise

    # All strategies exhausted
    logger.error("All player client strategies failed for %s", url)
    raise last_error


def _duration_filter(info_dict, *, incomplete):
    duration = info_dict.get("duration")
    if duration and duration > MAX_VIDEO_DURATION:
        return f"Video too long ({duration}s > {MAX_VIDEO_DURATION}s max)"
    return None


def _find_audio_file(job_dir: str) -> str:
    for fname in os.listdir(job_dir):
        if fname.endswith(".wav"):
            return os.path.join(job_dir, fname)
    raise FileNotFoundError(f"No WAV file found in {job_dir}")

import logging
import os
import shutil
import uuid
import yt_dlp

from app.config import TEMP_DIR, MAX_VIDEO_DURATION, YTDLP_COOKIES_FROM_BROWSER

logger = logging.getLogger(__name__)

COOKIES_FILE = "/tmp/yt_cookies.txt"


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


def download_video(url: str, job_id: str) -> dict:
    _ensure_node_in_path()
    """
    Download a YouTube video and extract audio.
    Returns a dict with:
      - video_path: path to the downloaded video file
      - audio_path: path to the extracted audio (WAV)
      - duration:   duration in seconds
      - title:      video title
    """
    job_dir = _make_job_dir(job_id)
    video_path = os.path.join(job_dir, "video.mp4")
    audio_path = os.path.join(job_dir, "audio.wav")

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        "outtmpl": video_path,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "match_filter": _duration_filter,
        **_cookies_opt(),
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

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        duration = info.get("duration", 0)
        title = info.get("title", "video")

    # yt-dlp names the audio file based on the video title — locate it
    audio_path = _find_audio_file(job_dir)

    return {
        "video_path": video_path,
        "audio_path": audio_path,
        "duration": duration,
        "title": title,
    }


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

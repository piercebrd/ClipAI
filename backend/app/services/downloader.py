import os
import uuid
import yt_dlp

from app.config import TEMP_DIR, MAX_VIDEO_DURATION, YTDLP_COOKIES_FROM_BROWSER


def _make_job_dir(job_id: str) -> str:
    job_dir = os.path.join(TEMP_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    return job_dir


def download_video(url: str, job_id: str) -> dict:
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
        "format": "bestvideo+bestaudio/best",
        "outtmpl": video_path,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "match_filter": _duration_filter,
        "cookiesfrombrowser": (YTDLP_COOKIES_FROM_BROWSER,),
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

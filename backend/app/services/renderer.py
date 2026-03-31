import os
import subprocess

import imageio_ffmpeg

from app.config import TEMP_DIR

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

TARGET_W = 1080
TARGET_H = 1920
FONT_SIZE = 52
FONT_COLOR = "white"
SHADOW_COLOR = "black"
SUB_Y_RATIO = 0.80  # 80% down the screen


def render_clip(job_id: str, clip: dict) -> str:
    """
    Render a single clip: trim → crop/scale to 9:16 → burn subtitles.
    Returns the path to the output MP4.
    """
    job_dir = os.path.join(TEMP_DIR, job_id)

    clip_id = clip["id"]
    start = float(clip["start"])
    end = float(clip["end"])
    duration = end - start
    subtitles = clip.get("subtitles", [])
    out_path = os.path.join(job_dir, f"{clip_id}.mp4")

    # Probe source dimensions
    src_w, src_h = _probe_dimensions(os.path.join(job_dir, "video.mp4"))

    # Build crop/scale filter
    crop_scale = _build_crop_scale(src_w, src_h)

    # Build drawtext subtitle filters if supported
    blocks = _group_words(subtitles, min_words=5, max_words=8)
    drawtext_filters = _build_drawtext_filters(blocks, start) if _has_drawtext() else []

    vf_parts = [crop_scale] + drawtext_filters
    vf = ",".join(vf_parts)

    cmd = [
        FFMPEG, "-y",
        "-ss", str(start),
        "-i", os.path.join(job_dir, "video.mp4"),
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264",
        "-crf", "23",
        "-preset", "fast",
        "-c:a", "aac",
        "-ar", "44100",
        "-movflags", "+faststart",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {result.stderr[-600:]}")

    return out_path


# ── Capability check ─────────────────────────────────────────────

_drawtext_supported: bool | None = None


def _has_drawtext() -> bool:
    global _drawtext_supported
    if _drawtext_supported is None:
        result = subprocess.run(
            [FFMPEG, "-filters"], capture_output=True, text=True
        )
        _drawtext_supported = "drawtext" in result.stdout or "drawtext" in result.stderr
    return _drawtext_supported


# ── Subtitle blocks ───────────────────────────────────────────────

def _group_words(words: list[dict], min_words: int, max_words: int) -> list[list[dict]]:
    blocks, current = [], []
    for w in words:
        current.append(w)
        gap = (w["start"] - current[-2]["end"]) if len(current) > 1 else 0
        if len(current) >= max_words or (len(current) >= min_words and gap > 0.4):
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _build_drawtext_filters(blocks: list[list[dict]], clip_start: float) -> list[str]:
    """Build one drawtext filter per subtitle block."""
    filters = []
    y = int(TARGET_H * SUB_Y_RATIO)

    for block in blocks:
        if not block:
            continue
        t_start = block[0]["start"] - clip_start
        t_end = block[-1]["end"] - clip_start
        text = " ".join(w["word"] for w in block)

        # Escape special drawtext characters: \, ', :
        text_escaped = (
            text.replace("\\", "\\\\")
                .replace("'", "\u2019")   # replace apostrophe with curly quote
                .replace(":", "\\:")
                .replace("%", "\\%")
        )

        f = (
            f"drawtext="
            f"text='{text_escaped}':"
            f"fontsize={FONT_SIZE}:"
            f"fontcolor={FONT_COLOR}:"
            f"shadowcolor={SHADOW_COLOR}:shadowx=2:shadowy=2:"
            f"x=(w-text_w)/2:"
            f"y={y}:"
            f"box=1:boxcolor=black@0.4:boxborderw=8:"
            f"enable='between(t\\,{t_start:.3f}\\,{t_end:.3f})'"
        )
        filters.append(f)

    return filters


# ── Video geometry ────────────────────────────────────────────────

def _probe_dimensions(video_path: str) -> tuple[int, int]:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        video_path,
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    w, h = out.split(",")
    return int(w), int(h)


def _build_crop_scale(src_w: int, src_h: int) -> str:
    src_ratio = src_w / src_h
    target_ratio = TARGET_W / TARGET_H  # 0.5625

    if src_ratio > target_ratio:
        # Landscape → crop sides to get 9:16
        crop_h = src_h
        crop_w = int(src_h * target_ratio)
        crop_x = (src_w - crop_w) // 2
        return f"crop={crop_w}:{crop_h}:{crop_x}:0,scale={TARGET_W}:{TARGET_H}"
    else:
        # Portrait / square → blur-pad top and bottom
        scale_h = int(TARGET_W / src_ratio)
        pad_y = (TARGET_H - scale_h) // 2
        return (
            f"split[orig][blur];"
            f"[blur]scale={TARGET_W}:{TARGET_H},boxblur=20:5[bg];"
            f"[orig]scale={TARGET_W}:{scale_h}[fg];"
            f"[bg][fg]overlay=0:{pad_y}"
        )

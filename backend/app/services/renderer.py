import os
import subprocess

import imageio_ffmpeg

from app.config import TEMP_DIR

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

FORMATS = {
    "portrait":       (1080, 1920),
    "landscape_blur": (1080, 1920),
    "square":         (1080, 1080),
    "original":       None,
}

SUBTITLE_STYLES = {
    "tiktok": {
        "fontsize": 52,
        "fontcolor": "white",
        "shadowcolor": "black",
        "shadowx": 2,
        "shadowy": 2,
        "box": 1,
        "boxcolor": "black@0.4",
        "boxborderw": 8,
        "y_ratio": 0.80,
    },
    "minimal": {
        "fontsize": 36,
        "fontcolor": "white",
        "shadowcolor": "black",
        "shadowx": 1,
        "shadowy": 1,
        "box": 0,
        "boxcolor": "black@0.0",
        "boxborderw": 0,
        "y_ratio": 0.85,
    },
}


def render_clip(
    job_id: str,
    clip: dict,
    fmt: str = "portrait",
    subtitle_style: str = "tiktok",
) -> str:
    """
    Render a single clip: trim -> crop/scale -> burn subtitles.
    Returns the path to the output MP4.
    """
    job_dir = os.path.join(TEMP_DIR, job_id)
    video_path = os.path.join(job_dir, "video.mp4")

    clip_id = clip["id"]
    start = float(clip["start"])
    end = float(clip["end"])
    duration = end - start
    subtitles = clip.get("subtitles", [])
    out_path = os.path.join(job_dir, f"{clip_id}.mp4")

    # Probe source dimensions
    src_w, src_h = _probe_dimensions(video_path)

    # Resolve target dimensions
    if fmt == "original":
        target_w, target_h = src_w, src_h
    else:
        target_w, target_h = FORMATS[fmt]

    # Build crop/scale filter
    crop_scale = _build_crop_scale(src_w, src_h, target_w, target_h, fmt)

    # Build subtitle filters
    vf_parts = [crop_scale]
    if subtitle_style != "none" and _has_drawtext():
        style = SUBTITLE_STYLES[subtitle_style]
        blocks = _group_words(subtitles, min_words=5, max_words=8)
        drawtext_filters = _build_drawtext_filters(blocks, start, target_h, style)
        vf_parts += drawtext_filters

    vf = ",".join(vf_parts)

    cmd = [
        FFMPEG, "-y",
        "-ss", str(start),
        "-i", video_path,
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


# -- Capability check ---------------------------------------------------------

_drawtext_supported: bool | None = None


def _has_drawtext() -> bool:
    global _drawtext_supported
    if _drawtext_supported is None:
        result = subprocess.run(
            [FFMPEG, "-filters"], capture_output=True, text=True
        )
        _drawtext_supported = "drawtext" in result.stdout or "drawtext" in result.stderr
    return _drawtext_supported


# -- Subtitle blocks ----------------------------------------------------------

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


def _build_drawtext_filters(
    blocks: list[list[dict]],
    clip_start: float,
    target_h: int,
    style: dict,
) -> list[str]:
    """Build one drawtext filter per subtitle block."""
    filters = []
    y = int(target_h * style["y_ratio"])

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
            f"fontsize={style['fontsize']}:"
            f"fontcolor={style['fontcolor']}:"
            f"shadowcolor={style['shadowcolor']}:"
            f"shadowx={style['shadowx']}:shadowy={style['shadowy']}:"
            f"x=(w-text_w)/2:"
            f"y={y}:"
            f"box={style['box']}:boxcolor={style['boxcolor']}:boxborderw={style['boxborderw']}:"
            f"enable='between(t\\,{t_start:.3f}\\,{t_end:.3f})'"
        )
        filters.append(f)

    return filters


# -- Video geometry ------------------------------------------------------------

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


def _build_crop_scale(
    src_w: int, src_h: int,
    target_w: int, target_h: int,
    fmt: str,
) -> str:
    if fmt == "original":
        return f"scale={target_w}:{target_h}"

    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if fmt == "landscape_blur":
        # Always use blur-pad style regardless of source aspect ratio
        if src_ratio > target_ratio:
            # Source wider than target — scale to fit width, blur-pad top/bottom
            scale_h = int(target_w / src_ratio)
            pad_y = (target_h - scale_h) // 2
            return (
                f"split[orig][blur];"
                f"[blur]scale={target_w}:{target_h},boxblur=20:5[bg];"
                f"[orig]scale={target_w}:{scale_h}[fg];"
                f"[bg][fg]overlay=0:{pad_y}"
            )
        else:
            scale_w = int(target_h * src_ratio)
            pad_x = (target_w - scale_w) // 2
            return (
                f"split[orig][blur];"
                f"[blur]scale={target_w}:{target_h},boxblur=20:5[bg];"
                f"[orig]scale={scale_w}:{target_h}[fg];"
                f"[bg][fg]overlay={pad_x}:0"
            )

    # portrait / square — center crop
    if src_ratio > target_ratio:
        # Source wider → crop sides
        crop_h = src_h
        crop_w = int(src_h * target_ratio)
        crop_x = (src_w - crop_w) // 2
        return f"crop={crop_w}:{crop_h}:{crop_x}:0,scale={target_w}:{target_h}"
    else:
        # Source taller → crop top/bottom
        crop_w = src_w
        crop_h = int(src_w / target_ratio)
        crop_y = (src_h - crop_h) // 2
        return f"crop={crop_w}:{crop_h}:0:{crop_y},scale={target_w}:{target_h}"

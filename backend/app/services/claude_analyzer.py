import json
import time
import uuid
import httpx

from app.config import ANTHROPIC_API_KEY

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"


def _build_transcript_text(words: list[dict]) -> str:
    """Format word list into a readable transcript with timestamps every 30s."""
    lines = []
    current_line = []
    last_marker = -30

    for w in words:
        if w["start"] - last_marker >= 30:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = []
            lines.append(f"\n[{int(w['start'])}s]")
            last_marker = w["start"]
        current_line.append(w["word"])

    if current_line:
        lines.append(" ".join(current_line))

    return " ".join(lines)


def _build_prompt(
    transcript: str,
    duration: float,
    title: str,
    user_prompt: str | None = None,
    min_duration: int = 15,
    max_duration: int = 90,
) -> str:
    user_section = ""
    if user_prompt:
        user_section = f"""
User instructions (IMPORTANT — follow these closely):
{user_prompt}
"""

    return f"""You are an expert viral content editor specializing in TikTok and Instagram Reels.

Analyze this YouTube video transcript and identify the 5 to 10 most viral-worthy moments.

Video title: {title}
Total duration: {int(duration)} seconds ({int(duration // 60)}m{int(duration % 60)}s)
{user_section}
Transcript with timestamps:
{transcript}

Rules:
- Each clip must be between {min_duration} and {max_duration} seconds long
- Distribute clips across the ENTIRE video, not just the beginning
- Prioritize moments with: strong hooks, surprising insights, emotional peaks, clear stories, or actionable tips
- The "start" and "end" must match actual words in the transcript timestamps

Return ONLY a valid JSON array (no markdown, no explanation) in this exact format:
[
  {{
    "title": "short title under 8 words",
    "start": 12.5,
    "end": 45.2,
    "type": "hook",
    "score": 87,
    "reason": "one sentence explaining why this moment is viral"
  }}
]

type must be one of: hook | insight | story | highlight"""


def analyze_transcript(
    words: list[dict],
    duration: float,
    title: str,
    user_prompt: str | None = None,
    min_duration: int = 15,
    max_duration: int = 90,
) -> list[dict]:
    """
    Send transcript to Claude API and get back a list of viral clip candidates.
    Returns a list of clip dicts with id, title, start, end, type, score, reason, subtitles.
    """
    transcript = _build_transcript_text(words)
    prompt = _build_prompt(transcript, duration, title, user_prompt, min_duration, max_duration)

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": MODEL,
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}],
    }

    max_retries = 5
    with httpx.Client(timeout=120) as client:
        for attempt in range(max_retries):
            response = client.post(CLAUDE_API_URL, headers=headers, json=payload)
            if response.status_code in (429, 529) and attempt < max_retries - 1:
                time.sleep(2 ** attempt * 10)  # 10s, 20s, 40s, 80s
                continue
            response.raise_for_status()
            break

    raw = response.json()["content"][0]["text"].strip()

    # Strip markdown code fences if Claude adds them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    clips_raw = json.loads(raw)

    clips = []
    for c in clips_raw:
        start = float(c["start"])
        end = float(c["end"])

        # Clamp duration to max
        if end - start > max_duration:
            end = start + max_duration

        # Attach word-level subtitles for this clip's time range
        subtitles = [
            w for w in words
            if w["start"] >= start - 0.5 and w["end"] <= end + 0.5
        ]

        clips.append({
            "id": str(uuid.uuid4()),
            "title": c.get("title", "Clip"),
            "start": start,
            "end": end,
            "type": c.get("type", "highlight"),
            "score": int(c.get("score", 50)),
            "reason": c.get("reason", ""),
            "subtitles": subtitles,
        })

    # Sort by score descending
    clips.sort(key=lambda x: x["score"], reverse=True)
    return clips

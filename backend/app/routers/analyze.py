import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.downloader import download_video
from app.services.transcriber import transcribe
from app.services.claude_analyzer import analyze_transcript
from app.utils.jobs import create_job, update_job, get_job
from app.utils.cleanup import schedule_cleanup

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    create_job(job_id)
    background_tasks.add_task(
        _run_pipeline, job_id, request.url,
        request.prompt, request.min_duration, request.max_duration,
        request.mode,
    )
    return AnalyzeResponse(job_id=job_id, clips=[])


@router.get("/status/{job_id}")
async def status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, **job}


def _run_pipeline(
    job_id: str, url: str,
    user_prompt: str | None = None,
    min_duration: int = 15,
    max_duration: int = 90,
    mode: str = "viral",
):
    try:
        # Step 1 — Download
        update_job(job_id, step="downloading", progress=10, message="Downloading video...")
        result = download_video(url, job_id)
        update_job(
            job_id, step="downloaded", progress=30,
            message=f"Downloaded: {result['title']} ({result['duration']}s)",
            video_path=result["video_path"],
            audio_path=result["audio_path"],
            duration=result["duration"],
            title=result["title"],
        )

        # Step 2 — Transcribe
        update_job(job_id, step="transcribing", progress=40, message="Transcribing audio...")
        words, language = transcribe(result["audio_path"])
        update_job(
            job_id, step="transcribed", progress=60,
            message=f"Transcribed {len(words)} words ({language})",
            video_path=result["video_path"],
            audio_path=result["audio_path"],
            duration=result["duration"],
            title=result["title"],
            words=words,
            language=language,
        )

        # Step 3 — Clip detection
        if mode == "sequential":
            update_job(job_id, step="analyzing", progress=70, message="Splitting video sequentially...")
            clips = _split_sequential(words, result["duration"], max_duration)
        else:
            update_job(job_id, step="analyzing", progress=70, message="Analyzing with Claude...")
            clips = analyze_transcript(
                words, result["duration"], result["title"],
                user_prompt, min_duration, max_duration,
            )
        update_job(
            job_id, step="analyzed", progress=90,
            message=f"{len(clips)} clips {'découpés' if mode == 'sequential' else 'détectés'}",
            video_path=result["video_path"],
            audio_path=result["audio_path"],
            duration=result["duration"],
            title=result["title"],
            words=words,
            language=language,
            clips=clips,
        )

        # Schedule temp file cleanup after TTL
        schedule_cleanup(job_id)

    except Exception as e:
        update_job(job_id, step="error", progress=0, message=str(e))


def _split_sequential(words: list[dict], duration: float, clip_duration: int) -> list[dict]:
    """Split the entire video into sequential clips of clip_duration seconds."""
    clips = []
    start = 0.0
    index = 1

    while start < duration:
        end = min(start + clip_duration, duration)

        # Skip tiny leftover segments (< 3s)
        if end - start < 3 and clips:
            clips[-1]["end"] = end
            # Extend subtitles of last clip
            clips[-1]["subtitles"] = [
                w for w in words
                if w["start"] >= clips[-1]["start"] - 0.5 and w["end"] <= end + 0.5
            ]
            break

        subtitles = [
            w for w in words
            if w["start"] >= start - 0.5 and w["end"] <= end + 0.5
        ]

        clips.append({
            "id": str(uuid.uuid4()),
            "title": f"Partie {index}",
            "start": start,
            "end": end,
            "type": "highlight",
            "score": 0,
            "reason": f"{int(start)}s - {int(end)}s",
            "subtitles": subtitles,
        })

        start = end
        index += 1

    return clips

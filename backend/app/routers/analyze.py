import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.downloader import download_video
from app.services.transcriber import transcribe
from app.utils.jobs import create_job, update_job, get_job

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    create_job(job_id)
    background_tasks.add_task(_run_pipeline, job_id, request.url)
    return AnalyzeResponse(job_id=job_id, clips=[])


@router.get("/status/{job_id}")
async def status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, **job}


def _run_pipeline(job_id: str, url: str):
    try:
        # Step 1 — Download
        update_job(job_id, step="downloading", progress=10, message="Downloading video...")
        result = download_video(url, job_id)

        update_job(
            job_id,
            step="downloaded",
            progress=30,
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
            job_id,
            step="transcribed",
            progress=60,
            message=f"Transcribed {len(words)} words ({language})",
            video_path=result["video_path"],
            audio_path=result["audio_path"],
            duration=result["duration"],
            title=result["title"],
            words=words,
            language=language,
        )

    except Exception as e:
        update_job(job_id, step="error", progress=0, message=str(e))

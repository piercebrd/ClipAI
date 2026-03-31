import os
import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from app.schemas import RenderRequest, RenderResponse
from app.services.renderer import render_clip
from app.utils.jobs import get_job, update_job
from app.config import TEMP_DIR

router = APIRouter()

# render_id → list of output file paths
_renders: dict[str, list[str]] = {}


@router.post("/render", response_model=RenderResponse)
async def render(request: RenderRequest, background_tasks: BackgroundTasks):
    job = get_job(request.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("step") != "analyzed":
        raise HTTPException(status_code=400, detail=f"Job not ready (step: {job.get('step')})")

    render_id = str(uuid.uuid4())
    _renders[render_id] = []
    background_tasks.add_task(_run_render, render_id, request.job_id, request.clips, job)
    return RenderResponse(render_id=render_id)


@router.get("/render/status/{render_id}")
async def render_status(render_id: str):
    job = _render_jobs.get(render_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Render not found")
    return {"render_id": render_id, **job}


@router.get("/download/{render_id}/{clip_id}")
async def download(render_id: str, clip_id: str):
    files = _renders.get(render_id, [])
    for f in files:
        if clip_id in os.path.basename(f):
            if not os.path.exists(f):
                raise HTTPException(status_code=404, detail="File not found or expired")
            return FileResponse(f, media_type="video/mp4", filename=f"{clip_id}.mp4")
    raise HTTPException(status_code=404, detail="Clip not found")


# ── Internal ──────────────────────────────────────────────────────

_render_jobs: dict[str, dict] = {}


def _run_render(render_id: str, job_id: str, clips_input: list, job: dict):
    _render_jobs[render_id] = {"step": "rendering", "progress": 0, "message": "Starting...", "files": []}

    # Build full clip dicts from job data (merge user timestamps with subtitles)
    job_clips = {c["id"]: c for c in job.get("clips", [])}
    clips_to_render = []
    for ci in clips_input:
        base = job_clips.get(ci.id, {})
        clips_to_render.append({
            "id": ci.id,
            "start": ci.start,
            "end": ci.end,
            "title": base.get("title", "clip"),
            "subtitles": base.get("subtitles", []),
            "format": ci.format,
            "subtitle_style": ci.subtitle_style,
        })

    done = []
    total = len(clips_to_render)

    for i, clip in enumerate(clips_to_render):
        try:
            _render_jobs[render_id]["message"] = f"Rendering clip {i+1}/{total}: {clip['title']}"
            out = render_clip(job_id, clip, fmt=clip.get("format", "portrait"), subtitle_style=clip.get("subtitle_style", "tiktok"))
            done.append(out)
            _renders[render_id].append(out)
            _render_jobs[render_id]["progress"] = int((i + 1) / total * 100)
            _render_jobs[render_id]["files"] = [os.path.basename(f) for f in done]
        except Exception as e:
            _render_jobs[render_id]["message"] = f"Error on clip {clip['id']}: {e}"

    _render_jobs[render_id].update({
        "step": "done",
        "progress": 100,
        "message": f"{len(done)}/{total} clips rendered",
        "files": [os.path.basename(f) for f in done],
    })

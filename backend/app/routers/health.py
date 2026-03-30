import shutil
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    ffmpeg_available = shutil.which("ffmpeg") is not None
    return {
        "status": "ok",
        "service": "ClipAI",
        "ffmpeg": ffmpeg_available,
    }

from typing import Literal

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    url: str
    prompt: str | None = None
    min_duration: int = 15
    max_duration: int = 90


class WordSchema(BaseModel):
    word: str
    start: float
    end: float


class ClipSchema(BaseModel):
    id: str
    title: str
    start: float
    end: float
    type: str
    score: int
    reason: str
    subtitles: list[WordSchema]


class AnalyzeResponse(BaseModel):
    job_id: str
    clips: list[ClipSchema] = []


class RenderClipInput(BaseModel):
    id: str
    start: float
    end: float
    format: Literal["portrait", "landscape_blur", "square", "original"] = "portrait"
    subtitle_style: Literal["tiktok", "minimal", "none"] = "tiktok"


class RenderRequest(BaseModel):
    job_id: str
    clips: list[RenderClipInput]


class RenderResponse(BaseModel):
    render_id: str

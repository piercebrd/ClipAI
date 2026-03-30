from pydantic import BaseModel, HttpUrl
from typing import Optional


class AnalyzeRequest(BaseModel):
    url: str


class JobStatus(BaseModel):
    job_id: str
    step: str
    progress: int
    message: str


class ClipSchema(BaseModel):
    id: str
    title: str
    start: float
    end: float
    type: str
    score: int
    reason: str
    subtitles: list


class AnalyzeResponse(BaseModel):
    job_id: str
    clips: list[ClipSchema] = []

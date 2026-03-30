from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    url: str


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


class RenderRequest(BaseModel):
    job_id: str
    clips: list[RenderClipInput]


class RenderResponse(BaseModel):
    render_id: str

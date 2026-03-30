"""
In-memory job store.
Keyed by job_id, each entry holds step, progress, message, and any result data.
"""

_jobs: dict[str, dict] = {}


def create_job(job_id: str) -> None:
    _jobs[job_id] = {"step": "queued", "progress": 0, "message": "Job created"}


def update_job(job_id: str, step: str, progress: int, message: str, **extra) -> None:
    _jobs[job_id] = {"step": step, "progress": progress, "message": message, **extra}


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)

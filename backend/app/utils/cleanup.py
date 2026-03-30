import os
import shutil
import threading

from app.config import TEMP_DIR, CLIP_TTL_SECONDS


def schedule_cleanup(job_id: str) -> None:
    """Delete job temp directory after TTL seconds."""
    def _delete():
        job_dir = os.path.join(TEMP_DIR, job_id)
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir, ignore_errors=True)

    timer = threading.Timer(CLIP_TTL_SECONDS, _delete)
    timer.daemon = True
    timer.start()

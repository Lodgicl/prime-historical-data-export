"""
Reads a jobs-page JSON file and extracts the list of job IDs.
"""

import json
from pathlib import Path
from typing import List


def load_job_ids(jobs_file: Path) -> List[str]:
    """Return a list of non-empty job ID strings from a jobs-page JSON file."""

    if not jobs_file.exists():
        raise RuntimeError(f"Jobs file not found: {jobs_file}")

    with jobs_file.open("r", encoding="utf-8") as f:
        jobs_json = json.load(f)

    job_ids: List[str] = []

    for item in jobs_json.get("data", []):
        job_id = item.get("id")

        if isinstance(job_id, str):
            job_id = job_id.strip()

            if job_id:
                job_ids.append(job_id)

    if not job_ids:
        raise RuntimeError("No job ids found in jobs page JSON")

    return job_ids
"""
Centralised configuration for the job-batch orchestrator.

All tuneable knobs live here so nothing is scattered across modules.
Reads API credentials and date range from config.json; everything
else has sensible defaults.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class BatchConfig:
    """All settings needed to run a batch of jobs."""

    # API credentials and date range (loaded from config.json)
    client_id: str = ""
    client_secret: str = ""
    username: str = ""
    password: str = ""
    base_url: str = ""
    from_date: str = ""
    to_date: str = ""
    per_page: int = 25

    # Child scripts to run for every job, in order
    scripts_to_run: List[str] = field(default_factory=lambda: [
        "get_site_forms.py",
        "estimates_snapshot_by_job.py",
    ])

    # Throttling
    delay_between_scripts_seconds: int = 10
    delay_between_jobs_seconds: int = 10
    delay_between_pages_seconds: int = 10

    # Retries
    max_retries: int = 2
    retry_delay_seconds: int = 70


def load_config(config_path: Path) -> BatchConfig:
    """Load a BatchConfig from a config.json file."""

    if not config_path.exists():
        raise RuntimeError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    required = [
        "client_id", "client_secret", "username",
        "password", "base_url", "from_date", "to_date",
    ]

    missing = [k for k in required if not raw.get(k)]
    if missing:
        raise RuntimeError("Missing required config fields: " + ", ".join(missing))

    return BatchConfig(
        client_id=raw["client_id"],
        client_secret=raw["client_secret"],
        username=raw["username"],
        password=raw["password"],
        base_url=raw["base_url"],
        from_date=raw["from_date"],
        to_date=raw["to_date"],
        per_page=int(raw.get("per_page", 25)),
    )
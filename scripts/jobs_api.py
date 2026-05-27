"""
Handles authentication and fetching pages of jobs from the API.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urlencode

import requests

from batch_config import BatchConfig


ACCEPT_HEADER = "application/vnd.api.v2+json"


def get_access_token(config: BatchConfig) -> str:
    """Authenticate and return a bearer token."""

    url = f"{config.base_url}/oauth/token"

    body = {
        "grant_type": "password",
        "username": config.username,
        "password": config.password,
        "client_id": config.client_id,
        "client_secret": config.client_secret,
    }

    print(f"\n=== Requesting access token ===")
    print(f"POST {url}")

    response = requests.post(
        url,
        headers={"Accept": ACCEPT_HEADER},
        data=body,
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Auth failed: status={response.status_code}, body={response.text}"
        )

    token = response.json().get("access_token")

    if not token:
        raise RuntimeError("access_token not found in auth response")

    return token


def fetch_jobs_page(
    config: BatchConfig,
    token: str,
    page: int,
) -> Dict[str, Any]:
    """Fetch a single page of jobs created within the configured date range."""

    from_dt = f"{config.from_date} 00:00:00"
    to_dt = f"{config.to_date} 23:59:59"

    q = f"'createdAt'.gte('{from_dt}'),'createdAt'.lte('{to_dt}')"

    params = {
        "q": q,
        "page": page,
        "per_page": config.per_page,
    }

    url = f"{config.base_url}/jobs"
    full_url = f"{url}?{urlencode(params)}"

    print(f"\n=== Fetching jobs page {page} ===")
    print(f"GET {full_url}")

    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": ACCEPT_HEADER,
            "Content-Type": "application/json",
        },
        params=params,
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Fetch jobs failed: status={response.status_code}, body={response.text}"
        )

    return response.json()


def extract_job_ids(page_json: Dict[str, Any]) -> List[str]:
    """Pull the list of job ID strings from a jobs API response."""

    job_ids: List[str] = []

    for item in page_json.get("data", []):
        job_id = item.get("id")
        if isinstance(job_id, str):
            job_id = job_id.strip()
            if job_id:
                job_ids.append(job_id)

    return job_ids


def get_total_pages(page_json: Dict[str, Any]) -> int:
    """Read the total page count from the pagination metadata."""

    pagination = page_json.get("meta", {}).get("pagination", {})
    total_pages = pagination.get("total_pages", 1)

    if isinstance(total_pages, str) and total_pages.strip().isdigit():
        return int(total_pages.strip())

    if isinstance(total_pages, int):
        return total_pages

    return 1


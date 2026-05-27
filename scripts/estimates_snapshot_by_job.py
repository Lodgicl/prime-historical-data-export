import json
import os
from pathlib import Path
from urllib.parse import urlencode

import requests

ACCEPT_HEADER = "application/vnd.api.v2+json"

# Remove these keys anywhere in the nested structure
EXCLUDED_FIELDS_ANYWHERE = {
    "totalIncludingTax",
    "authorisedTotalExcludingTax",
    "authorisedTotalIncludingTax",
    "materialMargin",
    "labourMargin",
    "materialCost",
    "materialTotal",
    "materialMarkup",
    "materialMarkupTotal",
    "labourCost",
    "labourTotal",
    "labourMarkup",
    "labourMarkupTotal",
    "tax",
    "additionalMargin",
}

# Remove these keys only when directly under attributes
EXCLUDED_FIELDS_UNDER_ATTRIBUTES_ONLY = {
    "label",
    "description",
}


def print_section(title):
    print(f"\n=== {title} ===")


def load_config():
    script_dir = Path(__file__).resolve().parent
    config_path = script_dir / "config.json"

    if not config_path.exists():
        raise RuntimeError("config.json not found")

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_job_id(config):
    job_id = os.environ.get("PRIME_JOB_ID") or config.get("job_id", "")
 
    job_id = str(job_id).strip()
 
    if not job_id:
        raise RuntimeError(
            "Job id not found. Set PRIME_JOB_ID env var "
            "or add job_id to config.json."
        )
 
    return job_id


def resolve_output_dir(script_dir: Path, job_id: str) -> Path:
    job_dir = os.environ.get("PRIME_JOB_DIR")

    if job_dir:
        path = Path(job_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    fallback = script_dir / "estimates"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def get_access_token(config):
    url = f"{config['base_url']}/oauth/token"

    body = {
        "grant_type": "password",
        "username": config["username"],
        "password": config["password"],
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
    }

    print_section("Getting Access Token")
    print(f"POST {url}")

    response = requests.post(
        url,
        headers={"Accept": ACCEPT_HEADER},
        data=body,
        timeout=60
    )

    if response.status_code != 200:
        raise RuntimeError(response.text)

    token = response.json().get("access_token")

    if not token:
        raise RuntimeError("access_token missing")

    return token


def get_estimates_snapshot(config, token, job_id):
    base_url = config["base_url"]

    q = f"'jobId'.eq('{job_id}')"

    params = {
        "q": q,
        "page": 1,
        "per_page": 50
    }

    url = f"{base_url}/estimates-snapshot"
    full_url = f"{url}?{urlencode(params)}"

    print_section("Calling estimates-snapshot endpoint")
    print(f"GET {full_url}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": ACCEPT_HEADER,
        "Content-Type": "application/json"
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=60
    )

    if response.status_code != 200:
        raise RuntimeError(response.text)

    return response.json()


def remove_excluded_fields_anywhere(obj):
    if isinstance(obj, dict):
        cleaned = {}

        for key, value in obj.items():
            if key in EXCLUDED_FIELDS_ANYWHERE:
                continue
            cleaned[key] = remove_excluded_fields_anywhere(value)

        return cleaned

    if isinstance(obj, list):
        return [remove_excluded_fields_anywhere(item) for item in obj]

    return obj


def clean_estimate_snapshot(data):
    cleaned = remove_excluded_fields_anywhere(data)

    for entry in cleaned.get("data", []):
        attributes = entry.get("attributes")
        if isinstance(attributes, dict):
            for key in EXCLUDED_FIELDS_UNDER_ATTRIBUTES_ONLY:
                attributes.pop(key, None)

    return cleaned


def main():
    script_dir = Path(__file__).resolve().parent

    config = load_config()
    job_id = resolve_job_id(config)
    token = get_access_token(config)

    print_section(f"Access Token Retrieved for job {job_id}")

    data = get_estimates_snapshot(config, token, job_id)

    pretty = json.dumps(data, indent=2, ensure_ascii=False)

    print_section("Response")
    print(pretty)

    output_dir = resolve_output_dir(script_dir, job_id)

    raw_file = output_dir / "estimates-snapshot.json"
    with open(raw_file, "w", encoding="utf-8") as f:
        f.write(pretty)

    cleaned_data = clean_estimate_snapshot(data)
    cleaned_pretty = json.dumps(cleaned_data, indent=2, ensure_ascii=False)

    cleaned_file = output_dir / "estimates-cleaned.json"
    with open(cleaned_file, "w", encoding="utf-8") as f:
        f.write(cleaned_pretty)

    print_section("Saved")
    print(f"Raw output written to {raw_file}")
    print(f"Cleaned output written to {cleaned_file}")


if __name__ == "__main__":
    main()
import json
import os
import re
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlencode

import requests


ACCEPT_HEADER = "application/vnd.api.v2+json"

# Fields to extract into the simpler output file.
# A field name may match either:
# - a top-level attribute key, e.g. "label", "status", "notes"
# - an item customFieldLabel, e.g. "General Comments", "Client Discussions"
EXTRACT_FIELD_NAMES = [
    "label",
    "status",
    "notes",
    "General Comments",
    "Details of Maintenance Issues",
    "Cause of Damage - Builders Observations",
    "General Observations/Resultant Damage From The Event."
    "Client Discussions",
    "Conclusion",
]


class HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self.parts.append(data)

    def get_text(self) -> str:
        text = " ".join(self.parts)
        text = unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text


def print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def strip_html_to_text(value: str) -> str:
    if not isinstance(value, str):
        return value

    if "<" not in value and "&" not in value:
        return value.strip()

    parser = HtmlTextExtractor()
    parser.feed(value)
    parser.close()
    return parser.get_text()


def normalise_value(custom_field_type: str, value: Any) -> Any:
    if value is None:
        return None

    if custom_field_type == "attachments":
        if isinstance(value, list):
            return str(len(value))
        return "0"

    if custom_field_type == "html":
        text_value = strip_html_to_text(value)
        return text_value if text_value else None

    if isinstance(value, list):
        cleaned_values = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, str):
                item = item.strip()
                if item:
                    cleaned_values.append(item)
            else:
                cleaned_values.append(item)

        if not cleaned_values:
            return None

        return ", ".join(str(item) for item in cleaned_values)

    if isinstance(value, str):
        value = value.strip()
        return value if value else None

    return value


def load_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        raise RuntimeError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    required_fields = [
        "client_id",
        "client_secret",
        "username",
        "password",
        "base_url",
    ]

    missing = [field for field in required_fields if field not in config]
    if missing:
        raise RuntimeError("Missing required config fields: " + ", ".join(missing))

    return config


def get_access_token(
    base_url: str,
    client_id: str,
    client_secret: str,
    username: str,
    password: str,
) -> str:
    token_url = f"{base_url}/oauth/token"

    form_data = {
        "grant_type": "password",
        "username": username,
        "password": password,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    print_section("Requesting access token")
    print(f"POST {token_url}")

    response = requests.post(
        token_url,
        headers={"Accept": ACCEPT_HEADER},
        data=form_data,
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Get access token request failed: "
            f"status={response.status_code}, body={response.text}"
        )

    response_json = response.json()
    access_token = response_json.get("access_token")

    if not access_token:
        raise RuntimeError("access_token not found in auth response")

    return access_token


def get_site_forms_by_job_id(
    base_url: str,
    access_token: str,
    job_id: str,
    page: int = 1,
    per_page: int = 25,
) -> Dict[str, Any]:
    q = f"'jobId'.eq('{job_id}')"

    params = {
        "q": q,
        "page": page,
        "per_page": per_page,
    }

    site_forms_url = f"{base_url}/site-forms"
    full_url = f"{site_forms_url}?{urlencode(params)}"

    print_section("Requesting site forms")
    print(f"GET {full_url}")

    response = requests.get(
        site_forms_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": ACCEPT_HEADER,
            "Content-Type": "application/json",
        },
        params=params,
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Get site forms request failed: "
            f"status={response.status_code}, body={response.text}"
        )

    return response.json()


def add_if_present(target: Dict[str, Any], key: str, value: Any) -> None:
    if value is None:
        return

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return

    target[key] = value


def condense_site_forms(raw_response: Dict[str, Any]) -> Dict[str, Any]:
    condensed_forms: List[Dict[str, Any]] = []

    for entry in raw_response.get("data", []):
        attributes = entry.get("attributes", {})
        condensed: Dict[str, Any] = {}

        add_if_present(condensed, "number", attributes.get("number"))
        add_if_present(condensed, "label", attributes.get("label"))
        add_if_present(condensed, "template", attributes.get("template"))
        add_if_present(condensed, "siteFormTemplateId", attributes.get("siteFormTemplateId"))
        add_if_present(condensed, "status", attributes.get("status"))
        add_if_present(condensed, "notes", attributes.get("notes"))
        add_if_present(condensed, "assignedUser", attributes.get("assignedUser"))
        add_if_present(condensed, "approvedBy", attributes.get("approvedBy"))
        add_if_present(condensed, "approvedAt", attributes.get("approvedAt"))

        for item in attributes.get("items", []):
            label = item.get("customFieldLabel")
            custom_field_type = item.get("customFieldType")
            raw_value = item.get("value")

            if not label:
                continue

            normalised = normalise_value(custom_field_type, raw_value)
            if normalised is None:
                continue

            if custom_field_type == "attachments":
                add_if_present(condensed, f"attachments-{label}", normalised)
            else:
                add_if_present(condensed, label, normalised)

        condensed_forms.append(condensed)

    result: Dict[str, Any] = {
        "site-forms": condensed_forms
    }

    pagination = raw_response.get("meta", {}).get("pagination")
    if pagination:
        result["pagination"] = pagination

    return result


def build_extract_for_form(attributes: Dict[str, Any], field_names: List[str]) -> Dict[str, Any]:
    extracted: Dict[str, Any] = {}

    # First collect top-level attribute matches
    for field_name in field_names:
        if field_name in attributes:
            add_if_present(extracted, field_name, attributes.get(field_name))

    # Then collect matching customFieldLabel values
    items_by_label: Dict[str, Any] = {}

    for item in attributes.get("items", []):
        label = item.get("customFieldLabel")
        custom_field_type = item.get("customFieldType")
        raw_value = item.get("value")

        if not label:
            continue

        normalised = normalise_value(custom_field_type, raw_value)
        if normalised is None:
            continue

        items_by_label[label] = normalised

    for field_name in field_names:
        if field_name in extracted:
            continue
        if field_name in items_by_label:
            add_if_present(extracted, field_name, items_by_label[field_name])

    return extracted


def extract_named_fields(raw_response: Dict[str, Any], field_names: List[str]) -> Dict[str, Any]:
    extracted_forms: List[Dict[str, Any]] = []

    for entry in raw_response.get("data", []):
        attributes = entry.get("attributes", {})
        extracted_form = build_extract_for_form(attributes, field_names)
        extracted_forms.append(extracted_form)

    result: Dict[str, Any] = {
        "site-forms-extract": extracted_forms,
        "fieldsRequested": field_names,
    }

    pagination = raw_response.get("meta", {}).get("pagination")
    if pagination:
        result["pagination"] = pagination

    return result


def resolve_job_id(config: Dict[str, Any]) -> str:
    job_id = os.environ.get("PRIME_JOB_ID") or config.get("job_id", "")
    job_id = str(job_id).strip()
 
    if not job_id:
        raise RuntimeError(
            "Job id not found. Set PRIME_JOB_ID env var "
            "or add job_id to config.json."
        )
 
    return job_id


def get_job_output_dir(script_dir: Path, job_id: str) -> Path:
    job_dir = os.environ.get("PRIME_JOB_DIR")

    if job_dir:
        output_dir = Path(job_dir)
    else:
        # Fallback for manual runs without the orchestrator
        output_dir = script_dir / "site-forms" / job_id

    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    config_path = script_dir / "config.json"

    try:
        config = load_config(config_path)
        job_id = resolve_job_id(config)

        output_dir = get_job_output_dir(script_dir, job_id)
        raw_output_path = output_dir / "site-forms.json"
        summary_output_path = output_dir / "site-forms-summary.json"
        extract_output_path = output_dir / "site-forms-extract.json"

        access_token = get_access_token(
            base_url=config["base_url"],
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            username=config["username"],
            password=config["password"],
        )

        print_section(f"Access token received for job {job_id}")
        print(f"Output directory: {output_dir}")

        site_forms_response = get_site_forms_by_job_id(
            base_url=config["base_url"],
            access_token=access_token,
            job_id=job_id,
            page=1,
            per_page=15,
        )

        print_section("Raw response JSON")
        raw_pretty_json = json.dumps(site_forms_response, indent=2, ensure_ascii=False)
        print(raw_pretty_json)

        with raw_output_path.open("w", encoding="utf-8") as f:
            f.write(raw_pretty_json)

        condensed_response = condense_site_forms(site_forms_response)
        condensed_pretty_json = json.dumps(condensed_response, indent=2, ensure_ascii=False)

        print_section("Condensed response JSON")
        print(condensed_pretty_json)

        with summary_output_path.open("w", encoding="utf-8") as f:
            f.write(condensed_pretty_json)

        extract_response = extract_named_fields(site_forms_response, EXTRACT_FIELD_NAMES)
        extract_pretty_json = json.dumps(extract_response, indent=2, ensure_ascii=False)

        print_section("Extracted fields JSON")
        print(extract_pretty_json)

        with extract_output_path.open("w", encoding="utf-8") as f:
            f.write(extract_pretty_json)

        print_section("Saved")
        print(f"Raw response written to {raw_output_path}")
        print(f"Condensed response written to {summary_output_path}")
        print(f"Extracted fields written to {extract_output_path}")

        return 0

    except Exception as exc:
        print_section("ERROR")
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
import requests
from urllib.parse import urlencode

# Calls to the Prime API https://primeeco.tech/api.prime/v2/docs

BASE_URL = "https://www.primeeco.tech/api.prime/v2"


def get_access_token(
    username: str, password: str, client_id: str, client_secret: str
) -> str:
    print("Getting access token...")
    url = f"{BASE_URL}/oauth/token"
    body = {
        "grant_type": "password",
        "username": username,
        "password": password,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    response = requests.post(
        url, data=body, headers={"Accept": "application/vnd.api.v2+json"}
    )
    response.raise_for_status()
    return response.json().get("access_token")


def get_site_forms(access_token: str, from_date: str) -> list:
    # Example from_date: "2016-12-20"
    return _get_all_pages(
        access_token,
        "site-forms",
        "site forms",
        {"q": f"'createdAt'.gte('{from_date} 00:00:00')"},
    )


def get_locked_estimates(access_token: str) -> list:
    return _get_all_pages(access_token, "estimates-snapshot", "locked estimates")


def get_estimate_categories_snapshot(access_token: str) -> list:
    return _get_all_pages(
        access_token, "estimate-categories-snapshot", "estimate categories"
    )


def get_estimate_items_snapshot(access_token: str) -> list:
    return _get_all_pages(access_token, "estimate-items-snapshot", "estimate items")


def get_jobs(access_token: str, from_date: str) -> list:
    return _get_all_pages(
        access_token, "jobs", "jobs", {"q": f"'createdAt'.gte('{from_date} 00:00:00')"}
    )


def get_non_individual_contacts(access_token: str) -> list:
    return _get_all_pages(
        access_token,
        "contacts",
        "non-individual contacts",
        {"q": "'isIndividual'.eq('false'),'status'.eq('active')"},
    )


def _get_all_pages(
    access_token: str, endpoint: str, label: str, extra_params: dict = None
) -> list:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.api.v2+json",
    }
    params = {"per_page": 250, "page": 1, **(extra_params or {})}
    all_data = []
    total_pages = None
    while True:
        response = requests.get(
            f"{BASE_URL}/{endpoint}", headers=headers, params=params
        )
        response.raise_for_status()
        response_body = response.json()
        all_data.extend(response_body.get("data", []))
        pagination = response_body.get("meta", {}).get("pagination", {})
        if total_pages is None:
            total_pages = pagination.get("total_pages", 1)
            print(f"Fetching {label}: {total_pages} page(s) total...")
        if params["page"] >= total_pages:
            break
        print(f"Fetched page {params['page']} of {total_pages}...")
        params["page"] += 1
    return all_data

import json
import os
from prime_api_v2 import (
    get_access_token,
    get_contacts_snapshot,
    get_estimate_categories_snapshot,
    get_estimate_items_snapshot,
    get_jobs,
    get_locked_estimates,
    get_site_form_template,
    get_site_forms,
)
from datetime import date

# The script uses Prime’s V2 public API (https://www.primeeco.tech/api.prime/v2/docs) to fetch jobs that were created in the last 12 months using {api_uri}/jobs.
# Then for every job we would get the following:

# Locked estimates from {api_uri}/estimates-snapshot. The result set can be stripped of any data but categories and items.
# Site forms from {api_uri}/site-forms by jobId. The result set can be stripped of PII.
# Site form template for the resulting site form from {api_uri}/site-form-templates/{id}


if __name__ == "__main__":

    print("\n=== Starting data export ===")

    access_token = get_access_token(
        os.environ["USERNAME"],
        os.environ["PASSWORD"],
        os.environ["CLIENT_ID"],
        os.environ["CLIENT_SECRET"],
    )

    today = date.today()
    twelve_months_ago = today.replace(year=today.year - 1)

    # Site forms
    site_forms_result = get_site_forms(
        access_token, twelve_months_ago.strftime("%Y-%m-%d")
    )
    with open("site-forms.json", "w") as f:
        json.dump(site_forms_result, f, indent=2)
    print(f"Saved {len(site_forms_result)} records to site-forms.json")

    # Site form templates
    site_form_templates_result = get_site_form_template(access_token)
    with open("site-form-templates.json", "w") as f:
        json.dump(site_form_templates_result, f, indent=2)
    print(
        f"Saved {len(site_form_templates_result)} records to site-form-templates.json"
    )

    # Locked estimates
    locked_estimates_result = get_locked_estimates(access_token)
    with open("locked-estimates.json", "w") as f:
        json.dump(locked_estimates_result, f, indent=2)
    print(f"Saved {len(locked_estimates_result)} records to locked-estimates.json")

    # Estimate categories snapshot
    estimate_categories_result = get_estimate_categories_snapshot(access_token)
    with open("estimate-categories-snapshot.json", "w") as f:
        json.dump(estimate_categories_result, f, indent=2)
    print(
        f"Saved {len(estimate_categories_result)} records to estimate-categories-snapshot.json"
    )

    # Estimate items snapshot
    estimate_items_result = get_estimate_items_snapshot(access_token)
    with open("estimate-items-snapshot.json", "w") as f:
        json.dump(estimate_items_result, f, indent=2)
    print(f"Saved {len(estimate_items_result)} records to estimate-items-snapshot.json")

    # Jobs
    jobs_result = get_jobs(access_token, twelve_months_ago.strftime("%Y-%m-%d"))
    with open("jobs.json", "w") as f:
        json.dump(jobs_result, f, indent=2)
    print(f"Saved {len(jobs_result)} records to jobs.json")

    # Non-individual contacts
    contacts_result = get_contacts_snapshot(access_token)
    with open("contacts-snapshot.json", "w") as f:
        json.dump(contacts_result, f, indent=2)
    print(f"Saved {len(contacts_result)} records to contacts-snapshot.json")

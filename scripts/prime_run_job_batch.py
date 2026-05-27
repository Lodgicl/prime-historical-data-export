"""
Orchestrator: processes a page of jobs by running configured scripts for each.

Saves progress after every successful script so it can resume after failures.
See prime_state.py for instructions on resuming, skipping, or starting over.
"""

import json
import time
from pathlib import Path
 
from batch_config import load_config
from jobs_api import get_access_token, fetch_jobs_page, extract_job_ids, get_total_pages
from prime_state import load_or_create_state, save_state
from script_runner import run_scripts_for_jobs
 
 
def _save_page_json(output_dir: Path, page_number: int, page_json: dict) -> Path:
    """Save a raw jobs-page response to disk for reference."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"jobs-page-{page_number}.json"
 
    with path.open("w", encoding="utf-8") as f:
        json.dump(page_json, f, indent=2, ensure_ascii=False)
 
    print(f"Saved page JSON to {path}")
    return path
 
 
def main() -> int:
    script_dir = Path(__file__).resolve().parent
    config_path = script_dir / "config.json"
    output_dir = script_dir / "out"
 
    try:
        config = load_config(config_path)
 
        state = load_or_create_state(
            output_dir=output_dir,
            from_date=config.from_date,
            to_date=config.to_date,
            per_page=config.per_page,
        )
 
        if state.completed:
            print("\n=== Batch already completed ===")
            print("Delete batch-state.json to run again.")
            return 0
 
        print(f"\n=== Batch: jobs from {config.from_date} to {config.to_date} ===")
 
        token = get_access_token(config)
 
        page = state.next_page
 
        while True:
            page_json = fetch_jobs_page(config, token, page)
 
            # Update total pages from the first response (or any response)
            total_pages = get_total_pages(page_json)
            state.total_pages = total_pages
 
            job_ids = extract_job_ids(page_json)
 
            print(f"\n=== Page {page}/{total_pages} — {len(job_ids)} jobs ===")
 
            if not job_ids:
                print("No jobs on this page, moving on.")
            else:
                _save_page_json(output_dir, page, page_json)
 
                for i, jid in enumerate(job_ids, 1):
                    print(f"  {i}. {jid}")
 
                run_scripts_for_jobs(config, script_dir, output_dir, job_ids, state)
 
            # Page complete — advance to the next one
            page += 1
            state.next_page = page
            save_state(output_dir, state)
 
            if page > total_pages:
                break
 
            print(f"\nWaiting {config.delay_between_pages_seconds}s before next page...")
            time.sleep(config.delay_between_pages_seconds)
 
        state.completed = True
        save_state(output_dir, state)
 
        print("\n=== Batch complete ===")
        print(f"Processed {total_pages} page(s) of jobs.")
        return 0
 
    except Exception as exc:
        print(f"\n=== ERROR ===\n{exc}")
        print("\nTo resume:        re-run this script")
        print("To skip a job:    edit batch-state.json (see prime_state.py)")
        return 1
 
 
if __name__ == "__main__":
    raise SystemExit(main())
 
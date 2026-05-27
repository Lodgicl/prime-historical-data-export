"""
Runs child Python scripts for a given job, with retry logic and throttling.

Updates the batch state after each successful script so the orchestrator
can resume from the right place if something fails.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

from batch_config import BatchConfig
from prime_state import BatchState, save_state


def _run_single_script(
    script_dir: Path,
    script_name: str,
    job_id: str,
    job_dir: Path,
    max_retries: int,
    retry_delay_seconds: int,
) -> None:
    """Execute one child script, retrying on failure."""

    script_path = script_dir / script_name

    if not script_path.exists():
        raise RuntimeError(f"Script not found: {script_path}")

    env = os.environ.copy()
    env["PRIME_JOB_ID"] = job_id
    env["PRIME_JOB_DIR"] = str(job_dir)

    last_error = None

    for attempt in range(1, max_retries + 1):
        print(
            f"\n=== Running {script_name} for job {job_id} "
            f"(attempt {attempt}/{max_retries}) ==="
        )

        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(script_dir),
            env=env,
            text=True,
        )

        if result.returncode == 0:
            return

        last_error = (
            f"{script_name} failed for job {job_id} "
            f"with exit code {result.returncode}"
        )

        if attempt < max_retries:
            delay = retry_delay_seconds * attempt
            print(f"{last_error}. Waiting {delay}s before retry...")
            time.sleep(delay)

    raise RuntimeError(last_error)


def run_scripts_for_jobs(
    config: BatchConfig,
    script_dir: Path,
    output_dir: Path,
    job_ids: list,
    state: BatchState,
) -> None:
    """
    Run all configured scripts for each job in the list.

    Starts from state.next_job_index / state.next_script_index so that
    resumed runs skip already-completed work. Saves progress after
    every successful script.
    """

    scripts = config.scripts_to_run
    start_job = state.next_job_index
    start_script = state.next_script_index

    if start_job > 0 or start_script > 0:
        print(
            f"Resuming from job index {start_job}, "
            f"script index {start_script}"
        )

    for job_index in range(start_job, len(job_ids)):
        job_id = job_ids[job_index]
        job_dir = output_dir / job_id

        print(f"\n=== Processing job {job_index + 1}/{len(job_ids)}: {job_id} ===")

        first_script = start_script if job_index == start_job else 0

        for script_index in range(first_script, len(scripts)):
            script_name = scripts[script_index]

            try:
                _run_single_script(
                    script_dir=script_dir,
                    script_name=script_name,
                    job_id=job_id,
                    job_dir=job_dir,
                    max_retries=config.max_retries,
                    retry_delay_seconds=config.retry_delay_seconds,
                )
            except RuntimeError as exc:
                state.next_job_index = job_index
                state.next_script_index = script_index
                state.last_error = str(exc)
                save_state(output_dir, state)
                raise

            # Script succeeded — advance the checkpoint
            state.next_job_index = job_index
            state.next_script_index = script_index + 1
            state.last_error = ""
            save_state(output_dir, state)

            if script_index < len(scripts) - 1:
                print(f"Waiting {config.delay_between_scripts_seconds}s before next script...")
                time.sleep(config.delay_between_scripts_seconds)

        # All scripts done for this job
        state.last_completed_job_id = job_id
        save_state(output_dir, state)

        if job_index < len(job_ids) - 1:
            print(f"Waiting {config.delay_between_jobs_seconds}s before next job...")
            time.sleep(config.delay_between_jobs_seconds)

    # All jobs on this page done — reset job/script counters for the next page
    state.next_job_index = 0
    state.next_script_index = 0
    save_state(output_dir, state)
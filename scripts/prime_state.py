"""
Tracks batch progress so the orchestrator can resume after a failure.

The state is saved to a JSON file after every successful step.
When the orchestrator starts, it loads the state and skips ahead
to wherever it left off.

── How to resume after a failure ──

  Just re-run the batch script. It reads the state file and picks up
  from the page/job/script that failed.

── How to skip a failing job ──

  Open batch-state.json (in the output folder) and change:

    "next_job_index":    increase by 1  (moves to the next job)
    "next_script_index": set to 0       (start from the first script)

  Then re-run the batch script.

── How to skip to the next page ──

  Open batch-state.json and change:

    "next_page":         increase by 1
    "next_job_index":    set to 0
    "next_script_index": set to 0

  Then re-run the batch script.

── How to start over from scratch ──

  Delete batch-state.json and re-run.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path


STATE_FILE_NAME = "batch-state.json"


@dataclass
class BatchState:
    """Progress checkpoint for a batch run."""

    # Config snapshot — used to detect if someone changed the date range
    from_date: str = ""
    to_date: str = ""
    per_page: int = 25

    # Page-level progress
    next_page: int = 1
    total_pages: int = 0

    # Job-level progress within the current page
    next_job_index: int = 0
    next_script_index: int = 0

    # Bookkeeping
    last_completed_job_id: str = ""
    last_error: str = ""
    completed: bool = False


def state_path(output_dir: Path) -> Path:
    return output_dir / STATE_FILE_NAME


def load_or_create_state(
    output_dir: Path,
    from_date: str,
    to_date: str,
    per_page: int,
) -> BatchState:
    """
    Load existing state from disk, or create a fresh one.

    Raises if the state file belongs to a different date range or page
    size, so you don't accidentally resume the wrong batch.
    """
    path = state_path(output_dir)

    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if data.get("from_date") != from_date or data.get("to_date") != to_date:
            raise RuntimeError(
                "State file date range does not match config. "
                "Delete batch-state.json to start a new batch."
            )

        if int(data.get("per_page", 0)) != per_page:
            raise RuntimeError(
                "State file per_page does not match config. "
                "Delete batch-state.json to start a new batch."
            )

        return BatchState(**{
            k: v for k, v in data.items()
            if k in BatchState.__dataclass_fields__
        })

    return BatchState(
        from_date=from_date,
        to_date=to_date,
        per_page=per_page,
    )


def save_state(output_dir: Path, state: BatchState) -> None:
    """Write the current state to disk."""
    path = state_path(output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(asdict(state), f, indent=2, ensure_ascii=False)
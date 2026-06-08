## Prime historical data retrieval

Assuming you have Python installed on your machine run the following commands to set-up the environment and install dependencies:

    python -m venv .venv
    pip install -r requirements.txt

## Running the export

Set the required environment variables, then run `data_export.py`:

    export PRIME_USERNAME='your_username'
    export PRIME_PASSWORD='your_password'
    export PRIME_CLIENT_ID='your_client_id'
    export PRIME_CLIENT_SECRET='your_client_secret'
    python data_export.py

**Important**: don't forget single quotes.

The script will export data to the following JSON files:

- `site-forms.json`
- `locked-estimates.json`
- `jobs.json`


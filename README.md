## Prime historical data retrieval

Assuming you have Python installed on your machine run the following commands to set-up the environment and install dependencies:

    python -m venv .venv
    pip install -r requirements.txt

## Running the export

Set the required environment variables, then run `data_export.py`:

    export USERNAME=your_username
    export PASSWORD=your_password
    export CLIENT_ID=your_client_id
    export CLIENT_SECRET=your_client_secret
    python data_export.py

The script will export data to the following JSON files:

- `site-forms.json`
- `site-form-templates.json`
- `locked-estimates.json`
- `estimate-categories-snapshot.json`
- `estimate-items-snapshot.json`
- `jobs.json`
- `contacts-snapshot.json`


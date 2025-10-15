# AWS SES / MSG91 Email Campaign Web App

This project provides a web UI to:
- Upload a CSV and send personalized emails via AWS SES
- Send template-based emails via MSG91 with batching and attachments
- Generate downloadable campaign reports by correlating your CSV with SES event logs in S3

## Quickstart

1. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set environment variables as needed:

- `FLASK_SECRET_KEY` (optional)
- `SES_REGION` (default: `ap-south-1`)
- `SES_FROM_EMAIL`
- `SES_CONFIG_SET` (optional)
- `YOUTUBE_LINK` (optional)
- `MSG91_AUTH_KEY` (required for MSG91 sending)
- `MSG91_FROM_EMAIL` (optional)
- `MSG91_DOMAIN` (optional)
- `MSG91_TEMPLATE_ID` (optional default)
- `MSG91_BATCH_SIZE` (default: 100)
- `MSG91_DELAY_BETWEEN_BATCHES` (default: 2)
- `SES_EVENT_BUCKET` (for reports; default: `ses-event-logs-example`)

Ensure your AWS credentials are configured (via `~/.aws/credentials`, environment variables, or instance role) for SES and S3 access.

4. Run the app locally:

```bash
python app.py
```

Open `http://localhost:5000` in your browser.

## Production

Use a production server such as gunicorn or deploy behind a reverse proxy.

```bash
gunicorn -w 2 -b 0.0.0.0:8000 app:app
```

## CSV Format

Headers required: `Email, Name, MembershipID, Mobile`.

## Notes

- Do not commit secrets. Set `MSG91_AUTH_KEY` in the environment.
- SES sending uses a single-threaded background worker per job with light throttling.
- The report generator reads SES event JSON lines from S3 prefixes like `ses/YYYY/MM/DD/`.

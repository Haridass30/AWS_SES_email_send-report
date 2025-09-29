import boto3
import csv
import json

# -------- Configuration --------
BUCKET_NAME = "ses-event-logs-example"
# Use just the date folder (no hour) so every hour below it is included
PREFIX = "ses/2025/09"       # <-- change only the date (YYYY/MM/DD)
INPUT_CSV = "test-mails.csv"
OUTPUT_CSV = "email_campaign_report5.csv"

EVENT_PRIORITY = {
    "Bounce": 5,
    "Complaint": 4,
    "Delivery": 3,
    "DeliveryDelay": 2,
    "Send": 1,
    "Open": 0,
    "Click": 0,
    "Reject": 0,
    "Unknown": -1,
}

s3_client = boto3.client("s3", region_name="ap-south-1")


def list_all_keys(bucket: str, prefix: str):
    """List every object key under prefix, handling pagination."""
    keys = []
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


def fetch_s3_events():
    email_events = {}

    # Grab ALL hour folders under the date prefix
    for key in list_all_keys(BUCKET_NAME, PREFIX):
        if not key.endswith(".json") and not key.endswith(".log"):
            # SES Firehose files usually have no extension,
            # so remove this check if your keys never end with .json/.log
            pass

        s3_object = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
        body = s3_object["Body"].read().decode("utf-8")

        for line in body.splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            event_type = event.get("eventType", "Unknown")
            mail = event.get("mail", {})
            email = mail.get("destination", [""])[0] if mail.get("destination") else ""
            message_id = mail.get("messageId", "")
            if not email or not message_id:
                continue

            error = ""
            if event_type == "Bounce":
                error = event.get("bounce", {}).get("diagnosticCode", "Unknown bounce reason")
            elif event_type == "Complaint":
                error = event.get("complaint", {}).get("complaintFeedbackType", "Unknown complaint")
            elif event_type == "DeliveryDelay":
                delayed = event.get("deliveryDelay", {}).get("delayedRecipients", [{}])
                error = delayed[0].get("diagnosticCode", "Unknown delay reason") if delayed else "Unknown delay reason"
            elif event_type in ["Reject", "HardBounce"]:
                error = event.get("bounce", {}).get("diagnosticCode", "Unknown reason")

            email_events.setdefault(email, []).append(
                {"status": event_type, "message_id": message_id, "error": error}
            )
    return email_events


def generate_report():
    # read recipients from input csv
    recipients = []
    with open(INPUT_CSV, newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 4:
                recipients.append(
                    {
                        "membership_id": row[0].strip(),
                        "name": row[1].strip(),
                        "email": row[2].strip(),
                        "mobile": row[3].strip(),
                    }
                )

    email_events = fetch_s3_events()

    with open(OUTPUT_CSV, "w", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["Email", "Name", "Membership ID", "Mobile", "Status", "Message ID", "Error"])

        for r in recipients:
            events = email_events.get(
                r["email"],
                [{"status": "Unknown", "message_id": "", "error": "No event data"}],
            )
            latest = max(events, key=lambda e: EVENT_PRIORITY.get(e["status"], -1))
            writer.writerow(
                [
                    r["email"],
                    r["name"],
                    r["membership_id"],
                    r["mobile"],
                    latest["status"],
                    latest["message_id"],
                    latest["error"],
                ]
            )

    print(f"Report generated locally: {OUTPUT_CSV}")


if __name__ == "__main__":
    generate_report()

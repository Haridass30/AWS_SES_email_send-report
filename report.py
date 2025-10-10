import boto3
import csv
import json
from botocore.exceptions import ClientError
from datetime import datetime, timedelta

# -------- Configuration --------
BUCKET_NAME = "ses-event-logs-example"
START_DATE = datetime(2025, 10, 10)
END_DATE = datetime(2025, 10, 10)
DATE_PREFIXES = [f"ses/2025/10/{(START_DATE + timedelta(days=x)).strftime('%d')}/" 
                 for x in range((END_DATE - START_DATE).days + 1)]
INPUT_CSV = "camp1.csv"
OUTPUT_CSV = "email_campaign_report2.csv"

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

# AWS S3 client
try:
    s3_client = boto3.client("s3", region_name="ap-south-1")
except Exception as e:
    print(f"⚠️ Failed to initialize S3 client: {e}")
    exit(1)

def list_all_keys(bucket: str, prefix: str):
    """List every object key under prefix, handling pagination."""
    keys = []
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        print(f"📋 Found {len(keys)} objects in bucket '{bucket}' with prefix '{prefix}'")
        return keys
    except ClientError as e:
        print(f"⚠️ Error listing objects for prefix '{prefix}': {e}")
        if e.response['Error']['Code'] == 'NoSuchBucket':
            print(f"Bucket '{bucket}' does not exist.")
        elif e.response['Error']['Code'] == 'AccessDenied':
            print(f"Access denied to bucket '{bucket}'. Check IAM permissions.")
        return []
    except Exception as e:
        print(f"⚠️ General error listing objects for prefix '{prefix}': {e}")
        return []

def fetch_s3_events():
    """Fetch SES events from S3 for multiple date prefixes and return a dict keyed by email."""
    email_events = {}
    file_count = 0

    # Process each date prefix
    for prefix in DATE_PREFIXES:
        print(f"🔍 Checking prefix: {prefix}")
        for key in list_all_keys(BUCKET_NAME, prefix):
            # Process all files (no extension check for SES Firehose files)
            file_count += 1
            print(f"📂 Processing file {file_count}: {key}")
            try:
                s3_object = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
                body = s3_object["Body"].read().decode("utf-8", errors="ignore")
                lines = body.splitlines()
                print(f"📜 {len(lines)} lines in {key}")

                for line in lines:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                        print(f"✅ Parsed JSON: {event.get('eventType')} for {event.get('mail', {}).get('destination', [])}")
                        event_type = event.get("eventType", "Unknown")
                        mail = event.get("mail", {})
                        destinations = mail.get("destination", [])
                        message_id = mail.get("messageId", "")
                        if not destinations or not message_id:
                            print(f"⚠️ Skipping event with missing email or message_id: {event}")
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

                        for email in destinations:
                            email = email.lower().strip()
                            if not email:
                                continue
                            print(f"📧 JSON email: '{email}'")
                            email_events.setdefault(email, []).append(
                                {"status": event_type, "message_id": message_id, "error": error}
                            )
                            print(f"✅ Recorded {event_type} for {email}")
                    except json.JSONDecodeError as e:
                        print(f"⚠️ JSON decode error in {key}: {e}")
                    except Exception as e:
                        print(f"⚠️ General error processing line in {key}: {e}")
            except ClientError as e:
                print(f"⚠️ Error reading {key}: {e}")
            except Exception as e:
                print(f"⚠️ General error reading {key}: {e}")

    print(f"📦 Processed {file_count} JSON files, {len(email_events)} unique emails with events")
    return email_events

def generate_report():
    """Generate CSV report combining input emails with SES events."""
    recipients = []
    try:
        with open(INPUT_CSV, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)  # <-- automatically uses the header row
            for row in reader:
                # Ensure all required columns exist
                if all(k in row for k in ["Email", "Name", "MembershipID", "Mobile"]):
                    recipients.append({
                        "email": row["Email"].strip().lower(),
                        "name": row["Name"].strip(),
                        "membership_id": row["MembershipID"].strip(),
                        "mobile": row["Mobile"].strip(),
                    })
                else:
                    print(f"⚠️ Skipping row with missing columns: {row}")
    except FileNotFoundError:
        print(f"⚠️ Input CSV file '{INPUT_CSV}' not found.")
        return
    except Exception as e:
        print(f"⚠️ Error reading CSV: {e}")
        return


    email_events = fetch_s3_events()

    try:
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as out:
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
        print(f"✅ Report generated locally: {OUTPUT_CSV}")
        print(f"📋 Processed {len(recipients)} recipients, {len(email_events)} emails with events")
    except Exception as e:
        print(f"⚠️ Error writing CSV report: {e}")

if __name__ == "__main__":
    generate_report()
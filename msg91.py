import csv
import json
import requests
import time
import base64

# MSG91 credentials
AUTH_KEY = "395929A2YW1qXt4afm682c115cP1"
TEMPLATE_ID = "bulk2"
FROM_EMAIL = "valuervijai@romexconsultancy.com"
DOMAIN = "romexconsultancy.com"

CSV_FILE = "test-mails.csv"
ATTACHMENT_FILE = "/home/adminuser/Desktop/py_aws/img/IEI NEW CE-10-KVK.jpg"
BATCH_SIZE = 100
DELAY_BETWEEN_BATCHES = 2
def get_attachment(file_path):
    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    filename = file_path.split("/")[-1]
    
    # Determine MIME type based on file extension
    if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
        mime_type = "image/jpeg"
    elif filename.lower().endswith(".png"):
        mime_type = "image/png"
    elif filename.lower().endswith(".pdf"):
        mime_type = "application/pdf"
    else:
        mime_type = "application/octet-stream"  # fallback

    return {
        "file": f"data:{mime_type};base64,{encoded}",  # <-- Include MIME type prefix
        "fileName": filename
    }


attachment = get_attachment(ATTACHMENT_FILE)

def send_email_batch(batch):
    payload = {
        "recipients": batch,
        "from": {"email": FROM_EMAIL},
        "domain": DOMAIN,
        "template_id": TEMPLATE_ID,
        "attachments": [attachment]  # Attach file correctly
    }
    headers = {
        "Content-Type": "application/json",
        "authkey": AUTH_KEY
    }

    response = requests.post("https://control.msg91.com/api/v5/email/send", 
                             headers=headers, data=json.dumps(payload))
    print(response.status_code, response.text)

def main():
    recipients_batch = []
    with open(CSV_FILE, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            recipient = {
                "to": [
                    {"email": row["Email"].strip(), "name": row["Name"].strip()}
                ],
                "variables": {
                    "VAR1": row["Name"].strip(),
                    "VAR2": row["MembershipID"].strip(),
                    "VAR3": row["Mobile"].strip()
                }
            }
            recipients_batch.append(recipient)

            if len(recipients_batch) >= BATCH_SIZE:
                send_email_batch(recipients_batch)
                recipients_batch = []
                time.sleep(DELAY_BETWEEN_BATCHES)

        if recipients_batch:
            send_email_batch(recipients_batch)

if __name__ == "__main__":
    main()

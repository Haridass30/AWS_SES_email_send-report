import os
import csv
import uuid
import time
import json
import threading
from datetime import datetime, timedelta

import boto3
import requests
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_file,
    jsonify,
    flash,
)
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-me")

# Folders for uploads and generated outputs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
GENERATED_DIR = os.path.join(BASE_DIR, "generated")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)


# In-memory job tracking (simple single-process background jobs)
job_states = {}


def _update_job(job_id, **kwargs):
    job = job_states.get(job_id, {})
    job.update(kwargs)
    job_states[job_id] = job


def _read_csv_rows(csv_path):
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _build_ses_client():
    region = os.environ.get("SES_REGION", "ap-south-1")
    return boto3.client("ses", region_name=region)


def _ses_send_worker(job_id, csv_path, attachment_path, subject_template, from_email, config_set, youtube_link, email_template, column_mappings):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication
    from email.mime.image import MIMEImage

    _update_job(job_id, status="running", processed=0, successes=0, failures=0, errors=[])
    rows = _read_csv_rows(csv_path)
    total = len(rows)
    _update_job(job_id, total=total)

    ses = _build_ses_client()

    attachment_bytes = None
    attachment_filename = None
    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            attachment_bytes = f.read()
        attachment_filename = os.path.basename(attachment_path)

    # Load inline images for templates that need them
    inline_images = {}
    if email_template == "kym_template.html":
        sign_image_path = os.path.join(BASE_DIR, "img", "sign.png")
        if os.path.exists(sign_image_path):
            with open(sign_image_path, "rb") as f:
                inline_images["signature"] = f.read()

    # Parse column mappings (JSON string from form)
    mappings = {}
    if column_mappings:
        try:
            mappings = json.loads(column_mappings)
        except:
            # Fallback: try to parse as default structure
            mappings = {}

    # Create reverse mapping: template_var -> csv_column
    reverse_mapping = {v: k for k, v in mappings.items() if v}

    # Auto-detect column mappings if not provided or incomplete
    if rows:
        sample_row = rows[0]
        # Always try to find Email column (required)
        if 'Email' not in reverse_mapping:
            for key in sample_row.keys():
                key_lower = key.lower().strip()
                if key_lower in ['email', 'e-mail', 'email address']:
                    reverse_mapping['Email'] = key
                    break
        
        # Auto-detect other common columns if not mapped
        for key in sample_row.keys():
            key_lower = key.lower().strip()
            if key_lower in ['name', 'full name', 'member name'] and 'Name' not in reverse_mapping:
                reverse_mapping['Name'] = key
            elif key_lower in ['membershipid', 'membership id', 'member id', 'memberid'] and 'Membershipid' not in reverse_mapping:
                reverse_mapping['Membershipid'] = key
            elif key_lower in ['mobile', 'phone', 'phone number', 'mobile number'] and 'Mobile' not in reverse_mapping:
                reverse_mapping['Mobile'] = key

    # Render email HTML using Jinja template in app context
    with app.app_context():
        for row in rows:
            # Extract values using dynamic mapping
            template_vars = {}
            
            # Get email (required) - try multiple methods
            email_col = reverse_mapping.get('Email')
            if not email_col:
                # Last resort: try common column names
                for col in ['Email', 'email', 'E-mail', 'Email Address']:
                    if col in row:
                        email_col = col
                        break
            
            if not email_col:
                errors = job_states[job_id].get("errors", [])
                errors.append({"email": "N/A", "error": "Email column not found in CSV. Please map the email column."})
                _update_job(job_id, processed=job_states[job_id]["processed"] + 1, failures=job_states[job_id]["failures"] + 1, errors=errors)
                continue
            
            to_email = row.get(email_col, "").strip()
            if not to_email:
                errors = job_states[job_id].get("errors", [])
                errors.append({"email": "N/A", "error": f"Email value is empty in row"})
                _update_job(job_id, processed=job_states[job_id]["processed"] + 1, failures=job_states[job_id]["failures"] + 1, errors=errors)
                continue

            # Map all other variables dynamically
            for template_var, csv_col in reverse_mapping.items():
                if template_var != 'Email':  # Already handled
                    template_vars[template_var] = row.get(csv_col, "").strip()
            
            # Add any additional columns from CSV as template variables (for flexibility)
            for csv_col, value in row.items():
                if csv_col not in reverse_mapping.values() and csv_col != email_col:
                    # Use column name as variable name (sanitized)
                    var_name = csv_col.replace(' ', '').replace('-', '').replace('_', '')
                    if var_name and var_name not in template_vars:
                        template_vars[var_name] = value.strip()
            
            # Add YouTube link if provided
            if youtube_link:
                template_vars['YouTubeLink'] = youtube_link

            # Replace subject template variables dynamically
            subject = subject_template
            for var_name, var_value in template_vars.items():
                subject = subject.replace(f"{{{var_name}}}", var_value)
                subject = subject.replace(f"{{{var_name.lower()}}}", var_value)
                subject = subject.replace(f"{{{var_name.upper()}}}", var_value)

            # Render template with all variables
            try:
                html_body = render_template(email_template, **template_vars)
            except Exception as e:
                errors = job_states[job_id].get("errors", [])
                errors.append({"email": to_email, "error": f"Template rendering error: {str(e)}"})
                _update_job(job_id, processed=job_states[job_id]["processed"] + 1, failures=job_states[job_id]["failures"] + 1, errors=errors)
                continue

            # Use 'related' multipart if we have inline images, otherwise use regular multipart
            if inline_images:
                msg = MIMEMultipart('related')
            else:
                msg = MIMEMultipart()
            
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = to_email
            
            # Create alternative part for HTML content
            if inline_images:
                alt = MIMEMultipart('alternative')
                alt.attach(MIMEText(html_body, "html"))
                msg.attach(alt)
            else:
                msg.attach(MIMEText(html_body, "html"))

            # Attach inline images
            for cid, image_data in inline_images.items():
                img = MIMEImage(image_data)
                img.add_header('Content-ID', f'<{cid}>')
                img.add_header('Content-Disposition', 'inline', filename=f'{cid}.png')
                msg.attach(img)

            if attachment_bytes:
                part = MIMEApplication(attachment_bytes)
                part.add_header("Content-Disposition", "attachment", filename=attachment_filename)
                msg.attach(part)

            try:
                kwargs = {
                    "Source": from_email,
                    "Destinations": [to_email],
                    "RawMessage": {"Data": msg.as_string()},
                }
                if config_set:
                    kwargs["ConfigurationSetName"] = config_set
                ses.send_raw_email(**kwargs)
                _update_job(job_id, processed=job_states[job_id]["processed"] + 1, successes=job_states[job_id]["successes"] + 1)
            except Exception as e:
                errors = job_states[job_id].get("errors", [])
                errors.append({"email": to_email, "error": str(e)})
                _update_job(job_id, processed=job_states[job_id]["processed"] + 1, failures=job_states[job_id]["failures"] + 1, errors=errors)

            # Light throttle to avoid SES burst issues
            if job_states[job_id]["processed"] % 14 == 0:
                time.sleep(1)

    _update_job(job_id, status="completed")


def _build_msg91_attachment(attachment_path):
    if not attachment_path or not os.path.exists(attachment_path):
        return None
    with open(attachment_path, "rb") as f:
        import base64

        encoded = base64.b64encode(f.read()).decode("utf-8")
    filename = os.path.basename(attachment_path)
    mime_type = "application/octet-stream"
    lower = filename.lower()
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        mime_type = "image/jpeg"
    elif lower.endswith(".png"):
        mime_type = "image/png"
    elif lower.endswith(".pdf"):
        mime_type = "application/pdf"

    return {"file": f"data:{mime_type};base64,{encoded}", "fileName": filename}


def _msg91_send_worker(job_id, csv_path, attachment_path, template_id, from_email, domain, auth_key, batch_size, delay_between_batches):
    _update_job(job_id, status="running", processed=0, successes=0, failures=0, errors=[])
    rows = _read_csv_rows(csv_path)
    total = len(rows)
    _update_job(job_id, total=total)

    recipients_batch = []
    attachment = _build_msg91_attachment(attachment_path)

    headers = {"Content-Type": "application/json", "authkey": auth_key}
    url = "https://control.msg91.com/api/v5/email/send"

    for row in rows:
        recipient = {
            "to": [{"email": row.get("Email", "").strip(), "name": row.get("Name", "").strip()}],
            "variables": {
                "VAR1": row.get("Name", "").strip(),
                "VAR2": row.get("MembershipID", "").strip(),
                "VAR3": row.get("Mobile", "").strip(),
            },
        }
        recipients_batch.append(recipient)

        if len(recipients_batch) >= batch_size:
            payload = {"recipients": recipients_batch, "from": {"email": from_email}, "domain": domain, "template_id": template_id}
            if attachment:
                payload["attachments"] = [attachment]
            try:
                resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
                if resp.status_code >= 200 and resp.status_code < 300:
                    _update_job(job_id, processed=job_states[job_id]["processed"] + len(recipients_batch), successes=job_states[job_id]["successes"] + len(recipients_batch))
                else:
                    errors = job_states[job_id].get("errors", [])
                    errors.append({"batch": len(recipients_batch), "error": f"HTTP {resp.status_code}: {resp.text[:300]}"})
                    _update_job(job_id, processed=job_states[job_id]["processed"] + len(recipients_batch), failures=job_states[job_id]["failures"] + len(recipients_batch), errors=errors)
            except Exception as e:
                errors = job_states[job_id].get("errors", [])
                errors.append({"batch": len(recipients_batch), "error": str(e)})
                _update_job(job_id, processed=job_states[job_id]["processed"] + len(recipients_batch), failures=job_states[job_id]["failures"] + len(recipients_batch), errors=errors)
            recipients_batch = []
            time.sleep(delay_between_batches)

    if recipients_batch:
        payload = {"recipients": recipients_batch, "from": {"email": from_email}, "domain": domain, "template_id": template_id}
        if attachment:
            payload["attachments"] = [attachment]
        try:
            resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
            if resp.status_code >= 200 and resp.status_code < 300:
                _update_job(job_id, processed=job_states[job_id]["processed"] + len(recipients_batch), successes=job_states[job_id]["successes"] + len(recipients_batch))
            else:
                errors = job_states[job_id].get("errors", [])
                errors.append({"batch": len(recipients_batch), "error": f"HTTP {resp.status_code}: {resp.text[:300]}"})
                _update_job(job_id, processed=job_states[job_id]["processed"] + len(recipients_batch), failures=job_states[job_id]["failures"] + len(recipients_batch), errors=errors)
        except Exception as e:
            errors = job_states[job_id].get("errors", [])
            errors.append({"batch": len(recipients_batch), "error": str(e)})
            _update_job(job_id, processed=job_states[job_id]["processed"] + len(recipients_batch), failures=job_states[job_id]["failures"] + len(recipients_batch), errors=errors)

    _update_job(job_id, status="completed")


def _s3_list_all_keys(s3_client, bucket, prefix):
    keys = []
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


def _report_worker(job_id, bucket, start_date, end_date, input_csv_path, output_csv_path):
    _update_job(job_id, status="running", processed=0, successes=0, failures=0, errors=[], total=0)

    try:
        recipients = []
        with open(input_csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            # Auto-detect column names (case-insensitive)
            first_row = next(reader, None)
            if not first_row:
                raise ValueError("CSV file is empty")
            
            # Find email column (required)
            email_col = None
            for key in first_row.keys():
                if key.lower().strip() in ['email', 'e-mail', 'email address']:
                    email_col = key
                    break
            
            if not email_col:
                raise ValueError("Email column not found in CSV. Please ensure CSV has an 'Email' column.")
            
            # Find other columns (optional)
            name_col = None
            membership_id_col = None
            mobile_col = None
            
            for key in first_row.keys():
                key_lower = key.lower().strip()
                if key_lower in ['name', 'full name', 'member name'] and not name_col:
                    name_col = key
                elif key_lower in ['membershipid', 'membership id', 'member id', 'memberid'] and not membership_id_col:
                    membership_id_col = key
                elif key_lower in ['mobile', 'phone', 'phone number', 'mobile number'] and not mobile_col:
                    mobile_col = key
            
            # Process first row
            email_val = first_row.get(email_col, "").strip().lower()
            if email_val:
                recipients.append({
                    "email": email_val,
                    "name": first_row.get(name_col, "").strip() if name_col else "",
                    "membership_id": first_row.get(membership_id_col, "").strip() if membership_id_col else "",
                    "mobile": first_row.get(mobile_col, "").strip() if mobile_col else "",
                })
            
            # Process remaining rows
            for row in reader:
                email_val = row.get(email_col, "").strip().lower()
                if email_val:
                    recipients.append({
                        "email": email_val,
                        "name": row.get(name_col, "").strip() if name_col else "",
                        "membership_id": row.get(membership_id_col, "").strip() if membership_id_col else "",
                        "mobile": row.get(mobile_col, "").strip() if mobile_col else "",
                    })
        _update_job(job_id, total=len(recipients))
    except Exception as e:
        _update_job(job_id, status="failed")
        errors = job_states[job_id].get("errors", [])
        errors.append({"stage": "read_csv", "error": str(e)})
        _update_job(job_id, errors=errors)
        return

    s3 = boto3.client("s3", region_name=os.environ.get("SES_REGION", "ap-south-1"))

    # Build all date prefixes like ses/YYYY/MM/DD/
    date_prefixes = []
    day = start_date
    while day <= end_date:
        date_prefixes.append(f"ses/{day.strftime('%Y/%m/%d/')}")
        day += timedelta(days=1)

    email_events = {}
    try:
        for prefix in date_prefixes:
            keys = _s3_list_all_keys(s3, bucket, prefix)
            for key in keys:
                obj = s3.get_object(Bucket=bucket, Key=key)
                body = obj["Body"].read().decode("utf-8", errors="ignore")
                for line in body.splitlines():
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                        event_type = event.get("eventType", "Unknown")
                        mail = event.get("mail", {})
                        destinations = mail.get("destination", [])
                        message_id = mail.get("messageId", "")
                        if not destinations or not message_id:
                            continue
                        error_msg = ""
                        if event_type == "Bounce":
                            error_msg = event.get("bounce", {}).get("diagnosticCode", "Unknown bounce reason")
                        elif event_type == "Complaint":
                            error_msg = event.get("complaint", {}).get("complaintFeedbackType", "Unknown complaint")
                        elif event_type == "DeliveryDelay":
                            delayed = event.get("deliveryDelay", {}).get("delayedRecipients", [{}])
                            error_msg = delayed[0].get("diagnosticCode", "Unknown delay reason") if delayed else "Unknown delay reason"
                        elif event_type in ["Reject", "HardBounce"]:
                            error_msg = event.get("bounce", {}).get("diagnosticCode", "Unknown reason")

                        for email in destinations:
                            email_key = email.lower().strip()
                            if not email_key:
                                continue
                            email_events.setdefault(email_key, []).append({"status": event_type, "message_id": message_id, "error": error_msg})
                    except json.JSONDecodeError:
                        # Ignore malformed JSON lines
                        continue
                    except Exception:
                        # Ignore any unexpected line-level errors and continue
                        continue
        # write report
        with open(output_csv_path, "w", newline="", encoding="utf-8-sig") as out:
            writer = csv.writer(out)
            writer.writerow(["Email", "Name", "Membership ID", "Mobile", "Status", "Message ID", "Error"])
            for r in recipients:
                events = email_events.get(r["email"], [{"status": "Unknown", "message_id": "", "error": "No event data"}])
                # priority mapping
                priority = {"Bounce": 5, "Complaint": 4, "Delivery": 3, "DeliveryDelay": 2, "Send": 1}
                latest = max(events, key=lambda e: priority.get(e["status"], -1))
                writer.writerow([r["email"], r["name"], r["membership_id"], r["mobile"], latest["status"], latest["message_id"], latest["error"]])
        _update_job(job_id, status="completed", output_path=output_csv_path)
    except Exception as e:
        errors = job_states[job_id].get("errors", [])
        errors.append({"stage": "s3_or_write", "error": str(e)})
        _update_job(job_id, status="failed", errors=errors)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/preview-csv", methods=["POST"])
def preview_csv():
    """Preview CSV columns for dynamic mapping"""
    csv_file = request.files.get("csv_file")
    if not csv_file:
        return jsonify({"error": "No CSV file provided"}), 400

    try:
        csv_filename = secure_filename(csv_file.filename or f"preview-{uuid.uuid4().hex}.csv")
        csv_path = os.path.join(UPLOAD_DIR, csv_filename)
        csv_file.save(csv_path)

        rows = _read_csv_rows(csv_path)
        if not rows:
            return jsonify({"error": "CSV file is empty"}), 400

        columns = list(rows[0].keys())
        # Clean up preview file
        try:
            os.remove(csv_path)
        except:
            pass

        return jsonify({"columns": columns, "sample_row": rows[0] if rows else {}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/send/ses", methods=["GET", "POST"])
def send_ses():
    default_subject = os.environ.get(
        "SES_SUBJECT_TEMPLATE",
        "{Name} {Membershipid} - IE(I) Council Election Appeal",
    )
    default_from = os.environ.get("SES_FROM_EMAIL", "valuervijai@romexconsultancy.com")
    default_youtube = os.environ.get("YOUTUBE_LINK", "https://www.youtube.com/watch?v=Nx-iCLXUYDw&feature=youtu.be")
    default_config_set = os.environ.get("SES_CONFIG_SET", "")

    if request.method == "POST":
        csv_file = request.files.get("csv_file")
        attachment_file = request.files.get("attachment")
        subject_template = request.form.get("subject_template") or default_subject
        from_email = request.form.get("from_email") or default_from
        youtube_link = request.form.get("youtube_link") or default_youtube
        config_set = request.form.get("config_set") or default_config_set
        email_template = request.form.get("email_template") or "email_template.html"
        column_mappings = request.form.get("column_mappings") or "{}"

        if not csv_file:
            flash("CSV file is required.", "danger")
            return redirect(request.url)

        csv_filename = secure_filename(csv_file.filename or f"recipients-{uuid.uuid4().hex}.csv")
        csv_path = os.path.join(UPLOAD_DIR, csv_filename)
        csv_file.save(csv_path)

        attachment_path = None
        if attachment_file and attachment_file.filename:
            attach_filename = secure_filename(attachment_file.filename)
            attachment_path = os.path.join(UPLOAD_DIR, attach_filename)
            attachment_file.save(attachment_path)

        job_id = uuid.uuid4().hex
        job_states[job_id] = {
            "id": job_id,
            "type": "ses",
            "created": time.time(),
            "description": "SES send",
        }
        thread = threading.Thread(
            target=_ses_send_worker,
            args=(job_id, csv_path, attachment_path, subject_template, from_email, config_set, youtube_link, email_template, column_mappings),
            daemon=True,
        )
        thread.start()
        return redirect(url_for("progress", job_id=job_id))

    return render_template(
        "send_ses.html",
        default_subject=default_subject,
        default_from=default_from,
        default_youtube=default_youtube,
        default_config_set=default_config_set,
    )


@app.route("/send/msg91", methods=["GET", "POST"])
def send_msg91():
    default_from = os.environ.get("MSG91_FROM_EMAIL", "valuervijai@romexconsultancy.com")
    default_domain = os.environ.get("MSG91_DOMAIN", "romexconsultancy.com")
    default_template_id = os.environ.get("MSG91_TEMPLATE_ID", "")
    default_batch_size = int(os.environ.get("MSG91_BATCH_SIZE", "100"))
    default_delay = int(os.environ.get("MSG91_DELAY_BETWEEN_BATCHES", "2"))

    if request.method == "POST":
        csv_file = request.files.get("test-mails.csv")
        attachment_file = request.files.get("attachment")
        template_id = request.form.get("template_id") or default_template_id
        from_email = request.form.get("from_email") or default_from
        domain = request.form.get("domain") or default_domain
        batch_size = int(request.form.get("batch_size") or default_batch_size)
        delay_between_batches = int(request.form.get("delay_between_batches") or default_delay)
        auth_key = os.environ.get("MSG91_AUTH_KEY")

        if not auth_key:
            flash("MSG91_AUTH_KEY is not set in environment.", "danger")
            return redirect(request.url)
        if not template_id:
            flash("Template ID is required.", "danger")
            return redirect(request.url)
        if not csv_file:
            flash("CSV file is required.", "danger")
            return redirect(request.url)

        csv_filename = secure_filename(csv_file.filename or f"recipients-{uuid.uuid4().hex}.csv")
        csv_path = os.path.join(UPLOAD_DIR, csv_filename)
        csv_file.save(csv_path)

        attachment_path = None
        if attachment_file and attachment_file.filename:
            attach_filename = secure_filename(attachment_file.filename)
            attachment_path = os.path.join(UPLOAD_DIR, attach_filename)
            attachment_file.save(attachment_path)

        job_id = uuid.uuid4().hex
        job_states[job_id] = {
            "id": job_id,
            "type": "msg91",
            "created": time.time(),
            "description": "MSG91 send",
        }
        thread = threading.Thread(
            target=_msg91_send_worker,
            args=(job_id, csv_path, attachment_path, template_id, from_email, domain, auth_key, batch_size, delay_between_batches),
            daemon=True,
        )
        thread.start()
        return redirect(url_for("progress", job_id=job_id))

    return render_template(
        "send_msg91.html",
        default_from=default_from,
        default_domain=default_domain,
        default_template_id=default_template_id,
        default_batch_size=default_batch_size,
        default_delay=default_delay,
    )


@app.route("/report", methods=["GET", "POST"])
def report():
    default_bucket = os.environ.get("SES_EVENT_BUCKET", "ses-event-logs-example")
    if request.method == "POST":
        bucket = request.form.get("bucket") or default_bucket
        start_date_str = request.form.get("start_date")
        end_date_str = request.form.get("end_date")
        input_csv = request.files.get("input_csv")

        if not input_csv:
            flash("Input CSV is required.", "danger")
            return redirect(request.url)
        if not start_date_str or not end_date_str:
            flash("Start and End dates are required.", "danger")
            return redirect(request.url)

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

        input_csv_name = secure_filename(input_csv.filename or f"input-{uuid.uuid4().hex}.csv")
        input_csv_path = os.path.join(UPLOAD_DIR, input_csv_name)
        input_csv.save(input_csv_path)

        out_name = f"email_campaign_report-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
        out_path = os.path.join(GENERATED_DIR, out_name)

        job_id = uuid.uuid4().hex
        job_states[job_id] = {"id": job_id, "type": "report", "created": time.time(), "description": "Generate report"}
        thread = threading.Thread(target=_report_worker, args=(job_id, bucket, start_date, end_date, input_csv_path, out_path), daemon=True)
        thread.start()
        return redirect(url_for("progress", job_id=job_id))

    return render_template("report.html", default_bucket=default_bucket)


@app.route("/progress/<job_id>")
def progress(job_id):
    job = job_states.get(job_id)
    if not job:
        flash("Job not found", "danger")
        return redirect(url_for("index"))
    return render_template("progress.html", job_id=job_id)


@app.route("/status/<job_id>")
def status(job_id):
    job = job_states.get(job_id)
    if not job:
        return jsonify({"error": "not found"}), 404
    return jsonify(job)


@app.route("/download/<path:filename>")
def download(filename):
    path = os.path.join(GENERATED_DIR, filename)
    if not os.path.exists(path):
        flash("File not found", "danger")
        return redirect(url_for("index"))
    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)

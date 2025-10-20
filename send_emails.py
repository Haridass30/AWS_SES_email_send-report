import boto3
import csv
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage

ses_client = boto3.client('ses', region_name='ap-south-1')

FROM_EMAIL = 'valuervijai@romexconsultancy.com'

ATTACHMENT_PATH1 = r'C:\Users\Admin\Documents\AWS_SES_email_send-report\img\1.png'
ATTACHMENT_PATH2 = r'C:\Users\Admin\Documents\AWS_SES_email_send-report\img\MR_K_VIJAYA_KUMAR.png'

SUBJECT = '{Name} - TOGETHER WE ACHIEVED IT! ALL INDIA NO.1 – THANK YOU FOR YOUR SUPPORT- WARM FESTIVAL WISHES.'
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>IEI Council Civil Election – An appeal to vote for – MR. K. VIJAYA KUMAR (F-1183849)</title>
  <style>
    body {{
      font-family: "Times New Roman", Times, serif !important;
      line-height: 1.6;
      color: #000;
    }}
    h1, h2, h3, h4, h5, h6, p, li, a, span, strong, b {{
      font-family: "Times New Roman", Times, serif !important;
    }}
    .blue-bold {{ font-weight: bold; color: blue; }}
    .red-center {{ color: red; text-align: center; }}
    h1, h3 {{ margin: 0.5em 0; }}
    ol {{ margin-left: 20px; }}
    ul {{ line-height: 1.8; }}
    ul ul {{
      line-height: 1.6;
      margin-top: 5px;
    }}
    li {{ margin-bottom: 10px; }}
  </style>
</head>
<body>
<div style="line-height:1.2;font-size:17px;">
  <h3 style="font-weight:bold;">To,</h3>
  <h3 class="blue-bold">{Name}</h3>
  <h3 class="blue-bold">{Membershipid}</h3>
  <h3 class="blue-bold">Mobile: {Mobile}</h3>
</div>

<div style="line-height:1.4;font-size:18px;">

  <img src="cid:image1"
       alt="MR. K. VIJAYA KUMAR"
       style="max-width:100%; height:auto; display:block; margin:auto; margin-top:30px;">

  <h3 style="text-align:center;">
    <span style="color:red;">10.</span>
    <span style="color:blue;">MR K VIJAYA KUMAR</span>,
  </h3>

  <h3 style="color:red;text-align:center;font-size:18px;">
    (ELECTED AS THE ALL INDIA NO.1 CANDIDATE IN THE IEI COUNCIL CIVIL DIVISION ELECTION (2025–2029)
  </h3>

  <h3 style="color:red;">DEAR {Name},</h3>
  <p style="font-family:Georgia, 'Times New Roman', Times, serif; font-size:17px;">
    Greetings!
  </p>
  <p style="font-size:17px;">
    I am delighted to share the wonderful news that, with your kind support and blessings, 
    <span style="color:blue; font-weight:bold;">I have been elected as the All India No. 1 Candidate in the IEI Council Election – Civil Engineering Division (2025–2029).</span><br><br>

    My sincere thanks to you for your <span style="color:red; font-weight:bold;">valuable vote, encouragement, and goodwill</span>. 
    Your trust and support have made this success possible, and I am truly grateful for it. 🙏<br><br>

    As I take up this responsibility, I assure you of my continued commitment to work for the growth of 
    <span style="color:red; font-weight:bold;">our Institution and the Civil Engineering fraternity</span> with dedication and integrity.<br><br>

    Wishing you and your family a very <span style="color:blue; font-weight:bold;">Happy and Prosperous Festival Season</span> filled with joy, peace, and success. 🌺✨<br><br>

    With warm regards and gratitude,
  </p>

  <img src="cid:image2"
       alt="MR. K. VIJAYA KUMAR"
       style="max-width:100%; height:900; display:block; margin:800; margin-top:20px;">

  <h3 style="text-align:center;">“Building Tomorrow Together | एक साथ मिलकर कल का निर्माण”</h3>

  <h3>Thanks & Regards,</h3>
  <p style="font-size:17px;">
    <img src="cid:image3"
         alt="Vote for MR. K. VIJAYA KUMAR"
         style="max-width:100%; height:100px;">
  </p>

  <p>
    <span style="font-weight:bold;font-size:18px">Mr. K. Vijaya Kumar</span><br>
    Chairman – IOV Madurai Branch<br>
    Past Chairman – IEI Madurai Local Centre<br>
    IEI Tamil Nadu State Committee Member<br>
    Romex Consultancy | <a href="http://www.romexconsultancy.com">www.romexconsultancy.com</a><br>
    📱 +91 98421 51415 | ✉ <a href="mailto:valuervijai@romexconsultancy.com">valuervijai@romexconsultancy.com</a>
  </p>
</div>
</body>
</html>
"""

def send_email(to_email, name, membership_id, mobile):
    body_html = HTML_TEMPLATE.format(
        Name=name,
        Membershipid=membership_id,
        Mobile=mobile
    )
    subject = SUBJECT.format(Name=name, Membershipid=membership_id)

    msg = MIMEMultipart('related')
    msg['Subject'] = subject
    msg['From'] = FROM_EMAIL
    msg['To'] = to_email

    alt = MIMEMultipart('alternative')
    alt.attach(MIMEText(body_html, 'html'))
    msg.attach(alt)

    # Inline images
    for cid, path in [('image1', ATTACHMENT_PATH1), ('image2', ATTACHMENT_PATH2)]:
        if os.path.exists(path):
            with open(path, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', f'<{cid}>')
                img.add_header('Content-Disposition', 'inline', filename=os.path.basename(path))
                msg.attach(img)

    # Extra PDF/image attachment (optional)
    # if os.path.exists(ATTACHMENT_PATH4):
    #     with open(ATTACHMENT_PATH4, 'rb') as f:
    #         part = MIMEApplication(f.read())
    #         part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(ATTACHMENT_PATH4))
    #         msg.attach(part)

    try:
        ses_client.send_raw_email(
            Source=FROM_EMAIL,
            Destinations=[to_email],
            RawMessage={'Data': msg.as_string()},
            ConfigurationSetName='ses-event-config'
        )
        print(f"✅ Sent: {to_email}")
    except Exception as e:
        print(f"❌ Error sending to {to_email}: {e}")

# CSV reading and threaded sending
CSV_FILE = 'camp4.csv'
MAX_THREADS = 14
with open(CSV_FILE, 'r') as file:
    reader = csv.DictReader(file)
    recipients = list(reader)

start = time.time()
futures = []
with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
    for row in recipients:
        futures.append(executor.submit(
            send_email,
            row['Email'].strip(),
            row['Name'].strip(),
            row['MembershipID'].strip(),
            row['Mobile'].strip()
        ))
        if len(futures) % 14 == 0:
            time.sleep(1)
    for f in as_completed(futures):
        f.result()

print(f"✅ All {len(recipients)} emails sent in {time.time()-start:.2f} seconds!")
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

ATTACHMENT_PATH1 = '/home/adminuser/Desktop/py_aws/img/1.png'
ATTACHMENT_PATH2 = '/home/adminuser/Desktop/py_aws/img/2.png'
ATTACHMENT_PATH3 = '/home/adminuser/Desktop/py_aws/img/3.png'
ATTACHMENT_PATH4 = '/home/adminuser/Desktop/py_aws/img/IEI NEW CE-10-KVK.jpg'
YOUTUBE_LINK = 'https://www.youtube.com/watch?v=Nx-iCLXUYDw&feature=youtu.be'

SUBJECT = '{Name}-10. MR K VIJAYA KUMAR (F-1183849) -TOGETHER, WE BUILD THE FUTURE – SUPPORT & ELECT THE ROW 10 – FOR IEI COUNCIL – CIVIL DIVISION ELECTION REMINDER.'

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
    ul {{
      line-height: 1.8;
    }}
    ul ul {{
      line-height: 1.6;
      margin-top: 5px;
    }}
    li {{
      margin-bottom: 10px;
    }}
  </style>
</head>
<body>
<div style="line-height:1.2;font-size:17px;">
  <h3 style="font-weight:bold;">To,</h3>
  <h3 class="blue-bold">{Name}</h3>
  <h3 class="blue-bold">{Membershipid}</h3>
  <h3 class="blue-bold">Mobile: {Mobile}</h3>
</div>

<div style="line-height:1.2;font-size:19px;">
  <h3 class="red-center">
    <span style="color:red;">10.</span>
    <span style="color:blue;">MR. K. VIJAYA KUMAR</span>
    <span style="color:red;">(F-1183849)</span>
  </h3>

  <h3 style="color:red;text-align:center;">
    An Appeal to Vote For
    <span style="color:blue;"> IE(I) Governing Council Election –</span>
    Civil Engineering <br> Division – <br> Session 2025–2029
  </h3>

  <h3 style="color:red;text-align:center;">
    Election Starting Date: 04/10/2025 – Election Closing Date: 18/10/2025
  </h3>

  <p style="text-align:center; font-size:20px;">
    For More Information click
    <a href="https://www.ieielections.in">https://www.ieielections.in</a>
  </p>

  <p style="text-align:center; font-size:20px;">
    <strong>Please note:</strong> Voting is completely online through the above link (no ballot papers).
  </p>
</div>
<h3 style="color:red;text-align:center;margin-top:12px;font-size:20px;">
  <span style='text-align:center;font-size:17px;color:green'>GENTLE REMINDER</span><br>
  <span style="color:blue;">ONLINE VOTING IS ONGOING</span><br>
  START DATE: 04.10.2025 / ENDING DATE: 18.10.2025
</h3>

<img src="cid:image1"
     alt="MR. K. VIJAYA KUMAR"
     style="max-width:100%; display:block; margin:auto; margin-top:30px;">

<h3 style="text-align:center;">
  <span style="color:red;">10.</span>
  <span style="color:blue;">MR K VIJAYA KUMAR</span>,
</h3>

<h3 style="color:red;text-align:center;font-size:19px;">
  (10th ROW IN THE CANDIDATE SELECTION PANEL)
</h3>

<h3 style="text-align:center;font-size:19px;">
  <span style="color:blue;">Watch this short YouTube video for the step-by-step voting procedure:</span><br>
  <span style='text-align:center;font-size:17px;color:green'>Click</span>
</h3>

<div style="text-align:center;">
  <a href="{YouTubeLink}">{YouTubeLink}</a>
</div>
<br>

<h3 style="color:red;">DEAR {Name},</h3>
<p style="font-family: Georgia, 'Times New Roman', Times, serif;font-size:17px;">
Greetings! Hope you are doing well and in good health.
</p>
<p style='font-size:17px'>This is a gentle reminder and renewed request for your <strong>valuable Vote & Support</strong> in the <strong>IE(I) Council Election – Civil Engineering Division (2025–2029).</strong></p>
<p style='font-size:17px'>I, <strong>10. MR K VIJAYA KUMAR (F-1183849),</strong> am contesting for the <strong>Governing Council (Civil).</strong><br>
The <strong>online voting is in progress from 4th to 18th October 2025</strong> — and only <strong>a few days remain</strong> to cast your vote.</p>
<p style='font-size:17px'>
 In the previous term (2021–2025), I missed success by just <strong>18 votes (6th All-India).</strong> With your kind support this time, I am confident of converting that near miss into success and continuing to serve our profession with greater commitment.
</p>
<p style='font-size:17px'>
If you’ve <strong>already voted,</strong> I sincerely thank you for your kind support. 🙏<br>
If <strong>not yet voted,</strong> please take a few minutes to cast your valuable vote.<br>
For your convenience, I’ve again attached the <strong>Step-by-Step Online Voting Guide.</strong>
</p>

<p style='font-size:17px'>
<strong>Your single vote truly matters — it can make all the difference.<strong>
Let’s together strengthen our Institution and the Civil Engineering fraternity.
</p>

<img src="cid:image2"
     alt="MR. K. VIJAYA KUMAR"
     style="height:900px; width:800px; display:block; margin:auto;">

<h3 style="text-align:center;margin-top:30px;">
  👉 Kindly select the Row <span style="color:red;">10.</span>
  <span style="color:blue;">MR. K. VIJAYA KUMAR (F-1183849)</span> while casting your online vote.
</h3>

<h3 style="text-align:center;">“Building Tomorrow Together | एक साथ मिलकर कल का निर्माण”</h3>

<h3>Thanks & Regards,</h3>
<p style='font-size:17px'>
  <img src="cid:image3"
       alt="Vote for MR. K. VIJAYA KUMAR"
       style="max-width:100%; height:100px;">
</p>

<p>
  <span style="font-weight:bold;font-size:18px">Mr.K. Vijaya Kumar</span><br>
  Chairman – IOV Madurai Branch<br>
  Past Chairman – IE(I) Madurai Local Centre<br>
  IE(I) Tamil Nadu State Committee Member<br>
  Romex Consultancy | <a href="http://www.romexconsultancy.com">www.romexconsultancy.com</a><br>
  📱 +91 98421 51415 | ✉️ <a href="mailto:valuervijai@romexconsultancy.com">valuervijai@romexconsultancy.com</a>
</p>
</body>
</html>
"""

def send_email(to_email, name, membership_id, mobile):
    body_html = HTML_TEMPLATE.format(
        Name=name,
        Membershipid=membership_id,
        Mobile=mobile,
        YouTubeLink=YOUTUBE_LINK
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
    for cid, path in [('image1', ATTACHMENT_PATH1), ('image2', ATTACHMENT_PATH2), ('image3', ATTACHMENT_PATH3)]:
        if os.path.exists(path):
            with open(path, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', f'<{cid}>')
                img.add_header('Content-Disposition', 'inline', filename=os.path.basename(path))
                msg.attach(img)

    # Extra PDF/image attachment (optional)
    if os.path.exists(ATTACHMENT_PATH4):
        with open(ATTACHMENT_PATH4, 'rb') as f:
            part = MIMEApplication(f.read())
            part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(ATTACHMENT_PATH4))
            msg.attach(part)

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
CSV_FILE = 'camp3.csv'
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

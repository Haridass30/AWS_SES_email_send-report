import boto3
import csv
import time

# Configure SES client (replace 'us-east-1' with your SES region)
ses_client = boto3.client('ses', region_name='ap-south-1')

# Email details
FROM_EMAIL = 'valuervijai@romexconsultancy.com'  # Must be verified in SES
SUBJECT = 'IEI Council Civil Election - An appeal to vote for - MR. K. VIJAYA KUMAR (F-1183849)'

# Full HTML template with personalization and image placeholders
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>IEI Council Civil Election – An appeal to vote for – MR. K. VIJAYA KUMAR (F-1183849)</title>
  <style>
    body {{
      font-family: "Times New Roman", Times, serif;
      line-height: 1.6;
      color: #000;
    }}
    .blue-bold {{ font-weight: bold; color: blue; }}
    .red-center {{ color: red; text-align: center; }}
    h1, h3 {{ margin: 0.5em 0; }}
    ol {{ margin-left: 20px; }}
    ul {{
    line-height: 1.8; /* space between main list items */
  }}

  ul ul {{
    line-height: 1.6; /* slightly smaller space for nested lists */
    margin-top: 5px;  /* extra spacing above nested list */
  }}

  li {{
    margin-bottom: 10px; /* extra space between items */
  }}
  </style>
</head>
<body>
<div style="line-height:1.2;font-size:17px">
  <h3 style="font-weight:bold;">To,</h3>
  <h3 class="blue-bold">&lt;{name}&gt;</h3>
  <h3 class="blue-bold">&lt;{membership_id}&gt;</h3>
  <h3 class="blue-bold">&lt;Mobile: {mobile}&gt;</h3>
</div>
<div style="line-height:1.2;font-size:19px">  <!-- optional global tweak -->
  <h3 class="red-center" style="margin:4px 0; line-height:1.2;">
    <span style="color:red;">11.</span>
    <span style="color:blue;">MR. K. VIJAYA KUMAR</span>
    <span style="color:red;">(F-1183849)</span>
  </h3>

  <h3 style="color:red;text-align:center;margin:4px 0;line-height:1.2;">
    An Appeal to Vote For
    <span style="color:blue;"> IE(I) Governing Council Election –</span>
    Civil Engineering <br> Division – <br> Session 2025–2029
  </h3>

  <h3 style="color:red;text-align:center;margin:4px 0;line-height:1.2;">
    Election Starting Date: 04/10/2025 – Election Closing Date: 18/10/2025
  </h3>

  <p style="text-align:center; margin:4px 0;font-size:20px">For More Information click
     <a href="https://www.ieielections.in">https://www.ieielections.in</a>
  </p>
</div>

 <img src="https://s3.ap-south-1.amazonaws.com/cdn.kaaikanistore.com/1.png"
     alt="MR. K. VIJAYA KUMAR"
     style="max-width:100%; display:block; margin:auto;margin-top:30px">
 <h3 style="text-align:center">
    <span style="color:red;">11.</span>
    <span style="color:blue;">MR K VIJAYA KUMAR</span>,
</h3>
  <h3 style="color:red;">DEAR &lt;{name}&gt;,</h3>
  <h3 style="font-family: Garamond, Georgia, serif;">
  Hope this finds you in good spirits and health…!
</h3>
  <h3>
    I, <span style="color:red;">11.</span>
    <span style="color:blue;">MR K VIJAYA KUMAR (F-1183849)</span>,
    am contesting for the Governing Council Election (Civil Engineering Division), Sessions 2025–2029.
  </h3>

  <h3>
    In the previous term (2021–2025), I narrowly missed success by just 18 votes, securing 6th place at the All-India level.
    With your continued support and encouragement this time, I am confident of converting this narrow miss into a meaningful success
    and making a stronger contribution to our profession.
  </h3>

  <h3>
    With over 36 years of professional experience in Civil Engineering, Valuation, and Institutional Service,
    I have devoted myself to advancing our profession, strengthening institutions, and fostering technical excellence across diverse platforms.
  </h3>

  <h3>Professional Contributions to IE(I) & IOV</h3>
  <ul>
    <li><b>Tamil Nadu State Committee Member (Civil), IE(I) (2023–2025)</b></li>
    <li>
      <b>Chairman & Secretary, IE(I) Madurai Local Centre (2014–2018)</b>
      <ul type="a">
        <li>Led the Centre to Best Centre Award twice</li>
        <li>Drove <b>infrastructure development, technical programs, and membership growth</b></li>
      </ul>
    </li>
    <li>
      <b>Chairman, Institution of Valuers, Madurai Branch</b>
      <ul type="a">
        <li>As Secretary earlier, guided the Branch to Best Branch Award</li>
        <li><b>Served as Vice Chairman twice, Institution of Valuers, Madurai Branch</b></li>
        <li>Organized multiple <b>technical lectures, seminars, training programs,</b> and networking events to enhance member participation and knowledge sharing</li>
      </ul>
    </li>
  </ul>

  <p>
    With your <b>valuable support and encouragement,</b> I am confident of making a stronger impact this time
    in <b>serving our Civil Engineering Division</b> at the national level.
  </p>
<img src="https://s3.ap-south-1.amazonaws.com/cdn.kaaikanistore.com/2.png" 
     alt="MR. K. VIJAYA KUMAR" 
     style="height:900px; width:800px;display:block; margin:auto">

  <h3 style="text-align:center;margin-top:30px">
    👉 Kindly select <span style="color:red;">11.</span>
    <span style="color:blue;">MR. K. VIJAYA KUMAR (F-1183849)</span> while casting your online vote.
  </h3>
  <h3 style="text-align:center">“Building Tomorrow Together | நாளையை சேர்ந்து கட்டுவோம்”</h3>

  <h3>Thanks & Regards,</h3>
  <img src="https://s3.ap-south-1.amazonaws.com/cdn.kaaikanistore.com/3.png" alt="KINDLY VOTE FOR" style="max-width:100%;height:100px;wight:100px;">

  <p>
    <span style="font-weight: bold;font-size:18px">Mr.K. Vijaya Kumar</span><br>
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
        name=name,
        membership_id=membership_id,
        mobile=mobile
    )
    try:
        response = ses_client.send_email(
            Source=FROM_EMAIL,
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {'Data': SUBJECT},
                'Body': {'Html': {'Data': body_html}}
            },
            ConfigurationSetName='ses-event-config'
        )
        print(f"Email sent to {to_email}! Message ID: {response['MessageId']}")
    except Exception as e:
        print(f"Error sending to {to_email}: {e}")

# Read CSV (no headers, use indices) and send in batches
CSV_FILE = 'test-mails.csv'  # Replace with your actual file path
BATCH_SIZE = 1000  # Adjust based on rate limits (e.g., 14/sec default)
DELAY_BETWEEN_BATCHES = 60  # Seconds; adjust to stay under rate limits

with open(CSV_FILE, 'r') as file:
    reader = csv.reader(file)
    recipients = list(reader)  # Load all rows
    
    for i in range(0, len(recipients), BATCH_SIZE):
        batch = recipients[i:i + BATCH_SIZE]
        for row in batch:
            if len(row) < 4:
                continue  # Skip invalid rows
            membership_id = row[0].strip()
            name = row[1].strip()
            email = row[2].strip()
            mobile = row[3].strip()
            send_email(email, name, membership_id, mobile)
            time.sleep(0.1)  # Slight delay within batch to avoid bursting limits
        print(f"Batch {i//BATCH_SIZE + 1} complete. Waiting {DELAY_BETWEEN_BATCHES} seconds...")
        time.sleep(DELAY_BETWEEN_BATCHES)

print("All emails sent!")
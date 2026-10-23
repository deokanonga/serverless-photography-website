"""Saves website inquiries to DynamoDB and emails them to you with Amazon SES.

Environment variables (set in Lambda → Configuration → Environment variables):
  TABLE_NAME   the DynamoDB table, e.g. Inquiries
  TO_EMAIL     where notifications go, e.g. contact@deokanonga.com
  FROM_EMAIL   a sender on your SES-verified domain, e.g. inquiries@deokanonga.com
"""
# Tools: base64 decoding, JSON replies, settings, unique IDs, timestamps, form parsing.
import base64
import json
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import parse_qs

# The AWS SDK for Python, used to talk to DynamoDB and SES.
import boto3

# Connections to DynamoDB and SES, opened once and reused for every inquiry.
dynamodb = boto3.resource("dynamodb")
ses = boto3.client("ses")

# The form fields we accept (must match the name="..." of each box on the website).
FIELDS = ["name", "email", "phone", "inquiry_type", "date", "venue_or_city", "message"]
# Friendly label for each field, used in the notification email.
LABELS = {
    "name": "Name",
    "email": "Email",
    "phone": "Phone",
    "inquiry_type": "Type of inquiry",
    "date": "Date",
    "venue_or_city": "Venue or city",
    "message": "Message",
}


# Builds the answer sent back to the website: a status code plus {"success": true/false}.
def respond(status, success):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"success": success}),
    }


# Lambda runs this every time someone submits the form.
def lambda_handler(event, context):
    # Read the form data API Gateway sent, decoding it if it arrived in base64.
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    # Split "name=Amara&email=..." into fields, then keep one clean value per field.
    raw = parse_qs(body)
    form = {k: raw.get(k, [""])[0].strip()[:5000] for k in FIELDS}

    # Bots fill the hidden "_honey" field; pretend it worked and drop it.
    if raw.get("_honey", [""])[0]:
        return respond(200, True)

    # Reject the form if the name, a valid-looking email or the inquiry type is missing.
    if not form["name"] or "@" not in form["email"] or not form["inquiry_type"]:
        return respond(400, False)

    # Build the database row: a unique ID, the time received, a status, and the filled-in fields.
    item = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "new",
        **{k: v for k, v in form.items() if v},
    }
    # Save the row in the DynamoDB table.
    dynamodb.Table(os.environ["TABLE_NAME"]).put_item(Item=item)

    # Write the email text: one "Label: value" line per field, then the message.
    lines = [f"{LABELS[k]}: {form[k]}" for k in FIELDS if k != "message"]
    text = "\n".join(lines) + "\n\n" + form["message"]
    # Email the inquiry to you; hitting Reply goes straight to the client.
    ses.send_email(
        Source=os.environ["FROM_EMAIL"],
        Destination={"ToAddresses": [os.environ["TO_EMAIL"]]},
        ReplyToAddresses=[form["email"]],
        Message={
            "Subject": {"Data": f"New inquiry — {form['name']} ({form['inquiry_type']})"},
            "Body": {"Text": {"Data": text}},
        },
    )
    # Tell the website it worked, so it shows "Thank you".
    return respond(200, True)

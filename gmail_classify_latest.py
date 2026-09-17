import base64
import re

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from ai_classify_email_test import classify_email

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def get_gmail_service():
    creds = None
    if Credentials and Credentials.from_authorized_user_file:
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def extract_text_from_payload(payload) -> str:
    """Extract plain text from Gmail payload"""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    if payload.get("parts"):
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    return ""


def get_latest_inbox_email_text(service) -> str:
    res = service.users().messages().list(
        userId="me",
        labelIds=["INBOX"],
        maxResults=1
    ).execute()

    msg_id = res["messages"][0]["id"]

    msg = service.users().messages().get(
        userId="me",
        id=msg_id,
        format="full"
    ).execute()

    headers = msg["payload"]["headers"]
    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
    body = extract_text_from_payload(msg["payload"])

    full_text = f"Subject: {subject}\n\n{body}"
    return full_text


def main():
    service = get_gmail_service()
    email_text = get_latest_inbox_email_text(service)

    print("=== EMAIL TEXT FROM GMAIL ===")
    print(email_text)

    classification = classify_email(email_text)

    print("\n=== AI CLASSIFICATION RESULT ===")
    print(classification.model_dump())


if __name__ == "__main__":
    main()
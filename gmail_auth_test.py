import os.path
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def get_gmail_service():
    creds: Optional[Credentials] = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"Не найден {CREDENTIALS_FILE}. Положи его в корень проекта."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def main():
    service = get_gmail_service()

    results = (
        service.users()
        .messages()
        .list(userId="me", labelIds=["INBOX"], maxResults=5)
        .execute()
    )

    messages = results.get("messages", [])
    print(f"Letters found: {len(messages)}")

    for m in messages:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=m["id"], format="metadata")
            .execute()
        )
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}

        subject = headers.get("subject", "(no subject)")
        sender = headers.get("from", "(no from)")
        date = headers.get("date", "(no date)")

        print("-" * 60)
        print(f"ID: {m['id']}")
        print(f"From: {sender}")
        print(f"Subject: {subject}")
        print(f"Date: {date}")


if __name__ == "__main__":
    main()
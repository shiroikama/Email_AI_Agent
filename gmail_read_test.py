import os
import base64
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def get_gmail_service():
    creds: Optional[Credentials] = None

    # 1) если токен уже есть — используем
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # 2) если токена нет/протух — обновим или пройдем OAuth заново
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"Не найден {CREDENTIALS_FILE} в корне проекта.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def get_header(headers, name: str) -> str:
    name = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name:
            return h.get("value", "")
    return ""


def main():
    service = get_gmail_service()

    # берём 5 последних писем из inbox
    results = (
        service.users()
        .messages()
        .list(userId="me", labelIds=["INBOX"], maxResults=5)
        .execute()
    )

    messages = results.get("messages", [])
    print(f"INBOX: найдено {len(messages)} писем (показываю до 5)")

    for m in messages:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=m["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"])
            .execute()
        )

        headers = msg.get("payload", {}).get("headers", [])
        from_ = get_header(headers, "From")
        subject = get_header(headers, "Subject")
        date = get_header(headers, "Date")

        print("-" * 70)
        print(f"ID: {m['id']}")
        print(f"From: {from_}")
        print(f"Subject: {subject}")
        print(f"Date: {date}")


if __name__ == "__main__":
    main()
import os
import base64
from email.message import EmailMessage
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
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
                raise FileNotFoundError(f"Не найден {CREDENTIALS_FILE} в корне проекта.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def create_draft(service, to_email: str, subject: str, body: str):
    # Формируем email
    message = EmailMessage()
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    # Gmail API ждёт raw = base64url
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    draft = {
        "message": {
            "raw": raw
        }
    }

    created = service.users().drafts().create(userId="me", body=draft).execute()
    return created


def main():
    service = get_gmail_service()

    # Куда "отвечаем" — пока просто на свой же адрес (для теста)
    to_email = "wireas1@gmail.com"   # можешь заменить на другой
    subject = "Черновик: тест"
    body = (
        "Привет!\n\n"
        "Это тестовый черновик, созданный через Gmail API.\n"
        "Если ты видишь его в Drafts — всё работает.\n\n"
        "— Mail Agent"
    )

    created = create_draft(service, to_email, subject, body)
    print("Draft создан ✅")
    print("Draft ID:", created.get("id"))
    print("Message ID:", created.get("message", {}).get("id"))


if __name__ == "__main__":
    main()
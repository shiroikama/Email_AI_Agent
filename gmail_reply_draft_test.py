import os
import base64
from email.message import EmailMessage
from typing import Optional, Tuple

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
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


def get_header(headers, name: str) -> str:
    name = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name:
            return h.get("value", "")
    return ""


def get_latest_inbox_message(service) -> Tuple[str, str]:
    """
    Возвращает (message_id, thread_id) самого свежего письма в INBOX.
    """
    res = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=1).execute()
    msgs = res.get("messages", [])
    if not msgs:
        raise RuntimeError("INBOX пустой — нечего реплаить.")
    msg_id = msgs[0]["id"]

    msg = service.users().messages().get(userId="me", id=msg_id, format="metadata").execute()
    thread_id = msg.get("threadId")
    if not thread_id:
        raise RuntimeError("Не найден threadId у сообщения.")
    return msg_id, thread_id


def get_message_metadata(service, msg_id: str):
    msg = service.users().messages().get(userId="me", id=msg_id, format="metadata").execute()
    headers = msg.get("payload", {}).get("headers", [])
    return msg, headers


def create_reply_draft(service, original_msg_id: str, thread_id: str, reply_body: str):
    """
    Создаёт черновик-ответ в том же thread.
    Чтобы Gmail точно прикрепил в цепочку, используем:
    - threadId в body draft
    - заголовки In-Reply-To / References (берём из Message-ID оригинала)
    """
    msg, headers = get_message_metadata(service, original_msg_id)

    from_ = get_header(headers, "From")
    subject = get_header(headers, "Subject")
    message_id_hdr = get_header(headers, "Message-ID")

    # To: отвечаем отправителю (простая версия)
    to_email = from_

    # Subject: если нет Re:, добавим
    if not subject.lower().startswith("re:"):
        subject = "Re: " + subject

    email_msg = EmailMessage()
    email_msg["To"] = to_email
    email_msg["Subject"] = subject

    # Эти заголовки помогают Gmail “прибить” ответ к цепочке
    if message_id_hdr:
        email_msg["In-Reply-To"] = message_id_hdr
        email_msg["References"] = message_id_hdr

    email_msg.set_content(reply_body)

    raw = base64.urlsafe_b64encode(email_msg.as_bytes()).decode("utf-8")

    draft_body = {
        "message": {
            "raw": raw,
            "threadId": thread_id,
        }
    }

    created = service.users().drafts().create(userId="me", body=draft_body).execute()

    # (опционально) пометим исходное письмо лейблом "STARRED" как тест
    # чтобы видеть, что мы его трогали — потом уберём это и сделаем свой лейбл
    service.users().messages().modify(
        userId="me",
        id=original_msg_id,
        body={"addLabelIds": ["STARRED"]}
    ).execute()

    return created


def main():
    service = get_gmail_service()

    original_msg_id, thread_id = get_latest_inbox_message(service)

    reply_body = (
        "Здравствуйте!\n\n"
        "Это тестовый черновик-ответ, созданный в том же треде через Gmail API.\n"
        "Если он лежит в цепочке письма — значит threading работает.\n\n"
        "— Mail Agent"
    )

    created = create_reply_draft(service, original_msg_id, thread_id, reply_body)

    print("Reply Draft создан ✅")
    print("Original Message ID:", original_msg_id)
    print("Thread ID:", thread_id)
    print("Draft ID:", created.get("id"))


if __name__ == "__main__":
    main()
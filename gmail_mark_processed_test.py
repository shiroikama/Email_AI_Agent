import os
from typing import Optional, Tuple

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

LABEL_AI_PROCESSED = "AI_PROCESSED"
LABEL_HUMAN_ONLY = "HUMAN_ONLY"


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


def get_or_create_label(service, label_name: str) -> str:
    existing = service.users().labels().list(userId="me").execute().get("labels", [])
    for lb in existing:
        if lb.get("name") == label_name:
            return lb["id"]

    created = service.users().labels().create(
        userId="me",
        body={
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        },
    ).execute()
    return created["id"]


def get_latest_inbox_message(service) -> str:
    res = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=1).execute()
    msgs = res.get("messages", [])
    if not msgs:
        raise RuntimeError("INBOX is empty.")
    return msgs[0]["id"]


def get_header(headers, name: str) -> str:
    name = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name:
            return h.get("value", "")
    return ""


def is_conversation_reply(headers) -> bool:
    in_reply_to = get_header(headers, "In-Reply-To")
    refs = get_header(headers, "References")
    return bool(in_reply_to.strip() or refs.strip())


def main():
    service = get_gmail_service()

    ai_label_id = get_or_create_label(service, LABEL_AI_PROCESSED)
    human_label_id = get_or_create_label(service, LABEL_HUMAN_ONLY)

    msg_id = get_latest_inbox_message(service)

    msg = service.users().messages().get(
        userId="me",
        id=msg_id,
        format="metadata",
        metadataHeaders=["From", "Subject", "In-Reply-To", "References"],
    ).execute()

    headers = msg.get("payload", {}).get("headers", [])
    label_ids = set(msg.get("labelIds", []))

    from_ = get_header(headers, "From")
    subject = get_header(headers, "Subject")

    flagged_human_only = human_label_id in label_ids
    already_processed = ai_label_id in label_ids
    conversation = is_conversation_reply(headers)

    should_process = (not flagged_human_only) and (not already_processed) and (not conversation)

    print("Message:", msg_id)
    print("From   :", from_)
    print("Subject:", subject)
    print("Decision:", "PROCESS ✅" if should_process else "SKIP ❌")

    if should_process:
        service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={"addLabelIds": [ai_label_id]},
        ).execute()
        print(f"OK: added label {LABEL_AI_PROCESSED} ✅")
    else:
        print("Ничего не делаю.")


if __name__ == "__main__":
    main()
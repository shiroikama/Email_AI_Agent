import base64
from email.message import EmailMessage

from gmail_auth_test import get_gmail_service
from gmail_full_ai_reply_preview import (
    get_latest_inbox_message,
    get_header,
    extract_plain_text,
    classify_email,
    generate_reply,
)
from decision_from_classification_test import decide_action
from build_business_payload import build_business_payload


def create_reply_draft(service, original_msg, reply_text: str) -> str:
    """
    Creates a Gmail Draft that is a reply in the same thread.
    Returns draftId.
    """
    headers = original_msg["payload"].get("headers", [])
    thread_id = original_msg.get("threadId")
    original_id = original_msg.get("id")

    to_addr = get_header(headers, "From") or ""
    subject = get_header(headers, "Subject") or ""
    message_id_header = get_header(headers, "Message-ID") or get_header(headers, "Message-Id") or ""

    # Ensure subject starts with Re:
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    msg = EmailMessage()
    msg["To"] = to_addr
    msg["Subject"] = subject

    # These headers help Gmail attach it as a proper reply
    if message_id_header:
        msg["In-Reply-To"] = message_id_header
        msg["References"] = message_id_header

    msg.set_content(reply_text)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    draft_body = {
        "message": {
            "raw": raw,
            "threadId": thread_id,
        }
    }

    created = service.users().drafts().create(userId="me", body=draft_body).execute()
    return created["id"]


def main():
    service = get_gmail_service()

    original = get_latest_inbox_message(service)
    if not original:
        print("No inbox messages found.")
        return

    headers = original["payload"].get("headers", [])
    subject = get_header(headers, "Subject") or "(no subject)"
    sender = get_header(headers, "From") or "(unknown sender)"

    body_text = extract_plain_text(original["payload"]).strip()
    if not body_text:
        body_text = original.get("snippet", "").strip()

    classification = classify_email(f"Subject: {subject}\n\nBody:\n{body_text}")
    proceed, reason = decide_action(classification)

    print(f"Latest email: {original['id']}")
    print(f"From       : {sender}")
    print(f"Subject    : {subject}")
    print(f"Decision   : {'PROCEED ✅' if proceed else 'SKIP ❌'} - {reason}")

    if not proceed:
        return

    payload = build_business_payload(classification)
    if not payload:
        print("ERROR: could not build business payload (SKU missing or not found).")
        return

    reply_text = generate_reply(payload)

    draft_id = create_reply_draft(service, original, reply_text)
    print(f"Draft created ✅ Draft ID: {draft_id}")


if __name__ == "__main__":
    main()
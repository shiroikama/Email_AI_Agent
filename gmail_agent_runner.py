import time
import traceback
from typing import List, Optional, Tuple

from gmail_auth_test import get_gmail_service
from gmail_full_ai_reply_preview import (
    get_header,
    extract_plain_text,
    classify_email,
    generate_reply,
)
from decision_from_classification_test import decide_action
from build_business_payload import build_business_payload

# Your draft creator (reply draft)
from gmail_create_draft_from_latest import create_reply_draft


AI_PROCESSED_LABEL = "AI_PROCESSED"
AI_ERROR_LABEL = "AI_ERROR"
HUMAN_ONLY_LABEL = "HUMAN_ONLY"


def ensure_label(service, label_name: str) -> str:
    """Ensure label exists and return labelId."""
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for lb in labels:
        if lb.get("name") == label_name:
            return lb["id"]

    created = (
        service.users()
        .labels()
        .create(
            userId="me",
            body={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        )
        .execute()
    )
    return created["id"]


def add_labels(service, msg_id: str, add_label_ids: List[str]):
    service.users().messages().modify(
        userId="me",
        id=msg_id,
        body={"addLabelIds": add_label_ids, "removeLabelIds": []},
    ).execute()


def list_candidate_message_ids(service, max_results: int = 10) -> List[str]:
    """
    Candidate emails = inbox, not processed, not human-only, not errors already.
    """
    query = (
        f"in:inbox "
        f"-label:{AI_PROCESSED_LABEL} "
        f"-label:{HUMAN_ONLY_LABEL} "
        f"-label:{AI_ERROR_LABEL}"
    )
    res = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    msgs = res.get("messages", [])
    return [m["id"] for m in msgs]


def get_message_full(service, msg_id: str) -> dict:
    return service.users().messages().get(userId="me", id=msg_id, format="full").execute()


def process_one(
    service,
    msg_id: str,
    ai_processed_label_id: str,
    ai_error_label_id: str,
) -> Optional[str]:
    """
    Returns draftId if created, else None.
    IMPORTANT:
      - If any failure happens after decision=PROCEED, we set AI_ERROR (not AI_PROCESSED).
      - We set AI_PROCESSED only when a draft was successfully created.
    """
    print(f"\n=== Processing message {msg_id} ===")

    try:
        original = get_message_full(service, msg_id)
        headers = original.get("payload", {}).get("headers", [])
        subject = get_header(headers, "Subject") or "(no subject)"
        sender = get_header(headers, "From") or "(unknown sender)"

        body_text = extract_plain_text(original.get("payload", {})).strip()
        if not body_text:
            body_text = (original.get("snippet") or "").strip()

        print(f"[1] From    : {sender}")
        print(f"[1] Subject : {subject}")
        print(f"[1] Body len: {len(body_text)} chars")

        # 1) AI classification
        print("[2] Classifying email with AI...")
        classification = classify_email(f"Subject: {subject}\n\nBody:\n{body_text}")
        print(f"[2] Classification: {classification}")

        # 2) Decision logic
        proceed, reason = decide_action(classification)
        print(f"[3] Decision: {reason}")

        if not proceed:
            # For SKIP - mark processed so it won't loop forever
            print("[3] SKIP -> marking AI_PROCESSED (no draft)")
            add_labels(service, msg_id, [ai_processed_label_id])
            return None

        # 3) Business payload from DB (no AI)
        print("[4] Building business payload from DB (no AI)...")
        payload = build_business_payload(classification)

        if not payload:
            print("[4] ERROR: Could not build business payload (SKU missing / not found / ambiguous).")
            add_labels(service, msg_id, [ai_error_label_id])
            return None

        print(f"[4] Business payload OK: keys={list(payload.keys())}")

        # 4) Generate reply text (AI writer)
        print("[5] Generating reply text with AI...")
        reply_text = generate_reply(payload)
        print(f"[5] Reply length: {len(reply_text)} chars")

        # 5) Create Gmail draft reply
        print("[6] Creating Gmail draft reply...")
        draft_id = create_reply_draft(service, original, reply_text)

        if not draft_id:
            print("[6] ERROR: Draft creation returned None/empty.")
            add_labels(service, msg_id, [ai_error_label_id])
            return None

        print(f"[6] Draft created ✅ Draft ID: {draft_id}")

        # 6) Mark processed ONLY after draft success
        add_labels(service, msg_id, [ai_processed_label_id])
        print("[7] Marked AI_PROCESSED ✅")

        return draft_id

    except Exception as e:
        print(f"!!! ERROR processing {msg_id}: {e}")
        print(traceback.format_exc())
        # Mark as AI_ERROR so it doesn't loop forever on the same broken email
        add_labels(service, msg_id, [ai_error_label_id])
        return None


def main(poll_seconds: int = 30, batch_size: int = 10):
    service = get_gmail_service()

    ai_processed_label_id = ensure_label(service, AI_PROCESSED_LABEL)
    ai_error_label_id = ensure_label(service, AI_ERROR_LABEL)

    print(f"Agent started. Poll interval: {poll_seconds}s | Batch size: {batch_size}")

    while True:
        try:
            ids = list_candidate_message_ids(service, max_results=batch_size)
            if ids:
                print(f"\nFound {len(ids)} candidate emails")
            else:
                print("\nNo candidates. Sleeping...")

            for msg_id in ids:
                process_one(service, msg_id, ai_processed_label_id, ai_error_label_id)

            time.sleep(poll_seconds)

        except KeyboardInterrupt:
            print("\nAgent stopped by user.")
            break
        except Exception as e:
            print(f"\nTop-level error: {e}")
            print(traceback.format_exc())
            time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
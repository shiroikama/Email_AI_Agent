import base64
from email.utils import parsedate_to_datetime

from dotenv import load_dotenv
from openai import OpenAI

from gmail_auth_test import get_gmail_service
from ai_classify_email_test import classify_email, Classification
from decision_from_classification_test import decide_action
from build_business_payload import build_business_payload

load_dotenv()
client = OpenAI()

SYSTEM_WRITER = """
You are a sales email assistant for a drink dispenser company.

Rules:
- Use ONLY the data provided in the JSON payload.
- Do NOT invent prices, lead times, SKUs, features, discounts, taxes, or policies.
- Output ONLY the email body text (no subject line, no JSON).
- Write in clear, professional English.
"""


def extract_plain_text(message_payload: dict) -> str:
    """
    Extract plaintext body from Gmail message payload.
    Prefers text/plain, falls back to snippet-like behavior.
    """

    def walk_parts(parts):
        for part in parts:
            mime = part.get("mimeType")
            body = part.get("body", {})
            data = body.get("data")

            if mime == "text/plain" and data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

            if part.get("parts"):
                found = walk_parts(part["parts"])
                if found:
                    return found
        return ""

    if message_payload.get("parts"):
        text = walk_parts(message_payload["parts"])
        if text:
            return text

    body = message_payload.get("body", {})
    data = body.get("data")
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    return ""


def get_latest_inbox_message(service):
    res = (
        service.users()
        .messages()
        .list(userId="me", labelIds=["INBOX"], maxResults=1)
        .execute()
    )
    msgs = res.get("messages", [])
    if not msgs:
        return None
    msg_id = msgs[0]["id"]
    full = (
        service.users()
        .messages()
        .get(userId="me", id=msg_id, format="full")
        .execute()
    )
    return full


def get_header(headers, name):
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value")
    return None


def generate_reply(payload: dict) -> str:
    """
    Handles:
    - Single product reply
    - Multiple option reply (PRINT + SCREEN)
    - Catalog reply
    """

    # ---- Case 1: Catalog ----
    if "catalog" in payload:
        lines = []
        lines.append("Thank you for your interest in our beverage dispenser systems.\n")
        lines.append("Please find our available models below:\n")

        for p in payload["catalog"]:
            lines.append(
                f"- {p['name']} (SKU: {p['sku']})\n"
                f"  Price: ${p['unit_price_usd']:,.2f}\n"
                f"  Lead time: {p['lead_time_days']} days\n"
                f"  Description: {p['description']}\n"
            )

        lines.append("Please let us know if you would like a formal quotation or further details.")
        return "\n".join(lines)

    # ---- Case 2: Multiple options (no signage specified) ----
    if "options" in payload:
        lines = []
        tap_count = payload["customer_request"].get("tap_count")

        lines.append(f"Thank you for your inquiry regarding our {tap_count}-tap system.\n")
        lines.append("We offer the following options:\n")

        for opt in payload["options"]:
            lines.append(
                f"- {opt['name']} (SKU: {opt['sku']})\n"
                f"  Price: ${opt['unit_price_usd']:,.2f}\n"
                f"  Lead time: {opt['lead_time_days']} days\n"
                f"  Description: {opt['description']}\n"
            )

        lines.append("Please let us know which version you are interested in, and we will be happy to assist further.")
        return "\n".join(lines)

    # ---- Case 3: Single product ----
    product = payload["product_data"]
    quantity = payload["customer_request"].get("quantity", 1)

    lines = []
    lines.append(f"Thank you for your inquiry regarding the {product['name']} (SKU: {product['sku']}).\n")

    lines.append(f"Unit price: ${product['unit_price_usd']:,.2f}")

    if quantity and quantity > 1:
        total = payload["computed"]["total_price_usd"]
        lines.append(f"Total price for {quantity} units: ${total:,.2f}")

    lines.append(f"Lead time: {product['lead_time_days']} days\n")
    lines.append("Please let us know if you would like to proceed with an order or require further information.")

    return "\n".join(lines)

def main():
    service = get_gmail_service()

    msg = get_latest_inbox_message(service)
    if not msg:
        print("No inbox messages found.")
        return

    headers = msg["payload"].get("headers", [])
    subject = get_header(headers, "Subject") or "(no subject)"
    sender = get_header(headers, "From") or "(unknown sender)"
    date_raw = get_header(headers, "Date")
    date = parsedate_to_datetime(date_raw).isoformat() if date_raw else "(unknown date)"

    body_text = extract_plain_text(msg["payload"]).strip()
    if not body_text:
        body_text = msg.get("snippet", "").strip()

    print("=== LATEST GMAIL EMAIL ===")
    print(f"From   : {sender}")
    print(f"Subject: {subject}")
    print(f"Date   : {date}")
    print("---- BODY ----")
    print(body_text)
    print("--------------")

    # 1) AI classification (single source of truth)
    classification: Classification = classify_email(f"Subject: {subject}\n\nBody:\n{body_text}")
    print("\n=== CLASSIFICATION ===")
    print(classification.model_dump())

    # 2) Decision logic
    proceed, reason = decide_action(classification)
    print("\n=== DECISION ===")
    print(("PROCEED ✅" if proceed else "SKIP ❌") + " - " + reason)

    if not proceed:
        return

    # 3) Business payload (NO AI)
    payload = build_business_payload(classification)
    if not payload:
        print("\nERROR: Could not build business payload (SKU missing / not found / ambiguous).")
        return

    print("\n=== BUSINESS PAYLOAD ===")
    print(payload)

    # 4) AI writer
    reply = generate_reply(payload)
    print("\n=== REPLY PREVIEW ===")
    print(reply)


if __name__ == "__main__":
    main()
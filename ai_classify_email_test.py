import json
from typing import Optional, Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

from db import SessionLocal
from models import Product

load_dotenv()
client = OpenAI()

# --------- Output schema (strict) ---------
EmailType = Literal["catalog_request", "price_request", "lead_time_request", "unknown"]
TapCount = Literal[1, 2, 4, 6]
Signage = Literal["PRINT", "SCREEN"]


class Classification(BaseModel):
    type: EmailType = Field(..., description="What the customer is asking about")

    # Exact SKU if explicitly provided and valid (in DB). Otherwise null.
    sku: Optional[str] = Field(
        None, description="One of allowed SKUs, or null if not explicitly stated/unknown"
    )

    # NEW: product inference when exact SKU is not provided
    tap_count: Optional[TapCount] = Field(
        None, description="1/2/4/6 if inferred from text, otherwise null"
    )
    signage: Optional[Signage] = Field(
        None, description="PRINT or SCREEN if inferred from text, otherwise null"
    )

    quantity: Optional[int] = Field(None, ge=1, description="Quantity requested, or null if not specified")
    delivery_location: Optional[str] = Field(None, description="City/country if mentioned, or null")
    is_conversation: bool = Field(..., description="True if this is an ongoing thread/reply, otherwise False")


def get_allowed_skus() -> list[str]:
    db = SessionLocal()
    try:
        return [p.sku for p in db.query(Product).order_by(Product.id).all()]
    finally:
        db.close()


SYSTEM_RULES = """You are an email classifier for a beverage dispenser company.

Return ONLY a valid JSON object that matches this exact schema:
{
  "type": "catalog_request" | "price_request" | "lead_time_request" | "unknown",
  "sku": string|null,
  "tap_count": 1|2|4|6|null,
  "signage": "PRINT"|"SCREEN"|null,
  "quantity": integer|null,
  "delivery_location": string|null,
  "is_conversation": boolean
}

CRITICAL:
- Output JSON ONLY. No extra keys. No comments. No markdown.
- Do NOT invent SKUs. Only return an exact SKU if it is explicitly present in the email AND it exists in ALLOWED_SKUS.
- If the email does NOT contain an exact SKU, set sku = null and try to infer tap_count/signage from wording.

Tap inference:
- "one tap", "1 tap", "single tap" -> tap_count = 1
- "two taps", "2 taps", "double tap" -> tap_count = 2
- "four taps", "4 taps" -> tap_count = 4
- "six taps", "6 taps" -> tap_count = 6

Signage inference:
- If email mentions "screen", "digital", "screens", "display" -> signage = "SCREEN"
- If it mentions "printed", "print", "card signage", "printed card" -> signage = "PRINT"
- If not mentioned -> signage = null

Quantity:
- If quantity is explicitly stated as a number of units -> quantity = that integer
- Otherwise quantity = null

Delivery location:
- If a city/country is explicitly stated -> delivery_location = that short string
- Otherwise null

Conversation:
- If the email looks like a reply/ongoing thread (e.g., starts with "Re:", "Fwd:", quotes prior message, refers to "as discussed", "thanks for your reply", etc.) -> is_conversation = true
- Otherwise false
"""


def classify_email(email_text: str) -> Classification:
    allowed_skus = get_allowed_skus()

    user_prompt = f"""EMAIL:
{email_text}

ALLOWED_SKUS (only choose from this list, otherwise null):
{allowed_skus}
"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_RULES},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )

    raw = (resp.choices[0].message.content or "").strip()

    try:
        data = json.loads(raw)
        return Classification.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        fix_prompt = f"""Your previous output was invalid.

INVALID_OUTPUT:
{raw}

Return ONLY a valid JSON object that matches the exact schema. No extra keys.
"""
        resp2 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_RULES},
                {"role": "user", "content": user_prompt},
                {"role": "user", "content": fix_prompt},
            ],
            temperature=0.0,
        )
        raw2 = (resp2.choices[0].message.content or "").strip()
        data2 = json.loads(raw2)
        return Classification.model_validate(data2)


def main():
    # Quick sanity tests (these are NOT Gmail reads, just local tests)
    test_emails = [
        "Hi! Could you please send me your catalog and prices?",
        "Hello, what is the price for FPB-D-PRINT? I need 2 units. Delivery to Sydney.",
        "Hi, what's the price for the six tap system? We need 2 units delivered to Sydney.",
        "Hi, what's the price for the 4 tap system with screens?",
        "Re: Thanks — can you confirm the lead time again?",
        "Do you ship internationally and what are your payment terms?",
    ]

    for i, txt in enumerate(test_emails, 1):
        result = classify_email(txt)
        print("=" * 70)
        print(f"TEST EMAIL #{i}: {txt}")
        print("CLASSIFICATION:", result.model_dump())


if __name__ == "__main__":
    main()
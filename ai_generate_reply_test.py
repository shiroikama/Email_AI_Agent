import os
from dotenv import load_dotenv
from openai import OpenAI

from build_business_payload import build_business_payload

load_dotenv()
client = OpenAI()

SYSTEM_PROMPT = """
You are a sales email assistant for a drink dispenser company.

Rules:
- Use ONLY the data provided in the JSON payload.
- Do NOT invent prices, lead times, SKUs, features, discounts, taxes, or policies.
- If a piece of information is not in the payload, politely say you don't have it yet and ask a clarifying question.
- Output ONLY the email body text (no subject line, no JSON).
- Write in clear, professional English.
"""

def main():
    # Simulate a classification result (normally produced by the classifier)
    classification = {
        "type": "price_request",
        "sku": "DISP-002",
        "quantity": 3,
        "delivery_location": "Sydney",
        "is_conversation": False,
    }

    payload = build_business_payload(classification)
    if not payload:
        print("ERROR: Could not build payload (missing SKU or product not found).")
        return

    user_prompt = f"""
Customer email (paraphrased):
- They asked for price and lead time for {payload['customer_request']['sku']}
- Quantity: {payload['customer_request']['quantity']}
- Delivery location: {payload['customer_request'].get('delivery_location')}

Business data (SOURCE OF TRUTH):
{payload}

Write a reply email.
"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ],
        temperature=0.2,
    )

    text = resp.choices[0].message.content
    print("=== GENERATED EMAIL ===")
    print(text)

if __name__ == "__main__":
    main()
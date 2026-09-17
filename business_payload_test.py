from build_business_payload import build_business_payload

test_classification = {
    "type": "price_request",
    "sku": "DISP-002",
    "quantity": 3,
    "delivery_location": "Sydney",
    "is_conversation": False,
}

payload = build_business_payload(test_classification)

print("BUSINESS PAYLOAD:")
print(payload)
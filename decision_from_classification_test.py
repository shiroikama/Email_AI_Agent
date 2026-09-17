from typing import Tuple, Union
from ai_classify_email_test import Classification

# What we consider "valid requests" for MVP
ALLOWED_TYPES = {"catalog_request", "price_request", "lead_time_request"}


def decide_action(c: Union[Classification, dict]) -> Tuple[bool, str]:
    """
    Accepts Classification OR dict (parsed JSON).
    Returns:
      (should_proceed, reason)

    Updated logic:
    - For price/lead_time, we allow:
        (a) explicit SKU, OR
        (b) inferred tap_count (1/2/4/6) even if signage is missing
      because later business logic can produce one or two product options.
    """
    if isinstance(c, dict):
        c = Classification(**c)

    if c.is_conversation:
        return False, "SKIP: ongoing conversation"

    if c.type not in ALLOWED_TYPES:
        return False, "SKIP: unsupported request type"

    # catalog_request is always OK to proceed (no SKU required)
    if c.type == "catalog_request":
        return True, "PROCEED: catalog request"

    # For price/lead_time requests:
    # We proceed if we have an exact SKU OR at least tap_count inferred.
    if c.type in {"price_request", "lead_time_request"}:
        if c.sku:
            return True, "PROCEED: exact SKU provided"
        if c.tap_count:
            # signage may be None -> later we return both PRINT/SCREEN options
            return True, "PROCEED: inferred product family (tap_count)"
        return False, "SKIP: missing product identifier (no SKU and no tap_count)"

    return True, "PROCEED: valid request"


def main():
    samples = [
        # Exact SKU -> proceed
        Classification(
            type="price_request",
            sku="FPB-D-PRINT",
            tap_count=None,
            signage=None,
            quantity=3,
            delivery_location="Sydney",
            is_conversation=False,
        ),
        # Inferred tap count (no SKU) -> proceed
        Classification(
            type="price_request",
            sku=None,
            tap_count=4,
            signage=None,
            quantity=1,
            delivery_location=None,
            is_conversation=False,
        ),
        # Conversation -> skip
        Classification(
            type="lead_time_request",
            sku="FPB-Q-SCREEN",
            tap_count=None,
            signage=None,
            quantity=None,
            delivery_location=None,
            is_conversation=True,
        ),
        # Unknown type -> skip
        Classification(
            type="unknown",
            sku=None,
            tap_count=None,
            signage=None,
            quantity=None,
            delivery_location=None,
            is_conversation=False,
        ),
        # Missing both SKU and tap_count -> skip
        Classification(
            type="price_request",
            sku=None,
            tap_count=None,
            signage=None,
            quantity=2,
            delivery_location=None,
            is_conversation=False,
        ),
        # Catalog request -> proceed
        Classification(
            type="catalog_request",
            sku=None,
            tap_count=None,
            signage=None,
            quantity=None,
            delivery_location=None,
            is_conversation=False,
        ),
    ]

    for s in samples:
        ok, reason = decide_action(s)
        print(s.model_dump(), "=>", ok, reason)


if __name__ == "__main__":
    main()
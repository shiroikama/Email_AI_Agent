from typing import Optional, Union

from ai_classify_email_test import Classification
from product_service import get_product_by_sku, list_products


def cents_to_usd(cents: int) -> float:
    return round(cents / 100, 2)


def family_prefix_from_taps(tap_count: int) -> Optional[str]:
    """
    Maps tap counts to SKU family prefixes.
    1 -> FPB-S
    2 -> FPB-D
    4 -> FPB-Q
    6 -> FPB-6
    """
    mapping = {
        1: "FPB-S",
        2: "FPB-D",
        4: "FPB-Q",
        6: "FPB-6",
    }
    return mapping.get(tap_count)


def build_sku(prefix: str, signage: str) -> str:
    """
    signage must be 'PRINT' or 'SCREEN'
    """
    return f"{prefix}-{signage}"


def build_product_option(product, quantity: int) -> dict:
    unit_price_usd = cents_to_usd(product.price_cents)
    total_price_usd = cents_to_usd(product.price_cents * quantity)

    return {
        "sku": product.sku,
        "name": product.name,
        "unit_price_usd": unit_price_usd,
        "lead_time_days": product.lead_time_days,
        "description": product.description,
        "computed": {
            "total_price_usd": total_price_usd,
        },
    }


def build_business_payload(classification: Union[Classification, dict]) -> dict | None:
    # Accept dict or Pydantic model
    if isinstance(classification, dict):
        c = Classification(**classification)
    else:
        c = classification

    req_type = c.type
    quantity = c.quantity or 1

    # --- CATALOG REQUEST: return all products ---
    if req_type == "catalog_request":
        products = list_products()
        catalog = []
        for p in products:
            catalog.append(
                {
                    "sku": p.sku,
                    "name": p.name,
                    "unit_price_usd": cents_to_usd(p.price_cents),
                    "lead_time_days": p.lead_time_days,
                    "description": p.description,
                }
            )

        return {
            "customer_request": {
                "type": req_type,
                "delivery_location": c.delivery_location,
            },
            "catalog": catalog,
        }

    # --- PRICE / LEAD TIME ---
    # Case A: exact SKU provided -> single product payload (same as before)
    if c.sku:
        product = get_product_by_sku(c.sku)
        if not product:
            return None

        option = build_product_option(product, quantity)

        return {
            "customer_request": {
                "type": req_type,
                "sku": c.sku,
                "quantity": quantity,
                "delivery_location": c.delivery_location,
            },
            "product_data": {
                "sku": option["sku"],
                "name": option["name"],
                "unit_price_usd": option["unit_price_usd"],
                "lead_time_days": option["lead_time_days"],
                "description": option["description"],
            },
            "computed": option["computed"],
        }

    # Case B: no SKU, but tap_count inferred -> resolve to one or two SKUs
    if c.tap_count:
        prefix = family_prefix_from_taps(int(c.tap_count))
        if not prefix:
            return None

        # If signage is specified -> single option
        if c.signage in ("PRINT", "SCREEN"):
            sku = build_sku(prefix, c.signage)
            product = get_product_by_sku(sku)
            if not product:
                return None

            option = build_product_option(product, quantity)

            return {
                "customer_request": {
                    "type": req_type,
                    "tap_count": c.tap_count,
                    "signage": c.signage,
                    "quantity": quantity,
                    "delivery_location": c.delivery_location,
                },
                "product_data": {
                    "sku": option["sku"],
                    "name": option["name"],
                    "unit_price_usd": option["unit_price_usd"],
                    "lead_time_days": option["lead_time_days"],
                    "description": option["description"],
                },
                "computed": option["computed"],
            }

        # If signage NOT specified -> return BOTH options (PRINT + SCREEN)
        if c.signage is None:
            skus = [build_sku(prefix, "PRINT"), build_sku(prefix, "SCREEN")]
            products = []
            for sku in skus:
                p = get_product_by_sku(sku)
                if p:
                    products.append(p)

            # If none found -> fail
            if not products:
                return None

            options = [build_product_option(p, quantity) for p in products]

            # payload with multiple options
            return {
                "customer_request": {
                    "type": req_type,
                    "tap_count": c.tap_count,
                    "signage": None,
                    "quantity": quantity,
                    "delivery_location": c.delivery_location,
                },
                "options": options,
                "note": "Customer did not specify signage type; providing both Printed and Screen options.",
            }

        # Any other signage value -> treat as unknown
        return None

    # No SKU and no tap_count -> cannot proceed for price/lead_time
    return None
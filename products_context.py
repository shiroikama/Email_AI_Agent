from db import SessionLocal
from models import Product


def money(cents: int) -> str:
    return f"${cents / 100:.2f}"


def build_products_context() -> str:
    """
    Returns a strict, factual context string with product data.
    This is the ONLY source of truth for the AI later.
    """
    db = SessionLocal()
    products = db.query(Product).order_by(Product.id).all()
    db.close()

    if not products:
        return "No products are currently available."

    lines = []
    lines.append("Available products:\n")

    for p in products:
        lines.append(
            f"- SKU: {p.sku}\n"
            f"  Name: {p.name}\n"
            f"  Price: {money(p.price_cents)}\n"
            f"  Lead time: {p.lead_time_days} days\n"
            f"  Description: {p.description}\n"
        )

    return "\n".join(lines)


def main():
    context = build_products_context()
    print(context)


if __name__ == "__main__":
    main()
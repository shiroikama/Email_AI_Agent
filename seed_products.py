from db import SessionLocal
from models import Product


def main():
    db = SessionLocal()

    # Clear table so you can re-run this script safely
    db.query(Product).delete()

    products = [
        Product(
            sku="DISP-001",
            name="Drink Dispenser Basic",
            price_cents=500_00,   # $500.00
            lead_time_days=7,
            description="Entry-level dispenser for chilled beverages."
        ),
        Product(
            sku="DISP-002",
            name="Drink Dispenser Pro",
            price_cents=1000_00,  # $1000.00
            lead_time_days=14,
            description="Professional-grade dispenser with increased capacity."
        ),
        Product(
            sku="DISP-003",
            name="Drink Dispenser Ultra",
            price_cents=1800_00,  # $1800.00
            lead_time_days=21,
            description="Premium commercial dispenser designed for high-volume use."
        ),
    ]

    db.add_all(products)
    db.commit()
    db.close()

    print("OK: test products have been seeded.")


if __name__ == "__main__":
    main()
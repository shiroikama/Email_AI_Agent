from typing import List, Optional

from db import SessionLocal
from models import Product


def get_product_by_sku(sku: str) -> Optional[Product]:
    db = SessionLocal()
    try:
        return db.query(Product).filter(Product.sku == sku).first()
    finally:
        db.close()


def list_products() -> List[Product]:
    """
    Returns all products from the database.
    """
    db = SessionLocal()
    try:
        return db.query(Product).order_by(Product.id).all()
    finally:
        db.close()
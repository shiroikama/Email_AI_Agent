from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # цена в центах, чтобы не было float-ошибок
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    # срок поставки/доставки как текст (пока просто)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)

    # короткое описание
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DB_URL = "sqlite:///./app.db"

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},  # нужно для sqlite в простом режиме
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
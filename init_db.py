from db import engine
from models import Product
from db import Base


def main():
    Base.metadata.create_all(bind=engine)
    print("OK: таблицы созданы (app.db).")


if __name__ == "__main__":
    main()
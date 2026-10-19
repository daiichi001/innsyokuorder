"""起動スクリプト:  python main.py"""
from restaurant.config import DB_PATH
from restaurant.database import Database
from restaurant.gui import run
from restaurant.order_service import OrderService


def main():
    db = Database(DB_PATH)
    try:
        run(OrderService(db))
    finally:
        db.close()


if __name__ == "__main__":
    main()

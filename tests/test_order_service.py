import unittest

from restaurant.database import Database
from restaurant.order_service import OrderError, OrderService


class OrderServiceTest(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.service = OrderService(self.db)

    def tearDown(self):
        self.db.close()

    def test_add_with_quantity(self):
        self.service.add("N02", 2)   # 200 x 2
        self.service.add("D01", 1)   # 200
        self.assertEqual(self.service.total(), 600)
        self.assertEqual([(l.menu_id, l.quantity) for l in self.service.lines()], [("N02", 2), ("D01", 1)])

    def test_invalid_add(self):
        for menu_id, qty in (("N01", 0), ("N01", 100), ("NOPE", 1)):
            with self.subTest(menu_id=menu_id, qty=qty):
                with self.assertRaises(OrderError):
                    self.service.add(menu_id, qty)

    def test_cancel_before_checkout(self):
        keep = self.service.add("N01", 1)
        drop = self.service.add("D05", 3)
        self.service.cancel(drop)
        self.assertEqual([l.id for l in self.service.lines()], [keep])
        self.assertEqual(self.service.total(), 150)
        # 取消も履歴として残る
        row = self.db.get_item(drop)
        self.assertEqual(row["status"], "cancelled")
        self.assertIsNotNone(row["cancelled_at"])
        with self.assertRaises(OrderError):
            self.service.cancel(drop)

    def test_cannot_cancel_after_checkout(self):
        line = self.service.add("N01", 1)
        self.service.checkout()
        with self.assertRaises(OrderError):
            self.service.cancel(line)

    def test_checkout_records_total_and_starts_new_order(self):
        self.service.add("N03", 1)   # 330
        self.service.add("S02", 2)   # 200 x 2
        first_order = self.service.order_id
        receipt = self.service.checkout()
        self.assertEqual(receipt.total, 330 + 200 * 2)
        self.assertNotEqual(self.service.order_id, first_order)
        self.assertEqual(self.service.lines(), [])
        history = self.service.history()
        self.assertEqual(history[0]["id"], first_order)
        self.assertEqual(history[0]["total"], 730)
        self.assertEqual(history[0]["item_count"], 3)

    def test_checkout_empty(self):
        with self.assertRaises(OrderError):
            self.service.checkout()

    def test_open_order_is_resumed(self):
        self.service.add("K02", 1)
        resumed = OrderService(self.db)
        self.assertEqual(resumed.order_id, self.service.order_id)
        self.assertEqual(resumed.total(), 130)

    def test_recommendation_is_logged(self):
        self.service.recommend(30, "女性", ["乳", "卵"])
        row = self.db.conn.execute("SELECT * FROM recommendation_logs").fetchone()
        self.assertEqual((row["age"], row["gender"], row["allergens"]), (30, "女性", "卵,乳"))

    def test_migrates_old_database(self):
        import os, sqlite3, tempfile
        path = os.path.join(tempfile.mkdtemp(), "old.db")
        old = sqlite3.connect(path)
        old.execute("""CREATE TABLE recommendation_logs (id INTEGER PRIMARY KEY, age INTEGER NOT NULL,
                       gender TEXT NOT NULL, menu_ids TEXT NOT NULL, requested_at TEXT NOT NULL)""")
        old.commit()
        old.close()
        db = Database(path)
        try:
            OrderService(db).recommend(20, "男性", ["そば"])
            self.assertEqual(db.conn.execute("SELECT allergens FROM recommendation_logs").fetchone()[0], "そば")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()

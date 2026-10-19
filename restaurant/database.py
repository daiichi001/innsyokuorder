"""SQLite への注文データの読み書き"""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    status      TEXT    NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'paid')),
    created_at  TEXT    NOT NULL,
    paid_at     TEXT,
    total       INTEGER
);

CREATE TABLE IF NOT EXISTS order_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id     INTEGER NOT NULL REFERENCES orders(id),
    menu_id      TEXT    NOT NULL,
    name         TEXT    NOT NULL,
    unit_price   INTEGER NOT NULL,
    quantity     INTEGER NOT NULL CHECK (quantity > 0),
    status       TEXT    NOT NULL DEFAULT 'ordered' CHECK (status IN ('ordered', 'cancelled')),
    ordered_at   TEXT    NOT NULL,
    cancelled_at TEXT
);

CREATE TABLE IF NOT EXISTS recommendation_logs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    age          INTEGER NOT NULL,
    gender       TEXT    NOT NULL,
    menu_ids     TEXT    NOT NULL,
    requested_at TEXT    NOT NULL
);
"""


class Database:
    def __init__(self, path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    def close(self):
        self.conn.close()

    # ---- orders ----
    def find_open_order_id(self):
        row = self.conn.execute(
            "SELECT id FROM orders WHERE status = 'open' ORDER BY id DESC LIMIT 1").fetchone()
        return row["id"] if row else None

    def create_order(self, now: str) -> int:
        with self.conn:
            cur = self.conn.execute("INSERT INTO orders (created_at) VALUES (?)", (now,))
        return cur.lastrowid

    def mark_paid(self, order_id: int, total: int, now: str):
        with self.conn:
            self.conn.execute(
                "UPDATE orders SET status = 'paid', paid_at = ?, total = ? WHERE id = ?",
                (now, total, order_id))

    def paid_orders(self, limit: int = 100):
        return self.conn.execute(
            """SELECT o.id, o.paid_at, o.total,
                      COALESCE(SUM(i.quantity), 0) AS item_count
               FROM orders o
               LEFT JOIN order_items i ON i.order_id = o.id AND i.status = 'ordered'
               WHERE o.status = 'paid'
               GROUP BY o.id ORDER BY o.id DESC LIMIT ?""", (limit,)).fetchall()

    # ---- order_items ----
    def add_item(self, order_id, menu_id, name, unit_price, quantity, now) -> int:
        with self.conn:
            cur = self.conn.execute(
                """INSERT INTO order_items (order_id, menu_id, name, unit_price, quantity, ordered_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (order_id, menu_id, name, unit_price, quantity, now))
        return cur.lastrowid

    def get_item(self, item_id: int):
        return self.conn.execute(
            "SELECT * FROM order_items WHERE id = ?", (item_id,)).fetchone()

    def cancel_item(self, item_id: int, now: str):
        with self.conn:
            self.conn.execute(
                "UPDATE order_items SET status = 'cancelled', cancelled_at = ? WHERE id = ?",
                (now, item_id))

    def active_items(self, order_id: int):
        return self.conn.execute(
            """SELECT * FROM order_items
               WHERE order_id = ? AND status = 'ordered' ORDER BY id""", (order_id,)).fetchall()

    # ---- recommendation_logs ----
    def log_recommendation(self, age: int, gender: str, menu_ids: str, now: str):
        with self.conn:
            self.conn.execute(
                """INSERT INTO recommendation_logs (age, gender, menu_ids, requested_at)
                   VALUES (?, ?, ?, ?)""", (age, gender, menu_ids, now))

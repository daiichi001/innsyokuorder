"""注文・取消・会計の業務ロジック（GUI から独立させてテスト可能にしている）"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .config import QUANTITY_MAX, QUANTITY_MIN
from .database import Database
from .menu import get_item
from .recommend import Recommendation, recommend


class OrderError(Exception):
    """利用者に表示できるメッセージを持つ業務エラー"""


@dataclass(frozen=True)
class OrderLine:
    id: int
    menu_id: str
    name: str
    unit_price: int
    quantity: int
    ordered_at: str

    @property
    def subtotal(self) -> int:
        return self.unit_price * self.quantity


@dataclass(frozen=True)
class Receipt:
    order_id: int
    lines: list
    total: int
    paid_at: str


def _now() -> str:
    return datetime.now().isoformat(sep=" ", timespec="seconds")


class OrderService:
    def __init__(self, db: Database):
        self.db = db
        # 前回会計せずに終了した注文があれば引き継ぐ
        self.order_id = db.find_open_order_id() or db.create_order(_now())

    def add(self, menu_id: str, quantity: int) -> int:
        if not isinstance(quantity, int) or not QUANTITY_MIN <= quantity <= QUANTITY_MAX:
            raise OrderError(f"数量は {QUANTITY_MIN}〜{QUANTITY_MAX} で指定してください。")
        try:
            item = get_item(menu_id)
        except KeyError as e:
            raise OrderError(str(e)) from None
        return self.db.add_item(self.order_id, item.id, item.name, item.price, quantity, _now())

    def cancel(self, line_id: int):
        row = self.db.get_item(line_id)
        if row is None or row["order_id"] != self.order_id:
            raise OrderError("取り消す注文が見つかりません。")
        if row["status"] == "cancelled":
            raise OrderError("この注文はすでに取り消されています。")
        self.db.cancel_item(line_id, _now())

    def lines(self) -> list:
        return [OrderLine(r["id"], r["menu_id"], r["name"], r["unit_price"], r["quantity"], r["ordered_at"])
                for r in self.db.active_items(self.order_id)]

    def total(self) -> int:
        return sum(line.subtotal for line in self.lines())

    def checkout(self) -> Receipt:
        lines = self.lines()
        if not lines:
            raise OrderError("注文がありません。")
        total = sum(line.subtotal for line in lines)
        paid_at = _now()
        self.db.mark_paid(self.order_id, total, paid_at)
        receipt = Receipt(self.order_id, lines, total, paid_at)
        self.order_id = self.db.create_order(_now())  # 次のお客さま用の新しい伝票
        return receipt

    def history(self, limit: int = 100):
        return self.db.paid_orders(limit)

    def recommend(self, age: int, gender: str) -> list:
        results: list[Recommendation] = recommend(age, gender)
        self.db.log_recommendation(age, gender, ",".join(r.item.id for r in results), _now())
        return results

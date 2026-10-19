"""アプリ全体の設定値"""
from __future__ import annotations

import os
from pathlib import Path

STORE_NAME = "洋食ダイニング こうべ亭"
STORE_CATCHPHRASE = "港町の洋食を、気軽にどうぞ。"

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 環境変数 RESTAURANT_DB で保存先を変更できる（テスト用など）
DB_PATH = Path(os.environ.get("RESTAURANT_DB", PROJECT_ROOT / "data" / "orders.db"))

AGE_MIN = 0
AGE_MAX = 120
QUANTITY_MIN = 1
QUANTITY_MAX = 99

"""入力チェック。不正な入力は ValidationError として返し、アプリは停止させない。"""
from __future__ import annotations

import re
import unicodedata

from .config import AGE_MAX, AGE_MIN, QUANTITY_MAX, QUANTITY_MIN

_DIGITS = re.compile(r"[0-9]+")


class ValidationError(ValueError):
    """利用者に表示できるメッセージを持つ入力エラー"""


def _parse_int(text, label: str, low: int, high: int) -> int:
    # 全角数字・前後の空白を許容する（"２０ " → "20"）
    normalized = unicodedata.normalize("NFKC", str(text if text is not None else "")).strip()
    if normalized == "":
        raise ValidationError(f"{label}を入力してください。")
    if normalized.startswith("-") and _DIGITS.fullmatch(normalized[1:]):
        raise ValidationError(f"{label}に負の値は入力できません。")
    if not _DIGITS.fullmatch(normalized):
        raise ValidationError(f"{label}は整数（半角または全角の数字）で入力してください。")
    value = int(normalized)
    if not low <= value <= high:
        raise ValidationError(f"{label}は {low}〜{high} の範囲で入力してください。")
    return value


def parse_age(text) -> int:
    return _parse_int(text, "年齢", AGE_MIN, AGE_MAX)


def parse_quantity(text) -> int:
    return _parse_int(text, "数量", QUANTITY_MIN, QUANTITY_MAX)

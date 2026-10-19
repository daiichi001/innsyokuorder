"""年齢・性別・アレルギーからおすすめ料理を選ぶ（ルールベースのスコアリング）"""
from __future__ import annotations

from dataclasses import dataclass

from .menu import CATEGORIES, MenuItem, items_in

GENDERS = ("回答しない", "男性", "女性", "その他")

# 年齢層ごとに、加点するタグと点数
AGE_GROUPS = (
    # (上限年齢, 年齢層名, タグ重み)
    (12, "お子さま", {"kids": 3, "kids_only": 2, "sweet": 1}),
    (19, "10代", {"teen": 3, "hearty": 1, "share": 1}),
    (39, "20〜30代", {"hearty": 2, "alcohol": 2, "alcohol_pair": 1, "share": 1}),
    (59, "40〜50代", {"healthy": 2, "alcohol_pair": 2, "alcohol": 1, "light": 1, "premium": 1}),
    (999, "60代以上", {"senior": 3, "healthy": 1, "light": 1, "premium": 1}),
)

GENDER_WEIGHTS = {
    "男性": {"hearty": 1, "protein": 1},
    "女性": {"healthy": 1, "sweet": 1},
}

TAG_REASONS = {
    "kids_only": "お子さま限定",
    "kids": "お子さまに人気",
    "teen": "10代に人気",
    "hearty": "食べごたえ満点",
    "share": "みんなでつまめる",
    "alcohol": "お酒好きの方に",
    "alcohol_pair": "お酒のおともに",
    "healthy": "ヘルシー",
    "light": "あっさり食べやすい",
    "senior": "やさしい味わい",
    "sweet": "甘いもの好きの方に",
    "protein": "高たんぱく",
    "premium": "旬の高級ネタ",
}


@dataclass(frozen=True)
class Recommendation:
    item: MenuItem
    score: int
    reason: str


def age_group(age: int) -> tuple[str, dict]:
    for upper, label, weights in AGE_GROUPS:
        if age <= upper:
            return label, weights
    raise ValueError(age)  # AGE_GROUPS の最後が上限を持つので到達しない


def is_allowed(item: MenuItem, age: int) -> bool:
    if "alcohol" in item.tags and age < 20:
        return False  # 未成年にお酒はすすめない
    if "kids_only" in item.tags and age > 12:
        return False
    return True


def recommend(age: int, gender: str, exclude_allergens=()) -> list[Recommendation]:
    """カテゴリごとに最もスコアの高い1品を返す（CATEGORIES の順）。
    アレルゲンを含む品は候補から外し、候補が残らないカテゴリは結果に含めない。"""
    _, weights = age_group(age)
    weights = dict(weights)
    for tag, point in GENDER_WEIGHTS.get(gender, {}).items():
        weights[tag] = weights.get(tag, 0) + point

    results = []
    for category in CATEGORIES:
        candidates = [item for item in items_in(category, exclude_allergens) if is_allowed(item, age)]
        if not candidates:
            continue
        # 同点ならメニュー順で先のものを選ぶ（max は最初の最大値を返す）
        best = max(candidates, key=lambda item: _score(item, weights))
        results.append(Recommendation(best, _score(best, weights), _reason(best, weights)))
    return results


def _score(item: MenuItem, weights: dict) -> int:
    return sum(weights.get(tag, 0) for tag in item.tags)


def _reason(item: MenuItem, weights: dict) -> str:
    matched = sorted((tag for tag in item.tags if weights.get(tag, 0) > 0 and tag in TAG_REASONS),
                     key=lambda tag: -weights[tag])
    if not matched:
        return "当店の定番"
    return "・".join(TAG_REASONS[tag] for tag in matched[:2])

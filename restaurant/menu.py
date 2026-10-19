"""メニューデータ（価格はすべて税込・円）"""
from __future__ import annotations

from dataclasses import dataclass

CATEGORIES = ("握り", "巻物・軍艦", "一品料理", "ドリンク", "デザート")

# 表示・絞り込みに使うアレルゲン。
# 先頭8品目は表示義務のある「特定原材料」、残りは寿司店で特に関係の深い推奨表示品目。
ALLERGENS = ("卵", "乳", "小麦", "えび", "かに", "そば", "落花生", "くるみ",
             "いか", "いくら", "さけ", "さば", "大豆", "ごま")


@dataclass(frozen=True)
class MenuItem:
    id: str
    name: str
    category: str
    price: int
    description: str
    allergens: frozenset  # ALLERGENS に含まれる名前のみ
    tags: frozenset       # おすすめ判定用のタグ（recommend.py 参照）

    def contains_any(self, allergens) -> bool:
        return not self.allergens.isdisjoint(allergens)

    @property
    def allergen_label(self) -> str:
        """ALLERGENS の順に並べた表示用文字列。なければ「なし」。"""
        return "・".join(a for a in ALLERGENS if a in self.allergens) or "なし"


def _item(id, name, category, price, description, allergens=(), tags=()):
    unknown = set(allergens) - set(ALLERGENS)
    assert not unknown, f"{id}: 未定義のアレルゲン {unknown}"
    return MenuItem(id, name, category, price, description, frozenset(allergens), frozenset(tags))


MENU = (
    # ---- 握り（2貫） ----
    _item("N01", "まぐろ", "握り", 480, "近海本まぐろの赤身", (), ("kids", "teen", "protein")),
    _item("N02", "中とろ", "握り", 880, "脂と赤身のバランスが絶妙", (), ("hearty", "premium")),
    _item("N03", "大とろ", "握り", 1280, "口の中でとろける極上部位", (), ("premium", "hearty")),
    _item("N04", "サーモン", "握り", 420, "とろけるノルウェー産", ("さけ",), ("kids", "teen")),
    _item("N05", "はまち", "握り", 480, "脂ののった瀬戸内産", (), ("alcohol_pair", "protein")),
    _item("N06", "明石鯛", "握り", 580, "明石海峡で育った真鯛", (), ("healthy", "senior", "light")),
    _item("N07", "えび", "握り", 420, "甘みのあるボイルえび", ("えび",), ("kids",)),
    _item("N08", "いか", "握り", 380, "ねっとり甘いもんごういか", ("いか",), ("light", "alcohol_pair")),
    _item("N09", "うに", "握り", 980, "北海道産の濃厚な生うに", (), ("premium", "alcohol_pair")),
    _item("N10", "玉子", "握り", 280, "だしの効いた自家製厚焼き", ("卵", "大豆"), ("kids", "sweet", "senior")),
    _item("N11", "煮穴子", "握り", 580, "ふっくら煮上げて甘だれで", ("小麦", "大豆"), ("senior", "sweet")),
    _item("N12", "しめさば", "握り", 420, "自家製の浅じめ", ("さば",), ("alcohol_pair", "healthy")),
    _item("N13", "ずわいがに", "握り", 780, "身をたっぷりのせて", ("かに",), ("premium",)),
    _item("N14", "お子さま寿司セット", "握り", 880, "12歳以下限定（まぐろ・サーモン・えび・玉子・巻物）",
          ("卵", "えび", "さけ", "小麦", "大豆"), ("kids_only", "kids")),
    # ---- 巻物・軍艦 ----
    _item("K01", "鉄火巻", "巻物・軍艦", 520, "まぐろ赤身の細巻き", (), ("protein", "share")),
    _item("K02", "かっぱ巻", "巻物・軍艦", 280, "きゅうりと白ごま", ("ごま",), ("light", "healthy")),
    _item("K03", "ねぎとろ巻", "巻物・軍艦", 580, "まぐろのたたきと青ねぎ", (), ("teen", "share", "senior")),
    _item("K04", "いくら軍艦", "巻物・軍艦", 780, "自家製醤油漬け", ("いくら", "小麦", "大豆"), ("premium", "alcohol_pair")),
    _item("K05", "カリフォルニアロール", "巻物・軍艦", 680, "かにかま・アボカド・マヨネーズ",
          ("卵", "小麦", "かに", "大豆", "ごま"), ("teen", "share", "hearty")),
    _item("K06", "サラダ軍艦", "巻物・軍艦", 380, "かにかまとマヨネーズ", ("卵", "小麦", "かに", "大豆"), ("kids", "teen")),
    # ---- 一品料理 ----
    _item("I01", "茶碗蒸し", "一品料理", 420, "えびと銀杏入り", ("卵", "えび", "小麦", "大豆"), ("senior", "light", "kids")),
    _item("I02", "えび天ぷら", "一品料理", 780, "大えび2本を天つゆで", ("えび", "小麦", "卵", "大豆"), ("hearty", "alcohol_pair")),
    _item("I03", "鶏の唐揚げ", "一品料理", 580, "生姜醤油に漬け込んで", ("小麦", "大豆"), ("kids", "teen", "hearty", "share")),
    _item("I04", "枝豆", "一品料理", 380, "塩ゆでしたての丹波産", ("大豆",), ("alcohol_pair", "healthy", "share")),
    _item("I05", "あさりの赤だし", "一品料理", 300, "八丁味噌の香り", ("大豆",), ("senior", "healthy", "light")),
    _item("I06", "天ざるそば", "一品料理", 980, "二八そばとえび天", ("そば", "小麦", "えび", "卵", "大豆"), ("hearty",)),
    _item("I07", "いんげんのピーナッツ和え", "一品料理", 380, "香ばしい落花生だれ", ("落花生", "大豆"), ("healthy",)),
    # ---- ドリンク ----
    _item("D01", "オレンジジュース", "ドリンク", 280, "果汁100%", (), ("kids", "soft")),
    _item("D02", "ウーロン茶", "ドリンク", 280, "すっきり無糖", (), ("soft", "healthy", "senior")),
    _item("D03", "コーラ", "ドリンク", 300, "よく冷えた瓶で", (), ("teen", "soft")),
    _item("D04", "ラムネ", "ドリンク", 250, "昔なつかしのびん入り", (), ("kids", "teen", "soft")),
    _item("D05", "生ビール", "ドリンク", 580, "※20歳以上", (), ("alcohol", "hearty")),
    _item("D06", "日本酒（灘の地酒）1合", "ドリンク", 780, "※20歳以上・冷/燗", (), ("alcohol", "alcohol_pair", "senior")),
    _item("D07", "レモンサワー", "ドリンク", 480, "※20歳以上", (), ("alcohol", "light")),
    _item("D08", "抹茶ラテ", "ドリンク", 420, "宇治抹茶とミルク", ("乳",), ("sweet", "soft")),
    # ---- デザート ----
    _item("S01", "抹茶アイス", "デザート", 320, "濃いめの宇治抹茶", ("乳",), ("sweet", "kids", "light")),
    _item("S02", "わらびもち", "デザート", 380, "きな粉と黒蜜で", ("大豆",), ("sweet", "senior", "light")),
    _item("S03", "杏仁豆腐", "デザート", 350, "なめらかな口あたり", ("乳",), ("sweet", "light")),
    _item("S04", "黒ごまプリン", "デザート", 380, "香ばしい練りごま", ("乳", "ごま"), ("sweet", "healthy")),
    _item("S05", "季節のフルーツ盛り", "デザート", 480, "旬の果物を3種", (), ("healthy", "light")),
    _item("S06", "くるみ餅", "デザート", 380, "くるみ入りのもちもち和菓子", ("くるみ", "大豆"), ("sweet", "senior")),
)

_MENU_BY_ID = {item.id: item for item in MENU}


def get_item(menu_id: str) -> MenuItem:
    try:
        return _MENU_BY_ID[menu_id]
    except KeyError:
        raise KeyError(f"メニューID {menu_id} は存在しません") from None


def items_in(category: str | None, exclude_allergens=()) -> list[MenuItem]:
    """カテゴリで絞り込み、指定アレルゲンを含む品を除外する。category が None ならすべて。"""
    return [item for item in MENU
            if (category is None or item.category == category) and not item.contains_any(exclude_allergens)]

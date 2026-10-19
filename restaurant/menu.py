"""メニューデータ（価格はすべて税込・円）"""
from __future__ import annotations

from dataclasses import dataclass

CATEGORIES = ("前菜", "メイン", "ドリンク", "デザート")


@dataclass(frozen=True)
class MenuItem:
    id: str
    name: str
    category: str
    price: int
    description: str
    tags: frozenset  # おすすめ判定用のタグ（recommend.py 参照）


def _item(id, name, category, price, description, *tags):
    return MenuItem(id, name, category, price, description, frozenset(tags))


MENU = (
    # ---- 前菜 ----
    _item("A01", "シーザーサラダ", "前菜", 680, "ロメインレタスと自家製ドレッシング", "healthy", "light"),
    _item("A02", "生ハムとチーズの盛り合わせ", "前菜", 980, "お酒によく合う人気の一皿", "alcohol_pair", "share"),
    _item("A03", "フライドポテト", "前菜", 480, "皮付きでホクホク", "kids", "teen", "share"),
    _item("A04", "季節野菜のバーニャカウダ", "前菜", 780, "旬の野菜をアンチョビソースで", "healthy"),
    _item("A05", "コーンスープ", "前菜", 420, "北海道産とうもろこし使用", "kids", "light", "senior"),
    _item("A06", "カプレーゼ", "前菜", 720, "トマトとモッツァレラ", "healthy", "light"),
    # ---- メイン ----
    _item("M01", "デミグラスハンバーグ", "メイン", 1280, "当店自慢の看板メニュー", "kids", "hearty"),
    _item("M02", "サーロインステーキ 200g", "メイン", 2480, "国産牛をミディアムレアで", "hearty", "protein"),
    _item("M03", "マルゲリータピザ", "メイン", 1180, "石窯で焼き上げる定番ピザ", "share", "teen", "kids"),
    _item("M04", "濃厚カルボナーラ", "メイン", 1080, "卵黄たっぷりのクリーミーな味わい", "hearty", "teen"),
    _item("M05", "鮮魚のアクアパッツァ", "メイン", 1680, "本日の鮮魚をあさりと煮込んで", "healthy", "senior"),
    _item("M06", "お子さまランチ", "メイン", 880, "12歳以下のお子さま限定", "kids_only", "kids"),
    _item("M07", "ふわとろオムライス", "メイン", 980, "やさしい味わいの卵料理", "kids", "senior", "light"),
    _item("M08", "ハーブチキンのグリル", "メイン", 1180, "鶏むね肉で高たんぱく・低脂質", "healthy", "protein"),
    # ---- ドリンク ----
    _item("D01", "オレンジジュース", "ドリンク", 380, "果汁100%", "kids", "soft"),
    _item("D02", "ウーロン茶", "ドリンク", 300, "すっきり無糖", "soft", "healthy", "senior"),
    _item("D03", "コーラ", "ドリンク", 350, "よく冷えたグラスで", "soft", "teen"),
    _item("D04", "ホットコーヒー", "ドリンク", 400, "自家焙煎ブレンド", "soft", "senior"),
    _item("D05", "生ビール", "ドリンク", 580, "※20歳以上", "alcohol", "hearty"),
    _item("D06", "グラスワイン（赤・白）", "ドリンク", 650, "※20歳以上", "alcohol", "alcohol_pair"),
    _item("D07", "ハイボール", "ドリンク", 500, "※20歳以上", "alcohol", "light"),
    _item("D08", "ほうじ茶ラテ", "ドリンク", 450, "香ばしくてほんのり甘い", "soft", "sweet"),
    # ---- デザート ----
    _item("S01", "バニラアイス", "デザート", 380, "濃厚ミルクのジェラート", "kids", "sweet", "light"),
    _item("S02", "ガトーショコラ", "デザート", 550, "しっとり濃厚なチョコレートケーキ", "sweet"),
    _item("S03", "季節のフルーツパフェ", "デザート", 880, "旬のフルーツをたっぷり", "sweet", "kids", "teen"),
    _item("S04", "抹茶プリン", "デザート", 480, "京都宇治抹茶使用", "sweet", "senior", "light"),
    _item("S05", "ニューヨークチーズケーキ", "デザート", 580, "どっしり濃厚な焼きチーズケーキ", "sweet", "hearty"),
)

_MENU_BY_ID = {item.id: item for item in MENU}


def get_item(menu_id: str) -> MenuItem:
    try:
        return _MENU_BY_ID[menu_id]
    except KeyError:
        raise KeyError(f"メニューID {menu_id} は存在しません") from None


def items_in(category: str | None) -> list[MenuItem]:
    """カテゴリで絞り込む。None ならすべて。"""
    return [item for item in MENU if category is None or item.category == category]

"""tkinter による画面"""
from __future__ import annotations

import tkinter as tk
import traceback
from datetime import date
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from .config import QUANTITY_MAX, QUANTITY_MIN, STORE_NAME
from .menu import ALLERGENS, CATEGORIES, items_in
from .order_service import OrderError, OrderService
from .recommend import GENDERS
from .validation import ValidationError, parse_age, parse_quantity

ALL_CATEGORIES = "すべて"
WEEKDAYS = "月火水木金土日"

# 配色: 生成り（和紙）・墨・朱
PAPER = "#f4efe4"      # 背景
SLIP = "#fbf8f1"       # 伝票・一覧の地
INK = "#2b2622"        # 文字
MUTED = "#8a7f72"      # 補足の文字
LINE = "#d8cdb9"       # 罫線
SELECT = "#eadfc8"     # 選択行
SHU = "#a8432c"        # 朱（合計とお会計だけに使う）
SHU_DARK = "#8c3622"

# フォントは起動時に環境にあるものから選ぶ（_setup_style）
F: dict = {}


def yen(value: int) -> str:
    return f"{value:,}円"


def receipt_yen(value: int) -> str:
    return f"¥{value:,}"


# ---------------------------------------------------------------------- 部品
def rule(parent, bg=LINE, height=1, **pack):
    line = tk.Frame(parent, bg=bg, height=height)
    line.pack(fill="x", **pack)
    return line


def section_title(parent, text, note="", bg=PAPER):
    row = tk.Frame(parent, bg=bg)
    row.pack(fill="x", pady=(0, 4))
    tk.Label(row, text=text, font=F["section"], fg=INK, bg=bg).pack(side="left")
    if note:
        tk.Label(row, text=note, font=F["small"], fg=MUTED, bg=bg).pack(side="left", padx=(10, 0), pady=(4, 0))
    rule(parent, pady=(0, 8))
    return row


def button(parent, text, command, primary=False, bg=PAPER):
    """枠線だけの控えめなボタン。primary は朱色のお会計ボタン。"""
    if primary:
        return tk.Button(parent, text=text, command=command, font=F["checkout"], fg="#ffffff", bg=SHU,
                         activebackground=SHU_DARK, activeforeground="#ffffff", relief="flat", bd=0,
                         cursor="hand2", pady=8)
    outer = tk.Frame(parent, bg=INK, padx=1, pady=1)
    tk.Button(outer, text=text, command=command, font=F["body"], fg=INK, bg=bg, activebackground=SELECT,
              activeforeground=INK, relief="flat", bd=0, cursor="hand2", padx=12, pady=2).pack(fill="both")
    return outer


def table(parent, columns, height=None, selectmode="browse"):
    """罫線で囲んだ Treeview。columns は (key, 見出し, 幅, 寄せ, 伸縮) のタプル。"""
    box = tk.Frame(parent, bg=LINE, padx=1, pady=1)
    inner = tk.Frame(box, bg=SLIP)
    inner.pack(fill="both", expand=True)
    tree = ttk.Treeview(inner, columns=[c[0] for c in columns], show="headings",
                        selectmode=selectmode, **({"height": height} if height else {}))
    for key, text, width, anchor, stretch in columns:
        tree.heading(key, text=text, anchor=anchor)
        tree.column(key, width=width, minwidth=40, anchor=anchor, stretch=stretch)
    scroll = ttk.Scrollbar(inner, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)
    return box, tree


class CategoryTabs(tk.Frame):
    """文字だけのタブ。選択中は下に朱の線を引く。"""

    def __init__(self, parent, names, variable: tk.StringVar, command):
        super().__init__(parent, bg=PAPER)
        self.variable = variable
        self.command = command
        self.tabs = {}
        for name in names:
            cell = tk.Frame(self, bg=PAPER, cursor="hand2")
            cell.pack(side="left", padx=(0, 18))
            label = tk.Label(cell, text=name, font=F["tab"], fg=MUTED, bg=PAPER, cursor="hand2")
            label.pack()
            underline = tk.Frame(cell, height=2, bg=PAPER)
            underline.pack(fill="x")
            for widget in (cell, label):
                widget.bind("<Button-1>", lambda _e, n=name: self.select(n))
            self.tabs[name] = (label, underline)
        variable.trace_add("write", lambda *_: self._paint())
        self._paint()

    def select(self, name):
        self.variable.set(name)
        self.command()

    def _paint(self):
        for name, (label, underline) in self.tabs.items():
            active = name == self.variable.get()
            label.configure(fg=INK if active else MUTED, font=F["tab_active"] if active else F["tab"])
            underline.configure(bg=SHU if active else PAPER)


# ---------------------------------------------------------------------- 本体
class OrderApp(tk.Frame):
    def __init__(self, master: tk.Tk, service: OrderService):
        super().__init__(master, bg=PAPER, padx=22, pady=14)
        self.service = service
        self.category_var = tk.StringVar(value=ALL_CATEGORIES)
        self.quantity_var = tk.StringVar(value="1")
        self.age_var = tk.StringVar()
        self.gender_var = tk.StringVar(value=GENDERS[0])
        self.total_var = tk.StringVar()
        self.slip_no_var = tk.StringVar()
        self.age_error_var = tk.StringVar()
        self.allergy_status_var = tk.StringVar()
        self.rec_note_var = tk.StringVar()
        self.allergen_vars = {name: tk.BooleanVar(value=False) for name in ALLERGENS}
        self._recommendation_shown = False

        self._build_header()
        body = tk.Frame(self, bg=PAPER)
        body.pack(fill="both", expand=True, pady=(14, 0))
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2, minsize=380)
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=PAPER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 22))
        self._build_allergy_panel(left)
        # おすすめ欄を先に下から配置し、残りの高さをお品書きに使う（画面が低くても欠けない）
        self._build_recommend_panel(left)
        self._build_menu_panel(left)
        self._build_slip(body)

        self.show_category()
        self.refresh_order()

    # ------------------------------------------------------------------ 画面構築
    def _build_header(self):
        header = tk.Frame(self, bg=PAPER)
        header.pack(fill="x")
        prefix, _, name = STORE_NAME.partition(" ")
        if name:
            tk.Label(header, text=prefix, font=F["store_prefix"], fg=INK, bg=PAPER).pack(side="left", pady=(10, 0))
        tk.Label(header, text=name or prefix, font=F["store"], fg=INK, bg=PAPER).pack(side="left", padx=(6, 0))

        history = tk.Label(header, text="会計履歴", font=F["small"], fg=MUTED, bg=PAPER, cursor="hand2")
        history.pack(side="right", pady=(14, 0))
        history.bind("<Button-1>", lambda _e: self.show_history())
        history.bind("<Enter>", lambda _e: history.configure(fg=INK, font=F["small_u"]))
        history.bind("<Leave>", lambda _e: history.configure(fg=MUTED, font=F["small"]))
        today = date.today()
        tk.Label(header, text=f"{today.month}月{today.day}日（{WEEKDAYS[today.weekday()]}）　",
                 font=F["small"], fg=MUTED, bg=PAPER).pack(side="right", pady=(14, 0))

        # 品書きふうの二重線
        rule(self, bg=INK, height=2, pady=(6, 0))
        rule(self, bg=INK, height=1, pady=(2, 0))

    def _build_allergy_panel(self, parent):
        frame = tk.Frame(parent, bg=PAPER)
        frame.pack(fill="x", pady=(0, 14))
        head = section_title(frame, "アレルギー", "チェックした食材を使った品は表示しません")
        tk.Label(head, textvariable=self.allergy_status_var, font=F["small"], fg=SHU, bg=PAPER).pack(side="right")

        row = tk.Frame(frame, bg=PAPER)
        row.pack(fill="x")
        grid = tk.Frame(row, bg=PAPER)
        grid.pack(side="left")
        per_row = 7
        for i, name in enumerate(ALLERGENS):
            tk.Checkbutton(grid, text=name, variable=self.allergen_vars[name], command=self.on_allergy_change,
                           font=F["body"], fg=INK, bg=PAPER, activebackground=PAPER, selectcolor=SLIP,
                           highlightthickness=0, bd=0, cursor="hand2", width=6, anchor="w"
                           ).grid(row=i // per_row, column=i % per_row, sticky="w", padx=(0, 4))
        button(row, "解除", self.clear_allergies).pack(side="right", anchor="n")
        tk.Label(frame, text="※醤油・甘だれには小麦・大豆を使用しています。",
                 font=F["small"], fg=MUTED, bg=PAPER).pack(anchor="w", pady=(4, 0))

    def _build_menu_panel(self, parent):
        frame = tk.Frame(parent, bg=PAPER)
        frame.pack(fill="both", expand=True)
        section_title(frame, "お品書き", "握りは二貫・価格は税込")

        CategoryTabs(frame, (ALL_CATEGORIES, *CATEGORIES), self.category_var,
                     self.show_category).pack(fill="x", pady=(0, 8))

        controls = tk.Frame(frame, bg=PAPER)
        controls.pack(side="bottom", fill="x", pady=(8, 0))
        box, self.menu_tree = table(frame, (
            ("category", "区分", 80, "w", False),
            ("name", "品名", 170, "w", False),
            ("description", "", 200, "w", True),
            ("allergens", "アレルギー", 160, "w", False),
            ("price", "価格", 80, "e", False),
        ), height=6)
        box.pack(fill="both", expand=True)
        self.menu_tree.bind("<Double-1>", lambda _e: self.add_selected_menu())

        tk.Label(controls, text="数量", font=F["body"], fg=INK, bg=PAPER).pack(side="left")
        ttk.Spinbox(controls, from_=QUANTITY_MIN, to=QUANTITY_MAX, width=4,
                    textvariable=self.quantity_var).pack(side="left", padx=(6, 10))
        button(controls, "注文", self.add_selected_menu).pack(side="left")
        tk.Label(controls, text="品名のダブルクリックでも注文できます", font=F["small"],
                 fg=MUTED, bg=PAPER).pack(side="right")

    def _build_recommend_panel(self, parent):
        frame = tk.Frame(parent, bg=PAPER)
        frame.pack(side="bottom", fill="x", pady=(16, 0))
        section_title(frame, "おすすめ", "年齢と性別から一品ずつお選びします")

        form = tk.Frame(frame, bg=PAPER)
        form.pack(fill="x", pady=(0, 8))
        tk.Label(form, text="年齢", font=F["body"], fg=INK, bg=PAPER).pack(side="left")
        age_entry = ttk.Entry(form, textvariable=self.age_var, width=5, justify="right")
        age_entry.pack(side="left", padx=(6, 2))
        age_entry.bind("<Return>", lambda _e: self.show_recommendations())
        tk.Label(form, text="歳", font=F["body"], fg=INK, bg=PAPER).pack(side="left", padx=(0, 16))
        tk.Label(form, text="性別", font=F["body"], fg=INK, bg=PAPER).pack(side="left")
        ttk.Combobox(form, textvariable=self.gender_var, values=GENDERS, state="readonly",
                     width=9).pack(side="left", padx=(6, 12))
        button(form, "表示", self.show_recommendations).pack(side="left")
        tk.Label(form, textvariable=self.age_error_var, font=F["small"], fg=SHU, bg=PAPER).pack(side="left", padx=12)

        box, self.rec_tree = table(frame, (
            ("category", "区分", 80, "w", False),
            ("name", "品名", 170, "w", False),
            ("reason", "", 200, "w", True),
            ("allergens", "アレルギー", 160, "w", False),
            ("price", "価格", 80, "e", False),
        ), height=len(CATEGORIES))
        box.pack(fill="x")
        self.rec_tree.bind("<Double-1>", lambda _e: self.add_selected_recommendation())

        bottom = tk.Frame(frame, bg=PAPER)
        bottom.pack(fill="x", pady=(8, 0))
        button(bottom, "選んだ品を注文", self.add_selected_recommendation).pack(side="left")
        tk.Label(bottom, textvariable=self.rec_note_var, font=F["small"], fg=MUTED, bg=PAPER).pack(side="left", padx=12)

    def _build_slip(self, parent):
        """右側のお伝票"""
        outer = tk.Frame(parent, bg=LINE, padx=1, pady=1)
        outer.grid(row=0, column=1, sticky="nsew")
        slip = tk.Frame(outer, bg=SLIP, padx=18, pady=14)
        slip.pack(fill="both", expand=True)

        head = section_title(slip, "お伝票", bg=SLIP)
        tk.Label(head, textvariable=self.slip_no_var, font=F["small"], fg=MUTED, bg=SLIP).pack(side="right")

        bottom = tk.Frame(slip, bg=SLIP)
        bottom.pack(side="bottom", fill="x")

        holder = tk.Frame(slip, bg=SLIP)
        holder.pack(fill="both", expand=True)
        self.order_tree = ttk.Treeview(holder, columns=("name", "price", "qty", "subtotal"), show="headings",
                                       selectmode="extended", style="Slip.Treeview")
        for key, text, width, anchor, stretch in (("name", "品名", 150, "w", True), ("price", "単価", 70, "e", False),
                                                  ("qty", "数", 40, "center", False),
                                                  ("subtotal", "金額", 80, "e", False)):
            self.order_tree.heading(key, text=text, anchor=anchor)
            self.order_tree.column(key, width=width, minwidth=36, anchor=anchor, stretch=stretch)
        self.order_tree.pack(fill="both", expand=True)
        self.empty_label = tk.Label(holder, text="ご注文はまだありません", font=F["body"], fg=MUTED, bg=SLIP)

        actions = tk.Frame(bottom, bg=SLIP)
        actions.pack(fill="x", pady=(8, 0))
        button(actions, "取消", self.cancel_selected, bg=SLIP).pack(side="left")
        tk.Label(actions, text="取り消す品を選んでから", font=F["small"], fg=MUTED, bg=SLIP).pack(side="left", padx=8)

        rule(bottom, bg=INK, pady=(12, 0))
        total_row = tk.Frame(bottom, bg=SLIP)
        total_row.pack(fill="x", pady=(8, 12))
        tk.Label(total_row, text="合計（税込）", font=F["body"], fg=INK, bg=SLIP).pack(side="left", anchor="s", pady=(0, 6))
        tk.Label(total_row, textvariable=self.total_var, font=F["total"], fg=SHU, bg=SLIP).pack(side="right")
        button(bottom, "お会計", self.checkout, primary=True).pack(fill="x")

    # ------------------------------------------------------------------ アレルギー
    def selected_allergens(self) -> tuple:
        return tuple(name for name, var in self.allergen_vars.items() if var.get())

    def on_allergy_change(self):
        self.show_category()
        if self._recommendation_shown:
            self.show_recommendations()

    def clear_allergies(self):
        for var in self.allergen_vars.values():
            var.set(False)
        self.on_allergy_change()

    # ------------------------------------------------------------------ お品書き
    def show_category(self):
        category = None if self.category_var.get() == ALL_CATEGORIES else self.category_var.get()
        allergens = self.selected_allergens()
        # 「すべて」のときだけ区分の列を出す
        columns = ("category", "name", "description", "allergens", "price")
        self.menu_tree.configure(displaycolumns=columns if category is None else columns[1:])
        self.menu_tree.delete(*self.menu_tree.get_children())
        for item in items_in(category, allergens):
            self.menu_tree.insert("", "end", iid=item.id,
                                  values=(item.category, item.name, item.description,
                                          item.allergen_label, yen(item.price)))
        hidden = len(items_in(category)) - len(self.menu_tree.get_children())
        self.allergy_status_var.set(f"{hidden}品を非表示" if allergens else "")

    def add_selected_menu(self):
        selected = self.menu_tree.selection()
        if not selected:
            messagebox.showinfo("注文", "お品書きから品を選んでください。", parent=self)
            return
        self._add(selected[0])

    def _add(self, menu_id: str):
        try:
            quantity = parse_quantity(self.quantity_var.get())
            self.service.add(menu_id, quantity)
        except (ValidationError, OrderError) as e:
            messagebox.showwarning("入力エラー", str(e), parent=self)
            return
        self.quantity_var.set("1")
        self.refresh_order()

    # ------------------------------------------------------------------ おすすめ
    def show_recommendations(self):
        self.rec_tree.delete(*self.rec_tree.get_children())
        self.rec_note_var.set("")
        self._recommendation_shown = False
        try:
            age = parse_age(self.age_var.get())
        except ValidationError as e:
            self.age_error_var.set(str(e))  # エラーを表示するだけで処理は続行
            return
        self.age_error_var.set("")
        allergens = self.selected_allergens()
        for rec in self.service.recommend(age, self.gender_var.get(), allergens):
            self.rec_tree.insert("", "end", iid=rec.item.id,
                                 values=(rec.item.category, rec.item.name, rec.reason,
                                         rec.item.allergen_label, yen(rec.item.price)))
        self._recommendation_shown = True
        if allergens:
            self.rec_note_var.set(f"{'・'.join(allergens)}を使った品は除いています")

    def add_selected_recommendation(self):
        selected = self.rec_tree.selection()
        if not selected:
            messagebox.showinfo("注文", "おすすめから品を選んでください。", parent=self)
            return
        self._add(selected[0])

    # ------------------------------------------------------------------ 注文・会計
    def refresh_order(self):
        self.order_tree.delete(*self.order_tree.get_children())
        lines = self.service.lines()
        for line in lines:
            self.order_tree.insert("", "end", iid=str(line.id),
                                   values=(line.name, yen(line.unit_price), line.quantity, yen(line.subtotal)))
        if lines:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(relx=0.5, rely=0.3, anchor="center")
        self.total_var.set(yen(self.service.total()))
        self.slip_no_var.set(f"No.{self.service.order_id:04d}")

    def cancel_selected(self):
        selected = self.order_tree.selection()
        if not selected:
            messagebox.showinfo("取消", "取り消す品をお伝票から選んでください。", parent=self)
            return
        names = "\n".join(f"{self.order_tree.set(iid, 'name')} × {self.order_tree.set(iid, 'qty')}"
                          for iid in selected)
        if not messagebox.askyesno("取消", f"取り消しますか？\n\n{names}", parent=self):
            return
        for iid in selected:
            try:
                self.service.cancel(int(iid))
            except OrderError as e:
                messagebox.showwarning("取消", str(e), parent=self)
        self.refresh_order()

    def checkout(self):
        if not self.service.lines():
            messagebox.showinfo("お会計", "まだご注文がありません。", parent=self)
            return
        receipt = self.service.checkout()
        self.refresh_order()
        ReceiptWindow(self, receipt)

    def show_history(self):
        HistoryWindow(self, self.service.history())


class ReceiptWindow(tk.Toplevel):
    """レシートふうの会計画面"""

    def __init__(self, parent, receipt):
        super().__init__(parent, bg=PAPER)
        self.title("お会計")
        self.resizable(False, False)
        self.transient(parent)
        paper = tk.Frame(self, bg="#fffdf8", padx=26, pady=20, highlightthickness=1, highlightbackground=LINE)
        paper.pack(padx=16, pady=16)

        tk.Label(paper, text=STORE_NAME, font=F["receipt_store"], fg=INK, bg=paper["bg"]).pack()
        paid = receipt.paid_at.replace("-", "/")[:16]
        tk.Label(paper, text=f"{paid}　No.{receipt.order_id:04d}", font=F["small"], fg=MUTED,
                 bg=paper["bg"]).pack(pady=(4, 0))
        self._dashed(paper)

        rows = tk.Frame(paper, bg=paper["bg"])
        rows.pack(fill="x")
        rows.columnconfigure(0, weight=1)
        for r, line in enumerate(receipt.lines):
            tk.Label(rows, text=line.name, font=F["body"], fg=INK, bg=paper["bg"]).grid(row=r * 2, column=0, sticky="w")
            tk.Label(rows, text=receipt_yen(line.subtotal), font=F["body"], fg=INK,
                     bg=paper["bg"]).grid(row=r * 2, column=1, sticky="e")
            if line.quantity > 1:
                tk.Label(rows, text=f"　{receipt_yen(line.unit_price)} × {line.quantity}", font=F["small"], fg=MUTED,
                         bg=paper["bg"]).grid(row=r * 2 + 1, column=0, sticky="w")
        self._dashed(paper)

        total = tk.Frame(paper, bg=paper["bg"])
        total.pack(fill="x")
        tk.Label(total, text="合計", font=F["section"], fg=INK, bg=paper["bg"]).pack(side="left", anchor="s")
        tk.Label(total, text=receipt_yen(receipt.total), font=F["total"], fg=INK, bg=paper["bg"]).pack(side="right")
        tax = receipt.total * 10 // 110
        tk.Label(paper, text=f"（内消費税等 10%　{receipt_yen(tax)}）", font=F["small"], fg=MUTED,
                 bg=paper["bg"]).pack(anchor="e")
        self._dashed(paper)
        tk.Label(paper, text="毎度ありがとうございます", font=F["receipt_store_s"], fg=INK, bg=paper["bg"]).pack()

        button(self, "閉じる", self.destroy).pack(pady=(0, 16))
        _center_on(self, parent.winfo_toplevel())
        self.grab_set()

    @staticmethod
    def _dashed(parent):
        canvas = tk.Canvas(parent, height=2, width=280, bg=parent["bg"], highlightthickness=0)
        canvas.create_line(0, 1, 2000, 1, fill=MUTED, dash=(4, 3))
        canvas.pack(fill="x", pady=10)


class HistoryWindow(tk.Toplevel):
    def __init__(self, parent, rows):
        super().__init__(parent, bg=PAPER, padx=16, pady=14)
        self.title("会計履歴")
        self.geometry("480x340")
        self.transient(parent)
        section_title(self, "会計履歴")
        box, tree = table(self, (
            ("id", "No.", 70, "w", False),
            ("paid_at", "日時", 170, "w", True),
            ("count", "点数", 60, "e", False),
            ("total", "合計", 100, "e", False),
        ))
        for row in rows:
            tree.insert("", "end", values=(f"{row['id']:04d}", row["paid_at"].replace("-", "/")[:16],
                                           row["item_count"], yen(row["total"])))
        box.pack(fill="both", expand=True)
        if not rows:
            tk.Label(self, text="会計済みの伝票はまだありません", font=F["body"], fg=MUTED, bg=PAPER).pack(pady=(8, 0))
        _center_on(self, parent.winfo_toplevel())


def _center_on(window: tk.Toplevel, parent: tk.Misc):
    window.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - window.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - window.winfo_height()) // 3
    window.geometry(f"+{max(x, 0)}+{max(y, 0)}")


def _pick(families, *candidates):
    return next((f for f in candidates if f in families), None)


def _setup_style(root: tk.Tk):
    families = set(tkfont.families(root))
    gothic = _pick(families, "Yu Gothic UI", "Meiryo UI", "Hiragino Sans", "Noto Sans CJK JP") \
        or tkfont.nametofont("TkDefaultFont").actual("family")
    # 見出しは明朝。なければゴシックで代用する
    mincho = _pick(families, "Yu Mincho", "游明朝", "YuMincho", "BIZ UDPMincho", "MS PMincho",
                   "Hiragino Mincho ProN", "Noto Serif CJK JP") or gothic
    for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont"):
        tkfont.nametofont(name).configure(family=gothic, size=10)

    F.update({
        "store": (mincho, 26, "bold"),
        "store_prefix": (mincho, 13),
        "section": (mincho, 13, "bold"),
        "tab": (mincho, 12),
        "tab_active": (mincho, 12, "bold"),
        "total": (mincho, 22, "bold"),
        "checkout": (mincho, 15, "bold"),
        "receipt_store": (mincho, 15, "bold"),
        "receipt_store_s": (mincho, 10),
        "body": (gothic, 10),
        "small": (gothic, 9),
        "small_u": (gothic, 9, "underline"),
    })

    root.configure(bg=PAPER)
    root.option_add("*TCombobox*Listbox.background", SLIP)
    root.option_add("*TCombobox*Listbox.selectBackground", SELECT)
    root.option_add("*TCombobox*Listbox.selectForeground", INK)

    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    style.configure(".", background=PAPER, foreground=INK, font=(gothic, 10))

    # 一覧: 枠なし・見出しは控えめ・選択行は薄い生成り
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure("Treeview", background=SLIP, fieldbackground=SLIP, foreground=INK,
                    rowheight=26, borderwidth=0, font=(gothic, 10))
    style.map("Treeview", background=[("selected", SELECT)], foreground=[("selected", INK)])
    style.configure("Treeview.Heading", background=SLIP, foreground=MUTED, relief="flat",
                    borderwidth=0, font=(gothic, 9), padding=(4, 4))
    style.map("Treeview.Heading", background=[("active", SLIP)])
    style.layout("Slip.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure("Slip.Treeview", background=SLIP, fieldbackground=SLIP, rowheight=28)
    style.configure("Slip.Treeview.Heading", background=SLIP, foreground=MUTED, relief="flat", borderwidth=0)

    style.configure("Vertical.TScrollbar", background=LINE, troughcolor=SLIP, bordercolor=SLIP,
                    lightcolor=LINE, darkcolor=LINE, arrowcolor=MUTED, gripcount=0)
    style.map("Vertical.TScrollbar", background=[("active", MUTED)])
    for widget in ("TEntry", "TSpinbox", "TCombobox"):
        style.configure(widget, fieldbackground=SLIP, background=PAPER, bordercolor=MUTED,
                        lightcolor=SLIP, darkcolor=SLIP, arrowcolor=INK, padding=(4, 2))
    style.map("TCombobox", fieldbackground=[("readonly", SLIP)], selectbackground=[("readonly", SLIP)],
              selectforeground=[("readonly", INK)])


def _window_icon(root: tk.Tk):
    """朱の角印ふうのアイコン（既定の羽根アイコンの代わり）"""
    size = 32
    icon = tk.PhotoImage(width=size, height=size)
    icon.put(SHU, to=(0, 0, size, size))
    icon.put("#fffdf8", to=(7, 7, size - 7, size - 7))
    icon.put(SHU, to=(10, 10, size - 10, size - 10))
    root.iconphoto(True, icon)
    root._icon = icon  # GC で消えないよう保持


def run(service: OrderService):
    root = tk.Tk()
    root.title(STORE_NAME)
    root.geometry("1200x800")
    root.minsize(1040, 720)
    _setup_style(root)
    _window_icon(root)

    # 想定外の例外が起きてもアプリを止めず、メッセージを表示して続行する
    def on_error(exc, value, tb):
        traceback.print_exception(exc, value, tb)
        messagebox.showerror("エラー", f"予期しないエラーが発生しました。\n{value}")
    root.report_callback_exception = on_error

    OrderApp(root, service).pack(fill="both", expand=True)
    root.mainloop()

"""tkinter による画面"""
from __future__ import annotations

import tkinter as tk
import traceback
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from .config import QUANTITY_MAX, QUANTITY_MIN, STORE_CATCHPHRASE, STORE_NAME
from .menu import ALLERGENS, CATEGORIES, items_in
from .order_service import OrderError, OrderService
from .recommend import GENDERS
from .validation import ValidationError, parse_age, parse_quantity

ALL_CATEGORIES = "すべて"

ACCENT = "#1f3a5f"         # 藍色
ACCENT_ACTIVE = "#2c5282"
CATCH_FG = "#c9d6e8"


def yen(value: int) -> str:
    return f"¥{value:,}"


class OrderApp(ttk.Frame):
    def __init__(self, master: tk.Tk, service: OrderService):
        super().__init__(master, padding=12)
        self.service = service
        self.category_var = tk.StringVar(value=ALL_CATEGORIES)
        self.quantity_var = tk.StringVar(value="1")
        self.age_var = tk.StringVar()
        self.gender_var = tk.StringVar(value=GENDERS[0])
        self.total_var = tk.StringVar()
        self.age_error_var = tk.StringVar()
        self.allergy_status_var = tk.StringVar()
        self.rec_note_var = tk.StringVar()
        self.allergen_vars = {name: tk.BooleanVar(value=False) for name in ALLERGENS}
        self._recommendation_shown = False

        self._build_header()
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=(10, 0))
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._build_allergy_panel(left)
        # おすすめ欄を先に下から配置し、残りの高さをメニュー一覧に使う（画面が低くても欠けない）
        self._build_recommend_panel(left)
        self._build_menu_panel(left)
        self._build_order_panel(body)

        self.show_category()
        self.refresh_order()

    # ------------------------------------------------------------------ 画面構築
    def _build_header(self):
        header = ttk.Frame(self, style="Header.TFrame", padding=(16, 10))
        header.pack(fill="x")
        ttk.Label(header, text=STORE_NAME, style="StoreName.TLabel").pack(side="left")
        ttk.Label(header, text=STORE_CATCHPHRASE, style="Catch.TLabel").pack(side="left", padx=16)
        ttk.Button(header, text="会計履歴", command=self.show_history).pack(side="right")

    def _build_allergy_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="アレルギー（チェックした食材を含む品をメニューとおすすめから除外）", padding=(8, 4))
        frame.pack(fill="x", pady=(0, 8))
        ttk.Label(frame, text="※醤油・甘だれには小麦・大豆が含まれます。ご不明な点はスタッフにおたずねください。",
                  style="Hint.TLabel").pack(side="bottom", anchor="w", pady=(4, 0))
        grid = ttk.Frame(frame)
        grid.pack(side="left", fill="x", expand=True)
        per_row = 7
        for i, name in enumerate(ALLERGENS):
            ttk.Checkbutton(grid, text=name, variable=self.allergen_vars[name],
                            command=self.on_allergy_change).grid(row=i // per_row, column=i % per_row,
                                                                 sticky="w", padx=(0, 10))
        side = ttk.Frame(frame)
        side.pack(side="right", fill="y")
        ttk.Button(side, text="すべて解除", command=self.clear_allergies).pack(anchor="e")
        ttk.Label(side, textvariable=self.allergy_status_var, style="Error.TLabel").pack(anchor="e", pady=(4, 0))

    def _build_menu_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="メニュー", padding=8)
        frame.pack(fill="both", expand=True)

        tabs = ttk.Frame(frame)
        tabs.pack(fill="x", pady=(0, 6))
        for name in (ALL_CATEGORIES, *CATEGORIES):
            ttk.Radiobutton(tabs, text=name, value=name, variable=self.category_var,
                            style="Toolbutton", command=self.show_category).pack(side="left", padx=2)

        columns = ("category", "name", "price", "allergens", "description")
        self.menu_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse", height=6)
        for col, text, width, anchor in (("category", "カテゴリ", 80, "center"), ("name", "品名", 160, "w"),
                                         ("price", "価格(税込)", 75, "e"), ("allergens", "アレルギー", 170, "w"),
                                         ("description", "説明", 200, "w")):
            self.menu_tree.heading(col, text=text)
            self.menu_tree.column(col, width=width, anchor=anchor, stretch=(col == "description"))
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.menu_tree.yview)
        self.menu_tree.configure(yscrollcommand=scroll.set)
        self.menu_tree.bind("<Double-1>", lambda _e: self.add_selected_menu())

        controls = ttk.Frame(frame)
        controls.pack(side="bottom", fill="x", pady=(6, 0))
        scroll.pack(side="right", fill="y")
        self.menu_tree.pack(side="left", fill="both", expand=True)

        ttk.Label(controls, text="数量").pack(side="left")
        ttk.Spinbox(controls, from_=QUANTITY_MIN, to=QUANTITY_MAX, width=5,
                    textvariable=self.quantity_var).pack(side="left", padx=6)
        ttk.Button(controls, text="注文する", style="Accent.TButton",
                   command=self.add_selected_menu).pack(side="left")
        ttk.Label(controls, text="（品名をダブルクリックでも注文できます）",
                  style="Hint.TLabel").pack(side="left", padx=8)

    def _build_recommend_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="おすすめ診断", padding=8)
        frame.pack(side="bottom", fill="x", pady=(10, 0))

        form = ttk.Frame(frame)
        form.pack(fill="x")
        ttk.Label(form, text="年齢").pack(side="left")
        age_entry = ttk.Entry(form, textvariable=self.age_var, width=6)
        age_entry.pack(side="left", padx=(4, 12))
        age_entry.bind("<Return>", lambda _e: self.show_recommendations())
        ttk.Label(form, text="性別").pack(side="left")
        ttk.Combobox(form, textvariable=self.gender_var, values=GENDERS, state="readonly",
                     width=10).pack(side="left", padx=(4, 12))
        ttk.Button(form, text="おすすめを見る", command=self.show_recommendations).pack(side="left")
        ttk.Label(form, textvariable=self.age_error_var, style="Error.TLabel").pack(side="left", padx=10)

        columns = ("category", "name", "price", "allergens", "reason")
        self.rec_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse",
                                     height=len(CATEGORIES))
        for col, text, width, anchor in (("category", "カテゴリ", 80, "center"), ("name", "品名", 160, "w"),
                                         ("price", "価格(税込)", 75, "e"), ("allergens", "アレルギー", 170, "w"),
                                         ("reason", "おすすめ理由", 200, "w")):
            self.rec_tree.heading(col, text=text)
            self.rec_tree.column(col, width=width, anchor=anchor, stretch=(col == "reason"))
        self.rec_tree.pack(fill="x", pady=6)
        self.rec_tree.bind("<Double-1>", lambda _e: self.add_selected_recommendation())

        bottom = ttk.Frame(frame)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="選んだおすすめを注文する（数量は上の欄の値）",
                   command=self.add_selected_recommendation).pack(side="left")
        ttk.Label(bottom, textvariable=self.rec_note_var, style="Hint.TLabel").pack(side="left", padx=10)

    def _build_order_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="ご注文内容（会計前）", padding=8)
        frame.grid(row=0, column=1, sticky="nsew")

        columns = ("time", "name", "price", "qty", "subtotal")
        self.order_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="extended")
        for col, text, width, anchor in (("time", "時刻", 60, "center"), ("name", "品名", 170, "w"),
                                         ("price", "単価", 70, "e"), ("qty", "数量", 45, "center"),
                                         ("subtotal", "小計", 80, "e")):
            self.order_tree.heading(col, text=text)
            self.order_tree.column(col, width=width, anchor=anchor, stretch=(col == "name"))

        bottom = ttk.Frame(frame)
        bottom.pack(side="bottom", fill="x", pady=(8, 0))
        self.order_tree.pack(fill="both", expand=True)

        ttk.Button(bottom, text="選択した注文を取り消す", command=self.cancel_selected).pack(fill="x")
        total_row = ttk.Frame(bottom)
        total_row.pack(fill="x", pady=8)
        ttk.Label(total_row, text="現在の合計", style="TotalCaption.TLabel").pack(side="left")
        ttk.Label(total_row, textvariable=self.total_var, style="Total.TLabel").pack(side="right")
        ttk.Button(bottom, text="会計する", style="Checkout.TButton", command=self.checkout).pack(fill="x", ipady=6)

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

    # ------------------------------------------------------------------ メニュー
    def show_category(self):
        category = None if self.category_var.get() == ALL_CATEGORIES else self.category_var.get()
        allergens = self.selected_allergens()
        self.menu_tree.delete(*self.menu_tree.get_children())
        for item in items_in(category, allergens):
            self.menu_tree.insert("", "end", iid=item.id,
                                  values=(item.category, item.name, yen(item.price),
                                          item.allergen_label, item.description))
        hidden = len(items_in(category)) - len(self.menu_tree.get_children())
        self.allergy_status_var.set(f"{hidden}品を除外中" if allergens else "")

    def add_selected_menu(self):
        selected = self.menu_tree.selection()
        if not selected:
            messagebox.showinfo("注文", "メニューから品を選んでください。", parent=self)
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
                                 values=(rec.item.category, rec.item.name, yen(rec.item.price),
                                         rec.item.allergen_label, rec.reason))
        self._recommendation_shown = True
        if allergens:
            self.rec_note_var.set(f"{'・'.join(allergens)} を含む品は除外しています")

    def add_selected_recommendation(self):
        selected = self.rec_tree.selection()
        if not selected:
            messagebox.showinfo("注文", "おすすめ一覧から品を選んでください。", parent=self)
            return
        self._add(selected[0])

    # ------------------------------------------------------------------ 注文・会計
    def refresh_order(self):
        self.order_tree.delete(*self.order_tree.get_children())
        for line in self.service.lines():
            self.order_tree.insert("", "end", iid=str(line.id),
                                   values=(line.ordered_at[11:16], line.name, yen(line.unit_price),
                                           line.quantity, yen(line.subtotal)))
        self.total_var.set(yen(self.service.total()))

    def cancel_selected(self):
        selected = self.order_tree.selection()
        if not selected:
            messagebox.showinfo("取消", "取り消す注文を右の一覧から選んでください。", parent=self)
            return
        names = "\n".join(f"・{self.order_tree.set(iid, 'name')} × {self.order_tree.set(iid, 'qty')}"
                          for iid in selected)
        if not messagebox.askyesno("取消の確認", f"次の注文を取り消しますか？\n\n{names}", parent=self):
            return
        for iid in selected:
            try:
                self.service.cancel(int(iid))
            except OrderError as e:
                messagebox.showwarning("取消エラー", str(e), parent=self)
        self.refresh_order()

    def checkout(self):
        lines = self.service.lines()
        if not lines:
            messagebox.showinfo("会計", "まだ注文がありません。", parent=self)
            return
        receipt = self.service.checkout()
        self.refresh_order()
        ReceiptWindow(self, receipt)

    def show_history(self):
        HistoryWindow(self, self.service.history())


class ReceiptWindow(tk.Toplevel):
    def __init__(self, parent, receipt):
        super().__init__(parent)
        self.title("お会計")
        self.resizable(False, False)
        self.transient(parent)
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=STORE_NAME, style="ReceiptStore.TLabel").pack()
        ttk.Label(frame, text=f"伝票No.{receipt.order_id}　{receipt.paid_at}").pack(pady=(2, 10))
        table = ttk.Frame(frame)
        table.pack(fill="x")
        for row, line in enumerate(receipt.lines):
            ttk.Label(table, text=line.name).grid(row=row, column=0, sticky="w")
            ttk.Label(table, text=f"{yen(line.unit_price)} × {line.quantity}").grid(row=row, column=1, sticky="e", padx=12)
            ttk.Label(table, text=yen(line.subtotal)).grid(row=row, column=2, sticky="e")
        table.columnconfigure(0, weight=1)
        ttk.Separator(frame).pack(fill="x", pady=10)
        total_row = ttk.Frame(frame)
        total_row.pack(fill="x")
        ttk.Label(total_row, text="合計（税込）", style="TotalCaption.TLabel").pack(side="left")
        ttk.Label(total_row, text=yen(receipt.total), style="Total.TLabel").pack(side="right")
        ttk.Label(frame, text="ありがとうございました。またのご来店をお待ちしております。").pack(pady=(14, 8))
        ttk.Button(frame, text="閉じる", command=self.destroy).pack()
        _center_on(self, parent.winfo_toplevel())
        self.grab_set()


class HistoryWindow(tk.Toplevel):
    def __init__(self, parent, rows):
        super().__init__(parent)
        self.title("会計履歴")
        self.geometry("460x320")
        self.transient(parent)
        tree = ttk.Treeview(self, columns=("id", "paid_at", "count", "total"), show="headings")
        for col, text, width, anchor in (("id", "伝票No.", 70, "center"), ("paid_at", "会計日時", 170, "center"),
                                         ("count", "点数", 60, "center"), ("total", "合計", 100, "e")):
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor=anchor)
        for row in rows:
            tree.insert("", "end", values=(row["id"], row["paid_at"], row["item_count"], yen(row["total"])))
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        if not rows:
            ttk.Label(self, text="まだ会計済みの伝票はありません。").pack(pady=(0, 10))
        _center_on(self, parent.winfo_toplevel())


def _center_on(window: tk.Toplevel, parent: tk.Misc):
    window.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - window.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - window.winfo_height()) // 3
    window.geometry(f"+{max(x, 0)}+{max(y, 0)}")


def _setup_style(root: tk.Tk):
    families = set(tkfont.families(root))
    family = next((f for f in ("Yu Gothic UI", "Meiryo UI", "Hiragino Sans", "Noto Sans CJK JP")
                   if f in families), None)
    if family:
        for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont"):
            tkfont.nametofont(name).configure(family=family, size=10)
    base = family or tkfont.nametofont("TkDefaultFont").actual("family")

    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    style.configure("Header.TFrame", background=ACCENT)
    style.configure("StoreName.TLabel", background=ACCENT, foreground="#ffffff", font=(base, 20, "bold"))
    style.configure("Catch.TLabel", background=ACCENT, foreground=CATCH_FG, font=(base, 11))
    style.configure("Hint.TLabel", foreground="#666666")
    style.configure("Error.TLabel", foreground="#c0392b")
    style.configure("TotalCaption.TLabel", font=(base, 12))
    style.configure("Total.TLabel", font=(base, 18, "bold"), foreground=ACCENT)
    style.configure("ReceiptStore.TLabel", font=(base, 14, "bold"))
    style.configure("Accent.TButton", font=(base, 10, "bold"))
    style.configure("Checkout.TButton", font=(base, 13, "bold"), foreground="#ffffff", background=ACCENT)
    style.map("Checkout.TButton", background=[("active", ACCENT_ACTIVE)])
    style.configure("Treeview", rowheight=24)


def run(service: OrderService):
    root = tk.Tk()
    root.title(f"{STORE_NAME} - オーダーシステム")
    root.geometry("1200x780")
    root.minsize(1000, 700)
    _setup_style(root)

    # 想定外の例外が起きてもアプリを止めず、メッセージを表示して続行する
    def on_error(exc, value, tb):
        traceback.print_exception(exc, value, tb)
        messagebox.showerror("エラー", f"予期しないエラーが発生しました。\n{value}")
    root.report_callback_exception = on_error

    OrderApp(root, service).pack(fill="both", expand=True)
    root.mainloop()

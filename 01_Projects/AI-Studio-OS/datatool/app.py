# -*- coding: utf-8 -*-
"""
数据处理助手 v0.2.0 —— 图形界面
项目：AI 个人工作室操作系统（AI Personal Studio OS）

怎么打开这个软件：
    双击本文件，或在命令行里运行：python app.py

使用顺序：
    ① 选择 CSV 文件 → 勾选清洗选项 → ② 预览清洗结果
    → 筛选 / 排序 / 画图 → ③ 统计信息 / ④ 导出结果
    （导出的是新文件，原文件绝不被修改）

v0.2.0 新增：按条件筛选行、按列排序、柱状图。
v0.1.1 界面精修：高分屏适配（文字不发虚）、现代配色、卡片式布局。
"""

import ctypes

# 高分屏适配：必须在创建窗口之前调用，否则整窗文字发虚
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import core

PREVIEW_MAX_ROWS = 50  # 预览最多显示多少行，防止大表格卡住界面

# ---------------- 配色（一套统一的高级感配色） ----------------
BG = "#eef1f7"          # 窗口底色：浅灰蓝
CARD = "#ffffff"        # 卡片底色：纯白
BORDER = "#dde3ee"      # 卡片描边
TEXT = "#1f2430"        # 正文：深灰黑
SUBTEXT = "#7a8499"     # 次要文字：灰
ACCENT = "#356ae6"      # 主色：沉静的蓝
ACCENT_HOVER = "#2456c4"
ACCENT_SOFT = "#e3ecfd"  # 主色的浅色底（选中行、次按钮用）
DANGER = "#e05935"


def _font(size=10, bold=False):
    """统一字体：微软雅黑，大小可调。"""
    return ("Microsoft YaHei UI", size, "bold" if bold else "normal")


def _style_button(btn, bg, fg, hover_bg, bold=True):
    """把按钮做成扁平精致样式，并带鼠标悬停变色。"""
    btn.configure(
        bg=bg, fg=fg,
        activebackground=hover_bg, activeforeground=fg,
        relief="flat", bd=0, cursor="hand2",
        padx=16, pady=7, font=_font(10, bold),
        disabledforeground="#aab2c5",
    )
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover_bg))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))


class DataToolApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.file_path = None      # 当前选择的 CSV 文件
        self.headers = []          # 原始表头
        self.rows = []             # 原始数据行
        self.cur_headers = []      # 当前显示的数据（清洗后就是清洗结果）
        self.cur_rows = []
        self.cleaned = False       # 当前显示的是否为清洗后的结果
        self.encoding = ""

        root.title(f"{core.APP_NAME} v{core.APP_VERSION}")
        root.geometry("980x780")
        root.minsize(900, 700)
        root.configure(bg=BG)

        self._build_ui()

    # ---------- 界面搭建 ----------

    def _build_ui(self):
        # clam 主题：唯一能自定义所有颜色的主题
        style = ttk.Style(self.root)
        style.theme_use("clam")

        # 表格样式：去边框、加行高、选中行用浅蓝
        style.configure(
            "Treeview",
            background=CARD, fieldbackground=CARD, foreground=TEXT,
            rowheight=32, font=_font(10), borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background="#f3f5fa", foreground=TEXT,
            font=_font(10, True), padding=(10, 9), relief="flat",
        )
        style.map(
            "Treeview",
            background=[("selected", ACCENT_SOFT)],
            foreground=[("selected", TEXT)],
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#e8ecf5")],
        )

        # 勾选框样式
        style.configure(
            "TCheckbutton",
            background=CARD, foreground=TEXT, font=_font(10),
        )

        # 滚动条样式
        style.configure(
            "Vertical.TScrollbar",
            background="#e6eaf3", troughcolor=BG,
            borderwidth=0, arrowcolor=SUBTEXT, relief="flat",
        )

        # ===== 顶部标题区 =====
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill=tk.X, padx=20, pady=(16, 4))
        tk.Label(header, text=core.APP_NAME, bg=BG, fg=TEXT,
                 font=_font(17, True)).pack(side=tk.LEFT)
        tk.Label(header, text=f"  v{core.APP_VERSION}", bg=BG, fg=SUBTEXT,
                 font=_font(10)).pack(side=tk.LEFT, pady=(6, 0))
        tk.Label(header, text="把杂乱的表格数据洗干净、数清楚",
                 bg=BG, fg=SUBTEXT, font=_font(10)).pack(side=tk.RIGHT, pady=(8, 0))

        # ===== 文件选择卡片 =====
        file_card = tk.Frame(self.root, bg=CARD,
                             highlightbackground=BORDER, highlightthickness=1)
        file_card.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(file_card, text="CSV 文件", bg=CARD, fg=SUBTEXT,
                 font=_font(9, True)).pack(side=tk.LEFT, padx=(14, 6), pady=10)

        self.file_var = tk.StringVar(value="（还没有选择文件）")
        file_entry = tk.Entry(
            file_card, textvariable=self.file_var,
            bg="#f6f8fc", fg=TEXT, readonlybackground="#f6f8fc",
            relief="flat", font=_font(10),
            highlightthickness=1, highlightcolor=ACCENT, highlightbackground=BORDER,
        )
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=5)

        btn_choose = tk.Button(file_card, text="① 选择 CSV 文件",
                               command=self.choose_file)
        _style_button(btn_choose, ACCENT, "#ffffff", ACCENT_HOVER)
        btn_choose.pack(side=tk.RIGHT, padx=(0, 12), pady=8)

        # ===== 数据预览区（标题 + 表格） =====
        mid = tk.Frame(self.root, bg=BG)
        mid.pack(fill=tk.BOTH, expand=True, padx=20)

        tk.Label(mid, text="数据预览", bg=BG, fg=SUBTEXT,
                 font=_font(9, True)).pack(anchor=tk.W, pady=(2, 4))

        table_card = tk.Frame(mid, bg=CARD,
                              highlightbackground=BORDER, highlightthickness=1)
        table_card.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(table_card, show="headings")
        self.tree.tag_configure("even", background="#f7f9fd")
        self.tree.tag_configure("odd", background=CARD)
        self.scroll_y = ttk.Scrollbar(table_card, orient=tk.VERTICAL,
                                      command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scroll_y.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        # ===== 清洗选项卡片 =====
        opts_card = tk.Frame(self.root, bg=CARD,
                             highlightbackground=BORDER, highlightthickness=1)
        opts_card.pack(fill=tk.X, padx=20, pady=(10, 0))

        tk.Label(opts_card, text="清洗选项", bg=CARD, fg=SUBTEXT,
                 font=_font(9, True)).pack(anchor=tk.W, padx=14, pady=(10, 2))

        row1 = tk.Frame(opts_card, bg=CARD)
        row1.pack(fill=tk.X, padx=10)
        row2 = tk.Frame(opts_card, bg=CARD)
        row2.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.var_trim = tk.BooleanVar(value=True)
        self.var_empty_rows = tk.BooleanVar(value=True)
        self.var_empty_cols = tk.BooleanVar(value=False)
        self.var_dedup = tk.BooleanVar(value=True)
        self.var_drop_missing = tk.BooleanVar(value=False)
        self.var_numeric = tk.BooleanVar(value=True)

        for parent, text, var in (
            (row1, "去首尾空格", self.var_trim),
            (row1, "删整行空白", self.var_empty_rows),
            (row1, "删整列空白", self.var_empty_cols),
            (row2, "删重复行", self.var_dedup),
            (row2, "删含空白格的行", self.var_drop_missing),
            (row2, "智能数字列", self.var_numeric),
        ):
            ttk.Checkbutton(parent, text=text, variable=var).pack(
                side=tk.LEFT, padx=6, pady=4)

        tk.Label(row2, text="空白格填成：", bg=CARD, fg=TEXT,
                 font=_font(10)).pack(side=tk.LEFT, padx=(14, 2))
        self.fill_var = tk.StringVar(value="")
        fill_entry = tk.Entry(
            row2, textvariable=self.fill_var, width=8,
            bg="#f6f8fc", fg=TEXT, relief="flat", font=_font(10),
            highlightthickness=1, highlightcolor=ACCENT, highlightbackground=BORDER,
        )
        fill_entry.pack(side=tk.LEFT, ipady=3)
        tk.Label(row2, text="（留空 = 不填）", bg=CARD, fg=SUBTEXT,
                 font=_font(9)).pack(side=tk.LEFT, padx=4)

        # ===== 筛选与排序卡片（v0.2.0 新增） =====
        fs_card = tk.Frame(self.root, bg=CARD,
                           highlightbackground=BORDER, highlightthickness=1)
        fs_card.pack(fill=tk.X, padx=20, pady=(10, 0))

        tk.Label(fs_card, text="筛选与排序", bg=CARD, fg=SUBTEXT,
                 font=_font(9, True)).pack(anchor=tk.W, padx=14, pady=(10, 2))

        frow = tk.Frame(fs_card, bg=CARD)
        frow.pack(fill=tk.X, padx=10)
        srow = tk.Frame(fs_card, bg=CARD)
        srow.pack(fill=tk.X, padx=10, pady=(0, 10))

        def _combo_style():
            return {
                "background": "#f6f8fc", "foreground": TEXT,
                "font": _font(10), "state": "readonly",
            }

        # —— 筛选一行：选列 + 选条件 + 填值 + 按钮 ——
        tk.Label(frow, text="筛选：", bg=CARD, fg=TEXT,
                 font=_font(10, True)).pack(side=tk.LEFT, padx=(4, 2))
        self.filter_col_var = tk.StringVar()
        self.filter_col = ttk.Combobox(frow, textvariable=self.filter_col_var,
                                       width=10, **_combo_style())
        self.filter_col.pack(side=tk.LEFT, padx=4)

        self.filter_op_var = tk.StringVar(value="包含")
        self.filter_op = ttk.Combobox(
            frow, textvariable=self.filter_op_var, width=9,
            values=[label for _, label in core.FILTER_OPS], **_combo_style())
        self.filter_op.pack(side=tk.LEFT, padx=4)

        self.filter_val_var = tk.StringVar()
        tk.Entry(frow, textvariable=self.filter_val_var, width=12,
                 bg="#f6f8fc", fg=TEXT, relief="flat", font=_font(10),
                 highlightthickness=1, highlightcolor=ACCENT,
                 highlightbackground=BORDER).pack(side=tk.LEFT, padx=4, ipady=3)

        btn_filter = tk.Button(frow, text="⑤ 筛选", command=self.apply_filter)
        _style_button(btn_filter, ACCENT, "#ffffff", ACCENT_HOVER)
        btn_filter.pack(side=tk.LEFT, padx=(8, 4))
        btn_unfilter = tk.Button(frow, text="清除筛选/排序",
                                 command=self.clear_filter)
        _style_button(btn_unfilter, "#e2e6ef", SUBTEXT, "#d2d8e5", bold=False)
        btn_unfilter.pack(side=tk.LEFT, padx=4)

        # —— 排序一行：选列 + 升序/降序 ——
        tk.Label(srow, text="排序：", bg=CARD, fg=TEXT,
                 font=_font(10, True)).pack(side=tk.LEFT, padx=(4, 2))
        self.sort_col_var = tk.StringVar()
        self.sort_col = ttk.Combobox(srow, textvariable=self.sort_col_var,
                                     width=10, **_combo_style())
        self.sort_col.pack(side=tk.LEFT, padx=4)

        btn_up = tk.Button(srow, text="升序 ↑", command=lambda: self.apply_sort(False))
        _style_button(btn_up, ACCENT_SOFT, ACCENT, "#d3e0fa")
        btn_up.pack(side=tk.LEFT, padx=(8, 4))
        btn_down = tk.Button(srow, text="降序 ↓", command=lambda: self.apply_sort(True))
        _style_button(btn_down, ACCENT_SOFT, ACCENT, "#d3e0fa")
        btn_down.pack(side=tk.LEFT, padx=4)

        tk.Label(srow, text="提示：数字列自动按大小排，文字列按拼音顺序排",
                 bg=CARD, fg=SUBTEXT, font=_font(9)).pack(side=tk.LEFT, padx=10)

        # ===== 底部操作按钮 =====
        bottom = tk.Frame(self.root, bg=BG)
        bottom.pack(fill=tk.X, padx=20, pady=12)

        btn_preview = tk.Button(bottom, text="② 预览清洗结果",
                                command=self.preview_clean)
        _style_button(btn_preview, ACCENT, "#ffffff", ACCENT_HOVER)
        btn_preview.pack(side=tk.LEFT, padx=(0, 8))

        btn_stats = tk.Button(bottom, text="③ 统计信息", command=self.show_stats)
        _style_button(btn_stats, ACCENT_SOFT, ACCENT, "#d3e0fa")
        btn_stats.pack(side=tk.LEFT, padx=(0, 8))

        btn_chart = tk.Button(bottom, text="⑤ 画柱状图", command=self.show_chart)
        _style_button(btn_chart, ACCENT_SOFT, ACCENT, "#d3e0fa")
        btn_chart.pack(side=tk.LEFT, padx=(0, 8))

        btn_export = tk.Button(bottom, text="④ 导出结果", command=self.export_result)
        _style_button(btn_export, ACCENT, "#ffffff", ACCENT_HOVER)
        btn_export.pack(side=tk.LEFT, padx=(0, 8))

        btn_raw = tk.Button(bottom, text="恢复原始预览", command=self.show_raw)
        _style_button(btn_raw, "#e2e6ef", SUBTEXT, "#d2d8e5", bold=False)
        btn_raw.pack(side=tk.LEFT)

        # ===== 状态栏 =====
        self.status_var = tk.StringVar(value="请先选择一个 CSV 文件")
        status = tk.Label(self.root, textvariable=self.status_var,
                          bg="#e5e9f2", fg=SUBTEXT, anchor=tk.W,
                          font=_font(9), padx=14, pady=7)
        status.pack(fill=tk.X, side=tk.BOTTOM)

    # ---------- 数据展示 ----------

    def _sync_column_combos(self):
        """让筛选/排序/图表的"选列"下拉框跟上当前数据的列。"""
        values = list(self.cur_headers)
        for combo, var in ((self.filter_col, self.filter_col_var),
                           (self.sort_col, self.sort_col_var)):
            combo.configure(values=values)
            if var.get() not in values:
                var.set(values[0] if values else "")

    def _find_col(self, name: str) -> int:
        """按列名找出列的位置（找不到就报错提示）。"""
        try:
            return list(self.cur_headers).index(name)
        except ValueError:
            raise ValueError(f"找不到列「{name}」，请先选择文件")

    def _refresh_preview(self):
        """把当前数据填进表格（只显示前若干行，列数多的表也能扛住）。"""
        self.tree.delete(*self.tree.get_children())
        self._sync_column_combos()
        if not self.cur_headers:
            return
        cols = [f"c{i}" for i in range(len(self.cur_headers))]
        self.tree.configure(columns=cols)
        width = max(90, min(240, 820 // max(1, len(cols))))
        for i, h in enumerate(self.cur_headers):
            self.tree.heading(f"c{i}", text=h or f"第{i + 1}列")
            self.tree.column(f"c{i}", width=width, anchor=tk.W)
        for idx, r in enumerate(self.cur_rows[:PREVIEW_MAX_ROWS]):
            self.tree.insert("", tk.END, values=r,
                             tags=("even",) if idx % 2 == 0 else ("odd",))
        note = "清洗后" if self.cleaned else "原始数据"
        shown = min(len(self.cur_rows), PREVIEW_MAX_ROWS)
        more = f"，仅预览前 {PREVIEW_MAX_ROWS} 行" if len(self.cur_rows) > PREVIEW_MAX_ROWS else ""
        self.status_var.set(
            f"{note}：共 {len(self.cur_rows)} 行 × {len(self.cur_headers)} 列"
            f"，已显示 {shown} 行{more}｜编码 {self.encoding}")

    def _get_options(self):
        """把界面上的勾选项翻译成核心模块看得懂的选项。"""
        return {
            "trim": self.var_trim.get(),
            "remove_empty_rows": self.var_empty_rows.get(),
            "remove_empty_cols": self.var_empty_cols.get(),
            "remove_duplicates": self.var_dedup.get(),
            "drop_missing": self.var_drop_missing.get(),
            "fill_missing": self.fill_var.get().strip(),
            "smart_numeric": self.var_numeric.get(),
        }

    # ---------- 按钮动作 ----------

    def choose_file(self):
        path = filedialog.askopenfilename(
            title="选择 CSV 文件",
            filetypes=[("CSV 表格", "*.csv"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            self.headers, self.rows, self.encoding = core.read_table(path)
        except Exception as e:
            messagebox.showerror("读取失败", str(e))
            return
        self.file_path = path
        self.file_var.set(path)
        self.show_raw()

    def show_raw(self):
        if not self.file_path:
            return
        self.cur_headers, self.cur_rows = self.headers, self.rows
        self.cleaned = False
        self._refresh_preview()

    def preview_clean(self):
        if not self._need_file():
            return
        before = len(self.rows)
        self.cur_headers, self.cur_rows = core.clean_table(
            self.headers, self.rows, self._get_options())
        self.cleaned = True
        self._refresh_preview()
        self.status_var.set(
            self.status_var.get()
            + f"｜清洗：{before} 行 → {len(self.cur_rows)} 行")

    def apply_filter(self):
        """按选好的列和条件筛出匹配的行。"""
        if not self._need_file() or not self.cur_headers:
            return
        col_name = self.filter_col_var.get()
        op_label = self.filter_op_var.get()
        value = self.filter_val_var.get()
        ops = {label: code for code, label in core.FILTER_OPS}
        if op_label not in ops:
            messagebox.showwarning("条件不对", "请在下拉框里选一个筛选条件")
            return
        op = ops[op_label]
        if op not in ("empty", "not_empty") and value.strip() == "":
            messagebox.showwarning("还缺一个值",
                                   "这个条件需要填一个要比较的内容")
            return
        try:
            idx = self._find_col(col_name)
            before = len(self.cur_rows)
            self.cur_headers, self.cur_rows = core.filter_rows(
                self.cur_headers, self.cur_rows, idx, op, value)
        except Exception as e:
            messagebox.showerror("筛选失败", str(e))
            return
        self._refresh_preview()
        self.status_var.set(
            self.status_var.get()
            + f"｜筛选「{col_name} {op_label} {value.strip()}」："
              f"{before} 行 → {len(self.cur_rows)} 行")

    def clear_filter(self):
        """撤掉筛选和排序：回到原始数据（若已清洗则回到清洗结果）。"""
        if not self._need_file():
            return
        if self.cleaned:
            self.cur_headers, self.cur_rows = core.clean_table(
                self.headers, self.rows, self._get_options())
        else:
            self.cur_headers, self.cur_rows = self.headers, self.rows
        self._refresh_preview()

    def apply_sort(self, reverse: bool):
        """按选好的列排序。"""
        if not self._need_file() or not self.cur_headers:
            return
        col_name = self.sort_col_var.get()
        try:
            idx = self._find_col(col_name)
            numeric = all(core._is_number(
                (r[idx] if idx < len(r) else "").strip())
                for r in self.cur_rows
                if (r[idx] if idx < len(r) else "").strip())
            self.cur_headers, self.cur_rows = core.sort_rows(
                self.cur_headers, self.cur_rows, idx,
                numeric=numeric, reverse=reverse)
        except Exception as e:
            messagebox.showerror("排序失败", str(e))
            return
        self._refresh_preview()
        way = "降序" if reverse else "升序"
        self.status_var.set(self.status_var.get()
                            + f"｜已按「{col_name}」{way}排列")

    def show_chart(self):
        """按"筛选"那行选的列，画一张柱状图（弹新窗口）。"""
        if not self._need_file() or not self.cur_headers:
            return
        col_name = self.filter_col_var.get()
        try:
            idx = self._find_col(col_name)
            series = core.chart_series(self.cur_headers, self.cur_rows, idx)
        except Exception as e:
            messagebox.showerror("画图失败", str(e))
            return
        self._open_chart_window(series)

    def _open_chart_window(self, series: dict):
        """画柱状图：底边、柱子、次数标签、柱名标签，全部手绘。"""
        win = tk.Toplevel(self.root)
        win.title(series["title"])
        win.configure(bg=CARD)
        win.geometry("760x480")
        win.minsize(640, 420)

        tk.Label(win, text=series["title"], bg=CARD, fg=TEXT,
                 font=_font(13, True)).pack(pady=(16, 4))
        items = series["items"]
        if not items:
            tk.Label(win, text="这一列暂时没有可画的数据", bg=CARD, fg=SUBTEXT,
                     font=_font(11)).pack(pady=30)
            return

        canvas = tk.Canvas(win, bg=CARD, highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=(4, 16))

        def draw(_event=None):
            canvas.delete("all")
            w = max(canvas.winfo_width(), 640)
            h = max(canvas.winfo_height(), 360)
            left, right, top, bottom = 60, w - 30, 20, h - 60
            max_n = max(n for _, n in items) if items else 1

            # 底边和左边（坐标轴）
            canvas.create_line(left, top, left, bottom, fill=BORDER, width=2)
            canvas.create_line(left, bottom, right, bottom, fill=BORDER, width=2)

            n = len(items)
            slot = (right - left) / n
            bar_w = min(slot * 0.55, 90)
            for i, (label, count) in enumerate(items):
                cx = left + slot * (i + 0.5)
                x1, x2 = cx - bar_w / 2, cx + bar_w / 2
                y1 = bottom - (bottom - top) * (count / max_n)
                color = ACCENT if i % 2 == 0 else "#6f9bf0"  # 深浅蓝交替，更耐看
                canvas.create_rectangle(x1, y1, x2, bottom,
                                        fill=color, outline="")
                canvas.create_text(cx, y1 - 12, text=str(count),
                                   fill=TEXT, font=_font(10, True))
                # 柱名太长就截断，免得挤成一团
                shown = label if len(label) <= 8 else label[:7] + "…"
                canvas.create_text(cx, bottom + 16, text=shown,
                                   fill=SUBTEXT, font=_font(9))

        canvas.bind("<Configure>", draw)  # 窗口大小一变就重画，图始终端正
        win.update_idletasks()
        draw()

    def show_stats(self):
        if not self._need_file():
            return
        data_headers = self.cur_headers if self.cleaned else self.headers
        data_rows = self.cur_rows if self.cleaned else self.rows
        scope = "当前显示（清洗后）" if self.cleaned else "原始数据"
        text = core.summary_text(core.summary(data_headers, data_rows))
        messagebox.showinfo(f"统计信息（{scope}）", text or "没有数据")

    def export_result(self):
        if not self._need_file():
            return
        if not self.cleaned:
            if not messagebox.askyesno(
                    "确认导出",
                    "还没有预览清洗结果，将按当前勾选的选项直接清洗并导出。\n"
                    "原始文件不会被修改，导出的新文件和原文件放在一起。\n\n"
                    "继续吗？"):
                return
            self.cur_headers, self.cur_rows = core.clean_table(
                self.headers, self.rows, self._get_options())
            self.cleaned = True
            self._refresh_preview()
        default_path = core.default_output_path(self.file_path)
        out = filedialog.asksaveasfilename(
            title="导出清洗结果",
            initialdir=os.path.dirname(self.file_path),
            initialfile=os.path.basename(default_path),
            defaultextension=".csv",
            filetypes=[("CSV 表格", "*.csv")])
        if not out:
            return
        try:
            core.write_table(out, self.cur_headers, self.cur_rows)
        except Exception as e:
            messagebox.showerror("导出失败", str(e))
            return
        messagebox.showinfo("导出成功",
                            f"已导出：{out}\n\n原始文件没有被修改。")

    def _need_file(self):
        if not self.file_path:
            messagebox.showwarning("还没有选择文件", "请先点「① 选择 CSV 文件」")
            return False
        return True


def main():
    root = tk.Tk()
    DataToolApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

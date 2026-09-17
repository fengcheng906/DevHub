# -*- coding: utf-8 -*-
"""
数据处理助手 v0.1 —— 图形界面
项目：AI 个人工作室操作系统（AI Personal Studio OS）

怎么打开这个软件：
    双击本文件，或在命令行里运行：python app.py

使用顺序：
    ① 选择 CSV 文件 → 勾选清洗选项 → ② 预览清洗结果
    → ③ 统计信息 / ④ 导出结果（导出的是新文件，原文件绝不被修改）
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import core

PREVIEW_MAX_ROWS = 50  # 预览最多显示多少行，防止大表格卡住界面


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
        root.geometry("900x620")
        root.minsize(780, 520)

        self._build_ui()

    # ---------- 界面搭建 ----------

    def _build_ui(self):
        # 顶部：文件选择
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="CSV 文件：").pack(side=tk.LEFT)
        self.file_var = tk.StringVar(value="（还没有选择文件）")
        ttk.Entry(top, textvariable=self.file_var, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(top, text="① 选择 CSV 文件", command=self.choose_file).pack(side=tk.LEFT)

        # 中部：数据预览表格
        mid = ttk.Frame(self.root, padding=(10, 0))
        mid.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(mid, show="headings")
        self.scroll_y = ttk.Scrollbar(mid, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scroll_y.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        # 选项区：清洗方式勾选
        opts = ttk.LabelFrame(self.root, text="清洗选项", padding=8)
        opts.pack(fill=tk.X, padx=10, pady=(8, 0))

        self.var_trim = tk.BooleanVar(value=True)
        self.var_empty_rows = tk.BooleanVar(value=True)
        self.var_empty_cols = tk.BooleanVar(value=False)
        self.var_dedup = tk.BooleanVar(value=True)
        self.var_drop_missing = tk.BooleanVar(value=False)
        self.var_numeric = tk.BooleanVar(value=True)

        ttk.Checkbutton(opts, text="去首尾空格", variable=self.var_trim).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(opts, text="删整行空白", variable=self.var_empty_rows).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(opts, text="删整列空白", variable=self.var_empty_cols).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(opts, text="删重复行", variable=self.var_dedup).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(opts, text="删含空白格的行", variable=self.var_drop_missing).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(opts, text="智能数字列", variable=self.var_numeric).pack(side=tk.LEFT, padx=4)

        ttk.Label(opts, text="空白格填成：").pack(side=tk.LEFT, padx=(10, 2))
        self.fill_var = tk.StringVar(value="")
        ttk.Entry(opts, textvariable=self.fill_var, width=8).pack(side=tk.LEFT)
        ttk.Label(opts, text="（留空 = 不填）").pack(side=tk.LEFT, padx=2)

        # 底部：操作按钮 + 状态栏
        bottom = ttk.Frame(self.root, padding=10)
        bottom.pack(fill=tk.X)

        ttk.Button(bottom, text="② 预览清洗结果", command=self.preview_clean).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="③ 统计信息", command=self.show_stats).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="④ 导出结果", command=self.export_result).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="恢复原始预览", command=self.show_raw).pack(side=tk.LEFT, padx=4)

        self.status_var = tk.StringVar(value="请先选择一个 CSV 文件")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN,
                  anchor=tk.W, padding=(10, 4)).pack(fill=tk.X, side=tk.BOTTOM)

    # ---------- 数据展示 ----------

    def _refresh_preview(self):
        """把当前数据填进表格（只显示前若干行，列数多的表也能扛住）。"""
        self.tree.delete(*self.tree.get_children())
        if not self.cur_headers:
            return
        cols = [f"c{i}" for i in range(len(self.cur_headers))]
        self.tree.configure(columns=cols)
        width = max(80, min(220, 760 // max(1, len(cols))))
        for i, h in enumerate(self.cur_headers):
            self.tree.heading(f"c{i}", text=h or f"第{i + 1}列")
            self.tree.column(f"c{i}", width=width, anchor=tk.W)
        for r in self.cur_rows[:PREVIEW_MAX_ROWS]:
            self.tree.insert("", tk.END, values=r)
        tag = "cleaned" if self.cleaned else "raw"
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

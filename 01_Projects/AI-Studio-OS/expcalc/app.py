# -*- coding: utf-8 -*-
"""
实验数据小算手 v0.1.0 —— 图形界面
项目：AI 个人工作室操作系统（AI Personal Studio OS）

怎么打开这个软件：
    双击本文件，或在命令行里运行：python app.py

使用顺序：
    ① 把测到的数填进去（逗号或空格隔开都行）
    → ② 算一算 → ③ 需要的话导出结果存成文本文件

按钮上的括号注：为了不换软件名、又让按钮一眼看懂，按用户拍板
在按钮名后加了一句大白话说明（v0.1.0 起实行）。
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
from tkinter import filedialog, messagebox

import core

# ---------------- 配色（和数据处理助手同一套高级感配色） ----------------
BG = "#eef1f7"          # 窗口底色：浅灰蓝
CARD = "#ffffff"        # 卡片底色：纯白
BORDER = "#dde3ee"      # 卡片描边
TEXT = "#1f2430"        # 正文：深灰黑
SUBTEXT = "#7a8499"     # 次要文字：灰
ACCENT = "#356ae6"      # 主色：沉静的蓝
ACCENT_HOVER = "#2456c4"
ACCENT_SOFT = "#e3ecfd"  # 主色的浅色底（次按钮用）
RESULT_BG = "#f6f8fc"   # 结果框底色


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


class ExpCalcApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.last_result = None  # 最近一次算出来的结果（导出用）

        root.title(f"{core.APP_NAME} v{core.APP_VERSION}")
        root.geometry("640x640")
        root.minsize(560, 560)
        root.configure(bg=BG)

        self._build_ui()

    # ---------- 界面搭建 ----------

    def _build_ui(self):
        # ===== 顶部标题区 =====
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill=tk.X, padx=20, pady=(16, 4))
        tk.Label(header, text=core.APP_NAME, bg=BG, fg=TEXT,
                 font=_font(17, True)).pack(side=tk.LEFT)
        tk.Label(header, text=f"  v{core.APP_VERSION}", bg=BG, fg=SUBTEXT,
                 font=_font(10)).pack(side=tk.LEFT, pady=(6, 0))
        tk.Label(header, text="实验课的数，一键算平均、波动多大",
                 bg=BG, fg=SUBTEXT, font=_font(10)).pack(side=tk.RIGHT, pady=(8, 0))

        # ===== 输入卡片 =====
        in_card = tk.Frame(self.root, bg=CARD,
                           highlightbackground=BORDER, highlightthickness=1)
        in_card.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(in_card, text="① 测到的数（逗号或空格隔开）", bg=CARD,
                 fg=SUBTEXT, font=_font(9, True)).pack(
            anchor=tk.W, padx=14, pady=(10, 2))

        self.input_text = tk.Text(
            in_card, height=5, bg=RESULT_BG, fg=TEXT,
            relief="flat", font=_font(11), wrap=tk.WORD,
            highlightthickness=1, highlightcolor=ACCENT,
            highlightbackground=BORDER, padx=10, pady=8,
        )
        self.input_text.pack(fill=tk.X, padx=14, pady=(0, 10))
        self.input_text.insert("1.0", core.SAMPLE_DATA)

        # ===== 按钮行 =====
        btns = tk.Frame(self.root, bg=BG)
        btns.pack(fill=tk.X, padx=20)

        btn_calc = tk.Button(btns, text="② 算一算（出全部结果）",
                             command=self.do_calc)
        _style_button(btn_calc, ACCENT, "#ffffff", ACCENT_HOVER)
        btn_calc.pack(side=tk.LEFT, padx=(0, 8))

        btn_export = tk.Button(btns, text="③ 导出结果（存成文本文件）",
                               command=self.do_export)
        _style_button(btn_export, ACCENT_SOFT, ACCENT, "#d3e0fa")
        btn_export.pack(side=tk.LEFT, padx=(0, 8))

        btn_sample = tk.Button(btns, text="填示例数（放一个例子）",
                               command=self.fill_sample)
        _style_button(btn_sample, "#e2e6ef", SUBTEXT, "#d2d8e5", bold=False)
        btn_sample.pack(side=tk.LEFT, padx=(0, 8))

        btn_clear = tk.Button(btns, text="清空（删掉重新填）",
                              command=self.do_clear)
        _style_button(btn_clear, "#e2e6ef", SUBTEXT, "#d2d8e5", bold=False)
        btn_clear.pack(side=tk.LEFT)

        # ===== 结果卡片 =====
        out_card = tk.Frame(self.root, bg=CARD,
                            highlightbackground=BORDER, highlightthickness=1)
        out_card.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 4))

        tk.Label(out_card, text="结果", bg=CARD, fg=SUBTEXT,
                 font=_font(9, True)).pack(anchor=tk.W, padx=14, pady=(10, 2))

        self.result_var = tk.StringVar(value="点上面的「算一算」，结果出现在这里。")
        result_label = tk.Label(
            out_card, textvariable=self.result_var,
            bg=RESULT_BG, fg=TEXT, anchor=tk.NW, justify=tk.LEFT,
            font=_font(11), padx=14, pady=12, wraplength=540,
        )
        result_label.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 14))

        # ===== 底部提醒 + 状态栏 =====
        tk.Label(self.root,
                 text="提醒：只在你电脑上算，不联网不上传；写进作业前自己再核对一遍数。",
                 bg=BG, fg=SUBTEXT, font=_font(9)).pack(padx=20, pady=(2, 6))

        self.status_var = tk.StringVar(value="已经放好示例数，直接点「算一算」试试")
        status = tk.Label(self.root, textvariable=self.status_var,
                          bg="#e5e9f2", fg=SUBTEXT, anchor=tk.W,
                          font=_font(9), padx=14, pady=7)
        status.pack(fill=tk.X, side=tk.BOTTOM)

    # ---------- 按钮动作 ----------

    def do_calc(self):
        """读输入框 → 算 → 显示结果。"""
        nums = core.parse_numbers(self.input_text.get("1.0", tk.END))
        res = core.analyze(nums)
        if res is None:
            self.last_result = None
            self.result_var.set("没读到数字。\n检查一下：数之间要用逗号、空格或换行隔开。")
            self.status_var.set("没算成：输入里没有数字")
            return
        self.last_result = res
        self.result_var.set("\n\n".join(core.result_lines(res)))
        self.status_var.set(
            f"算好了：{res['n']} 个数，平均 {round(res['avg'], 3)}")

    def do_export(self):
        """把最近一次结果存成文本文件。"""
        if self.last_result is None:
            messagebox.showwarning("还没有结果", "请先点「② 算一算」算出结果")
            return
        out = filedialog.asksaveasfilename(
            title="导出结果",
            initialdir=os.path.dirname(core.default_report_path()),
            initialfile="实验数据结果.txt",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt")])
        if not out:
            return
        try:
            core.write_report(out, self.last_result)
        except Exception as e:
            messagebox.showerror("导出失败", str(e))
            return
        messagebox.showinfo("导出成功", f"已保存到：{out}")

    def fill_sample(self):
        """填入示例数，方便第一次用的人照着填。"""
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", core.SAMPLE_DATA)
        self.status_var.set("已填入示例数，直接点「算一算」")

    def do_clear(self):
        """清空输入框和结果。"""
        self.input_text.delete("1.0", tk.END)
        self.last_result = None
        self.result_var.set("点上面的「算一算」，结果出现在这里。")
        self.status_var.set("已清空，重新填数吧")


def main():
    root = tk.Tk()
    ExpCalcApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

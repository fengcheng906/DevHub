# -*- coding: utf-8 -*-
"""智能文件工作台 GUI 冒烟测试：不弹任何窗口，自动点一遍主要功能。"""

import shutil
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import tkinter as tk
from tkinter import messagebox

import core
import app

# 防止测试过程真的弹出对话框挡住
messagebox.showinfo = lambda *a, **k: None
messagebox.showwarning = lambda *a, **k: None
messagebox.showerror = lambda *a, **k: None
messagebox.askyesno = lambda *a, **k: True

failures = []


def check(name, cond, detail=""):
    print(("  [通过] " if cond else "  [失败] ") + name + ("  " + detail if not cond else ""))
    if not cond:
        failures.append(name)


# 造一个测试文件夹
tmp = Path(tempfile.mkdtemp())
(tmp / "照片A.jpg").write_text("x", encoding="utf-8")
(tmp / "笔记.txt").write_text("x", encoding="utf-8")
(tmp / "电影.mp4").write_text("x", encoding="utf-8")
(tmp / "奇怪文件.xyz").write_text("x", encoding="utf-8")

root = tk.Tk() if not app.HAS_DND else app.TkinterDnD.Tk()
root.withdraw()
win = app.WorkbenchApp(root)

# 1. 初始状态：扫描/执行/撤销按钮应为禁用
check("初始：扫描按钮禁用", str(win.btn_scan["state"]) == "disabled")
check("初始：执行按钮禁用", str(win.btn_run["state"]) == "disabled")
check("初始：撤销按钮禁用", str(win.btn_undo["state"]) == "disabled")

# 2. 选文件夹后扫描按钮激活
win._set_folder(str(tmp))
check("选文件夹：路径已显示", win.folder_var.get() == str(tmp))
check("选文件夹：扫描按钮激活", str(win.btn_scan["state"]) == "normal")

# 3. 扫描预览：4 个文件进表格（3 个有规则 + 1 个跳过）
win.do_scan()
check("扫描：4 行进表格", len(win.tree.get_children()) == 4,
      f"实际={len(win.tree.get_children())}")
check("扫描：3 个将移动 → 执行按钮激活", str(win.btn_run["state"]) == "normal")
check("扫描：状态栏有统计", "将移动 3" in win.status_var.get())

# 4. 危险文件夹被安全拦截（桌面不可整理）
before = win.folder_var.get()
win._set_folder(str(Path.home() / "Desktop"))
check("安全拦截：桌面被拒绝", win.folder_var.get() == before)

# 5. 按日期模式也能扫描
win._set_folder(str(tmp))
win.mode_var.set("date")
win.do_scan()
check("日期模式：扫描不报错", len(win.tree.get_children()) == 4)

root.destroy()
shutil.rmtree(tmp, ignore_errors=True)

print()
if failures:
    print(f"GUI 冒烟失败 {len(failures)} 项")
    sys.exit(1)
print("GUI 冒烟全部通过")

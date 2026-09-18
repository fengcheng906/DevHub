# -*- coding: utf-8 -*-
"""数据处理助手 GUI 冒烟测试：不弹任何窗口，自动点一遍主要功能。"""

import csv
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


# 造一个测试 CSV
tmp = Path(tempfile.mkdtemp())
p = tmp / "测试.csv"
with open(p, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["姓名", "成绩", "备注"])
    w.writerow([" 张三 ", " 90 ", ""])
    w.writerow(["", "", ""])
    w.writerow(["李四", "88", "正常"])
    w.writerow(["李四", "88", "正常"])

root = tk.Tk()
root.withdraw()
win = app.DataToolApp(root)

# 1. 选择文件（直接调用读取逻辑，绕过文件对话框）
win.headers, win.rows, win.encoding = core.read_table(str(p))
win.file_path = str(p)
win.show_raw()
check("界面：原始数据载入", len(win.cur_rows) == 4, f"实际={len(win.cur_rows)}")
check("界面：状态栏显示编码", "utf-8-sig" in win.status_var.get())

# 2. 预览清洗
win.preview_clean()
check("界面：清洗后空行被删", len(win.cur_rows) == 2, f"实际={len(win.cur_rows)}")
check("界面：清洗后标记正确", win.cleaned is True)
items = win.tree.get_children()
check("界面：表格里能看到数据行", len(items) == 2, f"实际={len(items)}")

# 3. 导出（不弹保存框，直接写核心函数验证链路）
out = core.default_output_path(str(p))
core.write_table(out, win.cur_headers, win.cur_rows)
check("界面：导出文件已生成", Path(out).is_file())
h2, r2, _ = core.read_table(out)
check("界面：导出内容可读回", r2[0][0] == "张三", f"实际={r2}")

# 4. 统计不炸
stats = core.summary(win.cur_headers, win.cur_rows)
check("界面：统计功能可运行", len(stats) == 3)

# 5. 筛选：列下拉框已同步，直接选条件执行
check("界面：筛选列下拉框已同步", "姓名" in win.filter_col.cget("values"))
win.filter_col_var.set("姓名")
win.filter_op_var.set("包含")
win.filter_val_var.set("李")
win.apply_filter()
check("界面：筛选「姓名包含李」剩 1 行", len(win.cur_rows) == 1,
      f"实际={len(win.cur_rows)}")

# 6. 排序：数字列降序（当前只有一行数据，先恢复再测）
win.clear_filter()
win.sort_col_var.set("成绩")
win.apply_sort(reverse=True)
check("界面：按成绩降序后第一是 90", win.cur_rows[0][1] == "90",
      f"实际={win.cur_rows[0]}")

# 7. 清除筛选/排序后行数复原
win.clear_filter()
check("界面：清除后回到清洗结果 2 行", len(win.cur_rows) == 2,
      f"实际={len(win.cur_rows)}")

# 8. 图表数据 + 图表窗口能创建（不开新窗口画，只验数据）
series = core.chart_series(win.cur_headers, win.cur_rows, 1)
check("界面：图表数据非空", len(series["items"]) >= 1)
win._open_chart_window(series)
check("界面：图表窗口可创建", True)

# 9. 没选文件时筛选会被拦下
win.file_path = None
before_rows = len(win.cur_rows)
win.apply_filter()
check("界面：未选文件时筛选被拦截", len(win.cur_rows) == before_rows)

root.destroy()
import shutil
shutil.rmtree(tmp, ignore_errors=True)

print()
if failures:
    print(f"GUI 冒烟失败 {len(failures)} 项")
    sys.exit(1)
print("GUI 冒烟全部通过")

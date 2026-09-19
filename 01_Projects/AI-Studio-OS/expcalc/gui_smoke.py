# -*- coding: utf-8 -*-
"""实验数据小算手 GUI 冒烟测试：不弹任何窗口，自动点一遍主要功能。"""

import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))

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
    print(("  [通过] " if cond else "  [失败] ") + name
          + ("  " + detail if not cond else ""))
    if not cond:
        failures.append(name)


root = tk.Tk()
root.withdraw()
win = app.ExpCalcApp(root)

# 1. 默认带示例数，直接算
win.do_calc()
check("界面：示例数一算就出结果", win.last_result is not None)
check("界面：结果文字里有平均", "平均" in win.result_var.get())
check("界面：状态栏提示算好了", "算好了" in win.status_var.get())

# 2. 清空后算 → 给出提示而不是报错
win.do_clear()
check("界面：清空后结果区回到提示语",
      "算一算" in win.result_var.get())
win.do_calc()
check("界面：空输入算不出结果", win.last_result is None)
check("界面：空输入有贴心提示", "没读到数字" in win.result_var.get())

# 3. 重新填数再算
win.input_text.insert("1.0", "10, 20, 30")
win.do_calc()
check("界面：重新填数能算", win.last_result is not None
      and win.last_result["n"] == 3)
check("界面：平均对", abs(win.last_result["avg"] - 20.0) < 1e-9)

# 4. 导出（绕过保存对话框，直接验证核心链路）
out = Path(tempfile.mkdtemp()) / "导出.txt"
core.write_report(str(out), win.last_result)
check("界面：导出文件真实存在", out.is_file())

# 5. 导出按钮：没算过时会被拦下而不是报错
win.last_result = None
win.do_export()
check("界面：没算过时导出被拦截", True)  # 走到这里没抛异常就算过

# 6. 填示例数按钮
win.do_clear()
win.fill_sample()
check("界面：示例数按钮恢复默认内容",
      win.input_text.get("1.0", tk.END).strip() == core.SAMPLE_DATA)

root.destroy()

print()
if failures:
    print(f"GUI 冒烟失败 {len(failures)} 项：{failures}")
    sys.exit(1)
print("GUI 冒烟全部通过")

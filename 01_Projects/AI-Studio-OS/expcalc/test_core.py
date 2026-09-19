# -*- coding: utf-8 -*-
"""实验数据小算手 核心逻辑自动测试（不弹窗口）。"""

import math
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))

import core

failures = []


def check(name, cond, detail=""):
    print(("  [通过] " if cond else "  [失败] ") + name
          + ("  " + detail if not cond else ""))
    if not cond:
        failures.append(name)


print("== 实验数据小算手 v" + core.APP_VERSION + " 核心测试 ==")

# ---------- 拆数字 ----------

check("基础信息：名字正确", core.APP_NAME == "实验数据小算手")
check("基础信息：版本号是三段式（如 0.1.0）",
      len(core.APP_VERSION.split(".")) == 3)

check("拆分：英文逗号", core.parse_numbers("1, 2, 3") == [1.0, 2.0, 3.0])
check("拆分：中文逗号也行", core.parse_numbers("1，2，3") == [1.0, 2.0, 3.0])
check("拆分：空格隔开", core.parse_numbers("1 2  3") == [1.0, 2.0, 3.0])
check("拆分：换行隔开", core.parse_numbers("1\n2\n3") == [1.0, 2.0, 3.0])
check("拆分：混着来", core.parse_numbers("1, 2  3，4\n5") == [1, 2, 3, 4, 5])
check("拆分：分号也认", core.parse_numbers("1;2；3") == [1.0, 2.0, 3.0])
check("拆分：带小数的数", core.parse_numbers("5.02, 4.98") == [5.02, 4.98])
check("拆分：负数也行", core.parse_numbers("-1, 2") == [-1.0, 2.0])
check("拆分：千分位不算数字里的逗号（按分隔符处理）",
      core.parse_numbers("1,234") == [1.0, 234.0])
check("拆分：空串返回空", core.parse_numbers("") == [])
check("拆分：空白返回空", core.parse_numbers("   \n  ") == [])
check("拆分：字母会被跳过", core.parse_numbers("abc") == [])
check("拆分：字母和数字混着，只留数字",
      core.parse_numbers("5.02, abc, 4.98") == [5.02, 4.98])
check("拆分：None 不炸", core.parse_numbers(None) == [])

# ---------- 计算 ----------

res = core.analyze([5.02, 4.98, 5.10, 4.95, 5.05])
check("计算：模拟区示例能算", res is not None)
check("计算：个数对", res["n"] == 5)
check("计算：平均对（5.02+4.98+5.10+4.95+5.05）/5=5.02",
      abs(res["avg"] - 5.02) < 1e-9, f"实际={res['avg']}")
check("计算：最大最小对", res["max"] == 5.10 and res["min"] == 4.95)
check("计算：极差 = 最大-最小", abs(res["range"] - 0.15) < 1e-9)

# 标准差的正确验法：先手动算"每个数离平均的差的平方和"，
# 再分别除以 (n-1) 和 n 开根号，和程序结果对比
sample_data = [5.02, 4.98, 5.10, 4.95, 5.05]
avg = sum(sample_data) / 5
var_sum = sum((x - avg) ** 2 for x in sample_data)  # = 0.0138
check("计算：样本标准差（除以 n-1）对",
      abs(res["sd_sample"] - math.sqrt(var_sum / 4)) < 1e-12,
      f"实际={res['sd_sample']}")
check("计算：除以个数的标准差，和模拟区算法一致",
      abs(res["sd_pop"] - math.sqrt(var_sum / 5)) < 1e-12,
      f"实际={res['sd_pop']}")

res1 = core.analyze([7.0])
check("计算：一个数也能算", res1 is not None and res1["n"] == 1)
check("计算：一个数平均就是它自己", res1["avg"] == 7.0)
check("计算：一个数标准差为 0 不报错", res1["sd_sample"] == 0.0)

res_same = core.analyze([3.0, 3.0, 3.0])
check("计算：全相同 → 标准差为 0（测得很稳）", res_same["sd_sample"] == 0.0)

res_neg = core.analyze([-2.0, 2.0])
check("计算：负数参与运算", res_neg["avg"] == 0.0)

check("计算：空列表返回 None", core.analyze([]) is None)

# ---------- 结果文字 ----------

lines = core.result_lines(res)
text = "\n".join(lines)
check("报告：文字里有平均", "平均" in text)
check("报告：平均保留了 3 位小数", "5.02" in text)
check("报告：两种标准差都写明", text.count("标准差") == 2)
check("报告：个数写在第一行", lines[0] == "个数：5")

full = core.result_text(res)
check("报告：完整版带软件名", core.APP_NAME in full)
check("报告：完整版提醒问老师", "老师" in full)

# ---------- 导出 ----------

tmp = Path(tempfile.mkdtemp())
out = tmp / "结果.txt"
core.write_report(str(out), res)
check("导出：文件已生成", out.is_file())
content = out.read_text(encoding="utf-8-sig")
check("导出：内容里有平均", "平均" in content)
check("导出：utf-8-sig 带标记（记事本打开不乱码）",
      out.read_bytes()[:3] == b"\xef\xbb\xbf")

print()
if failures:
    print(f"核心测试失败 {len(failures)} 项：{failures}")
    sys.exit(1)
print(f"核心测试全部通过（共 30+ 项检查）")

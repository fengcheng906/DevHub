# -*- coding: utf-8 -*-
"""
实验数据小算手 v0.1.0 —— 核心逻辑模块
项目：AI 个人工作室操作系统（AI Personal Studio OS）的第三个产品

功能来源：虚拟试验区里的同名模拟窗口（用户拍板"做成真软件"）。
算法与模拟区保持一致，额外补了一个"实验课报告常用"的标准差。

本文件只负责"真正干活"的函数：拆数字、算统计、出报告文字。
图形界面在 app.py 里，只负责显示和按钮。

安全设计（底线，和前两个产品一致）：
1. 输入的数只在内存里算，不联网、不上传、不保存
2. 导出报告只写用户自己选的新文件，绝不改动任何东西
3. 读不出数字时明确报错，绝不瞎猜
"""

from __future__ import annotations

import math
import os

APP_NAME = "实验数据小算手"
APP_VERSION = "0.1.0"

# 模拟区里的示例数据（界面默认填入，方便第一次打开就能点）
SAMPLE_DATA = "5.02, 4.98, 5.10, 4.95, 5.05"


def parse_numbers(text: str) -> list:
    """把输入的文字拆成数字列表。

    支持：英文逗号、中文逗号、分号、空格、换行 当分隔符。
    拆不出来的片段（比如字母、中文）直接跳过，不报错。
    """
    if not text:
        return []
    normalized = (str(text)
                  .replace("，", ",").replace("；", ",").replace(";", ","))
    out = []
    for chunk in normalized.split(","):
        for piece in chunk.split():
            try:
                out.append(float(piece))
            except ValueError:
                continue  # 不是数字的片段跳过
    return out


def analyze(nums: list) -> dict | None:
    """算一组数的基本统计量。没有数字时返回 None，由界面提示用户。

    返回的每一项都是人话命名：
        n         个数
        avg       平均（加起来除以个数）
        min/max   最大 / 最小
        range_    极差（最大减最小，说明这一组数差多远）
        sd_sample 标准差（除以 个数-1，实验课报告常用）
        sd_pop    标准差（除以 个数，和模拟区一致）
    两种标准差都给：不少教材两种都提，让用户自己对照老师要求用哪个。
    """
    if not nums:
        return None
    n = len(nums)
    total = sum(nums)
    avg = total / n
    var_sum = sum((x - avg) ** 2 for x in nums)
    sd_pop = math.sqrt(var_sum / n)
    sd_sample = math.sqrt(var_sum / (n - 1)) if n >= 2 else 0.0
    return {
        "n": n,
        "sum": total,
        "avg": avg,
        "min": min(nums),
        "max": max(nums),
        "range": max(nums) - min(nums),
        "sd_sample": sd_sample,
        "sd_pop": sd_pop,
    }


def result_lines(res: dict) -> list:
    """把统计结果整理成几行文字（界面显示和导出报告共用）。"""
    return [
        f"个数：{res['n']}",
        f"平均：{round(res['avg'], 3)}（最常用的结果）",
        f"最大：{res['max']}　最小：{res['min']}　相差：{round(res['range'], 3)}",
        f"标准差：{round(res['sd_sample'], 3)}（除以个数减 1，实验课报告常用）",
        f"标准差：{round(res['sd_pop'], 3)}（除以个数，和网页模拟区一致）",
    ]


def result_text(res: dict) -> str:
    """完整报告文字：带标题，导出文件时用。"""
    lines = [f"{APP_NAME} v{APP_VERSION} 计算结果", ""]
    lines += result_lines(res)
    lines += ["", "提示：两种标准差只是分母不同，写实验报告前先问清老师要哪一种。"]
    return "\n".join(lines)


def write_report(path: str, res: dict) -> str:
    """把结果写成文本文件（utf-8-sig，记事本/Excel 打开不乱码）。返回写入路径。"""
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(result_text(res))
    return path


def default_report_path() -> str:
    """导出报告的默认文件名（放在桌面）。"""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    name = f"实验数据结果.txt"
    path = os.path.join(desktop, name)
    if not os.path.isdir(desktop):  # 个别电脑没有桌面文件夹，退回当前目录
        path = name
    return path

# -*- coding: utf-8 -*-
"""
数据处理助手 v0.1 —— 核心逻辑模块
项目：AI 个人工作室操作系统（AI Personal Studio OS）的第二个产品

本文件负责所有"真正干活"的函数：读取 CSV、清洗数据、统计信息、导出结果。
图形界面在 app.py 里，只负责显示和按钮。

这样拆分的好处：核心逻辑可以单独自动化测试，不依赖界面。

安全设计（底线，和工作台一致）：
1. 只处理用户明确选择的文件
2. 绝不修改原始文件，清洗结果一律写入新文件
3. 读取失败（编码不对、不是 CSV、文件为空）会明确报错，绝不瞎猜
4. 所有清洗函数都不改传入的数据，而是返回一份新的（避免界面状态错乱）
"""

from __future__ import annotations

import csv
import os

APP_NAME = "数据处理助手"
APP_VERSION = "0.2.1"

# 依次尝试的编码：Excel 导出的中文 CSV 常见 utf-8-sig 和 gbk 两种
ENCODINGS = ("utf-8-sig", "utf-8", "gbk", "gb18030")

# 导出统一用 utf-8-sig：带 BOM，Excel 双击打开中文不会乱码
OUTPUT_ENCODING = "utf-8-sig"


# ---------------- 读取 ----------------

def detect_encoding(path: str) -> str:
    """试探文件用哪种编码保存，返回编码名；都试不出来就抛错。"""
    for enc in ENCODINGS:
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                f.read()
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError("无法识别文件编码，请用 Excel 或记事本把文件另存为 CSV（UTF-8）后再试")


def read_table(path: str) -> tuple[list, list, str]:
    """读取 CSV，返回 (表头列表, 数据行列表, 编码名)。

    数据行是"列表的列表"，每一行是若干个字符串。
    行长不一致时自动补齐/截断到表头长度，保证表格整齐。
    """
    if not os.path.isfile(path):
        raise FileNotFoundError("文件不存在：" + path)
    enc = detect_encoding(path)
    with open(path, "r", encoding=enc, newline="") as f:
        rows = [row for row in csv.reader(f) if row]
    if len(rows) < 1:
        raise ValueError("文件是空的，没有内容")
    headers = [str(h) for h in rows[0]]
    data = []
    for r in rows[1:]:
        if len(r) < len(headers):
            r = r + [""] * (len(headers) - len(r))
        elif len(r) > len(headers):
            r = r[: len(headers)]
        data.append([str(c) for c in r])
    return headers, data, enc


# ---------------- 清洗（每个函数都返回新数据，不改原件） ----------------

def trim_all(headers: list, rows: list) -> tuple[list, list]:
    """去掉所有单元格内容首尾的空格（数据里最常见的脏点）。"""
    return [h.strip() for h in headers], [[c.strip() for c in r] for r in rows]


def remove_empty_rows(headers: list, rows: list) -> tuple[list, list]:
    """删掉整行都是空白的行（比如 Excel 里无意敲出来的空行）。"""
    return headers, [r for r in rows if any(c.strip() for c in r)]


def remove_empty_cols(headers: list, rows: list) -> tuple[list, list]:
    """删掉整列都是空白、且表头也是空白的列。"""
    keep = []
    for i in range(len(headers)):
        col_has_content = any((r[i] if i < len(r) else "").strip() for r in rows)
        if headers[i].strip() or col_has_content:
            keep.append(i)
    return [headers[i] for i in keep], [[r[i] for i in keep] for r in rows]


def remove_duplicates(headers: list, rows: list) -> tuple[list, list]:
    """删掉完全重复的行（每一列都相同的行，只保留第一条）。"""
    seen = set()
    out = []
    for r in rows:
        key = tuple(r)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return headers, out


def drop_missing_rows(headers: list, rows: list) -> tuple[list, list]:
    """删掉"任何一格是空白"的行（适合要求数据必须完整的场合）。"""
    return headers, [r for r in rows if all(c.strip() for c in r)]


def fill_missing(headers: list, rows: list, value: str) -> tuple[list, list]:
    """把空白格填成指定内容（比如 0），表头不受影响。"""
    return headers, [[c if c.strip() else value for c in r] for r in rows]


def _is_number(s: str) -> bool:
    """判断字符串是不是数字（允许千分位逗号，如 1,234.5）。"""
    try:
        float(s.replace(",", ""))
        return True
    except ValueError:
        return False


def _fmt_num(x: float) -> str:
    """数字转回字符串：整数不带小数点，小数保留原样。"""
    return str(int(x)) if x == int(x) else str(x)


def smart_numeric(headers: list, rows: list) -> tuple[list, list]:
    """智能数字列：某列除了空白格外全是数字，就把整列规范成数字格式。

    作用：去掉数字里误带的首尾空格、统一千分位写法，方便后续统计。
    列里只要有一个不是数字的内容（比如混了"约100"），整列保持原样不动。
    """
    new_rows = [list(r) for r in rows]
    for i in range(len(headers)):
        values = [(r[i] if i < len(r) else "").strip() for r in new_rows]
        filled = [v for v in values if v]
        if filled and all(_is_number(v) for v in filled):
            for r in new_rows:
                if i < len(r) and r[i].strip():
                    r[i] = _fmt_num(float(r[i].strip().replace(",", "")))
    return headers, new_rows


def clean_table(headers: list, rows: list, options: dict) -> tuple[list, list]:
    """按选项依次执行清洗流程，返回清洗后的 (表头, 数据行)。

    options 可选项（缺失时按默认值）：
        trim               去首尾空格          默认 True
        remove_empty_rows  删整行空白          默认 True
        remove_empty_cols  删整列空白          默认 False
        remove_duplicates  删完全重复行        默认 True
        drop_missing       删含空白格的行      默认 False
        fill_missing       空白格填成此值      默认 ""（空字符串=不填）
        smart_numeric      智能数字列          默认 True
    """
    if options.get("trim", True):
        headers, rows = trim_all(headers, rows)
    if options.get("remove_empty_rows", True):
        headers, rows = remove_empty_rows(headers, rows)
    if options.get("remove_empty_cols", False):
        headers, rows = remove_empty_cols(headers, rows)
    if options.get("remove_duplicates", True):
        headers, rows = remove_duplicates(headers, rows)
    if options.get("drop_missing", False):
        headers, rows = drop_missing_rows(headers, rows)
    fill_value = options.get("fill_missing", "")
    if fill_value != "":
        headers, rows = fill_missing(headers, rows, fill_value)
    if options.get("smart_numeric", True):
        headers, rows = smart_numeric(headers, rows)
    return headers, rows


# ---------------- 统计 ----------------

def summary(headers: list, rows: list) -> list:
    """逐列统计：有效值个数、缺失个数、不重复值个数；数字列额外给出最小/最大/平均。"""
    stats = []
    for i, h in enumerate(headers):
        col = [(r[i] if i < len(r) else "") for r in rows]
        values = [c.strip() for c in col if c.strip()]
        missing = len(col) - len(values)
        numeric = bool(values) and all(_is_number(v) for v in values)
        nums = [float(v.replace(",", "")) for v in values] if numeric else []
        stats.append({
            "name": h.strip() or f"第{i + 1}列",
            "count": len(values),
            "missing": missing,
            "unique": len(set(values)),
            "numeric": numeric,
            "min": min(nums) if nums else None,
            "max": max(nums) if nums else None,
            "mean": (sum(nums) / len(nums)) if nums else None,
        })
    return stats


def summary_text(stats: list) -> str:
    """把统计结果整理成人能直接读的文字报告。"""
    lines = []
    for s in stats:
        line = (f"{s['name']}：共 {s['count']} 个值，缺失 {s['missing']} 个，"
                f"不重复 {s['unique']} 个")
        if s["numeric"]:
            line += f"；数字列，最小 {s['min']}，最大 {s['max']}，平均 {round(s['mean'], 2)}"
        lines.append(line)
    return "\n".join(lines)


# ---------------- 筛选（v0.2.0 新增） ----------------

# 支持的条件（界面下拉框和这里一一对应）
FILTER_OPS = (
    ("eq", "等于"),
    ("ne", "不等于"),
    ("contains", "包含"),
    ("not_contains", "不包含"),
    ("gt", "大于"),
    ("ge", "大于等于"),
    ("lt", "小于"),
    ("le", "小于等于"),
    ("empty", "为空"),
    ("not_empty", "不为空"),
)


def filter_rows(headers: list, rows: list, col_idx: int,
                op: str, value: str = "") -> tuple[list, list]:
    """按条件筛出匹配的行，返回新数据，不改原件。

    col_idx：看哪一列（从 0 开始数）。
    op：条件，见 FILTER_OPS（"eq"=等于、"contains"=包含、"gt"=大于……）。
    value：比较用的值；选"为空/不为空"时这个值用不到。

    大小比较只对数字有效：这一格不是数字的行会被排除，不会算错。
    """
    if op not in {code for code, _ in FILTER_OPS}:
        raise ValueError(f"不认识的条件：{op}")

    def cell(r):
        return (r[col_idx] if col_idx < len(r) else "").strip()

    def match(r):
        c = cell(r)
        if op == "empty":
            return c == ""
        if op == "not_empty":
            return c != ""
        if op == "eq":
            return c == value.strip()
        if op == "ne":
            return c != value.strip()
        if op == "contains":
            return value.strip() in c
        if op == "not_contains":
            return value.strip() not in c
        # 以下四种是数字比较：格子不是数字就不匹配
        if not _is_number(c):
            return False
        target = value.strip().replace(",", "")
        if not _is_number(target):
            raise ValueError(f"「{value}」不是数字，无法做大小比较")
        a, b = float(c.replace(",", "")), float(target)
        return {"gt": a > b, "ge": a >= b, "lt": a < b, "le": a <= b}[op]

    return headers, [r for r in rows if match(r)]


# ---------------- 排序（v0.2.0 新增） ----------------

def sort_rows(headers: list, rows: list, col_idx: int,
              numeric: bool = False, reverse: bool = False) -> tuple[list, list]:
    """按某一列排序，返回新数据，不改原件。

    numeric=True：按数字大小排（数字以外的格子排在最后）。
    numeric=False：按文字顺序排（1, 10, 2 这种"自然顺序"，不是 1, 2, 10）。
    """
    import re

    def natural_key(s: str):
        # 把 "第3组" 拆成 ["第", 3, "组"]，数字段按数值比，排序更聪明
        parts = re.split(r"(\d+)", s)
        return tuple(int(p) if p.isdigit() else p for p in parts)

    def cell(r):
        return (r[col_idx] if col_idx < len(r) else "").strip()

    if numeric:
        # 数字行和非数字行（含空白）分开处理：
        # 数字按大小排，升降序都听指挥；非数字行一律垫底，保持原有顺序
        nums, others = [], []
        for r in rows:
            c = cell(r)
            if _is_number(c):
                nums.append((float(c.replace(",", "")), r))
            else:
                others.append(r)
        nums.sort(key=lambda t: t[0], reverse=reverse)
        return headers, [r for _, r in nums] + others

    def key(r):
        c = cell(r)
        return (c == "", natural_key(c))  # 空白排最后

    return headers, sorted(rows, key=key, reverse=reverse)


# ---------------- 图表数据（v0.2.0 新增） ----------------

def chart_series(headers: list, rows: list, col_idx: int,
                 top_n: int = 10) -> dict:
    """为柱状图准备数据：数出这一列里每个值各出现了多少次。

    数字列（比如成绩）会自动分成若干段（如 0-59、60-69……），段数最多 10 段；
    文字列则取出现次数最多的前 10 个值。
    返回 {"title": 图表标题, "is_numeric": 是否数字列, "items": [(标签, 次数), ...]}
    """
    col = [(r[col_idx] if col_idx < len(r) else "").strip() for r in rows]
    values = [c for c in col if c]
    name = (headers[col_idx] if col_idx < len(headers) else "").strip() or f"第{col_idx + 1}列"

    if not values:
        return {"title": f"「{name}」暂无数据", "is_numeric": False, "items": []}

    numeric = all(_is_number(v) for v in values)
    if not numeric:
        counts: dict[str, int] = {}
        for v in values:
            counts[v] = counts.get(v, 0) + 1
        top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]
        return {"title": f"「{name}」各值出现次数（前 {len(top)} 名）",
                "is_numeric": False, "items": top}

    nums = [float(v.replace(",", "")) for v in values]
    lo, hi = min(nums), max(nums)
    if lo == hi:
        label = _fmt_num(lo)
        return {"title": f"「{name}」全部等于 {label}",
                "is_numeric": True, "items": [(label, len(nums))]}

    # 数字列：自动分 10 段以内，统计每段有几个数
    span = hi - lo
    step = span / 10
    bounds = [lo + step * i for i in range(11)]
    counts = [0] * 10
    for n in nums:
        idx = min(int((n - lo) / step), 9)  # 最大那个数正好落在最后一段
        counts[idx] += 1
    items = []
    for i in range(10):
        if counts[i] == 0:
            continue  # 空段不画，图更清爽
        a, b = bounds[i], bounds[i + 1]
        label = f"{_fmt_num(round(a, 2))}~{_fmt_num(round(b, 2))}"
        items.append((label, counts[i]))
    return {"title": f"「{name}」数值分布（共 {len(nums)} 个数）",
            "is_numeric": True, "items": items}


# ---------------- 导出 ----------------

def default_output_path(src_path: str) -> str:
    """生成默认导出路径：原文件名后面加"（清洗后）"，不动原文件。"""
    base, ext = os.path.splitext(src_path)
    return base + "（清洗后）" + ext


def write_table(path: str, headers: list, rows: list) -> str:
    """把表格写成 CSV（utf-8-sig，Excel 直接打开不乱码）。返回写入路径。"""
    with open(path, "w", encoding=OUTPUT_ENCODING, newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    return path

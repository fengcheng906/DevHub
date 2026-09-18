# -*- coding: utf-8 -*-
r"""
数据处理助手 v0.1 —— 核心逻辑自动化测试

运行方式（在命令行里）：
    cd C:\DevHub\01_Projects\AI-Studio-OS\datatool
    python test_core.py

测试全部通过时，最后会显示 "全部测试通过"。
任何一项失败都会明确标出 FAIL。
"""

import csv
import shutil
import sys
from pathlib import Path

# 让中文在 Windows 命令行里正常显示
sys.stdout.reconfigure(encoding="utf-8")

import core

HERE = Path(__file__).parent
SANDBOX = HERE / "tests" / "sandbox"

passed = 0
failed = 0


def check(name, condition, detail=""):
    """每项测试的判定器。"""
    global passed, failed
    if condition:
        passed += 1
        print(f"  [通过] {name}")
    else:
        failed += 1
        print(f"  [失败] {name}  {detail}")


def write_csv(path, headers, rows, encoding="utf-8-sig"):
    """测试辅助：写一个 CSV 文件。"""
    with open(path, "w", encoding=encoding, newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def setup_sandbox():
    """每次测试前重建一个干净的测试文件夹。"""
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    SANDBOX.mkdir(parents=True)


# ---------------- 测试开始 ----------------

def test_read():
    setup_sandbox()
    print("读取功能：")

    # 1. 正常读取（utf-8-sig，Excel 默认导出格式之一）
    p = SANDBOX / "正常.csv"
    write_csv(p, ["姓名", "年龄"], [["张三", "20"], ["李四", "21"]])
    headers, rows, enc = core.read_table(str(p))
    check("读取：表头正确", headers == ["姓名", "年龄"], f"实际={headers}")
    check("读取：数据行正确", rows == [["张三", "20"], ["李四", "21"]], f"实际={rows}")
    check("读取：识别为 utf-8-sig 编码", enc == "utf-8-sig", f"实际={enc}")

    # 2. GBK 编码（老款 Excel / 部分国产软件导出）
    p2 = SANDBOX / "gbk.csv"
    write_csv(p2, ["姓名", "成绩"], [["王五", "88"]], encoding="gbk")
    headers2, rows2, enc2 = core.read_table(str(p2))
    check("读取：GBK 编码自动识别", enc2 == "gbk", f"实际={enc2}")
    check("读取：GBK 中文不乱码", rows2 == [["王五", "88"]], f"实际={rows2}")

    # 3. 行长不一致：自动补齐
    p3 = SANDBOX / "参差的行.csv"
    with open(p3, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["a", "b", "c"])
        w.writerow(["1", "2"])
        w.writerow(["1", "2", "3", "4"])
    _, rows3, _ = core.read_table(str(p3))
    check("读取：短行自动补空白", rows3[0] == ["1", "2", ""], f"实际={rows3[0]}")
    check("读取：长行自动截断", rows3[1] == ["1", "2", "3"], f"实际={rows3[1]}")

    # 4. 空文件要明确报错
    p4 = SANDBOX / "空的.csv"
    p4.write_text("", encoding="utf-8")
    try:
        core.read_table(str(p4))
        check("读取：空文件必须报错", False, "没有抛错")
    except ValueError:
        check("读取：空文件必须报错", True)

    # 5. 不存在的文件要明确报错
    try:
        core.read_table(str(SANDBOX / "不存在.csv"))
        check("读取：文件不存在必须报错", False, "没有抛错")
    except FileNotFoundError:
        check("读取：文件不存在必须报错", True)


def test_clean():
    setup_sandbox()
    print("清洗功能：")

    headers = ["姓名", "成绩", "备注"]
    rows = [
        [" 张三 ", " 90 ", ""],          # 带空格 → 去空格
        ["", "", ""],                     # 整行空白 → 删行
        ["李四", "", "缺考"],             # 部分空白
        ["李四", "", "缺考"],             # 与上一行完全重复 → 去重
        ["王五", "1,234.5", "千分位"],    # 千分位数字
    ]

    # 6. 去首尾空格
    h, r = core.trim_all(headers, rows)
    check("清洗：单元格首尾空格去掉", r[0] == ["张三", "90", ""], f"实际={r[0]}")

    # 7. 删整行空白
    _, r = core.remove_empty_rows(headers, rows)
    check("清洗：整行空白被删除", len(r) == 4, f"实际行数={len(r)}")

    # 8. 删整列空白（表头空白且内容全空的列才删）
    h8 = ["姓名", "成绩", ""]
    r8 = [["张三", "90", ""], ["李四", "80", ""]]
    h8, r8 = core.remove_empty_cols(h8, r8)
    check("清洗：空白表头+全空列被删除", len(h8) == 2 and all(len(x) == 2 for x in r8),
          f"实际表头={h8}")
    # 表头空白但列里有内容 → 保留
    h8b = ["姓名", "", "备注"]
    r8b = [["张三", "90", "好"]]
    h8b, r8b = core.remove_empty_cols(h8b, r8b)
    check("清洗：表头空白但列有内容则保留", len(h8b) == 3, f"实际表头={h8b}")

    # 9. 去完全重复行
    _, r9 = core.remove_duplicates(headers, rows)
    check("清洗：完全重复行只留一条", r9.count(["李四", "", "缺考"]) == 1)

    # 10. 删含空白格的行
    _, r10 = core.drop_missing_rows(headers, rows)
    check("清洗：含空白格的行全删掉", all(all(c.strip() for c in x) for x in r10)
          and len(r10) == 1, f"实际={r10}")

    # 11. 填充空白格
    _, r11 = core.fill_missing(headers, rows, "0")
    check("清洗：空白格填成指定值", r11[0][2] == "0" and r11[2][1] == "0", f"实际={r11}")

    # 12. 智能数字列：纯数字列被规范化（去空格/去千分位）
    h12, r12 = core.smart_numeric(["A", "B"], [[" 90 ", "abc"], ["1,234.5", "xyz"]])
    check("清洗：数字列规范化", r12[0][0] == "90" and r12[1][0] == "1234.5",
          f"实际={r12}")
    check("清洗：非数字列保持原样", r12[0][1] == "abc", f"实际={r12[0][1]}")

    # 13. 数字列里混一个非数字 → 整列不动
    h13, r13 = core.smart_numeric(["A"], [["10"], ["abc"], ["20"]])
    check("清洗：混合列不强行转数字", r13 == [["10"], ["abc"], ["20"]], f"实际={r13}")

    # 14. 完整流程：默认选项跑一遍，确认顺序和效果
    h14, r14 = core.clean_table(headers, rows, {})
    check("清洗：默认流程去空格+删空行+去重", len(r14) == 3 and r14[0][0] == "张三",
          f"实际={r14}")
    # drop_missing 选项
    _, r14b = core.clean_table(headers, rows, {"drop_missing": True})
    check("清洗：选「删含空白行」后只剩完整行", len(r14b) == 1, f"实际行数={len(r14b)}")

    # 15. 清洗不改动传入的原始数据（返回新数据）
    rows_copy = [list(x) for x in rows]
    core.clean_table(headers, rows, {"fill_missing": "0"})
    check("清洗：原始数据不被改动", rows == rows_copy, "传入的 rows 被改了")


def test_summary():
    setup_sandbox()
    print("统计功能：")

    headers = ["姓名", "成绩"]
    rows = [["张三", "80"], ["李四", "90"], ["王五", ""]]
    stats = core.summary(headers, rows)

    # 16. 逐列计数
    name_col = stats[0]
    score_col = stats[1]
    check("统计：有效值个数", name_col["count"] == 3, f"实际={name_col['count']}")
    check("统计：缺失个数", score_col["missing"] == 1, f"实际={score_col['missing']}")
    check("统计：不重复个数", name_col["unique"] == 3, f"实际={name_col['unique']}")

    # 17. 数字列的最小/最大/平均
    check("统计：数字列识别", score_col["numeric"] is True)
    check("统计：最小值", score_col["min"] == 80, f"实际={score_col['min']}")
    check("统计：最大值", score_col["max"] == 90, f"实际={score_col['max']}")
    check("统计：平均值", score_col["mean"] == 85, f"实际={score_col['mean']}")
    check("统计：文字列不当作数字", name_col["numeric"] is False)

    # 18. 文字报告
    text = core.summary_text(stats)
    check("统计：报告包含列名", "姓名" in text and "成绩" in text)
    check("统计：报告包含缺失数", "缺失 1 个" in text)


def test_export():
    setup_sandbox()
    print("导出功能：")

    headers = ["姓名", "成绩"]
    rows = [["张三", "90"], ["李四", "85"]]
    src = SANDBOX / "原始数据.csv"
    write_csv(src, headers, rows)

    # 19. 默认导出路径：原文件名加"（清洗后）"，不改原文件
    out_path = core.default_output_path(str(src))
    check("导出：默认路径带「清洗后」且后缀不变",
          out_path.endswith("原始数据（清洗后）.csv"), f"实际={out_path}")

    # 20. 写出后能原样读回，中文不乱码
    core.write_table(out_path, headers, rows)
    h2, r2, enc2 = core.read_table(out_path)
    check("导出：读回内容一致", h2 == headers and r2 == rows, f"实际={h2},{r2}")
    check("导出：编码为 utf-8-sig（Excel 直接打开不乱码）", enc2 == "utf-8-sig",
          f"实际={enc2}")

    # 21. 原则底线：读取+清洗+导出后，原始文件一个字节都没变
    before = src.read_bytes()
    h3, r3, _ = core.read_table(str(src))
    core.clean_table(h3, r3, {"fill_missing": "0"})
    core.write_table(core.default_output_path(str(src)), h3, r3)
    after = src.read_bytes()
    check("导出：原始文件绝不被修改", before == after)


def test_filter_sort_chart():
    print("筛选 / 排序 / 图表数据（v0.2.0 新增）：")

    headers = ["姓名", "班级", "成绩"]
    rows = [
        ["张三", "1班", "90"],
        ["李四", "2班", "55"],
        ["王五", "1班", ""],
        ["赵六", "2班", "77"],
        ["孙七", "1班", "90"],
    ]

    # 22. 等于
    _, r = core.filter_rows(headers, rows, 1, "eq", "1班")
    check("筛选：等于 1班 剩 3 行", len(r) == 3, f"实际={len(r)}")

    # 23. 包含
    _, r = core.filter_rows(headers, rows, 0, "contains", "张")
    check("筛选：姓名包含「张」剩 1 行", len(r) == 1 and r[0][0] == "张三")

    # 24. 大于（只认数字，空白格被排除）
    _, r = core.filter_rows(headers, rows, 2, "gt", "60")
    check("筛选：成绩大于 60 剩 3 行（空白不算）", len(r) == 3, f"实际={len(r)}")

    # 25. 大小比较遇到非数字的比较值会明确报错
    try:
        core.filter_rows(headers, rows, 2, "gt", "abc")
        check("筛选：比较值不是数字时抛错", False, "没有抛错")
    except ValueError:
        check("筛选：比较值不是数字时抛错", True)

    # 26. 为空 / 不为空
    _, r = core.filter_rows(headers, rows, 2, "empty")
    check("筛选：成绩为空剩 1 行", len(r) == 1)
    _, r = core.filter_rows(headers, rows, 2, "not_empty")
    check("筛选：成绩不为空剩 4 行", len(r) == 4)

    # 27. 不认识的条件会报错
    try:
        core.filter_rows(headers, rows, 0, "haha", "x")
        check("筛选：非法条件抛错", False, "没有抛错")
    except ValueError:
        check("筛选：非法条件抛错", True)

    # 28. 筛选不改原始数据
    core.filter_rows(headers, rows, 1, "eq", "1班")
    check("筛选：原始数据未被改动", len(rows) == 5)

    # 29. 数字排序：小的在前，空白排最后
    _, r = core.sort_rows(headers, rows, 2, numeric=True)
    check("排序：数字升序最后一个是空白", r[-1][2] == "", f"实际={r[-1]}")
    check("排序：数字升序第一个是 55", r[0][2] == "55")

    # 30. 数字降序
    _, r = core.sort_rows(headers, rows, 2, numeric=True, reverse=True)
    check("排序：数字降序第一个是 90", r[0][2] == "90")

    # 31. 文字排序：自然顺序（第2组 在 第10组 前）
    h2 = ["组名"]
    r2 = [["第10组"], ["第2组"], ["第1组"]]
    _, rs = core.sort_rows(h2, r2, 0)
    check("排序：文字自然顺序 1→2→10", [x[0] for x in rs] == ["第1组", "第2组", "第10组"],
          f"实际={[x[0] for x in rs]}")

    # 32. 文字排序不改原始数据
    check("排序：原始数据未被改动", [x[0] for x in r2] == ["第10组", "第2组", "第1组"])

    # 33. 图表数据：文字列数出现次数
    s = core.chart_series(headers, rows, 1)
    items = dict(s["items"])
    check("图表：文字列 1班 出现 3 次", items.get("1班") == 3, f"实际={items}")

    # 34. 图表数据：数字列自动分段且总数对得上
    s = core.chart_series(headers, rows, 2)
    total = sum(n for _, n in s["items"])
    check("图表：数字列各段次数加起来=有效数字个数", total == 4, f"实际={total}")
    check("图表：数字列标记为数字列", s["is_numeric"] is True)

    # 35. 图表数据：空列不崩溃
    s = core.chart_series(headers, [], 0)
    check("图表：没有数据时返回空项目", s["items"] == [])

    # 36. 连续组合：清洗 → 筛选 → 排序，链条结果正确
    hh, rr = core.clean_table(headers, rows, {})
    hh, rr = core.filter_rows(hh, rr, 2, "not_empty")
    hh, rr = core.sort_rows(hh, rr, 2, numeric=True, reverse=True)
    check("组合：先筛非空再降序，成绩依次 90/90/77/55",
          [x[2] for x in rr] == ["90", "90", "77", "55"], f"实际={[x[2] for x in rr]}")


def main():
    test_read()
    test_clean()
    test_summary()
    test_export()
    test_filter_sort_chart()
    print()
    print(f"共 {passed + failed} 项，通过 {passed} 项，失败 {failed} 项")
    if failed == 0:
        print("全部测试通过")
    else:
        print("存在失败项，请检查上面的 [失败] 明细")
        sys.exit(1)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
r"""
智能文件工作台 v0.1 —— 核心逻辑自动化测试

运行方式（在命令行里）：
    cd C:\DevHub\01_Projects\AI-Studio-OS\workbench
    python test_core.py

测试全部通过时，最后会显示 "全部测试通过"。
任何一项失败都会明确标出 FAIL。
"""

import sys
import shutil
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


def setup_sandbox():
    """每次测试前重建一个干净的沙盒文件夹，放入各种测试文件。"""
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    SANDBOX.mkdir(parents=True)

    # 普通文件：应该被分类
    for name in ("照片A.jpg", "笔记.txt", "电影.mp4", "歌曲.mp3", "资料.zip", "安装包.exe"):
        (SANDBOX / name).write_text(f"测试文件 {name}", encoding="utf-8")

    # 没有规则的扩展名：应该跳过
    (SANDBOX / "奇怪文件.xyz").write_text("无规则文件", encoding="utf-8")

    # 隐藏文件：应该跳过
    (SANDBOX / ".隐藏配置").write_text("hidden", encoding="utf-8")

    # 制造同名冲突：目标文件夹里已有一个同名文件
    (SANDBOX / "图片").mkdir()
    (SANDBOX / "图片" / "照片A.jpg").write_text("已存在的同名文件", encoding="utf-8")


print("=" * 60)
print("智能文件工作台 v0.1 —— 自动化测试")
print("=" * 60)

# 先建沙盒，保证"被允许"检查的对象真实存在
setup_sandbox()

# ---------- 测试 1：安全检查 ----------
print("\n[测试1] 安全检查：危险目录必须被拒绝")
ok1, _ = core.is_safe_folder("C:\\Windows")
check("C:\\Windows 被拒绝", not ok1)
ok2, _ = core.is_safe_folder("C:\\Program Files\\Git")
check("Program Files 内被拒绝", not ok2)
ok3, _ = core.is_safe_folder("C:\\")
check("盘符根目录被拒绝", not ok3)
home = Path.home()
ok4, _ = core.is_safe_folder(home / "Documents")
check("个人文档目录被拒绝", not ok4)
ok5, _ = core.is_safe_folder(str(SANDBOX))
check("沙盒文件夹被允许", ok5)

# ---------- 测试 2：扫描与规划 ----------
print("\n[测试2] 扫描与规划：预览不改动任何文件")
setup_sandbox()
before = sorted(p.name for p in SANDBOX.iterdir())
plan = core.build_plan(SANDBOX)
after = sorted(p.name for p in SANDBOX.iterdir())
check("规划后文件夹无任何变化（纯预览）", before == after)

status = {a["file"]: a["status"] for a in plan}
check("照片A.jpg 识别为冲突", status.get("照片A.jpg") == "CONFLICT")
check("笔记.txt 计划移入文档", status.get("笔记.txt") == "OK")
check("电影.mp4 计划移入视频", status.get("电影.mp4") == "OK")
check("奇怪文件.xyz 被跳过", status.get("奇怪文件.xyz") == "SKIP")
check("隐藏文件被跳过", status.get(".隐藏配置") == "SKIP")

ok_actions = [a for a in plan if a["status"] == "OK"]
check("计划移动数量 = 5（txt/mp4/mp3/zip/exe）", len(ok_actions) == 5,
      f"实际 {len(ok_actions)}")

# ---------- 测试 3：执行 ----------
print("\n[测试3] 执行整理：只有 OK 的文件被移动")
records = core.execute_plan(SANDBOX, plan)
moved = [r for r in records if r["operation"] == "move"]
check("实际移动 5 个文件", len(moved) == 5, f"实际 {len(moved)}")
check("笔记.txt 进入了 文档/", (SANDBOX / "文档" / "笔记.txt").exists())
check("电影.mp4 进入了 视频/", (SANDBOX / "视频" / "电影.mp4").exists())
check("歌曲.mp3 进入了 音乐/", (SANDBOX / "音乐" / "歌曲.mp3").exists())
check("资料.zip 进入了 压缩包/", (SANDBOX / "压缩包" / "资料.zip").exists())
check("安装包.exe 进入了 安装程序/", (SANDBOX / "安装程序" / "安装包.exe").exists())
check("冲突的照片A.jpg 原地未动", (SANDBOX / "照片A.jpg").exists())
check("原位置的笔记.txt 已不在", not (SANDBOX / "笔记.txt").exists())

# ---------- 测试 4：日志 ----------
print("\n[测试4] 日志与报告")
log_file, report_file = core.write_log(SANDBOX, records, note="自动化测试")
check("撤销日志已生成", log_file.exists())
check("人读报告已生成", report_file.exists())
check("日志里记录了 5 次移动", len(
    [r for r in __import__("json").loads(log_file.read_text(encoding="utf-8"))["operations"]
     if r["operation"] == "move"]) == 5)

# ---------- 测试 5：撤销 ----------
print("\n[测试5] 撤销：文件全部恢复原位，空分类文件夹被清理")
restored, errors, removed_dirs = core.undo_from_log(log_file)
check("撤销成功 5 个文件", restored == 5, f"实际 {restored}，错误 {errors}")
check("笔记.txt 回到原位", (SANDBOX / "笔记.txt").exists())
check("电影.mp4 回到原位", (SANDBOX / "电影.mp4").exists())
check("文档/ 里的副本已消失", not (SANDBOX / "文档" / "笔记.txt").exists())
check("文档/ 空目录已被清理", not (SANDBOX / "文档").exists())
check("视频/ 空目录已被清理", not (SANDBOX / "视频").exists())
check("音乐/ 空目录已被清理", not (SANDBOX / "音乐").exists())
check("压缩包/ 空目录已被清理", not (SANDBOX / "压缩包").exists())
check("安装程序/ 空目录已被清理", not (SANDBOX / "安装程序").exists())
check("原有的 图片/ 目录保留（里面还有冲突文件）",
      (SANDBOX / "图片" / "照片A.jpg").exists())
check("清理目录数 = 5", len(removed_dirs) == 5, f"实际 {removed_dirs}")

# ---------- 测试 6：找最新日志 ----------
print("\n[测试6] 定位最新日志")
latest = core.latest_log(SANDBOX)
check("能找到最新日志", latest is not None and latest == log_file)

# ---------- 测试 7：目录非空时绝不清理 ----------
print("\n[测试7] 边界情况：用户往分类目录里放了新东西，撤销不得误删")
setup_sandbox()  # 重建干净沙盒
plan2 = core.build_plan(SANDBOX)
records2 = core.execute_plan(SANDBOX, plan2)
log2, _ = core.write_log(SANDBOX, records2, note="边界测试")

# 撤销之前，用户手动往"文档"里放一个新文件
(SANDBOX / "文档" / "用户自己的文件.txt").write_text("这是用户放进去的", encoding="utf-8")

restored2, errors2, removed2 = core.undo_from_log(log2)
removed_names = [Path(d).name for d in removed2]
check("文件恢复数量 = 5", restored2 == 5, f"实际 {restored2}，错误 {errors2}")
check("用户自己的文件.txt 安然无恙",
      (SANDBOX / "文档" / "用户自己的文件.txt").exists())
check("非空的 文档/ 目录被保留（没有被误删）", (SANDBOX / "文档").exists()
      and "文档" not in removed_names)
check("空的 视频/ 被正常清理", "视频" in removed_names,
      f"实际清理了: {removed_names}")

# ---------- 总结 ----------
print("\n" + "=" * 60)
print(f"测试结果：通过 {passed} 项，失败 {failed} 项")
print("=" * 60)
if failed == 0:
    print("全部测试通过 ✔  智能文件工作台 v0.1 核心逻辑可用")
else:
    print("存在失败项 ✘  请修复后再使用")
    sys.exit(1)

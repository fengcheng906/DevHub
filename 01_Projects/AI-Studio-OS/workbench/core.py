# -*- coding: utf-8 -*-
"""
智能文件工作台 v0.1 —— 核心逻辑模块
项目：AI 个人工作室操作系统（AI Personal Studio OS）的第一个产品

本文件负责所有"真正干活"的函数：扫描、规划、执行、撤销、写记录。
图形界面在 app.py 里，只负责显示和按钮，不直接操作文件。

这样拆分的好处：核心逻辑可以单独自动化测试，不依赖界面。

安全设计（v0.1 的底线）：
1. 只处理用户明确选择的文件夹
2. 绝不删除文件，只做"移动到子文件夹"一种操作
3. 系统目录和个人重要目录直接拒绝
4. 执行前必须先预览（build_plan 不改任何东西）
5. 同名冲突的文件一律不动，留给用户处理
6. 每次操作都写日志，可以一键撤销
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

APP_NAME = "智能文件工作台"
APP_VERSION = "0.1.1"

# 整理记录的存放目录（整理时会跳过这个目录，不会把它当作文件分类）
LOG_DIR_NAME = "_工作台记录"

# ---------------- 默认分类规则（可扩展） ----------------
DEFAULT_RULES = {
    "图片": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico"],
    "文档": [".pdf", ".doc", ".docx", ".txt", ".md", ".xls", ".xlsx",
             ".ppt", ".pptx", ".csv"],
    "视频": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"],
    "音乐": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma"],
    "压缩包": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "安装程序": [".exe", ".msi"],
}


def build_ext_map(rules: dict | None = None) -> dict:
    """把 {类别: [扩展名...]} 翻译成 {扩展名: 类别}，方便查找。"""
    rules = rules or DEFAULT_RULES
    mapping = {}
    for category, exts in rules.items():
        for ext in exts:
            mapping[ext.lower()] = category
    return mapping


# ---------------- 安全检查 ----------------

def is_safe_folder(folder) -> tuple[bool, str]:
    """检查目标文件夹是否允许处理。返回 (是否安全, 原因)。"""
    folder = Path(folder).resolve()
    s = str(folder)

    if not folder.exists():
        return False, "文件夹不存在"
    if not folder.is_dir():
        return False, "选择的不是文件夹"
    if folder.parent == folder:  # 盘符根目录，如 C:\
        return False, "不允许选择整个磁盘分区"

    # 系统目录（精确匹配 + 前缀匹配）
    forbidden_prefix = (
        "c:\\windows",
        "c:\\program files",
        "c:\\program files (x86)",
    )
    home = Path.home()
    forbidden_exact = {
        "c:\\programdata",
        str(home).lower(),
        str(home / "Desktop").lower(),
        str(home / "Documents").lower(),
        str(home / "Downloads").lower(),
        str(home / "Pictures").lower(),
    }

    ls = s.lower().rstrip("\\")
    for p in forbidden_prefix:
        if ls.startswith(p):
            return False, "该位置位于系统目录内，为安全起见禁止整理"
    if ls in forbidden_exact:
        return False, "这是系统或个人重要目录，为安全起见禁止整理（请选择专门的工作文件夹）"

    return True, ""


# ---------------- 扫描 ----------------

def scan_folder(folder) -> list[dict]:
    """扫描文件夹第一层的所有文件（不进子文件夹），返回文件信息列表。"""
    folder = Path(folder)
    result = []
    for p in sorted(folder.iterdir()):
        if p.is_file():
            st = p.stat()
            result.append({
                "name": p.name,
                "suffix": p.suffix.lower(),
                "size": st.st_size,
                "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
    return result


# ---------------- 整理计划（只规划，不执行） ----------------

def build_plan(folder, rules: dict | None = None) -> list[dict]:
    """根据规则为每个文件生成整理计划。注意：本函数不修改任何文件。"""
    folder = Path(folder)
    ext_map = build_ext_map(rules)
    actions = []

    for info in scan_folder(folder):
        name = info["name"]

        # 隐藏文件不处理
        if name.startswith("."):
            actions.append({
                "file": name,
                "action": "跳过（隐藏文件）",
                "status": "SKIP",
            })
            continue

        category = ext_map.get(info["suffix"])
        if category is None:
            actions.append({
                "file": name,
                "action": "跳过（没有匹配的分类规则）",
                "status": "SKIP",
            })
            continue

        target_dir = folder / category
        target = target_dir / name

        if target.exists():
            # 同名冲突：绝不覆盖，留给用户自己决定
            actions.append({
                "file": name,
                "action": f"冲突：[{category}] 里已有同名文件，本次不动它",
                "status": "CONFLICT",
            })
        else:
            actions.append({
                "file": name,
                "action": f"移入 [{category}] 文件夹",
                "status": "OK",
                "target_dir": category,
                "target": str(target),
            })
    return actions


# ---------------- 执行 ----------------

def execute_plan(folder, plan: list[dict]) -> list[dict]:
    """执行整理计划。只执行状态为 OK 的项目，其余全部跳过。

    返回执行记录（每一条对应一次文件移动），用于写日志和撤销。
    """
    folder = Path(folder)
    records = []

    for act in plan:
        if act.get("status") != "OK":
            continue
        src = folder / act["file"]
        dst = Path(act["target"])

        # 执行前再做一次最终检查（文件还在吗？目标没有同名吗？）
        if not src.exists():
            records.append({
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "operation": "skip-missing",
                "from": str(src),
                "to": str(dst),
                "note": "源文件已不存在，跳过",
            })
            continue
        if dst.exists():
            records.append({
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "operation": "skip-conflict",
                "from": str(src),
                "to": str(dst),
                "note": "目标位置出现同名文件，跳过",
            })
            continue

        # 记录这个目录是不是本次整理才创建的（撤销时要清理空目录）
        created_dir = None
        if not dst.parent.exists():
            created_dir = str(dst.parent)

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        records.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "operation": "move",
            "from": str(src),
            "to": str(dst),
            # 记录"这个目录是本次整理才创建的"，撤销时用来清理空目录
            "created_dir": created_dir,
        })
    return records


# ---------------- 日志与报告 ----------------

def write_log(folder, records: list[dict], note: str = "") -> tuple[Path, Path]:
    """把执行记录写入日志文件（机器读的 JSON）和报告（人看的 TXT）。"""
    folder = Path(folder)
    log_dir = folder / LOG_DIR_NAME
    log_dir.mkdir(exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON 日志：撤销功能靠它
    log_file = log_dir / f"undo_{stamp}.json"
    data = {
        "app": APP_NAME,
        "version": APP_VERSION,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "folder": str(folder),
        "note": note,
        "operations": records,
        # 本次整理才创建的目录（撤销时若已空则清理掉）
        "created_dirs": sorted({
            r["created_dir"] for r in records if r.get("created_dir")
        }),
    }
    log_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # TXT 报告：给人看的
    report = log_dir / f"report_{stamp}.txt"
    moved = [r for r in records if r["operation"] == "move"]
    skipped = [r for r in records if r["operation"] != "move"]
    lines = [
        f"{APP_NAME} v{APP_VERSION} 整理报告",
        f"时间：{data['time']}",
        f"文件夹：{folder}",
        f"结果：成功移动 {len(moved)} 个文件，跳过 {len(skipped)} 个",
        "-" * 50,
    ]
    for r in moved:
        lines.append(f"[移动] {Path(r['from']).name}  →  {Path(r['to']).parent.name}/")
    for r in skipped:
        lines.append(f"[跳过] {Path(r['from']).name}（{r.get('note', '')}）")
    lines.append("")
    lines.append(f"撤销方法：打开本软件，点「撤销上次整理」，选择 undo_{stamp}.json")
    report.write_text("\n".join(lines), encoding="utf-8")

    return log_file, report


# ---------------- 撤销 ----------------

def undo_from_log(log_file) -> tuple[int, list[str], list[str]]:
    """根据日志把文件搬回原位。

    返回 (成功恢复数量, 出错信息列表, 已清理的空目录列表)。
    目录清理规则：只清理"本次整理才创建"且"撤销后已空"的目录；
    用 os.rmdir 语义（目录非空时拒绝删除），绝不误删用户原有内容。
    """
    data = json.loads(Path(log_file).read_text(encoding="utf-8"))
    restored = 0
    errors = []

    for op in data["operations"]:
        if op["operation"] != "move":
            continue
        now_pos = Path(op["to"])     # 文件现在在哪
        old_pos = Path(op["from"])   # 原来在哪

        if not now_pos.exists():
            errors.append(f"找不到 {now_pos.name}，可能已被移动或删除")
            continue
        if old_pos.exists():
            errors.append(f"无法恢复 {now_pos.name}：原位置已有同名文件")
            continue

        shutil.move(str(now_pos), str(old_pos))
        restored += 1

    # 清理本次整理才创建、且现在已空的目录
    removed_dirs = []
    for d in data.get("created_dirs", []):
        d = Path(d)
        if not d.exists():
            continue
        try:
            d.rmdir()  # 只允许删空目录，非空会抛 OSError
            removed_dirs.append(str(d))
        except OSError:
            # 目录里还有别的东西（用户自己放进去的），绝不动
            pass

    return restored, errors, removed_dirs


def latest_log(folder) -> Path | None:
    """返回文件夹里最新的一份撤销日志路径（没有则返回 None）。"""
    log_dir = Path(folder) / LOG_DIR_NAME
    if not log_dir.exists():
        return None
    logs = sorted(log_dir.glob("undo_*.json"))
    return logs[-1] if logs else None

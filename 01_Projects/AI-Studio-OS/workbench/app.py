# -*- coding: utf-8 -*-
"""
智能文件工作台 v0.1.8 —— 图形界面（精修版）
项目：AI 个人工作室操作系统（AI Personal Studio OS）

怎么打开这个软件：
    双击本文件，或在命令行里运行：python app.py

界面按钮从左到右按顺序用就行：
    ① 选择文件夹 ② 扫描预览 ③ 执行整理 ④ 撤销上次 ⑤ 规则管理 ⑥ 批量重命名
    （每个按钮名下面还有一句大白话说明，是干什么的一眼就看懂）

v0.1.8 按钮大白话：按钮分两行显示，名字下面加括号说明（用户拍板），功能零改动。
v0.1.7 界面精修：高分屏适配（文字不发虚）、现代配色、卡片式布局，功能零改动。
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

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

import core

# 拖拽支持：装了 tkinterdnd2 就能拖文件夹进窗口；没装也不影响其他功能
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

# ---------------- 配色（与数据处理助手同一套高级感配色） ----------------
BG = "#eef1f7"          # 窗口底色：浅灰蓝
CARD = "#ffffff"        # 卡片底色：纯白
BORDER = "#dde3ee"      # 卡片描边
TEXT = "#1f2430"        # 正文：深灰黑
SUBTEXT = "#7a8499"     # 次要文字：灰
ACCENT = "#356ae6"      # 主色：沉静的蓝
ACCENT_HOVER = "#2456c4"
ACCENT_SOFT = "#e3ecfd"  # 主色的浅色底（次按钮、选中行用）
OK_GREEN = "#16a34a"    # 绿：将移动
WARN_ORANGE = "#d97706"  # 橙：同名冲突
SKIP_GRAY = "#9aa3b5"   # 灰：跳过


def _font(size=10, bold=False):
    """统一字体：微软雅黑，大小可调。"""
    return ("Microsoft YaHei UI", size, "bold" if bold else "normal")


def _style_button(btn, bg, fg, hover_bg, bold=True):
    """把按钮做成扁平精致样式，并带鼠标悬停变色（禁用时不变色）。"""
    btn.configure(
        bg=bg, fg=fg,
        activebackground=hover_bg, activeforeground=fg,
        relief="flat", bd=0, cursor="hand2",
        padx=14, pady=7, font=_font(10, bold),
        disabledforeground="#aab2c5",
    )

    def _on_enter(e):
        if str(btn["state"]) != "disabled":
            btn.configure(bg=hover_bg)

    def _on_leave(e):
        btn.configure(bg=bg)

    btn.bind("<Enter>", _on_enter)
    btn.bind("<Leave>", _on_leave)


class WorkbenchApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.folder = None      # 当前选择的文件夹
        self.plan = []          # 最近一次生成的整理计划

        root.title(f"{core.APP_NAME} v{core.APP_VERSION}")
        root.geometry("980x660")
        root.minsize(860, 560)
        root.configure(bg=BG)

        self._build_ui()

    # ---------- 界面搭建 ----------

    def _build_ui(self):
        # clam 主题：唯一能自定义所有颜色的主题
        style = ttk.Style(self.root)
        style.theme_use("clam")

        # 表格样式：去边框、加行高、选中行用浅蓝
        style.configure(
            "Treeview",
            background=CARD, fieldbackground=CARD, foreground=TEXT,
            rowheight=32, font=_font(10), borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background="#f3f5fa", foreground=TEXT,
            font=_font(10, True), padding=(10, 9), relief="flat",
        )
        style.map(
            "Treeview",
            background=[("selected", ACCENT_SOFT)],
            foreground=[("selected", TEXT)],
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#e8ecf5")],
        )

        # 单选框 / 勾选框样式
        style.configure(
            "TCheckbutton",
            background=CARD, foreground=TEXT, font=_font(10),
        )
        style.configure(
            "TRadiobutton",
            background=CARD, foreground=TEXT, font=_font(10),
        )

        # 滚动条样式
        style.configure(
            "Vertical.TScrollbar",
            background="#e6eaf3", troughcolor=CARD,
            borderwidth=0, arrowcolor=SUBTEXT, relief="flat",
        )

        # ===== 顶部标题区 =====
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill=tk.X, padx=20, pady=(16, 4))
        tk.Label(header, text=core.APP_NAME, bg=BG, fg=TEXT,
                 font=_font(17, True)).pack(side=tk.LEFT)
        tk.Label(header, text=f"  v{core.APP_VERSION}", bg=BG, fg=SUBTEXT,
                 font=_font(10)).pack(side=tk.LEFT, pady=(6, 0))
        tk.Label(header, text="把文件夹收拾得井井有条",
                 bg=BG, fg=SUBTEXT, font=_font(10)).pack(side=tk.RIGHT, pady=(8, 0))

        # ===== 文件夹选择卡片 =====
        folder_card = tk.Frame(self.root, bg=CARD,
                               highlightbackground=BORDER, highlightthickness=1)
        folder_card.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(folder_card, text="目标文件夹", bg=CARD, fg=SUBTEXT,
                 font=_font(9, True)).pack(side=tk.LEFT, padx=(14, 6), pady=10)

        self.folder_var = tk.StringVar(value="（还没有选择文件夹）")
        folder_entry = tk.Entry(
            folder_card, textvariable=self.folder_var,
            bg="#f6f8fc", fg=TEXT, readonlybackground="#f6f8fc",
            relief="flat", font=_font(10),
            highlightthickness=1, highlightcolor=ACCENT, highlightbackground=BORDER,
        )
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True,
                          padx=(0, 10), ipady=5)

        btn_choose = tk.Button(folder_card, text="① 选择文件夹\n（选要整理的地方）",
                               command=self.choose_folder)
        _style_button(btn_choose, ACCENT, "#ffffff", ACCENT_HOVER)
        btn_choose.pack(side=tk.RIGHT, padx=(0, 12), pady=8)

        # ===== 预览区（标题 + 表格） =====
        mid = tk.Frame(self.root, bg=BG)
        mid.pack(fill=tk.BOTH, expand=True, padx=20)

        tk.Label(mid, text="整理预览", bg=BG, fg=SUBTEXT,
                 font=_font(9, True)).pack(anchor=tk.W, pady=(2, 4))

        table_card = tk.Frame(mid, bg=CARD,
                              highlightbackground=BORDER, highlightthickness=1)
        table_card.pack(fill=tk.BOTH, expand=True)

        columns = ("file", "type", "action", "status")
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings")
        self.tree.heading("file", text="文件名")
        self.tree.heading("type", text="类型")
        self.tree.heading("action", text="整理动作（预览）")
        self.tree.heading("status", text="状态")
        self.tree.column("file", width=250)
        self.tree.column("type", width=90, anchor=tk.CENTER)
        self.tree.column("action", width=340)
        self.tree.column("status", width=120, anchor=tk.CENTER)

        # 不同状态用不同颜色区分
        self.tree.tag_configure("ok", foreground=OK_GREEN)         # 绿：将移动
        self.tree.tag_configure("conflict", foreground=WARN_ORANGE)  # 橙：冲突
        self.tree.tag_configure("skip", foreground=SKIP_GRAY)      # 灰：跳过

        scrollbar = ttk.Scrollbar(table_card, orient=tk.VERTICAL,
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ===== 整理方式 + 操作按钮卡片 =====
        bottom_card = tk.Frame(self.root, bg=CARD,
                               highlightbackground=BORDER, highlightthickness=1)
        bottom_card.pack(fill=tk.X, padx=20, pady=(10, 0))

        mode_row = tk.Frame(bottom_card, bg=CARD)
        mode_row.pack(fill=tk.X, padx=10, pady=(10, 0))

        tk.Label(mode_row, text="整理方式", bg=CARD, fg=SUBTEXT,
                 font=_font(9, True)).pack(side=tk.LEFT, padx=(4, 10))

        self.mode_var = tk.StringVar(value="type")
        ttk.Radiobutton(mode_row, text="按类型", variable=self.mode_var,
                        value="type").pack(side=tk.LEFT)
        ttk.Radiobutton(mode_row, text="按日期", variable=self.mode_var,
                        value="date").pack(side=tk.LEFT, padx=(0, 14))

        self.recursive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(mode_row, text="包含子文件夹",
                        variable=self.recursive_var).pack(side=tk.LEFT, padx=(0, 14))

        if HAS_DND:
            tk.Label(mode_row,
                     text="提示：也可以直接把文件/文件夹拖进窗口",
                     bg=CARD, fg=SUBTEXT, font=_font(9)).pack(side=tk.RIGHT, padx=4)

        btn_row = tk.Frame(bottom_card, bg=CARD)
        btn_row.pack(fill=tk.X, padx=10, pady=(6, 10))

        # 按钮名后括号里是一句大白话说明（用户拍板：不换名，加括号标注）
        self.btn_scan = tk.Button(btn_row, text="② 扫描预览\n（先演习，不动真文件）",
                                  command=self.do_scan, state=tk.DISABLED)
        _style_button(self.btn_scan, ACCENT, "#ffffff", ACCENT_HOVER)
        self.btn_scan.pack(side=tk.LEFT, padx=(4, 8))

        self.btn_run = tk.Button(btn_row, text="③ 执行整理\n（真动手，可撤销）",
                                 command=self.do_execute, state=tk.DISABLED)
        _style_button(self.btn_run, ACCENT, "#ffffff", ACCENT_HOVER)
        self.btn_run.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_undo = tk.Button(btn_row, text="④ 撤销上次\n（反悔，恢复原样）",
                                  command=self.do_undo, state=tk.DISABLED)
        _style_button(self.btn_undo, ACCENT_SOFT, ACCENT, "#d3e0fa")
        self.btn_undo.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_rules = tk.Button(btn_row, text="⑤ 规则管理\n（哪些进哪个夹）",
                                   command=self.edit_rules)
        _style_button(self.btn_rules, "#e2e6ef", SUBTEXT, "#d2d8e5", bold=False)
        self.btn_rules.pack(side=tk.LEFT, padx=(16, 0))

        self.btn_rename = tk.Button(btn_row, text="⑥ 批量重命名\n（一次改一批）",
                                    command=self.open_rename)
        _style_button(self.btn_rename, "#e2e6ef", SUBTEXT, "#d2d8e5", bold=False)
        self.btn_rename.pack(side=tk.LEFT, padx=(8, 0))

        # ===== 状态栏 =====
        self.status_var = tk.StringVar(
            value=("请选择一个文件夹（或直接把它拖进窗口）" if HAS_DND
                   else "请先选择要整理的文件夹"))
        status = tk.Label(self.root, textvariable=self.status_var,
                          bg="#e5e9f2", fg=SUBTEXT, anchor=tk.W,
                          font=_font(9), padx=14, pady=7)
        status.pack(fill=tk.X, side=tk.BOTTOM)

        # 拖拽支持：整个窗口都接受拖入
        if HAS_DND and hasattr(self.root, "drop_target_register"):
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", self._on_drop)

    # ---------- 四个功能 ----------

    def choose_folder(self):
        """① 选择文件夹（带安全检查）。"""
        folder = filedialog.askdirectory(title="选择要整理的文件夹")
        if folder:
            self._set_folder(folder)

    def _set_folder(self, folder: str):
        """共用入口：对话框选择 和 拖拽进来 都走这里（带安全检查）。"""
        ok, reason = core.is_safe_folder(folder)
        if not ok:
            messagebox.showwarning("安全拦截", f"这个文件夹不允许整理：\n\n{reason}")
            return
        self.folder = folder
        self.folder_var.set(folder)
        self.plan = []
        self.tree.delete(*self.tree.get_children())
        self.btn_scan.config(state=tk.NORMAL)
        self.btn_run.config(state=tk.DISABLED)
        self.btn_undo.config(
            state=tk.NORMAL if core.latest_log(folder) else tk.DISABLED)
        self.status_var.set("文件夹已选择，点「② 扫描预览」查看整理方案"
                            + ("（也可以直接把文件/文件夹拖进窗口）"
                               if HAS_DND else ""))

    def _on_drop(self, event):
        """拖拽放下的回调：取第一个拖进来的路径（文件取其所在文件夹）。"""
        data = event.data.strip()
        if not data:
            return
        # Windows 拖来的路径：含空格时会带花括号 {}，此时用 splitlist 拆分；
        # 不带花括号的普通路径不能走 splitlist（反斜杠会被当转义符弄坏）
        if data.startswith("{"):
            try:
                paths = self.root.tk.splitlist(data)
            except tk.TclError:
                paths = [data]
        else:
            paths = [data]
        if not paths:
            return
        p = Path(paths[0])
        folder = str(p if p.is_dir() else p.parent)
        self._set_folder(folder)

    def do_scan(self):
        """② 扫描预览：只生成计划，不改任何文件。"""
        if not self.folder:
            return
        mode = self.mode_var.get()
        recursive = self.recursive_var.get()
        self.plan = core.build_plan(self.folder, rules=core.load_rules(),
                                    mode=mode, recursive=recursive)

        mode_name = "类型" if mode == "type" else "修改月份"
        self.tree.delete(*self.tree.get_children())
        for i, act in enumerate(self.plan):
            suffix = ("." + act["file"].rsplit(".", 1)[-1]) if "." in act["file"] else "（无）"
            status_text = {"OK": "✔ 将移动",
                           "CONFLICT": "⚠ 同名冲突",
                           "SKIP": "— 跳过"}[act["status"]]
            tag = {"OK": "ok", "CONFLICT": "conflict", "SKIP": "skip"}[act["status"]]
            self.tree.insert("", tk.END, iid=str(i), tags=(tag,),
                             values=(act["file"], suffix, act["action"], status_text))

        n_ok = sum(1 for a in self.plan if a["status"] == "OK")
        n_conflict = sum(1 for a in self.plan if a["status"] == "CONFLICT")
        n_skip = sum(1 for a in self.plan if a["status"] == "SKIP")
        self.btn_run.config(state=tk.NORMAL if n_ok else tk.DISABLED)
        self.status_var.set(
            f"扫描完成（按{mode_name}整理）：{len(self.plan)} 个文件 —— 将移动 {n_ok}，"
            f"冲突 {n_conflict}，跳过 {n_skip}。确认没问题后点「③ 执行整理」")

    def do_execute(self):
        """③ 执行整理：先弹窗确认，再真正移动文件。"""
        if not self.plan:
            return
        n_ok = sum(1 for a in self.plan if a["status"] == "OK")
        answer = messagebox.askyesno(
            "执行前确认",
            f"即将把 {n_ok} 个文件移入分类子文件夹。\n\n"
            f"文件夹：{self.folder}\n\n"
            f"冲突和跳过的文件不会被碰。移动完成后可以用「④ 撤销上次」恢复。\n\n确定执行吗？")
        if not answer:
            self.status_var.set("已取消，未做任何修改")
            return

        records = core.execute_plan(self.folder, self.plan)
        moved = [r for r in records if r["operation"] == "move"]
        log_file, report_file = core.write_log(
            self.folder, records, note="用户在界面确认后执行")

        self.btn_undo.config(state=tk.NORMAL)
        messagebox.showinfo(
            "整理完成",
            f"成功移动 {len(moved)} 个文件。\n\n"
            f"整理报告已保存到：\n{report_file}\n\n"
            f"如需恢复原状，点「④ 撤销上次」即可。")
        self.status_var.set(f"整理完成：移动 {len(moved)} 个文件。报告见 _工作台记录 文件夹")

        # 重新扫描显示最新状态
        self.do_scan()

    def do_undo(self):
        """④ 撤销上次：根据日志把文件搬回原位。"""
        if not self.folder:
            return
        log_file = core.latest_log(self.folder)
        if not log_file:
            messagebox.showinfo("没有可撤销的记录", "这个文件夹里还没有整理记录。")
            return

        answer = messagebox.askyesno(
            "撤销确认",
            f"将根据这份记录把文件恢复到整理前的位置：\n\n{log_file.name}\n\n确定撤销吗？")
        if not answer:
            return

        restored, errors, removed_dirs = core.undo_from_log(log_file)
        msg = f"成功恢复 {restored} 个文件到原位置。"
        if removed_dirs:
            msg += f"\n\n清理了 {len(removed_dirs)} 个空文件夹：" + "、".join(
                Path(d).name for d in removed_dirs)
        if errors:
            msg += "\n\n以下文件没能恢复：\n" + "\n".join(errors)
        messagebox.showinfo("撤销完成", msg)
        self.status_var.set(f"撤销完成：恢复 {restored} 个文件")
        self.do_scan()

    # ---------- 规则管理 ----------

    def edit_rules(self):
        """⑤ 规则管理：打开一个小窗口编辑分类规则，保存后下次扫描生效。"""
        win = tk.Toplevel(self.root)
        win.title("分类规则管理")
        win.geometry("540x480")
        win.transient(self.root)
        win.configure(bg=CARD)

        tk.Label(
            win,
            text="每行一条规则，格式：类别名称: .扩展名1 .扩展名2\n"
                 "例如：图片: .jpg .png    （保存后，下次「扫描预览」生效）",
            bg=CARD, fg=SUBTEXT, font=_font(9), justify=tk.LEFT, padx=12, pady=10,
        ).pack(anchor=tk.W)

        text = tk.Text(win, wrap=tk.NONE, font=("Consolas", 11),
                       bg="#f6f8fc", fg=TEXT, relief="flat",
                       highlightthickness=1, highlightcolor=ACCENT,
                       highlightbackground=BORDER)
        text.pack(fill=tk.BOTH, expand=True, padx=12)
        text.insert("1.0", core.rules_to_text(core.load_rules()))

        btns = tk.Frame(win, bg=CARD, padx=12, pady=10)
        btns.pack(fill=tk.X)

        def on_save():
            try:
                rules = core.parse_rules_text(text.get("1.0", tk.END))
            except ValueError as e:
                messagebox.showerror("格式错误", str(e), parent=win)
                return
            core.save_rules(rules)
            messagebox.showinfo("已保存", "规则已保存，下次「扫描预览」时生效。", parent=win)
            win.destroy()

        def on_default():
            text.delete("1.0", tk.END)
            text.insert("1.0", core.rules_to_text(core.DEFAULT_RULES))

        btn_cancel = tk.Button(btns, text="取消", command=win.destroy)
        _style_button(btn_cancel, "#e2e6ef", SUBTEXT, "#d2d8e5", bold=False)
        btn_cancel.pack(side=tk.RIGHT)

        btn_default = tk.Button(btns, text="恢复默认规则", command=on_default)
        _style_button(btn_default, ACCENT_SOFT, ACCENT, "#d3e0fa")
        btn_default.pack(side=tk.RIGHT, padx=8)

        btn_save = tk.Button(btns, text="保存", command=on_save)
        _style_button(btn_save, ACCENT, "#ffffff", ACCENT_HOVER)
        btn_save.pack(side=tk.RIGHT)

    # ---------- 批量重命名（v0.1.5） ----------

    def open_rename(self):
        """⑥ 批量重命名：选文件 → 选方式 → 预览 → 确认执行。"""
        if not self.folder:
            messagebox.showinfo("请先选择文件夹", "先在主窗口点「① 选择文件夹」，再来改名。")
            return
        folder = Path(self.folder)

        # 列出第一层里"可改名"的文件（不含记录目录和隐藏文件）
        files = sorted(p.name for p in folder.iterdir()
                       if p.is_file() and not p.name.startswith(".")
                       and p.name != core.RULES_FILE.name)

        win = tk.Toplevel(self.root)
        win.title("批量重命名")
        win.geometry("580x560")
        win.transient(self.root)
        win.configure(bg=CARD)

        tk.Label(win, text=f"当前文件夹：{folder}（点「刷新」可重新加载文件列表）",
                 bg=CARD, fg=SUBTEXT, font=_font(9), padx=12, pady=10,
                 wraplength=550, justify=tk.LEFT).pack(anchor=tk.W)

        # 左：可选文件列表（可多选）；右：预览结果
        lists = tk.Frame(win, bg=CARD, padx=12)
        lists.pack(fill=tk.BOTH, expand=True)

        tk.Label(lists, text="要改名的文件（按住 Ctrl 点选多个）：",
                 bg=CARD, fg=TEXT, font=_font(9, True)).pack(anchor=tk.W)
        src_list = tk.Listbox(lists, selectmode=tk.EXTENDED, height=8,
                              exportselection=False, font=_font(10),
                              bg="#f6f8fc", fg=TEXT, relief="flat",
                              highlightthickness=1, highlightcolor=ACCENT,
                              highlightbackground=BORDER, activestyle="none")
        src_list.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        for f in files:
            src_list.insert(tk.END, f)

        tk.Label(lists, text="改名方式：", bg=CARD, fg=TEXT,
                 font=_font(10), padx=(0, 0), pady=(10, 0)).pack(anchor=tk.W)
        opts = tk.Frame(lists, bg=CARD)
        opts.pack(anchor=tk.W, pady=(2, 0))
        rmode = tk.StringVar(value="serial")
        ttk.Radiobutton(opts, text="加序号", variable=rmode,
                        value="serial").pack(side=tk.LEFT)
        ttk.Radiobutton(opts, text="查找替换", variable=rmode,
                        value="replace").pack(side=tk.LEFT, padx=(10, 0))

        params = tk.Frame(lists, bg=CARD)
        params.pack(anchor=tk.W, pady=6)
        tk.Label(params, text="前缀：", bg=CARD, fg=TEXT,
                 font=_font(10)).pack(side=tk.LEFT)

        def _mini_entry(parent, var, width):
            e = tk.Entry(parent, textvariable=var, width=width,
                         bg="#f6f8fc", fg=TEXT, relief="flat", font=_font(10),
                         highlightthickness=1, highlightcolor=ACCENT,
                         highlightbackground=BORDER)
            e.pack(side=tk.LEFT, ipady=3)
            return e

        prefix_var = tk.StringVar(value="照片-")
        _mini_entry(params, prefix_var, 14)
        tk.Label(params, text="   查找：", bg=CARD, fg=TEXT,
                 font=_font(10)).pack(side=tk.LEFT)
        find_var = tk.StringVar()
        _mini_entry(params, find_var, 10)
        tk.Label(params, text="→替换为：", bg=CARD, fg=TEXT,
                 font=_font(10)).pack(side=tk.LEFT)
        replace_var = tk.StringVar()
        _mini_entry(params, replace_var, 10)

        preview = tk.Listbox(lists, height=8, exportselection=False,
                             font=_font(10), bg="#f6f8fc", fg=TEXT, relief="flat",
                             highlightthickness=1, highlightcolor=ACCENT,
                             highlightbackground=BORDER, activestyle="none")
        preview.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        state = {"plan": []}

        def do_preview():
            sel = [src_list.get(i) for i in src_list.curselection()]
            if not sel:
                messagebox.showinfo("没选文件", "先在上方列表里选中要改名的文件（可多选）。",
                                    parent=win)
                return
            mode = rmode.get()
            if mode == "serial":
                state["plan"] = core.build_rename_plan(
                    folder, sel, mode="serial", prefix=prefix_var.get())
            else:
                state["plan"] = core.build_rename_plan(
                    folder, sel, mode="replace",
                    find=find_var.get(), replace=replace_var.get())
            preview.delete(0, tk.END)
            for act in state["plan"]:
                mark = {"OK": "→", "CONFLICT": "✕", "SKIP": "—"}[act["status"]]
                preview.insert(tk.END, f"{act['file']}  {mark}  {act['action']}")
            n_ok = sum(1 for a in state["plan"] if a["status"] == "OK")
            btn_run.config(state=tk.NORMAL if n_ok else tk.DISABLED)

        def do_run():
            plan = state["plan"]
            n_ok = sum(1 for a in plan if a["status"] == "OK")
            if n_ok == 0:
                return
            answer = messagebox.askyesno(
                "改名前确认",
                f"即将把 {n_ok} 个文件改名（同目录内）。\n\n"
                f"冲突和跳过的文件不会被碰。改完可以用主窗口「④ 撤销上次」恢复。\n\n确定执行吗？",
                parent=win)
            if not answer:
                return
            records = core.execute_plan(folder, plan)
            done = [r for r in records if r["operation"] == "rename"]
            _, report_file = core.write_log(folder, records, note="批量重命名")
            self.btn_undo.config(state=tk.NORMAL)
            messagebox.showinfo(
                "改名完成",
                f"成功改名 {len(done)} 个文件。\n\n报告：{report_file}\n\n"
                f"如需恢复，回主窗口点「④ 撤销上次」。", parent=win)
            win.destroy()
            self.do_scan()

        btns = tk.Frame(lists, bg=CARD, pady=10)
        btns.pack(fill=tk.X)

        btn_preview = tk.Button(btns, text="预览改名", command=do_preview)
        _style_button(btn_preview, ACCENT_SOFT, ACCENT, "#d3e0fa")
        btn_preview.pack(side=tk.LEFT)

        btn_run = tk.Button(btns, text="确认改名", command=do_run,
                            state=tk.DISABLED)
        _style_button(btn_run, ACCENT, "#ffffff", ACCENT_HOVER)
        btn_run.pack(side=tk.LEFT, padx=8)

        btn_close = tk.Button(btns, text="关闭", command=win.destroy)
        _style_button(btn_close, "#e2e6ef", SUBTEXT, "#d2d8e5", bold=False)
        btn_close.pack(side=tk.RIGHT)


def main():
    root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
    WorkbenchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

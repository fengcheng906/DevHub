# -*- coding: utf-8 -*-
"""
智能文件工作台 v0.1 —— 图形界面
项目：AI 个人工作室操作系统（AI Personal Studio OS）

怎么打开这个软件：
    双击本文件，或在命令行里运行：python app.py

界面共 4 个按钮，从左到右按顺序用就行：
    ① 选择文件夹  ② 扫描预览  ③ 执行整理  ④ 撤销上次
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

import core


class WorkbenchApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.folder = None      # 当前选择的文件夹
        self.plan = []          # 最近一次生成的整理计划

        root.title(f"{core.APP_NAME} v{core.APP_VERSION}")
        root.geometry("880x560")
        root.minsize(760, 480)

        self._build_ui()

    # ---------- 界面搭建 ----------

    def _build_ui(self):
        # 顶部：文件夹选择
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="目标文件夹：").pack(side=tk.LEFT)
        self.folder_var = tk.StringVar(value="（还没有选择文件夹）")
        ttk.Entry(top, textvariable=self.folder_var, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(top, text="① 选择文件夹", command=self.choose_folder).pack(side=tk.LEFT)

        # 中部：预览表格
        mid = ttk.Frame(self.root, padding=(10, 0))
        mid.pack(fill=tk.BOTH, expand=True)

        columns = ("file", "type", "action", "status")
        self.tree = ttk.Treeview(mid, columns=columns, show="headings", height=18)
        self.tree.heading("file", text="文件名")
        self.tree.heading("type", text="类型")
        self.tree.heading("action", text="整理动作（预览）")
        self.tree.heading("status", text="状态")
        self.tree.column("file", width=230)
        self.tree.column("type", width=90, anchor=tk.CENTER)
        self.tree.column("action", width=330)
        self.tree.column("status", width=110, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(mid, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 不同状态用不同颜色区分
        self.tree.tag_configure("ok", foreground="#0a7d32")        # 绿：将移动
        self.tree.tag_configure("conflict", foreground="#c26600")  # 橙：冲突
        self.tree.tag_configure("skip", foreground="#888888")     # 灰：跳过

        # 底部：操作按钮 + 状态栏
        bottom = ttk.Frame(self.root, padding=10)
        bottom.pack(fill=tk.X)

        self.btn_scan = ttk.Button(bottom, text="② 扫描预览", command=self.do_scan,
                                   state=tk.DISABLED)
        self.btn_scan.pack(side=tk.LEFT, padx=(0, 6))
        self.btn_run = ttk.Button(bottom, text="③ 执行整理", command=self.do_execute,
                                  state=tk.DISABLED)
        self.btn_run.pack(side=tk.LEFT, padx=(0, 6))
        self.btn_undo = ttk.Button(bottom, text="④ 撤销上次", command=self.do_undo,
                                   state=tk.DISABLED)
        self.btn_undo.pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="请先选择要整理的文件夹")
        ttk.Label(self.root, textvariable=self.status_var, padding=(10, 4),
                  foreground="#555555").pack(fill=tk.X)

    # ---------- 四个功能 ----------

    def choose_folder(self):
        """① 选择文件夹（带安全检查）。"""
        folder = filedialog.askdirectory(title="选择要整理的文件夹")
        if not folder:
            return
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
        self.status_var.set("文件夹已选择，点「② 扫描预览」查看整理方案")

    def do_scan(self):
        """② 扫描预览：只生成计划，不改任何文件。"""
        if not self.folder:
            return
        self.plan = core.build_plan(self.folder)

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
            f"扫描完成：{len(self.plan)} 个文件 —— 将移动 {n_ok}，冲突 {n_conflict}，跳过 {n_skip}。"
            f"确认没问题后点「③ 执行整理」")

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


def main():
    root = tk.Tk()
    WorkbenchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

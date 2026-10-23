"""Run from any working directory: python examples/tkinter/demo.py.

Only Python's standard library and Tcl/Tk are needed. No files are processed.
SPDX-License-Identifier: AGPL-3.0-only
"""

from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk

REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY / "components" / "tkinter"))

from ui_center import ActionBar, TaskPanel, apply_theme, load_tokens


class DemoWindow:
    def __init__(self, root, *, tokens_path=None, interval_ms=240, theme_variable=None, font_scale=1.0):
        self.root = root
        self.tokens_path = tokens_path
        self.interval_ms = interval_ms
        self._pending = None
        self._closed = False
        self.completed = self.total = 0
        self.rows = []
        self.busy = self.cancelling = False
        tokens = load_tokens(tokens_path)
        self.gap = tokens["spacing"]
        self.theme = theme_variable if theme_variable is not None else tk.StringVar(master=root, value="light")
        self.project = tk.StringVar(master=root, value="演示资料")
        self.amount = tk.StringVar(master=root, value="12")
        self.outcome = tk.StringVar(master=root, value="正常完成")
        self.font_scale = font_scale
        apply_theme(root, self.theme.get(), tokens_path=tokens_path, font_scale=self.font_scale)
        root.title("UI_Center · 桌面组件示例")
        root.geometry("760x650")
        root.minsize(580, 570)
        outer = ttk.Frame(root, padding=self.gap["lg"])
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(4, weight=1)
        header = ttk.Frame(outer)
        header.grid(row=0, column=0, sticky="ew", pady=(0, self.gap["sm"]))
        ttk.Label(header, text="任务与结果", style="UIC.Heading.TLabel").pack(side="left")
        self.theme_picker = ttk.Combobox(header, textvariable=self.theme, state="readonly",
                                        values=("light", "dark"), width=8, takefocus=True)
        self.theme_picker.pack(side="right")
        ttk.Label(header, text="主题 ", style="UIC.Muted.TLabel").pack(side="right")
        self.theme_picker.bind("<<ComboboxSelected>>", self.change_theme)
        introduction = ttk.Label(outer, text="演示：主次操作、任务取消、结果反馈和明暗主题。不会读写你的文件。",
                                 style="UIC.Muted.TLabel", wraplength=700)
        introduction.grid(row=1, column=0, sticky="ew", pady=(0, self.gap["md"]))
        introduction.bind("<Configure>", lambda event: introduction.configure(wraplength=max(100, event.width)))
        form = ttk.LabelFrame(outer, text="演示参数", padding=self.gap["md"])
        form.grid(row=2, column=0, sticky="ew", pady=(0, self.gap["md"]))
        form.columnconfigure(1, weight=1)
        self.inputs = []
        for row, (label, variable) in enumerate((("项目名称", self.project), ("项目数量（1–50）", self.amount))):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", padx=(0, self.gap["md"]), pady=self.gap["xs"])
            control = ttk.Entry(form, textvariable=variable, takefocus=True)
            control.grid(row=row, column=1, sticky="ew", pady=self.gap["xs"])
            self.inputs.append(control)
        ttk.Label(form, text="任务结果").grid(row=2, column=0, sticky="w", padx=(0, self.gap["md"]), pady=self.gap["xs"])
        choice = ttk.Combobox(form, textvariable=self.outcome, state="readonly", takefocus=True,
                              values=("正常完成", "模拟失败"))
        choice.grid(row=2, column=1, sticky="ew", pady=self.gap["xs"])
        self.inputs.append(choice)
        self.actions = ActionBar(outer, on_primary=self.start, on_cancel=self.cancel,
                                 on_secondary=self.reset, secondary_text="重置演示", spacing=self.gap)
        self.actions.grid(row=3, column=0, sticky="ew", pady=(0, self.gap["md"]))
        self.panel = TaskPanel(outer, spacing=self.gap)
        self.panel.grid(row=4, column=0, sticky="nsew")
        self.panel.set_state("idle", message="选择参数后开始；所有结果均为虚构数据。")
        self.footer = ttk.Label(outer, text="Tab / Shift+Tab 移动焦点；空格激活按钮。示例任务在下一步检查取消请求。",
                                style="UIC.Muted.TLabel", wraplength=700)
        self.footer.grid(row=5, column=0, sticky="ew", pady=(self.gap["sm"], 0))
        self.footer.bind("<Configure>", lambda event: self.footer.configure(wraplength=max(100, event.width)))
        self.inputs[0].focus_set()
        root.protocol("WM_DELETE_WINDOW", self.close)

    def change_theme(self, _event=None):
        apply_theme(self.root, self.theme.get(), tokens_path=self.tokens_path, font_scale=self.font_scale)

    def _set_busy(self, busy):
        self.busy = busy
        self.actions.set_busy(busy, cancelling=self.cancelling)
        for widget in self.inputs:
            if isinstance(widget, ttk.Combobox):
                widget.configure(state="disabled" if busy else "readonly")
            else:
                widget.state(["disabled" if busy else "!disabled"])

    def start(self):
        if self.busy:
            return
        try:
            total = int(self.amount.get())
        except ValueError:
            total = 0
        if not 1 <= total <= 50 or not self.project.get().strip():
            self.panel.set_state("error", message="请输入项目名称，以及 1–50 之间的整数数量。")
            self.inputs[0 if not self.project.get().strip() else 1].focus_set()
            return
        self.total, self.completed, self.rows = total, 0, []
        self.cancelling = False
        self._set_busy(True)
        self.panel.set_state("running", completed=0, total=total, message="正在模拟处理；可随时请求取消。", results=[])
        self.actions.cancel.focus_set()
        self._pending = self.root.after(self.interval_ms, self._tick)

    def _tick(self):
        self._pending = None
        if self._closed:
            return
        if self.cancelling:
            self._finish("cancelled", f"已取消；保留 {self.completed} 项已完成的演示结果。")
            return
        name = f"{self.project.get().strip()} · 项目 {self.completed + 1:02d}"
        if self.outcome.get() == "模拟失败" and self.completed == min(2, self.total - 1):
            self.rows.append((name, "失败（演示）"))
            self._finish("error", "演示任务失败：模拟输入不可用。可以修改参数后重试。")
            return
        self.completed += 1
        self.rows.append((name, "已完成（演示）"))
        if self.completed == self.total:
            self._finish("completed", f"{self.total} 项演示任务已完成；未创建或修改任何业务文件。")
        else:
            self.panel.set_state("running", completed=self.completed, total=self.total,
                                 message=f"正在处理下一项，共 {self.total} 项。", results=self.rows)
            self._pending = self.root.after(self.interval_ms, self._tick)

    def cancel(self):
        if self.busy and not self.cancelling:
            self.cancelling = True
            self.actions.set_busy(True, cancelling=True)
            self.panel.set_state("cancelling", completed=self.completed, total=self.total,
                                 message="已收到取消请求，正在结束当前模拟步骤。")

    def _finish(self, state, message):
        self.panel.set_state(state, completed=self.completed, total=self.total, message=message, results=self.rows)
        self.cancelling = False
        self._set_busy(False)
        self.actions.primary.focus_set()

    def reset(self):
        if self.busy:
            return
        self.rows = []
        self.completed = self.total = 0
        self.panel.set_state("idle", message="已重置演示。选择参数后开始；所有结果均为虚构数据。", results=[])
        self.inputs[0].focus_set()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._pending is not None:
            self.root.after_cancel(self._pending)
            self._pending = None
        self.root.destroy()


if __name__ == "__main__":
    window = tk.Tk()
    DemoWindow(window)
    window.mainloop()

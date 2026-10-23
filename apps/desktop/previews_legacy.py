"""Separate embedded previews for the original theme, actions and task APIs.

Only these demonstrations simulate work; reusable widgets remain state-only.
SPDX-License-Identifier: AGPL-3.0-only
"""

import tkinter as tk
from tkinter import ttk

from ui_center.widgets import ActionBar, TaskPanel

from .preview_base import PreviewView, example_code


IDS = ("legacy-theme", "legacy-actions", "legacy-task")


class ThemePreview(PreviewView):
    def __init__(self, master, *, palette, reduced_motion=False):
        super().__init__(master, palette=palette, reduced_motion=reduced_motion)
        self.title = tk.StringVar(self, value="主题示例")
        self.input_text = tk.StringVar(self, value="主题切换保留输入")
        self.disabled = tk.BooleanVar(self, value=False)
        self.feedback = tk.StringVar(self, value="可使用Tab切换焦点，空格触发按钮。")
        ttk.Label(self.controls, text="标题").grid(row=0, column=0, padx=(0, 6))
        title_entry = ttk.Entry(self.controls, textvariable=self.title, width=22)
        title_entry.grid(row=0, column=1, sticky="w")
        title_entry.bind("<KeyRelease>", lambda event: self.heading.configure(text=self.title.get()))
        ttk.Checkbutton(self.controls, text="禁用主按钮", variable=self.disabled,
                        command=self._state).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.stage.columnconfigure(0, weight=1)
        self.heading = ttk.Label(self.stage, text=self.title.get(), style="UIC.Heading.TLabel")
        self.heading.grid(row=0, column=0, sticky="w", pady=(12, 16))
        ttk.Label(self.stage, text="真实的ttk输入框与按钮使用同一份主题参数。").grid(row=1, column=0, sticky="w")
        self.entry = ttk.Entry(self.stage, textvariable=self.input_text)
        self.entry.grid(row=2, column=0, sticky="ew", pady=12)
        self.button = ttk.Button(self.stage, text="使用当前输入", style="UIC.Primary.TButton",
                                 command=lambda: self.feedback.set("收到：" + self.input_text.get()))
        self.button.grid(row=3, column=0, sticky="w")
        self.feedback_label = ttk.Label(self.stage, textvariable=self.feedback, wraplength=420,
                                        style="UIC.Muted.TLabel")
        self.feedback_label.grid(row=4, column=0, sticky="ew", pady=16)
        self.stage.bind("<Configure>", lambda event: self.feedback_label.configure(wraplength=max(100, event.width - 12)))
        self.message.set("颜色和字号由工作台设置统一切换；输入、焦点和禁用状态由原生控件保留。")

    def _state(self):
        self.button.state(["disabled"] if self.disabled.get() else ["!disabled"])

    def reset(self):
        self.title.set("主题示例")
        self.input_text.set("主题切换保留输入")
        self.disabled.set(False)
        self.feedback.set("可使用Tab切换焦点，空格触发按钮。")
        self.heading.configure(text=self.title.get())
        self._state()

    def code(self):
        body = (f"ttk.Label(root, text={self.title.get()!r}, style='UIC.Heading.TLabel').pack(padx=20, pady=12)\n"
                f"value = tk.StringVar(root, value={self.input_text.get()!r})\n"
                "ttk.Entry(root, textvariable=value).pack(fill='x', padx=20, pady=12)\n"
                f"feedback = tk.StringVar(root, value={self.feedback.get()!r})\n"
                "button = ttk.Button(root, text='使用当前输入', style='UIC.Primary.TButton',\n"
                "                    command=lambda: feedback.set('收到：' + value.get()))\n"
                "button.pack(pady=12)\n"
                f"button.state({['disabled'] if self.disabled.get() else ['!disabled']!r})\n"
                "ttk.Label(root, textvariable=feedback, wraplength=520).pack(padx=20, pady=12)\n")
        return example_code("", body)


class ActionsPreview(PreviewView):
    def __init__(self, master, *, palette, reduced_motion=False, spacing=None):
        super().__init__(master, palette=palette, reduced_motion=reduced_motion)
        self.primary_text = tk.StringVar(self, value="开始任务")
        self.amount = tk.StringVar(self, value="8")
        self.busy, self.cancelling = False, False
        self.completed, self.total = 0, 0
        self.detail = tk.StringVar(self, value="点击开始，观察主动作、重置与取消的状态。")
        ttk.Label(self.controls, text="主按钮").grid(row=0, column=0, padx=(0, 6))
        entry = ttk.Entry(self.controls, textvariable=self.primary_text, width=18)
        entry.grid(row=0, column=1, sticky="w")
        entry.bind("<KeyRelease>", lambda event: self.actions.primary.configure(text=self.primary_text.get()))
        ttk.Label(self.controls, text="模拟数量").grid(row=1, column=0, padx=(0, 6), pady=(8, 0))
        ttk.Combobox(self.controls, textvariable=self.amount, values=("4", "8", "12"),
                     width=8, state="readonly").grid(row=1, column=1, sticky="w", pady=(8, 0))
        self.stage.columnconfigure(0, weight=1)
        self.actions = self.register(ActionBar(self.stage, on_primary=self.start,
                                               on_cancel=self.cancel, on_secondary=self.reset,
                                               spacing=spacing))
        self.actions.grid(row=0, column=0, sticky="ew", pady=(20, 16))
        self.detail_label = ttk.Label(self.stage, textvariable=self.detail, wraplength=440)
        self.detail_label.grid(row=1, column=0, sticky="ew")
        self.stage.bind("<Configure>", lambda event: self.detail_label.configure(wraplength=max(100, event.width - 12)))
        self.message.set("ActionBar只发出回调；本预览提供可取消的虚构任务。")

    def start(self):
        if self.busy:
            return
        self.cancel_task()
        self.busy, self.cancelling = True, False
        self.completed, self.total = 0, int(self.amount.get())
        self.actions.set_busy(True)
        self.detail.set(f"模拟处理中：0 / {self.total}；可取消。")
        self.schedule(250, self._advance)

    def _advance(self):
        self.completed += 1
        self.detail.set(f"模拟处理中：{self.completed} / {self.total}；可取消。")
        if self.completed < self.total:
            self.schedule(250, self._advance)
        else:
            self.busy = False
            self.actions.set_busy(False)
            self.detail.set(f"模拟任务完成：{self.completed} / {self.total}；已恢复操作。")

    def cancel(self):
        if not self.busy or self.cancelling:
            return
        self.cancelling = True
        self.actions.set_busy(True, cancelling=True)
        self.detail.set("正在等待模拟任务确认取消；已完成数量保留。")
        self.schedule(100, self._finish_cancel)

    def _finish_cancel(self):
        self.busy, self.cancelling = False, False
        self.actions.set_busy(False)
        self.detail.set(f"已取消：保留 {self.completed} / {self.total} 项。")

    def reset(self):
        self.cancel_task()
        self.busy, self.cancelling = False, False
        self.completed, self.total = 0, 0
        self.primary_text.set("开始任务")
        self.amount.set("8")
        self.actions.primary.configure(text=self.primary_text.get())
        self.actions.set_busy(False)
        self.detail.set("点击开始，观察主动作、重置与取消的状态。")

    def code(self):
        body = ("status = tk.StringVar(root, value='ActionBar只发出回调，由调用方处理任务')\n"
                "def start():\n    actions.set_busy(True)\n    status.set('请由业务完成回调恢复 actions.set_busy(False)')\n\n"
                "def cancel():\n    actions.set_busy(True, cancelling=True)\n    status.set('请由业务确认取消后恢复 actions.set_busy(False)')\n\n"
                "actions = ActionBar(root, on_primary=start, on_cancel=cancel,\n"
                f"                    on_secondary=lambda: status.set('已重置'), primary_text={self.primary_text.get()!r})\n"
                "actions.pack(fill='x', padx=20, pady=20)\n"
                f"actions.set_busy({self.busy!r}, cancelling={self.cancelling!r})\n"
                "ttk.Label(root, textvariable=status, wraplength=520).pack(padx=20, pady=12)\n")
        return example_code("from ui_center import ActionBar", body)


class TaskPreview(PreviewView):
    def __init__(self, master, *, palette, reduced_motion=False, spacing=None):
        super().__init__(master, palette=palette, reduced_motion=reduced_motion)
        self.amount = tk.StringVar(self, value="8")
        self.outcome = tk.StringVar(self, value="成功")
        self.busy, self.cancelling = False, False
        self.completed, self.total = 0, 0
        self.rows = []
        self._outcome = "成功"
        parameters = ttk.Frame(self.controls)
        parameters.grid(row=0, column=0, sticky="w")
        ttk.Label(parameters, text="数量").grid(row=0, column=0)
        ttk.Combobox(parameters, textvariable=self.amount, values=("4", "8", "12"),
                     state="readonly", width=7).grid(row=0, column=1, padx=6)
        ttk.Label(parameters, text="结果").grid(row=0, column=2)
        ttk.Combobox(parameters, textvariable=self.outcome, values=("成功", "失败"),
                     state="readonly", width=7).grid(row=0, column=3, padx=6)
        self.actions = self.register(ActionBar(self.controls, on_primary=self.start,
                                               on_cancel=self.cancel, on_secondary=self.reset,
                                               spacing=spacing))
        self.actions.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.controls.columnconfigure(0, weight=1)
        self.stage.columnconfigure(0, weight=1)
        self.stage.rowconfigure(0, weight=1)
        self.panel = self.register(TaskPanel(self.stage, spacing=spacing))
        self.panel.grid(row=0, column=0, sticky="nsew")
        self.message.set("虚构任务支持完成、取消和失败；主题切换保留进度、参数与结果。")

    def start(self):
        if self.busy:
            return
        self.cancel_task()
        self.busy, self.cancelling = True, False
        self.completed, self.total = 0, int(self.amount.get())
        self._outcome = self.outcome.get()
        self.rows = []
        self.actions.set_busy(True)
        self._render("running", "正在处理虚构条目，可取消。")
        self.schedule(250, self._advance)

    def _render(self, state, message):
        self.panel.set_state(state, completed=self.completed, total=self.total,
                             message=message, results=self.rows)

    def _advance(self):
        item = self.completed + 1
        if self._outcome == "失败" and item == max(1, self.total // 2):
            self.rows.append((f"虚构条目 {item}", "模拟失败"))
            self.busy = False
            self.actions.set_busy(False)
            self._render("error", "模拟失败；保留已完成结果，修正参数后可以重试。")
            return
        self.completed += 1
        self.rows.append((f"虚构条目 {item} · 支持保留完整名称", "已完成（模拟）"))
        if self.completed < self.total:
            self._render("running", "模拟处理中；可选择结果行查看完整内容。")
            self.schedule(250, self._advance)
        else:
            self.busy = False
            self.actions.set_busy(False)
            self._render("completed", "模拟任务完成；结果仅用于演示，不处理你的文件。")

    def cancel(self):
        if not self.busy or self.cancelling:
            return
        self.cancelling = True
        self.actions.set_busy(True, cancelling=True)
        self._render("cancelling", "正在等待模拟任务确认取消，已完成结果保留。")
        self.schedule(100, self._finish_cancel)

    def _finish_cancel(self):
        self.busy, self.cancelling = False, False
        self.actions.set_busy(False)
        self._render("cancelled", "已取消；可保留结果并重新开始。")

    def reset(self):
        self.cancel_task()
        self.busy, self.cancelling = False, False
        self.completed, self.total = 0, 0
        self.rows = []
        self.amount.set("8")
        self.outcome.set("成功")
        self.actions.set_busy(False)
        self._render("idle", "任务开始后将在这里显示进度和结果。")

    def code(self):
        body = ("panel = TaskPanel(root)\npanel.pack(fill='both', expand=True, padx=20, pady=20)\n"
                f"panel.set_state({self.panel.task_state!r}, completed={self.completed}, total={self.total},\n"
                f"                message={self.panel.message.get()!r}, results={self.rows!r})\n"
                "# 在消费应用的真实进度/完成/失败/取消回调中调用 panel.set_state(...)。\n")
        return example_code("from ui_center import TaskPanel", body)


def create_preview(key, master, *, palette, reduced_motion=False, spacing=None):
    classes = {"legacy-theme": ThemePreview, "legacy-actions": ActionsPreview,
               "legacy-task": TaskPreview}
    if key not in classes:
        raise ValueError("Unknown legacy preview: " + key)
    options = {"palette": palette, "reduced_motion": reduced_motion}
    if key != "legacy-theme":
        options["spacing"] = spacing
    return classes[key](master, **options)

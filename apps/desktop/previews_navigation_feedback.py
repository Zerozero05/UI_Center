"""Live navigation and feedback examples; all illustrative actions stay here.

SPDX-License-Identifier: AGPL-3.0-only
"""

import tkinter as tk
from tkinter import ttk

from ui_center.navigation import Accordion, SegmentedControl, Tabs
from ui_center.feedback import EmptyState, InlineAlert, Toast
from .preview_base import PreviewView, example_code


IDS = ("tabs", "accordion", "segmented-control", "inline-alert", "toast", "empty-state")
_LONG = "项目设置与很长的中文标签仍然完整换行显示"


class NavigationFeedbackPreview(PreviewView):
    def __init__(self, master, key, *, palette, reduced_motion=False):
        super().__init__(master, palette=palette, reduced_motion=reduced_motion)
        self.key = key
        self.stage.columnconfigure(0, weight=1)
        self.stage.rowconfigure(0, weight=1)
        if key == "tabs":
            self._build_tabs()
        elif key == "accordion":
            self._build_accordion()
        elif key == "segmented-control":
            self._build_segments()
        elif key == "inline-alert":
            self._build_alert()
        elif key == "toast":
            self._build_toast()
        else:
            self._build_empty()

    def _combo(self, column, title, variable, values, callback):
        self.controls.columnconfigure(column, weight=1, uniform="parameters")
        ttk.Label(self.controls, text=title).grid(row=0, column=column, sticky="w", padx=(0, 8))
        combo = ttk.Combobox(self.controls, textvariable=variable, values=values,
                             state="readonly", width=12, takefocus=True)
        combo.grid(row=1, column=column, sticky="ew", padx=(0, 8))
        combo.bind("<<ComboboxSelected>>", callback)
        return combo

    def _check(self, column, title, variable, callback):
        self.controls.columnconfigure(column, weight=1, uniform="parameters")
        ttk.Label(self.controls, text=title).grid(row=0, column=column, sticky="w", padx=(0, 8))
        ttk.Checkbutton(self.controls, text="启用", variable=variable, command=callback,
                        takefocus=True).grid(row=1, column=column, sticky="w")

    def _build_tabs(self):
        self.long_text = tk.BooleanVar(self, False)
        self.disabled = tk.BooleanVar(self, True)
        self._check(0, "长中文标签", self.long_text, self._update_tabs)
        self._check(1, "禁用第三页", self.disabled, self._update_tabs)
        self.widget = self.register(Tabs(self.stage, palette=self.palette,
                                        on_change=lambda key: self.message.set("已切换到：" + key)))
        self.widget.grid(row=0, column=0, sticky="nsew")
        for key, title in (("overview", "概览"), ("settings", "项目设置"), ("history", "历史记录")):
            page = self.widget.add(key, text=title, disabled=key == "history")
            page.columnconfigure(0, weight=1)
            ttk.Label(page, text="此页内容由调用方提供。输入会在切页与切主题后保留。",
                      wraplength=340).grid(row=0, column=0, sticky="w", pady=(0, 8))
            ttk.Entry(page).grid(row=1, column=0, sticky="ew")
        self.message.set("Tab 进入当前页签，方向键切页，跳过禁用页；再次 Tab 进入内容。")

    def _update_tabs(self, _event=None):
        self.widget.set_text("settings", _LONG if self.long_text.get() else "项目设置")
        self.widget.set_disabled("history", self.disabled.get())

    def _build_accordion(self):
        self.mode = tk.StringVar(self, "单项展开")
        self.long_text = tk.BooleanVar(self, False)
        self._combo(0, "展开方式", self.mode, ("单项展开", "多项展开"), self._update_accordion)
        self._check(1, "长中文标题", self.long_text, self._update_accordion)
        self.widget = self.register(Accordion(self.stage, palette=self.palette,
            on_change=lambda keys: self.message.set("展开：" + ("、".join(keys) or "无"))))
        self.widget.grid(row=0, column=0, sticky="new")
        for key, text in (("general", "通用设置"), ("advanced", "高级选项"), ("help", "使用说明")):
            body = self.widget.add(key, text=text, expanded=key == "general")
            body.columnconfigure(0, weight=1)
            ttk.Label(body, text="按需展开的内容由调用方提供，折叠时保留输入。",
                      wraplength=340).grid(row=0, column=0, sticky="w")
            ttk.Entry(body).grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.message.set("空格/Enter 展开或折叠；上下键定位标题，左右键控制展开。")

    def _update_accordion(self, _event=None):
        self.widget.set_multiple(self.mode.get() == "多项展开")
        self.widget.set_text("advanced", _LONG if self.long_text.get() else "高级选项")

    def _build_segments(self):
        self.disabled = tk.BooleanVar(self, True)
        self._check(0, "禁用年度选项", self.disabled, self._update_segments)
        self.current = tk.StringVar(self, "week")
        self._combo(1, "当前值", self.current, ("day", "week", "year"), self._update_segments)
        self.widget = self.register(SegmentedControl(self.stage, palette=self.palette,
            options=(("day", "日"), ("week", "周"), ("year", "年度")), value="week",
            disabled=("year",), on_change=self._segment_changed))
        self.widget.grid(row=0, column=0, sticky="new")
        self.message.set("互斥选项：Tab 聚焦当前值，方向键选择可用项，空格/Enter 激活。")

    def _segment_changed(self, key):
        self.current.set(key)
        self.message.set("调用方收到选择回调：" + key)

    def _update_segments(self, _event=None):
        self.widget.set_disabled("year", self.disabled.get())
        if not self.widget.select(self.current.get()):
            self.current.set(self.widget.select() or "")
            self.message.set("年度选项已禁用，保留可用选择。")

    def _build_alert(self):
        self.kind = tk.StringVar(self, "info")
        self.long_text = tk.BooleanVar(self, False)
        self._combo(0, "语义状态", self.kind, ("info", "success", "warning", "error"), self._update_alert)
        self._check(1, "长错误说明", self.long_text, self._update_alert)
        self.widget = self.register(InlineAlert(self.stage, palette=self.palette, kind="info",
            message="设置尚未保存。确认内容后再继续。", action_text="查看下一步",
            on_action=lambda: self.message.set("调用方处理“查看下一步”；提示仍持续显示。")))
        self.widget.grid(row=0, column=0, sticky="new")
        self.message.set("消息持续显示，可聚焦、选择复制并滚动；重要错误可保留在这里。")

    def _alert_message(self):
        return ("说明：请检查输入与网络状态，已填写的数据会保留。\n" * 12
                if self.long_text.get() else "设置尚未保存。确认内容后再继续。")

    def _update_alert(self, _event=None):
        self.widget.set_message(self._alert_message(), kind=self.kind.get())

    def _build_toast(self):
        self.kind = tk.StringVar(self, "success")
        self.duration = tk.StringVar(self, "4000")
        self._combo(0, "语义状态", self.kind, ("info", "success", "warning", "error"), lambda e: None)
        self._combo(1, "关闭时间(ms)", self.duration, ("1500", "4000", "0"), lambda e: None)
        ttk.Label(self.controls, text="再次触发").grid(row=0, column=2, sticky="w")
        ttk.Button(self.controls, text="显示提示", command=self._show_toast,
                   takefocus=True).grid(row=1, column=2, sticky="ew")
        self.controls.columnconfigure(2, weight=1, uniform="parameters")
        self.widget = self.register(Toast(self.stage, palette=self.palette, message="演示设置已保存。",
            kind="success", duration=4000,
            on_close=lambda reason: self.message.set("轻提示已关闭：" + reason)))
        self.widget.grid(row=0, column=0, sticky="new")
        self._show_toast()

    def _show_toast(self):
        self.widget.show("演示设置已保存。", kind=self.kind.get(), duration=int(self.duration.get()))
        self.message.set("悬停或将焦点移入关闭按钮可暂停计时；0 表示手动关闭。重要错误应使用持续提示。")

    def _build_empty(self):
        self.kind = tk.StringVar(self, "first-use")
        self._combo(0, "空状态原因", self.kind, ("first-use", "no-results", "no-data"), self._update_empty)
        self.disabled = tk.BooleanVar(self, False)
        self._check(1, "禁用操作", self.disabled, self._update_empty)
        self.widget = self.register(EmptyState(self.stage, palette=self.palette,
            on_action=lambda: self.message.set("调用方收到操作：" + self.widget.action_text)))
        self.widget.grid(row=0, column=0, sticky="new")
        self.message.set("首次使用、搜索无结果、暂时无数据各有明确说明和下一步。")

    def _update_empty(self, _event=None):
        self.widget.set_state(self.kind.get())
        self.widget.action.state(["disabled" if self.disabled.get() else "!disabled"])

    def reset(self):
        if self.key == "tabs":
            self.long_text.set(False)
            self.disabled.set(True)
            self._update_tabs()
            self.widget.select("overview")
        elif self.key == "accordion":
            self.mode.set("单项展开")
            self.long_text.set(False)
            self._update_accordion()
            self.widget.set_expanded("general", True)
        elif self.key == "segmented-control":
            self.disabled.set(True)
            self.current.set("week")
            self._update_segments()
        elif self.key == "inline-alert":
            self.kind.set("info")
            self.long_text.set(False)
            self._update_alert()
        elif self.key == "toast":
            self.kind.set("success")
            self.duration.set("4000")
            self._show_toast()
        else:
            self.kind.set("first-use")
            self.disabled.set(False)
            self._update_empty()

    def code(self):
        if self.key == "tabs":
            return example_code("from ui_center.navigation import Tabs", f'''tabs = Tabs(root, palette=palette, on_change=print)
tabs.pack(fill="both", expand=True, padx=12, pady=12)
for key, text in {[("overview", "概览"), ("settings", _LONG if self.long_text.get() else "项目设置"), ("history", "历史记录")]!r}:
    page = tabs.add(key, text=text, disabled=key == "history" and {self.disabled.get()!r})
    ttk.Label(page, text="调用方提供的页面内容").pack(anchor="w")
    ttk.Entry(page).pack(fill="x", pady=8)
tabs.select({self.widget.select()!r})''')
        if self.key == "accordion":
            return example_code("from ui_center.navigation import Accordion", f'''accordion = Accordion(root, palette=palette, multiple={self.mode.get() == "多项展开"!r}, on_change=print)
accordion.pack(fill="x", padx=12, pady=12)
for key, text in {[("general", "通用设置"), ("advanced", _LONG if self.long_text.get() else "高级选项"), ("help", "使用说明")]!r}:
    body = accordion.add(key, text=text, expanded=key in {self.widget.expanded!r})
    ttk.Label(body, text="折叠时保留此处输入").pack(anchor="w")
    ttk.Entry(body).pack(fill="x", pady=8)''')
        if self.key == "segmented-control":
            return example_code("from ui_center.navigation import SegmentedControl", f'''control = SegmentedControl(root, palette=palette,
    options=(("day", "日"), ("week", "周"), ("year", "年度")),
    value={self.widget.select()!r}, disabled={('year',) if self.disabled.get() else ()!r}, on_change=print)
control.pack(fill="x", padx=12, pady=12)''')
        if self.key == "inline-alert":
            return example_code("from ui_center.feedback import InlineAlert", f'''alert = InlineAlert(root, palette=palette, kind={self.kind.get()!r},
    message={self._alert_message()!r}, action_text="查看下一步", on_action=lambda: print("查看下一步"))
alert.pack(fill="x", padx=12, pady=12)''')
        if self.key == "toast":
            return example_code("from ui_center.feedback import Toast", f'''toast = Toast(root, palette=palette, kind={self.kind.get()!r}, duration={int(self.duration.get())!r},
    message="演示设置已保存。", on_close=print)
toast.pack(fill="x", padx=12, pady=12)
ttk.Button(root, text="再次显示", command=lambda: toast.show()).pack()
toast.show()
root.protocol("WM_DELETE_WINDOW", lambda: (toast.dispose(), root.destroy()))''')
        return example_code("from ui_center.feedback import EmptyState", f'''empty = EmptyState(root, palette=palette, kind={self.kind.get()!r}, on_action=lambda: print("执行下一步"))
empty.pack(fill="x", padx=12, pady=12)
empty.action.state({['disabled'] if self.disabled.get() else ['!disabled']!r})''')


def create_preview(key, master, *, palette, reduced_motion=False):
    if key not in IDS:
        raise KeyError(key)
    return NavigationFeedbackPreview(master, key, palette=palette, reduced_motion=reduced_motion)

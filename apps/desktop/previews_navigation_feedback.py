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
_LENGTHS = ((False, "常规"), (True, "长文本"))
_AVAILABILITY = ((False, "可用"), (True, "禁用"))
_KINDS = (("info", "提示"), ("success", "成功"), ("warning", "警告"), ("error", "错误"))
_PAGES = {"overview": "概览", "settings": "项目设置", "history": "历史记录"}
_SECTIONS = {"general": "通用设置", "advanced": "高级选项", "help": "使用说明"}
_SEGMENTS = (("day", "日"), ("week", "周"), ("year", "年度"))
_EMPTY_STATES = (("first-use", "首次使用"), ("no-results", "无搜索结果"), ("no-data", "暂无数据"))
_ALERT_MESSAGES = {"info": "设置尚未保存。确认内容后再继续。",
                   "success": "设置已保存，可以继续下一步。",
                   "warning": "部分设置尚未确认，请检查后再继续。",
                   "error": "设置保存失败。请检查输入后重试。"}
_TOAST_MESSAGES = {"info": "演示设置尚未保存。", "success": "演示设置已保存。",
                   "warning": "演示设置需要确认。", "error": "演示设置保存失败。"}


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

    def _build_tabs(self):
        self.long_text = tk.BooleanVar(self, False)
        self.disabled = tk.BooleanVar(self, True)
        self.long_choice = self.form.choice("标签长度", self.long_text, _LENGTHS, command=self._update_tabs)
        self.disabled_choice = self.form.choice("第三页", self.disabled, _AVAILABILITY, command=self._update_tabs)
        self.widget = self.register(Tabs(self.stage, palette=self.palette,
                                        on_change=lambda key: self.message.set("已切换到：" + _PAGES[key])))
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
        self.mode_choice = self.form.choice("展开方式", self.mode,
            (("单项展开", "单项展开"), ("多项展开", "多项展开")), command=self._update_accordion)
        self.long_choice = self.form.choice("标题长度", self.long_text, _LENGTHS, command=self._update_accordion)
        self.widget = self.register(Accordion(self.stage, palette=self.palette,
            on_change=lambda keys: self.message.set("已展开：" + ("、".join(_SECTIONS[key] for key in keys) or "无"))))
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
        self.disabled_choice = self.form.choice("年度选项", self.disabled, _AVAILABILITY,
                                               command=self._update_segments)
        self.current = tk.StringVar(self, "week")
        self.current_combo = self.form.combo("当前值", self.current, _SEGMENTS, command=self._update_segments)
        self.widget = self.register(SegmentedControl(self.stage, palette=self.palette,
            options=(("day", "日"), ("week", "周"), ("year", "年度")), value="week",
            disabled=("year",), on_change=self._segment_changed))
        self.widget.grid(row=0, column=0, sticky="new")
        self.message.set("互斥选项：Tab 聚焦当前值，方向键选择可用项，空格/Enter 激活。")

    def _segment_changed(self, key):
        self.current.set(key)
        self.message.set("已选择：" + dict(_SEGMENTS)[key])

    def _update_segments(self, _event=None):
        self.widget.set_disabled("year", self.disabled.get())
        if not self.widget.select(self.current.get()):
            self.current.set(self.widget.select() or "")
            self.message.set("年度选项已禁用，保留可用选择。")

    def _build_alert(self):
        self.kind = tk.StringVar(self, "info")
        self.long_text = tk.BooleanVar(self, False)
        self.kind_combo = self.form.combo("语义状态", self.kind, _KINDS, command=self._update_alert)
        self.long_choice = self.form.choice("内容长度", self.long_text,
            ((False, "简短"), (True, "长文本")), command=self._update_alert)
        self.widget = self.register(InlineAlert(self.stage, palette=self.palette, kind="info",
            message="设置尚未保存。确认内容后再继续。", action_text="查看下一步",
            on_action=lambda: self.message.set("调用方处理“查看下一步”；提示仍持续显示。")))
        self.widget.grid(row=0, column=0, sticky="new")
        self.message.set("消息持续显示，可聚焦、选择复制并滚动；重要错误可保留在这里。")

    def _alert_message(self):
        message = _ALERT_MESSAGES[self.kind.get()]
        return (message + "\n" + "补充说明：当前提示会持续显示，你可以选择复制，并在处理后返回此处。\n" * 12
                if self.long_text.get() else message)

    def _update_alert(self, _event=None):
        self.widget.set_message(self._alert_message(), kind=self.kind.get())

    def _build_toast(self):
        self.kind = tk.StringVar(self, "success")
        self.duration = tk.StringVar(self, "4000")
        self.kind_combo = self.form.combo("语义状态", self.kind, _KINDS, command=self._show_toast)
        self.duration_combo = self.form.combo("关闭方式", self.duration,
            (("1500", "1.5 秒后"), ("4000", "4 秒后"), ("0", "手动关闭")), command=self._show_toast)
        self.show_button = ttk.Button(self.actions, text="显示提示", command=self._show_toast, takefocus=True)
        self.show_button.grid(row=0, column=0, sticky="w")
        self.widget = self.register(Toast(self.stage, palette=self.palette, message="演示设置已保存。",
            kind="success", duration=4000,
            on_close=lambda reason: self.message.set("轻提示已关闭：" + {"manual": "手动关闭", "timeout": "自动关闭"}[reason])))
        self.widget.grid(row=0, column=0, sticky="new")
        self._show_toast()

    def _show_toast(self):
        self.widget.show(_TOAST_MESSAGES[self.kind.get()], kind=self.kind.get(), duration=int(self.duration.get()))
        self.message.set("悬停或将焦点移入关闭按钮可暂停计时；选择“手动关闭”可持续显示。重要错误应使用行内提示。")

    def _build_empty(self):
        self.kind = tk.StringVar(self, "first-use")
        self.kind_combo = self.form.combo("空状态原因", self.kind, _EMPTY_STATES, command=self._update_empty)
        self.disabled = tk.BooleanVar(self, False)
        self.disabled_choice = self.form.choice("操作按钮", self.disabled, _AVAILABILITY,
                                               command=self._update_empty)
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
            return example_code("from ui_center.navigation import Tabs", f'''page_names = {_PAGES!r}
tabs = Tabs(root, palette=palette, on_change=lambda key: print("已切换到：" + page_names[key]))
tabs.pack(fill="both", expand=True, padx=12, pady=12)
for key, text in {[("overview", "概览"), ("settings", _LONG if self.long_text.get() else "项目设置"), ("history", "历史记录")]!r}:
    page = tabs.add(key, text=text, disabled=key == "history" and {self.disabled.get()!r})
    ttk.Label(page, text="调用方提供的页面内容").pack(anchor="w")
    ttk.Entry(page).pack(fill="x", pady=8)
tabs.select({self.widget.select()!r})''')
        if self.key == "accordion":
            return example_code("from ui_center.navigation import Accordion", f'''section_names = {_SECTIONS!r}
accordion = Accordion(root, palette=palette, multiple={self.mode.get() == "多项展开"!r},
    on_change=lambda keys: print("已展开：" + ("、".join(section_names[key] for key in keys) or "无")))
accordion.pack(fill="x", padx=12, pady=12)
for key, text in {[("general", "通用设置"), ("advanced", _LONG if self.long_text.get() else "高级选项"), ("help", "使用说明")]!r}:
    body = accordion.add(key, text=text, expanded=key in {self.widget.expanded!r})
    ttk.Label(body, text="折叠时保留此处输入").pack(anchor="w")
    ttk.Entry(body).pack(fill="x", pady=8)''')
        if self.key == "segmented-control":
            return example_code("from ui_center.navigation import SegmentedControl", f'''option_names = {dict(_SEGMENTS)!r}
control = SegmentedControl(root, palette=palette,
    options=(("day", "日"), ("week", "周"), ("year", "年度")),
    value={self.widget.select()!r}, disabled={('year',) if self.disabled.get() else ()!r},
    on_change=lambda value: print("已选择：" + option_names[value]))
control.pack(fill="x", padx=12, pady=12)''')
        if self.key == "inline-alert":
            return example_code("from ui_center.feedback import InlineAlert", f'''alert = InlineAlert(root, palette=palette, kind={self.kind.get()!r},
    message={self._alert_message()!r}, action_text="查看下一步", on_action=lambda: print("查看下一步"))
alert.pack(fill="x", padx=12, pady=12)''')
        if self.key == "toast":
            return example_code("from ui_center.feedback import Toast", f'''close_reasons = {{"manual": "手动关闭", "timeout": "自动关闭"}}
toast = Toast(root, palette=palette, kind={self.kind.get()!r}, duration={int(self.duration.get())!r},
    message={_TOAST_MESSAGES[self.kind.get()]!r}, on_close=lambda reason: print("轻提示已关闭：" + close_reasons[reason]))
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

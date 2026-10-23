"""Interactive loading demonstrations; simulated work lives in this module.

SPDX-License-Identifier: AGPL-3.0-only
"""

import tkinter as tk
from tkinter import ttk

from ui_center.loading import (CircularProgress, LoadingButton, PageLoader,
                               ProgressBar, Shimmer, Skeleton, Spinner)

from .preview_base import PreviewView, example_code


IDS = ("spinner", "progress-bar", "circular-progress", "skeleton", "shimmer",
       "loading-button", "page-loader")


class LoadingPreview(PreviewView):
    def __init__(self, key, master, *, palette, reduced_motion=False):
        super().__init__(master, palette=palette, reduced_motion=reduced_motion)
        self.key = key
        self.setting = tk.StringVar(self)
        self.text = tk.StringVar(self)
        self.value = tk.DoubleVar(self, value=35)
        self.enabled = tk.BooleanVar(self, value=True)
        self.outcome = tk.StringVar(self, value="成功")
        self.start_button = ttk.Button(self.actions, text="开始", command=self.start)
        self.start_button.grid(row=0, column=0)
        self.stop_button = ttk.Button(self.actions, text="停止 / 取消", command=self.stop)
        self.stop_button.grid(row=0, column=1, padx=8)
        self.stage.columnconfigure(0, weight=1)
        self.stage.rowconfigure(0, weight=1)
        self.holder = ttk.Frame(self.stage, padding=16)
        self.holder.grid(row=0, column=0, sticky="nsew")
        self.holder.columnconfigure(0, weight=1)
        self.holder.rowconfigure(0, weight=1)
        kwargs = dict(palette=palette, reduced_motion=reduced_motion)
        if key == "spinner":
            self.form.combo("尺寸", self.setting, tuple((value, value + " 像素") for value in ("32", "48", "72")),
                            command=self._parameters)
            self.form.entry("说明", self.text, width=18, command=self._parameters)
            self.widget = Spinner(self.holder, **kwargs)
        elif key == "progress-bar":
            self.mode_choice = self.form.choice("模式", self.setting,
                                                (("determinate", "已知进度"), ("indeterminate", "未知进度")),
                                                command=self._parameters)
            self.form.scale("进度", self.value, command=self._parameters)
            self.widget = ProgressBar(self.holder, **kwargs)
        elif key == "circular-progress":
            self.form.combo("尺寸", self.setting, tuple((value, value + " 像素") for value in ("88", "112", "144")),
                            command=self._parameters)
            self.form.scale("进度", self.value, command=self._parameters)
            self.widget = CircularProgress(self.holder, **kwargs)
        elif key in ("skeleton", "shimmer"):
            self.layout_choice = self.form.choice("布局", self.setting, (("list", "列表"), ("card", "卡片")),
                                                  command=self._parameters)
            self.effect_choice = self.form.choice("脉动效果" if key == "skeleton" else "扫光效果", self.enabled,
                                                  ((True, "开启"), (False, "关闭")), command=self._parameters)
            cls = Skeleton if key == "skeleton" else Shimmer
            self.widget = cls(self.holder, **kwargs)
        elif key == "loading-button":
            self.form.entry("按钮", self.text, width=16, command=self._parameters)
            self.form.choice("模拟结果", self.outcome, (("成功", "成功"), ("失败", "失败")))
            self.widget = LoadingButton(self.holder, command=self.start, **kwargs)
        else:
            self.form.entry("说明", self.text, width=24, command=self._parameters)
            self.input_text = tk.StringVar(self, value="主题切换时保留的输入")
            ttk.Label(self.holder, text="示例页面内容").grid(row=0, column=0)
            self.entry = ttk.Entry(self.holder, textvariable=self.input_text, width=28)
            self.entry.grid(row=1, column=0, pady=8)
            ttk.Label(self.holder, text="遮罩只覆盖此示例区域。", style="UIC.Muted.TLabel").grid(row=2, column=0)
            self.widget = PageLoader(self.holder, on_cancel=self.stop, **kwargs)
            # place() intentionally does not size its parent. The demo page's
            # short label/entry requested less height than its loading overlay;
            # reserve the stage here rather than changing the reusable loader.
            for target in (self.widget, self.widget.caption, self.widget.progress_label,
                           self.widget.cancel_button):
                target.bind("<Configure>", self._fit_page_loader, add="+")
            self._fit_page_loader()
        self.register(self.widget)
        if key != "page-loader":
            self.widget.grid(row=0, column=0, sticky="ew" if key in ("progress-bar", "skeleton", "shimmer") else "")
        self.reset()

    def _fit_page_loader(self, _event=None):
        if not self._disposed:
            # Child Configure events also catch font and wrapping changes.
            # Account for the demonstration holder's 16px padding on each side.
            self.stage.rowconfigure(0, minsize=max(260, self.widget.winfo_reqheight() + 32))

    def set_reduced_motion(self, enabled):
        super().set_reduced_motion(enabled)
        if self.key in ("skeleton", "shimmer"):
            self._placeholder_feedback()

    def _placeholder_feedback(self):
        effect = "脉动" if self.key == "skeleton" else "扫光"
        self.effect_choice.set_enabled(not self.reduced_motion)
        if not self.widget.running:
            message = "已停止；保留静态占位，点击“开始”可重新演示。"
        elif self.reduced_motion:
            message = f"减少动画已启用，当前为静态占位；顶部选择“正常动画”可查看{effect}。"
        elif not self.enabled.get():
            message = f"{effect}效果已关闭；当前为静态占位。"
        else:
            message = ("正在演示脉动：占位块平滑明暗变化。" if self.key == "skeleton"
                       else "正在演示扫光：高光仅在占位块内移动，空白区域保持不变。")
        self.message.set(message)

    def _parameters(self):
        if not hasattr(self, "widget"):
            return
        key, widget = self.key, self.widget
        if key == "spinner":
            widget.set_size(int(self.setting.get()))
            widget.set_text(self.text.get())
        elif key == "progress-bar":
            widget.set_mode(self.setting.get())
            widget.set_progress(self.value.get())
        elif key == "circular-progress":
            widget.set_size(int(self.setting.get()))
            widget.set_progress(self.value.get())
        elif key in ("skeleton", "shimmer"):
            widget.set_variant(self.setting.get())
            if key == "shimmer":
                widget.set_enabled(self.enabled.get())
            else:
                widget.set_animation(self.enabled.get())
            self._placeholder_feedback()
        else:
            widget.set_text(self.text.get())

    def start(self):
        if self.key == "loading-button" and self.widget.busy:
            return
        self.cancel_task()
        self._parameters()
        widget, key = self.widget, self.key
        if key == "loading-button":
            widget.start()
            self.message.set("模拟任务进行中；按钮的鼠标和键盘重复触发均被禁用。")
            self.schedule(800, self._finish_button)
        elif key == "page-loader":
            widget.set_progress(0)
            widget.start()
            self.message.set("仅示例区域显示遮罩；可用取消按钮结束模拟任务。")
            self.schedule(180, self._advance)
        else:
            widget.start()
            if key in ("skeleton", "shimmer"):
                self._placeholder_feedback()
            else:
                self.message.set("装饰动画可随减少动画设置暂停；实际进度由调用者提供。")
            if key == "circular-progress" or (key == "progress-bar" and widget.mode == "determinate"):
                self.schedule(180, self._advance)

    def _advance(self):
        if self.key == "page-loader":
            current = self.widget.value
        else:
            current = self.value.get()
        current = min(100, current + 5)
        self.widget.set_progress(current)
        if self.key != "page-loader":
            self.value.set(current)
        if current < 100:
            self.schedule(180, self._advance)
        else:
            self.widget.stop()
            self.message.set("模拟任务已完成；显示的100%由示例调用者提供。")

    def _finish_button(self):
        self.widget.stop()
        self.message.set("模拟成功：已恢复按钮。" if self.outcome.get() == "成功"
                         else "模拟失败：保留参数并恢复按钮，可再次尝试。")

    def stop(self):
        self.cancel_task()
        self.widget.stop()
        self.message.set("模拟任务已取消；保留当前进度和参数。")
        if self.key in ("skeleton", "shimmer"):
            self._placeholder_feedback()

    def reset(self):
        self.cancel_task()
        self.widget.stop()
        self.text.set("正在加载" if self.key == "spinner" else "开始处理" if self.key == "loading-button" else "正在加载页面")
        self.setting.set({"spinner": "48", "progress-bar": "determinate",
                          "circular-progress": "112"}.get(self.key, "list"))
        self.value.set(35)
        self.enabled.set(True)
        self.outcome.set("成功")
        if self.key == "page-loader":
            self.widget.set_progress(0)
            self.input_text.set("主题切换时保留的输入")
        self._parameters()
        if self.key in ("spinner", "skeleton", "shimmer"):
            self.widget.start()
        self.message.set("预览使用虚构数据；可调整参数、开始、取消或重置。")
        if self.key in ("skeleton", "shimmer"):
            self._placeholder_feedback()

    def code(self):
        key, widget = self.key, self.widget
        reduced = f", reduced_motion={self.reduced_motion!r}"
        if key == "spinner":
            name = "Spinner"
            args = f"size={self.setting.get()}, text={self.text.get()!r}"
        elif key == "progress-bar":
            name = "ProgressBar"
            args = f"mode={self.setting.get()!r}, value={self.value.get():g}, maximum=100"
        elif key == "circular-progress":
            name = "CircularProgress"
            args = f"size={self.setting.get()}, value={self.value.get():g}, maximum=100"
        elif key in ("skeleton", "shimmer"):
            name = "Skeleton" if key == "skeleton" else "Shimmer"
            flag = "animate" if key == "skeleton" else "enabled"
            args = f"variant={self.setting.get()!r}, rows=3, {flag}={self.enabled.get()!r}"
        elif key == "loading-button":
            return example_code("from ui_center.loading import LoadingButton", """def on_start():
    button.set_busy(True)
    status.configure(text='请由你的任务完成回调调用 button.set_busy(False)')

status = ttk.Label(root, text='组件仅发出回调，不创建业务任务')
status.pack(pady=12)
button = LoadingButton(root, palette=palette, text=""" + repr(self.text.get()) + ", command=on_start" + reduced + ")\nbutton.pack(pady=20)\nbutton.set_busy(" + repr(widget.busy) + ")")
        else:
            value = "None" if widget.value is None else f"{widget.value:g}"
            body = ("stage = ttk.Frame(root, padding=20)\nstage.pack(fill='both', expand=True)\n"
                    "ttk.Label(stage, text='示例页面').pack()\n"
                    f"entry = ttk.Entry(stage)\nentry.insert(0, {self.input_text.get()!r})\nentry.pack(pady=12)\n"
                    f"loader = PageLoader(stage, palette=palette, text={self.text.get()!r}, value={value}, on_cancel=lambda: loader.stop(){reduced})\n")
            if widget.running:
                body += "loader.start()\n"
            else:
                body += "ttk.Button(stage, text='显示遮罩', command=loader.start).pack()\n"
            return example_code("from ui_center.loading import PageLoader", body)
        body = f"widget = {name}(root, palette=palette, {args}{reduced})\nwidget.pack(padx=24, pady=30, fill='x')\n"
        if widget.running:
            body += "widget.start()\n"
        return example_code(f"from ui_center.loading import {name}", body)


def create_preview(key, master, *, palette, reduced_motion=False):
    if key not in IDS:
        raise ValueError("Unknown loading preview: " + key)
    return LoadingPreview(key, master, palette=palette, reduced_motion=reduced_motion)

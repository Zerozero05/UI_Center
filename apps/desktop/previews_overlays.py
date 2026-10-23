"""Live, parameterized demonstrations for the five overlay components.

SPDX-License-Identifier: AGPL-3.0-only
"""
import tkinter as tk
from tkinter import ttk

from ui_center.overlays import Dialog, ConfirmDialog, Drawer, Popover, Tooltip
from .preview_base import PreviewView, example_code

IDS = ("dialog", "confirm-dialog", "drawer", "popover", "tooltip")
_TITLES = {"dialog": "对话框", "confirm-dialog": "确认对话框", "drawer": "侧边抽屉",
           "popover": "气泡面板", "tooltip": "工具提示"}


class OverlayPreview(PreviewView):
    def __init__(self, key, master, *, palette, reduced_motion=False):
        super().__init__(master, palette=palette, reduced_motion=reduced_motion)
        self.key = key
        self.text = tk.StringVar(master=self, value="此处只展示虚构数据，具体操作由调用方实现。")
        self.side = tk.StringVar(master=self, value="right")
        self.modal = tk.BooleanVar(master=self, value=True)
        self.delay = tk.IntVar(master=self, value=500)
        self.form.entry("内容", self.text, width=28)
        self.open_button = ttk.Button(self.actions, text="打开", command=self.open)
        self.open_button.grid(row=0, column=0)
        if key == "drawer":
            self.side_choice = self.form.choice("方向", self.side, (("left", "左侧"), ("right", "右侧")))
            self.modal_choice = self.form.choice("交互方式", self.modal, ((True, "模态"), (False, "非模态")))
        elif key == "tooltip":
            options = self.form.group("延时（毫秒）")
            ttk.Spinbox(options, textvariable=self.delay, from_=0, to=2000, increment=100,
                        width=8, command=self._update_tooltip).pack(side="left")
            ttk.Button(self.actions, text="应用参数", command=self._update_tooltip).grid(row=0, column=1, padx=8)
        self.stage.columnconfigure(0, weight=1)
        ttk.Label(self.stage, text=_TITLES[key], style="UIC.Heading.TLabel").grid(
            row=0, column=0, pady=(16, 16))
        self.trigger = ttk.Button(self.stage, text="打开" + _TITLES[key], command=self.open)
        self.trigger.grid(row=1, column=0, pady=16)
        hint = ("将鼠标停留在按钮上，或用 Tab 聚焦该按钮，延时后显示。"
                if key == "tooltip" else "使用上方参数后打开；Esc 关闭并恢复触发焦点；隐藏预览会关闭弹层。")
        ttk.Label(self.stage, text=hint, wraplength=400, justify="center",
                  style="UIC.Muted.TLabel").grid(row=2, column=0, padx=16, pady=16)
        self.overlay = None
        self._build_overlay()

    def _build_overlay(self):
        delay = min(2000, max(0, self.delay.get())) if self.key == "tooltip" else 0
        if self.overlay is not None:
            self.overlay.dispose()
            self.managed.remove(self.overlay)
        common = {"palette": self.palette}
        if self.key == "dialog":
            overlay = Dialog(self.stage, title="示例对话框", message=self.text.get(),
                             on_close=self._closed, **common)
        elif self.key == "confirm-dialog":
            overlay = ConfirmDialog(self.stage, title="确认示例操作", message=self.text.get(),
                                    confirm_text="确认示例操作", on_result=self._result, **common)
        elif self.key == "drawer":
            overlay = Drawer(self.stage, title="示例侧边面板", message=self.text.get(),
                             side=self.side.get(), modal=self.modal.get(),
                             reduced_motion=self.reduced_motion, on_close=self._closed, **common)
        elif self.key == "popover":
            overlay = Popover(self.stage, anchor=self.trigger, text=self.text.get(),
                              on_close=self._closed, **common)
        else:
            overlay = Tooltip(self.trigger, text=self.text.get(), delay_ms=delay, **common)
        self.overlay = self.register(overlay)
        self.overlay.set_visible(self.visible)

    def _update_tooltip(self):
        try:
            self._build_overlay()
            self.message.set("已应用提示内容与延时；可悬停、Tab 聚焦或点击打开。")
        except (tk.TclError, ValueError):
            self.message.set("延时请填写 0–2000 之间的整数。")

    def _closed(self, reason):
        reasons = {"close": "关闭按钮", "escape": "按下退出键", "window": "系统关闭",
                   "outside": "点击外部", "hidden": "预览隐藏", "disposed": "预览重置",
                   "cancel": "取消操作", "confirm": "确认操作", "error": "内容生成失败",
                   "pointer": "点击提示目标", "leave": "离开提示目标"}
        self.message.set("已关闭：" + reasons.get(reason, "操作结束"))

    def _result(self, confirmed):
        self.message.set("示例结果：" + ("已确认" if confirmed else "已取消"))

    def open(self):
        try:
            self._build_overlay()
        except (tk.TclError, ValueError):
            self.message.set("延时请填写 0–2000 之间的整数。")
            return
        self.message.set("弹层已打开。" if self.overlay.show(self.trigger) else "已有模态窗口，请先关闭它。")

    def reset(self):
        self.text.set("此处只展示虚构数据，具体操作由调用方实现。")
        self.side.set("right")
        self.modal.set(True)
        self.delay.set(500)
        self._build_overlay()
        self.message.set("已恢复默认参数。")

    def code(self):
        text = repr(self.text.get())
        names = {"dialog": "Dialog", "confirm-dialog": "ConfirmDialog", "drawer": "Drawer",
                 "popover": "Popover", "tooltip": "Tooltip"}
        name = names[self.key]
        prefix = "trigger = ttk.Button(root, text='打开" + _TITLES[self.key] + "')\ntrigger.pack(pady=40)\n"
        if self.key == "dialog":
            body = f"overlay = Dialog(root, palette=palette, title='示例对话框', message={text})\n"
        elif self.key == "confirm-dialog":
            body = (f"overlay = ConfirmDialog(root, palette=palette, message={text},\n"
                    "                        on_result=lambda confirmed: print('确认：', confirmed))\n")
        elif self.key == "drawer":
            body = (f"overlay = Drawer(root, palette=palette, message={text}, side={self.side.get()!r},\n"
                    f"                 modal={self.modal.get()!r}, reduced_motion={self.reduced_motion!r})\n")
        elif self.key == "popover":
            body = f"overlay = Popover(root, palette=palette, anchor=trigger, text={text})\n"
        else:
            try:
                delay = min(2000, max(0, self.delay.get()))
            except (tk.TclError, ValueError):
                delay = 500
            body = f"overlay = Tooltip(trigger, palette=palette, text={text}, delay_ms={delay})\n"
        body += "trigger.configure(command=lambda: overlay.show(trigger))\n"
        body += "root.protocol('WM_DELETE_WINDOW', lambda: (overlay.dispose(), root.destroy()))\n"
        return example_code("from ui_center.overlays import " + name, prefix + body)


def create_preview(key, master, *, palette, reduced_motion=False):
    if key not in IDS:
        raise KeyError(key)
    return OverlayPreview(key, master, palette=palette, reduced_motion=reduced_motion)

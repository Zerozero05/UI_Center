"""Shared, bounded lifecycle for real component demonstrations.

SPDX-License-Identifier: AGPL-3.0-only
"""
from tkinter import ttk, StringVar
from tkinter import font as tkfont
from .parameters import ParameterForm


class PreviewView(ttk.Frame):
    def __init__(self, master, *, palette, reduced_motion=False):
        super().__init__(master, padding=(0, 12, 0, 0))
        self.palette, self.reduced_motion = palette, bool(reduced_motion)
        self.visible, self._disposed = True, False
        self.managed = []
        self._after_id = self._continuation = None
        self._delay = 100
        self._workspace_pending = None
        self.wide_layout = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.demo_panel = ttk.Frame(self, style="UIC.Preview.TFrame", padding=1)
        self.demo_panel.columnconfigure(0, weight=1)
        self.demo_panel.rowconfigure(1, weight=1, minsize=260)
        demo_header = ttk.Frame(self.demo_panel, style="UIC.Stage.TFrame", padding=(16, 10))
        demo_header.grid(row=0, column=0, sticky="ew")
        ttk.Label(demo_header, text="组件预览", style="UIC.Stage.TLabel").pack(side="left")
        ttk.Label(demo_header, text="可交互", style="UIC.Stage.Muted.TLabel").pack(side="right")
        self.stage = ttk.Frame(self.demo_panel, padding=20)
        self.stage.grid(row=1, column=0, sticky="nsew")
        self.controls = ttk.Frame(self, padding=(16, 0, 0, 0))
        self.controls.columnconfigure(0, weight=1)
        ttk.Label(self.controls, text="参数设置", style="UIC.Section.TLabel").grid(row=0, column=0, sticky="w", pady=(8, 12))
        ttk.Separator(self.controls).grid(row=1, column=0, sticky="ew", pady=(0, 16))
        self.form = self.register(ParameterForm(self.controls, palette=palette))
        self.form.grid(row=2, column=0, sticky="ew")
        self.actions = ttk.Frame(self.controls)
        self._controls_actions = self.actions
        self.actions.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        self.actions.columnconfigure(98, weight=1)
        self.reset_button = ttk.Button(self.actions, text="重置", command=self.reset,
                                      style="UIC.Secondary.TButton")
        self.reset_button.grid(row=0, column=99, sticky="e")
        self.controls.bind("<Configure>", self._arrange_controls)
        self.message = StringVar(master=self, value="预览仅使用虚构数据，不处理你的文件。")
        self.status_label = ttk.Label(self, textvariable=self.message,
                                      style="UIC.Muted.TLabel", wraplength=650)
        self.status_label.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self.bind("<Configure>", self._queue_workspace)
        parent = master.master
        self._viewport = parent if parent is not None and parent.winfo_class() == "Canvas" else master
        self._viewport_binding = self._viewport.bind("<Configure>", self._queue_workspace, add="+")
        self.bind("<Destroy>", self._on_destroy, add="+")
        self._queue_workspace()

    def register(self, widget):
        self.managed.append(widget)
        return widget

    def _queue_workspace(self, _event=None):
        if not self._disposed and self._workspace_pending is None:
            self._workspace_pending = self.after_idle(self._layout_workspace)

    def _layout_workspace(self):
        self._workspace_pending = None
        available = self._viewport.winfo_width()
        if available <= 1:
            return
        font = tkfont.nametofont("TkDefaultFont", root=self)
        inspector_width = max(220, min(320, font.measure("0")*22))
        # Use the visible viewport, not the scroll host's potentially larger
        # request: a narrow window must actually return to one column.
        threshold = max(760, self.demo_panel.winfo_reqwidth() + inspector_width + 32)
        wide = available >= threshold
        self.form.configure(width=inspector_width)
        self.form.set_stacked(wide)
        if wide != self.wide_layout:
            self.wide_layout = wide
            self.demo_panel.grid(row=0, column=0, sticky="nsew")
            self.controls.grid(row=0 if wide else 1, column=1 if wide else 0, sticky="new",
                               padx=(16, 0) if wide else 0, pady=0 if wide else (20, 0))
            self.controls.configure(padding=(0, 0, 0, 0))
            self.columnconfigure(1, weight=0)
        self.status_label.configure(wraplength=max(160, available-24))

    def _arrange_controls(self, _event=None):
        other_actions = [child for child in self._controls_actions.winfo_children()
                         if child is not self.reset_button and child.winfo_manager()]
        if other_actions or self.reset_button.winfo_manager():
            self._controls_actions.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        else:
            self._controls_actions.grid_remove()

    def apply_palette(self, palette):
        self.palette = palette
        for widget in self.managed:
            if hasattr(widget, "apply_palette"):
                widget.apply_palette(palette)

    def set_reduced_motion(self, enabled):
        self.reduced_motion = bool(enabled)
        for widget in self.managed:
            if hasattr(widget, "set_reduced_motion"):
                widget.set_reduced_motion(enabled)

    def set_visible(self, visible):
        self.visible = bool(visible)
        if not visible:
            self._cancel_pending()
        elif self._continuation is not None and self._after_id is None:
            self._after_id = self.after(self._delay, self._run)
        for widget in self.managed:
            if hasattr(widget, "set_visible"):
                widget.set_visible(visible)

    def _cancel_pending(self):
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None

    def schedule(self, milliseconds, callback):
        self._cancel_pending()
        self._delay, self._continuation = milliseconds, callback
        if self.visible and not self._disposed:
            self._after_id = self.after(milliseconds, self._run)

    def _run(self):
        self._after_id = None
        callback, self._continuation = self._continuation, None
        if callback is not None and self.visible and not self._disposed:
            callback()

    def cancel_task(self):
        self._cancel_pending()
        self._continuation = None

    def reset(self):
        raise NotImplementedError

    def code(self):
        raise NotImplementedError

    def _on_destroy(self, event):
        if event.widget is self and not self._disposed:
            self._disposed = True
            if self._workspace_pending is not None:
                self.after_cancel(self._workspace_pending)
                self._workspace_pending = None
            if self._viewport.winfo_exists():
                self._viewport.unbind("<Configure>", self._viewport_binding)
            self.cancel_task()
            for widget in self.managed:
                if hasattr(widget, "dispose"):
                    widget.dispose()

    def dispose(self):
        if not self._disposed:
            self.destroy()


def example_code(imports, body):
    return ("from pathlib import Path\nimport tkinter as tk\nfrom tkinter import ttk\n"
            "from ui_center.theme import apply_theme\n" + imports.rstrip() + "\n\n"
            "root = tk.Tk()\nroot.title('UI_Center 组件示例')\nroot.geometry('620x420')\n"
            "palette = apply_theme(root, tokens_path=Path(__file__).parent / 'tokens' / 'design-tokens.json')\n"
            + body.rstrip() + "\nroot.mainloop()\n")

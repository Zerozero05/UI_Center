"""Shared, bounded lifecycle for real component demonstrations.

SPDX-License-Identifier: AGPL-3.0-only
"""
from tkinter import ttk, StringVar
from .parameters import ParameterForm


class PreviewView(ttk.Frame):
    def __init__(self, master, *, palette, reduced_motion=False):
        super().__init__(master, padding=16)
        self.palette = palette
        self.reduced_motion = bool(reduced_motion)
        self.managed = []
        self.visible = True
        self._disposed = False
        self._after_id = None
        self._continuation = None
        self._delay = 100
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.controls = ttk.Frame(self)
        self.controls.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.controls.columnconfigure(0, weight=1)
        self.form = self.register(ParameterForm(self.controls, palette=palette))
        self.form.grid(row=0, column=0, sticky="ew")
        self.actions = ttk.Frame(self.controls)
        self._controls_actions = self.actions
        self.actions.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.actions.columnconfigure(98, weight=1)
        self.reset_button = ttk.Button(self.actions, text="重置", command=self.reset,
                                      style="UIC.Secondary.TButton")
        self.reset_button.grid(row=0, column=99, sticky="e")
        self.controls.bind("<Configure>", self._arrange_controls)
        self.stage = ttk.Frame(self)
        self.stage.grid(row=1, column=0, sticky="nsew")
        self.message = StringVar(master=self, value="预览仅使用虚构数据，不处理你的文件。")
        self.status_label = ttk.Label(self, textvariable=self.message,
                                      style="UIC.Muted.TLabel", wraplength=650)
        self.status_label.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.bind("<Configure>", lambda e: self.status_label.configure(wraplength=max(160, e.width - 24)))
        self.bind("<Destroy>", self._on_destroy, add="+")

    def register(self, widget):
        self.managed.append(widget)
        return widget

    def _arrange_controls(self, _event=None):
        other_actions = [child for child in self._controls_actions.winfo_children()
                         if child is not self.reset_button and child.winfo_manager()]
        if other_actions:
            self._controls_actions.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=(8, 0))
        elif self.reset_button.winfo_manager():
            self._controls_actions.grid(row=0, column=1, columnspan=1, sticky="se", padx=(8, 0), pady=0)
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

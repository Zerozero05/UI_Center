"""Persistent feedback, bounded transient feedback and caller-driven empty states.

SPDX-License-Identifier: AGPL-3.0-only
"""

import time
import tkinter as tk
from tkinter import ttk


_KINDS = {"info": ("提示", "accent"), "success": ("成功", "success"),
          "warning": ("警告", "warning"), "error": ("错误", "error")}


def _semantic(kind):
    if kind not in _KINDS:
        raise ValueError("Unknown feedback kind: " + str(kind))
    return _KINDS[kind]


class InlineAlert(tk.Frame):
    """Persistent four-state feedback with selectable, scrollable message text."""

    def __init__(self, master, *, palette, message, kind="info", title=None,
                 action_text="处理", on_action=None, **kwargs):
        super().__init__(master, highlightthickness=1, padx=12, pady=10, **kwargs)
        self.palette = palette
        self._fit_id = None
        self._body_width = None
        self.columnconfigure(0, weight=1)
        self.title_label = tk.Label(self, anchor="w", justify="left", font="TkDefaultFont")
        self.title_label.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        box = tk.Frame(self, borderwidth=0)
        box.grid(row=1, column=0, sticky="nsew")
        box.columnconfigure(0, weight=1)
        self.body = tk.Text(box, height=1, width=1, wrap="word", font="TkDefaultFont",
                            borderwidth=0, highlightthickness=1, takefocus=True, undo=False)
        self.body.bind("<Tab>", lambda event: self._move_focus(False))
        self.body.bind("<Shift-Tab>", lambda event: self._move_focus(True))
        self.scrollbar = ttk.Scrollbar(box, command=self.body.yview)
        self.body.configure(yscrollcommand=self.scrollbar.set)
        self.body.grid(row=0, column=0, sticky="nsew")
        self.body.bind("<Configure>", self._body_resized)
        self.action = None
        if on_action is not None:
            self.action = ttk.Button(self, text=action_text, command=on_action, takefocus=True)
            self.action.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.bind("<Configure>", self._wrap)
        self.bind("<Destroy>", self._on_destroy, add="+")
        self.set_message(message, kind=kind, title=title)

    def _wrap(self, event):
        if event.widget is self:
            self.title_label.configure(wraplength=max(60, event.width - 30))

    def _body_resized(self, event):
        if event.width != self._body_width:
            self._body_width = event.width
            self._schedule_fit()

    def _schedule_fit(self):
        if self._fit_id is None:
            self._fit_id = self.after_idle(self._fit_body)

    def _fit_body(self):
        self._fit_id = None
        if self.body.winfo_width() <= 2:
            return
        lines = int(self.body.tk.call(self.body._w, "count", "-update", "-displaylines",
                                      "1.0", "end-1c")) + 1
        height = min(4, max(1, lines))
        if int(self.body.cget("height")) != height:
            self.body.configure(height=height)
        if lines > 4:
            if not self.scrollbar.winfo_manager():
                self.scrollbar.grid(row=0, column=1, sticky="ns")
        elif self.scrollbar.winfo_manager():
            self.scrollbar.grid_remove()

    def _on_destroy(self, event):
        if event.widget is self and self._fit_id is not None:
            self.after_cancel(self._fit_id)
            self._fit_id = None

    def _move_focus(self, previous):
        target = self.body.tk_focusPrev() if previous else self.body.tk_focusNext()
        if target is not None:
            target.focus_set()
        return "break"

    def set_message(self, message, *, kind=None, title=None):
        kind = self.kind if kind is None else kind
        label, _role = _semantic(kind)
        self.kind, self.message = kind, str(message)
        self.title = title
        self.title_label.configure(text=label + (" · " + title if title else ""))
        self.body.configure(state="normal")
        self.body.delete("1.0", "end")
        self.body.insert("1.0", self.message)
        self.body.configure(state="disabled")
        self.body.yview_moveto(0)
        self.apply_palette(self.palette)

    def apply_palette(self, palette):
        self.palette = palette
        _label, role = _semantic(self.kind)
        self.configure(background=palette["surface"], highlightbackground=palette[role])
        self.title_label.configure(background=palette["surface"], foreground=palette[role])
        self.body.master.configure(background=palette["surface"])
        self.body.configure(background=palette["surface"], foreground=palette["foreground"],
                            insertbackground=palette["foreground"],
                            selectbackground=palette["selected_background"],
                            selectforeground=palette["selected_foreground"],
                            inactiveselectbackground=palette["selected_background"],
                            highlightbackground=palette["surface"], highlightcolor=palette["focus"])
        self._schedule_fit()


class Toast(tk.Frame):
    """Transient inline feedback. Pack/grid/place it, then call ``show()``.

    ``duration`` is milliseconds; zero keeps the toast until manual close.
    Hover and focus pause the remaining time. Hide/dispose cancels callbacks.
    ``on_close(reason)`` receives ``manual`` or ``timeout`` once per showing.
    """

    def __init__(self, master, *, palette, message="", kind="info", duration=4000,
                 on_close=None, **kwargs):
        _semantic(kind)
        if duration < 0:
            raise ValueError("Toast duration must be nonnegative")
        super().__init__(master, highlightthickness=1, padx=10, pady=8, **kwargs)
        self.palette, self.message, self.kind = palette, str(message), kind
        self.duration, self.on_close = int(duration), on_close
        self._timer = None
        self._focus_timer = None
        self._started = None
        self._remaining = self.duration
        self._active = False
        self._visible = True
        self._hover = False
        self._focused = False
        self._disposed = False
        self._layout = None
        self.columnconfigure(0, weight=1)
        self.label = tk.Label(self, anchor="w", justify="left", wraplength=360, font="TkDefaultFont")
        self.label.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.close_button = ttk.Button(self, text="关闭", command=self.hide, takefocus=True)
        self.close_button.grid(row=0, column=1, sticky="ne")
        for widget in (self, self.label, self.close_button):
            widget.bind("<Enter>", lambda event: self._set_hover(True), add="+")
            widget.bind("<Leave>", lambda event: self._set_hover(False), add="+")
            widget.bind("<FocusIn>", lambda event: self._set_focus(True), add="+")
            widget.bind("<FocusOut>", self._defer_focus, add="+")
        self.bind("<Configure>", self._wrap, add="+")
        self.bind("<Map>", self._on_map, add="+")
        self.bind("<Unmap>", self._on_unmap, add="+")
        self.bind("<Destroy>", self._on_destroy, add="+")
        self.apply_palette(palette)

    @property
    def is_open(self):
        return self._active

    def _wrap(self, event):
        if event.widget is self:
            self.label.configure(wraplength=max(40, event.width - self.close_button.winfo_reqwidth() - 34))

    def _cancel_timer(self):
        if self._timer is not None:
            self.after_cancel(self._timer)
            self._timer = None
            self._remaining = max(0, self._remaining - (time.monotonic() - self._started) * 1000)
            self._started = None

    def _cancel_focus(self):
        if self._focus_timer is not None:
            self.after_cancel(self._focus_timer)
            self._focus_timer = None

    def _resume(self):
        if self._active and self._visible and not self._disposed and not self._hover and not self._focused and self.winfo_ismapped() and self.duration > 0 and self._timer is None:
            self._started = time.monotonic()
            self._timer = self.after(max(1, int(self._remaining)), self._expire)

    def _expire(self):
        self._timer = None
        self._started = None
        self._remaining = 0
        self.hide(reason="timeout")

    def _set_hover(self, hovered):
        self._hover = hovered
        self._cancel_timer() if hovered else self._resume()

    def _set_focus(self, focused):
        self._focused = focused
        self._cancel_timer() if focused else self._resume()

    def _defer_focus(self, _event):
        self._cancel_focus()
        if self._active and self._visible and not self._disposed:
            self._focus_timer = self.after_idle(self._check_focus)

    def _check_focus(self):
        self._focus_timer = None
        focus = self.focus_get()
        self._set_focus(focus is self or (focus is not None and str(focus).startswith(str(self) + ".")))

    def _on_map(self, event):
        if event.widget is self and not self._disposed:
            self._check_focus()
            self._resume()

    def _on_unmap(self, event):
        if event.widget is self:
            self._cancel_timer()
            self._cancel_focus()
            self._hover = self._focused = False

    def _forget(self):
        manager = self.winfo_manager()
        if manager in ("pack", "grid", "place"):
            self._layout = manager, getattr(self, manager + "_info")()
            getattr(self, manager + "_forget")()

    def _restore(self):
        if self._layout is not None and not self.winfo_manager():
            manager, options = self._layout
            getattr(self, manager)(**options)

    def show(self, message=None, *, duration=None, kind=None):
        if self._disposed:
            return
        if duration is not None and duration < 0:
            raise ValueError("Toast duration must be nonnegative")
        if kind is not None:
            _semantic(kind)
        self._cancel_timer()
        self._cancel_focus()
        if message is not None:
            self.message = str(message)
        if kind is not None:
            self.kind = kind
        if duration is not None:
            self.duration = int(duration)
        self._remaining = self.duration
        self._active = True
        self._visible = True
        self._restore()
        self.apply_palette(self.palette)
        self._check_focus()
        self._resume()

    def hide(self, *, reason="manual"):
        was_active = self._active
        self._active = False
        self._cancel_timer()
        self._cancel_focus()
        self._forget()
        if was_active and self.on_close is not None:
            self.on_close(reason)

    def set_visible(self, visible):
        if self._disposed:
            return
        self._visible = bool(visible)
        if not visible:
            self._cancel_timer()
            self._cancel_focus()
            self._hover = self._focused = False
            self._forget()
        elif self._active:
            self._restore()
            self._check_focus()
            self._resume()

    def apply_palette(self, palette):
        self.palette = palette
        label, role = _semantic(self.kind)
        self.configure(background=palette["surface"], highlightbackground=palette[role])
        self.label.configure(text=label + " · " + self.message,
                             background=palette["surface"], foreground=palette["foreground"])

    def _on_destroy(self, event):
        if event.widget is self:
            self._active = False
            self._cancel_timer()
            self._cancel_focus()
            self._disposed = True

    def dispose(self):
        if not self._disposed:
            self._active = False
            self._cancel_timer()
            self._cancel_focus()
            self._disposed = True
            self.destroy()


class EmptyState(tk.Frame):
    """First use, empty search and empty data with an optional caller action."""

    STATES = {
        "first-use": ("开始你的第一个项目", "创建项目后，内容会显示在这里。", "创建项目"),
        "no-results": ("没有匹配的搜索结果", "试试其他关键词，或清除当前筛选。", "清除筛选"),
        "no-data": ("暂时没有数据", "数据可用后会显示在这里，你也可以重新获取。", "刷新"),
    }

    def __init__(self, master, *, palette, kind="first-use", title=None, message=None,
                 action_text=None, on_action=None, **kwargs):
        super().__init__(master, padx=16, pady=16, **kwargs)
        self.palette, self.on_action = palette, on_action
        self.columnconfigure(0, weight=1)
        self.title_label = tk.Label(self, font="TkDefaultFont", justify="center")
        self.title_label.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.message_label = tk.Label(self, font="TkDefaultFont", justify="center")
        self.message_label.grid(row=1, column=0, sticky="ew")
        self.action = ttk.Button(self, command=self._invoke, takefocus=True)
        if on_action is not None:
            self.action.grid(row=2, column=0, pady=(12, 0))
        self.bind("<Configure>", self._wrap)
        self.set_state(kind, title=title, message=message, action_text=action_text)

    def _wrap(self, event):
        if event.widget is self:
            for label in (self.title_label, self.message_label):
                label.configure(wraplength=max(40, event.width - 36))

    def _invoke(self):
        if self.on_action is not None:
            self.on_action()

    def set_state(self, kind, *, title=None, message=None, action_text=None):
        if kind not in self.STATES:
            raise ValueError("Unknown empty state: " + str(kind))
        self.kind = kind
        defaults = self.STATES[kind]
        self.title = defaults[0] if title is None else str(title)
        self.message = defaults[1] if message is None else str(message)
        self.action_text = defaults[2] if action_text is None else str(action_text)
        self.title_label.configure(text=self.title)
        self.message_label.configure(text=self.message)
        self.action.configure(text=self.action_text)
        self.apply_palette(self.palette)

    def apply_palette(self, palette):
        self.palette = palette
        self.configure(background=palette["surface"])
        self.title_label.configure(background=palette["surface"], foreground=palette["foreground"])
        self.message_label.configure(background=palette["surface"], foreground=palette["muted"])

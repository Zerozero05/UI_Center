"""Scoped Tk overlays. Call every method on the Tk UI thread.

SPDX-License-Identifier: AGPL-3.0-only
"""
import tkinter as tk
from tkinter import ttk


def active_overlay(widget):
    """Return the most recently opened interactive overlay in this interpreter."""
    root = widget._root()
    stack = getattr(root, "_uic_overlays", ())
    return next((item for item in reversed(stack) if item.is_open), None)


def close_active_overlay(widget):
    """Let a host Escape handler dismiss an overlay before its own shortcuts."""
    overlay = active_overlay(widget)
    if overlay is None:
        return False
    overlay.close("escape")
    return True


class _Overlay:
    def __init__(self, master, *, palette, on_close=None):
        self.master = master
        self.palette = palette
        self.on_close = on_close
        self.window = None
        self.content = None
        self.visible = True
        self._disposed = False
        self._trigger = None
        self._previous_grab = None
        self._bindings = []
        self._after_id = None
        self._colors = []
        self._bordered = False
        self._master_binding = master.bind("<Destroy>", self._master_destroyed, add="+")

    @property
    def is_open(self):
        return self.window is not None

    def _master_destroyed(self, event):
        if event.widget is self.master:
            self.dispose()

    def _bind(self, widget, sequence, callback):
        self._bindings.append((widget, sequence, widget.bind(sequence, callback, add="+")))

    def _create(self, trigger, *, modal, title="", decorated=True, interactive=True):
        if self._disposed or not self.visible:
            return False
        if self.is_open:
            self.window.lift()
            return False
        trigger = trigger or self.master.focus_get() or self.master
        grabbed = self.master.grab_current()
        # Only an explicit trigger inside the existing modal may open a child.
        if grabbed is not None and trigger.winfo_toplevel() != grabbed.winfo_toplevel():
            return False
        self._trigger = trigger
        self._previous_grab = grabbed
        self._colors = []
        window = self.window = tk.Toplevel(self.master)
        window.withdraw()
        window.title(title)
        window.transient(self.master.winfo_toplevel())
        if not decorated:
            window.overrideredirect(True)
        self._bordered = True
        window.protocol("WM_DELETE_WINDOW", lambda: self.close("window"))
        window.bind("<Destroy>", self._window_destroyed, add="+")
        self.content = ttk.Frame(window, padding=16)
        edge = 1 if self._bordered else 0
        self.content.pack(fill="both", expand=True, padx=edge, pady=edge)
        self.content.columnconfigure(0, weight=1)
        self.apply_palette(self.palette)
        self._modal = modal
        self._interactive = interactive
        if interactive:
            root = self.master._root()
            if not hasattr(root, "_uic_overlays"):
                root._uic_overlays = []
            root._uic_overlays.append(self)
            window.bind("<Escape>", self._escape, add="+")
            if modal:
                window.bind("<Tab>", lambda event: self._tab(False))
                window.bind("<Shift-Tab>", lambda event: self._tab(True))
                if window.tk.call("tk", "windowingsystem") == "x11":
                    window.bind("<ISO_Left_Tab>", lambda event: self._tab(True))
        return True

    def _escape(self, _event):
        self.close("escape")
        return "break"

    def _focusables(self):
        result = []

        def visit(parent):
            for child in parent.winfo_children():
                if child.winfo_viewable() and bool(int(child.tk.call("tk::FocusOK", child))):
                    result.append(child)
                visit(child)
        visit(self.window)
        return result

    def _tab(self, backwards):
        widgets = self._focusables()
        if widgets:
            focused = self.window.focus_get()
            index = widgets.index(focused) if focused in widgets else (0 if backwards else -1)
            widgets[(index + (-1 if backwards else 1)) % len(widgets)].focus_set()
        return "break"

    def _present(self, *, focus=None, geometry=None):
        window = self.window
        window.update_idletasks()
        if geometry is None:
            owner = self.master.winfo_toplevel()
            width, height = window.winfo_reqwidth(), window.winfo_reqheight()
            x = owner.winfo_rootx() + max(0, (owner.winfo_width() - width) // 2)
            y = owner.winfo_rooty() + max(0, (owner.winfo_height() - height) // 2)
            geometry = f"+{max(0, x)}+{max(0, y)}"
        window.geometry(geometry)
        window.deiconify()
        window.lift()
        window.update_idletasks()
        if self._modal:
            window.grab_set()
        if focus is not None:
            focus.focus_force()

    def _label(self, text, *, heading=False):
        options = {"text": text, "justify": "left", "anchor": "w", "wraplength": 420}
        label = (ttk.Label(self.content, style="UIC.Heading.TLabel", **options) if heading
                 else tk.Label(self.content, font="TkDefaultFont", **options))
        label.pack(fill="x", pady=(0, 16))
        label.bind("<Configure>", lambda event: label.configure(wraplength=max(100, event.width - 4)))
        self._colors.append(label)
        self.apply_palette(self.palette)
        return label

    def _build_content(self, factory):
        if factory is not None:
            try:
                factory(self.content)
            except Exception:
                self.close("error")
                raise

    def apply_palette(self, palette):
        self.palette = palette
        if self.window is not None:
            self.window.configure(background=palette["border"] if self._bordered else palette["background"])
        for label in self._colors:
            label.configure(background=palette["background"], foreground=palette["foreground"])

    def _cancel_after(self):
        if self._after_id is not None:
            self.master.after_cancel(self._after_id)
            self._after_id = None

    def _release(self, window, *, restore_focus=True):
        self._cancel_after()
        for widget, sequence, binding in self._bindings:
            if widget.winfo_exists():
                widget.unbind(sequence, binding)
        self._bindings.clear()
        root = self.master._root()
        stack = getattr(root, "_uic_overlays", [])
        if self in stack:
            stack.remove(self)
        try:
            current_grab = window.grab_current()
            owned_grab = current_grab is window
            if owned_grab:
                window.grab_release()
            previous = self._previous_grab
            if owned_grab and previous is not None and previous.winfo_exists():
                previous.grab_set()
            if (restore_focus and self._interactive and (current_grab is None or owned_grab)
                    and self._trigger is not None
                    and self._trigger.winfo_exists()):
                self._trigger.focus_set()
        except tk.TclError:
            # During root destruction, Tcl may already have removed a window.
            pass
        self._previous_grab = None
        self.content = None
        self._colors.clear()

    def _window_destroyed(self, event):
        if event.widget is self.window:
            window, self.window = self.window, None
            self._release(window)

    def close(self, reason="close"):
        if self.window is None:
            self._cancel_after()
            return
        window, self.window = self.window, None
        self._release(window)
        window.destroy()
        if self.on_close is not None:
            self.on_close(reason)

    def set_visible(self, visible):
        self.visible = bool(visible)
        if not visible:
            self.close("hidden")

    def dispose(self):
        if not self._disposed:
            self._disposed = True
            self.close("disposed")
            if self.master.winfo_exists():
                self.master.unbind("<Destroy>", self._master_binding)


class Dialog(_Overlay):
    """Modal information dialog. Escape/WM close restore trigger focus."""
    def __init__(self, master, *, palette, title="对话框", message="", close_text="关闭", on_close=None):
        super().__init__(master, palette=palette, on_close=on_close)
        self.title, self.message, self.close_text = title, message, close_text

    def show(self, trigger=None):
        if not self._create(trigger, modal=True, title=self.title):
            return False
        self._label(self.title, heading=True)
        self._label(self.message)
        self.close_button = ttk.Button(self.content, text=self.close_text, command=self.close)
        self.close_button.pack(anchor="e")
        self._present(focus=self.close_button)
        return True


class ConfirmDialog(_Overlay):
    """Modal confirmation; initial focus and Return both choose cancellation."""
    def __init__(self, master, *, palette, title="确认操作", message="", confirm_text="确认",
                 cancel_text="取消", on_result=None, on_close=None):
        super().__init__(master, palette=palette, on_close=on_close)
        self.title, self.message = title, message
        self.confirm_text, self.cancel_text = confirm_text, cancel_text
        self.on_result = on_result
        self.result = None

    def show(self, trigger=None):
        if not self._create(trigger, modal=True, title=self.title):
            return False
        self.result = None
        self._label(self.title, heading=True)
        self._label(self.message)
        actions = ttk.Frame(self.content)
        actions.pack(fill="x")
        self.confirm_button = ttk.Button(actions, text=self.confirm_text, command=self.confirm)
        self.confirm_button.pack(side="right")
        self.cancel_button = ttk.Button(actions, text=self.cancel_text, command=lambda: self.close("cancel"))
        self.cancel_button.pack(side="right", padx=(0, 8))
        # Return follows the focused action, never an implicit destructive default.
        self.cancel_button.bind("<Return>", lambda event: self._return(False))
        self.confirm_button.bind("<Return>", lambda event: self._return(True))
        self._present(focus=self.cancel_button)
        return True

    def _return(self, confirmed):
        self.confirm() if confirmed else self.close("cancel")
        return "break"

    def confirm(self):
        if self.is_open:
            self.result = True
            self.close("confirm")

    def close(self, reason="close"):
        was_open = self.is_open
        result = reason == "confirm"
        if was_open:
            self.result = result
        super().close(reason)
        if was_open and self.on_result is not None:
            self.on_result(result)


class Drawer(_Overlay):
    """Left/right side sheet, modal by default, with six bounded opening steps."""
    def __init__(self, master, *, palette, title="侧边面板", message="", side="right", modal=True,
                 width=320, reduced_motion=False, content_factory=None, on_close=None):
        if side not in ("left", "right"):
            raise ValueError("side must be left or right")
        if width < 160:
            raise ValueError("width must be at least 160")
        super().__init__(master, palette=palette, on_close=on_close)
        self.title, self.message = title, message
        self.side, self.modal, self.width = side, bool(modal), int(width)
        self.reduced_motion = bool(reduced_motion)
        self.content_factory = content_factory
        self._animation_step = 0

    def show(self, trigger=None):
        if not self._create(trigger, modal=self.modal, title=self.title):
            return False
        self._label(self.title, heading=True)
        self._label(self.message)
        self._build_content(self.content_factory)
        self.close_button = ttk.Button(self.content, text="关闭面板", command=self.close)
        self.close_button.pack(side="bottom", anchor="e", pady=(16, 0))
        owner = self.master.winfo_toplevel()
        owner.update_idletasks()
        width = min(self.width, max(160, owner.winfo_width()))
        height = max(180, owner.winfo_height())
        self._drawer_size = (width, height)
        self._drawer_x = owner.winfo_rootx() + (owner.winfo_width() - width if self.side == "right" else 0)
        self._drawer_y = owner.winfo_rooty()
        self._animation_step = 6 if self.reduced_motion else 0
        self._present(focus=self.close_button, geometry=self._geometry(self._animation_step))
        if not self.reduced_motion:
            self._after_id = self.master.after(34, self._animate)
        return True

    def _geometry(self, step):
        width, height = self._drawer_size
        offset = round((6 - step) * min(48, width // 4) / 6)
        x = self._drawer_x + (offset if self.side == "right" else -offset)
        return f"{width}x{height}+{max(0, x)}+{max(0, self._drawer_y)}"

    def _animate(self):
        self._after_id = None
        if self.is_open:
            self._animation_step += 1
            self.window.geometry(self._geometry(self._animation_step))
            if self._animation_step < 6:
                self._after_id = self.master.after(34, self._animate)

    def set_reduced_motion(self, enabled):
        self.reduced_motion = bool(enabled)
        if enabled and self.is_open:
            self._cancel_after()
            self._animation_step = 6
            self.window.geometry(self._geometry(6))


class Popover(_Overlay):
    """Nonmodal anchored panel. Owner-window outside clicks or Escape dismiss it."""
    def __init__(self, master, *, palette, anchor=None, text="", content_factory=None, on_close=None):
        super().__init__(master, palette=palette, on_close=on_close)
        self.anchor, self.text, self.content_factory = anchor or master, text, content_factory

    def show(self, trigger=None):
        if not self._create(trigger or self.anchor, modal=False, decorated=False):
            return False
        self._label(self.text)
        self._build_content(self.content_factory)
        self.close_button = ttk.Button(self.content, text="关闭", command=self.close)
        self.close_button.pack(anchor="e")
        x, y = self.anchor.winfo_rootx(), self.anchor.winfo_rooty() + self.anchor.winfo_height()
        self._present(focus=self.close_button, geometry=f"+{max(0, x)}+{max(0, y)}")
        self._bind(self.master.winfo_toplevel(), "<ButtonPress-1>", self._outside)
        self._bind(self.master.winfo_toplevel(), "<Escape>", self._escape)
        return True

    def _outside(self, event):
        if self.window is not None and event.widget.winfo_toplevel() is not self.window:
            self.close("outside")


class Tooltip(_Overlay):
    """Delayed, noninteractive hint attached to one widget (hover and focus)."""
    def __init__(self, master, *, palette, text="", delay_ms=500):
        if delay_ms < 0:
            raise ValueError("delay_ms must not be negative")
        super().__init__(master, palette=palette)
        self.text, self.delay_ms = text, int(delay_ms)
        self._hovered = self._focused = False
        self._anchor_bindings = []
        for sequence, callback in (("<Enter>", self._enter), ("<Leave>", self._leave),
                                   ("<FocusIn>", self._focus_in), ("<FocusOut>", self._focus_out),
                                   ("<ButtonPress>", self._dismiss)):
            self._anchor_bindings.append((sequence, master.bind(sequence, callback, add="+")))

    def _enter(self, _event):
        self._hovered = True
        self._schedule()

    def _leave(self, _event):
        self._hovered = False
        self._dismiss_if_inactive()

    def _focus_in(self, _event):
        self._focused = True
        self._schedule()

    def _focus_out(self, _event):
        self._focused = False
        self._dismiss_if_inactive()

    def _dismiss(self, _event):
        self.close("pointer")

    def _dismiss_if_inactive(self):
        if not (self._hovered or self._focused):
            self.close("leave")

    def _schedule(self):
        self._cancel_after()
        if self.visible and not self._disposed and not self.is_open:
            self._after_id = self.master.after(self.delay_ms, self._show_pending)

    def _show_pending(self):
        self._after_id = None
        if self._hovered or self._focused:
            self.show()

    def show(self, trigger=None):
        # Explicit show is useful for keyboard help buttons and documentation demos.
        if not self._create(trigger or self.master, modal=False, decorated=False, interactive=False):
            return False
        self._label(self.text)
        self._colors[-1].pack_configure(pady=0)
        self.window.attributes("-topmost", True)
        x = self.master.winfo_rootx()
        y = self.master.winfo_rooty() + self.master.winfo_height() + 4
        self._present(geometry=f"+{max(0, x)}+{max(0, y)}")
        return True

    def dispose(self):
        if not self._disposed:
            if self.master.winfo_exists():
                for sequence, binding in self._anchor_bindings:
                    self.master.unbind(sequence, binding)
            self._anchor_bindings.clear()
        super().dispose()

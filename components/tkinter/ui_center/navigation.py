"""Focusable navigation controls; callers own page contents and application data.

SPDX-License-Identifier: AGPL-3.0-only
"""

import tkinter as tk
from tkinter import ttk


def _choice_colors(button, palette, selected=False):
    disabled = button.cget("state") == "disabled"
    if disabled:
        button._ui_center_hovered = False
    selected = selected and not disabled
    background = (palette["selected_background"] if selected else
                  palette["hover"] if button._ui_center_hovered else palette["surface"])
    foreground = (palette["disabled"] if disabled else
                  palette["selected_foreground"] if selected else palette["foreground"])
    button.configure(background=background, foreground=foreground,
                     activebackground=palette["selected_background"] if selected else
                     palette["surface"] if disabled else palette["hover"],
                     activeforeground=foreground,
                     disabledforeground=palette["disabled"],
                     highlightbackground=palette["border"], highlightcolor=palette["focus"])
    if isinstance(button, tk.Radiobutton):
        button.configure(selectcolor=palette["surface"] if disabled else palette["selected_background"])


def _bind_choice_hover(button, repaint):
    button._ui_center_hovered = False

    def set_hover(hovered):
        button._ui_center_hovered = hovered and button.cget("state") != "disabled"
        repaint()

    button.bind("<Enter>", lambda event: set_hover(True), add="+")
    button.bind("<Leave>", lambda event: set_hover(False), add="+")


class Tabs(ttk.Frame):
    """Wrapping page tabs with one roving tab stop and automatic arrow selection.

    ``add(key, text=...)`` returns a content Frame. ``on_change(key)`` runs after
    a changed selection. Keys are caller supplied unique strings.
    """

    def __init__(self, master, *, palette, on_change=None, **kwargs):
        super().__init__(master, **kwargs)
        self.palette, self.on_change = palette, on_change
        self._pages, self._buttons = {}, {}
        self._selected = None
        self._value = tk.StringVar(master=self)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.header = ttk.Frame(self)
        self.header.grid(row=0, column=0, sticky="ew")
        self.content = ttk.Frame(self)
        self.content.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)
        self.header.bind("<Configure>", self._wrap)

    def add(self, key, *, text, disabled=False):
        if not isinstance(key, str) or not key or key in self._pages:
            raise ValueError("Tab keys must be unique nonempty strings")
        page = ttk.Frame(self.content, padding=8)
        button = tk.Radiobutton(self.header, text=text, value=key, variable=self._value,
                                indicatoron=False, command=lambda: self.select(key),
                                font="TkDefaultFont", padx=8, pady=8, borderwidth=0,
                                relief="flat", offrelief="flat", overrelief="flat",
                                highlightthickness=1, wraplength=160, takefocus=False,
                                state="disabled" if disabled else "normal")
        index = len(self._pages)
        button.grid(row=0, column=index, sticky="nsew")
        self.header.columnconfigure(index, weight=1, uniform="tabs")
        self._pages[key], self._buttons[key] = page, button
        _bind_choice_hover(button, lambda: self.apply_palette(self.palette))
        for sequence, direction in (("<Right>", 1), ("<Down>", 1), ("<Left>", -1), ("<Up>", -1)):
            button.bind(sequence, lambda event, step=direction: self._move(step))
        button.bind("<Home>", lambda event: self._move("first"))
        button.bind("<End>", lambda event: self._move("last"))
        button.bind("<Return>", lambda event: self._activate_key(key))
        _choice_colors(button, self.palette)
        if self._selected is None and not disabled:
            self.select(key, notify=False)
        self._wrap()
        return page

    def _wrap(self, event=None):
        width = event.width if event is not None else self.header.winfo_width()
        for button in self._buttons.values():
            button.configure(wraplength=max(24, width // max(1, len(self._buttons)) - 24))

    def _activate_key(self, key):
        self.select(key)
        return "break"

    def _move(self, direction):
        keys = [key for key, button in self._buttons.items() if button.cget("state") != "disabled"]
        if keys:
            current = keys.index(self._selected) if self._selected in keys else 0
            index = 0 if direction == "first" else len(keys) - 1 if direction == "last" else (current + direction) % len(keys)
            self.select(keys[index])
            self._buttons[keys[index]].focus_set()
        return "break"

    def select(self, key=None, *, notify=True):
        if key is None:
            return self._selected
        if key not in self._pages:
            raise KeyError(key)
        if self._buttons[key].cget("state") == "disabled":
            return False
        previous = self._selected
        if previous is not None:
            self._pages[previous].grid_remove()
            self._buttons[previous].configure(takefocus=False)
        self._selected = key
        self._value.set(key)
        self._pages[key].grid(row=0, column=0, sticky="nsew")
        self._buttons[key].configure(takefocus=True)
        self.apply_palette(self.palette)
        if previous != key and notify and self.on_change is not None:
            self.on_change(key)
        return True

    def set_disabled(self, key, disabled=True):
        button = self._buttons[key]
        button.configure(state="disabled" if disabled else "normal")
        if disabled and self._selected == key:
            self._pages[key].grid_remove()
            button.configure(takefocus=False)
            self._selected = None
            self._value.set("")
            for candidate, control in self._buttons.items():
                if control.cget("state") != "disabled":
                    self.select(candidate)
                    break
        elif not disabled and self._selected is None:
            self.select(key)
        self.apply_palette(self.palette)

    def set_text(self, key, text):
        self._buttons[key].configure(text=text)

    def apply_palette(self, palette):
        self.palette = palette
        for key, button in self._buttons.items():
            _choice_colors(button, palette, key == self._selected)


class Accordion(ttk.Frame):
    """Disclosure sections, optionally allowing more than one open section."""

    def __init__(self, master, *, palette, multiple=False, on_change=None, **kwargs):
        super().__init__(master, **kwargs)
        self.palette, self.multiple, self.on_change = palette, bool(multiple), on_change
        self._sections, self._buttons, self._titles = {}, {}, {}
        self._expanded = set()
        self.columnconfigure(0, weight=1)
        self.bind("<Configure>", self._wrap)

    @property
    def expanded(self):
        return tuple(key for key in self._sections if key in self._expanded)

    def add(self, key, *, text, expanded=False, disabled=False):
        if not isinstance(key, str) or not key or key in self._sections:
            raise ValueError("Section keys must be unique nonempty strings")
        index = len(self._sections) * 2
        button = tk.Button(self, text="▸ " + text, anchor="w", font="TkDefaultFont",
                           command=lambda: self.toggle(key), takefocus=not disabled,
                           state="disabled" if disabled else "normal", padx=10, pady=8,
                           relief="flat", overrelief="flat", borderwidth=0,
                           highlightthickness=1, wraplength=300)
        button.grid(row=index, column=0, sticky="ew", pady=(0, 4))
        body = ttk.Frame(self, padding=(14, 4, 8, 12))
        self._sections[key], self._buttons[key], self._titles[key] = body, button, text
        _bind_choice_hover(button, lambda: self.apply_palette(self.palette))
        for sequence, direction in (("<Down>", 1), ("<Up>", -1), ("<Home>", "first"), ("<End>", "last")):
            button.bind(sequence, lambda event, step=direction, item=key: self._move(item, step))
        button.bind("<Right>", lambda event, item=key: self._key_expand(item, True))
        button.bind("<Left>", lambda event, item=key: self._key_expand(item, False))
        button.bind("<Return>", lambda event, item=key: self._key_toggle(item))
        self.apply_palette(self.palette)
        if expanded and not disabled:
            self.set_expanded(key, True, notify=False)
        return body

    def _wrap(self, event):
        if event.widget is self:
            for button in self._buttons.values():
                button.configure(wraplength=max(40, event.width - 36))

    def _move(self, key, direction):
        keys = [key for key, button in self._buttons.items() if button.cget("state") != "disabled"]
        if keys:
            index = 0 if direction == "first" else len(keys) - 1 if direction == "last" else (keys.index(key) + direction) % len(keys)
            self._buttons[keys[index]].focus_set()
        return "break"

    def _key_expand(self, key, expanded):
        self.set_expanded(key, expanded)
        return "break"

    def _key_toggle(self, key):
        self.toggle(key)
        return "break"

    def toggle(self, key):
        return self.set_expanded(key, key not in self._expanded)

    def set_expanded(self, key, expanded=True, *, notify=True):
        if key not in self._sections:
            raise KeyError(key)
        if self._buttons[key].cget("state") == "disabled":
            return False
        previous = self.expanded
        if expanded:
            if not self.multiple:
                self._expanded.clear()
            self._expanded.add(key)
        else:
            self._expanded.discard(key)
        self._render()
        if previous != self.expanded and notify and self.on_change is not None:
            self.on_change(self.expanded)
        return True

    def _render(self):
        for index, (key, body) in enumerate(self._sections.items()):
            is_open = key in self._expanded
            self._buttons[key].configure(text=("▾ " if is_open else "▸ ") + self._titles[key])
            if is_open:
                body.grid(row=index * 2 + 1, column=0, sticky="ew")
            else:
                body.grid_remove()
        self.apply_palette(self.palette)

    def set_multiple(self, multiple):
        self.multiple = bool(multiple)
        if not self.multiple and len(self._expanded) > 1:
            self._expanded = {self.expanded[0]}
            self._render()
            if self.on_change is not None:
                self.on_change(self.expanded)

    def set_text(self, key, text):
        self._titles[key] = text
        self._render()

    def apply_palette(self, palette):
        self.palette = palette
        for key, button in self._buttons.items():
            _choice_colors(button, palette, key in self._expanded)


class SegmentedControl(ttk.Frame):
    """Mutually exclusive, focusable options. ``on_change(value)`` reports changes."""

    def __init__(self, master, *, palette, options, value=None, disabled=(), on_change=None, **kwargs):
        super().__init__(master, **kwargs)
        self.palette, self.on_change = palette, on_change
        self._buttons = {}
        self._selected = None
        self._value = tk.StringVar(master=self)
        disabled = set(disabled)
        for index, (key, text) in enumerate(options):
            if not isinstance(key, str) or not key or key in self._buttons:
                raise ValueError("Option values must be unique nonempty strings")
            button = tk.Radiobutton(self, text=text, value=key, variable=self._value,
                                    command=lambda item=key: self.select(item), indicatoron=False,
                                    takefocus=False, font="TkDefaultFont", padx=8, pady=8,
                                    highlightthickness=1, borderwidth=0, relief="flat",
                                    offrelief="flat", overrelief="flat", wraplength=140,
                                    state="disabled" if key in disabled else "normal")
            button.grid(row=0, column=index, sticky="nsew")
            self.columnconfigure(index, weight=1, uniform="segments")
            self._buttons[key] = button
            _bind_choice_hover(button, lambda: self.apply_palette(self.palette))
            for sequence, direction in (("<Right>", 1), ("<Down>", 1), ("<Left>", -1), ("<Up>", -1), ("<Home>", "first"), ("<End>", "last")):
                button.bind(sequence, lambda event, step=direction: self._move(step))
            button.bind("<Return>", lambda event, item=key: self._activate_key(item))
        self.bind("<Configure>", self._wrap)
        self.apply_palette(palette)
        if value is not None:
            if value not in self._buttons:
                raise KeyError(value)
            self.select(value, notify=False)
        if self._selected is None:
            for key, button in self._buttons.items():
                if button.cget("state") != "disabled":
                    self.select(key, notify=False)
                    break

    def _wrap(self, event):
        if event.widget is self:
            for button in self._buttons.values():
                button.configure(wraplength=max(24, event.width // max(1, len(self._buttons)) - 24))

    def _activate_key(self, key):
        self.select(key)
        return "break"

    def _move(self, direction):
        keys = [key for key, button in self._buttons.items() if button.cget("state") != "disabled"]
        if keys:
            current = keys.index(self._selected) if self._selected in keys else 0
            index = 0 if direction == "first" else len(keys) - 1 if direction == "last" else (current + direction) % len(keys)
            self.select(keys[index])
            self._buttons[keys[index]].focus_set()
        return "break"

    def select(self, value=None, *, notify=True):
        if value is None:
            return self._selected
        button = self._buttons[value]
        if button.cget("state") == "disabled":
            return False
        previous = self._selected
        self._selected = value
        self._value.set(value)
        for key, control in self._buttons.items():
            control.configure(takefocus=key == value)
        self.apply_palette(self.palette)
        if previous != value and notify and self.on_change is not None:
            self.on_change(value)
        return True

    def set_disabled(self, value, disabled=True):
        self._buttons[value].configure(state="disabled" if disabled else "normal")
        if disabled and self._selected == value:
            self._selected = None
            self._value.set("")
            self._buttons[value].configure(takefocus=False)
            for key, button in self._buttons.items():
                if button.cget("state") != "disabled":
                    self.select(key)
                    break
        elif not disabled and self._selected is None:
            self.select(value)
        self.apply_palette(self.palette)

    def apply_palette(self, palette):
        self.palette = palette
        for key, button in self._buttons.items():
            _choice_colors(button, palette, key == self._selected)

"""Private Chinese parameter controls for the workbench.

SPDX-License-Identifier: AGPL-3.0-only
"""
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont


class ParameterChoice(ttk.Frame):
    def __init__(self, master, *, variable, options, palette, command=None):
        super().__init__(master)
        self.variable, self.options, self.command = variable, tuple(options), command
        self.palette, self.enabled = palette, True
        self.buttons = {}
        self._display = tk.StringVar(self)
        for index, (value, label) in enumerate(self.options):
            button = tk.Radiobutton(self, text=label, value=str(index), variable=self._display,
                indicatoron=False, command=lambda v=value: self.select(v), font="TkDefaultFont",
                relief="flat", borderwidth=0, padx=8, pady=6, highlightthickness=2, takefocus=False)
            button.grid(row=0, column=index, sticky="nsew")
            self.columnconfigure(index, weight=1, uniform="choice")
            self.buttons[value] = button
            for sequence, step in (("<Left>", -1), ("<Right>", 1), ("<Up>", -1),
                                   ("<Down>", 1), ("<Home>", "first"), ("<End>", "last")):
                button.bind(sequence, lambda event, direction=step: self._move(direction))
            button.bind("<Return>", lambda event, v=value: self._activate(v))
        self._trace = variable.trace_add("write", self._sync)
        self.bind("<Configure>", self._wrap)
        self.bind("<Destroy>", self._destroy, add="+")
        self._sync()

    def _destroy(self, event):
        if event.widget is self:
            self.variable.trace_remove("write", self._trace)

    def _wrap(self, event):
        if event.widget is self:
            width = max(24, event.width // max(1, len(self.buttons)) - 20)
            for button in self.buttons.values():
                button.configure(wraplength=width)

    def preferred_width(self):
        font = tkfont.nametofont("TkDefaultFont", root=self)
        return max(font.measure(label) + 24 for _value, label in self.options) * len(self.options)

    def _sync(self, *_args):
        selected = self.variable.get()
        for index, (value, _label) in enumerate(self.options):
            button = self.buttons[value]
            active = selected == value
            if active:
                self._display.set(str(index))
            button.configure(takefocus=self.enabled and active)
        self.apply_palette(self.palette)

    def select(self, value=None, *, notify=True):
        if value is None:
            return self.variable.get()
        if value not in self.buttons:
            raise KeyError(value)
        if not self.enabled:
            self._sync()
            return False
        previous = self.variable.get()
        self.variable.set(value)
        if previous != value and notify and self.command is not None:
            self.command()
        return True

    def _activate(self, value):
        self.select(value)
        return "break"

    def _move(self, direction):
        if self.enabled:
            values = [value for value, _label in self.options]
            current = values.index(self.variable.get())
            index = 0 if direction == "first" else len(values)-1 if direction == "last" else (current+direction) % len(values)
            self.select(values[index])
            self.buttons[values[index]].focus_set()
        return "break"

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        for button in self.buttons.values():
            button.configure(state="normal" if self.enabled else "disabled")
        self._sync()

    def apply_palette(self, palette):
        self.palette = palette
        selected = self.variable.get()
        for value, button in self.buttons.items():
            active = selected == value
            background = palette["selected_background"] if active and self.enabled else palette["hover"] if active else palette["surface"]
            foreground = palette["selected_foreground"] if active and self.enabled else palette["foreground"]
            button.configure(background=background, foreground=foreground, selectcolor=background,
                activebackground=background if active else palette["hover"], activeforeground=foreground,
                disabledforeground=palette["disabled"], highlightbackground=palette["surface"],
                highlightcolor=palette["focus"])


class MappedCombo(ttk.Combobox):
    def __init__(self, master, *, variable, options, command=None, width=14):
        self.variable, self.options, self.command = variable, tuple(options), command
        self.display = tk.StringVar(master)
        super().__init__(master, textvariable=self.display, values=[label for _, label in self.options],
                         state="readonly", width=width, takefocus=True)
        self.bind("<<ComboboxSelected>>", self._chosen)
        self._trace = variable.trace_add("write", self._sync)
        self.bind("<Destroy>", self._destroy, add="+")
        self._sync()

    def _sync(self, *_args):
        value = self.variable.get()
        self.display.set(next((label for key, label in self.options if key == value), str(value)))

    def _chosen(self, _event):
        match = next((key for key, label in self.options if label == self.display.get()), None)
        if match is not None and self.variable.get() != match:
            self.variable.set(match)
            if self.command is not None:
                self.command()

    def _destroy(self, event):
        if event.widget is self:
            self.variable.trace_remove("write", self._trace)


class ParameterForm(ttk.Frame):
    """Keep label/control groups intact and wrap them at their measured width."""
    def __init__(self, master, *, palette):
        super().__init__(master, height=1, width=1)
        self.palette = palette
        self._groups, self._choices = [], []
        self._pending = None
        self.bind("<Configure>", self._queue)
        self.bind("<Destroy>", self._destroy, add="+")

    def _destroy(self, event):
        if event.widget is self and self._pending is not None:
            self.after_cancel(self._pending)
            self._pending = None

    def group(self, label):
        field = ttk.Frame(self)
        title = ttk.Label(field, text=label, style="UIC.Muted.TLabel") if label else None
        if title is not None:
            title.pack(anchor="w", pady=(0, 4))
        field._parameter_title = title
        self._groups.append(field)
        field.bind("<Configure>", self._queue, add="+")
        self._queue()
        return field

    def _queue(self, _event=None):
        if self._pending is None:
            self._pending = self.after_idle(self._layout)

    def _layout(self):
        self._pending = None
        available = max(1, self.winfo_width())
        x = y = row_height = 0
        for field in self._groups:
            preferred = field._parameter_preferred() if hasattr(field, "_parameter_preferred") else field.winfo_reqwidth()
            width = min(available, max(120, preferred))
            if x and x + width > available:
                x, y, row_height = 0, y + row_height + 12, 0
            if field._parameter_title is not None:
                field._parameter_title.configure(wraplength=max(40, width))
            height = field.winfo_reqheight()
            field.place(x=x, y=y, width=width, height=height)
            x += width + 12
            row_height = max(row_height, height)
        height = y + row_height if self._groups else 1
        if int(self.cget("height")) != height:
            self.configure(height=height)

    def choice(self, label, variable, options, command=None):
        group = self.group(label)
        control = ParameterChoice(group, variable=variable, options=options, palette=self.palette, command=command)
        control.pack(fill="x")
        group._parameter_preferred = control.preferred_width
        self._choices.append(control)
        self._queue()
        return control

    def preferred_width(self):
        return sum(max(120, field.winfo_reqwidth()) for field in self._groups) + max(0, len(self._groups)-1) * 12

    def combo(self, label, variable, options, command=None, width=14):
        group = self.group(label)
        control = MappedCombo(group, variable=variable, options=options, command=command, width=width)
        control.pack(fill="x")
        self._queue()
        return control

    def entry(self, label, variable, width=20, command=None):
        group = self.group(label)
        control = ttk.Entry(group, textvariable=variable, width=width)
        control.pack(fill="x")
        if command is not None:
            control.bind("<KeyRelease>", lambda _event: command())
        self._queue()
        return control

    def scale(self, label, variable, command=None):
        group = self.group(label)
        control = ttk.Scale(group, variable=variable, from_=0, to=100, length=180,
                            command=lambda _value: command() if command is not None else None)
        control.pack(fill="x")
        self._queue()
        return control

    def apply_palette(self, palette):
        self.palette = palette
        for control in self._choices:
            control.apply_palette(palette)
        self._queue()

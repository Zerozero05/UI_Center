"""UI-only actions and task feedback; callers own work, cancellation and data.

SPDX-License-Identifier: AGPL-3.0-only
"""

import tkinter as tk
from tkinter import ttk

from .theme import load_tokens


class ActionBar(ttk.Frame):
    """One primary action, one optional secondary action and cooperative cancel."""

    def __init__(self, master, *, on_primary, on_cancel, primary_text="开始任务",
                 on_secondary=None, secondary_text="重置", spacing=None, **kwargs):
        super().__init__(master, **kwargs)
        gap = load_tokens()["spacing"] if spacing is None else spacing
        self.primary = ttk.Button(self, text=primary_text, command=on_primary,
                                  style="UIC.Primary.TButton", takefocus=True)
        self.primary.pack(side="left")
        self.secondary = None
        if on_secondary is not None:
            self.secondary = ttk.Button(self, text=secondary_text, command=on_secondary, takefocus=True)
            self.secondary.pack(side="left", padx=gap["sm"])
        self.cancel = ttk.Button(self, text="取消任务", command=on_cancel, takefocus=True)
        self.cancel.pack(side="right")
        self.set_busy(False)

    def set_busy(self, busy, *, cancelling=False):
        """Disable duplicate starts and resets; cancellation remains cooperative."""
        self.primary.state(["disabled" if busy else "!disabled"])
        if self.secondary is not None:
            self.secondary.state(["disabled" if busy else "!disabled"])
        self.cancel.state(["!disabled" if busy and not cancelling else "disabled"])
        self.cancel.configure(text="正在取消…" if cancelling else "取消任务")


class TaskPanel(ttk.Frame):
    """Render progress and results; safe only on the Tk UI thread.

    State is one of idle/running/cancelling/completed/cancelled/error.
    ``results`` is a sequence of (item_label, status_text), or None to retain
    existing rows. Text states carry meaning without depending on colors.
    """

    STATES = {
        "idle": ("尚未开始", "UIC.Muted.TLabel"),
        "running": ("正在处理", "TLabel"),
        "cancelling": ("正在取消", "UIC.Warning.TLabel"),
        "completed": ("处理完成", "UIC.Success.TLabel"),
        "cancelled": ("已取消", "UIC.Warning.TLabel"),
        "error": ("处理失败", "UIC.Error.TLabel"),
    }

    def __init__(self, master, *, spacing=None, **kwargs):
        super().__init__(master, **kwargs)
        gap = load_tokens()["spacing"] if spacing is None else spacing
        self.task_state = "idle"
        self.message = tk.StringVar(master=self)
        self.count = tk.StringVar(master=self)
        self.status = tk.StringVar(master=self)
        self.selected_detail = tk.StringVar(master=self, value="选择一行查看完整名称与结果")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew")
        self.status_label = ttk.Label(top, textvariable=self.status)
        self.status_label.pack(side="left")
        ttk.Label(top, textvariable=self.count, style="UIC.Muted.TLabel").pack(side="right")
        self.progress = ttk.Progressbar(self, mode="determinate", maximum=1, takefocus=False)
        self.progress.grid(row=1, column=0, sticky="ew", pady=(gap["sm"], gap["sm"]))
        message_box = self.message_box = ttk.Frame(self)
        message_box.grid(row=2, column=0, sticky="ew", pady=(0, gap["md"]))
        self.message_label = tk.Text(message_box, height=3, width=1, wrap="word", borderwidth=0,
                                     state="disabled", font="TkDefaultFont", takefocus=True, undo=False)
        message_scroll = ttk.Scrollbar(message_box, orient="vertical", command=self.message_label.yview)
        self.message_label.configure(yscrollcommand=message_scroll.set)
        message_scroll.pack(side="right", fill="y")
        self.message_label.pack(fill="both", expand=True)
        self.message_label.bind("<<ThemeChanged>>", self._refresh_message_colors)
        self.message_label.bind("<Tab>", lambda event: self._message_tab(event, False))
        self.message_label.bind("<Shift-Tab>", lambda event: self._message_tab(event, True))
        self._refresh_message_colors()
        table = ttk.Frame(self)
        table.grid(row=3, column=0, sticky="nsew")
        self.results = ttk.Treeview(table, columns=("item", "status"), show="headings", height=7, takefocus=True)
        self.results.heading("item", text="项目")
        self.results.heading("status", text="结果")
        self.results.column("item", width=330, minwidth=140, stretch=True)
        self.results.column("status", width=160, minwidth=90, stretch=False)
        scrollbar = ttk.Scrollbar(table, orient="vertical", command=self.results.yview)
        self.results.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.results.xview)
        self.results.configure(xscrollcommand=horizontal.set)
        horizontal.grid(row=4, column=0, sticky="ew")
        self.results.pack(fill="both", expand=True)
        self.detail_entry = ttk.Entry(self, textvariable=self.selected_detail, state="readonly", takefocus=True)
        self.detail_entry.grid(row=5, column=0, sticky="ew", pady=(gap["sm"], 0))
        self.results.bind("<<TreeviewSelect>>", self._select_result)
        self.set_state("idle", message="任务开始后将在这里显示进度和结果。")

    @staticmethod
    def _message_tab(event, previous):
        target = event.widget.tk_focusPrev() if previous else event.widget.tk_focusNext()
        if target is not None:
            target.focus_set()
        return "break"

    def _refresh_message_colors(self, _event=None):
        style = ttk.Style(self)
        options = {"background": style.lookup("TEntry", "fieldbackground"),
                   "foreground": style.lookup("TLabel", "foreground"),
                   "insertbackground": style.lookup("TLabel", "foreground"),
                   "highlightbackground": style.lookup(".", "bordercolor"),
                   "highlightcolor": style.lookup(".", "focuscolor"),
                   "selectbackground": style.lookup(".", "selectbackground"),
                   "inactiveselectbackground": style.lookup(".", "selectbackground"),
                   "selectforeground": style.lookup(".", "selectforeground")}
        self.message_label.configure(**{name: value for name, value in options.items() if value})

    def _select_result(self, _event=None):
        selection = self.results.selection()
        if selection:
            label, outcome = self.results.item(selection[0], "values")
            self.selected_detail.set(f"{label} · {outcome}")
            self.detail_entry.xview_moveto(0)

    def set_state(self, state, *, completed=0, total=0, message="", results=None):
        """Replace displayed state and optionally rows; never starts any task."""
        if state not in self.STATES:
            raise ValueError("Unknown task state: " + state)
        if not 0 <= completed <= total:
            raise ValueError("Progress must satisfy 0 <= completed <= total")
        title, style = self.STATES[state]
        self.task_state = state
        self.status.set(title)
        self.status_label.configure(style=style)
        self.message.set(message)
        self.message_label.configure(state="normal")
        self.message_label.delete("1.0", "end")
        self.message_label.insert("1.0", message)
        self.message_label.configure(state="disabled")
        self.message_label.yview_moveto(0)
        self.count.set(f"{completed} / {total}" if total else "")
        self.progress.configure(maximum=max(1, total), value=completed)
        if results is not None:
            self.selected_detail.set("选择一行查看完整名称与结果")
            children = self.results.get_children()
            if children:
                self.results.delete(*children)
            for label, outcome in results:
                self.results.insert("", "end", values=(label, outcome))

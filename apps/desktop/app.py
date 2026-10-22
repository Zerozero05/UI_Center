"""Offline UI guidance and component browser, with a shared-theme live preview."""

import tkinter as tk
from tkinter import ttk
import webbrowser

from ui_center import apply_theme, load_tokens
from examples.tkinter.demo import DemoWindow

from .catalog import ENTRIES, PLATFORMS, SCENES, adoption_note, body_for, filter_entries, usage_for
from .reader import DocumentReader


def work_area(root):
    """Usable monitor rectangle for this application window, in screen pixels."""
    if root.tk.call("tk", "windowingsystem") == "win32":
        import ctypes
        from ctypes import wintypes

        class MonitorInfo(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT),
                        ("work", wintypes.RECT), ("flags", wintypes.DWORD)]

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.MonitorFromWindow.argtypes = (wintypes.HWND, wintypes.DWORD)
        user32.MonitorFromWindow.restype = wintypes.HANDLE
        user32.GetMonitorInfoW.argtypes = (wintypes.HANDLE, ctypes.POINTER(MonitorInfo))
        user32.GetMonitorInfoW.restype = wintypes.BOOL
        monitor = user32.MonitorFromWindow(root.winfo_id(), 2)
        info = MonitorInfo(size=ctypes.sizeof(MonitorInfo))
        if monitor and user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return info.work.left, info.work.top, info.work.right, info.work.bottom
    left, top = root.winfo_vrootx(), root.winfo_vrooty()
    return left, top, left + root.winfo_vrootwidth(), top + root.winfo_vrootheight()


class BrowserApp:
    def __init__(self, root, store):
        self.root, self.store = root, store
        self.tokens = load_tokens(store.tokens_path)
        self.gap = self.tokens["spacing"]
        self.theme = tk.StringVar(master=root, value="light")
        self.query = tk.StringVar(master=root)
        self.platform = tk.StringVar(master=root, value=PLATFORMS[0])
        self.scene = tk.StringVar(master=root, value=SCENES[0])
        self.count = tk.StringVar(master=root)
        self.status = tk.StringVar(master=root, value="离线资料已就绪。选择条目，查看说明或复制采用建议。")
        self.current = None
        self.preview = None
        self._help = None
        self._closed = False
        self._filtering = False
        self._traces = []
        apply_theme(root, "light", tokens_path=store.tokens_path)
        root.title("UI_Center")
        if root.tk.call("tk", "windowingsystem") == "win32":
            icon = str(store.root / "apps" / "desktop" / "app.ico")
            root.iconbitmap(default=icon)
            root.iconbitmap(icon)
        root.geometry("1080x760")
        root.minsize(820, 600)
        self._build()
        for variable in (self.query, self.platform, self.scene):
            self._traces.append((variable, variable.trace_add("write", self.refresh_entries)))
        self._traces.append((self.theme, self.theme.trace_add("write", self.change_theme)))
        self.change_theme()
        self.refresh_entries()
        self._bind_shortcuts(root)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.search_entry.focus_set()

    def _build(self):
        g = self.gap
        shell = ttk.Frame(self.root, padding=g["lg"])
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(3, weight=1)
        header = ttk.Frame(shell)
        header.grid(row=0, column=0, sticky="ew", pady=(0, g["sm"]))
        ttk.Label(header, text="UI_Center", style="UIC.Heading.TLabel").pack(side="left")
        ttk.Label(header, text="  界面规范与组件", style="UIC.Muted.TLabel").pack(side="left", pady=(g["xs"], 0))
        ttk.Button(header, text="使用帮助", command=self.show_help).pack(side="right")
        for title, value in (("深色", "dark"), ("浅色", "light")):
            ttk.Radiobutton(header, text=title, variable=self.theme, value=value, takefocus=True).pack(side="right", padx=g["xs"])
        ttk.Label(shell, text="先查规范，再选源码；采用后在你的程序中验证。",
                  style="UIC.Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(0, g["md"]))
        search = ttk.Frame(shell)
        search.grid(row=2, column=0, sticky="ew", pady=(0, g["lg"]))
        ttk.Label(search, text="查找条目").pack(side="left", padx=(0, g["sm"]))
        self.search_entry = ttk.Entry(search, textvariable=self.query, takefocus=True)
        self.search_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(search, text="清空", command=self.clear_search).pack(side="left", padx=(g["sm"], 0))
        ttk.Label(search, text="  Ctrl+F / Esc", style="UIC.Muted.TLabel").pack(side="left")
        panes = ttk.Panedwindow(shell, orient="horizontal")
        panes.grid(row=3, column=0, sticky="nsew")
        navigation = ttk.Frame(panes, width=275, padding=(0, 0, g["md"], 0))
        panes.add(navigation, weight=0)
        self.content = ttk.Frame(panes, padding=(g["md"], 0, 0, 0))
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(3, weight=1)
        panes.add(self.content, weight=1)
        ttk.Label(navigation, text="平台", style="UIC.Muted.TLabel").pack(anchor="w")
        self.platform_picker = ttk.Combobox(navigation, textvariable=self.platform, state="readonly",
                                           values=PLATFORMS, width=23, takefocus=True)
        self.platform_picker.pack(fill="x", pady=(g["xs"], g["md"]))
        ttk.Label(navigation, text="场景", style="UIC.Muted.TLabel").pack(anchor="w")
        self.scene_picker = ttk.Combobox(navigation, textvariable=self.scene, state="readonly",
                                        values=SCENES, width=23, takefocus=True)
        self.scene_picker.pack(fill="x", pady=(g["xs"], g["md"]))
        ttk.Label(navigation, textvariable=self.count, style="UIC.Muted.TLabel").pack(anchor="w", pady=(0, g["sm"]))
        results = ttk.Frame(navigation)
        results.pack(fill="both", expand=True)
        self.entries = ttk.Treeview(results, show="tree", selectmode="browse", height=16, takefocus=True)
        self.entries.column("#0", width=240, minwidth=190, stretch=True)
        scroll = ttk.Scrollbar(results, orient="vertical", command=self.entries.yview)
        self.entries.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.entries.pack(fill="both", expand=True)
        self.entries.bind("<<TreeviewSelect>>", self._selection_changed)
        ttk.Label(navigation, text="平台筛选同时保留通用规范。\n搜索标题和摘要，可输入多个关键词。",
                  style="UIC.Muted.TLabel", wraplength=245).pack(fill="x", pady=(g["sm"], 0))
        self.title = ttk.Label(self.content, text="", style="UIC.Heading.TLabel", wraplength=650)
        self.title.grid(row=0, column=0, sticky="ew")
        self.boundary = ttk.Label(self.content, text="", style="UIC.Muted.TLabel", wraplength=650)
        self.boundary.grid(row=1, column=0, sticky="ew", pady=(g["xs"], g["sm"]))
        self.summary = ttk.Label(self.content, text="", wraplength=650)
        self.summary.grid(row=2, column=0, sticky="ew", pady=(0, g["md"]))
        self.tabs = ttk.Notebook(self.content, takefocus=True)
        self.tabs.grid(row=3, column=0, sticky="nsew")
        self.description = DocumentReader(self.tabs, store=self.store)
        self.usage = DocumentReader(self.tabs, store=self.store)
        self.tabs.add(self.description, text="  说明  ")
        self.tabs.add(self.usage, text="  用法 / 原文  ")
        self.content.bind("<Configure>", self._resize_text)
        actions = ttk.Frame(self.content)
        actions.grid(row=4, column=0, sticky="ew", pady=(g["md"], 0))
        self.copy_ai_button = ttk.Button(actions, text="复制给 AI 的采用说明", command=self.copy_ai,
                                         style="UIC.Primary.TButton")
        self.copy_ai_button.pack(side="left")
        self.copy_usage_button = ttk.Button(actions, text="复制用法", command=self.copy_usage)
        self.copy_usage_button.pack(side="left", padx=g["sm"])
        self.preview_button = ttk.Button(actions, text="预览组件", command=self.open_preview)
        self.preview_button.pack(side="left")
        source = ttk.Frame(self.content)
        source.grid(row=5, column=0, sticky="ew", pady=(g["sm"], 0))
        self.source_label = ttk.Label(source, text="", style="UIC.Muted.TLabel")
        self.source_label.pack(side="left")
        self.source_button = ttk.Button(source, text="在 GitHub 查看原文", command=self.open_source)
        self.source_button.pack(side="right")
        footer = ttk.Frame(shell)
        footer.grid(row=4, column=0, sticky="ew", pady=(g["md"], 0))
        footer.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(footer, textvariable=self.status, style="UIC.Muted.TLabel", wraplength=850)
        self.status_label.grid(row=0, column=0, sticky="ew")
        ttk.Label(footer, text="v" + self.store.version, style="UIC.Muted.TLabel").grid(row=0, column=1, sticky="e", padx=(g["sm"], 0))
        self.status_label.bind("<Configure>", lambda event: self.status_label.configure(wraplength=max(200, event.width)))

    def _resize_text(self, event):
        width = max(280, event.width - self.gap["lg"])
        for label in (self.title, self.boundary, self.summary):
            label.configure(wraplength=width)

    def _bind_shortcuts(self, widget):
        # Per-widget bindings run before Text/Entry class editing bindings.
        widget.bind("<Control-f>", self.focus_search, add="+")
        widget.bind("<Escape>", self.clear_search, add="+")
        if isinstance(widget, tk.Text):
            widget.bind("<Tab>", lambda event: self._move_focus(event, False))
            widget.bind("<Shift-Tab>", lambda event: self._move_focus(event, True))
        for child in widget.winfo_children():
            self._bind_shortcuts(child)

    @staticmethod
    def _move_focus(event, previous):
        target = event.widget.tk_focusPrev() if previous else event.widget.tk_focusNext()
        if target is not None:
            target.focus_set()
        return "break"

    def focus_search(self, _event=None):
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, "end")
        return "break"

    def clear_search(self, _event=None):
        self.query.set("")
        self.search_entry.focus_set()
        return "break"

    def refresh_entries(self, *_args):
        previous = self.current.key if self.current is not None else None
        filtered = filter_entries(self.query.get(), self.platform.get(), self.scene.get())
        self._filtering = True
        children = self.entries.get_children()
        if children:
            self.entries.delete(*children)
        for entry in filtered:
            self.entries.insert("", "end", iid=entry.key, text=entry.title)
        self.count.set(f"{len(filtered)} 个条目")
        selected = previous if previous in {entry.key for entry in filtered} else (filtered[0].key if filtered else None)
        self._filtering = False
        if selected:
            self.entries.selection_set(selected)
            self.entries.focus(selected)
            self.entries.see(selected)
            self.show_entry(next(entry for entry in filtered if entry.key == selected))
        else:
            self.show_empty()

    def _selection_changed(self, _event=None):
        if not self._filtering:
            selection = self.entries.selection()
            if selection:
                self.show_entry(next(entry for entry in ENTRIES if entry.key == selection[0]))

    def select_entry(self, key):
        self.query.set("")
        self.platform.set(PLATFORMS[0])
        self.scene.set(SCENES[0])
        self.entries.selection_set(key)
        self.entries.focus(key)
        self.entries.see(key)
        self.show_entry(next(entry for entry in ENTRIES if entry.key == key))

    def show_empty(self):
        self.current = None
        self.title.configure(text="没有找到匹配条目")
        self.boundary.configure(text="调整关键词，或选择全部平台与全部场景。")
        self.summary.configure(text="可试试：取消、焦点、主题、参数。")
        self.description.show("搜索范围为标题和摘要。\n清空搜索后，可继续从左侧选择平台和场景。", markdown=False)
        self.usage.show("当前没有可复制的条目。", markdown=False)
        for button in (self.copy_ai_button, self.copy_usage_button, self.preview_button, self.source_button):
            button.state(["disabled"])
        self.source_label.configure(text="")

    def show_entry(self, entry):
        self.current = entry
        self.title.configure(text=entry.title)
        self.boundary.configure(text=entry.boundary)
        self.summary.configure(text=entry.summary)
        self.description.show(body_for(self.store, entry), resource=entry.resource)
        self.usage.show(usage_for(self.store, entry), resource=entry.resource,
                        markdown=not entry.language and entry.key != "tokens")
        self.copy_ai_button.state(["!disabled"])
        self.copy_usage_button.state(["!disabled"])
        self.copy_usage_button.configure(text="复制用法" if entry.language or entry.key == "tokens" else "复制原文")
        self.preview_button.state(["!disabled" if entry.preview else "disabled"])
        self.source_button.state(["!disabled" if self.store.commit else "disabled"])
        identity = self.store.commit[:12] if self.store.commit else "尚未固定提交"
        self.source_label.configure(text=("来源 " if self.store.frozen else "开发工作区 · HEAD ") + identity)

    def _copy(self, text, label):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update_idletasks()
        self.status.set(label + "已复制。采用时保留来源提交和许可。")

    def copy_usage(self):
        if self.current is not None:
            self._copy(usage_for(self.store, self.current), "用法" if self.current.language else "原文")

    def copy_ai(self):
        if self.current is not None:
            self._copy(adoption_note(self.store, self.current), "采用说明")

    def open_source(self):
        if self.current is not None:
            url = self.store.github_url(self.current.resource)
            if url:
                webbrowser.open(url)

    def open_preview(self):
        if self.current is None or not self.current.preview:
            return None
        if self.preview is not None and not self.preview._closed:
            self.preview.root.deiconify()
            self.preview.root.lift()
            return self.preview
        top = tk.Toplevel(self.root)
        top.withdraw()
        top.title("UI_Center · 组件预览")
        top.transient(self.root)
        self.preview = DemoWindow(top, tokens_path=self.store.tokens_path, theme_variable=self.theme)
        top.title("UI_Center · 组件预览")
        top.bind("<Destroy>", self._preview_destroyed, add="+")
        left, upper, right, bottom = work_area(self.root)
        width, height = min(760, right - left - 32), min(650, bottom - upper - 64)
        top.minsize(min(580, width), min(570, height))
        x = min(max(self.root.winfo_rootx() + (self.root.winfo_width() - width) // 2, left + 8), right - width - 8)
        y = min(max(self.root.winfo_rooty() + (self.root.winfo_height() - height) // 2, upper + 32), bottom - height - 32)
        top.geometry(f"{width}x{height}+{x}+{y}")
        top.deiconify()
        self.status.set("预览使用虚构数据；主题与主窗口同步，已有输入和任务会保留。")
        return self.preview

    def _preview_destroyed(self, event):
        if self.preview is not None and event.widget is self.preview.root:
            self.preview = None

    def change_theme(self, *_args):
        palette = apply_theme(self.root, self.theme.get(), tokens_path=self.store.tokens_path)
        for reader in (self.description, self.usage):
            reader.apply_palette(palette, self.tokens)
        # ttk Radiobutton/Notebook are used by the browser in addition to the
        # original demo's widgets. Keep their active/selected states explicit.
        style = ttk.Style(self.root)
        style.configure("TRadiobutton", background=palette["background"], foreground=palette["foreground"],
                        indicatorbackground=palette["input_background"], indicatorforeground=palette["selected_foreground"])
        style.map("TRadiobutton", background=[("active", palette["background"])],
                  indicatorbackground=[("selected", palette["accent"])])
        style.configure("TNotebook", background=palette["background"], bordercolor=palette["border"])
        style.configure("TNotebook.Tab", background=palette["background"], foreground=palette["muted"],
                        padding=(self.gap["md"], self.gap["sm"]))
        style.map("TNotebook.Tab", background=[("selected", palette["surface"]), ("active", palette["hover"])],
                  foreground=[("selected", palette["foreground"])])

    def show_help(self):
        if self._help is not None and self._help.winfo_exists():
            self._help.lift()
            return
        self._help = top = tk.Toplevel(self.root)
        top.title("UI_Center · 使用帮助")
        top.geometry("620x400")
        top.transient(self.root)
        frame = ttk.Frame(top, padding=self.gap["lg"])
        frame.pack(fill="both", expand=True)
        text = ("1. 用标题、摘要关键词搜索，或在左侧选择平台和场景。\n\n"
                "2. 阅读条目的能力边界，再复制用法或给 AI 的采用说明。\n\n"
                "3. Tkinter 组件可打开真实预览；所有任务都是虚构数据。\n\n"
                "4. Android 条目仅为源码参考，尚未设备实测；规范不等于现成实现。\n\n"
                "5. Ctrl+F 聚焦搜索，Esc 清空关键词；Tab 移动焦点。\n\n"
                "资料离线可读。只有主动点击 GitHub 链接时才打开浏览器；不自动联网、保存配置或写业务文件。")
        ttk.Label(frame, text=text, wraplength=570, justify="left").pack(fill="both", expand=True)
        ttk.Button(frame, text="关闭", command=top.destroy).pack(anchor="e", pady=(self.gap["md"], 0))
        apply_theme(top, self.theme.get(), tokens_path=self.store.tokens_path)

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self.preview is not None:
            self.preview.close()
        for variable, callback in self._traces:
            variable.trace_remove("write", callback)
        self._traces.clear()
        self.root.destroy()

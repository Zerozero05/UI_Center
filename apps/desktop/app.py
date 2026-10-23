"""Offline component workbench, Chinese guidance and source adoption."""
import os
import tkinter as tk
from tkinter import font as tkfont, ttk
import webbrowser

from ui_center import apply_theme, load_tokens
from ui_center.feedback import EmptyState
from ui_center.overlays import close_active_overlay
from examples.tkinter.demo import DemoWindow

from .catalog import (ENTRIES, PLATFORMS, SCENES, SECTIONS, adoption_note, available_platforms,
                      available_scenes, body_for, filter_entries, section_for, source_notes, usage_for)
from .preferences import Preferences, THEMES, MOTIONS, program_directory, reduced_motion
from .previews import create_preview
from .reader import DocumentReader
from .parameters import ParameterForm
from .scrolling import AutoScrollbar


def work_area(root):
    """Usable monitor rectangle, including Windows taskbar reservations."""
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
    x, y = root.winfo_vrootx(), root.winfo_vrooty()
    return x, y, x + root.winfo_vrootwidth(), y + root.winfo_vrootheight()


class PreviewSurface(ttk.Frame):
    """Scrollable controls stay reachable at large font sizes."""
    def __init__(self, master):
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, highlightthickness=0, width=400, height=240)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vertical = vertical = AutoScrollbar(self, orient="vertical", command=self.canvas.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        self.horizontal = horizontal = AutoScrollbar(self, orient="horizontal", command=self.canvas.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.host = ttk.Frame(self.canvas)
        self.window = self.canvas.create_window(0, 0, window=self.host, anchor="nw")
        self.host.columnconfigure(0, weight=1)
        self.host.bind("<Configure>", self._size)
        self.canvas.bind("<Configure>", self._size)

    def bind_scroll(self, widget):
        if isinstance(widget, (ttk.Frame, ttk.Label, tk.Frame, tk.Label, tk.Canvas)):
            widget.bind("<MouseWheel>", self._wheel, add="+")
        for child in widget.winfo_children():
            self.bind_scroll(child)

    def _wheel(self, event):
        if self.vertical.winfo_ismapped():
            self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
            return "break"

    def _size(self, _event=None):
        self.canvas.itemconfigure(self.window, width=max(self.canvas.winfo_width(), self.host.winfo_reqwidth()))
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def apply_palette(self, palette):
        self.canvas.configure(background=palette["background"])


class PreviewWindow:
    def __init__(self, app, entry):
        self._closed = False
        self.entry_key = entry.key
        self.root = tk.Toplevel(app.root)
        self.root.title("UI_Center · " + entry.title)
        self.root.transient(app.root)
        self.root.geometry("760x620")
        self.root.minsize(520, 420)
        self.surface = PreviewSurface(self.root)
        self.surface.pack(fill="both", expand=True)
        self.view = create_preview(entry.preview_id, self.surface.host, palette=app.palette,
                                   reduced_motion=app.motion_reduced, spacing=app.gap)
        self.view.grid(row=0, column=0, sticky="nsew")
        self.surface.bind_scroll(self.view)
        self.surface.apply_palette(app.palette)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Escape>", self._escape)
        self.root.bind("<Unmap>", lambda e: self.view.set_visible(False) if e.widget is self.root else None)
        self.root.bind("<Map>", lambda e: self.view.set_visible(bool(self.root.winfo_viewable()))
                       if e.widget is self.root else None)

    def _escape(self, _event=None):
        close_active_overlay(self.root)
        return "break"

    def close(self):
        if not self._closed:
            self._closed = True
            self.view.dispose()
            self.root.destroy()


class BrowserApp:
    def __init__(self, root, store, *, preferences_path=None):
        self.root, self.store = root, store
        self.tokens = load_tokens(store.tokens_path)
        self.gap = self.tokens["spacing"]
        self.preferences = Preferences(preferences_path)
        saved = self.preferences.load()
        self.theme = tk.StringVar(master=root, value=saved["theme"])
        self.font_scale = tk.IntVar(master=root, value=saved["font_scale"])
        self.motion = tk.StringVar(master=root, value=saved["motion"])
        self.theme_label = tk.StringVar(master=root, value=self._label(THEMES, saved["theme"]))
        self.motion_label = tk.StringVar(master=root, value=self._label(MOTIONS, saved["motion"]))
        self.query = tk.StringVar(master=root)
        self.section = tk.StringVar(master=root, value=SECTIONS[0])
        self.platform = tk.StringVar(master=root, value=PLATFORMS[0])
        self.scene = tk.StringVar(master=root, value=SCENES[0])
        self.count = tk.StringVar(master=root)
        self.status = tk.StringVar(master=root, value=self.preferences.notice or "选择组件即可操作真实预览；用法和源码分别查看。")
        self.current = self.preview = self.live_view = self._help = None
        self._help_reader = None
        self.help_program_path = tk.StringVar(master=root)
        self.help_settings_path = tk.StringVar(master=root)
        self.help_location_status = tk.StringVar(master=root)
        self._closed = self._filtering = self._appearance_changing = False
        self._traces = []
        self._header_pending = None
        self._header_inline = None
        self.motion_reduced = reduced_motion(self.motion.get())
        if "Microsoft YaHei UI" in tkfont.families(root):
            for name in ("TkDefaultFont", "TkTextFont"):
                tkfont.nametofont(name, root=root).configure(family="Microsoft YaHei UI")
        self.palette = apply_theme(root, self.theme.get(), tokens_path=store.tokens_path, font_scale=self.scale)
        root.title("UI_Center")
        if root.tk.call("tk", "windowingsystem") == "win32":
            icon = str(store.root / "apps" / "desktop" / "app.ico")
            root.iconbitmap(default=icon)
            root.iconbitmap(icon)
        left, top, right, bottom = work_area(root)
        width, height = min(1180, right - left - 32), min(820, bottom - top - 64)
        root.geometry(f"{width}x{height}+{left + 16}+{top + 32}")
        root.minsize(min(820, width), min(600, height))
        self._build()
        for variable in (self.query, self.platform, self.scene, self.section):
            self._trace(variable, self.refresh_entries)
        for variable in (self.theme, self.font_scale, self.motion):
            self._trace(variable, self.change_theme)
        self._trace(self.theme_label, self._theme_selected)
        self._trace(self.motion_label, self._motion_selected)
        self.change_theme(save=False)
        self.refresh_entries()
        self._bind_shortcuts(root)
        root.bind("<Unmap>", self._visibility, add="+")
        root.bind("<Map>", self._visibility, add="+")
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.search_entry.focus_set()

    @property
    def scale(self):
        return 1.2 * self.font_scale.get() / 100

    @staticmethod
    def _label(mapping, value):
        return next(title for title, key in mapping.items() if key == value)

    def _trace(self, variable, callback):
        self._traces.append((variable, variable.trace_add("write", callback)))

    def _theme_selected(self, *_args):
        if not self._appearance_changing:
            self.theme.set(THEMES[self.theme_label.get()])

    def _motion_selected(self, *_args):
        if not self._appearance_changing:
            self.motion.set(MOTIONS[self.motion_label.get()])

    def _build(self):
        g = self.gap
        shell = ttk.Frame(self.root, padding=g["lg"])
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(2, weight=1)
        self.header = header = ttk.Frame(shell)
        header.grid(row=0, column=0, sticky="ew", pady=(0, g["sm"]))
        header.columnconfigure(1, weight=1)
        self.brand = ttk.Frame(header)
        self.brand.grid(row=0, column=0, sticky="w")
        ttk.Label(self.brand, text="UI_Center", style="UIC.Heading.TLabel").pack(anchor="w")
        ttk.Label(self.brand, text="组件与界面规范", style="UIC.Muted.TLabel").pack(anchor="w")
        self.appearance_form = appearance = ParameterForm(header, palette=self.palette)
        appearance.grid(row=0, column=1, sticky="ew", padx=g["lg"])
        appearance.combo("主题", self.theme, tuple((key, label) for label, key in THEMES.items()), width=9)
        appearance.combo("字号", self.font_scale, ((100, "100%"), (125, "125%"), (150, "150%")), width=5)
        appearance.combo("动画", self.motion, tuple((key, label) for label, key in MOTIONS.items()), width=8)
        self.help_button = ttk.Button(header, text="使用帮助", command=self.show_help, style="UIC.Secondary.TButton")
        self.help_button.grid(row=0, column=2, sticky="ne")
        header.bind("<Configure>", self._queue_header)
        search = ttk.Frame(shell)
        search.grid(row=1, column=0, sticky="ew", pady=(0, g["md"]))
        self.search_label = ttk.Label(search)
        self.search_label.pack(side="left", padx=(0, g["sm"]))
        self.search_entry = ttk.Entry(search, textvariable=self.query)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.clear_search_button = ttk.Button(search, text="清空关键词", command=self.clear_search)
        self.clear_search_button.pack(side="left", padx=(g["sm"], 0))
        self.panes = ttk.Panedwindow(shell, orient="horizontal")
        self.panes.grid(row=2, column=0, sticky="nsew")
        navigation = ttk.Frame(self.panes, width=245, padding=(0, 0, g["sm"], 0))
        self.panes.add(navigation, weight=0)
        self.content = ttk.Frame(self.panes, padding=(g["sm"], 0, 0, 0))
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(3, weight=1)
        self.panes.add(self.content, weight=1)
        for title, variable, values, name in (("内容", self.section, SECTIONS, "section_picker"),
                ("平台", self.platform, PLATFORMS, "platform_picker"),
                ("场景", self.scene, SCENES, "scene_picker")):
            ttk.Label(navigation, text=title, style="UIC.Muted.TLabel").pack(anchor="w")
            picker = ttk.Combobox(navigation, textvariable=variable, values=values, state="readonly", width=18)
            picker.pack(fill="x", pady=(2, g["sm"]))
            setattr(self, name, picker)
        ttk.Label(navigation, textvariable=self.count, style="UIC.Muted.TLabel").pack(anchor="w", pady=(0, 4))
        results = ttk.Frame(navigation)
        results.pack(fill="both", expand=True)
        self.entries = ttk.Treeview(results, show="tree", selectmode="browse", height=10)
        self.entries.column("#0", width=215, minwidth=130, stretch=True)
        scroll = AutoScrollbar(results, orient="vertical", command=self.entries.yview)
        self.entries.configure(yscrollcommand=scroll.set)
        results.columnconfigure(0, weight=1)
        results.rowconfigure(0, weight=1)
        scroll.grid(row=0, column=1, sticky="ns")
        self.entries.grid(row=0, column=0, sticky="nsew")
        self.entries.bind("<<TreeviewSelect>>", self._selection_changed)
        self.titlebar = titlebar = ttk.Frame(self.content)
        titlebar.grid(row=0, column=0, sticky="ew")
        titlebar.columnconfigure(0, weight=1)
        self.title = ttk.Label(titlebar, style="UIC.Heading.TLabel", wraplength=700)
        self.title.grid(row=0, column=0, sticky="ew")
        self.platform_badge = ttk.Label(titlebar, style="UIC.Muted.TLabel")
        self.platform_badge.grid(row=0, column=1, sticky="e", padx=(8, 0))
        self.boundary = ttk.Label(self.content, style="UIC.Muted.TLabel", wraplength=700)
        self.boundary.grid(row=1, column=0, sticky="ew", pady=(2, 4))
        self.summary = ttk.Label(self.content, wraplength=700)
        self.summary.grid(row=2, column=0, sticky="ew", pady=(0, g["sm"]))
        self.tabs = ttk.Notebook(self.content)
        self.tabs.grid(row=3, column=0, sticky="nsew")
        self.preview_surface = PreviewSurface(self.tabs)
        self.description = DocumentReader(self.tabs, store=self.store)
        self.usage = DocumentReader(self.tabs, store=self.store, horizontal=True)
        self.tabs.bind("<<NotebookTabChanged>>", self._tab_changed)
        self.content.bind("<Configure>", self._resize_text)
        self.entry_actions = actions = ParameterForm(self.content, palette=self.palette)
        actions.grid(row=4, column=0, sticky="ew", pady=(g["sm"], 0))
        self.copy_usage_button = ttk.Button(actions.group(""), text="复制示例", command=self.copy_usage,
                                            style="UIC.Primary.TButton")
        self.copy_ai_button = ttk.Button(actions.group(""), text="AI 说明", command=self.copy_ai, style="UIC.Secondary.TButton")
        self.preview_button = ttk.Button(actions.group(""), text="独立预览", command=self.open_preview, style="UIC.Secondary.TButton")
        self.source_button = ttk.Button(actions.group(""), text="GitHub", command=self.open_source, style="UIC.Secondary.TButton")
        for i, button in enumerate((self.copy_usage_button, self.copy_ai_button, self.preview_button, self.source_button)):
            button.pack(fill="x")
        self.source_label = ttk.Label(self.content, style="UIC.Muted.TLabel")
        self.source_label.grid(row=5, column=0, sticky="w")
        self.empty_state = EmptyState(self.content, palette=self.palette, kind="no-results",
                                      title="没有找到匹配条目", action_text="显示本类全部",
                                      on_action=self.show_section_entries)
        footer = ttk.Frame(shell)
        footer.grid(row=3, column=0, sticky="ew", pady=(g["sm"], 0))
        footer.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(footer, textvariable=self.status, style="UIC.Muted.TLabel", wraplength=900)
        self.status_label.grid(row=0, column=0, sticky="ew")
        ttk.Label(footer, text="v" + self.store.version, style="UIC.Muted.TLabel").grid(row=0, column=1, sticky="e")
        self.status_label.bind("<Configure>", lambda e: self.status_label.configure(wraplength=max(180, e.width)))

    def _queue_header(self, _event=None):
        if not self._closed and self._header_pending is None:
            self._header_pending = self.root.after_idle(self._layout_header)

    def _layout_header(self):
        self._header_pending = None
        required = self.brand.winfo_reqwidth() + self.appearance_form.preferred_width() + self.help_button.winfo_reqwidth() + 32
        inline = required <= self.header.winfo_width()
        if inline != self._header_inline:
            self._header_inline = inline
            self.appearance_form.grid(row=0 if inline else 1, column=1 if inline else 0,
                                      columnspan=1 if inline else 3, sticky="ew",
                                      padx=16 if inline else 0, pady=0 if inline else (8, 0))

    def _resize_text(self, event=None):
        width = max(180, (event.width if event else self.content.winfo_width()) - self.gap["md"])
        badge_width = self.platform_badge.winfo_reqwidth() + 8 if self.current and self.current.preview else 0
        self.title.configure(wraplength=max(140, width - badge_width))
        for label in (self.boundary, self.summary):
            label.configure(wraplength=width)

    def _bind_shortcuts(self, widget):
        if not getattr(widget, "_uic_shortcuts_bound", False):
            widget._uic_shortcuts_bound = True
            if isinstance(widget, (ttk.Frame, ttk.Label, ttk.LabelFrame, tk.Frame, tk.Label, tk.Canvas)):
                if str(widget.cget("takefocus")) not in ("1", "true", "yes"):
                    widget.configure(takefocus=False)
            widget.bind("<Control-f>", self.focus_search, add="+")
            widget.bind("<Escape>", self.clear_search, add="+")
            if isinstance(widget, tk.Text):
                widget.bind("<Tab>", lambda e: self._move_focus(e, False))
                widget.bind("<Shift-Tab>", lambda e: self._move_focus(e, True))
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
        if close_active_overlay(self.root):
            return "break"
        self.query.set("")
        self.search_entry.focus_set()
        return "break"

    def refresh_entries(self, *_args, preferred_key=None):
        if self._filtering:
            return
        previous = preferred_key or (self.current.key if self.current else None)
        self._filtering = True
        notices = []
        try:
            section = self.section.get()
            platforms = available_platforms(section)
            self.platform_picker.configure(values=platforms)
            if self.platform.get() not in platforms:
                notices.append(f"平台“{self.platform.get()}”不适用于“{section}”，已恢复为全部平台。")
                self.platform.set(PLATFORMS[0])
            scenes = available_scenes(section, self.platform.get())
            self.scene_picker.configure(values=scenes)
            if self.scene.get() not in scenes:
                notices.append(f"场景“{self.scene.get()}”不适用于当前分类及平台，已恢复为全部场景。")
                self.scene.set(SCENES[0])
            self.search_label.configure(text=f"在“{section}”中查找")
            filtered = filter_entries(self.query.get(), self.platform.get(), self.scene.get(), section)
            children = self.entries.get_children()
            if children != tuple(entry.key for entry in filtered):
                if children:
                    self.entries.delete(*children)
                for entry in filtered:
                    self.entries.insert("", "end", iid=entry.key, text=entry.title)
            self.count.set(f"{len(filtered)} 个条目")
            selected = next((entry for entry in filtered if entry.key == previous), filtered[0] if filtered else None)
        finally:
            self._filtering = False
        if selected:
            self.entries.selection_set(selected.key)
            self.entries.focus(selected.key)
            self.entries.see(selected.key)
            self.show_entry(selected)
        else:
            self.show_empty()
        if notices:
            self.status.set(" ".join(notices))

    def show_section_entries(self):
        self._filtering = True
        try:
            self.query.set("")
            self.platform.set(PLATFORMS[0])
            self.scene.set(SCENES[0])
        finally:
            self._filtering = False
        self.refresh_entries()
        self.search_entry.focus_set()
        self.status.set(f"已显示“{self.section.get()}”全部条目。")

    def _selection_changed(self, _event=None):
        selection = self.entries.selection()
        if not self._filtering and selection:
            self.show_entry(next(entry for entry in ENTRIES if entry.key == selection[0]))

    def select_entry(self, key):
        entry = next(entry for entry in ENTRIES if entry.key == key)
        self._filtering = True
        self.query.set("")
        self.platform.set(PLATFORMS[0])
        self.scene.set(SCENES[0])
        self.section.set(section_for(entry))
        self._filtering = False
        self.refresh_entries(preferred_key=key)

    def _dispose_views(self):
        if self.preview is not None:
            self.preview.close()
            self.preview = None
        if self.live_view is not None:
            self.live_view.dispose()
            self.live_view = None

    def _set_tabs(self, preview=False, code=False):
        for tab in self.tabs.tabs():
            self.tabs.forget(tab)
        if preview:
            self.tabs.add(self.preview_surface, text="实时预览")
        self.tabs.add(self.description, text="中文用法" if code else "规范 / 原文")
        if code:
            self.tabs.add(self.usage, text="示例与源码")
        self.tabs.select(self.preview_surface if preview else self.description)

    def show_empty(self):
        focus = self.root.focus_get()
        move_focus = focus is not None and any(str(focus).startswith(str(widget) + ".") or focus is widget
                                               for widget in (self.tabs, self.entry_actions))
        self._dispose_views()
        self.current = None
        for widget in (self.titlebar, self.boundary, self.summary, self.tabs,
                       self.entry_actions, self.source_label):
            widget.grid_remove()
        query = self.query.get().strip()
        reason = f"当前范围内未找到关键词“{query}”。" if query else "当前分类及筛选条件中没有条目。"
        self.empty_state.set_state("no-results", title="没有找到匹配条目",
            message=f"{reason}\n\n内容：{self.section.get()}\n平台：{self.platform.get()} · 场景：{self.scene.get()}\n\n"
                    "搜索仅查找当前分类的中文名称、英文别名、摘要和场景。",
            action_text="显示本类全部")
        self.empty_state.grid(row=0, column=0, rowspan=4, sticky="nsew")
        for button in (self.copy_ai_button, self.copy_usage_button, self.preview_button, self.source_button):
            button.state(["disabled"])
        self.source_label.configure(text="")
        if move_focus:
            self.empty_state.action.focus_set()

    def show_entry(self, entry):
        if self.current is not None and self.current.key == entry.key:
            return
        self._dispose_views()
        self.current = entry
        self.empty_state.grid_remove()
        for widget in (self.titlebar, self.tabs, self.entry_actions, self.source_label):
            widget.grid()
        self.title.configure(text=entry.title)
        self.boundary.configure(text=entry.boundary)
        self.summary.configure(text=entry.summary)
        if entry.preview:
            self.summary.grid_remove()
            self.boundary.grid_remove()
            self.platform_badge.configure(text="Tkinter · 虚构数据")
            self.platform_badge.grid()
        else:
            self.summary.grid()
            self.boundary.grid()
            self.platform_badge.grid_remove()
        self._resize_text()
        self.description.show(body_for(self.store, entry), resource=entry.resource)
        if entry.preview:
            self.live_view = create_preview(entry.preview_id, self.preview_surface.host,
                                            palette=self.palette, reduced_motion=self.motion_reduced,
                                            spacing=self.gap)
            self.live_view.grid(row=0, column=0, sticky="nsew")
            self.preview_surface.bind_scroll(self.live_view)
            self._bind_shortcuts(self.live_view)
            self.preview_surface.canvas.yview_moveto(0)
            self.preview_surface.canvas.xview_moveto(0)
        self._set_tabs(entry.preview, bool(entry.language) or entry.key == "tokens")
        self._show_code()
        for button in (self.copy_ai_button, self.copy_usage_button):
            button.state(["!disabled"])
        self.copy_usage_button.configure(text="复制示例" if entry.language else "复制原文")
        self.preview_button.state(["!disabled" if entry.preview else "disabled"])
        self.source_button.state(["!disabled" if self.store.commit else "disabled"])
        identity = self.store.commit[:12] if self.store.commit else "尚未固定提交"
        self.source_label.configure(text=("来源 " if self.store.frozen else "开发工作区 · HEAD ") + identity)

    def current_code(self):
        if self.current is None:
            return ""
        if self.live_view is not None and self.current.preview:
            return self.live_view.code()
        return usage_for(self.store, self.current) or body_for(self.store, self.current)

    def reset_preview(self):
        if self.live_view is not None:
            self.live_view.reset()
            self.status.set("当前组件已恢复默认参数；界面偏好保持不变。")

    def _show_code(self):
        if self.current and (self.current.language or self.current.key == "tokens"):
            language = self.current.language or "json"
            self.usage.show("## 当前参数示例\n\n```" + language + "\n" + self.current_code().rstrip() +
                            "\n```\n\n" + source_notes(self.store, self.current), resource=self.current.resource)

    def _tab_changed(self, _event=None):
        if self.live_view is not None:
            self.live_view.set_visible(self.tabs.select() == str(self.preview_surface)
                                       and bool(self.root.winfo_viewable())
                                       and self.root.state() not in ("iconic", "withdrawn"))
        if self.tabs.select() == str(self.usage):
            self._show_code()

    def _visibility(self, event):
        if event.widget is self.root and self.live_view is not None:
            self.live_view.set_visible(event.type == tk.EventType.Map and bool(self.root.winfo_viewable())
                                       and self.tabs.select() == str(self.preview_surface))

    def _copy(self, text, label):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update_idletasks()
        self.status.set(label + "已复制。采用时保留来源提交和许可。")

    def copy_usage(self):
        if self.current:
            self._copy(self.current_code(), "当前示例" if self.current.language else "原文")

    def copy_ai(self):
        if self.current:
            self._copy(adoption_note(self.store, self.current, self.current_code()), "采用说明")

    def open_source(self):
        if self.current:
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
        if self.current.key == "tk-theme":
            top = tk.Toplevel(self.root)
            self.preview = DemoWindow(top, tokens_path=self.store.tokens_path, theme_variable=self.theme,
                                      font_scale=self.scale)
            self.preview.entry_key = self.current.key
            self.change_theme(save=False)
        else:
            self.preview = PreviewWindow(self, self.current)
        self.preview.root.bind("<Destroy>", self._preview_destroyed, add="+")
        left, upper, right, bottom = work_area(self.root)
        width, height = min(760, right - left - 32), min(650, bottom - upper - 64)
        self.preview.root.geometry(f"{width}x{height}+{left + 24}+{upper + 32}")
        self.status.set("独立窗口使用同一组件实现和虚构数据；参数与内嵌预览各自独立。")
        return self.preview

    def _preview_destroyed(self, event):
        if self.preview is not None and event.widget is self.preview.root:
            self.preview = None

    def change_theme(self, *_args, save=True):
        if self._appearance_changing:
            return
        self._appearance_changing = True
        try:
            self.theme_label.set(self._label(THEMES, self.theme.get()))
            self.motion_label.set(self._label(MOTIONS, self.motion.get()))
            self.palette = palette = apply_theme(self.root, self.theme.get(), tokens_path=self.store.tokens_path,
                                                 font_scale=self.scale)
            self.appearance_form.apply_palette(palette)
            self.entry_actions.apply_palette(palette)
            self._queue_header()
            self.motion_reduced = reduced_motion(self.motion.get())
            for reader in (self.description, self.usage):
                reader.apply_palette(palette, self.tokens, font_scale=self.scale)
            if self._help_reader is not None and self._help_reader.winfo_exists():
                self._help_reader.apply_palette(palette, self.tokens, font_scale=self.scale)
            self.preview_surface.apply_palette(palette)
            self.empty_state.apply_palette(palette)
            if self.live_view is not None:
                self.live_view.apply_palette(palette)
                self.live_view.set_reduced_motion(self.motion_reduced)
            if self.preview is not None and hasattr(self.preview, "view"):
                self.preview.surface.apply_palette(palette)
                self.preview.view.apply_palette(palette)
                self.preview.view.set_reduced_motion(self.motion_reduced)
            elif self.preview is not None:
                self.preview.font_scale = self.scale
            style = ttk.Style(self.root)
            style.configure("TRadiobutton", background=palette["background"], foreground=palette["foreground"])
            style.configure("TCheckbutton", background=palette["background"], foreground=palette["foreground"])
            style.configure("TNotebook", background=palette["background"], bordercolor=palette["surface"], borderwidth=0)
            style.configure("TNotebook.Tab", background=palette["background"], foreground=palette["muted"], padding=(8, 6))
            style.map("TNotebook.Tab", background=[("selected", palette["surface"]), ("active", palette["hover"])],
                      foreground=[("selected", palette["foreground"])])
            self._resize_text()
            if save:
                self.preferences.save({"theme": self.theme.get(), "font_scale": self.font_scale.get(), "motion": self.motion.get()})
                self.status.set(self.preferences.notice or "界面偏好已保存；当前预览参数保持不变。")
                self._refresh_help_locations()
        finally:
            self._appearance_changing = False

    def show_help(self):
        if self._help is not None and self._help.winfo_exists():
            self._refresh_help_locations()
            self._help.lift()
            return
        self._help = top = tk.Toplevel(self.root)
        top.title("UI_Center · 使用帮助")
        top.geometry("720x620")
        frame = ttk.Frame(top, padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self._help_reader = reader = DocumentReader(frame, store=self.store)
        reader.grid(row=0, column=0, sticky="nsew")
        reader.show("## 选择、试用、采用\n\n"
                    "1. 在组件库按场景或中英文别名搜索；规范与来源在另外两个分类。\n\n"
                    "2. 在实时预览中调整参数、操作控件。隐藏预览后暂停动画；重置恢复该项默认值。\n\n"
                    "3. 中文用法说明用途、边界和参数；示例与源码显示当前参数代码及固定来源链接。\n\n"
                    "4. 复制当前示例或 AI 采用说明，带到目标项目验证。预览使用虚构任务。\n\n"
                    "5. Ctrl+F 搜索；Esc 优先关闭当前弹层，否则清空搜索；Tab 移动焦点。\n\n"
                    "6. 护眼主题是低刺激配色，不代表医学防护。减少动画保留静态等待和真实进度。\n\n"
                    "7. Android 为源码与构建参考，设备运行尚未验证。点击 GitHub 链接才打开浏览器。\n\n"
                    "界面偏好仅保存主题、字号与动画设置。\n\n"
                    "下方路径可选中后按 Ctrl+C 复制。打开目录不会创建文件或文件夹。")
        reader.apply_palette(self.palette, self.tokens, font_scale=self.scale)
        locations = ttk.LabelFrame(frame, text="文件与保存位置", padding=8)
        locations.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        locations.columnconfigure((0, 1), weight=1, uniform="location")
        ttk.Label(locations, text="当前程序目录", style="UIC.Muted.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w")
        self.help_program_entry = ttk.Entry(locations, textvariable=self.help_program_path, state="readonly")
        self.help_program_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 6))
        ttk.Label(locations, text="设置文件", style="UIC.Muted.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="w")
        self.help_settings_entry = ttk.Entry(locations, textvariable=self.help_settings_path, state="readonly")
        self.help_settings_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(2, 8))
        self.help_open_program_button = ttk.Button(locations, text="打开程序目录", command=self.open_program_directory)
        self.help_open_settings_button = ttk.Button(locations, text="打开设置目录", command=self.open_settings_directory)
        self.help_open_program_button.grid(row=4, column=0, sticky="ew", padx=(0, 4))
        self.help_open_settings_button.grid(row=4, column=1, sticky="ew", padx=(4, 0))
        location_status = ttk.Label(locations, textvariable=self.help_location_status,
                                    style="UIC.Muted.TLabel", wraplength=650)
        location_status.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        location_status.bind("<Configure>", lambda event: location_status.configure(wraplength=max(160, event.width)))
        self.help_close_button = ttk.Button(frame, text="关闭", command=top.destroy)
        self.help_close_button.grid(row=2, column=0, sticky="e", pady=(8, 0))
        self._refresh_help_locations()
        self._bind_shortcuts(top)

    def _refresh_help_locations(self):
        if self._help is None or not self._help.winfo_exists():
            return
        program = program_directory().resolve()
        settings = self.preferences.path.resolve()
        self.help_program_path.set(str(program))
        self.help_settings_path.set(str(settings))
        try:
            program_state = "程序目录可用。" if program.is_dir() else "程序目录不存在或无法访问。"
            if settings.is_file():
                settings_state = "设置文件已存在。"
            elif settings.exists():
                settings_state = "设置路径当前不是文件，保存可能失败。"
            elif settings.parent.is_dir():
                settings_state = "设置文件尚未创建；保存界面偏好时创建。"
            else:
                settings_state = "设置目录尚不存在；保存界面偏好时创建。"
            self.help_location_status.set(program_state + settings_state)
        except OSError:
            self.help_location_status.set("无法读取目录状态；你仍可复制上方完整路径。")

    def _open_help_directory(self, directory, label):
        self._refresh_help_locations()
        try:
            if not directory.is_dir():
                self.help_location_status.set(label + "不存在或不是文件夹；未打开，也未创建目录。")
                return
            os.startfile(directory)
        except AttributeError:
            self.help_location_status.set("当前系统不支持自动打开目录，请复制上方路径后手动打开。")
        except OSError as error:
            self.help_location_status.set("无法打开" + label + "，请复制上方路径后手动打开。系统提示：" + str(error))
        else:
            self.help_location_status.set("已请求打开" + label + "。")

    def open_program_directory(self):
        self._open_help_directory(program_directory().resolve(), "程序目录")

    def open_settings_directory(self):
        self._open_help_directory(self.preferences.path.resolve().parent, "设置目录")

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._header_pending is not None:
            self.root.after_cancel(self._header_pending)
            self._header_pending = None
        self._dispose_views()
        for variable, callback in self._traces:
            variable.trace_remove("write", callback)
        self._traces.clear()
        self.root.destroy()

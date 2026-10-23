"""Integration checks against actual workbench controls and local preferences."""
import ast
import ctypes
from contextlib import contextmanager
import json
from pathlib import Path
import sys
import tempfile
import time
import tkinter as tk
from tkinter import font as tkfont, ttk
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "tkinter"))

from apps.desktop.app import BrowserApp
from apps.desktop.catalog import CORE_COMPONENTS, ENTRIES, body_for, section_for
from apps.desktop.preferences import DEFAULTS, Preferences
from apps.desktop.resources import ResourceStore
from examples.tkinter.demo import DemoWindow
from ui_center.loading import (Spinner, ProgressBar, CircularProgress, Skeleton,
                               Shimmer, LoadingButton, PageLoader)
from ui_center.overlays import Dialog, ConfirmDialog, Drawer, Popover, Tooltip, active_overlay
from ui_center.navigation import Tabs, Accordion, SegmentedControl
from ui_center.feedback import InlineAlert, Toast, EmptyState

COMPONENTS = {
    "spinner": Spinner, "progress-bar": ProgressBar, "circular-progress": CircularProgress,
    "skeleton": Skeleton, "shimmer": Shimmer, "loading-button": LoadingButton,
    "page-loader": PageLoader, "dialog": Dialog, "confirm-dialog": ConfirmDialog,
    "drawer": Drawer, "popover": Popover, "tooltip": Tooltip, "tabs": Tabs,
    "accordion": Accordion, "segmented-control": SegmentedControl,
    "inline-alert": InlineAlert, "toast": Toast, "empty-state": EmptyState,
}


def work_directory(prefix):
    parent = ROOT / "work" / "workbench"
    parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=parent))


def clipboard_text(root):
    """Read the user's Unicode clipboard, avoiding Tk 8.6's 4000-byte read split."""
    if root.tk.call("tk", "windowingsystem") != "win32":
        return root.clipboard_get()
    from ctypes import wintypes
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.OpenClipboard.argtypes = (wintypes.HWND,)
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.argtypes = ()
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = (wintypes.UINT,)
    user32.GetClipboardData.restype = wintypes.HANDLE
    kernel32.GlobalLock.argtypes = (wintypes.HGLOBAL,)
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = (wintypes.HGLOBAL,)
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    if not user32.OpenClipboard(None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        handle = user32.GetClipboardData(13)  # CF_UNICODETEXT, as consumed by Windows apps.
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return ctypes.wstring_at(pointer).replace("\r\n", "\n")
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


@contextmanager
def visible_for_hit_testing(root):
    """Keep the test window above unrelated desktop apps; restore its own flag."""
    previous = root.attributes("-topmost")
    root.attributes("-topmost", True)
    root.lift()
    root.update()
    try:
        yield
    finally:
        root.attributes("-topmost", previous)


class PreferenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = work_directory("preferences-")
        self.path = self.directory / "preferences.json"

    def test_bad_json_uses_defaults_and_preserves_original_until_save(self):
        malformed = '{"theme": broken json'
        self.path.write_text(malformed, encoding="utf-8")
        preferences = Preferences(self.path)
        self.assertEqual(preferences.load(), DEFAULTS)
        self.assertIn("默认", preferences.notice)
        self.assertEqual(self.path.read_text(encoding="utf-8"), malformed)
        valid = {"theme": "sage", "font_scale": 125, "motion": "reduced"}
        self.assertTrue(preferences.save(valid))
        self.assertEqual(Preferences(self.path).load(), valid)
        self.assertEqual(preferences.notice, "")

    def test_unknown_values_rejected_and_save_contains_only_three_keys(self):
        preferences = Preferences(self.path)
        for values in ({"theme": "missing", "font_scale": 100, "motion": "normal"},
                       {"theme": "light", "font_scale": 99, "motion": "normal"},
                       {"theme": "light", "font_scale": 100, "motion": "missing"}, []):
            self.path.write_text(json.dumps(values), encoding="utf-8")
            self.assertEqual(preferences.load(), DEFAULTS)
            self.assertTrue(preferences.notice)
        values = {"theme": "dark", "font_scale": 150, "motion": "normal",
                  "query": "private search", "document": "private path"}
        self.assertTrue(preferences.save(values))
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(set(saved), {"theme", "font_scale", "motion"})
        self.assertNotIn("private", self.path.read_text(encoding="utf-8"))
        self.assertEqual(Preferences(self.path).load(), {key: values[key] for key in DEFAULTS})
        self.assertEqual(list(self.directory.glob("preferences-*.tmp")), [])

    def test_unwritable_parent_reports_failure_and_preserves_blocking_file(self):
        blocker = self.directory / "blocking-parent"
        blocker.write_text("KEEP THIS INPUT", encoding="utf-8")
        preferences = Preferences(blocker / "preferences.json")
        self.assertFalse(preferences.save(DEFAULTS))
        self.assertIn("无法保存", preferences.notice)
        self.assertEqual(blocker.read_text(encoding="utf-8"), "KEEP THIS INPUT")
        self.assertFalse(preferences.path.exists())


class WorkbenchIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = work_directory("app-")
        self.preferences_path = self.directory / "preferences.json"
        self.errors = []
        self._create_app()

    def _create_app(self, path=None):
        self.root = tk.Tk()
        self.root.report_callback_exception = lambda *details: self.errors.append(details)
        self.app = BrowserApp(self.root, ResourceStore(ROOT),
                              preferences_path=path or self.preferences_path)
        self.root.update()

    def tearDown(self):
        if not self.app._closed:
            self.app.close()
        self.assertEqual(self.errors, [], "Unexpected Tk callback exception")

    def update(self):
        self.root.update()

    def pump(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.root.update()
            time.sleep(.002)

    def test_legacy_previews_use_loaded_tokens_without_a_source_layout_lookup(self):
        with patch("ui_center.widgets.load_tokens", side_effect=FileNotFoundError("no source layout")):
            for key in ("tk-theme", "tk-actions", "tk-task"):
                with self.subTest(key=key):
                    self.app.select_entry(key)
                    self.update()
                    self.assertTrue(self.app.live_view.winfo_exists())
                    preview = self.app.open_preview()
                    self.update()
                    self.assertTrue(preview.root.winfo_exists())
                    preview.close()
                    self.update()

    def test_hidden_windows_do_not_resume_mock_progress_from_page_or_map_events(self):
        self.app.select_entry("progress-bar")
        self.update()
        view = self.app.live_view
        view.start()
        self.update()
        self.assertIsNotNone(view._after_id)
        self.root.withdraw()
        self.update()
        value = view.widget.value
        self.app.tabs.select(self.app.description)
        self.update()
        self.app.tabs.select(self.app.preview_surface)
        self.update()
        self.root.event_generate("<Map>")
        self.update()
        self.assertFalse(view.visible)
        self.assertIsNone(view._after_id)
        self.pump(.22)
        self.assertEqual(view.widget.value, value)
        self.root.deiconify()
        self.update()
        self.assertTrue(view.visible)
        self.pump(.22)
        self.assertGreater(view.widget.value, value)
        standalone = self.app.open_preview()
        self.update()
        standalone.view.start()
        self.update()
        self.assertIsNotNone(standalone.view._after_id)
        standalone.root.withdraw()
        self.update()
        value = standalone.view.widget.value
        standalone.root.event_generate("<Map>")
        self.update()
        self.assertFalse(standalone.view.visible)
        self.assertIsNone(standalone.view._after_id)
        self.pump(.22)
        self.assertEqual(standalone.view.widget.value, value)
        standalone.root.deiconify()
        self.update()
        self.pump(.22)
        self.assertGreater(standalone.view.widget.value, value)

    def tab_titles(self):
        return tuple(self.app.tabs.tab(tab, "text") for tab in self.app.tabs.tabs())

    @staticmethod
    def component(view):
        return view.overlay if hasattr(view, "overlay") else view.widget

    def assert_inside_root(self, widget):
        self.assertTrue(widget.winfo_ismapped(), str(widget))
        self.assertGreater(widget.winfo_width(), 10)
        self.assertGreater(widget.winfo_height(), 10)
        self.assertGreaterEqual(widget.winfo_rootx(), self.root.winfo_rootx())
        self.assertGreaterEqual(widget.winfo_rooty(), self.root.winfo_rooty())
        self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(),
                             self.root.winfo_rootx() + self.root.winfo_width())
        self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(),
                             self.root.winfo_rooty() + self.root.winfo_height())

    def test_eighteen_components_dispatch_exact_classes_and_distinct_tabs(self):
        self.assertEqual(tuple(row[0] for row in CORE_COMPONENTS), tuple(COMPONENTS))
        self.assertEqual(len(COMPONENTS), 18)
        self.assertEqual(self.app.section.get(), "组件库")
        self.assertTrue(all(section_for(next(entry for entry in ENTRIES if entry.key == key)) == "组件库"
                            for key in self.app.entries.get_children()))
        previous = None
        for key, cls in COMPONENTS.items():
            with self.subTest(component=key):
                self.app.select_entry(key)
                self.update()
                view = self.app.live_view
                self.assertEqual(self.app.current.preview_id, key)
                self.assertEqual(view.key, key)
                self.assertIsInstance(self.component(view), cls)
                self.assertEqual(self.tab_titles(), ("实时预览", "中文用法", "示例与源码"))
                self.assertEqual(len(set(self.app.tabs.tabs())), 3)
                guidance = self.app.description.text.get("1.0", "end-1c")
                self.assertIn(self.app.current.title, guidance)
                self.assertNotIn("from ui_center", guidance)
                code = self.app.current_code()
                ast.parse(code)
                self.assertIn(cls.__name__, code)
                self.assertNotIn("apps.desktop", code)
                self.assertTrue(view.stage.winfo_children())
                if previous is not None:
                    self.assertFalse(previous.winfo_exists())
                previous = view
                standalone = self.app.open_preview()
                self.update()
                self.assertEqual(standalone.entry_key, key)
                self.assertIsNot(standalone.view, view)
                self.assertIsInstance(self.component(standalone.view), cls)
                self.assertIs(self.app.open_preview(), standalone)
                standalone.close()
                self.update()
                self.assertIsNone(self.app.preview)

    def test_guidance_is_one_document_and_android_keeps_its_boundary(self):
        self.app.select_entry("spinner")
        old = self.app.live_view
        for key in ("guide-hierarchy", "pattern-files", "sources", "licenses"):
            self.app.select_entry(key)
            self.update()
            self.assertEqual(self.tab_titles(), ("规范 / 原文",))
            self.assertIsNone(self.app.live_view)
            self.assertTrue(self.app.preview_button.instate(["disabled"]))
            self.assertFalse(old.winfo_exists())
            self.app.copy_usage()
            self.assertEqual(clipboard_text(self.root), body_for(self.app.store, self.app.current))
        self.app.select_entry("guide-hierarchy")
        self.assertIn("视觉层次", self.app.description.text.get("1.0", "end-1c"))
        self.assertNotIn("布局与留白", self.app.description.text.get("1.0", "end-1c"))
        self.app.select_entry("android-actions")
        self.update()
        self.assertEqual(self.tab_titles(), ("中文用法", "示例与源码"))
        self.assertIsNone(self.app.live_view)
        self.assertIn("未设备实测", self.app.boundary.cget("text"))
        self.assertTrue(self.app.preview_button.instate(["disabled"]))

    def test_current_parameter_code_copy_and_source_tab_are_synchronized(self):
        self.app.select_entry("spinner")
        view = self.app.live_view
        view.setting.set("72")
        view.text.set("当前独有参数")
        view.start()
        self.app.tabs.select(self.app.usage)
        self.update()
        current = view.code()
        self.assertIn("size=72", current)
        self.assertIn("当前独有参数", current)
        rendered = self.app.usage.text.get("1.0", "end-1c")
        self.assertIn("size=72", rendered)
        self.assertEqual(rendered.count("from ui_center.loading import Spinner"), 1)
        self.app.copy_usage()
        self.assertEqual(self.root.clipboard_get(), current)
        self.app.copy_ai()
        self.assertIn(current.rstrip(), self.root.clipboard_get())
        self.assertIn("保留原业务", self.root.clipboard_get())
        self.app.tabs.select(self.app.preview_surface)
        self.update()
        self.assertTrue(self.app.preview_surface.reset_button.winfo_ismapped())
        self.app.preview_surface.reset_button.invoke()
        self.assertIs(self.app.live_view, view)
        self.app.copy_usage()
        self.assertNotIn("当前独有参数", self.root.clipboard_get())
        self.assertIn("size=48", self.root.clipboard_get())
        self.app.select_entry("drawer")
        view = self.app.live_view
        view.side.set("left")
        view.modal.set(False)
        view.text.set("独有抽屉内容")
        self.app.copy_usage()
        copied = self.root.clipboard_get()
        self.assertIn("side='left'", copied)
        self.assertIn("modal=False", copied)
        self.assertIn("独有抽屉内容", copied)

    def test_component_search_accepts_aliases_chinese_names_and_scene_filters(self):
        for query, expected in (("shummer", "shimmer"), ("Tabs", "tabs"),
                                ("Confirm Dialog", "confirm-dialog"), ("区域加载层", "page-loader")):
            self.app.query.set(query)
            self.update()
            self.assertEqual(self.app.entries.get_children(), (expected,))
            self.assertEqual(self.app.current.key, expected)
            self.assertIsInstance(self.component(self.app.live_view), COMPONENTS[expected])
        self.app.query.set("")
        self.app.scene.set("反馈组件")
        self.update()
        self.assertEqual(self.app.entries.get_children(), ("inline-alert", "toast", "empty-state"))
        self.app.platform.set("Android")
        self.update()
        self.assertIsNone(self.app.current)
        self.assertTrue(self.app.copy_usage_button.instate(["disabled"]))

    def test_help_reuses_window_tracks_appearance_and_supports_tab_and_search(self):
        self.app.show_help()
        self.update()
        window, reader = self.app._help, self.app._help_reader
        self.app.show_help()
        self.assertIs(self.app._help, window)
        content = reader.text.get("1.0", "end-1c")
        self.assertIn("Esc", content)
        self.assertIn("Android", content)
        self.app.theme.set("dark")
        self.app.font_scale.set(150)
        self.update()
        self.assertIs(self.app._help_reader, reader)
        self.assertEqual(reader.text.get("1.0", "end-1c"), content)
        self.assertEqual(str(reader.text.cget("background")), self.app.tokens["themes"]["dark"]["surface"])
        self.assertEqual(tkfont.Font(root=self.root, font=reader.text.cget("font")).actual("size"), 18)
        close_button = next(child for child in reader.master.winfo_children() if isinstance(child, ttk.Button))
        reader.text.focus_force()
        self.update()
        reader.text.event_generate("<Tab>")
        self.update()
        self.assertIsNot(self.root.focus_get(), reader.text)
        for _ in range(6):
            if self.root.focus_get() is close_button:
                break
            self.root.focus_get().event_generate("<Tab>")
            self.update()
        self.assertIs(self.root.focus_get(), close_button)
        self.assertEqual(reader.text.get("1.0", "end-1c"), content)
        reader.text.focus_force()
        self.update()
        reader.text.event_generate("<Control-f>")
        self.update()
        self.assertIs(self.root.focus_get(), self.app.search_entry)
        window.destroy()
        self.app.theme.set("sage")
        self.update()
        self.app.show_help()
        self.update()
        self.assertIsNot(self.app._help, window)
        self.assertEqual(str(self.app._help_reader.text.cget("background")), self.app.tokens["themes"]["sage"]["surface"])

    def test_legacy_demo_keeps_app_font_scale_when_changing_its_shared_theme(self):
        self.app.font_scale.set(150)
        self.app.select_entry("tk-theme")
        preview = self.app.open_preview()
        self.update()
        self.assertIsInstance(preview, DemoWindow)
        self.assertIs(preview.theme, self.app.theme)
        self.assertEqual(preview.font_scale, self.app.scale)
        preview.project.set("独立演示保留字号与输入")
        preview.panel.set_state("completed", completed=1, total=1, message="保留结果",
                                results=[("虚构数据", "已完成")])
        self.app.font_scale.set(125)
        self.update()
        preview.theme.set("light")
        preview.change_theme()
        self.update()
        self.assertEqual(self.app.font_scale.get(), 125)
        self.assertEqual(preview.font_scale, self.app.scale)
        self.assertEqual(tkfont.nametofont("TkDefaultFont", root=self.root).actual("size"), 15)
        self.assertEqual(tkfont.Font(root=self.root, font=self.app.description.text.cget("font")).actual("size"), 15)
        self.assertEqual(preview.project.get(), "独立演示保留字号与输入")
        self.assertEqual(preview.panel.task_state, "completed")

    def test_shortcut_rebinding_is_idempotent_and_escape_executes_once(self):
        target = self.app.description.text
        sequences = ("<Control-f>", "<Escape>", "<Tab>", "<Shift-Tab>")
        scripts = {sequence: target.bind(sequence) for sequence in sequences}
        registered = tuple(target._tclCommands)
        for _ in range(20):
            self.app._bind_shortcuts(self.root)
        self.assertEqual({sequence: target.bind(sequence) for sequence in sequences}, scripts)
        self.assertEqual(tuple(target._tclCommands), registered)
        self.app.query.set("Spinner")
        self.app.tabs.select(self.app.description)
        self.update()
        writes = []
        trace = self.app.query.trace_add("write", lambda *args: writes.append(self.app.query.get()))
        try:
            target.focus_force()
            self.update()
            target.event_generate("<Escape>")
            self.update()
            self.assertEqual(writes, [""])
            self.assertIs(self.root.focus_get(), self.app.search_entry)
        finally:
            self.app.query.trace_remove("write", trace)

    def test_theme_font_and_motion_keep_inputs_progress_focus_and_independent_state(self):
        self.app.select_entry("page-loader")
        view = self.app.live_view
        view.input_text.set("内嵌输入保留")
        view.text.set("内嵌参数保留")
        view.widget.set_progress(17)
        standalone = self.app.open_preview()
        standalone.view.input_text.set("独立窗口输入保留")
        self.update()
        view.entry.focus_force()
        self.update()
        for theme in ("light", "dark", "warm", "sage"):
            for scale in (100, 125, 150):
                self.app.theme.set(theme)
                self.app.font_scale.set(scale)
                self.app.motion.set("reduced")
                self.update()
                self.assertIs(self.app.live_view, view)
                self.assertIs(self.app.preview, standalone)
                self.assertEqual(view.input_text.get(), "内嵌输入保留")
                self.assertEqual(view.text.get(), "内嵌参数保留")
                self.assertEqual(view.widget.value, 17)
                self.assertEqual(standalone.view.input_text.get(), "独立窗口输入保留")
                self.assertIs(self.root.focus_get(), view.entry)
                self.assertEqual(view.palette, self.app.tokens["themes"][theme])
                self.assertTrue(view.reduced_motion)
                expected = round(self.app.tokens["typography"]["body"]["tk_points"] * 1.2 * scale / 100)
                self.assertEqual(tkfont.nametofont("TkDefaultFont", root=self.root).actual("size"), expected)

    def test_preferences_restart_only_three_keys_and_no_search_persistence(self):
        self.app.theme.set("sage")
        self.app.font_scale.set(125)
        self.app.motion.set("reduced")
        self.app.query.set("private search query")
        self.update()
        saved = json.loads(self.preferences_path.read_text(encoding="utf-8"))
        self.assertEqual(saved, {"theme": "sage", "font_scale": 125, "motion": "reduced"})
        self.app.close()
        self._create_app()
        self.assertEqual(self.app.theme.get(), "sage")
        self.assertEqual(self.app.font_scale.get(), 125)
        self.assertEqual(self.app.motion.get(), "reduced")
        self.assertEqual(self.app.query.get(), "")
        self.assertEqual(self.app.section.get(), "组件库")
        self.assertEqual(self.app.current.key, "spinner")

    def test_bad_and_unwritable_preferences_keep_the_workbench_usable(self):
        self.app.close()
        self.preferences_path.write_text("broken-json", encoding="utf-8")
        self._create_app()
        self.assertIn("默认", self.app.status.get())
        self.assertEqual(self.app.theme.get(), DEFAULTS["theme"])
        self.assertEqual(self.preferences_path.read_text(encoding="utf-8"), "broken-json")
        self.app.theme.set("light")
        self.update()
        self.assertEqual(json.loads(self.preferences_path.read_text(encoding="utf-8"))["theme"], "light")
        self.app.close()
        blocker = self.directory / "blocked-parent"
        blocker.write_text("KEEP", encoding="utf-8")
        self._create_app(blocker / "preferences.json")
        self.app.theme.set("dark")
        self.update()
        self.assertEqual(self.app.theme.get(), "dark")
        self.assertEqual(self.app.palette, self.app.tokens["themes"]["dark"])
        self.assertIn("无法保存", self.app.status.get())
        self.assertEqual(blocker.read_text(encoding="utf-8"), "KEEP")
        self.app.select_entry("dialog")
        self.app.live_view.open()
        self.update()
        self.assertTrue(self.app.live_view.overlay.is_open)

    def test_thirty_tab_hide_window_hide_and_component_switch_cycles_cancel_timers(self):
        self.app.motion.set("normal")
        self.app.select_entry("empty-state")
        self.update()
        baseline = set(self.root.tk.call("after", "info"))
        for cycle in range(30):
            with self.subTest(cycle=cycle):
                self.app.select_entry("spinner")
                view, spinner = self.app.live_view, self.app.live_view.widget
                self.update()
                self.assertIsNotNone(spinner._after_id)
                first_timer = spinner._after_id
                self.app.tabs.select(self.app.description)
                self.update()
                self.assertFalse(view.visible)
                self.assertIsNone(spinner._after_id)
                self.assertNotIn(first_timer, self.root.tk.call("after", "info"))
                self.app.tabs.select(self.app.preview_surface)
                self.update()
                self.assertTrue(view.visible)
                self.assertIsNotNone(spinner._after_id)
                self.root.withdraw()
                self.update()
                self.assertFalse(view.visible)
                self.assertIsNone(spinner._after_id)
                self.root.deiconify()
                self.update()
                self.assertTrue(view.visible)
                self.assertIsNotNone(spinner._after_id)
                last_timer = spinner._after_id
                self.app.select_entry("empty-state")
                self.update()
                self.assertFalse(view.winfo_exists())
                self.assertIsNone(spinner._after_id)
                self.assertNotIn(last_timer, self.root.tk.call("after", "info"))
                self.assertEqual(set(self.root.tk.call("after", "info")), baseline)
        self.app.select_entry("spinner")
        standalone = self.app.open_preview()
        self.update()
        widget = standalone.view.widget
        for cycle in range(30):
            with self.subTest(standalone_cycle=cycle):
                self.assertIsNotNone(widget._after_id)
                pending = widget._after_id
                standalone.root.withdraw()
                self.update()
                self.assertFalse(standalone.view.visible)
                self.assertIsNone(widget._after_id)
                self.assertNotIn(pending, self.root.tk.call("after", "info"))
                standalone.root.deiconify()
                self.update()
                self.assertTrue(standalone.view.visible)
                self.assertIsNotNone(widget._after_id)
        pending = widget._after_id
        standalone.close()
        self.update()
        self.assertIsNone(widget._after_id)
        self.assertNotIn(pending, self.root.tk.call("after", "info"))

    def test_escape_closes_popover_before_clearing_search_and_modal_focus_stays_scoped(self):
        self.app.select_entry("popover")
        self.app.query.set("Popover")
        view = self.app.live_view
        view.open()
        self.update()
        self.assertTrue(view.overlay.is_open)
        self.app.search_entry.focus_force()
        self.update()
        self.app.search_entry.event_generate("<Escape>")
        self.update()
        self.assertFalse(view.overlay.is_open)
        self.assertEqual(self.app.query.get(), "Popover")
        self.assertIsNone(active_overlay(self.root))
        self.app.search_entry.focus_force()
        self.update()
        self.app.search_entry.event_generate("<Escape>")
        self.update()
        self.assertEqual(self.app.query.get(), "")
        self.app.select_entry("confirm-dialog")
        self.app.query.set("Confirm Dialog")
        view = self.app.live_view
        view.open()
        self.update()
        self.assertIs(self.root.grab_current(), view.overlay.window)
        self.assertIs(self.root.focus_get(), view.overlay.cancel_button)
        view.overlay.cancel_button.event_generate("<Escape>")
        self.update()
        self.assertFalse(view.overlay.is_open)
        self.assertEqual(self.app.query.get(), "Confirm Dialog")
        self.assertIsNone(self.root.grab_current())

    def test_four_themes_three_sizes_keep_small_window_actions_and_preview_controls_reachable(self):
        with visible_for_hit_testing(self.root):
            self._assert_small_window_controls()

    def _assert_small_window_controls(self):
        self.app.select_entry("loading-button")
        self.root.geometry("820x600+30+30")
        self.app.motion.set("reduced")
        view = self.app.live_view
        for theme in ("light", "dark", "warm", "sage"):
            for scale in (100, 125, 150):
                with self.subTest(theme=theme, scale=scale):
                    self.app.theme.set(theme)
                    self.app.font_scale.set(scale)
                    self.update()
                    for widget in (self.app.copy_ai_button, self.app.copy_usage_button,
                                   self.app.preview_button, self.app.source_button, self.app.status_label,
                                   self.app.preview_surface.reset_button):
                        self.assert_inside_root(widget)
                    surface = self.app.preview_surface
                    region = tuple(float(value) for value in surface.canvas.cget("scrollregion").split())
                    self.assertEqual(len(region), 4)
                    self.assertGreater(region[2], 0)
                    self.assertGreater(region[3], 0)
                    for button in view.start_button.master.winfo_children():
                        if not isinstance(button, ttk.Button):
                            continue
                        x = button.winfo_rootx() - surface.host.winfo_rootx()
                        y = button.winfo_rooty() - surface.host.winfo_rooty()
                        surface.canvas.xview_moveto(max(0, (x - 4) / region[2]))
                        surface.canvas.yview_moveto(max(0, (y - 4) / region[3]))
                        self.update()
                        center_x = button.winfo_rootx() + button.winfo_width() // 2
                        center_y = button.winfo_rooty() + button.winfo_height() // 2
                        self.assertGreaterEqual(center_x, surface.canvas.winfo_rootx())
                        self.assertLess(center_x, surface.canvas.winfo_rootx() + surface.canvas.winfo_width())
                        self.assertGreaterEqual(center_y, surface.canvas.winfo_rooty())
                        self.assertLess(center_y, surface.canvas.winfo_rooty() + surface.canvas.winfo_height())
                        self.assertIs(self.root.winfo_containing(center_x, center_y), button)


if __name__ == "__main__":
    unittest.main()

"""Real Tk help-location behavior; Explorer launches are mocked, data is isolated."""
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from tkinter import font as tkfont
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "tkinter"))

from apps.desktop.app import BrowserApp
from apps.desktop.resources import ResourceStore


class HelpLocationTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / "work" / "v1.2.1" / "location-help"
        parent.mkdir(parents=True, exist_ok=True)
        self.directory = Path(tempfile.mkdtemp(prefix="case-", dir=parent))
        self.program = self.directory / "测试 程序"
        self.program.mkdir()
        self.settings = self.directory / "界面 设置" / "preferences.json"
        self.program_patch = patch("apps.desktop.app.program_directory", return_value=self.program)
        self.program_mock = self.program_patch.start()
        self.addCleanup(self.program_patch.stop)
        self.root = tk.Tk()
        self.errors = []
        self.root.report_callback_exception = lambda *details: self.errors.append(details)
        self.app = BrowserApp(self.root, ResourceStore(ROOT), preferences_path=self.settings)
        self.root.update()

    def tearDown(self):
        if not self.app._closed:
            self.app.close()
        self.assertEqual(self.errors, [], "Unexpected Tk callback exception")

    def show_help(self):
        self.app.show_help()
        self.root.update()
        return self.app._help

    def test_complete_resolved_paths_are_readonly_selectable_and_copyable(self):
        self.show_help()
        self.assertEqual(self.app.help_program_path.get(), str(self.program.resolve()))
        self.assertEqual(self.app.help_settings_path.get(), str(self.settings.resolve()))
        for entry, path in ((self.app.help_program_entry, self.program),
                            (self.app.help_settings_entry, self.settings)):
            self.assertEqual(str(entry.cget("state")), "readonly")
            entry.insert(0, "DO NOT CHANGE THE PATH")
            self.assertEqual(entry.get(), str(path.resolve()))
            entry.focus_force()
            entry.selection_range(0, "end")
            entry.event_generate("<Control-c>")
            self.root.update()
            self.assertEqual(self.root.clipboard_get(), str(path.resolve()))

    def test_open_buttons_pass_current_path_objects_without_shell_commands(self):
        self.settings.parent.mkdir()
        self.show_help()
        with patch("apps.desktop.app.os.startfile", create=True) as startfile:
            self.app.help_open_program_button.invoke()
            startfile.assert_called_once_with(self.program.resolve())
            self.assertIsInstance(startfile.call_args.args[0], Path)
            self.app.help_open_settings_button.invoke()
            self.assertEqual(startfile.call_args.args, (self.settings.resolve().parent,))
            self.assertEqual(startfile.call_count, 2)
            changed = self.directory / "显式 注入" / "other.json"
            changed.parent.mkdir()
            self.app.preferences.path = changed
            self.show_help()
            self.assertEqual(self.app.help_settings_path.get(), str(changed.resolve()))
            self.app.help_open_settings_button.invoke()
            self.assertEqual(startfile.call_args.args, (changed.resolve().parent,))

    def test_missing_directories_are_reported_without_creating_or_opening(self):
        missing_program = self.directory / "missing-program"
        self.program_mock.return_value = missing_program
        self.show_help()
        self.assertIn("不存在", self.app.help_location_status.get())
        with patch("apps.desktop.app.os.startfile", create=True) as startfile:
            self.app.help_open_program_button.invoke()
            self.assertIn("未创建", self.app.help_location_status.get())
            self.app.help_open_settings_button.invoke()
            self.assertIn("不存在", self.app.help_location_status.get())
            self.assertIn("未创建", self.app.help_location_status.get())
            startfile.assert_not_called()
        self.assertFalse(missing_program.exists())
        self.assertFalse(self.settings.parent.exists())
        self.assertFalse(self.settings.exists())

    def test_open_failure_is_understandable_and_keeps_workbench_and_help_alive(self):
        self.settings.parent.mkdir()
        help_window = self.show_help()
        with patch("apps.desktop.app.os.startfile", side_effect=PermissionError("访问被拒绝"), create=True):
            self.app.help_open_settings_button.invoke()
        self.root.update()
        self.assertIn("无法打开设置目录", self.app.help_location_status.get())
        self.assertIn("手动打开", self.app.help_location_status.get())
        self.assertTrue(help_window.winfo_exists())
        self.assertTrue(self.root.winfo_exists())
        self.assertIs(self.app._help, help_window)
        self.assertFalse(self.app._closed)

    def test_viewing_and_reusing_help_never_saves_preferences_or_creates_parent(self):
        with patch.object(self.app.preferences, "save", wraps=self.app.preferences.save) as save:
            help_window = self.show_help()
            reader = self.app._help_reader
            reader.text.yview_moveto(.7)
            self.root.update()
            before = reader.text.yview()[0]
            self.show_help()
            self.assertIs(self.app._help, help_window)
            self.assertIs(self.app._help_reader, reader)
            self.assertAlmostEqual(reader.text.yview()[0], before, places=3)
            self.assertIn("设置目录尚不存在", self.app.help_location_status.get())
            save.assert_not_called()
        self.assertFalse(self.settings.parent.exists())
        self.assertFalse(self.settings.exists())

    def test_reuse_and_appearance_save_refresh_the_file_state(self):
        help_window = self.show_help()
        self.assertIn("设置目录尚不存在", self.app.help_location_status.get())
        self.settings.parent.mkdir()
        self.show_help()
        self.assertIs(self.app._help, help_window)
        self.assertIn("设置文件尚未创建", self.app.help_location_status.get())
        self.assertFalse(self.settings.exists())
        self.app.theme.set("dark")
        self.root.update()
        self.assertTrue(self.settings.is_file())
        self.assertIn("设置文件已存在", self.app.help_location_status.get())
        saved = self.settings.read_bytes()
        self.show_help()
        self.assertIs(self.app._help, help_window)
        self.assertEqual(self.settings.read_bytes(), saved)
        self.assertEqual(self.app.help_settings_path.get(), str(self.settings.resolve()))

    def test_150_percent_help_keeps_copy_open_close_and_scrolling_keyboard_accessible(self):
        self.app.font_scale.set(150)
        help_window = self.show_help()
        help_window.geometry("660x560+40+40")
        previous = help_window.attributes("-topmost")
        help_window.attributes("-topmost", True)
        help_window.lift()
        self.root.update()
        try:
            for widget in (self.app.help_program_entry, self.app.help_settings_entry,
                           self.app.help_open_program_button, self.app.help_open_settings_button,
                           self.app.help_close_button):
                self.assertTrue(widget.winfo_ismapped())
                self.assertGreater(widget.winfo_height(), 10)
                self.assertGreaterEqual(widget.winfo_rootx(), help_window.winfo_rootx())
                self.assertGreaterEqual(widget.winfo_rooty(), help_window.winfo_rooty())
                self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(),
                                     help_window.winfo_rootx() + help_window.winfo_width())
                self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(),
                                     help_window.winfo_rooty() + help_window.winfo_height())
                x = widget.winfo_rootx() + widget.winfo_width() // 2
                y = widget.winfo_rooty() + widget.winfo_height() // 2
                self.assertIs(self.root.winfo_containing(x, y), widget)
            reader = self.app._help_reader
            self.assertGreater(reader.text.winfo_height(), 30)
            reader.text.yview_moveto(1)
            self.root.update()
            self.assertGreater(reader.text.yview()[0], 0)
            self.app.theme.set("dark")
            self.root.update()
            self.assertEqual(str(reader.text.cget("background")), self.app.palette["surface"])
            self.assertEqual(tkfont.Font(root=self.root, font=reader.text.cget("font")).actual("size"), 18)
            reader.text.focus_force()
            self.root.update()
            reached = []
            for _ in range(8):
                focused = self.root.focus_get()
                reached.append(focused)
                if focused is self.app.help_close_button:
                    break
                focused.event_generate("<Tab>")
                self.root.update()
            self.assertIn(self.app.help_program_entry, reached)
            self.assertIn(self.app.help_settings_entry, reached)
            self.assertIs(self.root.focus_get(), self.app.help_close_button)
            reader.text.focus_force()
            self.root.update()
            reader.text.event_generate("<Control-f>")
            self.root.update()
            self.assertIs(self.root.focus_get(), self.app.search_entry)
        finally:
            help_window.attributes("-topmost", previous)


if __name__ == "__main__":
    unittest.main()

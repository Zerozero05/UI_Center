"""Whole workbench coverage, including every component, theme and text size."""
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components/tkinter"))
from apps.desktop.app import BrowserApp
from apps.desktop.catalog import CORE_COMPONENTS
from apps.desktop.resources import ResourceStore
from apps.desktop.parameters import ParameterChoice


class WorkbenchLayoutTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / "work/v1.2.3/layout-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.directory = Path(tempfile.mkdtemp(dir=parent))
        self.root = tk.Tk()
        self.errors = []
        self.root.report_callback_exception = lambda *error: self.errors.append(error)
        self.app = BrowserApp(self.root, ResourceStore(ROOT), preferences_path=self.directory / "preferences.json")
        self.app.motion.set("reduced")
        self.root.update()

    def tearDown(self):
        self.app.close()
        self.assertEqual(self.errors, [])

    @staticmethod
    def descendants(widget):
        yield widget
        for child in widget.winfo_children():
            yield from WorkbenchLayoutTests.descendants(child)

    def test_every_preview_uses_text_choices_and_one_visible_reset(self):
        keys = [row[0] for row in CORE_COMPONENTS] + ["tk-theme", "tk-actions", "tk-task"]
        for key in keys:
            with self.subTest(component=key):
                self.app.select_entry(key)
                self.root.update()
                view = self.app.live_view
                children = list(self.descendants(view))
                self.assertFalse(any(isinstance(w, ttk.Checkbutton) for w in children))
                resets = [w for w in children if isinstance(w, (ttk.Button, tk.Button))
                          and w.winfo_ismapped() and "重置" in str(w.cget("text"))]
                self.assertEqual(len(resets), 1)
                self.assertTrue(view.code().strip())

    def test_all_previews_at_four_themes_three_sizes_and_minimum_window(self):
        keys = [row[0] for row in CORE_COMPONENTS] + ["tk-theme", "tk-actions", "tk-task"]
        self.root.geometry("820x600+30+30")
        for theme in ("warm", "sage", "light", "dark"):
            self.app.theme.set(theme)
            for scale in (100, 125, 150):
                self.app.font_scale.set(scale)
                for key in keys:
                    with self.subTest(theme=theme, scale=scale, component=key):
                        self.app.select_entry(key)
                        self.root.update()
                        view = self.app.live_view
                        for group in view.form._groups:
                            self.assertLessEqual(group.winfo_x()+group.winfo_width(), view.form.winfo_width()+1)
                        for button in (self.app.copy_usage_button, self.app.copy_ai_button,
                                       self.app.preview_button, self.app.source_button):
                            self.assertTrue(button.winfo_ismapped())
                            self.assertLessEqual(button.winfo_rootx()+button.winfo_width(), self.root.winfo_rootx()+self.root.winfo_width())
                            self.assertLessEqual(button.winfo_rooty()+button.winfo_height(), self.root.winfo_rooty()+self.root.winfo_height())
                        for choice in (w for w in self.descendants(view) if isinstance(w, ParameterChoice)):
                            self.assertFalse(any(bool(int(b.cget("indicatoron"))) for b in choice.buttons.values()))

    def test_header_changes_rows_and_form_reflow_does_not_rebuild_preview(self):
        self.app.select_entry("inline-alert")
        view = self.app.live_view
        view.long_text.set(True)
        view.kind.set("error")
        view._update_alert()
        self.root.geometry("1500x820")
        self.root.update()
        self.assertTrue(self.app._header_inline)
        self.root.geometry("820x600")
        self.app.font_scale.set(150)
        self.app.brand.winfo_children()[1].configure(text="组件与界面规范、源码复用和使用说明")
        self.root.update()
        self.assertFalse(self.app._header_inline)
        self.assertIs(self.app.live_view, view)
        self.assertTrue(view.long_text.get())
        self.assertEqual(view.kind.get(), "error")
        self.assertIn("kind='error'", view.code())
        self.assertEqual(int(view._controls_actions.grid_info()["row"]), 0)

    def test_short_and_overflowing_surface_and_scoped_wheel(self):
        self.app.select_entry("spinner")
        self.root.geometry("1180x820")
        self.root.update()
        surface = self.app.preview_surface
        self.assertFalse(surface.vertical.winfo_ismapped())
        self.assertFalse(surface.horizontal.winfo_ismapped())
        self.root.geometry("820x600")
        self.app.font_scale.set(150)
        self.app.select_entry("page-loader")
        self.root.update()
        self.assertTrue(surface.vertical.winfo_ismapped())
        before = surface.canvas.yview()[0]
        self.app.live_view.status_label.event_generate("<MouseWheel>", delta=-120)
        self.root.update()
        self.assertGreater(surface.canvas.yview()[0], before)
        self.assertNotIn("_wheel", self.app.search_entry.bind("<MouseWheel>"))

    def test_legacy_current_parameter_code_uses_the_active_preview(self):
        for key in ("tk-theme", "tk-actions", "tk-task"):
            with self.subTest(component=key):
                self.app.select_entry(key)
                view = self.app.live_view
                if key == "tk-theme":
                    view.disabled.set(True)
                    view._state()
                elif key == "tk-actions":
                    view.primary_text.set("本次参数独有操作")
                else:
                    view.outcome.set("失败")
                self.assertEqual(self.app.current_code(), view.code())
                self.app._show_code()
                self.assertIn(view.code().rstrip(), self.app.usage.text.get("1.0", "end-1c"))


if __name__ == "__main__":
    unittest.main()

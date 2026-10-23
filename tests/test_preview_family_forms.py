"""Workbench family controls retain component behavior through the shared form."""

from pathlib import Path
import sys
import time
import tkinter as tk
from tkinter import ttk
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "components" / "tkinter"))
sys.path.insert(0, str(ROOT))

from ui_center.theme import apply_theme, load_tokens
from apps.desktop import previews_loading, previews_overlays, previews_legacy


class PreviewFamilyFormTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry("800x680")
        self.errors = []
        self.root.report_callback_exception = lambda *details: self.errors.append(details)
        self.palette = apply_theme(self.root)
        self.view = None

    def tearDown(self):
        if self.view is not None:
            self.view.dispose()
        self.root.update_idletasks()
        self.root.destroy()
        self.assertEqual(self.errors, [], "Unexpected Tk callback exception")

    def create(self, family, key, **kwargs):
        if self.view is not None:
            self.view.dispose()
        self.view = family.create_preview(key, self.root, palette=self.palette, **kwargs)
        self.view.pack(fill="both", expand=True)
        self.root.update()
        return self.view

    @staticmethod
    def descendants(parent):
        for child in parent.winfo_children():
            yield child
            yield from PreviewFamilyFormTests.descendants(child)

    def test_all_fifteen_family_previews_use_forms_without_checkbox_or_duplicate_reset(self):
        count = 0
        for family in (previews_loading, previews_overlays, previews_legacy):
            for key in family.IDS:
                with self.subTest(component=key):
                    view = self.create(family, key, reduced_motion=True)
                    self.assertTrue(view.form.winfo_ismapped())
                    self.assertTrue(view.form._groups)
                    checkboxes = [widget for widget in self.descendants(view)
                                  if widget.winfo_class() in ("Checkbutton", "TCheckbutton")]
                    self.assertEqual(checkboxes, [])
                    reset_buttons = [widget for widget in self.descendants(view)
                                     if widget.winfo_class() in ("Button", "TButton")
                                     and widget.cget("text") == "重置" and widget.winfo_ismapped()]
                    self.assertEqual(len(reset_buttons), 1)
                    if key in ("legacy-actions", "legacy-task"):
                        self.assertIs(reset_buttons[0], view.actions.secondary)
                        self.assertFalse(view.reset_button.winfo_ismapped())
                    else:
                        self.assertIs(reset_buttons[0], view.reset_button)
                    count += 1
        self.assertEqual(count, 15)

    def test_loading_choice_and_mapped_size_preserve_english_component_api(self):
        view = self.create(previews_loading, "progress-bar")
        self.assertEqual(tuple(button.cget("text") for button in view.mode_choice.buttons.values()),
                         ("已知进度", "未知进度"))
        view.mode_choice.select("indeterminate")
        self.assertEqual(view.widget.mode, "indeterminate")
        self.assertIn("mode='indeterminate'", view.code())
        view.reset_button.invoke()
        self.assertEqual(view.setting.get(), "determinate")
        self.assertEqual(view.value.get(), 35)
        for key in ("spinner", "circular-progress"):
            view = self.create(previews_loading, key)
            combo = next(widget for widget in self.descendants(view.form) if isinstance(widget, ttk.Combobox))
            self.assertTrue(all("像素" in label for label in combo.cget("values")))
            combo.current(2)
            combo.event_generate("<<ComboboxSelected>>")
            self.assertEqual(view.setting.get(), "72" if key == "spinner" else "144")
            self.assertEqual(view.widget.size, int(view.setting.get()))
            self.assertNotIn("像素", view.code())

    def test_theme_choice_and_drawer_choices_preserve_state_across_palette_changes(self):
        theme = self.create(previews_legacy, "legacy-theme")
        theme.disabled_choice.select(True)
        theme.input_text.set("保留真实输入")
        self.assertTrue(theme.button.instate(["disabled"]))
        for name in load_tokens()["themes"]:
            theme.apply_palette(apply_theme(self.root, name))
            self.root.update()
            self.assertTrue(theme.disabled.get())
            self.assertTrue(theme.button.instate(["disabled"]))
            self.assertEqual(theme.input_text.get(), "保留真实输入")
        theme.reset_button.invoke()
        self.assertFalse(theme.disabled.get())
        self.assertFalse(theme.button.instate(["disabled"]))
        drawer = self.create(previews_overlays, "drawer", reduced_motion=True)
        drawer.side_choice.select("left")
        drawer.modal_choice.select(False)
        drawer.open_button.invoke()
        self.root.update()
        self.assertTrue(drawer.overlay.is_open)
        self.assertEqual(drawer.overlay.side, "left")
        self.assertFalse(drawer.overlay.modal)
        self.assertIsNone(self.root.grab_current())
        self.assertIn("side='left'", drawer.code())
        self.assertIn("modal=False", drawer.code())
        drawer.overlay.close("escape")
        self.assertEqual(drawer.message.get(), "已关闭：按下退出键")
        drawer.reset_button.invoke()
        self.assertEqual(drawer.side.get(), "right")
        self.assertTrue(drawer.modal.get())
        self.assertFalse(drawer.overlay.is_open)

    def test_overlay_close_reasons_are_chinese_and_keep_source_callback_values(self):
        view = self.create(previews_overlays, "dialog")
        for reason, text in (("close", "关闭按钮"), ("window", "系统关闭"), ("hidden", "预览隐藏"),
                             ("disposed", "预览重置"), ("outside", "点击外部"), ("escape", "按下退出键")):
            view._closed(reason)
            self.assertEqual(view.message.get(), "已关闭：" + text)
        view._closed("custom-code")
        self.assertEqual(view.message.get(), "已关闭：操作结束")

    def test_legacy_action_and_task_callbacks_still_cancel_and_reset_through_the_actionbar(self):
        for key in ("legacy-actions", "legacy-task"):
            with self.subTest(component=key):
                view = self.create(previews_legacy, key)
                view.amount.set("12")
                view.actions.primary.invoke()
                self.assertTrue(view.busy)
                self.assertTrue(view.actions.secondary.instate(["disabled"]))
                view.actions.cancel.invoke()
                self.assertTrue(view.cancelling)
                deadline = time.monotonic() + 2
                while view.busy and time.monotonic() < deadline:
                    self.root.update()
                    time.sleep(0.002)
                self.assertFalse(view.busy)
                self.assertFalse(view.cancelling)
                self.assertFalse(view.actions.secondary.instate(["disabled"]))
                if key == "legacy-task":
                    self.assertEqual(view.panel.task_state, "cancelled")
                else:
                    self.assertIn("已取消", view.detail.get())
                view.actions.secondary.invoke()
                self.assertEqual(view.amount.get(), "8")
                self.assertEqual(view.completed, 0)
                self.assertEqual(view.total, 0)
                if key == "legacy-task":
                    self.assertEqual(view.panel.task_state, "idle")
                    self.assertEqual(view.rows, [])


if __name__ == "__main__":
    unittest.main()

"""Chinese parameter controls keep raw component values and copied examples aligned."""

import ast
from pathlib import Path
import re
import sys
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "components" / "tkinter"))
sys.path.insert(0, str(ROOT))

from apps.desktop.previews_navigation_feedback import IDS, NavigationFeedbackPreview, create_preview
from ui_center.theme import apply_theme, load_tokens


def default_context(key):
    def variable(value):
        return SimpleNamespace(get=lambda: value)

    context = SimpleNamespace(key=key, long_text=variable(False),
        disabled=variable(key in ("tabs", "segmented-control")), mode=variable("单项展开"),
        kind=variable("success" if key == "toast" else "first-use" if key == "empty-state" else "info"),
        duration=variable("4000"),
        widget=SimpleNamespace(select=lambda: "week" if key == "segmented-control" else "overview",
                               expanded=("general",)))
    context._alert_message = lambda: NavigationFeedbackPreview._alert_message(context)
    return context


class NavigationFeedbackExampleTests(unittest.TestCase):
    def test_documented_default_examples_match_generated_code(self):
        document = (ROOT / "docs" / "components" / "navigation-feedback.md").read_text(encoding="utf-8")
        for key in IDS:
            with self.subTest(key=key):
                source = NavigationFeedbackPreview.code(default_context(key))
                match = re.search(r"<!-- example:" + re.escape(key) + r" -->\s*```python\n(.*?)\n```", document, re.S)
                self.assertIsNotNone(match)
                self.assertEqual(match.group(1).strip(), source.strip())
                ast.parse(source)
                self.assertNotIn("from apps", source)

    def test_copied_examples_use_original_component_identifiers(self):
        for key, value in (("inline-alert", "error"), ("toast", "warning"), ("empty-state", "no-results")):
            context = default_context(key)
            context.kind = SimpleNamespace(get=lambda current=value: current)
            source = NavigationFeedbackPreview.code(context)
            self.assertIn("kind=" + repr(value), source)
            ast.parse(source)
        context = default_context("toast")
        context.duration = SimpleNamespace(get=lambda: "0")
        source = NavigationFeedbackPreview.code(context)
        self.assertIn("duration=0", source)
        self.assertIn('"manual": "手动关闭"', source)


class NavigationFeedbackParameterTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry("620x520+50+50")
        self.errors = []
        self.root.report_callback_exception = lambda *error: self.errors.append(error)
        self.palette = apply_theme(self.root)
        self.view = None

    def tearDown(self):
        if self.view is not None:
            self.view.dispose()
        self.root.update_idletasks()
        self.root.destroy()
        self.assertEqual(self.errors, [])

    def make_view(self, key):
        if self.view is not None:
            self.view.dispose()
        self.view = create_preview(key, self.root, palette=self.palette)
        self.view.pack(fill="both", expand=True)
        self.root.update()
        return self.view

    def choose(self, combo, label):
        combo.set(label)
        combo.event_generate("<<ComboboxSelected>>")
        self.root.update()

    def descendants(self, widget):
        for child in widget.winfo_children():
            yield child
            yield from self.descendants(child)

    def test_all_six_parameters_have_no_checkboxes_and_one_shared_reset(self):
        for key in IDS:
            with self.subTest(key=key):
                view = self.make_view(key)
                children = list(self.descendants(view))
                self.assertFalse(any("Checkbutton" in widget.winfo_class() for widget in children))
                resets = [widget for widget in children if isinstance(widget, ttk.Button) and widget.cget("text") == "重置"]
                self.assertEqual(resets, [view.reset_button])
                self.assertEqual(view.reset_button.master, view.actions)
                self.assertEqual(int(view.form.grid_info()["row"]), 0)
                self.assertEqual(int(view.actions.grid_info()["row"]), 1 if key == "toast" else 0)
                if key != "toast":
                    self.assertEqual(int(view.actions.grid_info()["column"]), 1)

    def test_tabs_boolean_choices_callback_and_reset_keep_current_code(self):
        view = self.make_view("tabs")
        view.long_choice.buttons[True].invoke()
        view.disabled_choice.buttons[False].invoke()
        self.root.update()
        self.assertTrue(view.long_text.get())
        self.assertFalse(view.disabled.get())
        self.assertIn("长的中文", view.widget._buttons["settings"].cget("text"))
        view.widget.select("history")
        self.assertEqual(view.message.get(), "已切换到：历史记录")
        self.assertIn("tabs.select('history')", view.code())
        self.assertIn('key == "history" and False', view.code())
        view.reset_button.invoke()
        self.root.update()
        self.assertEqual(view.widget.select(), "overview")
        self.assertFalse(view.long_choice.select())
        self.assertTrue(view.disabled_choice.select())
        self.assertEqual(view.widget._buttons["history"].cget("state"), "disabled")

    def test_accordion_binary_mode_is_text_choice_and_feedback_is_chinese(self):
        view = self.make_view("accordion")
        view.mode_choice.buttons["多项展开"].invoke()
        view.long_choice.buttons[True].invoke()
        view.widget.set_expanded("advanced")
        self.assertEqual(view.widget.expanded, ("general", "advanced"))
        self.assertEqual(view.message.get(), "已展开：通用设置、高级选项")
        self.assertIn("multiple=True", view.code())
        view.reset_button.invoke()
        self.assertEqual(view.widget.expanded, ("general",))
        self.assertEqual(view.mode_choice.select(), "单项展开")

    def test_segment_chinese_combo_preserves_raw_value_and_disabled_fallback(self):
        view = self.make_view("segmented-control")
        self.assertEqual(tuple(view.current_combo.cget("values")), ("日", "周", "年度"))
        view.disabled_choice.select(False)
        self.choose(view.current_combo, "年度")
        self.assertEqual(view.current.get(), "year")
        self.assertEqual(view.widget.select(), "year")
        self.assertEqual(view.message.get(), "已选择：年度")
        self.assertIn("value='year'", view.code())
        view.disabled_choice.select(True)
        self.root.update()
        self.assertEqual(view.widget.select(), "day")
        self.assertEqual(view.current_combo.get(), "日")
        self.assertIn("value='day'", view.code())

    def test_alert_chinese_state_and_text_length_update_component_and_copy(self):
        view = self.make_view("inline-alert")
        self.assertEqual(tuple(view.kind_combo.cget("values")), ("提示", "成功", "警告", "错误"))
        self.choose(view.kind_combo, "错误")
        self.assertEqual(view.kind.get(), "error")
        self.assertEqual(view.widget.kind, "error")
        self.assertIn("失败", view.widget.message)
        view.long_choice.select(True)
        self.root.update()
        self.assertTrue(view.widget.scrollbar.winfo_ismapped())
        self.assertIn("kind='error'", view.code())
        self.assertIn("补充说明", view.code())
        view.reset_button.invoke()
        self.root.update()
        self.assertEqual(view.kind_combo.get(), "提示")
        self.assertFalse(view.widget.scrollbar.winfo_ismapped())

    def test_toast_chinese_parameters_action_row_and_close_reason(self):
        view = self.make_view("toast")
        self.choose(view.kind_combo, "警告")
        self.choose(view.duration_combo, "手动关闭")
        self.assertEqual(view.kind.get(), "warning")
        self.assertEqual(view.duration.get(), "0")
        self.assertEqual(view.widget.kind, "warning")
        self.assertEqual(view.widget.duration, 0)
        self.assertEqual(view.show_button.master, view.actions)
        self.assertIn("kind='warning'", view.code())
        self.assertIn("duration=0", view.code())
        view.widget.close_button.invoke()
        self.assertEqual(view.message.get(), "轻提示已关闭：手动关闭")
        view.show_button.invoke()
        self.assertTrue(view.widget.is_open)
        view.widget.hide(reason="timeout")
        self.assertEqual(view.message.get(), "轻提示已关闭：自动关闭")

    def test_empty_chinese_reason_action_disabled_and_reset(self):
        view = self.make_view("empty-state")
        self.assertEqual(tuple(view.kind_combo.cget("values")), ("首次使用", "无搜索结果", "暂无数据"))
        self.choose(view.kind_combo, "无搜索结果")
        view.disabled_choice.select(True)
        self.assertEqual(view.widget.kind, "no-results")
        self.assertTrue(view.widget.action.instate(["disabled"]))
        before = view.message.get()
        view.widget.action.invoke()
        self.assertEqual(view.message.get(), before)
        self.assertIn("kind='no-results'", view.code())
        view.disabled_choice.select(False)
        view.widget.action.invoke()
        self.assertIn("清除筛选", view.message.get())
        view.reset_button.invoke()
        self.assertEqual(view.kind_combo.get(), "首次使用")
        self.assertFalse(view.disabled_choice.select())

    def test_theme_and_font_changes_preserve_live_parameters_and_code(self):
        for key in IDS:
            with self.subTest(key=key):
                view = self.make_view(key)
                if key == "tabs":
                    view.long_choice.select(True)
                elif key == "accordion":
                    view.mode_choice.select("多项展开")
                    view.widget.set_expanded("advanced")
                elif key == "segmented-control":
                    self.choose(view.current_combo, "日")
                elif key == "inline-alert":
                    self.choose(view.kind_combo, "错误")
                elif key == "toast":
                    self.choose(view.duration_combo, "手动关闭")
                else:
                    self.choose(view.kind_combo, "暂无数据")
                    view.disabled_choice.select(True)
                before = view.code()
                for mode in load_tokens()["themes"]:
                    view.apply_palette(apply_theme(self.root, mode, font_scale=1.5))
                    self.root.update()
                    self.assertEqual(view.code(), before)
                view.reset_button.invoke()


if __name__ == "__main__":
    unittest.main()

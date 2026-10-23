"""Real Tk behavior and lifecycle checks for navigation and feedback."""

import ast
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
from ui_center.navigation import Accordion, SegmentedControl, Tabs
from ui_center.feedback import EmptyState, InlineAlert, Toast
from apps.desktop.previews_navigation_feedback import IDS, create_preview


class NavigationFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry("620x480+50+50")
        self.errors = []
        self.root.report_callback_exception = lambda *details: self.errors.append(details)
        self.palette = apply_theme(self.root)

    def tearDown(self):
        self.root.update_idletasks()
        self.root.destroy()
        self.assertEqual(self.errors, [], "Unexpected Tk callback failure")

    def pump(self, milliseconds):
        deadline = time.monotonic() + milliseconds / 1000
        while time.monotonic() < deadline:
            self.root.update()
            time.sleep(.002)

    def key(self, widget, key):
        widget.focus_force()
        self.root.update()
        widget.event_generate("<KeyPress-" + key + ">")
        widget.event_generate("<KeyRelease-" + key + ">")
        self.root.update()

    def test_tabs_keyboard_skips_disabled_and_enters_page(self):
        calls = []
        tabs = Tabs(self.root, palette=self.palette, on_change=calls.append)
        tabs.pack(fill="both", expand=True)
        first = tabs.add("first", text="概览")
        tabs.add("disabled", text="不可使用", disabled=True)
        third = tabs.add("third", text="设置")
        first_entry = ttk.Entry(first)
        first_entry.pack()
        third_entry = ttk.Entry(third)
        third_entry.pack()
        self.root.update()
        self.key(tabs._buttons["first"], "Right")
        self.assertEqual(tabs.select(), "third")
        self.assertEqual(calls, ["third"])
        self.assertEqual(self.root.focus_get(), tabs._buttons["third"])
        self.key(tabs._buttons["third"], "Tab")
        self.assertEqual(self.root.focus_get(), third_entry)
        tabs._buttons["disabled"].invoke()
        self.assertEqual(tabs.select(), "third")
        self.assertFalse(tabs.select("disabled"))
        self.key(tabs._buttons["third"], "Home")
        self.assertEqual(tabs.select(), "first")
        self.assertEqual(calls, ["third", "first"])
        self.assertFalse(third.winfo_ismapped())
        self.assertTrue(first.winfo_ismapped())

    def test_tabs_wrap_chinese_and_preserve_entries_across_palettes(self):
        self.root.geometry("420x480+50+50")
        tabs = Tabs(self.root, palette=self.palette)
        tabs.pack(fill="both", expand=True)
        page = tabs.add("one", text="中文页面标题需要完整换行而不是被截断" * 2)
        entry = ttk.Entry(page)
        entry.pack(fill="x")
        entry.insert(0, "主题切换后仍保留的内容")
        tabs.add("two", text="第二页")
        tabs.add("three", text="第三页", disabled=True)
        tabs.select("two")
        self.root.update()
        for mode in load_tokens()["themes"]:
            tabs.apply_palette(apply_theme(self.root, mode))
            self.root.update()
            self.assertEqual(tabs.select(), "two")
            self.assertEqual(entry.get(), "主题切换后仍保留的内容")
            self.assertEqual(tabs._buttons["three"].cget("state"), "disabled")
        button = tabs._buttons["one"]
        self.assertGreater(button.winfo_height(), 40)
        self.assertLessEqual(button.winfo_x() + button.winfo_width(), self.root.winfo_width())
        self.assertEqual(button.cget("text"), "中文页面标题需要完整换行而不是被截断" * 2)

    def test_tabs_disabling_selected_chooses_available_page(self):
        calls = []
        tabs = Tabs(self.root, palette=self.palette, on_change=calls.append)
        tabs.pack()
        tabs.add("a", text="A")
        tabs.add("b", text="B")
        tabs.set_disabled("a")
        self.assertEqual(tabs.select(), "b")
        tabs.set_disabled("b")
        self.assertIsNone(tabs.select())
        tabs.set_disabled("a", False)
        self.assertEqual(tabs.select(), "a")
        self.assertEqual(calls, ["b", "a"])

    def test_accordion_single_multiple_callback_and_keyboard(self):
        calls = []
        accordion = Accordion(self.root, palette=self.palette, on_change=calls.append)
        accordion.pack(fill="x")
        first = accordion.add("first", text="第一项", expanded=True)
        second = accordion.add("second", text="第二项")
        accordion.add("disabled", text="禁用项", disabled=True)
        entry = ttk.Entry(first)
        entry.insert(0, "折叠保留")
        entry.pack()
        ttk.Entry(second).pack()
        self.root.update()
        self.key(accordion._buttons["first"], "Down")
        self.assertEqual(self.root.focus_get(), accordion._buttons["second"])
        self.key(accordion._buttons["second"], "Return")
        self.assertEqual(accordion.expanded, ("second",))
        self.assertFalse(first.winfo_ismapped())
        self.assertEqual(entry.get(), "折叠保留")
        accordion.set_multiple(True)
        accordion._buttons["first"].invoke()
        self.assertEqual(accordion.expanded, ("first", "second"))
        self.assertFalse(accordion.toggle("disabled"))
        accordion.set_multiple(False)
        self.assertEqual(accordion.expanded, ("first",))
        self.key(accordion._buttons["first"], "Left")
        self.assertEqual(accordion.expanded, ())
        self.key(accordion._buttons["first"], "Right")
        self.assertEqual(accordion.expanded, ("first",))
        before = list(calls)
        accordion.apply_palette(apply_theme(self.root, "dark"))
        self.assertEqual(accordion.expanded, ("first",))
        self.assertEqual(entry.get(), "折叠保留")
        self.assertEqual(calls, before)

    def test_segments_are_mutually_exclusive_focusable_and_disabled(self):
        calls = []
        control = SegmentedControl(self.root, palette=self.palette,
            options=(("a", "日"), ("b", "周"), ("c", "年")), disabled=("b",), on_change=calls.append)
        control.pack(fill="x")
        after = ttk.Button(self.root, text="下一个")
        after.pack()
        self.root.update()
        self.key(control._buttons["a"], "Right")
        self.assertEqual(control.select(), "c")
        self.assertEqual(control._value.get(), "c")
        self.assertEqual(calls, ["c"])
        self.key(control._buttons["c"], "Tab")
        self.assertEqual(self.root.focus_get(), after)
        control._buttons["b"].invoke()
        self.assertEqual(control.select(), "c")
        control._buttons["a"].invoke()
        self.assertEqual(control.select(), "a")
        self.assertEqual(calls, ["c", "a"])
        control.set_disabled("a")
        self.assertEqual(control.select(), "c")
        control.apply_palette(apply_theme(self.root, "dark"))
        self.assertEqual(control.select(), "c")
        self.assertEqual(control._buttons["b"].cget("state"), "disabled")

    def test_navigation_flat_hover_selected_disabled_and_focus_states(self):
        tabs = Tabs(self.root, palette=self.palette)
        tabs.pack(fill="x")
        tabs.add("first", text="概览")
        tabs.add("second", text="设置")
        accordion = Accordion(self.root, palette=self.palette)
        accordion.pack(fill="x")
        accordion.add("first", text="通用", expanded=True)
        accordion.add("second", text="更多")
        segments = SegmentedControl(self.root, palette=self.palette,
            options=(("first", "日"), ("second", "周")))
        segments.pack(fill="x")
        self.root.update()
        for mode in load_tokens()["themes"]:
            palette = apply_theme(self.root, mode)
            for component in (tabs, accordion, segments):
                component.apply_palette(palette)
                selected, other = component._buttons["first"], component._buttons["second"]
                other.event_generate("<Leave>")
                self.root.update()
                self.assertEqual(int(other.cget("borderwidth")), 0)
                self.assertEqual(other.cget("relief"), "flat")
                self.assertEqual(other.cget("background"), palette["surface"])
                self.assertEqual(selected.cget("background"), palette["selected_background"])
                self.assertEqual(selected.cget("foreground"), palette["selected_foreground"])
                other.event_generate("<Enter>")
                self.root.update()
                self.assertEqual(other.cget("background"), palette["hover"])
                selected.focus_force()
                self.root.update()
                self.assertEqual(self.root.focus_get(), selected)
                self.assertEqual(selected.cget("highlightcolor"), palette["focus"])
                other.event_generate("<Leave>")
        tabs.set_disabled("first")
        segments.set_disabled("first")
        for component in (tabs, segments):
            disabled = component._buttons["first"]
            disabled.event_generate("<Enter>")
            self.root.update()
            self.assertEqual(disabled.cget("background"), palette["surface"])
            self.assertEqual(disabled.cget("disabledforeground"), palette["disabled"])
            self.assertEqual(component.select(), "second")
        accordion.set_expanded("second")
        self.assertEqual(accordion._buttons["first"].cget("background"), palette["surface"])
        self.assertEqual(accordion._buttons["second"].cget("background"), palette["selected_background"])

    def test_inline_alert_persists_readable_text_and_action(self):
        calls = []
        message = "非常长的中文说明，可以选择复制。\n" * 50
        alert = InlineAlert(self.root, palette=self.palette, message=message,
                            on_action=lambda: calls.append("action"), action_text="修正输入")
        alert.pack(fill="x")
        self.root.update()
        for kind, prefix in (("info", "提示"), ("success", "成功"), ("warning", "警告"), ("error", "错误")):
            alert.set_message(message, kind=kind)
            self.assertEqual(alert.body.get("1.0", "end-1c"), message)
            self.assertEqual(alert.body.cget("state"), "disabled")
            self.assertIn(prefix, alert.title_label.cget("text"))
        alert.body.yview_moveto(1)
        self.root.update()
        scroll = alert.body.yview()
        alert.apply_palette(apply_theme(self.root, "dark"))
        self.assertEqual(alert.kind, "error")
        self.assertEqual(alert.body.get("1.0", "end-1c"), message)
        self.assertEqual(alert.body.yview(), scroll)
        alert.action.invoke()
        self.assertEqual(calls, ["action"])
        self.key(alert.body, "Tab")
        self.assertEqual(self.root.focus_get(), alert.action)
        with self.assertRaises(ValueError):
            alert.set_message("invalid", kind="unknown")

    def test_inline_alert_height_fits_short_messages_and_scrolls_only_overflow(self):
        alert = InlineAlert(self.root, palette=self.palette, message="一行提示")
        alert.pack(fill="x")
        for lines in range(1, 6):
            message = "\n".join("第" + str(index) + "行" for index in range(lines))
            alert.set_message(message)
            self.root.update()
            self.assertEqual(int(alert.body.cget("height")), min(lines, 4))
            self.assertEqual(bool(alert.scrollbar.winfo_ismapped()), lines > 4)
            self.assertEqual(alert.body.get("1.0", "end-1c"), message)
        alert.set_message("恢复为短提示")
        self.root.update()
        self.assertEqual(int(alert.body.cget("height")), 1)
        self.assertFalse(alert.scrollbar.winfo_ismapped())

    def test_inline_alert_reflows_with_width_font_and_keeps_selection_and_read_position(self):
        alert = InlineAlert(self.root, palette=self.palette, message="中文" * 50)
        alert.pack(fill="x")
        self.root.update()
        self.assertLess(int(alert.body.cget("height")), 4)
        self.assertFalse(alert.scrollbar.winfo_ismapped())
        self.root.geometry("220x480+50+50")
        self.root.update()
        self.assertEqual(int(alert.body.cget("height")), 4)
        self.assertTrue(alert.scrollbar.winfo_ismapped())
        self.root.geometry("900x480+50+50")
        self.root.update()
        self.assertLess(int(alert.body.cget("height")), 4)
        self.assertFalse(alert.scrollbar.winfo_ismapped())
        alert.set_message("一行\n两行\n三行\n四行")
        self.root.update()
        normal_height = alert.body.winfo_height()
        alert.apply_palette(apply_theme(self.root, font_scale=1.5))
        self.root.update()
        self.assertEqual(int(alert.body.cget("height")), 4)
        self.assertGreater(alert.body.winfo_height(), normal_height)
        self.assertFalse(alert.scrollbar.winfo_ismapped())
        message = "可以选择和复制的中文说明。\n" * 50
        alert.set_message(message)
        self.root.update()
        alert.body.yview_moveto(.5)
        alert.body.tag_add("sel", "20.0", "20.5")
        self.root.update()
        position, selection = alert.body.yview(), alert.body.tag_ranges("sel")
        alert.apply_palette(apply_theme(self.root, "dark", font_scale=1.5))
        self.root.update()
        self.assertEqual(alert.body.yview(), position)
        self.assertEqual(alert.body.tag_ranges("sel"), selection)
        self.assertEqual(alert.body.get("sel.first", "sel.last"), message.splitlines()[19][:5])

    def test_inline_alert_destroy_cancels_pending_measurement(self):
        self.root.update()
        baseline = set(self.root.tk.call("after", "info"))
        alert = InlineAlert(self.root, palette=self.palette, message="等待布局")
        self.assertIsNotNone(alert._fit_id)
        alert.destroy()
        self.root.update()
        self.assertIsNone(alert._fit_id)
        self.assertEqual(set(self.root.tk.call("after", "info")), baseline)

    def test_empty_state_reasons_actions_and_theme_preserve_state(self):
        calls = []
        empty = EmptyState(self.root, palette=self.palette, on_action=lambda: calls.append(empty.kind))
        empty.pack(fill="x")
        for kind in EmptyState.STATES:
            empty.set_state(kind)
            self.assertEqual(empty.title_label.cget("text"), EmptyState.STATES[kind][0])
            empty.action.invoke()
        self.assertEqual(calls, list(EmptyState.STATES))
        empty.set_state("no-results", message="没有匹配“中文关键词”的结果。")
        empty.action.state(["disabled"])
        empty.apply_palette(apply_theme(self.root, "dark"))
        empty.action.invoke()
        self.assertEqual(empty.kind, "no-results")
        self.assertEqual(empty.message, "没有匹配“中文关键词”的结果。")
        self.assertTrue(empty.action.instate(["disabled"]))
        self.assertEqual(len(calls), 3)

    def make_toast(self, duration=100):
        calls = []
        toast = Toast(self.root, palette=self.palette, message="已保存", duration=duration, on_close=calls.append)
        toast.pack(fill="x")
        outside = ttk.Button(self.root, text="焦点移出")
        outside.pack(side="bottom")
        self.root.update()
        outside.focus_force()
        toast.event_generate("<Leave>")
        self.root.update()
        toast.show()
        return toast, outside, calls

    def test_toast_auto_manual_and_zero_duration(self):
        toast, _outside, calls = self.make_toast(80)
        self.pump(160)
        self.assertFalse(toast.is_open)
        self.assertEqual(calls, ["timeout"])
        self.assertEqual(toast.winfo_manager(), "")
        toast.show(duration=0)
        self.pump(100)
        self.assertTrue(toast.is_open)
        self.assertIsNone(toast._timer)
        toast.close_button.invoke()
        self.assertEqual(calls, ["timeout", "manual"])
        toast.hide()
        self.assertEqual(calls, ["timeout", "manual"])

    def test_toast_hover_and_keyboard_focus_pause_remaining_time(self):
        toast, outside, calls = self.make_toast(180)
        self.pump(35)
        toast.event_generate("<Enter>")
        self.root.update()
        self.assertIsNone(toast._timer)
        self.pump(230)
        self.assertTrue(toast.is_open)
        toast.close_button.focus_force()
        self.root.update()
        toast.event_generate("<Leave>")
        self.root.update()
        self.pump(230)
        self.assertTrue(toast.is_open)
        self.assertEqual(calls, [])
        outside.focus_force()
        self.root.update()
        self.pump(230)
        self.assertFalse(toast.is_open)
        self.assertEqual(calls, ["timeout"])

    def test_toast_30_lifecycles_hide_destroy_cancel_all_timers(self):
        outside = ttk.Button(self.root, text="外部")
        outside.pack(side="bottom")
        self.root.update()
        outside.focus_force()
        baseline = set(self.root.tk.call("after", "info"))
        calls = []
        for _cycle in range(30):
            toast = Toast(self.root, palette=self.palette, message="生命周期", duration=20, on_close=calls.append)
            toast.pack(fill="x")
            toast.show()
            toast.set_visible(False)
            self.assertIsNone(toast._timer)
            self.assertIsNone(toast._focus_timer)
            self.assertTrue(toast.is_open)
            toast.set_visible(True)
            toast.apply_palette(self.palette)
            toast.dispose()
            toast.dispose()
            self.assertFalse(toast.winfo_exists())
        self.pump(80)
        self.assertEqual(calls, [])
        self.assertEqual(set(self.root.tk.call("after", "info")), baseline)
        toast, _outside, _calls = self.make_toast(20)
        toast.destroy()
        self.pump(80)
        self.assertIsNone(toast._timer)
        self.assertIsNone(toast._focus_timer)

    def test_toast_hidden_pauses_and_theme_does_not_restart_duration(self):
        toast, _outside, calls = self.make_toast(170)
        self.pump(45)
        toast.set_visible(False)
        remaining = toast._remaining
        self.pump(220)
        self.assertTrue(toast.is_open)
        self.assertEqual(calls, [])
        toast.apply_palette(apply_theme(self.root, "dark"))
        self.assertEqual(toast._remaining, remaining)
        self.assertEqual(toast.message, "已保存")
        toast.set_visible(True)
        self.pump(200)
        self.assertEqual(calls, ["timeout"])

    def test_toast_external_unmap_and_parent_withdraw_pause_timers(self):
        toast, _outside, calls = self.make_toast(100)
        toast.pack_forget()
        self.root.update()
        self.assertIsNone(toast._timer)
        self.pump(150)
        self.assertTrue(toast.is_open)
        self.assertEqual(calls, [])
        toast.pack(fill="x")
        self.root.update()
        self.root.withdraw()
        self.root.update()
        self.assertIsNone(toast._timer)
        self.pump(150)
        self.assertEqual(calls, [])
        self.root.deiconify()
        self.root.update()
        self.pump(180)
        self.assertEqual(calls, ["timeout"])

    def test_all_previews_current_parameter_examples_and_disposal(self):
        for key in IDS:
            view = create_preview(key, self.root, palette=self.palette)
            view.pack(fill="both", expand=True)
            self.root.update()
            if key == "tabs":
                view.disabled.set(False)
                view._update_tabs()
                view.widget.select("history")
                self.assertIn("tabs.select('history')", view.code())
            elif key == "accordion":
                view.mode.set("多项展开")
                view._update_accordion()
                view.widget.set_expanded("advanced")
                self.assertIn("multiple=True", view.code())
            elif key == "segmented-control":
                view.widget.select("day")
                self.assertIn("value='day'", view.code())
            elif key == "inline-alert":
                view.kind.set("error")
                view._update_alert()
                self.assertIn("kind='error'", view.code())
            elif key == "toast":
                view.duration.set("0")
                self.assertIn("duration=0", view.code())
            else:
                view.kind.set("no-results")
                view._update_empty()
                self.assertIn("kind='no-results'", view.code())
            source = view.code()
            ast.parse(source)
            self.assertNotIn("from apps", source)
            self.assertIn("root.mainloop()", source)
            view.apply_palette(self.palette)
            view.set_reduced_motion(True)
            view.set_visible(False)
            view.set_visible(True)
            view.reset()
            view.dispose()
            self.root.update()
            self.assertFalse(view.winfo_exists())


if __name__ == "__main__":
    unittest.main()

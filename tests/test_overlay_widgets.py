"""Real Tk behavior checks for scoped overlays; a desktop is required."""
import ast
from pathlib import Path
import re
import sys
import time
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "components" / "tkinter"))
sys.path.insert(0, str(ROOT))
from ui_center.theme import apply_theme, load_tokens
from ui_center.overlays import (Dialog, ConfirmDialog, Drawer, Popover, Tooltip,
                                active_overlay, close_active_overlay)
from apps.desktop.previews_overlays import IDS, create_preview


class OverlayBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry("700x520+30+30")
        self.errors = []
        self.root.report_callback_exception = lambda *details: self.errors.append(details)
        self.palette = apply_theme(self.root)
        self.trigger = ttk.Button(self.root, text="触发")
        self.trigger.pack()
        self.other = ttk.Entry(self.root)
        self.other.pack()
        self.overlays = []
        self.root.update()
        self.trigger.focus_force()
        self.root.update()

    def tearDown(self):
        for overlay in self.overlays:
            overlay.dispose()
        self.root.update_idletasks()
        self.root.destroy()
        self.assertEqual(self.errors, [], "Unexpected Tk callback exception")

    def make(self, cls, **kwargs):
        overlay = cls(self.root, palette=self.palette, **kwargs)
        self.overlays.append(overlay)
        return overlay

    def pump(self, seconds=0.03):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.002)

    def test_dialog_grab_focus_cycle_escape_and_restore(self):
        reasons = []
        dialog = self.make(Dialog, title="信息", message="允许阅读的长消息" * 15,
                           on_close=reasons.append)
        self.assertTrue(dialog.show(self.trigger))
        self.pump()
        self.assertIs(self.root.grab_current(), dialog.window)
        self.assertIs(self.root.focus_get(), dialog.close_button)
        dialog.close_button.event_generate("<Tab>")
        self.root.update()
        self.assertIs(self.root.focus_get(), dialog.close_button)
        dialog.close_button.event_generate("<Shift-Tab>")
        self.root.update()
        self.assertIs(self.root.focus_get(), dialog.close_button)
        dialog.close_button.event_generate("<Escape>")
        self.root.update()
        self.assertFalse(dialog.is_open)
        self.assertIsNone(self.root.grab_current())
        self.assertIs(self.root.focus_get(), self.trigger)
        self.assertEqual(reasons, ["escape"])

    def test_confirm_safe_default_return_tab_and_explicit_confirm(self):
        results = []
        dialog = self.make(ConfirmDialog, message="确认虚构操作？", on_result=results.append)
        dialog.show(self.trigger)
        self.pump()
        self.assertIs(self.root.focus_get(), dialog.cancel_button)
        dialog.cancel_button.event_generate("<Return>")
        self.root.update()
        self.assertEqual(results, [False])
        self.assertFalse(dialog.is_open)
        dialog.show(self.trigger)
        self.pump()
        dialog.cancel_button.event_generate("<Tab>")
        self.root.update()
        self.assertIs(self.root.focus_get(), dialog.confirm_button)
        dialog.confirm_button.event_generate("<Return>")
        self.root.update()
        self.assertEqual(results, [False, True])
        self.assertIs(self.root.focus_get(), self.trigger)

    def test_modal_competition_nested_restore_and_no_foreign_grab_release(self):
        first = self.make(Dialog)
        second = self.make(Dialog)
        first.show(self.trigger)
        self.pump()
        self.assertFalse(second.show(self.trigger))
        self.assertIs(self.root.grab_current(), first.window)
        child = Dialog(first.window, palette=self.palette)
        self.overlays.append(child)
        self.assertTrue(child.show(first.close_button))
        self.pump()
        self.assertIs(self.root.grab_current(), child.window)
        child.close()
        self.pump()
        self.assertIs(self.root.grab_current(), first.window)
        self.assertIs(self.root.focus_get(), first.close_button)
        foreign = tk.Toplevel(self.root)
        foreign.update()
        foreign.grab_set()
        foreign.focus_force()
        self.root.update()
        first.close()
        self.assertIs(self.root.grab_current(), foreign)
        self.assertIs(self.root.focus_get(), foreign)
        foreign.grab_release()
        foreign.destroy()

    def test_drawer_sides_modes_bounded_animation_and_reduced_motion(self):
        drawer = self.make(Drawer, message="可选的辅助内容", side="left", modal=False)
        drawer.show(self.trigger)
        self.pump(0.36)
        self.assertIsNone(self.root.grab_current())
        self.assertEqual(drawer._animation_step, 6)
        self.assertIsNone(drawer._after_id)
        self.assertEqual(drawer.window.winfo_x(), drawer._drawer_x)
        drawer.close()
        drawer.side, drawer.modal = "right", True
        drawer.show(self.trigger)
        drawer.set_reduced_motion(True)
        self.pump()
        self.assertIs(self.root.grab_current(), drawer.window)
        self.assertEqual(drawer._animation_step, 6)
        self.assertIsNone(drawer._after_id)
        self.assertEqual(drawer.window.winfo_x(), drawer._drawer_x)
        drawer.close_button.event_generate("<Escape>")
        self.root.update()
        self.assertFalse(drawer.is_open)
        self.assertIsNone(self.root.grab_current())

    def test_drawer_limits_every_animation_step_and_cancels_on_reduce_or_hide(self):
        drawer = self.make(Drawer, modal=False)
        with patch.object(self.root, "after", wraps=self.root.after) as schedule:
            drawer.show(self.trigger)
            self.pump(0.36)
            frames = [call.args[0] for call in schedule.call_args_list
                      if len(call.args) > 1 and call.args[1] == drawer._animate]
            self.assertEqual(len(frames), 6)
            self.assertTrue(all(delay >= 34 for delay in frames), frames)
            self.assertEqual(drawer._animation_step, 6)
            self.assertIsNone(drawer._after_id)
            drawer.close()
            drawer.show(self.trigger)
            pending = drawer._after_id
            self.assertIsNotNone(pending)
            drawer.set_reduced_motion(True)
            self.assertEqual(drawer._animation_step, 6)
            self.assertIsNone(drawer._after_id)
            self.assertNotIn(pending, self.root.tk.call("after", "info"))
            reduced_calls = schedule.call_count
            self.pump(0.08)
            self.assertEqual(schedule.call_count, reduced_calls)
            drawer.close()
            drawer.show(self.trigger)
            self.assertEqual(drawer._animation_step, 6)
            self.assertIsNone(drawer._after_id)
            self.assertEqual(schedule.call_count, reduced_calls)
            drawer.close()
            drawer.set_reduced_motion(False)
            drawer.show(self.trigger)
            pending = drawer._after_id
            self.assertIsNotNone(pending)
            drawer.set_visible(False)
            hidden_calls = schedule.call_count
            self.pump(0.08)
            self.assertFalse(drawer.is_open)
            self.assertIsNone(drawer._after_id)
            self.assertNotIn(pending, self.root.tk.call("after", "info"))
            self.assertEqual(schedule.call_count, hidden_calls)

    def test_undecorated_panels_keep_one_pixel_theme_border_when_recolored(self):
        tooltip = Tooltip(self.trigger, palette=self.palette, text="可辨认的提示边界")
        self.overlays.append(tooltip)
        for overlay in (self.make(Popover, anchor=self.trigger, text="可辨认的气泡边界"), tooltip):
            overlay.show(self.trigger)
            self.root.update()
            window, content = overlay.window, overlay.content
            self.assertTrue(window.overrideredirect())
            for mode in load_tokens()["themes"]:
                palette = apply_theme(self.root, mode)
                overlay.apply_palette(palette)
                self.root.update()
                self.assertIs(overlay.window, window)
                self.assertEqual(str(window.cget("background")), palette["border"])
                self.assertNotEqual(palette["border"], palette["background"])
                self.assertEqual(content.winfo_x(), 1)
                self.assertEqual(content.winfo_y(), 1)
                self.assertEqual(window.winfo_width() - content.winfo_width(), 2)
                self.assertEqual(window.winfo_height() - content.winfo_height(), 2)
                self.assertEqual(str(overlay._colors[0].cget("background")), palette["background"])
            overlay.close()

    def test_popover_outside_escape_and_preserved_host_bindings(self):
        events = []
        binding = self.root.bind("<ButtonPress-1>", lambda e: events.append("host"), add="+")
        popover = self.make(Popover, anchor=self.trigger, text="辅助设置")
        popover.show(self.trigger)
        self.pump()
        self.assertIsNone(self.root.grab_current())
        self.other.event_generate("<ButtonPress-1>", x=3, y=3)
        self.root.update()
        self.assertFalse(popover.is_open)
        self.assertEqual(events, ["host"])
        self.assertIn(binding, self.root.bind("<ButtonPress-1>"))
        popover.show(self.trigger)
        self.pump()
        popover.close_button.event_generate("<Escape>")
        self.root.update()
        self.assertFalse(popover.is_open)
        # Host first refusal prevents a search Escape handler from also running.
        host_escape = []
        self.root.bind("<Escape>", lambda e: "break" if close_active_overlay(self.root)
                       else host_escape.append("search"))
        popover.show(self.trigger)
        self.trigger.focus_force()
        self.root.update()
        self.trigger.event_generate("<Escape>")
        self.root.update()
        self.assertFalse(popover.is_open)
        self.assertEqual(host_escape, [])
        self.trigger.event_generate("<Escape>")
        self.root.update()
        self.assertEqual(host_escape, ["search"])

    def test_tooltip_delayed_hover_focus_noninteractive_and_timer_cleanup(self):
        tooltip = Tooltip(self.trigger, palette=self.palette, text="键盘同样可见", delay_ms=35)
        self.overlays.append(tooltip)
        self.other.focus_force()
        self.root.update()
        self.trigger.event_generate("<Enter>")
        self.assertFalse(tooltip.is_open)
        self.pump(0.06)
        self.assertTrue(tooltip.is_open)
        self.assertIs(self.root.focus_get(), self.other)
        self.assertIsNone(self.root.grab_current())
        self.assertIsNone(active_overlay(self.root))
        self.assertFalse(tooltip._focusables())
        self.trigger.event_generate("<Leave>")
        self.root.update()
        self.assertFalse(tooltip.is_open)
        self.trigger.focus_force()
        self.pump(0.06)
        self.assertTrue(tooltip.is_open)
        self.other.focus_force()
        self.pump()
        self.assertFalse(tooltip.is_open)
        self.trigger.event_generate("<Enter>")
        pending = tooltip._after_id
        self.assertIsNotNone(pending)
        tooltip.dispose()
        self.assertNotIn(pending, self.root.tk.call("after", "info"))
        self.pump(0.06)
        self.assertFalse(tooltip.is_open)
        self.assertIsNone(tooltip._after_id)

    def test_palette_preserves_open_window_and_focus(self):
        dialog = self.make(Dialog, title="保持焦点", message="保持消息")
        dialog.show(self.trigger)
        self.pump()
        window = dialog.window
        for mode in load_tokens()["themes"]:
            for scale in (1.0, 1.25, 1.5):
                palette = apply_theme(self.root, mode, font_scale=scale)
                dialog.apply_palette(palette)
                self.root.update()
                self.assertIs(dialog.window, window)
                self.assertIs(self.root.focus_get(), dialog.close_button)
                self.assertEqual(str(dialog._colors[0].cget("foreground")), palette["foreground"])
                self.assertEqual(dialog._colors[0].cget("style"), "UIC.Heading.TLabel")
                self.assertEqual(dialog._colors[1].cget("text"), "保持消息")

    def test_thirty_open_close_cycles_hide_dispose_and_no_orphan_timers(self):
        overlays = [self.make(Dialog), self.make(ConfirmDialog), self.make(Drawer),
                    self.make(Popover, anchor=self.trigger),
                    Tooltip(self.trigger, palette=self.palette, delay_ms=100)]
        self.overlays.append(overlays[-1])
        baseline = tuple(self.root.tk.call("after", "info"))
        for overlay in overlays:
            for cycle in range(30):
                self.assertTrue(overlay.show(self.trigger), (type(overlay).__name__, cycle))
                self.root.update_idletasks()
                window = overlay.window
                overlay.set_visible(False)
                self.assertFalse(window.winfo_exists())
                self.assertFalse(overlay.is_open)
                self.assertIsNone(overlay._after_id)
                self.assertIsNone(self.root.grab_current())
                self.assertFalse(overlay.show(self.trigger))
                overlay.set_visible(True)
            overlay.show(self.trigger)
            window = overlay.window
            overlay.dispose()
            self.assertFalse(window.winfo_exists())
            self.assertFalse(overlay.show(self.trigger))
        self.root.update()
        self.assertEqual(tuple(self.root.tk.call("after", "info")), baseline)
        self.assertIsNone(active_overlay(self.root))
        self.assertFalse(any(isinstance(child, tk.Toplevel) for child in self.root.winfo_children()))

    def test_external_destroy_releases_state_and_anchor_destroy_cancels_hint(self):
        dialog = self.make(Dialog)
        dialog.show(self.trigger)
        dialog.window.destroy()
        self.root.update()
        self.assertFalse(dialog.is_open)
        self.assertIsNone(self.root.grab_current())
        button = ttk.Button(self.root)
        button.pack()
        tooltip = Tooltip(button, palette=self.palette, delay_ms=40)
        self.overlays.append(tooltip)
        button.event_generate("<Enter>")
        button.destroy()
        self.pump(0.06)
        self.assertTrue(tooltip._disposed)
        self.assertIsNone(tooltip._after_id)
        self.assertFalse(tooltip.is_open)

    def test_every_preview_opens_resets_and_emits_independent_example(self):
        for key in IDS:
            view = create_preview(key, self.root, palette=self.palette, reduced_motion=True)
            view.pack(fill="both", expand=True)
            self.root.update()
            view.text.set("当前参数：" + key)
            view.open()
            self.root.update()
            self.assertTrue(view.overlay.is_open, key)
            self.assertIn("当前参数", view.code())
            self.assertNotIn("apps.", view.code())
            source = ast.parse(view.code())
            source.body.pop()  # mainloop alone is omitted to exercise the standalone example.
            view.set_visible(False)
            self.assertFalse(view.overlay.is_open)
            view.reset()
            self.assertEqual(view.side.get(), "right")
            view.dispose()
            namespace = {"__file__": str(ROOT / "example.py")}
            exec(compile(source, "<component-example>", "exec"), namespace)
            example_root, overlay = namespace["root"], namespace["overlay"]
            try:
                example_root.update()
                namespace["trigger"].invoke()
                example_root.update()
                self.assertTrue(overlay.is_open, key)
            finally:
                overlay.dispose()
                example_root.destroy()

    def test_documentation_examples_execute_with_only_component_imports(self):
        document = (ROOT / "docs" / "components" / "overlays.md").read_text(encoding="utf-8")
        examples = re.findall(r"<!-- example:([^>]+) -->\s*```python\n(.*?)\n```", document, re.S)
        self.assertEqual(tuple(key for key, code in examples), IDS)
        for key, code in examples:
            self.assertNotIn("apps.", code)
            source = ast.parse(code)
            source.body.pop()  # Keep actual construction, omit the blocking mainloop.
            namespace = {"__file__": str(ROOT / "example.py")}
            exec(compile(source, "<documentation-example>", "exec"), namespace)
            example_root = namespace["root"]
            name = {"dialog": "dialog", "confirm-dialog": "dialog", "drawer": "drawer",
                    "popover": "popover", "tooltip": "tooltip"}[key]
            overlay = namespace[name]
            try:
                example_root.update()
                self.assertTrue(overlay.show(namespace["trigger"]), key)
                example_root.update()
                self.assertTrue(overlay.is_open, key)
            finally:
                overlay.dispose()
                example_root.destroy()

    def test_tooltip_preview_invalid_delay_recovers_without_losing_instance(self):
        view = create_preview("tooltip", self.root, palette=self.palette)
        view.pack(fill="both", expand=True)
        self.root.update()
        original = view.overlay
        view.delay.set("invalid")
        view._update_tooltip()
        self.assertIs(view.overlay, original)
        self.assertIn(original, view.managed)
        self.assertIn("整数", view.message.get())
        view.delay.set(100)
        view._update_tooltip()
        view.open()
        self.root.update()
        self.assertTrue(view.overlay.is_open)
        self.assertEqual(view.overlay.delay_ms, 100)
        view.dispose()

    def test_failed_content_factory_closes_partial_window(self):
        def broken_factory(content):
            ttk.Entry(content).pack()
            raise RuntimeError("caller content failed")
        for cls in (Drawer, Popover):
            overlay = self.make(cls, content_factory=broken_factory)
            with self.assertRaisesRegex(RuntimeError, "caller content failed"):
                overlay.show(self.trigger)
            self.assertFalse(overlay.is_open)
            self.assertIsNone(overlay._after_id)
            self.assertIsNone(self.root.grab_current())
            self.assertIsNone(active_overlay(self.root))


if __name__ == "__main__":
    unittest.main()

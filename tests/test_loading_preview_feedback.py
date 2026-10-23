"""Rendered loading effects and user-visible controls, using real Tk widgets."""

from pathlib import Path
import _tkinter
import sys
import time
import tkinter as tk
from tkinter import ttk
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "components" / "tkinter"))
sys.path.insert(0, str(ROOT))

from ui_center.loading import Shimmer, Skeleton
from ui_center.theme import apply_theme, load_tokens
from apps.desktop.previews_loading import create_preview


class LoadingRenderingFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry("760x620")
        self.errors = []
        self.root.report_callback_exception = lambda *details: self.errors.append(details)
        self.palette = apply_theme(self.root)

    def tearDown(self):
        self.root.update_idletasks()
        self.root.destroy()
        self.assertEqual(self.errors, [], "Unexpected exception in a real Tk callback")

    def make(self, cls, **kwargs):
        widget = cls(self.root, palette=self.palette, **kwargs)
        widget.pack(fill="x")
        widget.start()
        self.root.update()
        return widget

    def color(self, widget):
        item = widget.canvas.find_withtag("placeholder")[0]
        return widget.canvas.itemcget(item, "fill")

    def test_pulse_is_smooth_periodic_and_continuous_across_counter_wrap(self):
        widget = self.make(Skeleton)
        self.assertEqual(widget.interval_ms * 48, 2400)
        for name, palette in load_tokens()["themes"].items():
            with self.subTest(theme=name):
                widget.apply_palette(palette)
                colors = []
                for phase in range(49):
                    widget._phase = phase
                    widget._draw()
                    colors.append(self.color(widget))
                self.assertGreater(len(set(colors)), 12, "Pulse must blend colors, not toggle two fills")
                self.assertEqual(colors[0], colors[48])
                channels = [self.root.winfo_rgb(color) for color in colors]
                self.assertLessEqual(max(abs(a - b) for previous, current in zip(channels, channels[1:])
                                         for a, b in zip(previous, current)), 3 * 257)
                widget._phase = 239
                widget._draw()
                before = self.root.winfo_rgb(self.color(widget))
                widget._phase = 0
                widget._draw()
                after = self.root.winfo_rgb(self.color(widget))
                self.assertLessEqual(max(abs(a - b) for a, b in zip(before, after)), 3 * 257)

    def test_real_timer_changes_pulse_and_stop_leaves_static_placeholder(self):
        widget = self.make(Skeleton)
        initial = self.color(widget)
        deadline = time.monotonic() + 2
        while self.color(widget) == initial and time.monotonic() < deadline:
            self.root.tk.dooneevent(_tkinter.DONT_WAIT)
            time.sleep(0.002)
        self.assertNotEqual(self.color(widget), initial)
        self.assertIsNotNone(widget._after_id)
        widget.stop()
        self.assertIsNone(widget._after_id)
        self.assertEqual(self.color(widget), self.palette["hover"])
        self.assertEqual(len(widget.canvas.find_withtag("placeholder")), 9)

    def test_sweep_is_gradient_moving_and_clipped_to_each_placeholder(self):
        widget = self.make(Shimmer)
        for name, palette in load_tokens()["themes"].items():
            widget.apply_palette(palette)
            for variant in ("list", "card"):
                with self.subTest(theme=name, variant=variant):
                    widget.set_variant(variant)
                    positions, colors = set(), set()
                    saw_circle = False
                    for phase in (2, 6, 12, 20, 28, 36):
                        widget._phase = phase
                        widget._draw()
                        placeholders = widget.canvas.find_withtag("placeholder")
                        self.assertEqual(len(placeholders), 9 if variant == "list" else 3)
                        self.assertEqual({widget.canvas.itemcget(item, "fill") for item in placeholders},
                                         {palette["hover"]}, "The sweep must not pulse its base")
                        signature = []
                        for item in widget.canvas.find_withtag("shimmer"):
                            tags = widget.canvas.gettags(item)
                            index = int(next(tag[5:] for tag in tags if tag.startswith("clip-")))
                            base = placeholders[index]
                            x0, y0, x1, y1 = widget.canvas.coords(base)
                            coords = widget.canvas.coords(item)
                            if widget.canvas.type(base) == "oval":
                                saw_circle = True
                                self.assertEqual(widget.canvas.type(item), "polygon")
                                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                                rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
                                for x, y in zip(coords[::2], coords[1::2]):
                                    self.assertLessEqual(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2,
                                                         1 + 1e-9, "Highlight escaped the circular placeholder")
                            else:
                                self.assertEqual(widget.canvas.type(item), "rectangle")
                                a, top, b, bottom = coords
                                self.assertGreaterEqual(a, x0)
                                self.assertLessEqual(b, x1)
                                self.assertGreaterEqual(top, y0)
                                self.assertLessEqual(bottom, y1)
                            signature.append(tuple(round(value, 3) for value in coords))
                            colors.add(widget.canvas.itemcget(item, "fill"))
                        positions.add(tuple(signature))
                        self.assertEqual(widget.canvas.cget("background"), palette["background"])
                    self.assertGreater(len(positions), 3, "The highlight must move through the placeholders")
                    self.assertGreater(len(colors), 8, "The highlight must have a gradient")
                    self.assertEqual(saw_circle, variant == "list")

    def test_stopped_disabled_and_reduced_motion_keep_static_shapes_without_timer(self):
        for cls in (Skeleton, Shimmer):
            widget = self.make(cls)
            for action in ("stopped", "disabled", "reduced", "animation-off"):
                with self.subTest(component=cls.__name__, action=action):
                    widget.set_reduced_motion(False)
                    if cls is Shimmer:
                        widget.set_enabled(True)
                    else:
                        widget.set_animation(True)
                    widget.start()
                    widget._phase = 12
                    widget._draw()
                    if action == "stopped":
                        widget.stop()
                    elif action == "disabled":
                        widget.set_enabled(False) if cls is Shimmer else widget.set_animation(False)
                    elif action == "reduced":
                        widget.set_reduced_motion(True)
                    else:
                        widget.set_animation(False)
                    self.assertIsNone(widget._after_id)
                    self.assertEqual(widget.running, action != "stopped")
                    self.assertEqual(len(widget.canvas.find_all()), 9)
                    self.assertEqual(widget.canvas.find_withtag("shimmer"), ())
                    self.assertEqual(self.color(widget), self.palette["hover"])
            widget.destroy()

    def test_chinese_controls_keep_internal_values_and_generated_api(self):
        for key, parameter in (("skeleton", "animate"), ("shimmer", "enabled")):
            with self.subTest(component=key):
                view = create_preview(key, self.root, palette=self.palette)
                view.pack(fill="x")
                self.root.update()
                self.assertEqual(tuple(view.layout_combo.cget("values")), ("列表", "卡片"))
                self.assertEqual(tuple(view.effect_combo.cget("values")), ("开启", "关闭"))
                self.assertEqual(str(view.effect_combo.cget("state")), "readonly")
                self.assertEqual(view.layout_label.get(), "列表")
                view.layout_combo.set("卡片")
                view.layout_combo.event_generate("<<ComboboxSelected>>")
                self.assertEqual(view.setting.get(), "card")
                self.assertEqual(view.widget.variant, "card")
                view.effect_combo.set("关闭")
                view.effect_combo.event_generate("<<ComboboxSelected>>")
                self.assertFalse(view.enabled.get())
                self.assertIsNone(view.widget._after_id)
                self.assertIn("效果已关闭", view.message.get())
                code = view.code()
                self.assertIn("variant='card'", code)
                self.assertIn(parameter + "=False", code)
                self.assertNotIn("variant='卡片'", code)
                view.effect_combo.set("开启")
                view.effect_combo.event_generate("<<ComboboxSelected>>")
                self.assertTrue(view.enabled.get())
                self.assertIn("正在演示", view.message.get())
                self.assertIsNotNone(view.widget._after_id)
                self.assertEqual(str(view.layout_combo.tk.call("tk_focusNext", str(view.layout_combo))),
                                 str(view.effect_combo))
                view.dispose()
                self.root.update()

    def test_motion_feedback_preserves_choice_and_never_restarts_stopped_preview(self):
        for key in ("skeleton", "shimmer"):
            with self.subTest(component=key):
                view = create_preview(key, self.root, palette=self.palette)
                view.pack(fill="x")
                self.root.update()
                view.set_reduced_motion(True)
                self.assertTrue(view.enabled.get())
                self.assertEqual(view.effect_label.get(), "开启")
                self.assertEqual(str(view.effect_combo.cget("state")), "disabled")
                self.assertIsNone(view.widget._after_id)
                self.assertIn("减少动画已启用", view.message.get())
                self.assertIn("静态占位", view.message.get())
                self.assertIn("reduced_motion=True", view.code())
                view.set_reduced_motion(False)
                self.assertEqual(str(view.effect_combo.cget("state")), "readonly")
                self.assertIsNotNone(view.widget._after_id)
                self.assertIn("正在演示", view.message.get())
                view.enabled.set(False)
                view._parameters()
                view.set_reduced_motion(True)
                view.set_reduced_motion(False)
                self.assertFalse(view.enabled.get())
                self.assertEqual(view.effect_label.get(), "关闭")
                self.assertIsNone(view.widget._after_id)
                self.assertIn("效果已关闭", view.message.get())
                view.start()
                self.assertIn("效果已关闭", view.message.get())
                view.stop()
                view.set_reduced_motion(True)
                view.set_reduced_motion(False)
                self.assertFalse(view.widget.running)
                self.assertIsNone(view.widget._after_id)
                self.assertIn("已停止", view.message.get())
                view.reset()
                self.assertTrue(view.widget.running)
                self.assertTrue(view.enabled.get())
                self.assertEqual(view.layout_label.get(), "列表")
                self.assertIn("正在演示", view.message.get())
                view.dispose()
                self.root.update()

    def test_two_preview_instances_follow_motion_without_sharing_local_choices(self):
        embedded = create_preview("shimmer", self.root, palette=self.palette)
        standalone = create_preview("shimmer", self.root, palette=self.palette)
        for view in (embedded, standalone):
            view.pack(fill="x")
        self.root.update()
        embedded.enabled.set(False)
        embedded._parameters()
        standalone.stop()
        for reduced in (True, False):
            for view in (embedded, standalone):
                view.set_reduced_motion(reduced)
            self.assertFalse(embedded.enabled.get())
            self.assertTrue(standalone.enabled.get())
            self.assertTrue(embedded.widget.running)
            self.assertFalse(standalone.widget.running)
            self.assertIn("已停止", standalone.message.get())
            self.assertEqual(str(embedded.effect_combo.cget("state")), "disabled" if reduced else "readonly")
            self.assertEqual(str(standalone.effect_combo.cget("state")), "disabled" if reduced else "readonly")
            self.assertIsNone(embedded.widget._after_id)
            self.assertIsNone(standalone.widget._after_id)
        embedded.dispose()
        standalone.dispose()


if __name__ == "__main__":
    unittest.main()

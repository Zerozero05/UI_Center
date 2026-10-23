"""Real Tk lifecycle, progress and preview behavior checks (desktop required)."""

from pathlib import Path
import _tkinter
import math
import sys
import time
import tkinter as tk
from tkinter import ttk
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "components" / "tkinter"))
sys.path.insert(0, str(ROOT))

from ui_center.loading import (CircularProgress, LoadingButton, PageLoader,
                               ProgressBar, Shimmer, Skeleton, Spinner)
from ui_center.theme import apply_theme, load_tokens
from apps.desktop.previews_loading import IDS, create_preview


class LoadingBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry("680x520")
        self.errors = []
        self.root.report_callback_exception = lambda *details: self.errors.append(details)
        self.palette = apply_theme(self.root)

    def tearDown(self):
        self.root.update_idletasks()
        self.root.destroy()
        self.assertEqual(self.errors, [], "Unexpected exception in a real Tk callback")

    def pump_until(self, condition, timeout=2):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if condition():
                return
            self.root.tk.dooneevent(_tkinter.DONT_WAIT)
            time.sleep(0.002)
        self.fail("Timed out waiting for real Tk state")

    def make_widgets(self):
        classes = (Spinner, ProgressBar, CircularProgress, Skeleton, Shimmer, LoadingButton)
        widgets = [cls(self.root, palette=self.palette) for cls in classes]
        for widget in widgets:
            widget.pack()
        # Give the overlay a small, independent stage rather than the whole root.
        stage = ttk.Frame(self.root, width=160, height=100)
        stage.pack()
        stage.pack_propagate(False)
        overlay = PageLoader(stage, palette=self.palette)
        widgets.append(overlay)
        return widgets, stage

    def test_thirty_cycles_leave_no_after_callbacks(self):
        baseline = set(self.root.tk.call("after", "info"))
        for cycle in range(30):
            widgets, stage = self.make_widgets()
            widgets[1].set_mode("indeterminate")
            for widget in widgets:
                widget.start()
            self.root.update()
            for widget in widgets:
                pending = widget._after_id
                for _ in range(4):
                    widget.start()
                self.assertEqual(widget._after_id, pending, (cycle, type(widget).__name__))
                if pending is not None:
                    self.assertIn(pending, self.root.tk.call("after", "info"))
                widget.set_visible(False)
                self.assertIsNone(widget._after_id)
                widget.set_visible(True)
                widget.set_reduced_motion(True)
                self.assertIsNone(widget._after_id)
                widget.set_reduced_motion(False)
                widget.stop()
                self.assertIsNone(widget._after_id)
                widget.dispose()
                widget.dispose()
            stage.destroy()
            self.root.update()
            self.assertEqual(set(self.root.tk.call("after", "info")), baseline, cycle)

    def test_hidden_and_unmapped_animation_stops_and_resumes(self):
        spinner = Spinner(self.root, palette=self.palette, interval_ms=1)
        self.assertEqual(spinner.interval_ms, 34, "Animation is capped below 30fps")
        spinner.pack()
        spinner.start()
        self.root.update()
        self.assertIsNotNone(spinner._after_id)
        self.pump_until(lambda: spinner._phase > 0)
        spinner.pack_forget()
        self.root.update()
        phase = spinner._phase
        self.assertIsNone(spinner._after_id)
        spinner.pack()
        self.root.update()
        self.assertIsNotNone(spinner._after_id)
        spinner.set_reduced_motion(True)
        self.assertTrue(spinner.running)
        self.assertIsNone(spinner._after_id)
        self.assertEqual(spinner._phase, phase)
        spinner.set_visible(False)
        spinner.set_reduced_motion(False)
        self.assertIsNone(spinner._after_id)
        spinner.set_visible(True)
        self.assertIsNotNone(spinner._after_id)

    def test_determinate_and_circular_show_actual_progress_without_timer(self):
        bar = ProgressBar(self.root, palette=self.palette, value=37, maximum=80)
        circle = CircularProgress(self.root, palette=self.palette, value=37, maximum=80)
        for widget in (bar, circle):
            widget.pack()
            widget.start()
        self.root.update()
        self.assertEqual(bar.caption.cget("text"), "46%")
        circle_text = [circle.canvas.itemcget(item, "text") for item in circle.canvas.find_all()
                       if circle.canvas.type(item) == "text"]
        self.assertEqual(circle_text, ["46%"])
        for widget in (bar, circle):
            self.assertIsNone(widget._after_id)
            widget.set_reduced_motion(True)
            widget.set_visible(False)
            widget.apply_palette(load_tokens()["themes"]["dark"])
            self.assertEqual((widget.value, widget.maximum), (37, 80))
            widget.set_progress(80)
            self.assertEqual(widget.value, 80)
        circle.set_progress(0)
        self.assertEqual(circle.value, 0)

    def test_indeterminate_does_not_overwrite_actual_value(self):
        bar = ProgressBar(self.root, palette=self.palette, value=23, mode="indeterminate")
        bar.pack()
        bar.start()
        self.root.update()
        self.pump_until(lambda: bar._phase >= 2)
        self.assertEqual(bar.value, 23)
        self.assertIn("进度未知", bar.caption.cget("text"))
        bar.set_mode("determinate")
        self.assertEqual(bar.caption.cget("text"), "23%")
        self.assertIsNone(bar._after_id)

    def test_invalid_progress_is_atomic(self):
        for cls in (ProgressBar, CircularProgress, PageLoader):
            widget = cls(self.root, palette=self.palette, value=35)
            for value, maximum in ((-1, 100), (101, 100), (1, 0), (math.nan, 100), (1, math.inf)):
                with self.assertRaises(ValueError):
                    widget.set_progress(value, maximum)
                self.assertEqual((widget.value, widget.maximum), (35, 100))
            widget.destroy()
        with self.assertRaises(ValueError):
            ProgressBar(self.root, palette=self.palette, mode="unknown")
        with self.assertRaises(ValueError):
            Skeleton(self.root, palette=self.palette, variant="unknown")

    def test_skeleton_variants_and_shimmer_disable_retains_placeholder(self):
        for cls in (Skeleton, Shimmer):
            widget = cls(self.root, palette=self.palette)
            widget.pack()
            widget.start()
            self.root.update()
            self.assertIsNotNone(widget._after_id)
            self.assertEqual(len(widget.canvas.find_all()), 9 if cls is Skeleton else 10)
            widget.set_variant("card")
            self.assertEqual(widget.variant, "card")
            if cls is Shimmer:
                widget.set_enabled(False)
            else:
                widget.set_animation(False)
            self.assertIsNone(widget._after_id)
            self.assertTrue(widget.running)
            self.assertEqual(len(widget.canvas.find_all()), 3)
            widget.destroy()

    def test_loading_button_uses_real_button_and_guards_reentry(self):
        calls = []
        button = LoadingButton(self.root, palette=self.palette,
                               command=lambda: (calls.append("start"), button.set_busy(True)))
        button.pack()
        self.root.update()
        self.assertIsInstance(button.button, ttk.Button)
        button.button.invoke()
        button.button.invoke()
        self.assertEqual(calls, ["start"])
        self.assertTrue(button.button.instate(["disabled"]))
        self.assertTrue(button.busy)
        button.set_reduced_motion(True)
        button.apply_palette(load_tokens()["themes"]["dark"])
        self.assertTrue(button.busy)
        self.assertTrue(button.button.instate(["disabled"]))
        self.assertIsNone(button._after_id)
        button.stop()
        self.assertTrue(button.button.instate(["!disabled"]))
        button.button.state(["disabled"])
        button.apply_palette(self.palette)
        self.assertTrue(button.button.instate(["disabled"]), "A palette change preserves external disabled state")

    def test_loading_button_keyboard_space_uses_native_button_binding(self):
        calls = []
        button = LoadingButton(self.root, palette=self.palette,
                               command=lambda: (calls.append("start"), button.start()))
        button.pack()
        self.root.update()
        button.button.focus_force()
        self.root.update()
        button.button.event_generate("<KeyPress-space>")
        button.button.event_generate("<KeyRelease-space>")
        self.pump_until(lambda: len(calls) == 1)
        self.assertTrue(button.busy)
        button.button.event_generate("<KeyPress-space>")
        button.button.event_generate("<KeyRelease-space>")
        self.root.update()
        self.assertEqual(calls, ["start"])

    def test_page_loader_is_confined_and_cancel_is_caller_callback(self):
        outside = ttk.Entry(self.root)
        outside.pack()
        outside.insert(0, "保留输入")
        stage = ttk.Frame(self.root, width=380, height=220)
        stage.pack()
        stage.pack_propagate(False)
        cancelled = []
        loader = PageLoader(stage, palette=self.palette, value=42,
                            on_cancel=lambda: cancelled.append("cancel"))
        loader.start()
        self.root.update()
        self.assertEqual(loader.master, stage)
        self.assertEqual(loader.winfo_width(), stage.winfo_width())
        self.assertEqual(loader.winfo_height(), stage.winfo_height())
        self.assertIsNone(self.root.grab_current())
        self.assertEqual(loader.progress_label.cget("text"), "42%")
        loader.cancel_button.invoke()
        self.assertEqual(cancelled, ["cancel"])
        self.assertTrue(loader.running, "The caller decides whether cancellation has completed")
        loader.set_visible(False)
        self.root.update()
        self.assertFalse(loader.winfo_ismapped())
        self.assertEqual(loader.value, 42)
        loader.apply_palette(load_tokens()["themes"]["dark"])
        self.assertEqual(outside.get(), "保留输入")
        loader.set_visible(True)
        self.root.update()
        self.assertTrue(loader.winfo_ismapped())
        loader.stop()
        self.assertEqual(loader.winfo_manager(), "")

    def test_page_loader_preview_fits_overlay_and_cancel_at_all_appearance_sizes(self):
        # Match the workbench's Canvas window: its host takes the preview's
        # requested height, rather than stretching it to the whole root.
        # Previously place() left the stage at the underlying page's ~108px
        # request, clipping the loader's progress text and cancel button.
        self.root.geometry("940x860")
        previous_topmost = self.root.attributes("-topmost")
        # This test checks real desktop hit testing. Keep unrelated windows
        # from covering its pixels, and restore the root's original setting.
        self.root.attributes("-topmost", True)
        canvas = tk.Canvas(self.root, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        try:
            for mode in load_tokens()["themes"]:
                for percent in (100, 125, 150):
                    with self.subTest(theme=mode, font_percent=percent):
                        host, view, window = None, None, None
                        try:
                            palette = apply_theme(self.root, mode, font_scale=1.2 * percent / 100)
                            host = ttk.Frame(canvas)
                            host.columnconfigure(0, weight=1)
                            window = canvas.create_window(0, 0, window=host, anchor="nw", width=900)
                            view = create_preview("page-loader", host, palette=palette, reduced_motion=True)
                            view.grid(row=0, column=0, sticky="nsew")
                            view.input_text.set("主题与字号切换后保留输入")
                            view.start()
                            self.root.update()
                            view.widget.set_progress(42)
                            holder, loader = view.holder, view.widget
                            self.assertGreaterEqual(holder.winfo_height(), loader.winfo_reqheight())
                            holder_bounds = (holder.winfo_rootx(), holder.winfo_rooty(),
                                             holder.winfo_rootx() + holder.winfo_width(),
                                             holder.winfo_rooty() + holder.winfo_height())
                            for widget in (loader, loader.canvas, loader.caption,
                                           loader.progress_label, loader.cancel_button):
                                self.assertTrue(widget.winfo_ismapped())
                                self.assertGreaterEqual(widget.winfo_rootx(), holder_bounds[0])
                                self.assertGreaterEqual(widget.winfo_rooty(), holder_bounds[1])
                                self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(), holder_bounds[2])
                                self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), holder_bounds[3])
                            button = loader.cancel_button
                            x, y = button.winfo_width() // 2, button.winfo_height() // 2
                            self.assertIs(self.root.winfo_containing(button.winfo_rootx() + x,
                                                                     button.winfo_rooty() + y), button)
                            button.event_generate("<ButtonPress-1>", x=x, y=y)
                            button.event_generate("<ButtonRelease-1>", x=x, y=y)
                            self.root.update()
                            self.assertFalse(loader.running)
                            self.assertFalse(loader.winfo_ismapped())
                            self.assertIsNone(view._after_id)
                            self.assertEqual(loader.value, 42)
                            self.assertEqual(view.input_text.get(), "主题与字号切换后保留输入")
                            self.assertIn("取消", view.message.get())
                        finally:
                            if view is not None:
                                view.dispose()
                            if host is not None:
                                host.destroy()
                            if window is not None:
                                canvas.delete(window)
                            self.root.update()
        finally:
            self.root.attributes("-topmost", previous_topmost)
            canvas.destroy()

    def test_all_previews_preserve_state_and_generate_runnable_source(self):
        for key in IDS:
            view = create_preview(key, self.root, palette=self.palette)
            view.pack(fill="both", expand=True)
            self.root.update()
            if key == "spinner":
                view.setting.set("72")
                view.text.set("保留说明")
            elif key in ("progress-bar", "circular-progress"):
                view.value.set(61)
            elif key in ("skeleton", "shimmer"):
                view.setting.set("card")
                view.enabled.set(False)
            elif key == "loading-button":
                view.text.set("保留的按钮标题")
            else:
                view.input_text.set("保留页面输入")
                view.widget.set_progress(61)
            view._parameters()
            before = (view.setting.get(), view.text.get(), view.value.get(), view.enabled.get())
            for mode in load_tokens()["themes"]:
                view.apply_palette(apply_theme(self.root, mode))
                view.set_reduced_motion(True)
                self.assertIsNone(view.widget._after_id)
                self.assertEqual(before, (view.setting.get(), view.text.get(), view.value.get(), view.enabled.get()))
            if key == "page-loader":
                self.assertEqual(view.input_text.get(), "保留页面输入")
                self.assertEqual(view.widget.value, 61)
            code = view.code()
            self.assertNotIn("apps.", code)
            namespace = {"__file__": str(ROOT / "loading-example.py")}
            exec(compile(code.replace("root.mainloop()", "root.update()\nroot.destroy()"), "example", "exec"), namespace)
            view.reset()
            view.dispose()
            self.root.update()

    def test_preview_button_reentry_and_cancel_keep_task_consistent(self):
        view = create_preview("loading-button", self.root, palette=self.palette)
        view.pack()
        self.root.update()
        view.widget.button.invoke()
        pending = view._after_id
        view.start()
        self.assertEqual(view._after_id, pending)
        self.assertTrue(view.widget.busy)
        view.set_visible(False)
        self.assertIsNone(view._after_id)
        self.assertIsNone(view.widget._after_id)
        view.set_visible(True)
        self.assertIsNotNone(view._after_id)
        view.outcome.set("失败")
        self.pump_until(lambda: not view.widget.busy)
        self.assertIn("失败", view.message.get())
        view.start()
        view.stop()
        self.assertFalse(view.widget.busy)
        self.assertIsNone(view._after_id)
        view.dispose()

    def test_all_previews_can_cancel_and_reset_after_thirty_rebuilds(self):
        for cycle in range(30):
            for key in IDS:
                view = create_preview(key, self.root, palette=self.palette, reduced_motion=True)
                view.pack(fill="both", expand=True)
                view.start()
                self.root.update()
                view.set_visible(False)
                self.assertIsNone(view._after_id)
                self.assertIsNone(view.widget._after_id)
                view.stop()
                view.reset()
                view.dispose()
            self.root.update()
            self.assertEqual(self.root.tk.splitlist(self.root.tk.call("after", "info")), (), cycle)


if __name__ == "__main__":
    unittest.main()

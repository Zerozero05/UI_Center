"""Behavior checks using real Tk widgets; require a desktop/Tk runtime."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import _tkinter
import tkinter as tk
from tkinter import ttk
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "components" / "tkinter"))
from ui_center import ActionBar, TaskPanel, apply_theme, load_tokens

spec = importlib.util.spec_from_file_location("uicenter_tk_demo", ROOT / "examples" / "tkinter" / "demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class TkBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry("760x650")
        self.errors = []
        self.root.report_callback_exception = lambda *details: self.errors.append(details)
        apply_theme(self.root)

    def tearDown(self):
        try:
            if self.root.winfo_exists():
                self.root.update_idletasks()
                self.root.destroy()
        except tk.TclError:
            pass
        self.assertEqual(self.errors, [], "Tk callbacks raised unexpected errors")

    def pump_until(self, condition, timeout=2):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if condition():
                return
            # update() drains every currently eligible timer. With deliberately
            # fast demo ticks, that can complete a task before a cancel test
            # regains control. Dispatch one real event, then observe state.
            self.root.tk.dooneevent(_tkinter.DONT_WAIT)
            time.sleep(0.002)
        self.fail("Timed out waiting for UI state")

    def make_demo(self, **kwargs):
        app = demo.DemoWindow(self.root, interval_ms=5, **kwargs)
        self.root.update()
        return app

    def test_theme_switch_preserves_data_focus_and_disabled_state(self):
        app = self.make_demo()
        app.project.set("长文本示例 · 保留用户输入")
        app.inputs[0].focus_force()
        self.root.update()
        for mode in ("dark", "light", "dark"):
            app.theme.set(mode)
            app.change_theme()
            self.root.update()
            tokens = load_tokens()["themes"][mode]
            self.assertEqual(ttk.Style(self.root).lookup("TFrame", "background"), tokens["background"])
            self.assertEqual(str(self.root.cget("background")), tokens["background"])
            self.assertEqual(app.project.get(), "长文本示例 · 保留用户输入")
            self.assertEqual(self.root.focus_get(), app.inputs[0])
            self.assertTrue(app.actions.cancel.instate(["disabled"]))

    def test_keyboard_tab_and_space_callbacks(self):
        calls = []
        bar = ActionBar(self.root, on_primary=lambda: calls.append("start"),
                        on_cancel=lambda: calls.append("cancel"), on_secondary=lambda: calls.append("reset"))
        bar.pack(fill="x")
        self.root.update()
        bar.primary.focus_force()
        self.root.update()
        bar.primary.event_generate("<Tab>")
        self.root.update()
        self.assertEqual(self.root.focus_get(), bar.secondary)
        bar.secondary.event_generate("<KeyPress-space>")
        bar.secondary.event_generate("<KeyRelease-space>")
        self.pump_until(lambda: len(calls) == 1)
        self.assertEqual(calls, ["reset"])
        bar.set_busy(True)
        bar.primary.invoke()
        bar.secondary.invoke()
        self.assertEqual(calls, ["reset"])
        bar.cancel.invoke()
        self.assertEqual(calls, ["reset", "cancel"])

    def test_modified_token_spacing_reaches_component_layout(self):
        destination = ROOT / "work" / "desktop" / ("spacing-" + str(time.time_ns()))
        destination.mkdir(parents=True)
        tokens_path = destination / "design-tokens.json"
        tokens = load_tokens()
        tokens["spacing"] = {"xs": 7, "sm": 13, "md": 21, "lg": 29, "xl": 37}
        tokens_path.write_text(json.dumps(tokens), encoding="utf-8")
        app = self.make_demo(tokens_path=tokens_path)
        self.assertEqual(int(app.actions.secondary.pack_info()["padx"]), 13)
        self.assertEqual(int(app.inputs[0].grid_info()["pady"]), 7)
        for widget, expected in ((app.panel.progress, (13, 13)),
                                 (app.panel.message_box, (0, 21)),
                                 (app.panel.detail_entry, (13, 0))):
            actual = widget.grid_info()["pady"]
            # Tk reports symmetric padding as one integer, asymmetric as a pair.
            actual = (actual, actual) if isinstance(actual, int) else actual
            self.assertEqual(actual, expected)
        # Calls without an explicit mapping keep reading the repository source.
        default_bar = ActionBar(self.root, on_primary=lambda: None,
                                on_cancel=lambda: None, on_secondary=lambda: None)
        self.assertEqual(int(default_bar.secondary.pack_info()["padx"]), load_tokens()["spacing"]["sm"])

    def test_success_disables_inputs_then_restores_controls(self):
        app = self.make_demo()
        app.amount.set("3")
        app.start()
        self.assertTrue(app.actions.primary.instate(["disabled"]))
        self.assertTrue(all(widget.instate(["disabled"]) for widget in app.inputs))
        self.assertTrue(app.actions.cancel.instate(["!disabled"]))
        app.actions.primary.invoke()
        self.pump_until(lambda: app.panel.task_state == "completed")
        self.assertEqual(app.completed, 3)
        self.assertEqual(len(app.panel.results.get_children()), 3)
        self.assertEqual(app.panel.count.get(), "3 / 3")
        self.assertTrue(app.actions.primary.instate(["!disabled"]))
        self.assertTrue(app.actions.cancel.instate(["disabled"]))
        self.assertEqual(str(app.inputs[-1].cget("state")), "readonly")
        app.reset()
        self.assertEqual(app.panel.task_state, "idle")
        self.assertEqual(app.panel.results.get_children(), ())

    def test_cancel_preserves_completed_rows_and_can_restart(self):
        app = self.make_demo()
        app.amount.set("20")
        app.start()
        self.pump_until(lambda: app.completed >= 1)
        done = app.completed
        app.cancel()
        self.assertEqual(app.panel.task_state, "cancelling")
        self.assertTrue(app.actions.cancel.instate(["disabled"]))
        app.cancel()
        self.pump_until(lambda: app.panel.task_state == "cancelled")
        self.assertEqual(app.completed, done)
        self.assertEqual(len(app.panel.results.get_children()), done)
        app.amount.set("1")
        app.start()
        self.pump_until(lambda: app.panel.task_state == "completed")
        self.assertEqual(len(app.panel.results.get_children()), 1)

    def test_error_keeps_partial_results_and_retry_succeeds(self):
        app = self.make_demo()
        app.amount.set("4")
        app.outcome.set("模拟失败")
        app.start()
        self.pump_until(lambda: app.panel.task_state == "error")
        self.assertEqual(app.completed, 2)
        self.assertEqual(len(app.panel.results.get_children()), 3)
        last = app.panel.results.get_children()[-1]
        self.assertIn("失败", app.panel.results.item(last, "values")[1])
        self.assertFalse(app.busy)
        app.outcome.set("正常完成")
        app.amount.set("1")
        app.start()
        self.pump_until(lambda: app.panel.task_state == "completed")

    def test_invalid_parameters_do_not_schedule_work(self):
        app = self.make_demo()
        for value in ("0", "51", "不是数字", "1.5"):
            app.amount.set(value)
            app.start()
            self.assertEqual(app.panel.task_state, "error")
            self.assertIsNone(app._pending)
            self.assertFalse(app.busy)
        app.amount.set("1")
        app.project.set("  ")
        app.start()
        self.assertEqual(app.panel.task_state, "error")
        self.assertIsNone(app._pending)

    def test_small_window_long_text_and_both_themes(self):
        app = self.make_demo()
        message = "这是一段较长的任务信息，需要随窗口换行并保留所有文字。" * 8
        self.root.geometry("580x570")
        app.panel.set_state("running", completed=1, total=8, message=message,
                            results=[("很长的虚构项目名称" * 10, "已完成（演示）")])
        for mode in ("light", "dark"):
            app.theme.set(mode)
            app.change_theme()
            self.root.update()
            self.assertEqual(app.panel.message.get(), message)
            self.assertLess(app.panel.message_label.winfo_reqheight(), 260)
            self.assertGreater(app.panel.results.winfo_height(), 20)
            for widget in (app.actions.primary, app.actions.cancel, app.panel.results):
                self.assertGreater(widget.winfo_width(), 20)
                self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(),
                                     self.root.winfo_rootx() + self.root.winfo_width())
        selected = app.panel.results.get_children()[0]
        app.panel.results.selection_set(selected)
        self.root.update()
        self.assertEqual(app.panel.selected_detail.get(), "很长的虚构项目名称" * 10 + " · 已完成（演示）")
        self.assertEqual(str(app.panel.detail_entry.cget("state")), "readonly")

    def test_feedback_full_result_and_footer_are_visible_at_both_sizes(self):
        app = self.make_demo()
        message = "长任务说明需要能滚动查看，不能挤走结果字段或键盘说明。" * 50
        app.panel.set_state("running", completed=1, total=8, message=message,
                            results=[("保留的完整结果名称", "已完成")])
        for geometry in ("760x650", "580x570"):
            self.root.geometry(geometry)
            self.root.update()
            for widget in (app.panel.message_label, app.panel.results, app.panel.detail_entry, app.footer):
                self.assertTrue(widget.winfo_ismapped(), geometry)
                self.assertGreater(widget.winfo_height(), 10, geometry)
                self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(),
                                     self.root.winfo_rooty() + self.root.winfo_height(), geometry)
            app.panel.message_label.yview_moveto(1)
            self.root.update()
            self.assertGreater(app.panel.message_label.yview()[0], 0)
            self.assertEqual(app.panel.message_label.get("1.0", "end-1c"), message)
        app.theme.set("dark")
        app.change_theme()
        self.root.update()
        self.assertEqual(app.panel.message_label.cget("background"), load_tokens()["themes"]["dark"]["input_background"])
        self.assertEqual(app.panel.message_label.cget("highlightcolor"), load_tokens()["themes"]["dark"]["focus"])
        self.assertEqual(app.panel.message_label.cget("highlightbackground"), load_tokens()["themes"]["dark"]["border"])

    def test_close_removes_pending_task_callback(self):
        app = self.make_demo()
        app.start()
        pending = app._pending
        self.assertIn(pending, self.root.tk.call("after", "info"))
        app.close()
        self.assertIsNone(app._pending)
        self.assertNotIn(pending, self.root.tk.call("after", "info"))
        app.close()

    def test_widget_rejects_invalid_progress(self):
        panel = TaskPanel(self.root)
        panel.state(["disabled"])
        self.assertTrue(panel.instate(["disabled"]))
        panel.state(["!disabled"])
        with self.assertRaises(ValueError):
            panel.set_state("unknown")
        with self.assertRaises(ValueError):
            panel.set_state("running", completed=4, total=3)
        panel.set_state("running", completed=0, total=0, message="没有已知总数")
        self.assertEqual(panel.progress.cget("maximum"), 1)


class SourceCopyTests(unittest.TestCase):
    def test_copy_runs_without_repository_imports(self):
        destination = ROOT / "work" / "desktop" / ("source-copy-" + str(time.time_ns()))
        destination.mkdir(parents=True)
        shutil.copytree(ROOT / "components" / "tkinter" / "ui_center", destination / "ui_center")
        shutil.copy2(ROOT / "tokens" / "design-tokens.json", destination / "design-tokens.json")
        consumer = destination / "consumer.py"
        consumer.write_text('''from pathlib import Path
import sys
import tkinter as tk
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
import ui_center
assert Path(ui_center.__file__).resolve().is_relative_to(base)
root = tk.Tk()
ui_center.apply_theme(root, "dark", tokens_path=base / "design-tokens.json")
spacing = ui_center.load_tokens(base / "design-tokens.json")["spacing"]
called = []
actions = ui_center.ActionBar(root, on_primary=lambda: called.append("start"), on_cancel=lambda: None, spacing=spacing)
actions.pack()
panel = ui_center.TaskPanel(root, spacing=spacing)
panel.pack()
panel.set_state("completed", completed=1, total=1, message="Copied consumer", results=[("Fake", "Complete")])
root.update()
actions.primary.invoke()
assert called == ["start"]
assert panel.task_state == "completed"
root.destroy()
print("Independent source consumer passed")
''', encoding="utf-8")
        result = subprocess.run([sys.executable, "-I", "-B", str(consumer)], cwd=destination,
                                capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Independent source consumer passed", result.stdout)


if __name__ == "__main__":
    unittest.main()

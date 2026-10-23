"""Real keyboard, state and reflow checks for workbench parameter controls."""
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components/tkinter"))
from apps.desktop.parameters import ParameterChoice, ParameterForm
from apps.desktop.reader import DocumentReader
from apps.desktop.resources import ResourceStore
from ui_center.theme import apply_theme, load_tokens


class ParameterFormTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry("700x460+40+40")
        self.errors = []
        self.root.report_callback_exception = lambda *error: self.errors.append(error)
        self.palette = apply_theme(self.root, "warm")

    def tearDown(self):
        self.root.destroy()
        self.assertEqual(self.errors, [])

    def test_boolean_native_choices_notify_once_and_preserve_disabled_model(self):
        value = tk.BooleanVar(self.root, True)
        calls = []
        choice = ParameterChoice(self.root, variable=value, options=((True, "可用"), (False, "禁用")),
                                 palette=self.palette, command=lambda: calls.append(value.get()))
        choice.pack(fill="x")
        self.root.update()
        self.assertTrue(all(not bool(int(button.cget("indicatoron"))) for button in choice.buttons.values()))
        choice.buttons[False].invoke()
        choice.buttons[False].invoke()
        self.assertEqual(calls, [False])
        value.set(True)
        self.assertEqual(calls, [False])
        choice.set_enabled(False)
        choice.buttons[False].invoke()
        self.assertTrue(value.get())
        value.set(False)
        self.assertEqual(choice.select(), False)
        choice.set_enabled(True)
        self.assertFalse(value.get())
        self.assertEqual(calls, [False])

    def test_arrow_enter_and_tab_have_one_selected_tab_stop(self):
        value = tk.StringVar(self.root, "short")
        calls = []
        choice = ParameterChoice(self.root, variable=value, options=(("short", "简短"), ("long", "长文本")),
                                 palette=self.palette, command=lambda: calls.append(value.get()))
        choice.pack(fill="x")
        after = ttk.Entry(self.root)
        after.pack()
        self.root.update()
        choice.buttons["short"].focus_force()
        choice.buttons["short"].event_generate("<KeyPress-Right>")
        self.root.update()
        self.assertEqual(value.get(), "long")
        self.assertEqual(calls, ["long"])
        self.assertEqual(self.root.focus_get(), choice.buttons["long"])
        self.assertEqual(str(self.root.tk.call("tk_focusNext", str(choice.buttons["long"]))), str(after))
        choice.buttons["long"].event_generate("<KeyPress-Home>")
        choice.buttons["short"].event_generate("<KeyPress-Return>")
        self.assertEqual(calls, ["long", "short"])

    def test_chinese_combo_roundtrips_original_values_and_reset_without_callback(self):
        value = tk.StringVar(self.root, "info")
        calls = []
        form = ParameterForm(self.root, palette=self.palette)
        form.pack(fill="x")
        combo = form.combo("语义状态", value, (("info", "提示"), ("success", "成功"),
                           ("warning", "警告"), ("error", "错误")), lambda: calls.append(value.get()))
        self.root.update()
        self.assertEqual(combo.get(), "提示")
        combo.set("错误")
        combo.event_generate("<<ComboboxSelected>>")
        self.assertEqual(value.get(), "error")
        self.assertEqual(calls, ["error"])
        value.set("info")
        self.assertEqual(combo.get(), "提示")
        self.assertEqual(calls, ["error"])

    def test_reflow_keeps_controls_and_values_at_large_fonts(self):
        form = ParameterForm(self.root, palette=self.palette)
        form.pack(fill="x")
        values = [tk.BooleanVar(self.root, i % 2 == 0) for i in range(4)]
        choices = [form.choice("参数" + str(i), value, ((True, "开启"), (False, "关闭")))
                   for i, value in enumerate(values)]
        self.root.update()
        wide_height = form.winfo_height()
        self.root.geometry("240x460")
        self.palette = apply_theme(self.root, "dark", font_scale=1.8)
        form.apply_palette(self.palette)
        self.root.update()
        self.assertGreater(form.winfo_height(), wide_height)
        for group in form._groups:
            self.assertGreaterEqual(group.winfo_x(), 0)
            self.assertLessEqual(group.winfo_x()+group.winfo_width(), form.winfo_width())
        self.assertEqual([choice.select() for choice in choices], [True, False, True, False])

    def test_destroy_removes_variable_traces_and_pending_layout(self):
        value = tk.StringVar(self.root, "a")
        before = value.trace_info()
        for _ in range(20):
            form = ParameterForm(self.root, palette=self.palette)
            form.choice("选择", value, (("a", "甲"), ("b", "乙")))
            form.combo("名称", value, (("a", "甲"), ("b", "乙")))
            form.destroy()
        self.root.update()
        self.assertEqual(value.trace_info(), before)

    def test_short_chinese_choices_do_not_wrap_when_space_is_available(self):
        form = ParameterForm(self.root, palette=self.palette)
        form.pack(fill="x")
        value = tk.BooleanVar(self.root, False)
        choice = form.choice("内容长度", value, ((False, "简短"), (True, "长文本")))
        self.root.update()
        height = tkfont.nametofont("TkDefaultFont", root=self.root).metrics("linespace")
        for button in choice.buttons.values():
            self.assertLessEqual(button.winfo_height(), height + 20)

    def test_document_scrollbars_follow_overflow_and_keep_selection_on_appearance(self):
        reader = DocumentReader(self.root, store=ResourceStore(ROOT), horizontal=True)
        reader.pack(fill="both", expand=True)
        reader.apply_palette(self.palette, load_tokens())
        reader.show("简短文本", markdown=False)
        self.root.update()
        self.assertFalse(reader.vertical.winfo_ismapped())
        self.assertFalse(reader.horizontal.winfo_ismapped())
        reader.show(("很长的代码内容" * 70 + "\n") * 100, markdown=False)
        self.root.update()
        self.assertTrue(reader.vertical.winfo_ismapped())
        self.assertTrue(reader.horizontal.winfo_ismapped())
        reader.text.yview_moveto(.5)
        reader.text.tag_add("sel", "50.0", "50.5")
        reader.apply_palette(apply_theme(self.root, "dark"), load_tokens())
        self.root.update()
        self.assertGreater(reader.text.yview()[0], .3)
        self.assertEqual(tuple(map(str, reader.text.tag_ranges("sel"))), ("50.0", "50.5"))
        reader.show("再次变短", markdown=False)
        self.root.update()
        self.assertFalse(reader.vertical.winfo_ismapped())
        self.assertFalse(reader.horizontal.winfo_ismapped())


if __name__ == "__main__":
    unittest.main()

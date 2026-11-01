"""Native theme resources and older consumer token compatibility."""
import json
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "components/tkinter"))
from ui_center.theme import apply_theme, load_tokens
from ui_center.loading import PageLoader


class VisualSystemTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.errors = []
        self.root.report_callback_exception = lambda *error: self.errors.append(error)

    def tearDown(self):
        self.root.update_idletasks()
        self.root.destroy()
        self.assertEqual(self.errors, [])

    def test_old_consumer_tokens_are_readable_without_rewriting_the_file(self):
        parent = ROOT / "work/v1.3.0/compatibility"
        parent.mkdir(parents=True, exist_ok=True)
        folder = tempfile.mkdtemp(dir=parent)
        tokens = load_tokens()
        for palette in tokens["themes"].values():
            del palette["divider"], palette["accent_soft"]
        path = Path(folder) / "tokens.json"
        original = json.dumps(tokens).encode()
        path.write_bytes(original)
        for mode in tokens["themes"]:
            palette = apply_theme(self.root, mode, tokens_path=path)
            self.assertEqual(palette["border"], tokens["themes"][mode]["border"])
            self.assertEqual(ttk.Style(self.root).lookup("TLabel", "foreground"), palette["foreground"])
        self.assertEqual(path.read_bytes(), original)

    def test_repeated_theme_and_size_changes_do_not_accumulate_button_images(self):
        for mode in ("warm", "sage", "light", "dark"):
            apply_theme(self.root, mode)
        baseline = set(self.root.tk.splitlist(self.root.tk.call("image", "names")))
        calls = []
        button = ttk.Button(self.root, text="应用设置", command=lambda: calls.append("applied"),
                            style="UIC.Primary.TButton")
        button.pack(padx=20, pady=20)
        for mode in ("warm", "sage", "light", "dark"):
            for scale in (1, 1.25, 1.5):
                apply_theme(self.root, mode, font_scale=scale)
                self.root.update()
                self.assertEqual(button.identify(button.winfo_width()//2, button.winfo_height()//2), "label")
                button.state(["disabled"])
                button.invoke()
                self.assertEqual(calls, [])
                button.state(["!disabled"])
        self.assertEqual(set(self.root.tk.splitlist(self.root.tk.call("image", "names"))), baseline)
        button.invoke()
        self.assertEqual(calls, ["applied"])

    def test_known_page_progress_stops_decoration_and_unknown_resumes_one_timer(self):
        palette = apply_theme(self.root)
        stage = ttk.Frame(self.root, width=320, height=240)
        stage.pack()
        stage.pack_propagate(False)
        loader = PageLoader(stage, palette=palette, value=35)
        loader.start()
        self.root.update()
        self.assertIsNone(loader._after_id)
        loader.set_progress(None)
        self.assertIsNotNone(loader._after_id)
        loader.set_progress(100)
        self.assertIsNone(loader._after_id)
        self.assertEqual(loader.progress_label.cget("text"), "100%")
        loader.dispose()


if __name__ == "__main__":
    unittest.main()

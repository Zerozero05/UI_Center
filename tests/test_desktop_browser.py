"""Real desktop browser behavior, resources and source/frozen CLI contract."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import tkinter as tk
from tkinter import ttk
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "tkinter"))

from apps.desktop.app import BrowserApp, work_area
from apps.desktop.catalog import ENTRIES, body_for, filter_entries, usage_for
from apps.desktop.resources import REQUIRED_RESOURCES, ResourceStore


def frozen_fixture():
    directory = ROOT / "work" / "browser" / ("assets-test-" + str(time.time_ns()))
    assets = directory / "assets"
    for name in REQUIRED_RESOURCES:
        destination = assets / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    information = {"version": (assets / "VERSION").read_text().strip(), "commit": "a" * 40}
    (assets / "build-info.json").write_text(json.dumps(information), encoding="utf-8")
    return directory, assets


class ResourceTests(unittest.TestCase):
    def test_frozen_assets_and_exact_identity(self):
        directory, assets = frozen_fixture()
        store = ResourceStore.from_entry(directory / "main.py", frozen=True)
        self.assertEqual(store.root, assets)
        self.assertEqual(store.commit, "a" * 40)
        self.assertEqual(store.version, (ROOT / "VERSION").read_text().strip())
        self.assertIn("/blob/" + "a" * 40 + "/docs/patterns.md", store.github_url("docs/patterns.md"))
        with self.assertRaises(ValueError):
            store.read("../outside.txt")

    def test_inconsistent_frozen_version_is_rejected(self):
        _directory, assets = frozen_fixture()
        (assets / "build-info.json").write_text(json.dumps({"version": "99.0.0", "commit": "a" * 40}))
        with self.assertRaisesRegex(ValueError, "版本信息"):
            ResourceStore(assets, frozen=True)

    def test_missing_asset_is_explicit_and_runtime_licenses_are_original(self):
        directory = ROOT / "work" / "browser" / ("missing-test-" + str(time.time_ns()))
        directory.mkdir(parents=True)
        with self.assertRaisesRegex(FileNotFoundError, "资料不完整"):
            ResourceStore(directory)
        _directory, assets = frozen_fixture()
        (assets / "licenses").mkdir()
        (assets / "licenses" / "fixture-license.txt").write_text("TEST FIXTURE COPYRIGHT\n", encoding="utf-8")
        self.assertIn("TEST FIXTURE COPYRIGHT", ResourceStore(assets, frozen=True).license_text())

    def test_catalog_reads_original_sections_and_code(self):
        store = ResourceStore(ROOT)
        guide = next(entry for entry in ENTRIES if entry.key == "guide-hierarchy")
        self.assertIn("## 视觉层次", body_for(store, guide))
        self.assertNotIn("## 布局与留白", body_for(store, guide))
        component = next(entry for entry in ENTRIES if entry.key == "tk-task")
        self.assertIn(usage_for(store, component).strip(), store.read(component.resource))
        self.assertIn("需在目标应用实现", guide.boundary)
        self.assertEqual(filter_entries("ActionGroup", "Android")[0].key, "android-actions")


class BrowserWidgetTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.errors = []
        self.root.report_callback_exception = lambda *details: self.errors.append(details)
        self.app = BrowserApp(self.root, ResourceStore(ROOT))
        self.root.update()

    def tearDown(self):
        if not self.app._closed:
            self.app.close()
        self.assertEqual(self.errors, [])

    def test_search_filter_empty_state_and_keyboard_focus(self):
        self.app.platform.set("Android")
        self.app.query.set("ActionGroup")
        self.root.update()
        self.assertEqual(self.app.entries.get_children(), ("android-actions",))
        self.assertTrue(self.app.preview_button.instate(["disabled"]))
        self.assertIn("未设备实测", self.app.boundary.cget("text"))
        self.app.description.text.focus_force()
        self.root.update()
        self.app.description.text.event_generate("<Control-f>")
        self.root.update()
        self.assertEqual(self.root.focus_get(), self.app.search_entry)
        self.app.query.set("没有对应条目zzzz")
        self.assertIsNone(self.app.current)
        self.assertTrue(self.app.copy_ai_button.instate(["disabled"]))
        self.app.search_entry.event_generate("<Escape>")
        self.root.update()
        self.assertEqual(self.app.query.get(), "")
        self.assertGreater(len(self.app.entries.get_children()), 1)
        self.assertTrue(all(next(entry for entry in ENTRIES if entry.key == key).platform in ("通用", "Android")
                            for key in self.app.entries.get_children()))

    def test_readonly_copy_and_development_provenance(self):
        self.app.select_entry("tk-task")
        original = self.app.description.text.get("1.0", "end-1c")
        self.app.description.text.insert("1.0", "UNAUTHORIZED EDIT")
        self.assertEqual(self.app.description.text.get("1.0", "end-1c"), original)
        self.app.copy_usage()
        self.assertEqual(self.root.clipboard_get(), usage_for(self.app.store, self.app.current))
        self.app.copy_ai()
        copied = self.root.clipboard_get()
        self.assertIn(self.app.store.commit, copied)
        self.assertIn("开发工作区", copied)
        self.assertIn("保留原业务", copied)

    def test_single_preview_shares_theme_without_clearing_state(self):
        self.app.select_entry("tk-theme")
        preview = self.app.open_preview()
        self.assertIs(self.app.open_preview(), preview)
        self.root.update()
        left, top, right, bottom = work_area(self.root)
        self.assertGreaterEqual(preview.root.winfo_rootx(), left)
        self.assertGreaterEqual(preview.root.winfo_rooty(), top)
        self.assertLessEqual(preview.root.winfo_rootx() + preview.root.winfo_width(), right)
        self.assertLessEqual(preview.root.winfo_rooty() + preview.root.winfo_height(), bottom)
        preview.project.set("保留这个输入")
        preview.panel.set_state("completed", completed=1, total=1, message="保留结果",
                                results=[("虚构数据", "已完成")])
        self.app.theme.set("dark")
        self.root.update()
        self.assertEqual(preview.theme.get(), "dark")
        self.assertEqual(preview.project.get(), "保留这个输入")
        self.assertEqual(preview.panel.task_state, "completed")
        preview.theme.set("light")
        preview.change_theme()
        self.root.update()
        self.assertEqual(self.app.theme.get(), "light")
        self.assertEqual(self.app.description.text.cget("background"), self.app.tokens["themes"]["light"]["surface"])
        preview.close()
        self.root.update()
        self.assertIsNone(self.app.preview)
        self.assertTrue(self.root.winfo_exists())

    def test_small_window_actions_and_long_documents_stay_available(self):
        self.app.select_entry("licenses")
        self.root.geometry("820x600")
        self.root.update()
        for widget in (self.app.copy_ai_button, self.app.copy_usage_button, self.app.preview_button,
                       self.app.source_button, self.app.status_label):
            self.assertTrue(widget.winfo_ismapped())
            self.assertGreater(widget.winfo_height(), 10)
            self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(),
                                 self.root.winfo_rootx() + self.root.winfo_width())
            self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(),
                                 self.root.winfo_rooty() + self.root.winfo_height())
        text = self.app.description.text
        text.yview_moveto(.6)
        self.root.update()
        before = text.yview()[0]
        self.app.theme.set("dark")
        self.root.update()
        self.assertAlmostEqual(text.yview()[0], before, places=2)
        self.assertEqual(ttk.Style(self.root).lookup("TNotebook.Tab", "background", ("selected",)),
                         self.app.tokens["themes"]["dark"]["surface"])

    def test_guidelines_are_not_presented_as_implemented_components(self):
        self.app.select_entry("pattern-files")
        self.assertIn("规范建议", self.app.boundary.cget("text"))
        self.assertTrue(self.app.preview_button.instate(["disabled"]))
        self.app.copy_ai()
        self.assertIn("不代表已有可复制", self.root.clipboard_get())


class BrowserCliTests(unittest.TestCase):
    def test_real_entry_smoke_report_and_exit_code(self):
        report = ROOT / "work" / "browser" / ("cli-test-" + str(time.time_ns()) + ".json")
        result = subprocess.run([sys.executable, "-B", str(ROOT / "apps" / "desktop" / "main.py"),
                                 "--smoke-test", str(report)], cwd=ROOT.parent,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "passed")
        self.assertEqual(data["version"], (ROOT / "VERSION").read_text().strip())
        self.assertFalse(data["frozen"])
        self.assertTrue(all(item["passed"] for item in data["checks"]))
        self.assertGreaterEqual(len(data["checks"]), 13)


if __name__ == "__main__":
    unittest.main()

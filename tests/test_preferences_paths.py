"""Appearance data follows the program, while source runs remain isolated.

No Tk windows are created. Every fixture stays under work/v1.2.1.
"""

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apps.desktop import preferences


class PreferencesPathTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / "work" / "v1.2.1"
        parent.mkdir(parents=True, exist_ok=True)
        self.directory = Path(tempfile.mkdtemp(prefix="preferences-paths-", dir=parent))

    def test_portable_uses_executable_directory_and_resolves_each_instance(self):
        first = self.directory / "portable-one"
        second = self.directory / "portable-two"
        with patch.object(preferences.sys, "frozen", True, create=True), \
                patch.object(preferences, "__file__", str(first / "_internal/apps/desktop/preferences.py")), \
                patch.object(preferences.sys, "executable", str(first / "UI_Center.exe")):
            self.assertEqual(preferences.program_directory(), first.resolve())
            self.assertEqual(preferences.Preferences().path, first / "data/preferences.json")
            with patch.object(preferences.sys, "executable", str(second / "UI_Center.exe")):
                self.assertEqual(preferences.Preferences().path, second / "data/preferences.json")
            self.assertIsInstance(preferences.DEFAULT_PATH, Path)
        self.assertFalse(first.exists(), "Resolving a path must not create its directory")
        self.assertFalse(second.exists())

    def test_onefile_ignores_temporary_meipass_and_saves_next_to_executable(self):
        program = self.directory / "single-file"
        extraction = self.directory / "temporary" / "_MEI12345"
        with patch.object(preferences.sys, "frozen", True, create=True), \
                patch.object(preferences.sys, "executable", str(program / "UI_Center_v1.2.1.exe")), \
                patch.object(preferences.sys, "_MEIPASS", str(extraction), create=True), \
                patch.object(preferences, "__file__", str(extraction / "apps/desktop/preferences.py")):
            store = preferences.Preferences()
            self.assertEqual(preferences.program_directory(), program.resolve())
            self.assertEqual(store.path, program / "data/preferences.json")
            self.assertTrue(store.save(preferences.DEFAULTS))
        self.assertTrue((program / "data/preferences.json").is_file())
        self.assertFalse(extraction.exists(), "One-file extraction must not become persistent storage")

    def test_current_working_directory_does_not_change_installed_data_path(self):
        program = self.directory / "portable"
        locations = (self.directory / "unrelated", self.directory / "中文 工作目录")
        for directory in locations:
            directory.mkdir()
        original = Path.cwd()
        try:
            with patch.object(preferences.sys, "frozen", True, create=True), \
                    patch.object(preferences.sys, "executable", str(program / "UI_Center.exe")):
                for directory in locations:
                    os.chdir(directory)
                    self.assertEqual(preferences.program_directory(), program.resolve())
                    self.assertEqual(preferences.default_preferences_path(), program / "data/preferences.json")
                    self.assertEqual(preferences.Preferences().path, program / "data/preferences.json")
        finally:
            os.chdir(original)

    def test_source_data_stays_in_that_repository_work_directory(self):
        repository = self.directory / "UI_Center" / "dev"
        module = repository / "apps/desktop/preferences.py"
        installed = self.directory / "UI_Center"
        with patch.object(preferences.sys, "frozen", False, create=True), \
                patch.object(preferences.sys, "executable", str(installed / "UI_Center.exe")), \
                patch.object(preferences, "__file__", str(module)):
            store = preferences.Preferences()
            self.assertEqual(preferences.program_directory(), repository.resolve())
            self.assertEqual(store.path, repository / "work/data/preferences.json")
            self.assertTrue(store.save({"theme": "sage", "font_scale": 125, "motion": "reduced"}))
        self.assertFalse((installed / "data").exists(), "Source runs must not change installed settings")
        self.assertTrue((repository / "work/data/preferences.json").is_file())

    def test_explicit_path_takes_priority_without_resolving_any_default(self):
        explicit = self.directory / "explicit" / "settings.json"
        values = {"theme": "dark", "font_scale": 150, "motion": "normal", "query": "do not persist"}
        with patch.object(preferences, "default_preferences_path", side_effect=AssertionError("default must not be used")):
            store = preferences.Preferences(explicit)
            self.assertEqual(store.path, explicit)
            self.assertTrue(store.save(values))
        self.assertEqual(json.loads(explicit.read_text(encoding="utf-8")),
                         {key: values[key] for key in preferences.DEFAULTS})

    def test_default_save_creates_only_new_data_and_no_old_top_level_directory(self):
        projects = self.directory / "projects"
        program = projects / "UI_Center"
        old_data = projects / "UI_Center_Data"
        with patch.object(preferences.sys, "frozen", True, create=True), \
                patch.object(preferences.sys, "executable", str(program / "UI_Center.exe")):
            store = preferences.Preferences()
            self.assertEqual(store.path, program / "data/preferences.json")
            self.assertTrue(store.save({"theme": "light", "font_scale": 100, "motion": "system"}))
        self.assertEqual(sorted(path.relative_to(projects).as_posix() for path in projects.rglob("*") if path.is_file()),
                         ["UI_Center/data/preferences.json"])
        self.assertFalse(old_data.exists())

    def test_old_top_level_settings_are_not_read_or_migrated_automatically(self):
        projects = self.directory / "projects"
        program = projects / "UI_Center"
        old_data = projects / "UI_Center_Data"
        old_data.mkdir(parents=True)
        old_file = old_data / "preferences.json"
        old_file.write_text('{"theme":"dark","font_scale":150,"motion":"normal"}', encoding="utf-8")
        original = old_file.read_bytes()
        with patch.object(preferences.sys, "frozen", True, create=True), \
                patch.object(preferences.sys, "executable", str(program / "UI_Center.exe")):
            store = preferences.Preferences()
            self.assertEqual(store.path, program / "data/preferences.json")
            self.assertEqual(store.load(), preferences.DEFAULTS)
            self.assertFalse(store.path.exists())
            self.assertTrue(store.save({"theme": "sage", "font_scale": 125, "motion": "reduced"}))
        self.assertEqual(old_file.read_bytes(), original)
        self.assertEqual(sorted(path.name for path in old_data.iterdir()), ["preferences.json"])

    def test_existing_new_location_settings_keep_all_three_values_without_rewrite(self):
        program = self.directory / "portable"
        path = program / "data/preferences.json"
        path.parent.mkdir(parents=True)
        values = {"theme": "sage", "font_scale": 125, "motion": "reduced"}
        path.write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8-sig")
        original = path.read_bytes()
        with patch.object(preferences.sys, "frozen", True, create=True), \
                patch.object(preferences.sys, "executable", str(program / "UI_Center.exe")):
            store = preferences.Preferences()
            self.assertEqual(store.path, path)
            self.assertEqual(store.load(), values)
            self.assertEqual(store.notice, "")
        self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()

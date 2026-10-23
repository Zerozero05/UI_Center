"""Exercise the frozen write guard with mocked paths, no Tk or filesystem writes."""
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apps.desktop import smoke


class SmokeWriteGuardTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = ROOT / "work" / "v1.2.1" / "smoke-guard"
        self.program = self.sandbox / "copied-program"
        self.default_path = self.program / "data" / "preferences.json"
        self.report_path = self.sandbox / "reports" / "smoke.json"
        self.app = SimpleNamespace(
            root=Mock(),
            store=SimpleNamespace(version="1.2.1", commit="a" * 40, frozen=True),
            preferences=SimpleNamespace(path=self.report_path.parent / "preferences-smoke.json"),
            close=Mock(),
            show_help=Mock(side_effect=RuntimeError("non-GUI probe reached regular smoke")),
        )

    def test_lexically_inside_but_resolved_outside_rejects_before_default_preferences_access(self):
        outside = ROOT / "work" / "v1.2.1" / "outside" / "preferences.json"
        self.assertTrue(self.default_path.is_relative_to(self.sandbox))
        self.assertFalse(outside.is_relative_to(self.sandbox))
        original_resolve = type(self.default_path).resolve

        def resolve_target(path, *args, **kwargs):
            if path == self.default_path:
                return outside
            return original_resolve(path, *args, **kwargs)

        with patch.dict(os.environ, {"UI_CENTER_SMOKE_SANDBOX": str(self.sandbox)}), \
                patch.object(smoke.sys, "executable", str(self.program / "UI_Center.exe")), \
                patch.object(smoke, "program_directory", return_value=self.program), \
                patch.object(smoke, "default_preferences_path", return_value=self.default_path), \
                patch.object(type(self.default_path), "resolve", new=resolve_target), \
                patch.object(smoke, "Preferences") as preferences, \
                patch.object(smoke, "write_report") as write_report:
            result = smoke.run_smoke(self.app, self.report_path)

        self.assertEqual(result, 1)
        preferences.assert_not_called()
        preferences.return_value.save.assert_not_called()
        self.app.show_help.assert_not_called()
        self.app.close.assert_called_once_with()
        write_report.assert_called_once()
        report = write_report.call_args.args[1]
        self.assertEqual(report["status"], "failed")
        self.assertTrue(all(check["passed"] for check in report["checks"][:-1]))
        self.assertEqual(report["checks"][-1],
                         {"name": "default_probe_is_inside_explicit_sandbox", "passed": False})
        self.assertIn("AssertionError: default_probe_is_inside_explicit_sandbox", report["error"])

    def test_normal_frozen_smoke_without_sandbox_never_starts_default_write_probe(self):
        environment = dict(os.environ)
        environment.pop("UI_CENTER_SMOKE_SANDBOX", None)
        with patch.dict(os.environ, environment, clear=True), \
                patch.object(smoke.sys, "executable", str(self.program / "UI_Center.exe")), \
                patch.object(smoke, "program_directory", return_value=self.program), \
                patch.object(smoke, "default_preferences_path", return_value=self.default_path), \
                patch.object(smoke, "Preferences") as preferences, \
                patch.object(smoke, "write_report") as write_report:
            smoke.run_smoke(self.app, self.report_path)

        preferences.assert_not_called()
        preferences.return_value.save.assert_not_called()
        self.app.show_help.assert_called_once_with()
        self.app.close.assert_called_once_with()
        report = write_report.call_args.args[1]
        self.assertTrue(all(check["passed"] for check in report["checks"]))
        self.assertNotIn("default_probe_is_inside_explicit_sandbox",
                         [check["name"] for check in report["checks"]])
        # This intentional stop prevents later GUI calls; it is not a smoke success.
        self.assertEqual(report["error"], "RuntimeError: non-GUI probe reached regular smoke")


if __name__ == "__main__":
    unittest.main()

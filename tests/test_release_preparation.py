"""Reject stale evidence if a tested runtime artifact is replaced.

SPDX-License-Identifier: AGPL-3.0-only
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_preparation", ROOT / "scripts/prepare_desktop_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseEvidenceTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / "work/v1.2.1/release-evidence-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.folder = Path(tempfile.mkdtemp(dir=parent))
        self.commit = "1" * 40
        self.artifacts = []
        for mode, name in (("portable", "UI_Center_v1.2.1_Windows_x64_Portable.zip"),
                           ("single", "UI_Center_v1.2.1_Windows_x64.exe")):
            path = self.folder / name
            path.write_bytes(("fixture:" + mode).encode())
            artifact = {"name": name, "bytes": path.stat().st_size,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            self.artifacts.append(artifact)
            for prefix in ("", "relocated-"):
                self.write("smoke-" + prefix + mode + ".json", {"status": "passed", "version": "1.2.1",
                           "commit": self.commit, "frozen": True, "checks": [{"name": "fixture", "passed": True}],
                           "artifact": artifact})
        self.write("verify-desktop-report.json", {"status": "package_integrity_passed", "version": "1.2.1",
                   "commit": self.commit, "artifacts": self.artifacts})

    def write(self, name, contents):
        (self.folder / name).write_text(json.dumps(contents), encoding="utf-8")

    def test_matching_evidence_accepts_exact_bytes(self):
        self.assertEqual(len(release.validate_runtime_reports(self.folder, "1.2.1", self.commit)), 2)

    def test_replaced_executable_is_rejected(self):
        (self.folder / self.artifacts[1]["name"]).write_bytes(b"replacement")
        with self.assertRaisesRegex(ValueError, "artifact hash/size mismatch"):
            release.validate_runtime_reports(self.folder, "1.2.1", self.commit)

    def test_stale_smoke_is_rejected_even_if_integrity_is_current(self):
        path = self.folder / "smoke-portable.json"
        smoke = json.loads(path.read_text())
        smoke["artifact"]["sha256"] = "0" * 64
        self.write(path.name, smoke)
        with self.assertRaisesRegex(ValueError, "not bound to these artifact bytes"):
            release.validate_runtime_reports(self.folder, "1.2.1", self.commit)

    def test_previous_release_report_cannot_approve_the_new_candidate(self):
        path = self.folder / "verify-desktop-report.json"
        report = json.loads(path.read_text())
        report["version"] = "1.2.0"
        self.write(path.name, report)
        with self.assertRaisesRegex(ValueError, "integrity report identity/status"):
            release.validate_runtime_reports(self.folder, "1.2.1", self.commit)

    def test_other_commit_smoke_cannot_approve_matching_runtime_bytes(self):
        path = self.folder / "smoke-single.json"
        smoke = json.loads(path.read_text())
        smoke["commit"] = "2" * 40
        self.write(path.name, smoke)
        with self.assertRaisesRegex(ValueError, "Frozen smoke identity"):
            release.validate_runtime_reports(self.folder, "1.2.1", self.commit)

    def test_missing_relocated_report_cannot_approve_original_pair(self):
        path = self.folder / "smoke-relocated-portable.json"
        # Retain the withheld report as evidence instead of deleting a fixture.
        path.rename(path.with_suffix(".withheld.json"))
        with self.assertRaisesRegex(FileNotFoundError, "smoke-relocated-portable"):
            release.validate_runtime_reports(self.folder, "1.2.1", self.commit)

    def test_relocated_report_from_other_commit_is_rejected(self):
        path = self.folder / "smoke-relocated-single.json"
        smoke = json.loads(path.read_text())
        smoke["commit"] = "2" * 40
        self.write(path.name, smoke)
        with self.assertRaisesRegex(ValueError, "Frozen smoke identity failed: relocated-single"):
            release.validate_runtime_reports(self.folder, "1.2.1", self.commit)

    def test_prepare_rejects_previous_version_before_git_or_archive_writes(self):
        (self.folder / "VERSION").write_text("1.2.0\n", encoding="utf-8")
        with mock.patch.object(release, "ROOT", self.folder), mock.patch.object(release, "git") as git:
            with self.assertRaisesRegex(ValueError, "restricted to 1.2.1"):
                release.prepare(self.folder)
            git.assert_not_called()
        self.assertFalse((self.folder / "UI_Center_v1.2.0_Source.zip").exists())


if __name__ == "__main__":
    unittest.main()

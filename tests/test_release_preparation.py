"""Reject stale evidence if a tested runtime artifact is replaced.

SPDX-License-Identifier: AGPL-3.0-only
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_preparation", ROOT / "scripts/prepare_desktop_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.folder = ROOT / "work/release-evidence-tests" / str(time.time_ns())
        self.folder.mkdir(parents=True)
        self.commit = "1" * 40
        self.artifacts = []
        for mode, name in (("portable", "UI_Center_v1.1.0_Windows_x64_Portable.zip"),
                           ("single", "UI_Center_v1.1.0_Windows_x64.exe")):
            path = self.folder / name
            path.write_bytes(("fixture:" + mode).encode())
            artifact = {"name": name, "bytes": path.stat().st_size,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            self.artifacts.append(artifact)
            self.write("smoke-" + mode + ".json", {"status": "passed", "version": "1.1.0",
                       "commit": self.commit, "frozen": True, "checks": [{"name": "fixture", "passed": True}],
                       "artifact": artifact})
        self.write("verify-desktop-report.json", {"status": "package_integrity_passed", "version": "1.1.0",
                   "commit": self.commit, "artifacts": self.artifacts})

    def write(self, name, contents):
        (self.folder / name).write_text(json.dumps(contents), encoding="utf-8")

    def test_matching_evidence_accepts_exact_bytes(self):
        self.assertEqual(len(release.validate_runtime_reports(self.folder, "1.1.0", self.commit)), 2)

    def test_replaced_executable_is_rejected(self):
        (self.folder / self.artifacts[1]["name"]).write_bytes(b"replacement")
        with self.assertRaisesRegex(ValueError, "artifact hash/size mismatch"):
            release.validate_runtime_reports(self.folder, "1.1.0", self.commit)

    def test_stale_smoke_is_rejected_even_if_integrity_is_current(self):
        path = self.folder / "smoke-portable.json"
        smoke = json.loads(path.read_text())
        smoke["artifact"]["sha256"] = "0" * 64
        self.write(path.name, smoke)
        with self.assertRaisesRegex(ValueError, "not bound to these artifact bytes"):
            release.validate_runtime_reports(self.folder, "1.1.0", self.commit)


if __name__ == "__main__":
    unittest.main()

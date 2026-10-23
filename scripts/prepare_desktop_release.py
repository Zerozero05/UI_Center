"""Prepare verified v1.2.1 candidate files; never publishes anything.

SPDX-License-Identifier: AGPL-3.0-only
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def validate_runtime_reports(directory, version, commit):
    artifacts = [directory / f"UI_Center_v{version}_Windows_x64_Portable.zip",
                 directory / f"UI_Center_v{version}_Windows_x64.exe"]
    integrity = json.loads((directory / "verify-desktop-report.json").read_text(encoding="utf-8-sig"))
    if not (integrity.get("status") == "package_integrity_passed"
            and integrity.get("version") == version and integrity.get("commit") == commit):
        raise ValueError("Package integrity report identity/status failed")
    recorded = {item["name"]: item for item in integrity.get("artifacts", [])}
    if len(integrity.get("artifacts", [])) != 2 or set(recorded) != {path.name for path in artifacts}:
        raise ValueError("Package integrity report must name exactly both runtime artifacts")
    for mode, path in zip(("portable", "single"), artifacts):
        actual = {"name": path.name, "bytes": path.stat().st_size,
                  "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        if recorded[path.name] != actual:
            raise ValueError("Verified artifact hash/size mismatch: " + path.name)
        for prefix in ("", "relocated-"):
            report_name = prefix + mode
            smoke = json.loads((directory / f"smoke-{report_name}.json").read_text(encoding="utf-8-sig"))
            if not (smoke.get("status") == "passed" and smoke.get("version") == version
                    and smoke.get("commit") == commit and smoke.get("frozen") is True):
                raise ValueError("Frozen smoke identity failed: " + report_name)
            if not smoke.get("checks") or not all(item["passed"] for item in smoke["checks"]):
                raise ValueError("Frozen smoke checks failed: " + report_name)
            if smoke.get("artifact") != actual:
                raise ValueError("Smoke report is not bound to these artifact bytes: " + report_name)
    return artifacts


def prepare(directory):
    version = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    if version != "1.2.1":
        raise ValueError("This candidate release preparation is restricted to 1.2.1")
    commit = git("rev-parse", "HEAD").decode().strip()
    runtime = validate_runtime_reports(directory, version, commit)
    archive_path = directory / f"UI_Center_v{version}_Source.zip"
    subprocess.run(["git", "-C", str(ROOT), "archive", "--format=zip", "--prefix=UI_Center/",
                    f"--output={archive_path}", "HEAD"], check=True)
    tracked = git("ls-files", "-z").decode().rstrip("\0").split("\0")
    with zipfile.ZipFile(archive_path) as archive:
        names = {item.filename for item in archive.infolist() if not item.is_dir()}
        if names != {"UI_Center/" + name for name in tracked}:
            raise ValueError("Source archive file set differs from Git")
        for name in tracked:
            if archive.read("UI_Center/" + name) != git("show", "HEAD:" + name):
                raise ValueError("Source archive differs: " + name)
    assets = runtime + [archive_path]
    lines = [hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name for path in assets]
    (directory / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    notes = (ROOT / f"docs/releases/v{version}.md").read_text(encoding="utf-8-sig").rstrip()
    notes += f"\n\n源码提交：`{commit}`。本次 Windows 源码/便携包/单文件包及 Android 构建检查均需成功后才公开。\n"
    notes += "\n附件实际大小：\n\n"
    notes += "\n".join(f"- `{path.name}`：{path.stat().st_size:,} 字节。" for path in assets)
    notes += "\n\n" + "两种冻结包均在中文及空格路径、整个运行目录迁移后、无 Python/Tcl 环境变量及无关工作目录下完成真实控件冒烟；四份报告均绑定同一源码提交与对应附件字节，具体检查见该次 Actions 日志。\n"
    (directory / "release-notes.md").write_text(notes, encoding="utf-8")
    print(f"PASS: source archive matches {len(tracked)} Git files; three assets hashed for {commit}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.directory.resolve())

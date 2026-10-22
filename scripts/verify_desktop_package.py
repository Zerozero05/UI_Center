"""Verify archive/source identity. This does not claim a frozen GUI smoke test passed.

SPDX-License-Identifier: AGPL-3.0-only
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packaging"))
from desktop_common import (PYINSTALLER_VERSION, asset_filenames, asset_names,
                            check_windows_executable, git_bytes, native_notices, safe_member, sha256,
                            source_commit, version_value, windows_system_runtime)


def verify_resources(read, prefix, available, commit, version):
    names = asset_names()
    allowed = {prefix + name for name in names}
    generated = {prefix + "build-info.json", prefix + "licenses/manifest.json", prefix + "licenses/binaries.json"}
    for name in names:
        actual = read(prefix + name)
        if actual != git_bytes(commit, name):
            raise ValueError("Packaged resource differs from Git: " + name)
    metadata = json.loads(read(prefix + "build-info.json"))
    if metadata.get("version") != version or metadata.get("commit") != commit:
        raise ValueError("Packaged version/source commit does not match the requested identity")
    if metadata.get("pyinstaller") != PYINSTALLER_VERSION:
        raise ValueError("Packaged PyInstaller version differs from the pinned build tool")
    manifest = json.loads(read(prefix + "licenses/manifest.json"))
    snapshots = {entry["path"]: entry for entry in json.loads(
        git_bytes(commit, "packaging/licenses/sources.json"))["files"]}
    license_names = set()
    for entry in manifest["files"]:
        name = safe_member(entry["path"])
        if name in license_names or "/" in name:
            raise ValueError("Duplicate or nested runtime license: " + name)
        contents = read(prefix + "licenses/" + name)
        if not contents or sha256(contents) != entry["sha256"]:
            raise ValueError("Missing or changed runtime license: " + name)
        if name in snapshots:
            if entry != snapshots[name] or contents != git_bytes(commit, "packaging/licenses/" + name):
                raise ValueError("Upstream notice differs from the committed snapshot: " + name)
        elif name not in {"Python-LICENSE.txt", "TclTk-distribution-LICENSE.txt"} and not name.startswith("PyInstaller-"):
            raise ValueError("Unrecognized runtime license: " + name)
        license_names.add(name)
        generated.add(prefix + "licenses/" + name)
    if not {"Python-LICENSE.txt", "TclTk-distribution-LICENSE.txt"} <= license_names:
        raise ValueError("Python and Tcl/Tk distribution licenses must be present")
    if read(prefix + "licenses/Python-LICENSE.txt") != read(prefix + "licenses/TclTk-distribution-LICENSE.txt"):
        raise ValueError("The shared Python/Tcl/Tk distribution notices must remain unmodified")
    if not any(name.startswith("PyInstaller-") for name in license_names):
        raise ValueError("The PyInstaller license/bootloader exception must be present")
    asset_members = {name for name in available if name.startswith(prefix)}
    if asset_members != allowed | generated:
        raise ValueError("The package assets differ from the explicit allowlist")
    inventory = json.loads(read(prefix + "licenses/binaries.json"))
    if inventory.get("license_files") != manifest["files"]:
        raise ValueError("The binary and license manifests disagree")
    for entry in inventory["binaries"]:
        if windows_system_runtime(entry["path"]):
            raise ValueError("Package incorrectly bundles a Windows-provided UCRT/API-set library")
        provider, required = native_notices(entry["path"])
        if entry.get("provider") != provider or entry.get("distribution_notices") != required:
            raise ValueError("Incorrect native dependency license mapping: " + entry["path"])
        if not set(required) <= license_names:
            raise ValueError("Missing native dependency license: " + entry["path"])
    return metadata, inventory, len(names)


def verify_binaries(read, available, inventory, prefix):
    native = {name for name in available if name.lower().endswith((".dll", ".pyd"))}
    declared = set()
    for entry in inventory["binaries"]:
        path = prefix + safe_member(entry["path"])
        declared.add(path)
        if sha256(read(path)) != entry["sha256"]:
            raise ValueError("Runtime binary differs from the inventory: " + path)
    if native != declared:
        raise ValueError("Actual native dependencies differ from the recorded inventory")
    return len(native)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portable-zip", type=Path, required=True)
    parser.add_argument("--single-exe", type=Path, required=True)
    parser.add_argument("--version")
    parser.add_argument("--source-commit")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    version = version_value(args.version)
    commit = source_commit(args.source_commit)
    portable_name, single_name = asset_filenames(version)
    if args.portable_zip.name != portable_name or args.single_exe.name != single_name:
        raise ValueError("Release artifact names do not match the version/platform contract")
    with zipfile.ZipFile(args.portable_zip) as archive:
        files = [entry for entry in archive.infolist() if not entry.is_dir()]
        names = [safe_member(entry.filename) for entry in files]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive member")
        available = set(names)
        if "UI_Center.exe" not in available or any(name != "UI_Center.exe" and not name.startswith("_internal/")
                                                  for name in available):
            raise ValueError("Portable ZIP must have UI_Center.exe and its _internal directory at the root")
        if any(name.lower().endswith(".py") for name in available):
            raise ValueError("Unexpected loose source file in the portable runtime")
        check_windows_executable(archive.read("UI_Center.exe"))
        metadata, inventory, resource_count = verify_resources(archive.read, "_internal/assets/", available, commit, version)
        binary_count = verify_binaries(archive.read, available, inventory, "_internal/")
    single_data = args.single_exe.read_bytes()
    check_windows_executable(single_data)
    try:
        from PyInstaller.archive.readers import CArchiveReader
    except ImportError as error:
        raise ValueError("Single-file inspection needs the pinned PyInstaller build environment") from error
    single = CArchiveReader(str(args.single_exe))
    single_members = {safe_member(name): name for name in single.toc}
    if len(single_members) != len(single.toc):
        raise ValueError("Duplicate normalized single-file archive member")
    single_names = set(single_members)
    if any(name.lower().endswith(".py") for name in single_names):
        raise ValueError("Unexpected loose source file in the single-file runtime")
    def read_single(name):
        return single.extract(single_members[name])
    single_metadata, single_inventory, single_resource_count = verify_resources(read_single, "assets/", single_names, commit, version)
    if single_metadata != metadata or single_inventory != inventory or single_resource_count != resource_count:
        raise ValueError("Portable and single-file metadata/resources differ")
    verify_binaries(read_single, single_names, single_inventory, "")
    report = {"status": "package_integrity_passed", "version": version, "commit": commit,
              "resources_compared_with_git": resource_count, "native_binaries_checked": binary_count,
              "runtime_smoke_test": "not_performed_by_this_verifier",
              "artifacts": [{"name": path.name, "bytes": path.stat().st_size,
                             "sha256": sha256(path.read_bytes())}
                            for path in (args.portable_zip, args.single_exe)]}
    if args.report:
        if args.report.exists():
            raise ValueError("Refusing to overwrite an existing verification report")
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.CalledProcessError) as error:
        print("Desktop package verification failed: " + str(error), file=sys.stderr)
        raise SystemExit(1)

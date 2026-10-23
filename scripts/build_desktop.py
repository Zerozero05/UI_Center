"""Build the two Windows x64 assets. Never installs packages or deletes old outputs.

SPDX-License-Identifier: AGPL-3.0-only
"""
from pathlib import Path
import argparse
import importlib.metadata
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packaging"))
from desktop_common import (PYINSTALLER_VERSION, asset_filenames, check_committed_sources,
                            check_inputs, license_snapshots, native_notices, sha256,
                            source_commit, version_value, windows_system_runtime)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def collect_licenses(target):
    """Keep the actual CPython distribution notices, including its Windows/Tcl/Tk terms."""
    notices = []
    python_license = next((path for name in ("LICENSE.txt", "LICENSE")
                           if (path := Path(sys.base_prefix) / name).is_file()), None)
    if python_license is None:
        raise ValueError("The Python distribution must include its complete LICENSE file")
    text = python_license.read_text(encoding="utf-8-sig")
    if "Tcl/Tk" not in text and "Scriptics Corporation" not in text:
        raise ValueError("The installed Python notices do not contain the bundled Tcl/Tk terms")
    if "Microsoft" not in text or "Distributable Code" not in text:
        raise ValueError("The installed Python notices lack the Windows runtime redistributable conditions")
    for name in ("Python-LICENSE.txt", "TclTk-distribution-LICENSE.txt"):
        output = target / name
        output.write_bytes(python_license.read_bytes())
        notices.append({"path": name, "sha256": sha256(output.read_bytes()),
                        "source": "Installed CPython Windows distribution LICENSE (unmodified)"})
    distribution = importlib.metadata.distribution("pyinstaller")
    license_files = [entry for entry in distribution.files or ()
                     if Path(str(entry)).name.lower().startswith(("copying", "license", "notice"))]
    if not license_files:
        raise ValueError("PyInstaller's installed distribution is missing its license/bootloader exception")
    for index, entry in enumerate(license_files):
        original = Path(distribution.locate_file(entry))
        if not original.is_file():
            continue
        name = f"PyInstaller-{index + 1}-{original.name}"
        output = target / name
        output.write_bytes(original.read_bytes())
        notices.append({"path": name, "sha256": sha256(output.read_bytes()),
                        "source": "Installed PyInstaller " + PYINSTALLER_VERSION + " distribution (unmodified)"})
    write_json(target / "manifest.json", {"files": notices})
    return notices


def windows_version_file(path, version):
    number = tuple(map(int, version.split("."))) + (0,)
    path.write_text(
        "VSVersionInfo(ffi=FixedFileInfo(filevers=" + repr(number) + ", prodvers=" + repr(number) +
        ", mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)), "
        "kids=[StringFileInfo([StringTable('040904B0', ["
        "StringStruct('CompanyName', 'Zerozero05'), "
        "StringStruct('FileDescription', 'UI Center - Guides and Components'), "
        f"StringStruct('FileVersion', {version!r}), StringStruct('ProductVersion', {version!r}), "
        "StringStruct('InternalName', 'UI_Center'), StringStruct('OriginalFilename', 'UI_Center.exe'), "
        "StringStruct('ProductName', 'UI Center'), "
        "StringStruct('LegalCopyright', 'Copyright 2026 Zerozero05; AGPL-3.0-only')])]), "
        "VarFileInfo([VarStruct('Translation', [1033, 1200])])])\n", encoding="utf-8"
    )


def binary_inventory(bundle, licenses, notices):
    """Inventory actual shipped native files, not all installed pip packages."""
    result = []
    snapshots = license_snapshots()
    required = {"CPython-additional-licenses.rst"}
    distribution_native = {path.name.lower() for parent in (Path(sys.base_prefix), Path(sys.base_prefix) / "DLLs")
                           for path in parent.glob("*") if path.suffix.lower() in {".dll", ".pyd"}}
    for path in sorted((bundle / "_internal").rglob("*")):
        if path.is_file() and path.suffix.lower() in {".dll", ".pyd"}:
            if windows_system_runtime(path.name):
                raise ValueError("Windows-provided UCRT/API-set library unexpectedly entered the bundle: " + path.name)
            provider, distribution_notices = native_notices(path.name)
            if path.name.lower() not in distribution_native and not provider.startswith("Microsoft runtime"):
                raise ValueError("A native library is outside the supported CPython distribution: " + path.name)
            if path.name.lower() in {"_sqlite3.pyd", "sqlite3.dll"}:
                raise ValueError("SQLite was unexpectedly collected; review its runtime use and notices first")
            required.update(name for name in distribution_notices if name in snapshots)
            result.append({"path": path.relative_to(bundle / "_internal").as_posix(),
                           "sha256": sha256(path.read_bytes()),
                           "distribution_notices": distribution_notices, "provider": provider})
    if not any(Path(entry["path"]).name.lower().startswith("python") for entry in result):
        raise ValueError("The onedir output is missing the Python runtime")
    if not any(Path(entry["path"]).name.lower().startswith("tcl") for entry in result):
        raise ValueError("The onedir output is missing the Tcl runtime")
    if not any(Path(entry["path"]).name.lower().startswith("tk") for entry in result):
        raise ValueError("The onedir output is missing the Tk runtime")
    for name in sorted(required):
        source = ROOT / "packaging/licenses" / name
        shutil.copyfile(source, licenses / name)
        notices.append(dict(snapshots[name]))
    write_json(licenses / "manifest.json", {"files": notices})
    return {"binaries": result, "license_files": notices,
            "note": "Unmodified distribution/upstream license notices accompany only the actual collected binary families. "
                    "License snapshot tags identify notice sources, not the installed binary versions. "
                    "Application source uses AGPL-3.0-only."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        help="Build destination; defaults to work/v<VERSION>/desktop-dist")
    parser.add_argument("--version")
    parser.add_argument("--source-commit")
    parser.add_argument("--check-only", action="store_true", help="Read inputs only; no installs, build or writes")
    args = parser.parse_args()
    version = version_value(args.version)
    names = check_inputs(version)
    commit = source_commit(args.source_commit)
    if args.check_only:
        print(json.dumps({"status": "inputs_valid", "version": version, "commit": commit,
                          "allowlisted_assets": len(names), "pyinstaller_required": PYINSTALLER_VERSION,
                          "wrote_files": False}))
        return 0
    if sys.platform != "win32" or struct.calcsize("P") != 8 or platform.machine().upper() not in {"AMD64", "X86_64"}:
        raise ValueError("Build both assets on Windows x64 with a 64-bit Python")
    if importlib.metadata.version("pyinstaller") != PYINSTALLER_VERSION:
        raise ValueError("Install the pinned requirements-desktop-build.txt in the build environment first")
    check_committed_sources(commit)
    output = (args.output_dir or ROOT / "work" / ("v" + version) / "desktop-dist").resolve()
    portable_name, single_name = asset_filenames(version)
    for filename in (portable_name, single_name, "build-desktop-report.json"):
        if (output / filename).exists():
            raise ValueError("Refusing to overwrite an existing build artifact: " + filename)
    output.mkdir(parents=True, exist_ok=True)
    work = output / ("build-" + version + "-" + str(time.time_ns()))
    assets = work / "stage/assets"
    assets.mkdir(parents=True)
    for name in names:
        target = assets / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    licenses = assets / "licenses"
    licenses.mkdir()
    notices = collect_licenses(licenses)
    build_info = {"version": version, "commit": commit,
                  "source_url": "https://github.com/Zerozero05/UI_Center/tree/" + commit,
                  "python": platform.python_version(), "pyinstaller": PYINSTALLER_VERSION,
                  "toolchain": {"python": platform.python_version(), "pyinstaller": PYINSTALLER_VERSION,
                                "platform": "Windows_x64"}}
    write_json(assets / "build-info.json", build_info)
    version_file = work / "windows-version.txt"
    windows_version_file(version_file, version)
    build_environment = os.environ.copy()
    build_environment["PYINSTALLER_CONFIG_DIR"] = str(work / "pyinstaller-config")
    build_environment.update({"UI_CENTER_BUILD_ROOT": str(ROOT), "UI_CENTER_BUILD_ASSETS": str(assets),
                              "UI_CENTER_WINDOWS_VERSION_FILE": str(version_file)})
    policies = {}
    def run_build(mode):
        destination = work / (mode + "-dist")
        policy_report = work / (mode + "-native-policy.json")
        build_environment.update({"UI_CENTER_BUILD_MODE": mode, "UI_CENTER_NATIVE_POLICY_REPORT": str(policy_report)})
        subprocess.run([sys.executable, "-m", "PyInstaller", "--distpath", str(destination), "--workpath",
                       str(work / (mode + "-work")), str(ROOT / "packaging/desktop.spec")],
                       cwd=ROOT, env=build_environment, check=True)
        policies[mode] = json.loads(policy_report.read_text(encoding="utf-8"))
        return destination
    portable = run_build("onedir") / "UI_Center"
    inventory = binary_inventory(portable, licenses, notices)
    write_json(licenses / "binaries.json", inventory)
    for path in licenses.iterdir():
        shutil.copyfile(path, portable / "_internal/assets/licenses" / path.name)
    single = run_build("onefile") / "UI_Center.exe"
    if policies["onedir"] != policies["onefile"]:
        raise ValueError("Portable and single-file native-library policies differ")
    shutil.copyfile(single, output / single_name)
    with zipfile.ZipFile(output / portable_name, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(portable.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(portable).as_posix())
    report = {"status": "built_not_runtime_tested", **build_info, "licenses": notices,
              "windows_native_policy": policies["onedir"],
              "artifacts": [{"name": name, "bytes": (output / name).stat().st_size,
                             "sha256": sha256((output / name).read_bytes())}
                            for name in (portable_name, single_name)]}
    write_json(output / "build-desktop-report.json", report)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError, importlib.metadata.PackageNotFoundError) as error:
        print("Desktop build failed: " + str(error), file=sys.stderr)
        raise SystemExit(1)

"""Shared, standard-library-only desktop packaging contracts.

SPDX-License-Identifier: AGPL-3.0-only
"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PYINSTALLER_VERSION = "6.22.3"
ROOT_DATA = (
    "README.md", "AGENTS.md", "VALIDATION.md", "LICENSE",
    "THIRD_PARTY_NOTICES.md", "CHANGELOG.md", "VERSION",
)
EXAMPLE_DATA = (
    "examples/tkinter/README.md", "examples/android/README.md",
)
ICON_DATA = "apps/desktop/app.ico"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def asset_names(root=ROOT):
    """An allowlist, never an archive of the working directory."""
    names = set(ROOT_DATA + EXAMPLE_DATA + ("references/sources.md", "tokens/README.md", ICON_DATA))
    for pattern in ("docs/**/*.md", "components/*/README.md", "tokens/*.json"):
        names.update(path.relative_to(root).as_posix() for path in root.glob(pattern) if path.is_file())
    return sorted(names)


def version_value(value=None, root=ROOT):
    recorded = (root / "VERSION").read_text(encoding="utf-8-sig").strip()
    version = value or recorded
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or version != recorded:
        raise ValueError("--version must match the three-part version in VERSION")
    return version


def source_commit(value=None, root=ROOT):
    commit = value or os.environ.get("UI_CENTER_SOURCE_COMMIT") or os.environ.get("GITHUB_SHA")
    if not commit:
        commit = subprocess.check_output(
            ["git", "--no-optional-locks", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
        raise ValueError("The source commit must be a full 40-character Git SHA")
    return commit.lower()


def git_bytes(commit, name, root=ROOT):
    return subprocess.check_output(["git", "--no-optional-locks", "show", f"{commit}:{name}"], cwd=root)


def check_inputs(version, root=ROOT):
    version_value(version, root)
    required = ["apps/desktop/main.py", "components/tkinter/ui_center/__init__.py", *asset_names(root)]
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise ValueError("Missing packaging inputs: " + ", ".join(missing))
    if (root / "requirements-desktop-build.txt").read_text(encoding="utf-8").count(
            f"PyInstaller=={PYINSTALLER_VERSION}") != 1:
        raise ValueError("The desktop build requirement must pin PyInstaller " + PYINSTALLER_VERSION)
    license_snapshots(root)
    return asset_names(root)


def license_snapshots(root=ROOT):
    entries = json.loads((root / "packaging/licenses/sources.json").read_text(encoding="utf-8"))["files"]
    for entry in entries:
        if Path(entry["path"]).name != entry["path"]:
            raise ValueError("License snapshots must use a filename without directories")
        if sha256((root / "packaging/licenses" / entry["path"]).read_bytes()) != entry["sha256"]:
            raise ValueError("Changed upstream license snapshot: " + entry["path"])
    return {entry["path"]: entry for entry in entries}


def check_committed_sources(commit, root=ROOT):
    """Refuse to label modified or newly untracked app/build inputs with an old SHA."""
    tracked = subprocess.check_output(
        ["git", "--no-optional-locks", "ls-tree", "-r", "--name-only", commit], cwd=root, text=True
    ).splitlines()
    relevant = set(asset_names(root))
    for folder, suffix in (("apps/desktop", ".py"), ("components/tkinter/ui_center", ".py"),
                           ("packaging", ".py")):
        relevant.update(path.relative_to(root).as_posix() for path in (root / folder).rglob("*" + suffix))
    relevant.update(("scripts/build_desktop.py", "scripts/verify_desktop_package.py",
                     "requirements-desktop-build.txt", "examples/tkinter/demo.py",
                     "packaging/README.md", "packaging/licenses/sources.json"))
    relevant.update("packaging/licenses/" + name for name in license_snapshots(root))
    for name in sorted(relevant):
        if name not in tracked or (root / name).read_bytes() != git_bytes(commit, name, root):
            raise ValueError("Packaging input differs from the declared source commit: " + name)


def asset_filenames(version):
    return (f"UI_Center_v{version}_Windows_x64_Portable.zip",
            f"UI_Center_v{version}_Windows_x64.exe")


def native_notices(name):
    """License families for the standard Windows CPython distribution only."""
    name = Path(name).name.lower()
    notices = ["Python-LICENSE.txt", "CPython-additional-licenses.rst"]
    provider = "CPython Windows distribution"
    if name.startswith(("tcl", "tk")) or name == "_tkinter.pyd":
        notices.append("TclTk-distribution-LICENSE.txt")
        provider = "Tcl/Tk and CPython's _tkinter binding"
    elif name.startswith(("vcruntime", "msvcp", "ucrtbase", "api-ms-win-crt", "concrt")):
        provider = "Microsoft runtime; CPython Windows redistributable conditions"
    elif name.startswith(("libcrypto", "libssl")) or name in {"_hashlib.pyd", "_ssl.pyd"}:
        notices.append("OpenSSL-3-LICENSE.txt")
        provider = "OpenSSL 3 and CPython bindings"
    elif name.startswith("libffi") or name == "_ctypes.pyd":
        notices.append("libffi-LICENSE.txt")
        provider = "libffi and CPython's _ctypes binding"
    elif name.startswith("zlib") or name.startswith("python"):
        # zlib is built into the standard Windows python DLL.
        notices.append("zlib-LICENSE.txt")
    elif name.startswith("libexpat") or name == "pyexpat.pyd":
        notices.append("Expat-COPYING.txt")
        provider = "Expat and CPython's pyexpat binding"
    elif name.startswith("liblzma") or name == "_lzma.pyd":
        notices.append("liblzma-COPYING.txt")
        provider = "XZ Utils liblzma and CPython's _lzma binding"
    return provider, notices


def safe_member(name):
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if normalized.startswith("/") or ":" in normalized or ".." in path.parts:
        raise ValueError("Unsafe archive member: " + name)
    if any(part.lower() in {".git", "work", "outputs", ".gradle", "__pycache__"}
           for part in path.parts):
        raise ValueError("Private or development directory in package: " + name)
    if path.suffix.lower() in {".apk", ".aab", ".jks", ".keystore", ".pfx", ".p12", ".pem", ".key", ".log"}:
        raise ValueError("Private/build material in package: " + name)
    return normalized


def check_windows_executable(data):
    """Check AMD64/PE32+ and the GUI subsystem, independently of filename."""
    if data[:2] != b"MZ" or len(data) < 64:
        raise ValueError("Not a Windows executable")
    offset = struct.unpack_from("<I", data, 60)[0]
    if offset + 94 > len(data) or data[offset:offset + 4] != b"PE\0\0":
        raise ValueError("Invalid PE header")
    if struct.unpack_from("<H", data, offset + 4)[0] != 0x8664:
        raise ValueError("The desktop executable is not Windows x64")
    if struct.unpack_from("<H", data, offset + 24)[0] != 0x20B:
        raise ValueError("The desktop executable is not PE32+")
    if struct.unpack_from("<H", data, offset + 24 + 68)[0] != 2:
        raise ValueError("The desktop executable must use the windowed GUI subsystem")

# SPDX-License-Identifier: AGPL-3.0-only
"""Build both modes with the same explicit Windows 11 native-library policy."""
import json
import os
from pathlib import Path
import sys

source_root = Path(os.environ["UI_CENTER_BUILD_ROOT"])
sys.path.insert(0, str(source_root / "packaging"))
from desktop_common import windows_system_runtime

mode = os.environ["UI_CENTER_BUILD_MODE"]
if mode not in {"onedir", "onefile"}:
    raise ValueError("Unsupported UI Center build mode")

a = Analysis(
    [str(source_root / "apps/desktop/main.py")],
    pathex=[str(source_root), str(source_root / "apps/desktop"), str(source_root / "components/tkinter")],
    binaries=[], datas=[(os.environ["UI_CENTER_BUILD_ASSETS"], "assets")],
    hiddenimports=["examples.tkinter.demo", "ui_center"],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False, optimize=0,
)

# PyInstaller 6.22.3 explicitly collects these for older Windows compatibility.
# Windows 11 supplies the UCRT and resolves API-set contracts through the OS.
# Filter before EXE/COLLECT; do not edit built bundles or allow arbitrary DLLs.
system_dlls = sorted({name for name, source, kind in a.binaries if windows_system_runtime(name)})
a.binaries = [(name, source, kind) for name, source, kind in a.binaries if not windows_system_runtime(name)]
Path(os.environ["UI_CENTER_NATIVE_POLICY_REPORT"]).write_text(json.dumps({
    "minimum_supported_windows": "Windows 11 x64",
    "excluded_system_dlls": system_dlls,
    "reason": "Windows-provided UCRT/API-set compatibility forwarders; VC runtime libraries remain bundled.",
}, indent=2) + "\n", encoding="utf-8")
print("Windows 11 system-provided DLLs excluded: " + ", ".join(system_dlls))

pyz = PYZ(a.pure)
options = dict(
    name="UI_Center", debug=False, bootloader_ignore_signals=False, strip=False,
    upx=False, console=False, disable_windowed_traceback=False,
    version=os.environ["UI_CENTER_WINDOWS_VERSION_FILE"],
    icon=str(source_root / "apps/desktop/app.ico"),
)
if mode == "onedir":
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **options)
    bundle = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="UI_Center")
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], **options)

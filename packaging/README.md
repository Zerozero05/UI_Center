# Windows desktop packaging

The app uses Python/Tk and standard-library modules. `requirements-desktop-build.txt`
pins **PyInstaller 6.22.3 as a build tool**; the build script never installs it.
Build on Windows x64 with the complete CPython Windows distribution (including
its Python, Windows runtime, and bundled Tcl/Tk license notices).

```console
python scripts/build_desktop.py --check-only --version 1.1.0
python scripts/build_desktop.py --output-dir work/desktop-dist --version 1.1.0
python scripts/verify_desktop_package.py --portable-zip work/desktop-dist/UI_Center_v1.1.0_Windows_x64_Portable.zip --single-exe work/desktop-dist/UI_Center_v1.1.0_Windows_x64.exe --version 1.1.0 --source-commit FULL_GIT_SHA --report work/desktop-dist/package-verification.json
```

The first command is read-only and does not require PyInstaller. A real build
requires all application/build inputs to match the declared Git commit. The
commit comes from `--source-commit`, `UI_CENTER_SOURCE_COMMIT`, `GITHUB_SHA`, or
the local Git HEAD, in that order. Existing output assets are never overwritten.

The portable ZIP has `UI_Center.exe` and `_internal/` at its root. The standalone
EXE contains the same assets and extracts them using PyInstaller's normal
one-file mechanism. Resources live beside the frozen entry point in `assets/`.
Only the allowlisted public documents, shared tokens, example documentation,
app icon, original AGPL/source notices, and generated build/license
metadata enter that directory; the working directory is never archived.
The shared Tk demo is imported as a compiled module, with no loose `.py` source
file added to either runtime asset. Its build input still has to match Git.

`assets/build-info.json` records `version`, full `commit`, source URL and toolchain
versions. `assets/licenses/` preserves the installed CPython distribution notices
(including its Tcl/Tk and Windows runtime terms), PyInstaller's complete installed
license/bootloader exception, and an inventory of the actual shipped DLL/PYD files.
The standard-library native files are checked against the building CPython
distribution; extra native libraries require an explicit review. The inventory
maps each file to its notices. Microsoft VC/UCRT files use the unmodified Windows
redistributable conditions in the installed Python license. OpenSSL 3, libffi,
Expat and liblzma notices are included when those native families are collected;
zlib and CPython's additional notices cover code incorporated into the Python DLL.
No local installation paths are recorded in that inventory. The app's About
page reads these same packaged notices.

The unmodified upstream notice snapshots and their source URLs/SHA-256 values
live in [licenses/sources.json](licenses/sources.json). Their tags identify the
notice text's provenance, not the installed binary versions. They come from
[CPython 3.12.14](https://github.com/python/cpython/tree/v3.12.14),
[OpenSSL 3.0.16](https://github.com/openssl/openssl/blob/openssl-3.0.16/LICENSE.txt),
[libffi 3.4.4](https://github.com/libffi/libffi/blob/v3.4.4/LICENSE),
[zlib 1.3.1](https://github.com/madler/zlib/blob/v1.3.1/LICENSE), and
[XZ Utils 5.2.5](https://github.com/tukaani-project/xz/blob/v5.2.5/COPYING).
These are license texts, not imported library source or additional app dependencies.
The build does not modify CPython or these native libraries.

Outputs also include `build-desktop-report.json`. Build intermediates are kept in
a uniquely named directory under `--output-dir`; no cleanup is performed.
The verifier checks both archives' metadata/resources against Git and checks the
actual native-file inventory, Windows x64/GUI PE headers, license presence/hashes,
and forbidden private/build paths. It does **not** start the app or claim GUI
acceptance. CI must run each app's separate `--smoke-test REPORT_JSON` contract.

Implementation references: [PyInstaller usage](https://pyinstaller.org/en/stable/usage.html),
[data files](https://pyinstaller.org/en/stable/spec-files.html#adding-data-files),
and [entry-point-relative resources](https://pyinstaller.org/en/stable/runtime-information.html#using-file).
These are tool/API references; no upstream packaging implementation was copied.

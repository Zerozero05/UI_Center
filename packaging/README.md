# Windows desktop packaging

The app uses Python/Tk and standard-library modules. `requirements-desktop-build.txt`
pins **PyInstaller 6.22.3 as a build tool**; the build script never installs it.
Build on Windows x64 with the complete CPython Windows distribution (including
its Python, Windows runtime, and bundled Tcl/Tk license notices).
The supported runtime target is **Windows 11 x64**.

The v1.2.2 candidate improves skeleton/shimmer previews and linked filters.
It keeps the existing component APIs, profile format, directory layout, license
collection and pinned build toolchain.
Source inputs resolve relative to the repository root, so moving the complete
source checkout does not require replacing it with a machine-specific path.

```console
python scripts/build_desktop.py --check-only --version 1.2.2
python scripts/build_desktop.py --output-dir work/v1.2.2/desktop-dist --version 1.2.2
python scripts/verify_desktop_package.py --portable-zip work/v1.2.2/desktop-dist/UI_Center_v1.2.2_Windows_x64_Portable.zip --single-exe work/v1.2.2/desktop-dist/UI_Center_v1.2.2_Windows_x64.exe --version 1.2.2 --source-commit FULL_GIT_SHA --report work/v1.2.2/desktop-dist/package-verification.json
```

The first command is read-only and does not require PyInstaller. A real build
requires all application/build inputs to match the declared Git commit. The
commit comes from `--source-commit`, `UI_CENTER_SOURCE_COMMIT`, `GITHUB_SHA`, or
the local Git HEAD, in that order. Existing output assets are never overwritten.
Without `--output-dir`, builds use `work/v<VERSION>/desktop-dist` under the
source root. v1.2.2 CI keeps its runtime, smoke, release and failure evidence
under `work/v1.2.2`, separate from prior versions. Both successful runtime
artifacts and failed-build diagnostics are retained by Actions for seven days.

The portable ZIP has `UI_Center.exe` and `_internal/` at its root. The standalone
EXE contains the same assets and extracts them using PyInstaller's normal
one-file mechanism. Resources live beside the frozen entry point in `assets/`.
Only the allowlisted public documents, shared tokens, example documentation,
app icon, original AGPL/source notices, and generated build/license
metadata enter that directory; the working directory is never archived.
Updated path/usage documents and the in-app help are built from those same
committed application/resource inputs; local preferences, the protected private
directory and development caches are not runtime resource inputs.
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
The fixed [desktop.spec](desktop.spec) removes only `ucrtbase.dll` and versioned
`api-ms-win-core-*-lN-N-N.dll` / `api-ms-win-crt-*-lN-N-N.dll` compatibility copies
from the analyzed binary list before either bundle is assembled. Windows 11
supplies these components. The actual removed names are recorded in
`build-desktop-report.json` under `windows_native_policy.excluded_system_dlls`;
both build forms must report the same policy. VC runtime DLLs stay bundled and
unknown native libraries still fail the distribution/license check.

This follows [PyInstaller 6.22.3's explicit legacy UCRT collection policy](https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/PyInstaller/depend/dylib.py#L130-L139)
and [Microsoft's Windows 10/11 UCRT deployment guidance](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment?view=msvc-170#local-deployment).
Microsoft also documents that [API-set names are operating-system contracts](https://learn.microsoft.com/en-us/windows/win32/apiindex/windows-apisets),
resolved by the loader, rather than application libraries to supply.
The verifier checks both archives' metadata/resources against Git and checks the
actual native-file inventory, Windows x64/GUI PE headers, license presence/hashes,
and forbidden private/build paths. It does **not** start the app or claim GUI
acceptance. CI must run each app's separate `--smoke-test REPORT_JSON` contract.
CI retains both original reports and `smoke-relocated-portable.json` /
`smoke-relocated-single.json` after moving the complete extracted directory;
all four must use the actual executable's `data/preferences.json`, and relocated
reports must retain the original `sage` / `125` / `reduced` profile values.
Default-profile write probes require a child-only `UI_CENTER_SMOKE_SANDBOX`
and an executable strictly inside it; ordinary smoke invocations do not write
the default profile.

Implementation references: [PyInstaller usage](https://pyinstaller.org/en/stable/usage.html),
[data files](https://pyinstaller.org/en/stable/spec-files.html#adding-data-files),
and [entry-point-relative resources](https://pyinstaller.org/en/stable/runtime-information.html#using-file).
These are tool/API references; no upstream packaging implementation was copied.

Publication is restricted to `refs/tags/v1.2.2` in the release workflow. Updating
the version or building a candidate does not create that tag or publish a release;
the user must first approve this version's concrete candidate and attachments.
Older tags and published assets remain unchanged.

For a reviewed v1.2.2 release, the annotated tag contains one `Candidate-Run: N`
line naming the successful same-commit CI run, and `Portable-SHA256:` /
`Single-SHA256:` lines binding the exact reviewed binary hashes. The release job
requires an actual annotated tag, checks the downloaded bytes and that run's
commit and conclusion, downloads its exact artifact, and binds integrity/smoke
evidence to the bytes before publishing. A fresh tag build is a regression gate,
not permission to substitute different binaries for the reviewed candidate.

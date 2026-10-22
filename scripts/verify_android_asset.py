"""Verify the built Android app actually ships the canonical design tokens."""
from pathlib import Path
import argparse
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk', nargs='?', type=Path,
                        default=ROOT / 'examples/android/app/build/outputs/apk/debug/app-debug.apk')
    args = parser.parse_args()
    source = (ROOT / 'tokens/design-tokens.json').read_bytes()
    with zipfile.ZipFile(args.apk) as archive:
        packaged = archive.read('assets/design-tokens.json')
    if packaged != source:
        raise SystemExit('FAIL: APK design tokens differ from the canonical JSON')
    print('PASS: APK contains byte-identical canonical design tokens')
    print('Token SHA256:', hashlib.sha256(source).hexdigest())
    print('APK SHA256:', hashlib.sha256(args.apk.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()

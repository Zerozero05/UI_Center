"""Generate our original panel icon with the Python standard library only.

Run explicitly when editing artwork; the application never runs this writer.
SPDX-License-Identifier: AGPL-3.0-only
"""

import argparse
import binascii
from pathlib import Path
import struct
import zlib

LAYERS = (
    (1, 1, 63, 63, 13, "#155eef"),
    (9, 11, 55, 53, 5, "#ffffff"),
    (12, 14, 52, 20, 2, "#e4ebf5"),
    (12, 24, 22, 49, 2, "#bdc7d4"),
    (26, 24, 51, 34, 2, "#155eef"),
    (26, 38, 36, 49, 2, "#e4ebf5"),
    (40, 38, 51, 49, 2, "#e4ebf5"),
)


def inside(x, y, layer):
    left, top, right, bottom, radius, _color = layer
    if not (left <= x <= right and top <= y <= bottom):
        return False
    center_x = max(left + radius, min(x, right - radius))
    center_y = max(top + radius, min(y, bottom - radius))
    return (x - center_x) ** 2 + (y - center_y) ** 2 <= radius ** 2


def png(size):
    raw = bytearray()
    colors = [tuple(bytes.fromhex(layer[-1][1:])) for layer in LAYERS]
    for row in range(size):
        raw.append(0)
        for col in range(size):
            samples = []
            for dy in range(4):
                for dx in range(4):
                    x, y = (col + (dx + .5) / 4) * 64 / size, (row + (dy + .5) / 4) * 64 / size
                    color = None
                    for layer, rgb in zip(LAYERS, colors):
                        if inside(x, y, layer):
                            color = rgb
                    if color is not None:
                        samples.append(color)
            if samples:
                raw.extend(round(sum(c[i] for c in samples) / len(samples)) for i in range(3))
                raw.append(round(255 * len(samples) / 16))
            else:
                raw.extend((0, 0, 0, 0))

    def chunk(kind, content):
        return (struct.pack(">I", len(content)) + kind + content +
                struct.pack(">I", binascii.crc32(kind + content) & 0xffffffff))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def generate(directory, preview=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    sizes = (16, 24, 32, 48, 64, 128, 256)
    images = [png(size) for size in sizes]
    offset = 6 + 16 * len(sizes)
    entries = bytearray()
    for size, content in zip(sizes, images):
        entries.extend(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(content), offset))
        offset += len(content)
    (directory / "app.ico").write_bytes(struct.pack("<HHH", 0, 1, len(sizes)) + entries + b"".join(images))
    rectangles = [f'  <rect x="{l}" y="{t}" width="{r-l}" height="{b-t}" rx="{radius}" fill="{color}"/>'
                  for l, t, r, b, radius, color in LAYERS]
    (directory / "app.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">\n' +
                                        "\n".join(rectangles) + "\n</svg>\n", encoding="utf-8")
    if preview is not None:
        target = Path(preview)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(images[-1])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate UI_Center's original panel icon")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    generate(args.output_dir, args.preview)

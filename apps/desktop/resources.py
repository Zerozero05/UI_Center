"""Read original repository documents from source or a frozen assets mirror."""

import json
from pathlib import Path
import re

REPOSITORY_URL = "https://github.com/Zerozero05/UI_Center"
REQUIRED_RESOURCES = (
    "VERSION", "LICENSE", "THIRD_PARTY_NOTICES.md", "VALIDATION.md",
    "docs/design-guide.md", "docs/patterns.md", "docs/cases.md", "docs/consumption.md",
    "docs/components/loading.md", "docs/components/overlays.md", "docs/components/navigation-feedback.md",
    "components/tkinter/README.md", "components/android/README.md",
    "examples/tkinter/README.md", "examples/android/README.md",
    "tokens/README.md", "tokens/design-tokens.json", "references/sources.md",
    "apps/desktop/app.ico",
)


def section_text(text, heading=None):
    if heading is None:
        return text
    lines = text.splitlines()
    start, end, in_code = None, len(lines), False
    for index, line in enumerate(lines):
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if start is None and line == "## " + heading:
            start = index
        elif start is not None and re.match(r"^#{1,2} ", line):
            end = index
            break
    if start is None:
        raise ValueError("原文缺少章节：" + heading)
    return "\n".join(lines[start:end]) + "\n"


def first_code_block(text, language):
    blocks = re.findall(r"^```([^\n]*)\n(.*?)^```\s*$", text, flags=re.M | re.S)
    return next((body.rstrip() + "\n" for kind, body in blocks if kind.strip() == language), "")


class ResourceStore:
    def __init__(self, root, *, frozen=False):
        self.root = Path(root).resolve()
        self.frozen = frozen
        missing = [name for name in REQUIRED_RESOURCES if not (self.root / name).is_file()]
        if missing:
            raise FileNotFoundError("资料不完整，请重新解压完整程序包。缺少：" + ", ".join(missing))
        self.version = self.read("VERSION").strip()
        if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", self.version):
            raise ValueError("VERSION 不是有效的程序版本。")
        if frozen:
            information = json.loads(self.read("build-info.json"))
            if information.get("version") != self.version:
                raise ValueError("程序的版本信息与随附资料不一致。")
            self.commit = information.get("commit", "")
            if not re.fullmatch(r"[0-9a-f]{40}", self.commit):
                raise ValueError("程序缺少可核对的完整源码提交。")
        else:
            self.commit = self._source_commit()

    @classmethod
    def from_entry(cls, entry_file, *, frozen=False):
        entry = Path(entry_file).resolve()
        return cls(entry.parent / "assets" if frozen else entry.parents[2], frozen=frozen)

    def read(self, relative_path):
        candidate = (self.root / relative_path).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("资料路径超出随附内容范围。")
        return candidate.read_text(encoding="utf-8-sig")

    @property
    def tokens_path(self):
        return self.root / "tokens" / "design-tokens.json"

    def _source_commit(self):
        git_dir = self.root / ".git"
        if not git_dir.is_dir():
            return ""
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref: "):
            reference = head[5:]
            ref_file = git_dir / reference
            if ref_file.is_file():
                head = ref_file.read_text(encoding="utf-8").strip()
            elif (git_dir / "packed-refs").is_file():
                head = next((line.split(" ", 1)[0] for line in
                             (git_dir / "packed-refs").read_text(encoding="utf-8").splitlines()
                             if line.endswith(" " + reference)), "")
            else:
                head = ""
        return head if re.fullmatch(r"[0-9a-f]{40}", head) else ""

    def github_url(self, relative_path):
        if not self.commit:
            return ""
        from urllib.parse import quote
        return f"{REPOSITORY_URL}/blob/{self.commit}/{quote(relative_path, safe='/')}"

    def license_text(self):
        parts = [self.read("LICENSE"), self.read("THIRD_PARTY_NOTICES.md")]
        folder = self.root / "licenses"
        if folder.is_dir():
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    parts.append("\n# " + path.relative_to(folder).as_posix() + "\n\n" +
                                 path.read_text(encoding="utf-8-sig"))
        elif not self.frozen:
            parts.append("\n源码运行说明：当前未通过本程序分发运行库。正式程序包将随附实际 Python、Tcl/Tk 等运行库的许可。")
        return "\n\n".join(parts)

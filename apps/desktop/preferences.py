"""Only appearance preferences, stored independently of the replaceable runtime."""
from pathlib import Path
import ctypes
import json
import os
import sys
import tempfile


def program_directory():
    """Locate the installed executable or the source repository, never the cwd."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def default_preferences_path():
    """Keep installed data beside the program and source data in ignored work."""
    directory = program_directory()
    if not getattr(sys, "frozen", False):
        directory = directory / "work"
    return directory / "data" / "preferences.json"


# Compatibility for callers importing the original constant. New instances
# resolve dynamically so frozen/source execution and explicit paths stay separate.
DEFAULT_PATH = default_preferences_path()
DEFAULTS = {"theme": "warm", "font_scale": 100, "motion": "system"}
THEMES = {"暖纸护眼": "warm", "灰绿护眼": "sage", "浅色": "light", "深色": "dark"}
MOTIONS = {"跟随系统": "system", "正常动画": "normal", "减少动画": "reduced"}


class Preferences:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else default_preferences_path()
        self.notice = ""

    def load(self):
        values = dict(DEFAULTS)
        try:
            if not self.path.exists():
                return values
            recorded = json.loads(self.path.read_text(encoding="utf-8-sig"))
            if not isinstance(recorded, dict):
                raise ValueError("设置不是对象")
            if (recorded.get("theme") not in THEMES.values()
                    or recorded.get("font_scale") not in (100, 125, 150)
                    or recorded.get("motion") not in MOTIONS.values()):
                raise ValueError("设置值不受支持")
            values.update({name: recorded[name] for name in DEFAULTS})
            values["font_scale"] = int(values["font_scale"])
        except (OSError, ValueError):
            self.notice = "界面偏好无法读取，已使用默认设置；你仍可正常使用并重新选择。"
        return values

    def save(self, values):
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix="preferences-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump({name: values[name] for name in DEFAULTS}, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            os.replace(temporary, self.path)
            self.notice = ""
            return True
        except OSError:
            self.notice = "无法保存界面偏好，本次选择仍有效；下次启动可能使用旧设置。"
            return False
        finally:
            # This is this transaction's own temporary file, never user input.
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass  # A failed cleanup must not hide the save error.


def reduced_motion(mode):
    if mode != "system":
        return mode == "reduced"
    if os.name == "nt":
        enabled = ctypes.c_int(1)
        if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0):
            return not bool(enabled.value)
    return False

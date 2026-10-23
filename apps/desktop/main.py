"""Launch UI_Center. --smoke-test REPORT verifies real source/frozen controls."""

import argparse
from pathlib import Path
import sys
import tkinter as tk
from tkinter import messagebox

if not getattr(sys, "frozen", False):
    source_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(source_root))
    sys.path.insert(0, str(source_root / "components" / "tkinter"))

from apps.desktop.app import BrowserApp
from apps.desktop.resources import ResourceStore
from apps.desktop.smoke import run_smoke, write_report


def main(argv=None):
    parser = argparse.ArgumentParser(description="UI_Center 离线规范与组件浏览器")
    parser.add_argument("--smoke-test", metavar="REPORT.json", help="创建真实控件、验证交互并写出报告后退出")
    arguments = parser.parse_args(argv)
    root = None
    try:
        store = ResourceStore.from_entry(__file__, frozen=bool(getattr(sys, "frozen", False)))
        root = tk.Tk()
        preferences_path = (Path(arguments.smoke_test).resolve().parent / "preferences-smoke.json"
                            if arguments.smoke_test else None)
        app = BrowserApp(root, store, preferences_path=preferences_path)
        if arguments.smoke_test:
            return run_smoke(app, arguments.smoke_test)

        def show_callback_error(_kind, error, _traceback):
            messagebox.showerror("UI_Center · 操作未完成", str(error), parent=root)

        root.report_callback_exception = show_callback_error
        root.mainloop()
        return 0
    except Exception as error:
        if arguments.smoke_test:
            write_report(arguments.smoke_test, {"status": "failed", "version": "未知",
                         "commit": "开发源码", "frozen": bool(getattr(sys, "frozen", False)),
                         "checks": [], "error": f"{type(error).__name__}: {error}"})
        else:
            messagebox.showerror("UI_Center 无法启动", "请确认解压了完整程序包。\n\n" + str(error), parent=root)
        if root is not None:
            try:
                root.destroy()
            except tk.TclError:
                pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

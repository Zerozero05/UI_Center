"""Runtime acceptance inside the actual source/frozen entry, without tests/."""

import hashlib
import json
from pathlib import Path
import time
import _tkinter

from .catalog import ENTRIES
from .resources import REQUIRED_RESOURCES


def write_report(path, report):
    destination = Path(path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_smoke(app, report_path):
    report = {"status": "failed", "version": app.store.version,
              "commit": app.store.commit or "开发源码", "frozen": app.store.frozen, "checks": []}

    def check(name, condition):
        report["checks"].append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    try:
        root = app.root
        callback_errors = []
        root.report_callback_exception = lambda _kind, error, _trace: callback_errors.append(str(error))
        root.update()
        report["resources"] = [{"path": name, "sha256": hashlib.sha256((app.store.root / name).read_bytes()).hexdigest()}
                               for name in REQUIRED_RESOURCES]
        check("offline_original_resources", len(report["resources"]) == len(REQUIRED_RESOURCES))
        check("real_browser_widgets", len(app.entries.get_children()) == len(ENTRIES) and app.description.text.winfo_exists())
        app.query.set("取消")
        check("title_summary_search", "pattern-tasks" in app.entries.get_children())
        app.query.set("不会存在的匹配字符串XYZ")
        check("empty_search_results", app.current is None and app.copy_ai_button.instate(["disabled"]))
        app.select_entry("android-theme")
        check("android_reference_boundary", "未设备实测" in app.boundary.cget("text") and app.preview_button.instate(["disabled"]))
        app.select_entry("tk-task")
        app.copy_usage()
        check("copy_original_usage", "from ui_center import" in root.clipboard_get())
        app.copy_ai()
        check("copy_adoption_with_provenance", (app.store.commit or "开发源码") in root.clipboard_get())
        preview = app.open_preview()
        check("single_live_preview", preview is not None and app.open_preview() is preview)
        root.update()
        check("preview_bottom_controls_visible", all(widget.winfo_ismapped() and
              widget.winfo_rooty() + widget.winfo_height() <= preview.root.winfo_rooty() + preview.root.winfo_height()
              for widget in (preview.panel.detail_entry, preview.footer)))
        preview.project.set("自动验证：保留输入")
        preview.amount.set("20")
        preview.interval_ms = 20
        preview.actions.primary.invoke()
        app.theme.set("dark")
        root.update_idletasks()
        check("shared_theme_and_input", preview.theme.get() == "dark" and preview.project.get() == "自动验证：保留输入" and preview.busy)
        check("readonly_dark_document", str(app.description.text.cget("state")) == "disabled" and
              app.description.text.cget("background") == app.tokens["themes"]["dark"]["surface"])
        preview.actions.cancel.invoke()
        deadline = time.monotonic() + 3
        while preview.panel.task_state != "cancelled" and time.monotonic() < deadline:
            root.tk.dooneevent(_tkinter.DONT_WAIT)
            time.sleep(.002)
        check("preview_cancel", preview.panel.task_state == "cancelled")
        app.theme.set("light")
        check("light_theme_restores_without_reset", preview.project.get() == "自动验证：保留输入" and preview.panel.task_state == "cancelled")
        app.root.geometry("820x600")
        root.update()
        check("small_window_actions_visible", app.copy_ai_button.winfo_ismapped() and app.preview_button.winfo_rooty() < root.winfo_rooty() + root.winfo_height())
        report["callback_errors"] = callback_errors
        check("no_tk_callback_errors", not callback_errors)
        report["status"] = "passed"
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        app.close()
        write_report(report_path, report)
    return 0 if report["status"] == "passed" else 1

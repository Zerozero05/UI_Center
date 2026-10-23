"""Runtime acceptance inside the actual source/frozen entry, without tests/."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import _tkinter

from .catalog import CORE_COMPONENTS, body_for, usage_for
from .resources import REQUIRED_RESOURCES
from .preferences import Preferences, default_preferences_path, program_directory


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
        program = program_directory()
        default_path = default_preferences_path()
        active_path = app.preferences.path.resolve()
        expected_program = Path(sys.executable).resolve().parent if app.store.frozen else app.store.root
        expected_default = expected_program / ("data" if app.store.frozen else "work/data") / "preferences.json"
        report["locations"] = {"program_directory": str(program),
                               "default_preferences_file": str(default_path),
                               "active_preferences_file": str(active_path)}
        check("program_directory_uses_actual_entry", program == expected_program)
        check("default_preferences_stay_in_project", default_path == expected_default)
        check("smoke_keeps_explicit_preferences", active_path == Path(report_path).resolve().parent / "preferences-smoke.json")
        sandbox = os.environ.get("UI_CENTER_SMOKE_SANDBOX")
        if app.store.frozen and sandbox:
            sandbox_root = Path(sandbox).resolve()
            check("default_probe_is_inside_explicit_sandbox", program != sandbox_root
                  and program.is_relative_to(sandbox_root) and default_path.is_relative_to(sandbox_root))
            profile = Preferences()
            report["default_profile_before"] = profile.load()
            probe_values = {"theme": "sage", "font_scale": 125, "motion": "reduced"}
            check("default_preferences_write", profile.save(probe_values))
            report["default_profile_after"] = Preferences().load()
            check("default_preferences_restart_read", report["default_profile_after"] == probe_values)
            check("default_preferences_only_three_fields", set(json.loads(default_path.read_text(encoding="utf-8")))
                  == set(probe_values))
        app.show_help()
        root.update()
        check("help_shows_actual_locations", app.help_program_path.get() == str(program)
              and app.help_settings_path.get() == str(active_path))
        check("help_paths_are_readonly", str(app.help_program_entry.cget("state")) == "readonly"
              and str(app.help_settings_entry.cget("state")) == "readonly")
        app.help_close_button.invoke()
        root.update()
        report["resources"] = [{"path": name, "sha256": hashlib.sha256((app.store.root / name).read_bytes()).hexdigest()}
                               for name in REQUIRED_RESOURCES]
        check("offline_original_resources", len(report["resources"]) == len(REQUIRED_RESOURCES))
        check("real_browser_widgets", "spinner" in app.entries.get_children() and app.description.text.winfo_exists())
        app.query.set("shummer")
        check("english_alias_search", app.entries.get_children() == ("shimmer",))
        app.query.set("不会存在的匹配字符串XYZ")
        check("empty_search_results", app.current is None and app.copy_ai_button.instate(["disabled"]))
        app.select_entry("pattern-tasks")
        check("guidelines_have_one_document", len(app.tabs.tabs()) == 1 and app.preview_button.instate(["disabled"]))
        app.select_entry("android-theme")
        check("android_reference_boundary", "未设备实测" in app.boundary.cget("text") and app.preview_button.instate(["disabled"]))
        app.select_entry("tk-task")
        app.copy_usage()
        check("copy_exact_original_usage", root.clipboard_get() == usage_for(app.store, app.current))
        app.copy_ai()
        check("copy_adoption_with_provenance", (app.store.commit or "开发源码") in root.clipboard_get())
        app.live_view.start()
        app.live_view.cancel()
        deadline = time.monotonic() + 3
        while app.live_view.panel.task_state != "cancelled" and time.monotonic() < deadline:
            root.tk.dooneevent(_tkinter.DONT_WAIT)
            time.sleep(.002)
        check("legacy_task_cancel", app.live_view.panel.task_state == "cancelled")
        for key, *_rest in CORE_COMPONENTS:
            app.select_entry(key)
            root.update()
            view = app.live_view
            code = app.current_code()
            ast.parse(code)
            if key in ("dialog", "confirm-dialog", "drawer", "popover", "tooltip"):
                view.trigger.invoke()
                root.update()
                view.overlay.close()
            elif key in ("spinner", "progress-bar", "circular-progress", "skeleton", "shimmer", "loading-button", "page-loader"):
                view.start_button.invoke()
                root.update()
                view.stop()
            elif key == "tabs":
                view.widget.select("settings")
            elif key == "accordion":
                view.widget.toggle("help")
            elif key == "segmented-control":
                view.widget.select("day")
            elif key == "toast":
                view._show_toast()
                view.widget.hide()
            view.reset()
            root.update()
            check("component_" + key, view.winfo_exists() and len(app.tabs.tabs()) == 3
                  and code.strip() != body_for(app.store, app.current).strip())
        app.select_entry("page-loader")
        view = app.live_view
        view.input_text.set("切换后保留输入")
        for mode in ("warm", "sage", "light", "dark"):
            for size in (100, 125, 150):
                app.theme.set(mode)
                app.font_scale.set(size)
                root.update_idletasks()
                check("appearance_" + mode + "_" + str(size), view.input_text.get() == "切换后保留输入"
                      and app.description.text.cget("background") == app.tokens["themes"][mode]["surface"])
        app.motion.set("reduced")
        check("reduced_motion", app.motion_reduced and view.reduced_motion)
        app.select_entry("spinner")
        preview = app.open_preview()
        check("single_component_window", preview is not None and app.open_preview() is preview)
        preview.close()
        root.update()
        check("standalone_close_preserves_workbench", app.preview is None and root.winfo_exists())
        app.root.geometry("820x600")
        root.update()
        check("small_window_actions_visible", all(widget.winfo_ismapped() and
              widget.winfo_rooty() + widget.winfo_height() <= root.winfo_rooty() + root.winfo_height()
              for widget in (app.copy_ai_button, app.copy_usage_button, app.preview_button, app.source_button)))
        report["callback_errors"] = callback_errors
        check("no_tk_callback_errors", not callback_errors)
        report["status"] = "passed"
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        app.close()
        write_report(report_path, report)
    return 0 if report["status"] == "passed" else 1

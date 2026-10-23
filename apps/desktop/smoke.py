"""Runtime acceptance inside the actual source/frozen entry, without tests/."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import _tkinter

from .catalog import CORE_COMPONENTS, body_for
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

    def descendants(widget):
        yield widget
        for child in widget.winfo_children():
            yield from descendants(child)

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
                  and program.is_relative_to(sandbox_root) and default_path.resolve().is_relative_to(sandbox_root))
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
        scene_choices = tuple(app.scene_picker.cget("values"))
        app.query.set("不会存在的匹配字符串XYZ")
        check("empty_search_results", app.current is None and app.copy_ai_button.instate(["disabled"]))
        root.update()
        check("empty_results_have_recovery_not_document_tabs", app.empty_state.winfo_ismapped()
              and not app.tabs.winfo_ismapped() and not app.entry_actions.winfo_ismapped()
              and app.empty_state.action.cget("text") == "显示本类全部")
        check("keywords_do_not_change_filter_choices", tuple(app.scene_picker.cget("values")) == scene_choices)
        app.empty_state.action.invoke()
        check("empty_recovery_preserves_category", app.section.get() == "组件库" and app.query.get() == ""
              and app.platform.get() == "全部平台" and app.scene.get() == "全部场景"
              and app.current is not None)
        check("component_choices_exclude_impossible_combinations", "通用" not in app.platform_picker.cget("values")
              and "复用与来源" not in app.scene_picker.cget("values"))
        app.scene.set("加载组件")
        app.platform.set("Android")
        check("platform_change_resets_only_invalid_scene", app.platform.get() == "Android"
              and app.scene.get() == "全部场景" and len(app.entries.get_children()) == 3
              and "加载组件" not in app.scene_picker.cget("values"))
        app.section.set("资料与来源")
        app.scene.set("复用与来源")
        app.query.set("借鉴来源")
        check("references_remain_in_their_category", app.entries.get_children() == ("sources",))
        app.clear_search()
        check("clear_keyword_keeps_filters", app.query.get() == "" and app.section.get() == "资料与来源"
              and app.platform.get() == "Android" and app.scene.get() == "复用与来源"
              and len(app.entries.get_children()) == 5)
        app.query.set("不会存在的匹配字符串XYZ")
        app.empty_state.action.invoke()
        check("reference_empty_recovery_stays_in_category", app.section.get() == "资料与来源"
              and app.query.get() == "" and app.platform.get() == "全部平台"
              and app.scene.get() == "全部场景" and len(app.entries.get_children()) == 6)
        app.select_entry("pattern-tasks")
        check("guidelines_have_one_document", len(app.tabs.tabs()) == 1 and app.preview_button.instate(["disabled"]))
        app.select_entry("android-theme")
        check("android_reference_boundary", "未设备实测" in app.boundary.cget("text") and app.preview_button.instate(["disabled"]))
        app.select_entry("tk-task")
        app.copy_usage()
        check("copy_exact_current_parameter_usage", root.clipboard_get() == app.live_view.code())
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
            children = list(descendants(view))
            resets = [w for w in children if w.winfo_class() in ("TButton", "Button")
                      and w.winfo_ismapped() and "重置" in str(w.cget("text"))]
            check(key + "_unified_text_parameters_and_single_reset",
                  not any(w.winfo_class() in ("TCheckbutton", "Checkbutton") for w in children)
                  and all(not int(w.cget("indicatoron")) for w in children if w.winfo_class() == "Radiobutton")
                  and len(resets) == 1
                  and all(field.winfo_x() + field.winfo_width() <= view.form.winfo_width() + 1
                          for field in view.form._groups))
            if key == "inline-alert":
                check("inline_alert_short_content_is_compact", int(view.widget.body.cget("height")) == 1
                      and not view.widget.scrollbar.winfo_ismapped())
                view.long_text.set(True)
                view._update_alert()
                root.update()
                check("inline_alert_long_content_remains_scrollable", int(view.widget.body.cget("height")) == 4
                      and view.widget.scrollbar.winfo_ismapped())
            if key in ("skeleton", "shimmer"):
                app.motion.set("normal")
                view.reset()
                root.update()
                check(key + "_chinese_effect_controls", tuple(b.cget("text") for b in view.layout_choice.buttons.values()) == ("列表", "卡片")
                      and tuple(b.cget("text") for b in view.effect_choice.buttons.values()) == ("开启", "关闭")
                      and view.effect_choice.enabled)
                view.layout_choice.select("card")
                view.effect_choice.select(False)
                argument = "animate" if key == "skeleton" else "enabled"
                check(key + "_chinese_choices_keep_original_api", view.setting.get() == "card"
                      and view.widget.variant == "card" and not view.enabled.get()
                      and "variant='card'" in view.code() and argument + "=False" in view.code()
                      and view.widget._after_id is None and "效果已关闭" in view.message.get())
                app.motion.set("reduced")
                check(key + "_reduced_motion_keeps_local_choice", not view.enabled.get()
                      and view.effect_choice.select() is False and not view.effect_choice.enabled
                      and view.widget._after_id is None and "减少动画" in view.message.get())
                view.stop()
                app.motion.set("normal")
                check(key + "_motion_restore_does_not_restart_stopped", not view.widget.running
                      and view.widget._after_id is None and "已停止" in view.message.get())
                view.reset()
                canvas = view.widget.canvas
                first = canvas.find_withtag("placeholder")[0]
                original_color = canvas.itemcget(first, "fill")
                deadline = time.monotonic() + 2
                changed = False
                while time.monotonic() < deadline:
                    root.tk.dooneevent(_tkinter.DONT_WAIT)
                    changed = (canvas.itemcget(canvas.find_withtag("placeholder")[0], "fill") != original_color if key == "skeleton"
                               else bool(canvas.find_withtag("shimmer")))
                    if changed:
                        break
                    time.sleep(.002)
                check(key + "_actual_timer_renders_effect", changed and view.widget._after_id is not None)
                if key == "shimmer":
                    check("shimmer_keeps_stable_base", all(canvas.itemcget(item, "fill") == view.palette["hover"]
                          for item in canvas.find_withtag("placeholder")))
                    clipped = True
                    for item in canvas.find_withtag("shimmer"):
                        tag = next(tag for tag in canvas.gettags(item) if tag.startswith("clip-"))
                        base = canvas.find_withtag("placeholder")[int(tag[5:])]
                        x0, y0, x1, y1 = canvas.coords(base)
                        points = canvas.coords(item)
                        if canvas.type(base) == "oval":
                            cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
                            clipped &= all(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1 + 1e-7
                                           for x, y in zip(points[::2], points[1::2]))
                        else:
                            a, top, b, bottom = points
                            clipped &= x0 <= a <= b <= x1 and y0 <= top <= bottom <= y1
                    check("shimmer_highlights_stay_in_occupied_shapes", clipped)
        app.select_entry("shimmer")
        view = app.live_view
        view.enabled.set(False)
        view._parameters()
        independent = app.open_preview()
        independent.view.stop()
        app.motion.set("reduced")
        app.motion.set("normal")
        check("loading_windows_keep_independent_parameters", not view.enabled.get() and view.widget.running
              and independent.view.enabled.get() and not independent.view.widget.running
              and view.widget._after_id is None and independent.view.widget._after_id is None
              and "已停止" in independent.view.message.get())
        independent.close()
        root.update()
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
        report["small_window"] = {"width": root.winfo_width(), "height": root.winfo_height(),
            "actions": [{"text": widget.cget("text"), "mapped": bool(widget.winfo_ismapped()),
                         "bottom": widget.winfo_rooty() + widget.winfo_height() - root.winfo_rooty()}
                        for widget in (app.copy_ai_button, app.copy_usage_button, app.preview_button, app.source_button)]}
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

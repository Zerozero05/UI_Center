"""Run exact catalog examples against copied sources, with no app dependency.

Requires a real Tk desktop. Evidence remains under work/component-consumption.
"""

import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Catalog/resource reads do not import the desktop app, preview or DemoWindow.
from apps.desktop.catalog import CORE_COMPONENTS, ENTRIES, usage_for
from apps.desktop.resources import ResourceStore


def _consumer_script(example, key):
    """Keep the example intact except for replacing its blocking main loop."""
    tree = ast.parse(example, filename=key)
    loops = [node for node in tree.body if isinstance(node, ast.Expr)
             and isinstance(node.value, ast.Call)
             and isinstance(node.value.func, ast.Attribute)
             and isinstance(node.value.func.value, ast.Name)
             and node.value.func.value.id == "root"
             and node.value.func.attr == "mainloop"]
    if len(loops) != 1 or loops[0].value.args or loops[0].value.keywords:
        raise ValueError(key + " must contain exactly one top-level root.mainloop()")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            imports = [node.module or ""]
        else:
            continue
        if any(name.split(".")[0] in ("apps", "examples") for name in imports):
            raise ValueError(key + " imports repository application code")

    prelude = textwrap.dedent("""\
        from pathlib import Path as _ConsumerPath
        import sys as _consumer_sys
        import traceback as _consumer_traceback
        import tkinter as _consumer_tk
        import ui_center as _consumer_ui

        _consumer_base = _ConsumerPath(__file__).resolve().parent
        assert _ConsumerPath(_consumer_ui.__file__).resolve().is_relative_to(_consumer_base)
        _consumer_errors = []
        def _consumer_callback_error(kind, value, trace):
            _consumer_errors.append(''.join(_consumer_traceback.format_exception(kind, value, trace)))
        _consumer_tk.Tk.report_callback_exception = staticmethod(_consumer_callback_error)
    """) + "\n"
    shutdown = textwrap.dedent("""\
        root.update()
        assert not _consumer_errors, _consumer_errors
        for _consumer_name, _consumer_module in tuple(_consumer_sys.modules.items()):
            if _consumer_name == 'ui_center' or _consumer_name.startswith('ui_center.'):
                assert _ConsumerPath(_consumer_module.__file__).resolve().is_relative_to(_consumer_base), _consumer_name
        assert not any(name == 'apps' or name.startswith('apps.') or name == 'examples'
                       or name.startswith('examples.') for name in _consumer_sys.modules)
        assert not any(name.split('.')[0] in ('fitz', 'pypdf', 'pdfplumber', 'pypdfium2',
                                             'paddleocr', 'pytesseract')
                       for name in _consumer_sys.modules)
        root.update_idletasks()
        root.destroy()
        assert not root.tk.splitlist(root.tk.call('after', 'info')), 'Unreleased Tk callbacks'
        assert not _consumer_errors, _consumer_errors
    """).rstrip()
    lines = example.splitlines(keepends=True)
    loop = loops[0]
    start = sum(map(len, lines[:loop.lineno - 1])) + loop.col_offset
    end = sum(map(len, lines[:loop.end_lineno - 1])) + loop.end_col_offset
    return prelude + example[:start] + shutdown + example[end:] + "\nprint(" + repr("UI_CENTER_COPY_OK " + key) + ")\n"


class IndependentComponentConsumptionTests(unittest.TestCase):
    def test_exact_examples_use_only_copied_ui_center_and_tokens(self):
        keys = tuple(row[0] for row in CORE_COMPONENTS) + ("tk-theme", "tk-actions", "tk-task")
        self.assertEqual(len(CORE_COMPONENTS), 18)
        self.assertEqual(len(set(keys)), 21)
        entries = {entry.key: entry for entry in ENTRIES}
        store = ResourceStore(ROOT)
        evidence_parent = ROOT / "work" / "component-consumption"
        evidence_parent.mkdir(parents=True, exist_ok=True)
        destination = Path(tempfile.mkdtemp(prefix="copy-", dir=evidence_parent))
        # mkdtemp reserves a fresh directory atomically; it is deliberately not
        # a TemporaryDirectory, because failed consumers must remain reviewable.
        shutil.copytree(ROOT / "components" / "tkinter" / "ui_center", destination / "ui_center",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        (destination / "tokens").mkdir()
        shutil.copy2(ROOT / "tokens" / "design-tokens.json", destination / "tokens" / "design-tokens.json")
        package_manifest = {path.relative_to(destination).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                            for folder in (destination / "ui_center", destination / "tokens")
                            for path in sorted(folder.rglob("*")) if path.is_file()}
        self.assertTrue(package_manifest)
        self.assertFalse(any("__pycache__" in name or name.endswith((".pyc", ".pyo"))
                             for name in package_manifest))
        (destination / "package-manifest.json").write_text(
            json.dumps(package_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        environment = {name: value for name, value in os.environ.items()
                       if not name.upper().startswith("PYTHON")}
        records = []
        print("Independent component consumer evidence:", destination, flush=True)
        for key in keys:
            with self.subTest(component=key, evidence=str(destination)):
                entry = entries[key]
                self.assertEqual(entry.platform, "Tkinter")
                self.assertEqual(entry.language, "python")
                example = usage_for(store, entry)
                self.assertTrue(example.strip())
                (destination / (key + ".example.py")).write_text(example, encoding="utf-8")
                consumer = destination / (key + ".consumer.py")
                consumer.write_text(_consumer_script(example, key), encoding="utf-8")
                command = [sys.executable, "-B", "-E", "-s", "-X", "utf8", str(consumer)]
                started = time.monotonic()
                try:
                    completed = subprocess.run(command, cwd=destination, env=environment,
                                               capture_output=True, timeout=30)
                    stdout, stderr = completed.stdout, completed.stderr
                    outcome = {"returncode": completed.returncode, "timeout": False}
                except subprocess.TimeoutExpired as error:
                    stdout, stderr = error.stdout or b"", error.stderr or b""
                    outcome = {"returncode": None, "timeout": True}
                (destination / (key + ".stdout.txt")).write_bytes(stdout)
                (destination / (key + ".stderr.txt")).write_bytes(stderr)
                record = {"key": key, "resource": entry.resource, "usage_key": entry.usage_key,
                          "example_sha256": hashlib.sha256(example.encode("utf-8")).hexdigest(),
                          "command": command, "seconds": round(time.monotonic() - started, 3), **outcome}
                records.append(record)
                # Write after every child, including failure/timeout, so an
                # interrupted run still leaves the exact scripts and evidence.
                (destination / "results.json").write_text(
                    json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                detail = ("Evidence: " + str(destination) + "\n" +
                          stdout.decode("utf-8", errors="replace") + stderr.decode("utf-8", errors="replace"))
                self.assertFalse(outcome["timeout"], detail)
                self.assertEqual(outcome["returncode"], 0, detail)
                self.assertIn(("UI_CENTER_COPY_OK " + key).encode("ascii"), stdout, detail)


if __name__ == "__main__":
    unittest.main()

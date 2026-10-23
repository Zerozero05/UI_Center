"""Small, read-only Tk text renderer; original Markdown remains the source."""

from pathlib import PurePosixPath
import re
import tkinter as tk
from tkinter import font as tkfont, ttk
from urllib.parse import urlsplit
import webbrowser
from .scrolling import AutoScrollbar


class DocumentReader(ttk.Frame):
    def __init__(self, master, *, store, horizontal=False):
        super().__init__(master)
        self.store = store
        self.text = tk.Text(self, wrap="none" if horizontal else "word", borderwidth=0,
                            takefocus=True, state="disabled", cursor="xterm", undo=False)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.vertical = bar = AutoScrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=bar.set)
        bar.grid(row=0, column=1, sticky="ns")
        if horizontal:
            self.horizontal = horizontal_bar = AutoScrollbar(self, orient="horizontal", command=self.text.xview)
            self.text.configure(xscrollcommand=horizontal_bar.set)
            horizontal_bar.grid(row=1, column=0, sticky="ew")
        self.text.grid(row=0, column=0, sticky="nsew")
        self._links = []

    def apply_palette(self, palette, tokens, *, font_scale=1.0):
        text = self.text
        gap = tokens["spacing"]
        text.configure(background=palette["surface"], foreground=palette["foreground"],
                       insertbackground=palette["foreground"],
                       selectbackground=palette["selected_background"],
                       selectforeground=palette["selected_foreground"],
                       inactiveselectbackground=palette["selected_background"],
                       highlightbackground=palette["surface"], highlightcolor=palette["focus"],
                       highlightthickness=1, padx=gap["lg"], pady=gap["md"])
        family = tkfont.nametofont("TkDefaultFont", root=text).actual("family")
        size = max(1, round(tokens["typography"]["body"]["tk_points"] * font_scale))
        text.configure(font=(family, size))
        text.tag_configure("heading", font=(family, round(tokens["typography"]["heading"]["tk_points"] * font_scale), "bold"),
                           spacing1=gap["md"], spacing3=gap["sm"])
        text.tag_configure("bold", font=(family, size, "bold"))
        text.tag_configure("code", font="TkFixedFont", background=palette["hover"], lmargin1=gap["md"], lmargin2=gap["md"],
                           spacing1=max(1, gap["xs"] // 2), spacing3=max(1, gap["xs"] // 2))
        text.tag_configure("link", foreground=palette["accent"], underline=True)
        text.tag_configure("body", spacing3=gap["xs"], spacing2=2)

    def _target(self, target, resource):
        if urlsplit(target).scheme in ("https", "http"):
            return target
        path, _, fragment = target.partition("#")
        relative = PurePosixPath(resource).parent / path if path else PurePosixPath(resource)
        # Resolve relative components without reading anything outside assets.
        resolved = (self.store.root / str(relative)).resolve()
        if not resolved.is_relative_to(self.store.root):
            return ""
        url = self.store.github_url(resolved.relative_to(self.store.root).as_posix())
        return url + ("#" + fragment if fragment and url else "")

    def show(self, content, *, resource="README.md", markdown=True):
        text = self.text
        text.configure(state="normal")
        text.delete("1.0", "end")
        for tag in self._links:
            text.tag_delete(tag)
        self._links.clear()
        in_code = False
        for line in content.splitlines():
            if markdown and line.startswith("```"):
                in_code = not in_code
                text.insert("end", "\n")
                continue
            if in_code or not markdown:
                text.insert("end", line + "\n", "code")
                continue
            heading = re.match(r"^#{1,6}\s+(.*)", line)
            if heading:
                self._inline(heading[1], resource, "heading")
            elif not line.startswith("<a "):
                if line.startswith("- "):
                    line = "• " + line[2:]
                self._inline(line, resource, "body")
        text.configure(state="disabled")
        text.yview_moveto(0)

    def _inline(self, line, resource, base):
        pattern = r"\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*|`([^`]+)`"
        cursor = 0
        for match in re.finditer(pattern, line):
            self.text.insert("end", line[cursor:match.start()], base)
            if match[1] is not None:
                url = self._target(match[2], resource)
                if url:
                    tag = "url_" + str(len(self._links))
                    self._links.append(tag)
                    self.text.insert("end", match[1], (base, "link", tag))
                    self.text.tag_bind(tag, "<Button-1>", lambda _event, link=url: webbrowser.open(link))
                    self.text.tag_bind(tag, "<Enter>", lambda _event: self.text.configure(cursor="hand2"))
                    self.text.tag_bind(tag, "<Leave>", lambda _event: self.text.configure(cursor="xterm"))
                else:
                    self.text.insert("end", match[1], base)
            else:
                self.text.insert("end", match[3] or match[4], (base, "bold" if match[3] else "code"))
            cursor = match.end()
        self.text.insert("end", line[cursor:] + "\n", base)

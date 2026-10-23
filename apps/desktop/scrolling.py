"""Private overflow-aware scrolling for the desktop workbench.

SPDX-License-Identifier: AGPL-3.0-only
"""
from tkinter import ttk


class AutoScrollbar(ttk.Scrollbar):
    def set(self, first, last):
        start, end = float(first), float(last)
        needed = end > start and (start > 0.00001 or end < 0.99999)
        if needed:
            if self.winfo_manager() != "grid":
                self.grid()
        elif self.winfo_manager() == "grid":
            self.grid_remove()
        super().set(first, last)

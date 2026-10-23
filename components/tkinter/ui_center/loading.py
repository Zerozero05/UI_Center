"""State-only Tk loading components with bounded, optional decoration.

All methods run on the Tk UI thread. No component starts business work.
SPDX-License-Identifier: AGPL-3.0-only
"""

import math
import tkinter as tk
from tkinter import ttk


def _progress(value, maximum):
    value, maximum = float(value), float(maximum)
    if not math.isfinite(maximum) or maximum <= 0:
        raise ValueError("maximum must be finite and greater than zero")
    if not math.isfinite(value) or not 0 <= value <= maximum:
        raise ValueError("value must satisfy 0 <= value <= maximum")
    return value, maximum


def _mix_rgb(first, second, amount):
    return "#" + "".join(f"{round((a + (b - a) * amount) / 257):02x}"
                         for a, b in zip(first, second))


class _AnimatedFrame(ttk.Frame):
    """One timer per component; mapping and reduced motion suspend decoration."""

    def __init__(self, master, *, palette, interval_ms=50, reduced_motion=False, **kwargs):
        super().__init__(master, **kwargs)
        self.palette = dict(palette)
        self.interval_ms = max(34, int(interval_ms))
        self.reduced_motion = bool(reduced_motion)
        self._after_id = None
        self._running = False
        self._visible = True
        self._mapped = False
        self._disposed = False
        self._phase = 0
        self.bind("<Map>", self._map, add="+")
        self.bind("<Unmap>", self._unmap, add="+")
        self.bind("<Destroy>", self._destroy, add="+")

    @property
    def running(self):
        return self._running

    def _map(self, event):
        if event.widget is self:
            self._mapped = True
            self._sync_animation()

    def _unmap(self, event):
        if event.widget is self:
            self._mapped = False
            self._cancel_animation()

    def _destroy(self, event):
        if event.widget is self:
            self._disposed = True
            self._cancel_animation()

    def _cancel_animation(self):
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _animate_enabled(self):
        return True

    def _sync_animation(self):
        enabled = (self._running and self._visible and self._mapped
                   and not self._disposed and not self.reduced_motion
                   and self._animate_enabled())
        if not enabled:
            self._cancel_animation()
        elif self._after_id is None:
            self._after_id = self.after(self.interval_ms, self._tick)

    def _tick(self):
        self._after_id = None
        if self._disposed:
            return
        # A common multiple of the 48-step pulse and 40-step sweep keeps both
        # continuous when the bounded counter wraps.
        self._phase = (self._phase + 1) % 240
        self._draw()
        self._sync_animation()

    def start(self):
        self._running = True
        self._draw()
        self._sync_animation()

    def stop(self):
        self._running = False
        self._cancel_animation()
        self._draw()

    def apply_palette(self, palette):
        self.palette = dict(palette)
        self._draw()

    def set_visible(self, visible):
        self._visible = bool(visible)
        self._sync_animation()

    def set_reduced_motion(self, enabled):
        self.reduced_motion = bool(enabled)
        self._draw()
        self._sync_animation()

    def dispose(self):
        if not self._disposed:
            self.destroy()


class Spinner(_AnimatedFrame):
    """Unknown-duration indicator. start/stop never changes caller task state."""

    def __init__(self, master, *, palette, size=40, text="正在加载", **kwargs):
        super().__init__(master, palette=palette, **kwargs)
        self.size = max(16, int(size))
        self.text = str(text)
        self.canvas = tk.Canvas(self, width=self.size, height=self.size,
                                highlightthickness=0, takefocus=False)
        self.canvas.pack()
        self.caption = ttk.Label(self, text=self.text, wraplength=360, anchor="center")
        self.caption.pack(pady=(6, 0))
        self._draw()

    def set_text(self, text):
        self.text = str(text)
        self.caption.configure(text=self.text)

    def set_size(self, size):
        self.size = max(16, int(size))
        self.canvas.configure(width=self.size, height=self.size)
        self._draw()

    def _draw(self):
        p, size = self.palette, self.size
        self.canvas.configure(background=p["background"])
        self.canvas.delete("all")
        width = max(2, size / 10)
        bounds = (width, width, size - width, size - width)
        self.canvas.create_oval(*bounds, outline=p["border"], width=width)
        self.canvas.create_arc(*bounds, start=90 - self._phase * 12,
                               extent=100, style="arc", outline=p["accent"], width=width)


class ProgressBar(_AnimatedFrame):
    """Linear real progress or an explicitly unknown-duration segment."""

    def __init__(self, master, *, palette, value=0, maximum=100,
                 mode="determinate", length=320, **kwargs):
        self.value, self.maximum = _progress(value, maximum)
        if mode not in ("determinate", "indeterminate"):
            raise ValueError("mode must be determinate or indeterminate")
        super().__init__(master, palette=palette, **kwargs)
        self.mode = mode
        self.canvas = tk.Canvas(self, width=max(80, int(length)), height=18,
                                highlightthickness=0, takefocus=False)
        self.canvas.pack(fill="x")
        self.caption = ttk.Label(self, anchor="center")
        self.caption.pack(fill="x", pady=(6, 0))
        self.canvas.bind("<Configure>", lambda event: self._draw())
        self._draw()

    def set_progress(self, value, maximum=None):
        self.value, self.maximum = _progress(value, self.maximum if maximum is None else maximum)
        self._draw()

    def set_mode(self, mode):
        if mode not in ("determinate", "indeterminate"):
            raise ValueError("mode must be determinate or indeterminate")
        self.mode = mode
        self._draw()
        self._sync_animation()

    def _animate_enabled(self):
        return self.mode == "indeterminate"

    def _draw(self):
        p = self.palette
        width = self.canvas.winfo_width()
        if width <= 1:
            width = int(self.canvas.cget("width"))
        self.canvas.configure(background=p["background"])
        self.canvas.delete("all")
        self.canvas.create_rectangle(1, 1, width - 1, 17, fill=p["input_background"], outline=p["border"])
        if self.mode == "determinate":
            end = 2 + (width - 4) * self.value / self.maximum
            if self.value:
                self.canvas.create_rectangle(2, 2, end, 16, fill=p["accent"], outline="")
            self.caption.configure(text=f"{self.value / self.maximum:.0%}")
        else:
            fraction = 0.35 if self.reduced_motion else (self._phase % 40) / 40
            start = 2 + max(0, width - 4) * 0.7 * fraction
            self.canvas.create_rectangle(start, 2, start + (width - 4) * 0.3, 16,
                                         fill=p["accent"], outline="")
            self.caption.configure(text="进度未知 · 正在处理" if self.running else "进度未知")


class CircularProgress(_AnimatedFrame):
    """Circular real progress; it never estimates progress with a timer."""

    def __init__(self, master, *, palette, value=0, maximum=100, size=112, **kwargs):
        self.value, self.maximum = _progress(value, maximum)
        super().__init__(master, palette=palette, **kwargs)
        self.size = max(40, int(size))
        self.canvas = tk.Canvas(self, width=self.size, height=self.size,
                                highlightthickness=0, takefocus=False)
        self.canvas.pack()
        self._draw()

    def set_progress(self, value, maximum=None):
        self.value, self.maximum = _progress(value, self.maximum if maximum is None else maximum)
        self._draw()

    def set_size(self, size):
        self.size = max(40, int(size))
        self.canvas.configure(width=self.size, height=self.size)
        self._draw()

    def _animate_enabled(self):
        return False

    def _draw(self):
        p, size = self.palette, self.size
        self.canvas.configure(background=p["background"])
        self.canvas.delete("all")
        bounds = (7, 7, size - 7, size - 7)
        self.canvas.create_oval(*bounds, outline=p["border"], width=6)
        if self.value:
            if self.value == self.maximum:
                self.canvas.create_oval(*bounds, outline=p["accent"], width=6)
            else:
                self.canvas.create_arc(*bounds, start=90, extent=-360 * self.value / self.maximum,
                                       style="arc", outline=p["accent"], width=6)
        self.canvas.create_text(size / 2, size / 2, text=f"{self.value / self.maximum:.0%}",
                                fill=p["foreground"], font="TkDefaultFont")


class Skeleton(_AnimatedFrame):
    """List/card content placeholder; optional pulse is purely decorative."""

    def __init__(self, master, *, palette, variant="list", rows=3, width=360,
                 animate=True, **kwargs):
        if variant not in ("list", "card"):
            raise ValueError("variant must be list or card")
        if not 1 <= int(rows) <= 10:
            raise ValueError("rows must be between 1 and 10")
        super().__init__(master, palette=palette, **kwargs)
        self.variant, self.rows = variant, int(rows)
        self.animate = bool(animate)
        self.canvas = tk.Canvas(self, width=max(100, int(width)),
                                height=self.rows * 48 if variant == "list" else 168,
                                highlightthickness=0, takefocus=False)
        self.canvas.pack(fill="x", expand=True)
        self.caption = ttk.Label(self, text="内容正在加载", style="UIC.Muted.TLabel")
        self.caption.pack(pady=(8, 0))
        self.canvas.bind("<Configure>", lambda event: self._draw())
        self._draw()

    def set_variant(self, variant):
        if variant not in ("list", "card"):
            raise ValueError("variant must be list or card")
        self.variant = variant
        self.canvas.configure(height=self.rows * 48 if variant == "list" else 168)
        self._draw()

    def set_animation(self, enabled):
        self.animate = bool(enabled)
        self._draw()
        self._sync_animation()

    def _animate_enabled(self):
        return self.animate

    def _canvas_width(self):
        width = self.canvas.winfo_width()
        if width <= 1:
            width = int(self.canvas.cget("width"))
        return width

    def _placeholder_shapes(self, width):
        if self.variant == "card":
            return [("rectangle", (4, 4, width - 4, 100)),
                    ("rectangle", (4, 114, width * 0.78, 128)),
                    ("rectangle", (4, 142, width * 0.55, 154))]
        shapes = []
        for row in range(self.rows):
            y = row * 48 + 4
            shapes.extend((("oval", (4, y, 36, y + 32)),
                           ("rectangle", (48, y + 2, width - 4, y + 13)),
                           ("rectangle", (48, y + 22, width * 0.7, y + 31))))
        return shapes

    def _placeholder_color(self):
        p = self.palette
        if not (self.running and self.animate and not self.reduced_motion):
            return p["hover"]
        # One gentle cosine cycle takes 48 ticks, or 2.4s at the default 50ms.
        strength = 0.14 * (1 - math.cos(2 * math.pi * self._phase / 48))
        return _mix_rgb(self.winfo_rgb(p["hover"]), self.winfo_rgb(p["border"]), strength)

    def _draw(self):
        p = self.palette
        width = self._canvas_width()
        self.canvas.configure(background=p["background"])
        self.canvas.delete("all")
        color = self._placeholder_color()
        for index, (shape, bounds) in enumerate(self._placeholder_shapes(width)):
            draw = self.canvas.create_oval if shape == "oval" else self.canvas.create_rectangle
            draw(*bounds, fill=color, outline="", tags=("placeholder", f"shape-{index}"))


class Shimmer(Skeleton):
    """Skeleton with a moving highlight that can be disabled independently."""

    def __init__(self, master, *, palette, enabled=True, **kwargs):
        self.enabled = bool(enabled)
        super().__init__(master, palette=palette, animate=enabled, **kwargs)

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        self.set_animation(enabled)

    def _animate_enabled(self):
        return self.enabled and self.animate

    def _placeholder_color(self):
        return self.palette["hover"]

    def _draw(self):
        super()._draw()
        if not (self.enabled and self.animate and self.running and not self.reduced_motion):
            return
        width = self._canvas_width()
        half = max(24, min(80, width * 0.16))
        center = (self._phase % 40) / 40 * (width + 2 * half) - half
        base = self.winfo_rgb(self.palette["hover"])
        surface = self.winfo_rgb(self.palette["surface"])
        # The dark theme's surface is darker than its placeholder. Select the
        # lighter existing role so the sweep remains a highlight in every theme.
        highlight = surface if sum(surface) > sum(base) else self.winfo_rgb(self.palette["border"])
        shapes = self._placeholder_shapes(width)
        steps = 24
        for step in range(steps):
            left = center - half + 2 * half * step / steps
            right = center - half + 2 * half * (step + 1) / steps
            weight = 0.65 * math.sin(math.pi * (step + 0.5) / steps) ** 2
            color = _mix_rgb(base, highlight, weight)
            for index, (shape, bounds) in enumerate(shapes):
                x0, y0, x1, y1 = bounds
                a, b = max(left, x0), min(right, x1)
                if b <= a:
                    continue
                tags = ("shimmer", f"clip-{index}")
                if shape == "rectangle":
                    self.canvas.create_rectangle(a, y0, b, y1, fill=color, outline="", tags=tags)
                else:
                    # Inscribed chords clip each gradient strip to the circle;
                    # unlike a full-canvas stripe they cannot color empty space.
                    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                    rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
                    count = max(1, math.ceil((b - a) / 2))
                    xs = [a + (b - a) * point / count for point in range(count + 1)]
                    edge = lambda x: ry * math.sqrt(max(0, 1 - ((x - cx) / rx) ** 2))
                    points = [(x, cy - edge(x)) for x in xs]
                    points.extend((x, cy + edge(x)) for x in reversed(xs))
                    self.canvas.create_polygon(points, fill=color, outline="", tags=tags)


class LoadingButton(_AnimatedFrame):
    """A real ttk.Button; caller switches busy state and performs work."""

    def __init__(self, master, *, palette, text="开始处理", busy_text="正在处理",
                 command=None, **kwargs):
        super().__init__(master, palette=palette, **kwargs)
        self.text, self.busy_text = str(text), str(busy_text)
        self.command = command
        self.busy = False
        self.canvas = tk.Canvas(self, width=24, height=24, highlightthickness=0, takefocus=False)
        self.canvas.grid(row=0, column=0, padx=(0, 8))
        self.button = ttk.Button(self, text=self.text, command=self._invoke, style="UIC.Primary.TButton")
        self.button.grid(row=0, column=1)
        self._draw()

    def _invoke(self):
        if not self.busy and self.command is not None:
            self.command()

    def set_text(self, text, busy_text=None):
        self.text = str(text)
        if busy_text is not None:
            self.busy_text = str(busy_text)
        self._draw()

    def set_busy(self, busy=True):
        self.busy = bool(busy)
        self.button.state(["disabled"] if self.busy else ["!disabled"])
        if self.busy:
            super().start()
        else:
            super().stop()

    def start(self):
        self.set_busy(True)

    def stop(self):
        self.set_busy(False)

    def _draw(self):
        p = self.palette
        self.button.configure(text=self.busy_text if self.busy else self.text)
        self.canvas.configure(background=p["background"])
        self.canvas.delete("all")
        if self.busy:
            self.canvas.create_oval(4, 4, 20, 20, outline=p["border"], width=2)
            self.canvas.create_arc(4, 4, 20, 20, start=90 - self._phase * 12,
                                   extent=110, style="arc", outline=p["accent"], width=2)


class PageLoader(_AnimatedFrame):
    """Place an overlay inside its master only; never creates a Toplevel/grab."""

    def __init__(self, master, *, palette, text="正在加载页面", value=None,
                 maximum=100, on_cancel=None, **kwargs):
        if value is not None:
            value, maximum = _progress(value, maximum)
        else:
            _, maximum = _progress(0, maximum)
        super().__init__(master, palette=palette, padding=20, **kwargs)
        self.text, self.value, self.maximum = str(text), value, maximum
        self.on_cancel = on_cancel
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)
        self.canvas = tk.Canvas(self, width=48, height=48, highlightthickness=0, takefocus=False)
        self.canvas.grid(row=1, column=0)
        self.caption = ttk.Label(self, text=self.text, anchor="center", wraplength=380)
        self.caption.grid(row=2, column=0, sticky="ew", pady=(10, 4))
        self.progress_label = ttk.Label(self, anchor="center", style="UIC.Muted.TLabel")
        self.progress_label.grid(row=3, column=0, sticky="ew")
        self.cancel_button = None
        if on_cancel is not None:
            self.cancel_button = ttk.Button(self, text="取消", command=on_cancel)
            self.cancel_button.grid(row=4, column=0, pady=10)
        self.bind("<Configure>", lambda event: self.caption.configure(wraplength=max(80, event.width - 40)), add="+")
        self._draw()

    def set_text(self, text):
        self.text = str(text)
        self.caption.configure(text=self.text)

    def set_progress(self, value, maximum=None):
        maximum = self.maximum if maximum is None else maximum
        if value is None:
            _, self.maximum = _progress(0, maximum)
            self.value = None
        else:
            self.value, self.maximum = _progress(value, maximum)
        self._draw()

    def start(self):
        if self._visible:
            self.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.lift()
        super().start()

    def stop(self):
        super().stop()
        self.place_forget()

    def set_visible(self, visible):
        super().set_visible(visible)
        if not visible:
            self.place_forget()
        elif self.running:
            self.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.lift()

    def _draw(self):
        p = self.palette
        self.canvas.configure(background=p["background"])
        self.canvas.delete("all")
        self.canvas.create_oval(5, 5, 43, 43, outline=p["border"], width=4)
        self.canvas.create_arc(5, 5, 43, 43, start=90 - self._phase * 12,
                               extent=100, style="arc", outline=p["accent"], width=4)
        self.progress_label.configure(text="进度未知" if self.value is None else f"{self.value / self.maximum:.0%}")

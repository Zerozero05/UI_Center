"""Small native drawing primitives; no image files or third-party renderer.

SPDX-License-Identifier: AGPL-3.0-only
"""
import math
import tkinter as tk
from functools import lru_cache


def blend(first, second, amount):
    """Blend two #RRGGBB colors for decorative surfaces, never state text."""
    return "#" + "".join(f"{round(int(first[i:i+2], 16) * (1-amount) + int(second[i:i+2], 16) * amount):02x}"
                         for i in (1, 3, 5))


def state_icon(canvas, palette, kind, *, background=None):
    """Vector state marker; meaning is also supplied by the adjacent text."""
    role = kind if kind in ("success", "warning", "error") else "accent"
    ink = palette[role]
    canvas.configure(width=28, height=28, background=background or palette["surface"])
    canvas.delete("all")
    canvas.create_oval(1, 1, 27, 27, fill=blend(palette["surface"], ink, .12), outline="")
    if kind == "success":
        canvas.create_line(8, 14, 12, 18, 21, 9, fill=ink, width=2, capstyle="round", joinstyle="round")
    elif kind == "panel":
        canvas.create_rectangle(7, 7, 21, 21, outline=ink, width=2)
        canvas.create_line(16, 7, 16, 21, fill=ink, width=2)
    else:
        canvas.create_line(14, 8 if kind != "info" else 12, 14, 16 if kind != "info" else 21,
                           fill=ink, width=2, capstyle="round")
        y = 20 if kind != "info" else 8
        canvas.create_oval(13, y-1, 15, y+1, fill=ink, outline="")


def rounded_rect(canvas, bounds, radius, **options):
    x0, y0, x1, y1 = bounds
    r = min(radius, (x1-x0)/2, (y1-y0)/2)
    points = (x0+r, y0, x1-r, y0, x1, y0, x1, y0+r,
              x1, y1-r, x1, y1, x1-r, y1, x0+r, y1,
              x0, y1, x0, y1-r, x0, y0+r, x0, y0)
    return canvas.create_polygon(points, smooth=True, splinesteps=16, **options)


def ring(canvas, bounds, *, track, color, width, start, extent):
    """A quiet track and one rounded arc, with no extra timers."""
    canvas.create_oval(*bounds, outline=track, width=width)
    if extent == 0:
        return
    if abs(extent) >= 360:
        canvas.create_oval(*bounds, outline=color, width=width)
        return
    canvas.create_arc(*bounds, start=start, extent=extent, style="arc", outline=color, width=width)
    x0, y0, x1, y1 = bounds
    cx, cy, rx, ry = (x0+x1)/2, (y0+y1)/2, (x1-x0)/2, (y1-y0)/2
    r = width/2
    for angle in (start, start+extent):
        x, y = cx + rx*math.cos(math.radians(angle)), cy - ry*math.sin(math.radians(angle))
        canvas.create_oval(x-r, y-r, x+r, y+r, fill=color, outline="")


@lru_cache(maxsize=128)
def _button_pixels(size, fill, edge, canvas, radius, focus):
    """Antialiased 9-slice image. Reconfigure retained images on font changes."""
    thickness = 4 if focus else 1
    rows = []
    def inside(x, y, inset):
        near = max(radius, min(size-radius, x)), max(radius, min(size-radius, y))
        return (inset <= x <= size-inset and inset <= y <= size-inset
                and (x-near[0])**2 + (y-near[1])**2 <= (radius-inset)**2)
    for y in range(size):
        row = []
        for x in range(size):
            outer = gap = inner = 0
            for dx, dy in ((.25,.25), (.75,.25), (.25,.75), (.75,.75)):
                outer += inside(x+dx, y+dy, 0)
                if focus:
                    gap += inside(x+dx, y+dy, 2)
                inner += inside(x+dx, y+dy, thickness)
            color = blend(canvas, edge, outer/4)
            if focus:
                color = blend(color, canvas, gap/4)
            row.append(blend(color, fill, inner/4))
        rows.append("{" + " ".join(row) + "}")
    return " ".join(rows)


def _button_image(image, fill, edge, canvas, radius, *, focus=False):
    image.put(_button_pixels(image.width(), fill, edge, canvas, radius, focus))


def button_layouts(root, style, palette, radius):
    """Keep native ttk.Button bindings/focus, replace only its border artwork."""
    cache = getattr(root._root(), "_uic_button_images", None)
    if cache is None:
        cache = root._root()._uic_button_images = {}
    theme = style.theme_use()
    p = palette
    palettes = getattr(root._root(), "_uic_button_palettes", {})
    radius = max(2, int(radius))
    size = max(25, radius*2 + 3)
    refresh = palettes.get(theme) != (p, radius)
    for variant, style_name in (("Default", "TButton"), ("Primary", "UIC.Primary.TButton"),
                                ("Secondary", "UIC.Secondary.TButton"), ("Busy", "UIC.Busy.TButton"),
                                ("Nav", "UIC.Nav.TButton"), ("NavSelected", "UIC.NavSelected.TButton")):
        primary = variant == "Primary"
        fills = {"normal": p["accent"] if primary else p["surface"],
                 "active": p["accent_active"] if primary else p["hover"],
                 "pressed": p["accent_active"] if primary else p["hover"],
                 "disabled": p["background"]}
        if variant in ("Busy", "NavSelected"):
            fills = {state: p["accent_soft"] for state in fills}
        elif variant == "Nav":
            fills["normal"] = p["background"]
        images = {}
        for state in ("normal", "active", "pressed", "disabled", "focus", "focus_active", "focus_pressed"):
            key = theme, variant, radius, state
            if key not in cache:
                cache[key] = tk.PhotoImage(master=root, width=size, height=size)
            fill = fills.get(state.replace("focus_", ""), fills["normal"])
            edge = (p["focus"] if state.startswith("focus") else fill if variant != "Default"
                    else p["divider"])
            if refresh:
                _button_image(cache[key], fill, edge, p["background"], radius, focus=state.startswith("focus"))
            images[state] = cache[key]
        element = f"UIC.{variant}.r{radius}.border"
        if element not in style.element_names():
            style.element_create(element, "image", images["normal"],
                ("disabled", images["disabled"]), ("focus", "pressed", images["focus_pressed"]),
                ("focus", "active", images["focus_active"]), ("focus", images["focus"]),
                ("pressed", images["pressed"]), ("active", images["active"]),
                border=radius+1, padding=0, sticky="nswe")
        if style.layout(style_name)[0][0] != element:
            style.layout(style_name, [(element, {"sticky": "nswe", "children": [
                ("Button.padding", {"sticky": "nswe", "children": [("Button.label", {"sticky": "nswe"})]})]})])
    for name in ("UIC.Segmented.TFrame", "UIC.Accordion.TFrame"):
        element = f"UIC.Default.r{radius}.border"
        if style.layout(name)[0][0] != element:
            style.layout(name, [(element, {"sticky": "nswe"})])
    palettes[theme] = (dict(p), radius)
    root._root()._uic_button_palettes = palettes


def field_layouts(root, style, palette, radius):
    """Rounded native entry fields and scroll thumbs, with original bindings."""
    owner, p = root._root(), palette
    cache = getattr(owner, "_uic_field_images", {})
    palettes = getattr(owner, "_uic_field_palettes", {})
    theme = style.theme_use()
    radius = max(2, int(radius))
    size = max(25, 2*radius+3)
    refresh = palettes.get(theme) != (p, radius)
    fields = {}
    for state in ("normal", "focus", "disabled"):
        key = theme, radius, state
        if key not in cache:
            cache[key] = tk.PhotoImage(master=root, width=size, height=size)
        if refresh:
            _button_image(cache[key], p["background"] if state == "disabled" else p["input_background"],
                          p["focus"] if state == "focus" else p["border"], p["background"], radius,
                          focus=state == "focus")
        fields[state] = cache[key]
    for kind in ("Entry", "Combobox"):
        element = f"UIC.{kind}.r{radius}.field"
        if element not in style.element_names():
            style.element_create(element, "image", fields["normal"], ("disabled", fields["disabled"]),
                                 ("focus", fields["focus"]), border=radius+1, padding=0, sticky="nswe")
        children = [(kind+".padding", {"expand": "1", "sticky": "nswe", "children": [(kind+".textarea", {"sticky": "nswe"})]})]
        if kind == "Combobox":
            children.insert(0, ("Combobox.downarrow", {"side": "right", "sticky": "ns"}))
        if style.layout("T"+kind)[0][0] != element:
            style.layout("T"+kind, [(element, {"sticky": "nswe", "children": children})])
    for direction, dimensions, sticky in (("Vertical", (12, 28), "ns"), ("Horizontal", (28, 12), "ew")):
        for part in ("thumb", "active", "trough"):
            key = theme, direction, part
            if key not in cache:
                cache[key] = tk.PhotoImage(master=root, width=dimensions[0] if part != "trough" else 1,
                                          height=dimensions[1] if part != "trough" else 1)
            if refresh:
                if part == "trough":
                    cache[key].put(p["background"], to=(0,0,1,1))
                else:
                    # Draw the rounded thumb once; ttk stretches its middle.
                    w, h = dimensions
                    color = p["muted"] if part == "active" else p["border"]
                    rows = []
                    for y in range(h):
                        row = []
                        for x in range(w):
                            cx, cy = max(5, min(w-5, x+.5)), max(5, min(h-5, y+.5))
                            row.append(color if (x+.5-cx)**2+(y+.5-cy)**2 <= 25 else p["background"])
                        rows.append("{"+" ".join(row)+"}")
                    cache[key].put(" ".join(rows))
        trough, thumb = "UIC."+direction+".trough", "UIC."+direction+".thumb"
        if trough not in style.element_names():
            style.element_create(trough, "image", cache[(theme,direction,"trough")], sticky="nswe")
            style.element_create(thumb, "image", cache[(theme,direction,"thumb")],
                                 ("active", cache[(theme,direction,"active")]), border=5, padding=0, sticky="nswe")
        if style.layout(direction+".TScrollbar")[0][0] != trough:
            style.layout(direction+".TScrollbar", [(trough, {"sticky": sticky, "children": [(thumb, {"expand": "1", "sticky": "nswe"})]})])
    palettes[theme] = (dict(p), radius)
    owner._uic_field_images, owner._uic_field_palettes = cache, palettes

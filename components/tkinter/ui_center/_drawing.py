"""Small native drawing primitives; no image files or third-party renderer.

SPDX-License-Identifier: AGPL-3.0-only
"""
import math
import tkinter as tk


def blend(first, second, amount):
    """Blend two #RRGGBB colors for decorative surfaces, never state text."""
    return "#" + "".join(f"{round(int(first[i:i+2], 16) * (1-amount) + int(second[i:i+2], 16) * amount):02x}"
                         for i in (1, 3, 5))


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


def _button_image(image, fill, edge, canvas, radius, *, focus=False):
    """Antialiased 9-slice image. Reconfigure retained images on font changes."""
    size, thickness = image.width(), 4 if focus else 1
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
    image.put(" ".join(rows))


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
                                ("Secondary", "UIC.Secondary.TButton")):
        primary = variant == "Primary"
        fills = {"normal": p["accent"] if primary else p["surface"],
                 "active": p["accent_active"] if primary else p["hover"],
                 "pressed": p["accent_active"] if primary else p["hover"],
                 "disabled": p["background"]}
        images = {}
        for state in ("normal", "active", "pressed", "disabled", "focus", "focus_active", "focus_pressed"):
            key = theme, variant, radius, state
            if key not in cache:
                cache[key] = tk.PhotoImage(master=root, width=size, height=size)
            fill = fills.get(state.replace("focus_", ""), fills["normal"])
            edge = (p["focus"] if state.startswith("focus") else fill if primary or variant == "Secondary"
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
        style.layout(style_name, [(element, {"sticky": "nswe", "children": [
            ("Button.padding", {"sticky": "nswe", "children": [("Button.label", {"sticky": "nswe"})]})]})])
    palettes[theme] = (dict(p), radius)
    root._root()._uic_button_palettes = palettes

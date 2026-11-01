"""Apply UI_Center tokens to one Tk interpreter; call on its UI thread.

Adapted from Zerozero05/PDF_Bookmarks/ui_theme.py at
0097a07ba494e3376fab680e880bf2d2a1ced66c, lines 12-34, 53-154,
190-237, 257-297 (AGPL v3). The clam style strategy is retained; palettes are loaded
from shared JSON, names are independent and PDF-specific behavior is omitted.
SPDX-License-Identifier: AGPL-3.0-only
"""

import json
from pathlib import Path
from tkinter import font as tkfont, ttk
from ._drawing import blend, button_layouts, field_layouts


def load_tokens(path=None):
    """Load the shared source; copied consumers should pass their own path."""
    source = Path(path) if path is not None else Path(__file__).resolve().parents[3] / "tokens" / "design-tokens.json"
    with source.open(encoding="utf-8") as stream:
        tokens = json.load(stream)
    # Older consumer token files remain readable. New decorative roles never
    # replace the existing control border, text or keyboard-focus roles.
    for palette in tokens["themes"].values():
        palette.setdefault("divider", blend(palette["border"], palette["background"], .72))
        palette.setdefault("accent_soft", blend(palette["background"], palette["accent"], .09))
    return tokens


def apply_theme(root, mode="light", *, tokens_path=None, font_scale=1.0):
    """Apply tokens to this interpreter's ttk widgets and return its palette.

    The system theme, files, and application data are untouched. Plain Tk
    widgets other than root/toplevel backgrounds need their own color adapter.
    Native file dialogs retain the operating system's own appearance.
    """
    tokens = load_tokens(tokens_path)
    if font_scale <= 0:
        raise ValueError("font_scale must be positive")
    if mode not in tokens["themes"]:
        raise ValueError("Unknown theme: " + mode)
    p = tokens["themes"][mode]
    gap = tokens["spacing"]
    typography = tokens["typography"]
    body_font = tkfont.nametofont("TkDefaultFont", root=root)
    point = lambda role: max(1, round(typography[role]["tk_points"] * font_scale))
    if body_font.actual("size") != point("body"):
        body_font.configure(size=point("body"))
    family = body_font.actual("family")
    # Share the same font objects across themes. Literal font tuples in every
    # theme force native metrics to be rebuilt when only colors change.
    fonts = getattr(root._root(), "_uic_fonts", {})
    for role, weight in (("small", "normal"), ("heading", "bold")):
        values = {"family": family, "size": point(role), "weight": weight}
        if role not in fonts:
            fonts[role] = tkfont.Font(root=root, **values)
        elif any(fonts[role].actual(option) != value for option, value in values.items()):
            fonts[role].configure(**values)
    root._root()._uic_fonts = fonts
    body, small, heading = "TkDefaultFont", fonts["small"], fonts["heading"]
    for name in ("TkTextFont", "TkFixedFont"):
        font = tkfont.nametofont(name, root=root)
        if font.actual("size") != point("body"):
            font.configure(size=point("body"))
    disabled = [("disabled", p["disabled"])]
    edge = [("disabled", p["border"]), ("focus", p["focus"]), ("active", p["accent"])]
    settings = {
        ".": {"configure": {
            "background": p["background"], "foreground": p["foreground"],
            "fieldbackground": p["input_background"], "font": body,
            "bordercolor": p["border"], "lightcolor": p["border"],
            "darkcolor": p["border"], "focuscolor": p["focus"],
            "selectbackground": p["selected_background"],
            "selectforeground": p["selected_foreground"],
        }},
        "TFrame": {"configure": {"background": p["background"]}},
        "TLabel": {"configure": {"background": p["background"], "foreground": p["foreground"]}},
        "UIC.Heading.TLabel": {"configure": {"font": heading}},
        "UIC.Muted.TLabel": {"configure": {"foreground": p["muted"], "font": small}},
        "UIC.Badge.TLabel": {"configure": {"background": p["accent_soft"], "foreground": p["accent"],
                                             "font": small, "padding": (8, 4)}},
        "UIC.Preview.TFrame": {"configure": {"background": p["surface"], "borderwidth": 1,
                                               "relief": "solid", "bordercolor": p["divider"],
                                               "lightcolor": p["divider"], "darkcolor": p["divider"]}},
        "UIC.Section.TLabel": {"configure": {"font": (family, point("body"), "bold")}},
        "UIC.Loader.TFrame": {"configure": {"background": p["hover"]}},
        "UIC.Popover.TFrame": {"configure": {"background": p["surface"]}},
        "UIC.Tooltip.TFrame": {"configure": {"background": p["foreground"]}},
        "UIC.Stage.TFrame": {"configure": {"background": p["surface"]}},
        "UIC.Stage.TLabel": {"configure": {"background": p["surface"], "foreground": p["foreground"]}},
        "UIC.Stage.Muted.TLabel": {"configure": {"background": p["surface"], "foreground": p["muted"], "font": small}},
        "TSeparator": {"configure": {"background": p["divider"]}},
        "UIC.Success.TLabel": {"configure": {"foreground": p["success"]}},
        "UIC.Warning.TLabel": {"configure": {"foreground": p["warning"]}},
        "UIC.Error.TLabel": {"configure": {"foreground": p["error"]}},
        "TLabelframe": {"configure": {"background": p["background"], "bordercolor": p["divider"]}},
        "TLabelframe.Label": {"configure": {"background": p["background"], "foreground": p["foreground"]}},
        "TButton": {
            "configure": {"padding": (gap["md"], gap["sm"]), "background": p["surface"],
                          "foreground": p["foreground"], "borderwidth": 1},
            "map": {"background": [("disabled", p["background"]), ("pressed", p["hover"]),
                                    ("active", p["hover"])],
                    "foreground": disabled, "bordercolor": edge, "lightcolor": edge, "darkcolor": edge},
        },
        "UIC.Primary.TButton": {
            "configure": {"background": p["accent"], "foreground": p["selected_foreground"]},
            "map": {"background": [("disabled", p["background"]), ("pressed", p["accent_active"]),
                                    ("active", p["accent_active"])],
                    "foreground": [("disabled", p["disabled"]), ("!disabled", p["selected_foreground"])],
                    "bordercolor": edge, "lightcolor": edge, "darkcolor": edge},
        },
        "UIC.Secondary.TButton": {
            "configure": {"padding": (gap["sm"], gap["xs"]), "relief": "flat",
                          "borderwidth": 1, "background": p["surface"], "foreground": p["foreground"]},
            "map": {"background": [("disabled", p["background"]), ("active", p["hover"])],
                    "foreground": disabled, "bordercolor": [("focus", p["focus"]), ("!focus", p["surface"])],
                    "lightcolor": [("focus", p["focus"]), ("!focus", p["surface"])],
                    "darkcolor": [("focus", p["focus"]), ("!focus", p["surface"])]},
        },
        "UIC.Busy.TButton": {"configure": {"padding": (12, 8), "foreground": p["accent"]},
                             "map": {"foreground": [("disabled", p["accent"])],
                                     "background": [("disabled", p["accent_soft"]) ]}},
        "UIC.Nav.TButton": {"configure": {"padding": (12, 8), "anchor": "w", "foreground": p["muted"]}},
        "UIC.NavSelected.TButton": {"configure": {"padding": (12, 8), "anchor": "w", "foreground": p["accent"]}},
        "TEntry": {
            "configure": {"padding": (gap["sm"], gap["xs"]), "insertcolor": p["foreground"], "borderwidth": 1},
            "map": {"foreground": disabled, "fieldbackground": [("disabled", p["background"])],
                    "bordercolor": edge, "lightcolor": edge, "darkcolor": edge},
        },
        "TCombobox": {
            "configure": {"padding": (gap["sm"], gap["xs"]), "background": p["surface"],
                          "arrowcolor": p["muted"], "arrowsize": 13, "borderwidth": 1},
            "map": {"foreground": disabled,
                    "fieldbackground": [("disabled", p["background"]), ("readonly", p["input_background"])],
                    "selectbackground": [("readonly", p["selected_background"])],
                    "selectforeground": [("readonly", p["selected_foreground"])],
                    "bordercolor": edge, "lightcolor": edge, "darkcolor": edge,
                    "arrowcolor": disabled},
        },
        "TScrollbar": {
            "configure": {"background": p["divider"], "troughcolor": p["background"],
                          "arrowcolor": p["foreground"], "width": max(10, round(10 * font_scale))},
            "map": {"background": [("active", p["hover"])]},
        },
        "Treeview": {
            "configure": {"background": p["surface"], "fieldbackground": p["surface"],
                          "foreground": p["foreground"], "rowheight": body_font.metrics("linespace") + gap["md"],
                          "borderwidth": 0, "relief": "flat", "bordercolor": p["surface"],
                          "lightcolor": p["surface"], "darkcolor": p["surface"]},
            "map": {"background": [("selected", p["selected_background"])],
                    "foreground": [("selected", p["selected_foreground"])]},
        },
        "Treeview.Heading": {
            "configure": {"background": p["hover"], "foreground": p["foreground"], "padding": gap["xs"]},
            "map": {"background": [("active", p["surface"])]},
        },
        "Horizontal.TProgressbar": {"configure": {"background": p["accent"],
            "troughcolor": p["hover"], "bordercolor": p["hover"], "lightcolor": p["accent"],
            "darkcolor": p["accent"], "thickness": 8}},
        "TNotebook": {"configure": {"background": p["background"], "bordercolor": p["background"], "borderwidth": 0,
                                      "lightcolor": p["background"], "darkcolor": p["background"],
                                      "tabmargins": (0, 0, 0, 6)}},
        "TNotebook.Tab": {"configure": {"padding": (12, 8), "background": p["background"],
                                          "foreground": p["muted"], "bordercolor": p["divider"],
                                          "lightcolor": p["background"], "darkcolor": p["divider"],
                                          "focuscolor": p["focus"]},
                          "map": {"background": [("selected", p["accent_soft"]), ("active", p["hover"])],
                                  "foreground": [("selected", p["accent"])],
                                  "lightcolor": [("selected", p["accent_soft"])],
                                  "bordercolor": [("selected", p["accent_soft"])],
                                  "darkcolor": [("selected", p["accent_soft"])]}},
        "UIC.Navigation.Treeview": {"configure": {"background": p["background"], "fieldbackground": p["background"],
                                                   "bordercolor": p["background"], "lightcolor": p["background"],
                                                   "darkcolor": p["background"]},
                                    "map": {"background": [("selected", p["accent_soft"])],
                                            "foreground": [("selected", p["accent"])]}},
    }
    style = ttk.Style(root)
    name = "uicenter_" + mode
    if name in style.theme_names():
        style.theme_settings(name, settings)
    else:
        style.theme_create(name, parent="clam", settings=settings)
    if style.theme_use() != name:
        style.theme_use(name)
    button_layouts(root, style, p, tokens["radii"]["control"])
    field_layouts(root, style, p, tokens["radii"]["control"])
    # The combobox popup is a Tk listbox, not a ttk widget. Recolor already-opened
    # popdowns as well as future popdowns; do not open a popup to refresh it.
    for option, color in (("background", p["input_background"]), ("foreground", p["foreground"]),
                          ("selectBackground", p["selected_background"]),
                          ("selectForeground", p["selected_foreground"])):
        root.option_add("*TCombobox*Listbox." + option, color)
    pending = [str(root)]
    while pending:
        path = pending.pop()
        widget_class = root.tk.call("winfo", "class", path)
        if widget_class in ("Tk", "Toplevel"):
            root.tk.call(path, "configure", "-background", p["background"])
        elif widget_class == "Listbox":
            root.tk.call(path, "configure", "-background", p["input_background"],
                         "-foreground", p["foreground"], "-selectbackground", p["selected_background"],
                         "-selectforeground", p["selected_foreground"])
        pending.extend(root.tk.splitlist(root.tk.call("winfo", "children", path)))
    return dict(p)

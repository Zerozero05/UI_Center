"""Explicit dispatch: every component opens its own real demonstration."""
from . import previews_loading, previews_overlays, previews_navigation_feedback, previews_legacy

FAMILIES = (previews_loading, previews_overlays, previews_navigation_feedback, previews_legacy)
IDS = tuple(key for family in FAMILIES for key in family.IDS)


def create_preview(key, master, *, palette, reduced_motion=False, spacing=None):
    for family in FAMILIES:
        if key in family.IDS:
            options = {"palette": palette, "reduced_motion": reduced_motion}
            if family is previews_legacy:
                options["spacing"] = spacing
            return family.create_preview(key, master, **options)
    raise ValueError("没有对应的组件预览：" + key)

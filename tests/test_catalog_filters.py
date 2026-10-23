"""Category-aware navigation without changing exact catalog search semantics."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apps.desktop.catalog import (PLATFORMS, SCENES, SECTIONS, available_platforms,
                                  available_scenes, filter_entries)


class CatalogFilterTests(unittest.TestCase):
    def test_screenshot_combination_is_empty_but_the_references_still_exist(self):
        self.assertEqual(filter_entries(scene="复用与来源", section="组件库"), [])
        self.assertEqual(len(filter_entries(scene="复用与来源", section="资料与来源")), 5)
        self.assertNotIn("复用与来源", available_scenes("组件库", "全部平台"))
        self.assertIn("复用与来源", available_scenes("资料与来源", "全部平台"))

    def test_components_offer_only_applicable_platforms_and_scenes_in_global_order(self):
        self.assertEqual(available_platforms("组件库"), ("全部平台", "Tkinter", "Android"))
        self.assertEqual(available_scenes("组件库", "全部平台"),
                         ("全部场景", "加载组件", "弹层组件", "导航组件", "反馈组件", "任务与结果", "主题与设置"))
        self.assertEqual(available_scenes("组件库", "Android"), ("全部场景", "任务与结果", "主题与设置"))
        self.assertEqual(filter_entries(platform="Android", scene="反馈组件", section="组件库"), [])

    def test_general_guidance_remains_available_with_specific_platforms(self):
        for section in ("设计规范", "资料与来源"):
            self.assertEqual(available_platforms(section), PLATFORMS)
            self.assertEqual(available_scenes(section, "全部平台"), available_scenes(section, "Android"))
            self.assertEqual(filter_entries(section=section), filter_entries(section=section, platform="Android"))

    def test_every_offered_specific_option_has_results_and_keeps_global_order(self):
        for section in SECTIONS:
            platforms = available_platforms(section)
            self.assertEqual(platforms, tuple(value for value in PLATFORMS if value in platforms))
            for platform in platforms:
                scenes = available_scenes(section, platform)
                self.assertEqual(scenes, tuple(value for value in SCENES if value in scenes))
                for scene in scenes:
                    with self.subTest(section=section, platform=platform, scene=scene):
                        self.assertTrue(filter_entries(section=section, platform=platform, scene=scene))

    def test_search_remains_category_scoped_case_insensitive_and_all_terms_required(self):
        self.assertEqual(filter_entries("借鉴来源", section="组件库"), [])
        self.assertEqual([entry.key for entry in filter_entries("借鉴来源", section="资料与来源")], ["sources"])
        self.assertEqual([entry.key for entry in filter_entries("pRoGrEsS bAr", section="组件库")], ["progress-bar"])
        self.assertEqual(filter_entries("普通弹窗 骨架屏", section="组件库"), [])
        self.assertEqual([entry.key for entry in filter_entries("shummer", section="组件库")], ["shimmer"])


if __name__ == "__main__":
    unittest.main()

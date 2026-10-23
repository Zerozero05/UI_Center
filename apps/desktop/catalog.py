"""Navigation metadata only; document and code text remain in their originals."""

from dataclasses import dataclass

import re

from .resources import section_text


@dataclass(frozen=True)
class Entry:
    key: str
    title: str
    summary: str
    platform: str
    scene: str
    resource: str
    kind: str = "reference"
    heading: str | None = None
    language: str = ""
    preview_id: str = ""
    aliases: str = ""
    source_files: tuple = ()
    usage_key: str = ""

    @property
    def preview(self):
        return bool(self.preview_id)

    @property
    def boundary(self):
        if self.platform == "Android":
            return "Android 源码参考 · 已有构建检查，尚未设备实测"
        if self.kind in ("guide", "pattern"):
            return "规范建议 · 需在目标应用实现与验证"
        if self.preview:
            return "Tkinter · 实时控件 · 使用虚构数据"
        return "原文资料 · 按选定源码提交查阅"


CORE_COMPONENTS = (
    ("spinner", "旋转加载", "Spinner loading", "进度未知时的等待指示，支持尺寸、速度与暂停", "加载组件", "loading"),
    ("progress-bar", "条形进度", "ProgressBar Progress Bar linear determinate indeterminate", "显示真实完成量，或明确的不确定进度", "加载组件", "loading"),
    ("circular-progress", "环形进度", "CircularProgress Circular Progress ring percentage", "紧凑区域显示调用方提供的真实百分比", "加载组件", "loading"),
    ("skeleton", "骨架屏", "Skeleton placeholder", "内容结构已知时，先显示列表或卡片占位", "加载组件", "loading"),
    ("shimmer", "扫光骨架", "Shimmer shummer skeleton", "可关闭扫光的骨架加载，减少动画时保留静态占位", "加载组件", "loading"),
    ("loading-button", "加载按钮", "LoadingButton Button Loading busy submit", "按钮内反馈忙碌状态，防止重复提交并恢复操作", "加载组件", "loading"),
    ("page-loader", "区域加载层", "PageLoader Page Loader overlay loading", "在内容区域显示等待、真实进度与取消入口", "加载组件", "loading"),
    ("dialog", "普通弹窗", "Dialog modal", "详情与小表单，支持键盘关闭和焦点返回", "弹层组件", "overlays"),
    ("confirm-dialog", "确认弹窗", "ConfirmDialog Confirm Dialog Alert Dialog", "说明重要操作的后果，默认聚焦安全操作", "弹层组件", "overlays"),
    ("drawer", "抽屉", "Drawer Sheet", "左侧或右侧展开的面板，区分模态与非模态", "弹层组件", "overlays"),
    ("popover", "气泡面板", "Popover popup", "触发按钮附近的轻量交互，点击外部或Esc关闭", "弹层组件", "overlays"),
    ("tooltip", "工具提示", "Tooltip hint", "悬停或键盘聚焦时显示补充解释", "弹层组件", "overlays"),
    ("tabs", "标签页", "Tabs Notebook tab", "切换同层内容，支持禁用项、长标题与键盘", "导航组件", "navigation-feedback"),
    ("accordion", "折叠面板", "Accordion Collapsible", "按需展开帮助和分组，支持单项或多项展开", "导航组件", "navigation-feedback"),
    ("segmented-control", "分段选择", "SegmentedControl Segmented Control toggle group", "互斥模式选择，展示选中、禁用和回调", "导航组件", "navigation-feedback"),
    ("inline-alert", "行内提示", "InlineAlert Inline Alert message status", "持续可读的信息、成功、警告和错误反馈", "反馈组件", "navigation-feedback"),
    ("toast", "轻通知", "Toast notification snackbar", "短暂反馈、手动关闭与悬停或聚焦暂停", "反馈组件", "navigation-feedback"),
    ("empty-state", "空状态", "EmptyState Empty State no data no results", "区分首次使用、无数据和无搜索结果，给出下一步", "反馈组件", "navigation-feedback"),
)


def _component_entry(row):
    key, title, aliases, summary, scene, document = row
    module = "navigation" if scene == "导航组件" else "feedback" if scene == "反馈组件" else document
    return Entry(key, title, summary, "Tkinter", scene, f"docs/components/{document}.md", "component",
                 heading=key, language="python", preview_id=key, aliases=aliases, usage_key=key,
                 source_files=(f"components/tkinter/ui_center/{module}.py",
                               "components/tkinter/ui_center/theme.py", "tokens/design-tokens.json"))


ENTRIES = [_component_entry(row) for row in CORE_COMPONENTS] + [
    Entry("guide-" + key, title, summary, "通用", "设计规范", "docs/design-guide.md", "guide", title)
    for key, title, summary in (
        ("hierarchy", "视觉层次", "标题、正文、辅助文字和主动作，明确当前任务"),
        ("layout", "布局与留白", "分组、间距、小窗口滚动与输入状态保持"),
        ("actions", "主次操作", "一个主动作，辅助操作、忙碌与取消入口"),
        ("feedback", "反馈分级", "就地校验、完成、错误与持续可读的结果"),
        ("keyboard", "键盘与焦点", "Tab、快捷键、输入编辑与弹窗焦点恢复"),
        ("themes", "明暗主题", "语义颜色、正常、禁用、焦点和选中状态"),
    )
] + [
    Entry("pattern-" + key, title, summary, "通用", scene, "docs/patterns.md", "pattern", title)
    for key, title, summary, scene in (
        ("files", "文件选择", "选择、取消、长路径与权限边界；未提取文件访问代码", "文件与表单"),
        ("forms", "参数表单", "空值、范围、就地校验和键盘操作", "文件与表单"),
        ("tasks", "长任务与取消", "进度、禁止重复开始、取消、部分结果和重试", "任务与结果"),
        ("results", "结果列表", "成功、失败、长条目与部分完成", "任务与结果"),
        ("settings", "设置面板", "会话主题、共享状态与应用自行持久化", "主题与设置"),
        ("validation", "校验与确认", "修正输入、明确操作后果、保留原状态", "文件与表单"),
    )
] + [
    Entry("tk-theme", "Tkinter 明暗主题", "apply_theme、共享参数、系统字体与焦点", "Tkinter", "主题与设置",
          "components/tkinter/README.md", "component", heading="tk-theme", language="python", preview_id="legacy-theme", usage_key="tk-theme",
          source_files=("components/tkinter/ui_center/theme.py", "tokens/design-tokens.json")),
    Entry("tk-actions", "Tkinter 主次操作区", "ActionBar、开始、次操作、忙碌禁用与取消", "Tkinter", "任务与结果",
          "components/tkinter/README.md", "component", heading="tk-actions", language="python", preview_id="legacy-actions", usage_key="tk-actions",
          source_files=("components/tkinter/ui_center/widgets.py", "tokens/design-tokens.json")),
    Entry("tk-task", "Tkinter 任务与结果", "TaskPanel、进度、取消、失败、长名称与复制", "Tkinter", "任务与结果",
          "components/tkinter/README.md", "component", heading="tk-task", language="python", preview_id="legacy-task", usage_key="tk-task",
          source_files=("components/tkinter/ui_center/widgets.py", "tokens/design-tokens.json")),
    Entry("android-theme", "Android Views 主题", "UiTheme、JSON 参数、字号、圆角与系统栏", "Android", "主题与设置",
          "components/android/README.md", "component", heading="android-theme", language="java", usage_key="android-theme"),
    Entry("android-actions", "Android 主操作与取消", "ActionGroup、触控目标、长文字与回调", "Android", "任务与结果",
          "components/android/README.md", "component", heading="android-actions", language="java", usage_key="android-actions"),
    Entry("android-state", "Android 任务状态与结果", "TaskState、TaskPanel、进度、取消与恢复边界", "Android", "任务与结果",
          "components/android/README.md", "component", heading="android-state", language="java", usage_key="android-state"),
    Entry("tokens", "共享设计参数", "唯一 JSON、颜色、间距、字号与平台映射", "通用", "主题与设置", "tokens/README.md"),
    Entry("consumption", "复制源码与更新", "固定提交、采用记录、差异升级与独立消费", "通用", "复用与来源", "docs/consumption.md"),
    Entry("cases", "已有应用案例", "桌面与 Android 的来源、提炼内容与业务边界", "通用", "复用与来源", "docs/cases.md"),
    Entry("sources", "借鉴来源", "代码改编、方法参考、运行依赖与固定上游提交", "通用", "复用与来源", "references/sources.md"),
    Entry("validation", "实际验证与限制", "已经验证、未测试范围、Android 设备验收后延", "通用", "复用与来源", "VALIDATION.md"),
    Entry("licenses", "许可与第三方通知", "AGPL、源码、实际随附运行库与版权声明", "通用", "复用与来源", "THIRD_PARTY_NOTICES.md"),
]

PLATFORMS = ("全部平台", "通用", "Tkinter", "Android")
SCENES = ("全部场景", "加载组件", "弹层组件", "导航组件", "反馈组件", "设计规范", "文件与表单", "任务与结果", "主题与设置", "复用与来源")
SECTIONS = ("组件库", "设计规范", "资料与来源")


def section_for(entry):
    if entry.kind == "component":
        return "组件库"
    if entry.kind in ("guide", "pattern"):
        return "设计规范"
    return "资料与来源"


def filter_entries(query="", platform="全部平台", scene="全部场景", section=None):
    terms = query.casefold().split()
    return [entry for entry in ENTRIES
            if (section is None or section_for(entry) == section)
            and (platform == "全部平台" or entry.platform in ("通用", platform))
            and (scene == "全部场景" or entry.scene == scene)
            and all(term in (entry.title + " " + entry.summary + " " + entry.aliases + " " + entry.scene
                             + " " + entry.key).casefold() for term in terms)]


def available_platforms(section):
    """Keep the platform order, including shared entries in platform scopes."""
    return tuple(platform for platform in PLATFORMS
                 if platform == PLATFORMS[0] or filter_entries(platform=platform, section=section))


def available_scenes(section, platform):
    """Navigation choices depend on scope, never on a transient search query."""
    return tuple(scene for scene in SCENES
                 if scene == SCENES[0] or filter_entries(platform=platform, scene=scene, section=section))


def body_for(store, entry):
    if entry.key == "licenses":
        return store.license_text()
    body = section_text(store.read(entry.resource), entry.heading)
    if entry.kind == "component":
        body = re.sub(r"<!-- example:[^>]+ -->\s*```[^\n]*\n.*?^```\s*", "", body, flags=re.M | re.S)
        body = re.sub(r"^## [^\n]+", "## " + entry.title, body, count=1)
    return body


def usage_for(store, entry):
    if entry.language:
        pattern = r"<!-- example:" + re.escape(entry.usage_key) + r" -->\s*```" + re.escape(entry.language) + r"\s*\n(.*?)^```"
        match = re.search(pattern, store.read(entry.resource), flags=re.M | re.S)
        if match is None:
            raise ValueError("原文缺少示例代码：" + entry.resource)
        return match[1].rstrip() + "\n"
    if entry.key == "tokens":
        return store.read("tokens/design-tokens.json")
    return ""


def adoption_note(store, entry, usage_override=None):
    source = store.commit or "开发源码（尚无固定提交，采用前先确定稳定提交）"
    if store.commit and not store.frozen:
        source += "（开发工作区的 HEAD 参考；采用前核对本地变更并固定提交）"
    url = store.github_url(entry.resource)
    task = ("按以下规范评估并优化目标界面；规范条目不代表已有可复制的通用控件。"
            if entry.kind in ("guide", "pattern") else
            "先核对条目的适用条件，再选用说明和实际源码接口。")
    return (f"请参考 UI_Center {store.version} 的「{entry.title}」。\n"
            f"来源提交：{source}\n原文：{entry.resource}\n" +
            (f"{'固定来源' if store.frozen else 'HEAD 参考原文'}链接：{url}\n" if url else "") +
            "许可：AGPL-3.0-only；第三方内容保留各自许可与必要声明。\n" +
            ("源码依赖：完整 ui_center 包及 tokens/design-tokens.json；示例导入语句不是组件源码。\n"
             if entry.platform == "Tkinter" and entry.kind == "component" else "") +
            f"能力边界：{entry.boundary}\n\n{task}\n"
            "先读取目标项目的要求与现有实现，保留原业务、文件操作、配置和已确认功能。\n"
            "说明采用的规范/源码、来源提交、本地调整与许可；在目标程序验证正常、忙碌、取消、完成、失败、长文本、焦点和主题。\n"
            "Android 条目只作为源码与构建参考，不能宣称设备界面已实测。\n\n"
            "以下为当前采用内容（参数示例仅针对所选平台）：\n\n" +
            (usage_override if usage_override is not None else usage_for(store, entry) or body_for(store, entry)))


def source_notes(store, entry):
    files = entry.source_files or (entry.resource,)
    lines = ["## 完整源码与依赖", "", "最小示例需要复制 ui_center 组件包与 tokens/design-tokens.json，保留许可与来源记录。", ""]
    for path in files:
        url = store.github_url(path)
        lines.append(f"- [{path}]({url})" if url else "- " + path)
    if entry.platform == "Tkinter":
        lines += ["", "## 其他平台适配", "", "Web 可按相同状态模型选择原生元素或相应组件库；Android 可按相同职责采用平台 Views。这里的实时预览只验证 Tkinter 实现，不代表其他平台已经实现或设备验收。"]
    lines += ["", "自有组件采用 AGPL-3.0-only；引用指定提交后记录本地调整。"]
    return "\n".join(lines)

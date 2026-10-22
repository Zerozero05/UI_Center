"""Navigation metadata only; document and code text remain in their originals."""

from dataclasses import dataclass

from .resources import first_code_block, section_text


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
    preview: bool = False

    @property
    def boundary(self):
        if self.platform == "Android":
            return "Android 源码参考 · 已有构建检查，尚未设备实测"
        if self.kind in ("guide", "pattern"):
            return "规范建议 · 需在目标应用实现与验证"
        if self.preview:
            return "Tkinter 组件 · 可打开真实控件预览"
        return "原文资料 · 按选定源码提交查阅"


ENTRIES = [
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
          "components/tkinter/README.md", "component", language="python", preview=True),
    Entry("tk-actions", "Tkinter 主次操作区", "ActionBar、开始、次操作、忙碌禁用与取消", "Tkinter", "任务与结果",
          "components/tkinter/README.md", "component", language="python", preview=True),
    Entry("tk-task", "Tkinter 任务与结果", "TaskPanel、进度、取消、失败、长名称与复制", "Tkinter", "任务与结果",
          "components/tkinter/README.md", "component", language="python", preview=True),
    Entry("android-theme", "Android Views 主题", "UiTheme、JSON 参数、字号、圆角与系统栏", "Android", "主题与设置",
          "components/android/README.md", "component", language="java"),
    Entry("android-actions", "Android 主操作与取消", "ActionGroup、触控目标、长文字与回调", "Android", "任务与结果",
          "components/android/README.md", "component", language="java"),
    Entry("android-state", "Android 任务状态与结果", "TaskState、TaskPanel、进度、取消与恢复边界", "Android", "任务与结果",
          "components/android/README.md", "component", language="java"),
    Entry("tokens", "共享设计参数", "唯一 JSON、颜色、间距、字号与平台映射", "通用", "主题与设置", "tokens/README.md"),
    Entry("consumption", "复制源码与更新", "固定提交、采用记录、差异升级与独立消费", "通用", "复用与来源", "docs/consumption.md"),
    Entry("cases", "已有应用案例", "桌面与 Android 的来源、提炼内容与业务边界", "通用", "复用与来源", "docs/cases.md"),
    Entry("sources", "借鉴来源", "代码改编、方法参考、运行依赖与固定上游提交", "通用", "复用与来源", "references/sources.md"),
    Entry("validation", "实际验证与限制", "已经验证、未测试范围、Android 设备验收后延", "通用", "复用与来源", "VALIDATION.md"),
    Entry("licenses", "许可与第三方通知", "AGPL、源码、实际随附运行库与版权声明", "通用", "复用与来源", "THIRD_PARTY_NOTICES.md"),
]

PLATFORMS = ("全部平台", "通用", "Tkinter", "Android")
SCENES = ("全部场景", "设计规范", "文件与表单", "任务与结果", "主题与设置", "复用与来源")


def filter_entries(query="", platform="全部平台", scene="全部场景"):
    terms = query.casefold().split()
    return [entry for entry in ENTRIES
            if (platform == "全部平台" or entry.platform in ("通用", platform))
            and (scene == "全部场景" or entry.scene == scene)
            and all(term in (entry.title + " " + entry.summary).casefold() for term in terms)]


def body_for(store, entry):
    if entry.key == "licenses":
        return store.license_text()
    return section_text(store.read(entry.resource), entry.heading)


def usage_for(store, entry):
    if entry.language:
        code = first_code_block(store.read(entry.resource), entry.language)
        if not code:
            raise ValueError("原文缺少示例代码：" + entry.resource)
        return code
    if entry.key == "tokens":
        return store.read("tokens/design-tokens.json")
    return body_for(store, entry)


def adoption_note(store, entry):
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
            f"能力边界：{entry.boundary}\n\n{task}\n"
            "先读取目标项目的要求与现有实现，保留原业务、文件操作、配置和已确认功能。\n"
            "说明采用的规范/源码、来源提交、本地调整与许可；在目标程序验证正常、忙碌、取消、完成、失败、长文本、焦点和主题。\n"
            "Android 条目只作为源码与构建参考，不能宣称设备界面已实测。\n\n"
            "以下内容直接来自对应原文：\n\n" + usage_for(store, entry))

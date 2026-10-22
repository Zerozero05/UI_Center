# 来源与采用记录

核验日期：2026-10-23。仓库、提交与许可证通过官方 GitHub API 和原始文件核对；提交日期按 UTC 记录。下列固定提交是本次参考快照，后续升级应更新实际采用范围与验证结果。

本项目区分三类来源：**代码改编**表示实际提炼或重写已有实现；**方法参考**表示参考组织、交互或设计方法而没有引入其源码或资源；**运行依赖**表示消费者运行时需要加载的外部库。

## 已有程序的代码改编

UI_Center 的通用组件提炼自 Zerozero05 已有的桌面与 Android 程序。相关改编代码采用 **AGPL-3.0-only**；完整许可见 [LICENSE](../LICENSE)，署名和许可说明见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。

### Tkinter / ttk

- 原项目：[Zerozero05/PDF_Bookmarks](https://github.com/Zerozero05/PDF_Bookmarks)。
- 固定提交：[`0097a07ba494e3376fab680e880bf2d2a1ced66c`](https://github.com/Zerozero05/PDF_Bookmarks/commit/0097a07ba494e3376fab680e880bf2d2a1ced66c)。
- 原始许可：[LICENSE.txt](https://github.com/Zerozero05/PDF_Bookmarks/blob/0097a07ba494e3376fab680e880bf2d2a1ced66c/LICENSE.txt)，GNU AGPL v3。

| 原始文件 | 本项目采用位置 | 类型与范围 |
| --- | --- | --- |
| [ui_theme.py](https://github.com/Zerozero05/PDF_Bookmarks/blob/0097a07ba494e3376fab680e880bf2d2a1ced66c/ui_theme.py) | [theme.py](../components/tkinter/ui_center/theme.py) | 代码改编：基于 `clam` 的 ttk 主题、语义颜色、明暗控件状态、组合框弹出列表及窗口背景刷新策略。参考原文件第 12–34、53–154、190–237、257–297 行；颜色改读共享 tokens，移除 PDF 专属标签、图标及提示逻辑。 |
| [bookmarks_gui.py](https://github.com/Zerozero05/PDF_Bookmarks/blob/0097a07ba494e3376fab680e880bf2d2a1ced66c/bookmarks_gui.py) | [widgets.py](../components/tkinter/ui_center/widgets.py)、[演示程序](../examples/tkinter/demo.py) | 方法参考：主次操作、忙碌反馈和轮询更新；通用操作组、任务面板及模拟任务独立编写。 |

### Android 原生 Views

- 原项目：[Zerozero05/PDF_Bookmarks_Android](https://github.com/Zerozero05/PDF_Bookmarks_Android)。
- 固定提交：[`b44ab5d14e547fef4b80e9469b7c8eb503e2302e`](https://github.com/Zerozero05/PDF_Bookmarks_Android/commit/b44ab5d14e547fef4b80e9469b7c8eb503e2302e)。
- 原始许可：[LICENSE](https://github.com/Zerozero05/PDF_Bookmarks_Android/blob/b44ab5d14e547fef4b80e9469b7c8eb503e2302e/LICENSE)，GNU AGPL v3。

| 原始文件 | 本项目采用位置 | 类型与范围 |
| --- | --- | --- |
| [UiAppearance.java](https://github.com/Zerozero05/PDF_Bookmarks_Android/blob/b44ab5d14e547fef4b80e9469b7c8eb503e2302e/app/src/main/java/cn/local/pdfbookmarks/UiAppearance.java) | [UiTheme.java](../components/android/src/main/java/cn/local/uicenter/UiTheme.java) | 代码改编：原生按钮状态与涟漪、48dp 触控目标、系统栏刷新；颜色由共享 tokens 提供。 |
| [MainActivity.java](https://github.com/Zerozero05/PDF_Bookmarks_Android/blob/b44ab5d14e547fef4b80e9469b7c8eb503e2302e/app/src/main/java/cn/local/pdfbookmarks/MainActivity.java) | [ActionGroup.java](../components/android/src/main/java/cn/local/uicenter/ActionGroup.java)、[TaskPanel.java](../components/android/src/main/java/cn/local/uicenter/TaskPanel.java) | 代码改编：提炼按钮/样式、卡片和结果状态呈现；删除原应用的持久设置、文件与 PDF 业务逻辑。 |
| [TaskOutcome.java](https://github.com/Zerozero05/PDF_Bookmarks_Android/blob/b44ab5d14e547fef4b80e9469b7c8eb503e2302e/app/src/main/java/cn/local/pdfbookmarks/TaskOutcome.java) | [TaskState.java](../components/android/src/main/java/cn/local/uicenter/TaskState.java) | 代码改编：把阶段结果/状态快照泛化为通用任务生命周期，重写业务枚举及运行、取消、成功和失败状态。 |

[Android 演示程序](../examples/android/)使用独立应用标识与模拟数据。上述提炼不要求安装或运行原 PDF 程序，也不引入其 PDF、OCR 和文件处理依赖。

## 外部开源项目的方法参考

以下六项均为**方法参考**，没有将其源码、模板、图片、图标、字体或其他资源复制进本项目，也没有作为本项目的运行依赖。

| 来源与固定提交 | 提交日期 | 上游许可 | 具体参考内容与边界 |
| --- | --- | --- | --- |
| [shadcn/ui · 25af02b](https://github.com/shadcn-ui/ui/tree/25af02b1b467fcd53b63e0c6d6d324c57c16ef18) | 2026-10-22 | [MIT](https://github.com/shadcn-ui/ui/blob/25af02b1b467fcd53b63e0c6d6d324c57c16ef18/LICENSE.md) | 源码复制后由消费者维护的分发方式，以及条目索引/文件清单。首版只采用清晰的源码复制说明，没有安装 CLI 或建立 registry。 |
| [Storybook · 40d47bf](https://github.com/storybookjs/storybook/tree/40d47bf739fc8d97fdddaa2d22d8dc79fb2f0bd6) | 2026-10-22 | [MIT](https://github.com/storybookjs/storybook/blob/40d47bf739fc8d97fdddaa2d22d8dc79fb2f0bd6/LICENSE) | 按场景组织组件、展示明暗/忙碌/错误状态并验证交互。Tkinter 与 Android 直接提供原生示例，不为首版增加 Storybook 工具链。 |
| [Style Dictionary · 745264a](https://github.com/style-dictionary/style-dictionary/tree/745264a62d01037581c6654fb4ac66bb3d245f07) | 2026-10-16 | [Apache-2.0](https://github.com/style-dictionary/style-dictionary/blob/745264a62d01037581c6654fb4ac66bb3d245f07/LICENSE) | 一处维护语义 tokens、按平台映射。首版由小型平台适配读取 JSON，没有安装或引入该构建系统。 |
| [Sun Valley ttk theme · 16a9ccc](https://github.com/rdbende/Sun-Valley-ttk-theme/tree/16a9ccca67d9e64f8b77bf189e854c2131073dae) | 2025-06-08 | [MIT](https://github.com/rdbende/Sun-Valley-ttk-theme/blob/16a9ccca67d9e64f8b77bf189e854c2131073dae/LICENSE) | ttk 明暗主题及控件状态的参考；没有搬用 Tcl 主题、图像资源或 Python 实现。上游说明主题主要适用于 ttk，普通 Tk 控件不会自动获得同样外观。 |
| [ttkbootstrap · 37d7b35](https://github.com/israel-dryer/ttkbootstrap/tree/37d7b3584b8f3b70671b30f798b0e30378ae1190) | 2026-09-12 | [MIT](https://github.com/israel-dryer/ttkbootstrap/blob/37d7b3584b8f3b70671b30f798b0e30378ae1190/LICENSE) | 语义样式、明暗主题和示例组织方式；没有复制主题/控件实现或增加运行依赖。 |
| [Material Components Android · 66b0eeb](https://github.com/material-components/material-components-android/tree/66b0eeb53afeb6025ffbbd37734b08e5bce197ed) | 2026-10-16 | [Apache-2.0](https://github.com/material-components/material-components-android/blob/66b0eeb53afeb6025ffbbd37734b08e5bce197ed/LICENSE) | Views 控件状态、主题和 `catalog` 示例目录的组织参考；没有引入 Material 控件库。上游已进入维护模式，未归档，README 明确不再计划 Views 功能版本；现有 Views 示例因此保留为独立平台实现。 |

方法说明可参阅 [shadcn registry](https://ui.shadcn.com/docs/registry)、[GitHub registry](https://ui.shadcn.com/docs/registry/github)、[Storybook 仓库](https://github.com/storybookjs/storybook)和 [Style Dictionary 官方说明](https://styledictionary.com/)。Web 组件分发、交互展示和打包可在实际需求出现后逐步接入。

## 构建与 CI 工具依赖

以下固定提交由 GitHub Actions 校验流程引用，用于检出源码和配置构建环境，属于**构建/CI 工具依赖**，不属于 UI 运行依赖。本仓库没有复制或再分发这些工具的源码或二进制；其自身及传递依赖仍使用各自许可。

| 工具与固定提交 | 用途 | 上游许可 |
| --- | --- | --- |
| [actions/checkout · 3d3c42e](https://github.com/actions/checkout/tree/3d3c42e5aac5ba805825da76410c181273ba90b1) | 在 GitHub 托管 runner 检出本仓库 | [MIT](https://github.com/actions/checkout/blob/3d3c42e5aac5ba805825da76410c181273ba90b1/LICENSE) |
| [actions/setup-python · 6d4fd22](https://github.com/actions/setup-python/tree/6d4fd22b20465ccc0f7354476588e8df7c9ca0e0) | 配置 Python 校验环境 | [MIT](https://github.com/actions/setup-python/blob/6d4fd22b20465ccc0f7354476588e8df7c9ca0e0/LICENSE) |
| [actions/setup-java · b843ebf](https://github.com/actions/setup-java/tree/b843ebf9b913146b38da2eaa7aeddf76074ae1ad) | 配置 JDK 构建环境 | [MIT](https://github.com/actions/setup-java/blob/b843ebf9b913146b38da2eaa7aeddf76074ae1ad/LICENSE) |
| [gradle/actions · 3f5f9ad](https://github.com/gradle/actions/tree/3f5f9adaf7d9fecd50b5935e54106014257a94e6) | 配置 Gradle 构建环境；CI 设置 `cache-disabled: true` | [LICENSE](https://github.com/gradle/actions/blob/3f5f9adaf7d9fecd50b5935e54106014257a94e6/LICENSE)声明主体 MIT，并附带单独许可的专有缓存组件；详见下文 |

`gradle/actions` 的 [DISTRIBUTION.md](https://github.com/gradle/actions/blob/3f5f9adaf7d9fecd50b5935e54106014257a94e6/DISTRIBUTION.md)、[NOTICE](https://github.com/gradle/actions/blob/3f5f9adaf7d9fecd50b5935e54106014257a94e6/NOTICE)和 [缓存组件许可](https://github.com/gradle/actions/blob/3f5f9adaf7d9fecd50b5935e54106014257a94e6/licenses/gradle-actions-caching-license.txt)区分 MIT 的 action/basic caching 与专有 enhanced caching。官方说明在禁用缓存或使用 basic caching 时，不加载或使用专有缓存组件。本项目仅在 GitHub 托管 CI 引用该工具，禁用缓存，不把整个上游标为 MIT-only，也不把其组件纳入 UI 源码分发。

## 运行依赖与后续更新

- Tkinter 示例使用 Python 与其 Tk/ttk 接口；Android 示例使用 Android 平台 Views API。具体支持范围与构建环境以各平台说明为准。
- Python/Tk、Android SDK、构建工具各有自己的许可；源码示例没有把这些环境的软件二进制打包进仓库。上表的方法参考项目不能据此被误列为运行依赖。
- 后续实质复制或改编外部代码/资源时，先核对具体文件、固定版本与许可，更新本记录及第三方声明，保留原有版权/许可/NOTICE 和必要的修改说明。
- 新增平台先复用规范与 tokens，再按该平台实现；共享设计值不代表 Tkinter、Android Views 与 Web 组件实现可以直接互换。

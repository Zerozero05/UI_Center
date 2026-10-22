# 许可与第三方声明

UI_Center 的代码采用 **GNU Affero General Public License version 3 only（SPDX：AGPL-3.0-only）**。完整许可见 [LICENSE](LICENSE)。本文件记录实际源码改编与方法参考，不替代上游许可。

## 已有源码的改编与署名

以下原项目由 **Zerozero05** 维护，原始许可均为 GNU AGPL v3。改编文件保留来源与固定提交，继续采用 AGPL-3.0-only。

| 原项目与固定提交 | 实际采用内容 | 本项目位置 |
| --- | --- | --- |
| [Zerozero05/PDF_Bookmarks@0097a07ba494e3376fab680e880bf2d2a1ced66c](https://github.com/Zerozero05/PDF_Bookmarks/tree/0097a07ba494e3376fab680e880bf2d2a1ced66c) | `ui_theme.py` 的 ttk 主题与刷新策略；移除 PDF 专属逻辑，改读共享 tokens | `components/tkinter/ui_center/theme.py` |
| [Zerozero05/PDF_Bookmarks_Android@b44ab5d14e547fef4b80e9469b7c8eb503e2302e](https://github.com/Zerozero05/PDF_Bookmarks_Android/tree/b44ab5d14e547fef4b80e9469b7c8eb503e2302e) | `UiAppearance.java`、`MainActivity.java`、`TaskOutcome.java` 的主题、操作组、状态呈现与阶段结果；泛化为独立 UI 组件及任务状态 | `components/android/src/main/java/cn/local/uicenter/` 下的 `UiTheme.java`、`ActionGroup.java`、`TaskPanel.java`、`TaskState.java` |

本项目的 [LICENSE](LICENSE)逐字节保留自桌面原项目固定提交的 [LICENSE.txt](https://github.com/Zerozero05/PDF_Bookmarks/blob/0097a07ba494e3376fab680e880bf2d2a1ced66c/LICENSE.txt)。Android 原项目该固定提交的 [LICENSE](https://github.com/Zerozero05/PDF_Bookmarks_Android/blob/b44ab5d14e547fef4b80e9469b7c8eb503e2302e/LICENSE)为相同内容。更详细的原始文件、采用范围与本地修改见 [来源记录](references/sources.md)。

## 方法参考项目

shadcn/ui、Storybook、Style Dictionary、Sun Valley ttk theme、ttkbootstrap、Material Components Android 仅用于方法参考。当前没有将其源码、模板、图片、图标、字体或其他资源纳入本项目，也没有引入其运行库。

这些项目的原始许可、固定提交及具体借鉴内容列在 [来源记录](references/sources.md#外部开源项目的方法参考)。它们的上游许可不会被本仓库的 AGPL 声明替换。来源名称不表示其作者认可、参与或支持本项目。

## 构建与 CI 工具引用

GitHub Actions 流程按固定提交使用 `actions/checkout`、`actions/setup-python`、`actions/setup-java` 和 `gradle/actions`。这些是构建/CI 工具依赖，不是 UI 运行依赖；本仓库没有复制或再分发其工具代码/二进制。前三项上游使用 MIT 许可；具体提交和完整许可链接见[工具来源](references/sources.md#构建与-ci-工具依赖)。

仅针对已确认 v1.0.0 的源码发布任务使用 runner 预装的 GitHub CLI（MIT），实际工具版本记录在该次流程日志；来源链接见同一来源说明。不随源码包分发 CLI 二进制。

`gradle/actions` 的[完整许可](https://github.com/gradle/actions/blob/3f5f9adaf7d9fecd50b5935e54106014257a94e6/LICENSE)声明主体 MIT，同时包含单独许可的专有 `gradle-actions-caching` 组件，不能将整个上游概括为 MIT-only。其 [DISTRIBUTION.md](https://github.com/gradle/actions/blob/3f5f9adaf7d9fecd50b5935e54106014257a94e6/DISTRIBUTION.md)和 [NOTICE](https://github.com/gradle/actions/blob/3f5f9adaf7d9fecd50b5935e54106014257a94e6/NOTICE)说明缓存禁用时不加载或使用该专有组件；本项目的托管 CI 设置 `cache-disabled: true`。构建工具的许可不会替换 UI_Center 源码的 AGPL-3.0-only。

以后引入外部代码、资源或二进制时，应按实际采用部分补充原始版权和许可文本；适用时保留 NOTICE 并注明修改。Python/Tk、Android 平台和构建工具的环境许可由各自发行方提供；本项目不随源码示例分发这些工具的二进制。

# UI_Center

个人 UI 规范与源码复用中心。用于在优化程序界面时，先查适用原则和案例，再复制当前技术栈的实现。首版覆盖 **Python Tkinter/ttk** 与 **Java Android Views**，使用同一份设计参数；自有及改编代码采用 **AGPL-3.0-only**。

当前源码为 **v1.2.0 候选组件工作台**，新增18项真实 Tkinter 控件、中文用法与独立源码示例，保留已有规范和两端源码。候选仍在验收，当前正式运行版是 [v1.1.0](https://github.com/Zerozero05/UI_Center/releases/tag/v1.1.0)。

这里借鉴 shadcn/ui 的源码分发组织、Storybook 的状态示例、Style Dictionary 的参数共享，以及 Sun Valley、ttkbootstrap 和 Material Components Android 的主题/控件方法。实际采用内容、固定提交、改编文件及许可见[来源说明](references/sources.md)和[第三方通知](THIRD_PARTY_NOTICES.md)。这些外部 UI 库没有作为运行依赖引入。

## 按需要查找

| 需要解决的问题 | 入口 |
| --- | --- |
| 层次、留白、主次操作、反馈、焦点、主题 | [UI 设计规范](docs/design-guide.md) |
| 文件选择、表单、任务、结果、设置、确认 | [六类交互模式](docs/patterns.md) |
| Tkinter 界面复用 | [桌面组件](components/tkinter/README.md) · [可运行示例](examples/tkinter/README.md) |
| Spinner、条形/环形进度、骨架屏、扫光、加载按钮、区域加载层 | [7项加载组件](docs/components/loading.md) |
| 普通/确认弹窗、抽屉、气泡面板、工具提示 | [5项弹层组件](docs/components/overlays.md) |
| 标签页、折叠面板、分段选择、行内提示、轻通知、空状态 | [6项导航与反馈组件](docs/components/navigation-feedback.md) |
| 原生 Android 界面复用 | [Android 组件](components/android/README.md) · [可运行示例](examples/android/README.md) |
| 颜色、间距、字号的统一来源 | [设计参数](tokens/design-tokens.json) · [映射说明](tokens/README.md) |
| 从现有程序提炼了什么 | [案例及兼容边界](docs/cases.md) |
| 在其他程序中采用、升级源码 | [复制与更新](docs/consumption.md) |
| 实际验证及未测范围 | [验证记录](VALIDATION.md) |

## Windows 11 运行版

v1.2.0 候选将浏览器扩展为 **组件工作台**：组件优先检索、内嵌实时预览与参数操作、中文用途与边界、当前参数示例及完整源码入口。规范仅显示一份原文，原有 Tkinter/Android 条目各自绑定精确用法。Web/Android 的组件映射属于适配建议，本轮没有新建对应平台实现。

新增暖纸/灰绿护眼配色，保留浅色/深色。默认正文12pt，可选100% / 125% / 150%字号和减少动画。仅主题、字号、动画设置保存在运行目录之外；当前预览参数随外观切换保留。偏好位置、源码依赖和实际操作见[工作台说明](docs/desktop-browser.md)。

运行包统一放在 [GitHub Releases](https://github.com/Zerozero05/UI_Center/releases)，同一版本提供以下附件：

| 附件 | 用途 |
| --- | --- |
| `UI_Center_v1.1.0_Windows_x64_Portable.zip` | 推荐日常使用。解压整个目录后运行 `UI_Center.exe`，保留旁边的 `_internal` |
| `UI_Center_v1.1.0_Windows_x64.exe` | 单文件运行；启动时释放临时运行文件，无需自行安装 Python |
| `UI_Center_v1.1.0_Source.zip` | 完整源码、规范、测试、构建脚本和许可，供开发与复用 |
| `SHA256SUMS` | 对应附件的 SHA-256 校验值 |

运行包只包含必需的 Python/Tcl/Tk、只读内容及许可，不包含 Android 工具链、开发缓存或本机工作记录。实际冻结验证状态见 [VALIDATION](VALIDATION.md)；使用流程、目录及升级建议见 [浏览器说明](docs/desktop-browser.md)。

上表仍是已发布的v1.1.0附件。v1.2.0候选的兼容性、拟交付物及未测范围见[候选说明](docs/releases/v1.2.0.md)；完成实际冻结验收和本次发布确认后才提供新版附件。

## 源码快速开始

浏览器源码入口（包含 Tcl/Tk 的 Python 3.10+）：

```console
python apps/desktop/main.py
```

### Tkinter

需要包含 Tcl/Tk 的 Python 3.10+。在仓库根目录运行：

```console
python examples/tkinter/demo.py
```

示例使用虚构数据和模拟任务；开始、取消、主题和结果反馈不处理任何真实文献。

### Android

使用 JDK 17、Android SDK 35、Gradle 8.9；具体构建命令与安装方式见[Android 示例说明](examples/android/README.md)。示例应用 ID 独立，不覆盖来源应用。组件只依赖系统 Android Views，构建时直接打包仓库内的同一份 JSON 参数。

## 在 UI 优化任务中使用

1. 先读取目标项目的说明、原界面行为与已确认要求。
2. 提供本仓库链接和选定的提交；从上表找到对应平台、场景。
3. 阅读模式、源码及适用边界，明确本次采用内容；项目专属决定保留在目标项目。
4. 修改目标界面后，在目标程序实际验证。将可通用的改进反馈到本中心，再由其他程序按需采用。

例如：`参考 UI_Center 的指定提交，按 Tkinter 任务模式优化操作区；保留原文件处理和配置行为，说明采用内容并验证开始、取消、完成及错误反馈。`

## 支持范围与维护

首版提供规范、源码复制和两端独立示例。Python 与 Java 的实现分别维护；共享语义参数及交互规则。Web、组件包与批量源码 registry 在出现实际消费者后扩展。来源程序保持各自的业务、配置和发布节奏。

首版以 **Windows 11 桌面使用与实际验收**为准。Android 源码与已通过的构建检查保留，设备运行验收安排在后续；当前不能据此认定 Android 界面已实测。

复制时保留来源提交、版权与许可；更新时比较本地修改。[复用步骤](docs/consumption.md)也说明独立消费验证。示例展示不等于目标程序或所有设备已通过验证，实际范围以验证记录为准。

## 更新日志

| 日期 | 涉及内容 | 主要变更 |
| --- | --- | --- |
| 2026-10-23 | v1.2.0 组件工作台（候选） | 1、新增18项真实组件及中文用法、参数示例和按条目分发的预览。<br>2、修复重复说明，增加护眼配色、字号、减少动画和外置偏好；保留原接口与平台边界。<br>3、扩展独立消费、生命周期和打包门禁验证，正式发行仍需具体确认。<br>[本次完整记录](CHANGELOG.md#v120-2026-10-23) |
| 2026-10-23 | v1.1.0 公开附件核验（文档） | 1、正式运行包独立下载校验，与批准候选字节一致。<br>2、两包再次各15项本机检查通过；完整源码77文件与标签逐项一致，补齐体积、哈希及未测边界。<br>[本次完整记录](CHANGELOG.md#release-verification-2026-10-23) |
| 2026-10-23 | 测试隔离修复 | 1、使用原子创建的唯一测试目录，修复 Windows 时间戳目录重名。<br>2、三个发行证据检查保持原断言通过；不改变运行行为、依赖、版本或已批准候选二进制。<br>[本次完整记录](CHANGELOG.md#test-isolation-2026-10-23) |
| 2026-10-23 | v1.1.0 浏览器与 Windows 运行版 | 1、新增离线规范/组件检索、源码用法复制及真实桌面预览。<br>2、提供约10MiB的便携 ZIP 与单文件 EXE，统一资源、版本、许可和冻结验证。<br>[本次完整记录](CHANGELOG.md#v110-2026-10-23) |
| 2026-10-23 | v1.0.0 首次源码发行 | 1、提供首个正式源码版及校验文件。<br>2、仅对已确认的 v1.0.0 标签，在两端检查通过后核对附件并发布。<br>[本次完整记录](CHANGELOG.md#v100-2026-10-23) |
| 2026-10-23 | 源码上传与云端核验（未发行） | 1、上传源码并核对全部 46 个远端文件，仓库已公开。<br>2、Windows 测试、Android 构建与状态检查在 GitHub Actions 通过。<br>3、文档检查排除生成目录，统一源码验证范围。<br>[本次完整记录](CHANGELOG.md#remote-2026-10-23) |
| 2026-10-23 | 首版验收范围（文档更新，未发行） | 1、确认 Windows 11 优先的首版验收范围。<br>2、保留 Android 源码及构建结果，设备验收后延并继续标明未测。<br>[本次完整记录](CHANGELOG.md#scope-2026-10-23) |
| 2026-10-23 | 首次建设（未发行） | 1、建立 UI 规范、六类模式、案例与共享设计参数。<br>2、提供 Tkinter/ttk 和 Java Android Views 源码及独立模拟示例。<br>3、整理固定来源、许可、复制与验证流程。<br>[本次完整记录](CHANGELOG.md#initial-2026-10-23) |

[查看全部完整更新记录](CHANGELOG.md)。

## 许可

自有及由既有 AGPL 程序改编的源码、说明采用 [GNU AGPL v3](LICENSE)，详见[第三方通知](THIRD_PARTY_NOTICES.md)。正式版本见[发行页](https://github.com/Zerozero05/UI_Center/releases)，首版内容与使用方式见 [v1.0.0 发行说明](docs/releases/v1.0.0.md)。

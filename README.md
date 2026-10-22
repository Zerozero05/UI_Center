# UI_Center

个人 UI 规范与源码复用中心。用于在优化程序界面时，先查适用原则和案例，再复制当前技术栈的实现。首版覆盖 **Python Tkinter/ttk** 与 **Java Android Views**，使用同一份设计参数；自有及改编代码采用 **AGPL-3.0-only**。

这里借鉴 shadcn/ui 的源码分发组织、Storybook 的状态示例、Style Dictionary 的参数共享，以及 Sun Valley、ttkbootstrap 和 Material Components Android 的主题/控件方法。实际采用内容、固定提交、改编文件及许可见[来源说明](references/sources.md)和[第三方通知](THIRD_PARTY_NOTICES.md)。这些外部 UI 库没有作为运行依赖引入。

## 按需要查找

| 需要解决的问题 | 入口 |
| --- | --- |
| 层次、留白、主次操作、反馈、焦点、主题 | [UI 设计规范](docs/design-guide.md) |
| 文件选择、表单、任务、结果、设置、确认 | [六类交互模式](docs/patterns.md) |
| Tkinter 界面复用 | [桌面组件](components/tkinter/README.md) · [可运行示例](examples/tkinter/README.md) |
| 原生 Android 界面复用 | [Android 组件](components/android/README.md) · [可运行示例](examples/android/README.md) |
| 颜色、间距、字号的统一来源 | [设计参数](tokens/design-tokens.json) · [映射说明](tokens/README.md) |
| 从现有程序提炼了什么 | [案例及兼容边界](docs/cases.md) |
| 在其他程序中采用、升级源码 | [复制与更新](docs/consumption.md) |
| 实际验证及未测范围 | [验证记录](VALIDATION.md) |

## 快速开始

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
| 2026-10-23 | 源码上传与云端核验（未发行） | 1、上传源码并核对全部 46 个远端文件，仓库已公开。<br>2、Windows 测试、Android 构建与状态检查在 GitHub Actions 通过。<br>3、文档检查排除生成目录，统一源码验证范围。<br>[本次完整记录](CHANGELOG.md#remote-2026-10-23) |
| 2026-10-23 | 首版验收范围（文档更新，未发行） | 1、确认 Windows 11 优先的首版验收范围。<br>2、保留 Android 源码及构建结果，设备验收后延并继续标明未测。<br>[本次完整记录](CHANGELOG.md#scope-2026-10-23) |
| 2026-10-23 | 首次建设（未发行） | 1、建立 UI 规范、六类模式、案例与共享设计参数。<br>2、提供 Tkinter/ttk 和 Java Android Views 源码及独立模拟示例。<br>3、整理固定来源、许可、复制与验证流程。<br>[本次完整记录](CHANGELOG.md#initial-2026-10-23) |

[查看全部完整更新记录](CHANGELOG.md)。

## 许可

自有及由既有 AGPL 程序改编的源码、说明采用 [GNU AGPL v3](LICENSE)，详见[第三方通知](THIRD_PARTY_NOTICES.md)。公开源代码仓库与正式版本发行分别管理；首批源码不附带正式版本标签或发行附件。

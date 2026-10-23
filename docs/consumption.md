# 源码复制与更新

## 选择与记录

先从 README 找到平台与场景，选定一个完整 Git 提交。阅读平台说明、设计参数、来源及许可。为消费项目建立简短采用记录：UI_Center 提交、复制文件、参数文件版本、用途、本地调整及验证结果。

复制源码后由消费项目维护；上游变化不会自动改动应用。保留每份源码的 SPDX/来源标记、AGPL 完整许可和实际适用的版权通知。

## Tkinter 消费

复制整个 `components/tkinter/ui_center` 目录及 `tokens/design-tokens.json`，将组件父目录加入 Python 导入路径，并显式提供复制后的参数路径。以[平台说明](../components/tkinter/README.md)和对应[组件文档](components/loading.md)中的实际接口为准。包内导出会引用多个模块；只复制单个类文件或示例代码可能遗漏依赖。

v1.2.0 的18个新增组件均为本项目自行实现的 Tk/ttk/Canvas 源码，分布在 `loading.py`、`overlays.py`、`navigation.py`、`feedback.py`，没有新增第三方源码或运行依赖。它们与原有 ActionBar、TaskPanel、theme API 一同保留；桌面工作台不是消费项目必须安装的依赖。

先运行最小示例，再把模拟数据和回调替换为自己的业务。工作台“复制当前参数示例”针对当前内嵌预览生成代码；独立窗口的参数不自动同步到它。后台工作与 UI 主线程交接由应用负责；组件只呈现状态、发出调用者回调，模拟任务仅在预览中。组件不负责文件处理、网络请求或持久业务配置。

调用 `apply_theme(root, mode, tokens_path=...)` 取得 palette，再向新组件传 `palette=palette`。切换颜色时重新应用主题并调用组件的 `apply_palette()`；动画或弹层组件按各自 API 同步 `set_visible()`，支持减少动画的组件在偏好变化时调用 `set_reduced_motion()`。静态组件无需装饰计时器，也不统一要求这些接口。减少动画与隐藏不抹掉真实进度；真实任务是否暂停/取消由消费应用决定。销毁页面时释放组件和调用方自己的计时器/业务资源。

主题支持 `light`、`dark`、`warm`、`sage`；`font_scale` 是 `apply_theme` 的可选倍率，默认1.0保留既有基础字号。桌面工作台以1.2倍率得到默认12pt正文，再提供100% / 125% / 150%选择。消费项目继续采用自身的字号和持久设置，不复制工作台偏好路径。v1.2.1工作台只在EXE旁的data/preferences.json保存主题、字号、动画3项；源码调试隔离到仓库work/data，显式路径优先。

以下结构可直接承载工作台复制的代码：

```text
consumer/
  app.py
  ui_center/
    __init__.py
    theme.py
    widgets.py
    loading.py
    overlays.py
    navigation.py
    feedback.py
  tokens/
    design-tokens.json
```

保留完整包中的其他实际文件及许可；上面的目录说明不是删除清单。

## Android 消费

复制 `components/android/src/main/java/cn/local/uicenter` 内的源码，在消费项目的 assets 中放入同一份 `design-tokens.json`。按[平台说明](../components/android/README.md)建立主题、操作回调和状态渲染。

保留消费项目自己的应用 ID、签名、存储授权及业务生命周期。UI_Center 示例的独立应用身份只用于演示。

## Web 与 Android 的适配边界

本次18个新组件只实现 Tkinter。文档中的其他平台说明是规范映射，不是可直接运行的 Web/Android 新组件；原有 Android ActionGroup、TaskPanel、TaskState 和主题仍按既有平台说明使用。

| 交互职责 | 在目标平台需要实现的内容 |
| --- | --- |
| 等待、进度与占位 | 使用目标平台的进度/状态控件；真实进度来自任务，未知进度明确标注；适配平台动画偏好 |
| 弹窗、抽屉与气泡 | 使用目标平台的窗口或浮层机制，分别处理焦点、取消、外部点击与调用者生命周期 |
| 标签、折叠与互斥选择 | 保持所选值、禁用项和键盘/触控行为；不要把同名 Tk 类当作跨平台实现 |
| 提示、轻通知与空状态 | 呈现持续时间、关闭动作、真实空/错原因和下一步，并适配平台的辅助功能 |

采用相同 tokens 可以统一语义角色，不能保证平台控件像素一致或直接共享实现。新增平台应有自己的源代码、依赖说明和实际验收；本次不新增 Web 工具链，也不扩大 Android 设备实测范围。

## 更新步骤

1. 比较上次采用提交与目标提交，阅读 CHANGELOG 及受影响条目。
2. 对照消费项目的本地修改合并，保持业务接口和持久数据兼容。
3. 配色角色发生变化时同步源码映射与 JSON；不只替换其中一份。
4. 验证受影响的正常、忙碌、取消、完成、失败、长文本、焦点与主题；记录新提交和结果。

## 独立消费验收

在 git-ignored 的隔离消费目录中，只复制约定组件、参数和最小调用方，再启动 Tk 或构建 Android 示例。Tk 使用 `python -I` 且只导入复制品；Android 消费工程不使用跨仓库的 `sourceSets` 路径。检查不存在原仓库路径/PDF/OCR 的隐藏依赖。验证产物保留在工作目录，不自动删除。

稳定实现实际服务至少两个独立项目后，再提取对应平台组件包。Web、Storybook 与源码 registry 由真实消费者需求驱动，分别保持可验证的技术范围。

# 源码复制与更新

## 选择与记录

先从 README 找到平台与场景，选定一个完整 Git 提交。阅读平台说明、设计参数、来源及许可。为消费项目建立简短采用记录：UI_Center 提交、复制文件、参数文件版本、用途、本地调整及验证结果。

复制源码后由消费项目维护；上游变化不会自动改动应用。保留每份源码的 SPDX/来源标记、AGPL 完整许可和实际适用的版权通知。

## Tkinter 消费

复制整个 `components/tkinter/ui_center` 目录及 `tokens/design-tokens.json`，将组件父目录加入 Python 导入路径，并显式提供复制后的参数路径。以[平台说明](../components/tkinter/README.md)中的实际接口为准。

先运行最小示例，再把模拟数据和回调替换为自己的业务。后台工作与 UI 主线程交接由应用负责；主题只调整该应用拥有的控件。

## Android 消费

复制 `components/android/src/main/java/cn/local/uicenter` 内的源码，在消费项目的 assets 中放入同一份 `design-tokens.json`。按[平台说明](../components/android/README.md)建立主题、操作回调和状态渲染。

保留消费项目自己的应用 ID、签名、存储授权及业务生命周期。UI_Center 示例的独立应用身份只用于演示。

## 更新步骤

1. 比较上次采用提交与目标提交，阅读 CHANGELOG 及受影响条目。
2. 对照消费项目的本地修改合并，保持业务接口和持久数据兼容。
3. 配色角色发生变化时同步源码映射与 JSON；不只替换其中一份。
4. 验证受影响的正常、忙碌、取消、完成、失败、长文本、焦点与主题；记录新提交和结果。

## 独立消费验收

在 git-ignored 的隔离消费目录中，只复制约定组件、参数和最小调用方，再启动 Tk 或构建 Android 示例。Tk 使用 `python -I` 且只导入复制品；Android 消费工程不使用跨仓库的 `sourceSets` 路径。检查不存在原仓库路径/PDF/OCR 的隐藏依赖。验证产物保留在工作目录，不自动删除。

稳定实现实际服务至少两个独立项目后，再提取对应平台组件包。Web、Storybook 与源码 registry 由真实消费者需求驱动，分别保持可验证的技术范围。

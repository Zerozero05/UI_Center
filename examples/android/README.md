# Android 独立示例

纯 Java + 原生 Android Views。应用 ID 为 `cn.local.uicenter.demo`，与原 PDF 程序不同。示例不请求文件、存储、网络或其他敏感权限，所有任务与结果均为虚构数据。

演示主次操作、参数校验、长文本、明暗主题、六步任务、取消、失败和重试。切换主题保留校验提示、输入内容与选择范围、控件焦点、滚动和任务结果；旋转使用同组快照恢复。任务每 600ms 模拟一步，切到后台时暂停模拟。真实后台工作不应照搬此 Handler 示例的生命周期策略。

## 构建

需要 JDK17、Gradle8.9、Android SDK35、Build-tools35.0.0 和 AGP8.7.3。没有内置 Gradle Wrapper；避免运行会自动下载依赖的命令。已有完整工具链和缓存时：

```powershell
./build.ps1 -ToolingRoot '<已有工具目录>'
```

该目录需有 `jdk/<JDK17目录>`、`gradle/gradle-8.9`、`sdk` 和含依赖的 `gradle-home/caches/modules-2`。脚本强制 `--offline`，只读复用依赖；本次新缓存位于根 `work/android`，常规构建输出位于 `app/build`。脚本恢复调用者环境变量。缺少工具或缓存时应先按使用者保存位置规则准备环境，不自动下载。

其他已有环境可以直接设置 `JAVA_HOME`、`ANDROID_HOME`、适合本任务的 `GRADLE_USER_HOME` 后运行：

```text
gradle --offline assembleDebug lintDebug assembleDebugAndroidTest
```

`app/build/outputs/apk/debug/app-debug.apk` 是调试试用包；无正式发行签名或 Release。`app/build/reports/lint-results-debug.html` 是静态检查报告。`build.ps1` 还运行 `tests/android/TaskStateTest.java` 的宿主 JVM 回归。

本项目的 Gradle `sourceSets` 从根组件目录编译代码，并直接把根 `tokens/` 加入 assets，因此 APK 实际包含 `design-tokens.json`，不维护另一份 tokens。独立消费项目应按[复制指南](../../components/android/README.md)导入源码与所选提交的 tokens 快照。

## 设备验证

本节保留为后续验收步骤，不阻塞 Windows 11 优先的首版交付；当前设备运行未测，构建通过不能替代实际运行验证。

只在已授权设备上安装此独立 ID 的示例和测试包：

```text
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb install -r app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
adb shell am instrument -w cn.local.uicenter.demo.test/cn.local.uicenter.demo.DemoSmoke
```

平台自带的 smoke runner 检查空输入、切主题后保留校验提示/选择/焦点/非零滚动位置、长文本、运行时按钮、旋转恢复、取消后保留结果、模拟失败、重试和成功。运行结果需明确包含 `UI Center Android device smoke passed`，仅生成测试 APK 不能算执行通过。

再手动核对横竖屏、系统大字号、键盘/返回、系统栏、输入法以及长结果的滚动与选取。触控目标不低于48dp，按钮竖排避免窄屏双按钮互相挤占。自动 smoke 通过仍不代表所有设备视觉验收通过。

## 维护

通用组件来源与许可见[Android 组件说明](../../components/android/README.md)；实际检查证据见[验证记录](../../VALIDATION.md)。示例使用四个组件的公开接口；自身不应引入原应用业务和运行依赖。变更应同步示例、来源及验证记录。不要更改独立应用 ID 来覆盖其他应用。

Windows 现有环境还可运行 `tests/android/source-copy.ps1 -ToolingRoot '<已有工具目录>'`，它在 `work/android` 创建独立消费工程，复制四个组件与 tokens 快照后离线构建和 lint。消费工程不含指向本仓组件的 `sourceSets` 路径。

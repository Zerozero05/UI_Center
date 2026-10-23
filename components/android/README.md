# Android Java Views

独立的原生 Views 源码组件。当前不提供 Maven 包；适用于 `minSdk 26` 及以上项目，示例采用 JDK17、Android SDK35。仅依赖 Android 平台与 Java 标准库，无 AndroidX、Material、PDF 或 OCR 依赖。

## 条目与接口

| 条目 | 使用方法 | 输入与职责 |
| --- | --- | --- |
| `UiTheme` | `UiTheme.fromAssets(context, dark)` | 从 `design-tokens.json` 读取颜色、间距、字号和圆角；`button/input/text/systemBars` 应用于宿主控件；不读写应用偏好 |
| `ActionGroup` | `new ActionGroup(context, theme, label, onStart, onCancel)` | 主操作及取消回调；`setRunning(boolean)` 同步禁用状态；竖排容纳长文本及大字号 |
| `TaskState` | `start(title, total)`，`advance(result)`，`fail(message)`，`cancel()` | 与 Android 无关的界面状态；保留已完成结果；终态拒绝迟到更新；宿主恢复实际任务后才能 `restore(...)` |
| `TaskPanel` | `new TaskPanel(context, theme)`，`render(state)` | 显示进度、明确的完成/取消/错误文字及逐项结果；不启动工作线程、不访问文件 |

状态由宿主在主线程中管理。业务操作与取消信号属于宿主；界面 `cancel()` 不能替代实际取消。新任务会清空上次结果，取消/失败保留本次已完成项。真实后台长任务应使用自己项目已有的任务/持久恢复机制。

## 复制到其他 Android 项目

1. 在本仓选定完整 Git 提交，记录在消费项目的来源文件中。
2. 将 `src/main/java/cn/local/uicenter/` 下四个 Java 文件复制到消费项目的 `app/src/main/java/cn/local/uicenter/`。保留包名、版权头和 AGPL 声明。
3. 将仓库根的 `tokens/design-tokens.json` 复制到消费项目 `app/src/main/assets/design-tokens.json`。这是跟随所选来源提交的消费快照，编辑参数应回到中心的唯一真源，重新复制。
4. 把根 `LICENSE` 和相关来源记录一并保留。记录所选提交、复制文件、当地调整和验证范围；不要把复制项当作自动更新依赖。
5. 在 Activity 建立组件：

```java
UiTheme theme = UiTheme.fromAssets(this, false);
TaskState state = new TaskState();
TaskPanel panel = new TaskPanel(this, theme);
ActionGroup actions = new ActionGroup(this, theme, "开始任务", () -> {
    state.start("示例", 2);
    panel.render(state);
    // 在此调用消费程序已有任务入口；完成/进度回主线程再更新状态。
}, () -> {
    // 先向宿主真实任务发送取消，确认后再调用 state.cancel()。
});
```

将 `actions`、`panel` 加入现有布局；每次状态变化调用 `actions.setRunning(state.isRunning())` 和 `panel.render(state)`。宿主自行处理重建时的状态保存，参考[独立示例](../../examples/android/README.md)。`UiTheme.systemBars(activity)` 需要在 `setContentView` 后调用；宿主仍负责 WindowInsets，避免内容被系统栏遮挡。

## android-theme

UiTheme读取同一设计参数，明确应用到Activity内控件。现有Android适配仍采用light/dark两主题；桌面新增主题不代表Android已经支持同样的设备外观。以下片段位于Activity创建界面时，设备运行仍未验收。

<!-- example:android-theme -->
```java
UiTheme theme = UiTheme.fromAssets(this, false);
TextView heading = new TextView(this);
heading.setText("主题示例");
theme.text(heading, "heading");
setContentView(heading);
theme.systemBars(this);
```

## android-actions

ActionGroup使用调用方提供的开始/取消回调；setRunning控制防重复操作。以下片段位于Activity创建界面时，真实业务由宿主实现。

<!-- example:android-actions -->
```java
UiTheme theme = UiTheme.fromAssets(this, false);
ActionGroup actions = new ActionGroup(this, theme, "开始任务",
    () -> { /* 调用宿主的开始入口 */ },
    () -> { /* 请求宿主取消 */ });
actions.setRunning(false);
setContentView(actions);
```

## android-state

TaskState与TaskPanel组合显示任务生命周期。下面是虚构数据的状态演示，所有UI更新必须在主线程进行；终态不会接收迟到进度。

<!-- example:android-state -->
```java
UiTheme theme = UiTheme.fromAssets(this, false);
TaskState state = new TaskState();
TaskPanel panel = new TaskPanel(this, theme);
state.start("虚构示例", 2);
state.advance("示例A");
panel.render(state);
setContentView(panel);
```

## 来源与改编

源代码改编自 Zerozero05/PDF_Bookmarks_Android，固定提交 [`b44ab5d14e547fef4b80e9469b7c8eb503e2302e`](https://github.com/Zerozero05/PDF_Bookmarks_Android/tree/b44ab5d14e547fef4b80e9469b7c8eb503e2302e)。

- `UiTheme.java`：改编 `app/src/main/java/cn/local/pdfbookmarks/UiAppearance.java` 的原生状态样式、触控目标、系统栏延迟设置；改为 JSON tokens，移除偏好与原应用资源。
- `ActionGroup.java`、`TaskPanel.java`：改编 `MainActivity.java` 的 `button/styleButton/card/renderOutcome` 模式；改为回调与通用状态，删除全部 PDF/文件业务。
- `TaskState.java`：改编 `TaskOutcome.java` 的结果快照与状态管理；改为通用进度、取消和恢复接口。

许可为 AGPL-3.0-only，详见[完整来源](../../references/sources.md)及[第三方说明](../../THIRD_PARTY_NOTICES.md)。示例与测试为本次新编内容。当前构建/检查证据和设备验证限制见[验证记录](../../VALIDATION.md)。

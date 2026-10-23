# 设计参数与平台映射

唯一手写源是 [design-tokens.json](design-tokens.json)，当前 schema_version 为 1。它是本仓库的小型参数格式，借鉴共享设计参数的方法；不宣称完整实现 DTCG 或 Style Dictionary。

| 区域 | 语义与映射 |
| --- | --- |
| themes.light/dark/warm/sage | 浅色、深色、暖纸、灰绿四套配色共享同一组角色。background/surface 为区域；foreground/muted 为正文/辅助文字；accent 为主动作；selected_background/selected_foreground 为选中配色；其余用于输入、边框、悬停、禁用、焦点和结果状态 |
| spacing | xs/sm/md/lg/xl 为间距级别，Tk 采用布局像素，Android 转 dp；显示缩放仍需各平台验证 |
| typography | body/small/heading 为字号角色，每个角色分别给出 tk_points 与 android_sp；系统字体由平台选择 |
| radii.control | Android 控件圆角 dp；ttk 能力不同，使用其原生主题边界，不承诺像素级一致 |

两端使用相同 JSON。Tk 调用方显式指定文件路径；Android 示例的 assets 源目录指向本文件所在目录，构建产物中会有参数副本，但它不是第二份手写源。复制到独立应用后，参数副本由消费项目按采用提交维护。

Tk 的 `apply_theme(root, mode='light', *, tokens_path=None, font_scale=1.0)` 保留原默认配色/基础字号接口，增加 `warm` / `sage` 与显式字体倍率。JSON 中 `body.tk_points=10` 继续作为共享基础值；桌面工作台采用1.2倍得到默认12pt正文，100% / 125% / 150%选择对应实际倍率1.2 / 1.5 / 1.8、正文12 / 15 / 18pt。它不改写 JSON，不修改 Windows 显示缩放，也不强迫独立消费项目使用工作台字号。

工作台默认 `warm`，仅在 `D:\03_github_projects\UI_Center_Data\preferences.json` 持久保存 `theme`、`font_scale`、`motion`。这些是应用偏好，不是新增设计参数，也不随参数文件复制到消费项目。动画支持跟随系统、正常和减少；装饰计时器与真实任务进度分别管理。主题/字号更新不应重建控件或清空输入、选择和进度。

18个新 Tkinter 组件在自身的 `apply_palette()` 中使用这些语义角色，源码没有引入 Web 主题库。其他平台可按相同角色自行适配，但本次没有新增 Web/Android 的18个组件实现。平台支持范围与设备验证仍以各自文档为准。

添加或删除角色时同步两端映射、对应测试和说明；普通色值调整保持角色名。检查正文、辅助文字和状态文字对区域背景的对比度，焦点可见；禁用状态与系统原生弹窗按真实平台范围单独验证。

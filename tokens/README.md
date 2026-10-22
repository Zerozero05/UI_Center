# 设计参数与平台映射

唯一手写源是 [design-tokens.json](design-tokens.json)，当前 schema_version 为 1。它是本仓库的小型参数格式，借鉴共享设计参数的方法；不宣称完整实现 DTCG 或 Style Dictionary。

| 区域 | 语义与映射 |
| --- | --- |
| themes.light/dark | background/surface 为区域；foreground/muted 为正文/辅助文字；accent 为主动作；selected_background/selected_foreground 为选中配色；其余用于输入、边框、悬停、禁用、焦点和结果状态 |
| spacing | xs/sm/md/lg/xl 为间距级别，Tk 采用布局像素，Android 转 dp；显示缩放仍需各平台验证 |
| typography | body/small/heading 为字号角色，每个角色分别给出 tk_points 与 android_sp；系统字体由平台选择 |
| radii.control | Android 控件圆角 dp；ttk 能力不同，使用其原生主题边界，不承诺像素级一致 |

两端使用相同 JSON。Tk 调用方显式指定文件路径；Android 示例的 assets 源目录指向本文件所在目录，构建产物中会有参数副本，但它不是第二份手写源。复制到独立应用后，参数副本由消费项目按采用提交维护。

添加或删除角色时同步两端映射、对应测试和说明；普通色值调整保持角色名。检查正文、辅助文字和状态文字对区域背景的对比度，焦点可见；禁用状态与系统原生弹窗按真实平台范围单独验证。

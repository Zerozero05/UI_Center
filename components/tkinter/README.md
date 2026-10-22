# Tkinter / ttk 源码组件

适用于已有 Python Tkinter/ttk 桌面程序。需要 Python 3.10+ 和可用的 Tcl/Tk；运行时只有 Python 标准库，不需要 PDF、OCR、第三方主题或安装器。当前实际验证为 Windows 11、Python 3.12、Tcl/Tk 8.6；其他系统尚未实测。

## 独立运行

在仓库根目录执行：

```powershell
python examples/tkinter/demo.py
```

演示使用虚构项目，可切换明暗主题、设置数量、模拟成功或失败、请求取消和重新开始。不会打开、写入或删除业务文件。项目名称和数量是示例业务参数，组件本身不理解它们。

## 组件与接口

| 入口 | 用途 | 输入与边界 |
| --- | --- | --- |
| `load_tokens(path=None)` | 读取共享设计参数 | 原仓库默认读取 `tokens/design-tokens.json`；独立复制后显式传路径 |
| `apply_theme(root, mode="light", tokens_path=...)` | 明暗主题 | 只在 Tk 主线程调用；作用于该 Tk 解释器中的 ttk 控件，不修改操作系统设置 |
| `ActionBar(master, on_primary=..., on_cancel=..., on_secondary=..., spacing=...)` | 主操作、可选次操作、取消 | 回调由应用实现；`set_busy(busy, cancelling=False)` 防止重复开始并管理按钮状态 |
| `TaskPanel(master, spacing=...)` | 进度、文字反馈、结果列表 | 只显示数据，业务任务、异常处理和取消策略由应用负责 |
| `TaskPanel.set_state(state, completed=0, total=0, message="", results=None)` | 渲染任务状态 | 状态为 `idle/running/cancelling/completed/cancelled/error`；进度满足 `0 <= completed <= total` |

`results` 接收 `(项目显示名, 结果文本)` 序列。传 `None` 保留现有结果；传空序列清空结果。任务状态可通过 `panel.task_state` 读取；保留 ttk 原有的 `state()` / `instate()` 控件接口。选择结果行后，下方只读字段保留完整名称与结果，支持键盘移动和复制长文本。所有状态均有文字说明，不只依靠颜色。未知总数时可传 `completed=total=0`，显示文字反馈；首版不包含不定进度动画。

主题映射读取语义颜色、`spacing` 和 `typography.*.tk_points`。两组件的 `spacing` 参数接收该 JSON 中的间距映射；省略时读取仓库根目录的共享 JSON。独立复制或使用自定义 tokens 路径时，显式传入 `load_tokens(自有路径)["spacing"]`，让内部按钮间距、进度区和反馈区间距与主题保持同一来源。间距在创建组件时应用，修改后重新创建组件。字体族沿用当前平台的 `TkDefaultFont`；Android 的 sp 值不直接作为桌面字号。ttk clam 的矩形控件不支持统一圆角，因此 `radii.control` 不在本适配器生效。原生文件对话框继续使用系统外观，普通 `tk.Text`/`Canvas` 等需由应用另外适配；本组件主要使用 ttk。

## 复制到自己的程序

将 `ui_center/` 复制到应用的源码目录，将当前选定的 `tokens/design-tokens.json` 复制到应用资源目录；保留仓库许可和 [来源声明](../../THIRD_PARTY_NOTICES.md)。在接入项目记录所用 UI_Center 提交及本地改动，后续通过差异比较升级。

```python
from pathlib import Path
import tkinter as tk
from ui_center import ActionBar, TaskPanel, apply_theme, load_tokens

root = tk.Tk()
token_path = Path(__file__).parent / "design-tokens.json"
spacing = load_tokens(token_path)["spacing"]
apply_theme(root, "dark", tokens_path=token_path)
panel = TaskPanel(root, spacing=spacing)
panel.pack(fill="both", expand=True)

def preview():
    panel.set_state("completed", completed=1, total=1,
                    message="已预览示例；具体业务由应用实现。",
                    results=[("虚构项目", "预览完成")])

actions = ActionBar(root, primary_text="预览", on_primary=preview,
                    on_cancel=lambda: None, spacing=spacing)
actions.pack(fill="x")
root.mainloop()
```

主题切换重复调用 `apply_theme`；当前输入、结果及焦点不会被重建。`ActionBar` 不自动控制其他输入框，应用在任务开始/结束时管理这些状态。

实际耗时任务应在工作线程运行，通过队列把进度交回 Tk 主线程；不要从线程访问 Tk 控件。取消要由业务在安全边界检查请求，收到请求后先显示 `cancelling`，确认结束再显示 `cancelled`。示例使用 `after` 模拟短步骤，仅用于展示状态；关闭时取消尚未执行的回调。

## 真实验证与限制

```powershell
python -B -m unittest discover -s tests -p test_tkinter_ui.py -v
```

测试实际创建 Tk 窗口和控件，覆盖主题/输入/焦点保持、Tab 和空格、忙碌禁用、成功、取消、保留部分结果、失败后重试、参数校验、小窗口长反馈、关闭清理和独立源码消费。需要可用桌面环境，无法加载 Tk 时测试会失败，不会把该场景算作通过。

独立消费测试复制代码和 JSON 到 `work/desktop/source-copy-*` 后，使用 `python -I` 隔离启动，仅导入复制品；测试产物保留以便核对。此测试不证明冻结 EXE、系统原生对话框、多屏、所有 DPI 或其他操作系统已经通过。可手动验证：Tab/Shift+Tab 和空格、明暗、缩小窗口、长项目名、取消后重试和关闭运行中的演示。

## 来源与本地改动

- **源码改编**：[PDF_Bookmarks/ui_theme.py](https://github.com/Zerozero05/PDF_Bookmarks/blob/0097a07ba494e3376fab680e880bf2d2a1ced66c/ui_theme.py)，提交 `0097a07ba494e3376fab680e880bf2d2a1ced66c`，原许可 GNU AGPL v3。采用 L12–34、L53–154、L190–237、L257–297 的语义配色、clam 样式、主题注册和已有控件刷新策略。配色改从统一 JSON 读取，样式独立命名，补充状态文字样式；未采用 PDF 专有标记、图标、护眼主题和工具提示。
- **方法参考**：同提交 [bookmarks_gui.py](https://github.com/Zerozero05/PDF_Bookmarks/blob/0097a07ba494e3376fab680e880bf2d2a1ced66c/bookmarks_gui.py) 的操作分组 L171–185、主线程反馈 L1276–1337。`widgets.py` 与演示独立编写，没有复制 PDF/OCR/写入逻辑。
- 自有及改编源码采用 AGPL v3；完整分类与其他上游见 [来源记录](../../references/sources.md)。原应用未作修改。

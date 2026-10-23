# Tk 弹层组件

五种组件均在 Tk 主线程调用，只依赖 Python 标准库 `tkinter` / `ttk` 和本仓库主题。源码为 [overlays.py](../../components/tkinter/ui_center/overlays.py)，预览实现见 [previews_overlays.py](../../apps/desktop/previews_overlays.py)。复制 `ui_center/` 与 `tokens/design-tokens.json` 到自己的程序，保留 [许可与来源](../../THIRD_PARTY_NOTICES.md)。下面示例以脚本旁的 `tokens/` 为资源目录。

共同接口：构造器必须传 `palette=apply_theme(...)` 的返回值；`show(trigger=None)` 返回是否成功打开，重复打开会抬升原窗口并返回 `False`；`is_open` 表示是否存在当前 Toplevel；`close(reason="close")` 关闭；`apply_palette(palette)` 原位更新普通 Tk 内容；`set_visible(False)` 关闭并禁止再次打开，恢复 `True` 后需明确 `show()`；`dispose()` 永久停止并解绑本组件。主题切换时同时调用应用的 `apply_theme()` 和组件的 `apply_palette()`，不会重建当前弹层。

`on_close(reason)` 仅在组件的关闭路径调用，常见原因有 `close`、`escape`、`window`、`hidden`、`disposed`。直接从外部销毁 Toplevel 仍会释放内部状态，但不代替调用业务回调。隐藏和销毁均会取消本组件计时器，只释放本组件拥有的 grab；关闭模态子弹层时恢复仍存在的前一个 grab。已有其他模态窗口时，不抢占它；只有从该模态窗口内部的明确触发控件发起，才允许嵌套。

宿主若也使用 Escape（例如清空搜索），应先调用 `close_active_overlay(root)`，返回 `True` 时结束该快捷键处理。组件不调用 `bind_all` / `unbind_all`，不会移除宿主的其他绑定。`active_overlay(root)` 可查询同一 Tk 解释器中最近打开的交互弹层；Tooltip 不参与该栈。

本次组件与示例独立编写，未引入新的外部代码、素材或运行依赖；沿用 [现有来源分类](../../references/sources.md) 与 AGPL-3.0-only 许可。真实自动测试见 [test_overlay_widgets.py](../../tests/test_overlay_widgets.py)。已验证 Windows Tk；其他系统、多屏边界和全部 DPI 不在此处宣称已通过。Toplevel 为平台窗口，不能当作网页中的半透明遮罩。

## dialog

**用途与边界：** `Dialog` 用于需要用户阅读并明确关闭的简短信息。它是模态窗口，不执行任务、不内置文件操作；需要复杂表单时由消费项目决定布局，而不是把业务塞进通用信息框。

**参数：** `Dialog(master, *, palette, title="对话框", message="", close_text="关闭", on_close=None)`。`title` 同时用于窗口标题和内容标题；长 `message` 随当前宽度换行。`show(trigger)` 记录返回焦点的控件，默认使用当前焦点。

**键盘：** 初始焦点位于关闭按钮，Tab / Shift+Tab 在模态弹层内循环；Escape 与系统关闭按钮均关闭弹层并返回触发控件。不会把 Escape 传播成宿主的清空搜索操作。**依赖：** Tk、ttk、共享主题 palette。

<!-- example:dialog -->
```python
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui_center.theme import apply_theme
from ui_center.overlays import Dialog

root = tk.Tk()
root.title("Dialog 示例")
root.geometry("620x420")
palette = apply_theme(root, tokens_path=Path(__file__).parent / "tokens" / "design-tokens.json")
dialog = Dialog(root, palette=palette, title="处理说明",
                message="这里是虚构数据的说明。关闭后回到打开按钮。")
trigger = ttk.Button(root, text="打开对话框", command=lambda: dialog.show(trigger))
trigger.pack(pady=40)
root.protocol("WM_DELETE_WINDOW", lambda: (dialog.dispose(), root.destroy()))
root.mainloop()
```

## confirm-dialog

**用途与边界：** `ConfirmDialog` 发出布尔确认结果，实际操作由 `on_result` 执行。用于用户有明确选择的问题；不要在打开时自动执行确认动作，也不要把确认框当作操作成功证明。

**参数：** `ConfirmDialog(master, *, palette, title="确认操作", message="", confirm_text="确认", cancel_text="取消", on_result=None, on_close=None)`。`result` 每次打开重置为 `None`，关闭后为 `True` / `False`；调用 `confirm()` 或激活确认按钮为 `True`，其他关闭路径为 `False`。一次打开只触发一次 `on_result(bool)`。

**键盘：** 安全默认焦点在取消按钮；直接按 Return 取消，Tab 可移至确认按钮后用 Return / 空格明确确认。Escape、系统关闭、隐藏与销毁均作为取消。焦点循环与返回行为同 Dialog。**依赖：** Tk、ttk、共享主题 palette。

<!-- example:confirm-dialog -->
```python
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui_center.theme import apply_theme
from ui_center.overlays import ConfirmDialog

root = tk.Tk()
root.title("ConfirmDialog 示例")
root.geometry("620x420")
palette = apply_theme(root, tokens_path=Path(__file__).parent / "tokens" / "design-tokens.json")
result = tk.StringVar(root, value="等待选择")
dialog = ConfirmDialog(root, palette=palette, message="确认这次虚构操作？",
                       confirm_text="确认示例操作",
                       on_result=lambda confirmed: result.set("已确认" if confirmed else "已取消"))
trigger = ttk.Button(root, text="请求确认", command=lambda: dialog.show(trigger))
trigger.pack(pady=20)
ttk.Label(root, textvariable=result).pack()
root.protocol("WM_DELETE_WINDOW", lambda: (dialog.dispose(), root.destroy()))
root.mainloop()
```

## drawer

**用途与边界：** `Drawer` 沿所属窗口左侧或右侧展示补充内容。默认右侧、模态，适合暂时独立完成的少量选项；非模态模式允许继续操作主窗口。它是有系统边框的独立侧边窗口，不覆盖宿主布局、不提供自动保存。

**参数：** `Drawer(master, *, palette, title="侧边面板", message="", side="right", modal=True, width=320, reduced_motion=False, content_factory=None, on_close=None)`。`side` 只接受 `left` / `right`；`width` 至少 160，打开时参考宿主宽度限制。`content_factory(content)` 可向内容 Frame 放入调用方控件；每次打开调用一次，关闭时这些控件销毁，持久输入状态应由调用方变量维护。

**动画与键盘：** 默认只做 6 步、每步至少34毫秒（约204毫秒）的有界打开过渡，低于30fps；关闭立即完成。`set_reduced_motion(True)` 取消尚未完成的过渡并立即到终点。模态模式保留 Tab 焦点循环；Escape、关闭按钮和系统关闭入口均可退出并恢复触发焦点。非模态模式允许焦点离开，宿主 Escape 应使用共同快捷键约定。**依赖：** Tk、ttk、共享主题 palette，动画只用 `after`。

<!-- example:drawer -->
```python
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui_center.theme import apply_theme
from ui_center.overlays import Drawer

root = tk.Tk()
root.title("Drawer 示例")
root.geometry("620x420")
palette = apply_theme(root, tokens_path=Path(__file__).parent / "tokens" / "design-tokens.json")
choice = tk.BooleanVar(root, value=False)
drawer = Drawer(root, palette=palette, title="辅助选项", message="这里的选择由调用方维护。",
                side="right", modal=True, reduced_motion=True,
                content_factory=lambda content: ttk.Checkbutton(
                    content, text="示例选项", variable=choice).pack(anchor="w"))
trigger = ttk.Button(root, text="打开抽屉", command=lambda: drawer.show(trigger))
trigger.pack(pady=40)
root.protocol("WM_DELETE_WINDOW", lambda: (drawer.dispose(), root.destroy()))
root.mainloop()
```

## popover

**用途与边界：** `Popover` 是锚定控件下方的非模态补充面板，可包含少量交互。点击所属主窗口中的外部区域或 Escape 关闭；独立于所属主窗口的其他应用 / 其他 Toplevel 不在点外监听范围。需要阻止其他操作时应使用模态 Dialog / Drawer。

**参数：** `Popover(master, *, palette, anchor=None, text="", content_factory=None, on_close=None)`。省略 `anchor` 时使用 `master`；`content_factory(content)` 可添加调用方控件。打开后焦点进入面板关闭按钮，不设置 grab。面板固定在打开时的锚点位置；宿主移动后可关闭并重新打开定位。

**键盘：** Escape 关闭，关闭后回到触发控件；Tab 使用 Tk 非模态窗口的原生顺序，不把焦点锁在面板内。宿主若已绑定 Escape，应优先调用 `close_active_overlay()`。**依赖：** Tk、ttk、共享主题 palette。

<!-- example:popover -->
```python
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui_center.theme import apply_theme
from ui_center.overlays import Popover, close_active_overlay

root = tk.Tk()
root.title("Popover 示例")
root.geometry("620x420")
palette = apply_theme(root, tokens_path=Path(__file__).parent / "tokens" / "design-tokens.json")
trigger = ttk.Button(root, text="显示补充信息")
trigger.pack(pady=40)
popover = Popover(root, palette=palette, anchor=trigger, text="这是可关闭的补充信息。")
trigger.configure(command=lambda: popover.show(trigger))
root.bind("<Escape>", lambda event: "break" if close_active_overlay(root) else None)
root.protocol("WM_DELETE_WINDOW", lambda: (popover.dispose(), root.destroy()))
root.mainloop()
```

## tooltip

**用途与边界：** `Tooltip` 为控件提供非交互的简短说明，不抢焦点、不设置 grab、不承载按钮。重要信息应在正常界面持续可见，不应只放在提示中。

**参数：** `Tooltip(master, *, palette, text="", delay_ms=500)`，`master` 就是被说明的控件，`delay_ms` 为非负整数。鼠标进入或键盘聚焦时延时显示；鼠标与焦点都离开后关闭。鼠标按下会关闭当前提示。`show()` 可供明确的帮助动作立即显示；`close()`、隐藏、锚点销毁和 `dispose()` 都会取消尚未执行的计时器。提示不参与 `active_overlay()` 的交互弹层栈。

**键盘：** 通过 Tab 聚焦锚点即可触发；提示本身没有焦点顺序，移动到下一控件后关闭。**依赖：** Tk、ttk、共享主题 palette，延时只用 `after`。当前实现不提供屏幕阅读器语义扩展，不能以此宣称完整辅助技术支持。

<!-- example:tooltip -->
```python
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui_center.theme import apply_theme
from ui_center.overlays import Tooltip

root = tk.Tk()
root.title("Tooltip 示例")
root.geometry("620x420")
palette = apply_theme(root, tokens_path=Path(__file__).parent / "tokens" / "design-tokens.json")
trigger = ttk.Button(root, text="悬停或 Tab 聚焦")
trigger.pack(pady=40)
tooltip = Tooltip(trigger, palette=palette, text="此操作只展示虚构数据。", delay_ms=500)
root.protocol("WM_DELETE_WINDOW", lambda: (tooltip.dispose(), root.destroy()))
root.mainloop()
```

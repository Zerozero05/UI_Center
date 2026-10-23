# 导航与反馈组件（Tkinter）

这些组件仅呈现调用方的数据并发出回调；不会处理文件、访问网络或保存设置。实现使用 Python 标准库 Tk/ttk，沿用仓库 [设计规范](../design-guide.md) 和共享 [tokens](../../tokens/README.md)，没有新增第三方运行依赖或外部源码改编。源文件：[navigation.py](../../components/tkinter/ui_center/navigation.py)、[feedback.py](../../components/tkinter/ui_center/feedback.py)。

接入时把 `components/tkinter/ui_center/` 复制到应用可导入位置，并在示例脚本旁放置 `tokens/design-tokens.json`。以下示例完整可运行；所有组件都要求在 Tk UI 线程上调用。先执行 `palette = apply_theme(root, mode)`，再向已创建的组件调用 `apply_palette(palette)`，保留选择、输入、展开状态和消息。字号随 `TkDefaultFont` 更新。颜色本身不能替代消息中的语义文字。

## tabs

**用途**：在同一任务下切换并保留多个页面的内容。长中文页签按可用宽度换行；禁用页不响应鼠标、键盘或 `select`。

**不适用**：大量页面或很长的文档目录；这些场景更适合列表、树或可滚动导航。页签本身不会滚动页面，内容超长时由调用方加入滚动容器。

**参数**：`Tabs(master, *, palette, on_change=None)`；`on_change(key)` 仅在选项实际变化时调用。`add(key, *, text, disabled=False)` 返回页面 `ttk.Frame`，key 是非空唯一字符串。`select()` 返回当前 key（全部禁用时为 `None`）；`select(key, notify=True)` 选择页面，禁用时返回 `False`。`set_disabled(key, bool)` 禁用当前页时选中首个可用页；`set_text(key, text)` 修改标题；`apply_palette(palette)` 仅更新呈现。

**键盘**：Tab 进入当前页签，再次 Tab 进入当前页面中的控件；方向键循环切页并跳过禁用页；Home/End 到首末可用页；Enter/空格激活当前页签。每个页签使用真实可聚焦的 Tk 单选按钮。

**接入**：把业务控件添加到 `add` 返回的页面中，通过回调获知切换，不在回调中无条件重建页面。页签支持的键位限定在页签本身，页面输入框保留编辑按键。

**依赖**：标准库 `tkinter`、`ttk` 与项目主题。读屏器对 Tk 自定义页签的角色识别依赖平台，未声明具备原生 Notebook 的全部辅助功能。

<!-- example:tabs -->
```python
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui_center.theme import apply_theme
from ui_center.navigation import Tabs

root = tk.Tk()
root.title('UI_Center 组件示例')
root.geometry('620x420')
palette = apply_theme(root, tokens_path=Path(__file__).parent / 'tokens' / 'design-tokens.json')
tabs = Tabs(root, palette=palette, on_change=print)
tabs.pack(fill="both", expand=True, padx=12, pady=12)
for key, text in [('overview', '概览'), ('settings', '项目设置'), ('history', '历史记录')]:
    page = tabs.add(key, text=text, disabled=key == "history" and True)
    ttk.Label(page, text="调用方提供的页面内容").pack(anchor="w")
    ttk.Entry(page).pack(fill="x", pady=8)
tabs.select('overview')
root.mainloop()
```

## accordion

**用途**：按需展开一组设置、说明或其他低频内容。折叠仅隐藏内容，不销毁页面和输入。

**不适用**：必须始终可见的错误、主要操作或关键结果；不要把影响决策的内容藏在默认折叠项中。较多或较高的区块需要调用方提供滚动容器。

**参数**：`Accordion(master, *, palette, multiple=False, on_change=None)`；`add(key, *, text, expanded=False, disabled=False)` 返回区块内容 Frame。`expanded` 返回按添加顺序排列的已展开 key 元组。`toggle(key)`、`set_expanded(key, expanded=True, notify=True)` 展开或收起，禁用项返回 `False`；`set_multiple(bool)` 切单项模式时保留添加顺序中的首个展开项；`set_text` 修改标题；`on_change(keys)` 仅在展开集变化时调用。

**键盘**：Tab 逐项定位可用标题及已展开的内容控件；空格/Enter 切换；上下键在标题之间循环并跳过禁用项；Home/End 到首末标题；右键展开、左键收起。箭头文字同时表达展开状态。

**接入**：把内容放入 `add` 返回的 Frame；标题按钮可直接通过真实鼠标或键盘操作。业务校验、数据加载和滚动由调用方负责。`apply_palette` 不改变展开集。

**依赖**：标准库 Tk/ttk 和共享主题，无动画或计时资源。

<!-- example:accordion -->
```python
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui_center.theme import apply_theme
from ui_center.navigation import Accordion

root = tk.Tk()
root.title('UI_Center 组件示例')
root.geometry('620x420')
palette = apply_theme(root, tokens_path=Path(__file__).parent / 'tokens' / 'design-tokens.json')
accordion = Accordion(root, palette=palette, multiple=False, on_change=print)
accordion.pack(fill="x", padx=12, pady=12)
for key, text in [('general', '通用设置'), ('advanced', '高级选项'), ('help', '使用说明')]:
    body = accordion.add(key, text=text, expanded=key in ('general',))
    ttk.Label(body, text="折叠时保留此处输入").pack(anchor="w")
    ttk.Entry(body).pack(fill="x", pady=8)
root.mainloop()
```

## segmented-control

**用途**：在少量同类选项中选择一个，例如时间范围或视图模式。各项是真实可聚焦的单选按钮，互斥值统一保存在组件内部。

**不适用**：多选、独立动作按钮、大量选项或内容页面导航；这些需求分别使用复选框、按钮、下拉框或 Tabs。

**参数**：`SegmentedControl(master, *, palette, options, value=None, disabled=(), on_change=None)`；`options` 是 `(key, text)` 序列，key 必须唯一且非空；默认选择首个可用项。`select()` 读取当前值，`select(value, notify=True)` 修改值并在实际变化时调用 `on_change(value)`，禁用项返回 `False`。`set_disabled(value, bool)` 禁用当前值时改选首个可用项；全部禁用时值为 `None`。`apply_palette` 保留选中值和禁用状态。

**键盘**：Tab 进入当前选项，再次 Tab 离开整组；方向键循环选择可用项；Home/End 到首末可用项；空格/Enter 激活当前项。禁用项不参与方向键循环。

**接入**：在回调里更新调用方视图；不要把同一回调同时绑定到鼠标事件，以免一次操作触发两次。文本按宽度换行，仍应采用简洁、同层级的选项名。

**依赖**：标准库 Tk/ttk 与共享主题，无业务状态存储和计时器。

<!-- example:segmented-control -->
```python
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui_center.theme import apply_theme
from ui_center.navigation import SegmentedControl

root = tk.Tk()
root.title('UI_Center 组件示例')
root.geometry('620x420')
palette = apply_theme(root, tokens_path=Path(__file__).parent / 'tokens' / 'design-tokens.json')
control = SegmentedControl(root, palette=palette,
    options=(("day", "日"), ("week", "周"), ("year", "年度")),
    value='week', disabled=('year',), on_change=print)
control.pack(fill="x", padx=12, pady=12)
root.mainloop()
```

## inline-alert

**用途**：持续显示输入提示、成功、警告和错误。四种状态均有中文语义前缀，正文可以聚焦、选择、复制和滚动，适合保留长错误说明。

**不适用**：需要用户作出明确决定的确认窗口；组件不会阻塞操作或自动执行修复，也不会自动消失。

**参数**：`InlineAlert(master, *, palette, message, kind="info", title=None, action_text="处理", on_action=None)`。kind 为 `info/success/warning/error`；`set_message(message, *, kind=None, title=None)` 更新正文和标题，并把阅读位置移到开头。传入 `on_action` 才显示可聚焦操作按钮。`body` 是只读 Text；`action` 是可选 ttk.Button；`apply_palette` 保留正文、状态和滚动位置。

**键盘**：Tab 进入正文，再次 Tab 到操作按钮或下一个可聚焦控件；Shift+Tab 反向；正文支持标准选择、复制和滚动；按钮以空格激活。只读并不妨碍选择复制。

**接入**：在输入区或结果区就近放置；错误修复由 `on_action()` 通知调用方处理。消息区显示有限行数并提供滚动条，不会把后续操作挤出窗口。

**依赖**：标准库 Tk/ttk 与共享主题。没有计时器；持续保留直到调用方更新或销毁。

<!-- example:inline-alert -->
```python
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui_center.theme import apply_theme
from ui_center.feedback import InlineAlert

root = tk.Tk()
root.title('UI_Center 组件示例')
root.geometry('620x420')
palette = apply_theme(root, tokens_path=Path(__file__).parent / 'tokens' / 'design-tokens.json')
alert = InlineAlert(root, palette=palette, kind='info',
    message='设置尚未保存。确认内容后再继续。', action_text="查看下一步", on_action=lambda: print("查看下一步"))
alert.pack(fill="x", padx=12, pady=12)
root.mainloop()
```

## toast

**用途**：短暂提示非关键操作的完成情况，支持自动关闭、手动关闭和再次显示。使用行内 Frame，可由应用布局在状态区或提示容器中。

**不适用**：必须被读到的错误、任务结果或需要确认的操作；这些信息应放入 InlineAlert 或持续结果区。组件不会创建跨窗口全局浮层，不主动抢焦点。

**参数**：`Toast(master, *, palette, message="", kind="info", duration=4000, on_close=None)`，kind 同 InlineAlert。duration 是非负毫秒数，`0` 表示仅手动关闭。先 pack/grid/place，再 `show(message=None, *, duration=None, kind=None)`；`hide()` 手动关闭，`on_close(reason)` 收到 `manual/timeout`，每轮仅一次。`is_open` 表示该轮是否仍打开。`set_visible(False)` 隐藏并暂停剩余时间；`set_visible(True)` 恢复仍打开的一轮；`dispose()` 取消全部计时并销毁。父容器销毁也会取消 timer。`apply_palette` 不重新开始计时。

**键盘**：Tab 可到达“关闭”按钮，空格关闭；焦点在提示内部时暂停倒计时，离开后继续剩余时间。鼠标悬停同样暂停。自动关闭不会跳到新焦点。

**接入**：重要信息同时写入调用方的持续状态区。页面隐藏时调用 `set_visible(False)`，退出时调用 `dispose()` 或销毁父容器。直接取消布局或隐藏父窗口产生的 Unmap 也会暂停倒计时，重新映射后继续。再次 `show()` 开始新的一轮；组件保存自己的 pack/grid/place 布局信息以便恢复。没有淡入淡出，因此正常和减少动画模式下均不产生动画。

**依赖**：标准库 Tk/ttk、`time.monotonic` 与共享主题；只使用 Tk `after`，不创建线程。

<!-- example:toast -->
```python
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui_center.theme import apply_theme
from ui_center.feedback import Toast

root = tk.Tk()
root.title('UI_Center 组件示例')
root.geometry('620x420')
palette = apply_theme(root, tokens_path=Path(__file__).parent / 'tokens' / 'design-tokens.json')
toast = Toast(root, palette=palette, kind='success', duration=4000,
    message="演示设置已保存。", on_close=print)
toast.pack(fill="x", padx=12, pady=12)
ttk.Button(root, text="再次显示", command=lambda: toast.show()).pack()
toast.show()
root.protocol("WM_DELETE_WINDOW", lambda: (toast.dispose(), root.destroy()))
root.mainloop()
```

## empty-state

**用途**：区分首次使用、搜索无结果和暂时无数据，并提供调用方实际可以执行的下一步操作。

**不适用**：加载中、权限失败或请求出错。空白不能代替加载或错误提示；未取得数据时应先明确真实状态。

**参数**：`EmptyState(master, *, palette, kind="first-use", title=None, message=None, action_text=None, on_action=None)`；kind 是 `first-use/no-results/no-data`。省略标题、说明和操作文字时采用对应中文默认值；传 `on_action()` 才显示按钮。`set_state(kind, *, title=None, message=None, action_text=None)` 更新说明并保留同一个回调；`action` 是真实 ttk.Button，可通过 `action.state(["disabled"])` 设置不可用。`apply_palette` 保留当前原因、自定义文字和禁用状态。

**键盘**：Tab 到达操作按钮，空格执行；禁用按钮不触发回调。标题和说明不是虚假按钮，不加入多余焦点站点。

**接入**：调用方传入符合当前原因的回调，例如创建、清除筛选或刷新；组件只发出回调，不创建演示数据、不自行加载数据。

**依赖**：标准库 Tk/ttk 与共享主题，无计时器、线程或数据依赖。

<!-- example:empty-state -->
```python
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui_center.theme import apply_theme
from ui_center.feedback import EmptyState

root = tk.Tk()
root.title('UI_Center 组件示例')
root.geometry('620x420')
palette = apply_theme(root, tokens_path=Path(__file__).parent / 'tokens' / 'design-tokens.json')
empty = EmptyState(root, palette=palette, kind='first-use', on_action=lambda: print("执行下一步"))
empty.pack(fill="x", padx=12, pady=12)
empty.action.state(['!disabled'])
root.mainloop()
```

上述键盘、状态保持和计时资源通过真实 Tk 控件测试；全平台读屏器、全部 DPI 与触控设备并未据此获得验证。消费应用仍需核验自己的页面内容、状态回调和布局。

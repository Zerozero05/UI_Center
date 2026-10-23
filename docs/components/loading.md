# 加载与进度组件（Tkinter）

这些组件只显示调用方提供的状态，不读取文件、不访问网络，也不创建业务任务。源码在 [loading.py](../../components/tkinter/ui_center/loading.py)，交互预览在 [previews_loading.py](../../apps/desktop/previews_loading.py)。本次未引入新的外部借鉴；沿用项目已有 Tk/ttk 主题和设计参数，无第三方运行依赖。

把 `components/tkinter/ui_center/` 和 `tokens/design-tokens.json` 复制到消费项目；以下完整示例假设二者与脚本同级。所有方法在 Tk UI 线程调用；工作线程结果先通过消费应用已有的 UI 调度机制转交。

共同接口：构造器必须传 `palette=`；`apply_palette(palette)` 只换颜色；`start()` / `stop()` 控制装饰状态；`set_visible(False)` 在页面隐藏时暂停装饰；`set_reduced_motion(True)` 保留静态状态和真实进度；`dispose()` 销毁组件。实际取消任务必须由调用方完成。组件不自动管理普通组件的 pack/grid 显隐，PageLoader 自己管理 stage 内的遮罩。

每个组件最多持有一个待执行 `after`，间隔至少34ms（少于30fps，默认50ms）；隐藏、取消映射、销毁、停止或减少动画会取消装饰计时器。真实进度、说明和调用方输入保留。无需动画的确定进度不创建计时器。屏幕阅读器对 Tk Canvas 图形的支持取决于运行环境，重要业务状态还应写入应用现有文字反馈区。

## spinner

**用途：** 总量未知的短时等待，配合明确说明显示仍在处理。

**不适用条件：** 已知完成量时优先用 progress-bar；长时任务还需要应用自己的取消、失败或超时反馈。

**参数：** `Spinner(master, *, palette, size=40, text='正在加载', interval_ms=50, reduced_motion=False)`。`size` 以 Tk 像素计，最小16；`set_size(size)`、`set_text(text)` 可更新尺寸与说明。`running` 只表示调用方已标记为加载。

**接入：** 创建并布局后调用 `start()`，业务完成时 `stop()`。切换主题调用 `apply_palette()`，页面离开调用 `set_visible(False)`。

**依赖：** Python 标准库 `tkinter/ttk/Canvas`；复制主题和 tokens。

<!-- example:spinner -->
```python
from pathlib import Path
import tkinter as tk
from ui_center.theme import apply_theme
from ui_center.loading import Spinner

root = tk.Tk()
root.title('等待状态')
palette = apply_theme(root, tokens_path=Path(__file__).parent / 'tokens' / 'design-tokens.json')
spinner = Spinner(root, palette=palette, size=48, text='正在读取列表')
spinner.pack(padx=24, pady=24)
spinner.start()
# 在真实任务的完成回调中调用 spinner.stop()
root.mainloop()
```

## progress-bar

**用途：** 横向呈现调用方真实的完成量；总量未知时使用明确标注“进度未知”的不确定模式。

**不适用条件：** 不要用定时器伪造百分比；不确定模式的移动色块不代表实际完成量。

**参数：** `ProgressBar(master, *, palette, value=0, maximum=100, mode='determinate', length=320, ...)`。`mode` 为 `determinate` / `indeterminate`；`set_mode(mode)` 切换模式；`set_progress(value, maximum=None)` 更新真实进度。要求有限数值且 `maximum > 0`、`0 <= value <= maximum`，无效值抛 `ValueError` 并保留此前状态。`value/maximum` 可读取；百分比文字按最接近的整数显示。

**接入：** 接收业务进度回调后更新 `set_progress`。确定模式没有动画计时器；切到不确定模式也保留原真实进度，切回后继续显示。

**依赖：** Python 标准库 Tk/ttk/Canvas；无 ttk 原生自动递增计时器或第三方依赖。

<!-- example:progress-bar -->
```python
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui_center.theme import apply_theme
from ui_center.loading import ProgressBar

root = tk.Tk()
root.title('真实进度')
palette = apply_theme(root, tokens_path=Path(__file__).parent / 'tokens' / 'design-tokens.json')
progress = ProgressBar(root, palette=palette, value=3, maximum=8)
progress.pack(fill='x', padx=24, pady=24)
# 示例由按钮提供真实的已完成数量；业务应用改接自己的进度回调。
ttk.Button(root, text='已完成8项', command=lambda: progress.set_progress(8)).pack(pady=12)
root.mainloop()
```

## circular-progress

**用途：** 在紧凑区域显示真实完成比例，中心始终显示百分比。

**不适用条件：** 总量未知时不要估算百分比，改用 spinner。需要同时比较大量任务时更适合横向进度和文字列表。

**参数：** `CircularProgress(master, *, palette, value=0, maximum=100, size=112, ...)`。`size` 最小40；`set_size(size)` 更新尺寸；`set_progress(value, maximum=None)` 与 progress-bar 的范围规则一致。0%为空环，100%为完整实环；`start()` 不自动增加数值，也不创建装饰计时器。

**接入：** 将真实任务完成量传给 `set_progress()`。主题、减少动画和隐藏切换均保留 `value/maximum`。

**依赖：** Python 标准库 Tk/ttk/Canvas 与项目主题。

<!-- example:circular-progress -->
```python
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui_center.theme import apply_theme
from ui_center.loading import CircularProgress

root = tk.Tk()
root.title('环形进度')
palette = apply_theme(root, tokens_path=Path(__file__).parent / 'tokens' / 'design-tokens.json')
progress = CircularProgress(root, palette=palette, value=3, maximum=8, size=112)
progress.pack(padx=24, pady=24)
ttk.Button(root, text='完成', command=lambda: progress.set_progress(8)).pack(pady=12)
root.mainloop()
```

## skeleton

**用途：** 内容尚未到达但布局已知时，提前显示列表或卡片的大致结构，减少布局跳动。正常动画下可选平滑脉动，让整组占位温和改变明暗；它与移动高光的扫光骨架共用布局。

**不适用条件：** 内容可能永久为空、权限拒绝或已失败时应显示真实的空/错误状态。占位块不应替代已可见的用户数据。

**参数：** `Skeleton(master, *, palette, variant='list', rows=3, width=360, animate=True, ...)`。`variant` 为 `list` / `card`；`rows` 为1–10（列表行数）；`set_variant()` 切换布局；`set_animation(False)` 关闭装饰脉动而保留占位；`reduced_motion=True` 同样保留静态占位。`stop()` 停止装饰，调用者在内容到达后自行替换布局。

**接入：** 用与最终内容相同的容器和布局位置放置占位。业务完成时停止并 `grid_remove()` / `pack_forget()`，再呈现真实内容。

**工作台预览：** “布局”的列表／卡片、“脉动效果”的开启／关闭均使用相邻文字选项，当前选择直接可见；代码仍使用 `list/card` 与 `animate`。顶部启用减少动画时局部效果选项禁用，原选择保留，并说明当前为静态占位；选择正常动画后，仍处于运行状态的预览才恢复脉动。统一“重置”恢复本组件参数；停止预览不代表业务完成或取消。

**依赖：** Python 标准库 Tk/ttk/Canvas 与项目主题。

<!-- example:skeleton -->
```python
from pathlib import Path
import tkinter as tk
from ui_center.theme import apply_theme
from ui_center.loading import Skeleton

root = tk.Tk()
root.title('列表占位')
palette = apply_theme(root, tokens_path=Path(__file__).parent / 'tokens' / 'design-tokens.json')
placeholder = Skeleton(root, palette=palette, variant='list', rows=3, animate=True)
placeholder.pack(fill='x', padx=24, pady=24)
placeholder.start()
# 数据到达后：placeholder.stop(); placeholder.pack_forget()
root.mainloop()
```

## shimmer

**用途：** 在骨架占位形状内添加可关闭的渐变移动高光，底色保持稳定、间隔空白保持不变；`shummer` 是目录搜索别名，Python类名为 `Shimmer`。它与骨架屏的区别是移动高光，而非另一份内容布局。

**不适用条件：** 用户选择减少动画、长时间等待、需要集中阅读或高光造成干扰时关闭。不能将高光速度解释为业务速度。

**参数：** `Shimmer(master, *, palette, enabled=True, variant='list', rows=3, width=360, ...)`。布局参数与Skeleton相同；`set_enabled(False)` 移除高光、取消装饰计时器并保留占位；`set_reduced_motion(True)` 无须改变用户的 `enabled` 选择。

**接入：** 显式传入用户的动画偏好；离开页面调用 `set_visible(False)`。恢复页面后仍由真实加载状态决定是否继续。

**工作台预览：** “扫光效果”使用相邻的开启／关闭文字选项。减少动画时与骨架屏一样显示静态占位，这是预期降级；状态说明会给出原因。关闭局部效果或停止预览后也保留占位，状态文字分别说明，不把等待动画当作真实业务进度。下面独立示例采用已有公开组件 `SegmentedControl`，无需工作台表单辅助代码。

**依赖：** Python标准库Tk/ttk/Canvas及已有主题颜色，不使用图片或额外运行库。

<!-- example:shimmer -->
```python
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui_center.theme import apply_theme
from ui_center.loading import Shimmer
from ui_center.navigation import SegmentedControl

root = tk.Tk()
root.title('可关闭高光')
palette = apply_theme(root, tokens_path=Path(__file__).parent / 'tokens' / 'design-tokens.json')
placeholder = Shimmer(root, palette=palette, variant='card', enabled=True)
placeholder.pack(fill='x', padx=24, pady=24)
placeholder.start()
controls = ttk.Frame(root)
controls.pack(pady=12)
ttk.Label(controls, text='扫光效果').pack(side='left', padx=(0, 8))
picker = SegmentedControl(controls, palette=palette,
                          options=(('on', '开启'), ('off', '关闭')), value='on',
                          on_change=lambda value: placeholder.set_enabled(value == 'on'))
picker.pack(side='left')
root.mainloop()
```

## loading-button

**用途：** 为单个动作显示忙碌并防止重复提交，保留真实 `ttk.Button` 的键盘、焦点和禁用行为。

**不适用条件：** 取消任务不应再次使用忙碌按钮；提供单独取消入口。多个独立动作需要各自的业务状态，不要共用一个按钮伪装全局任务锁。

**参数：** `LoadingButton(master, *, palette, text='开始处理', busy_text='正在处理', command=None, ...)`。`.button` 是真实的 `ttk.Button`；`set_busy(True/False)` 切换忙碌与禁用；`start()` / `stop()` 等价；`set_text(text, busy_text=None)` 更新文案。`command` 由消费应用执行，组件不会自动置忙、创建线程或自动宣布完成。忙碌时忽略重复触发。主题更新保留当前忙碌与外部禁用状态。

**接入：** 在业务动作开始后立即 `set_busy(True)`；成功、失败或取消最终落定时都恢复 `set_busy(False)`。减少动画仍保留忙碌文字和禁用行为。

**依赖：** Python 标准库 Tk/ttk；装饰用 Canvas。无需替换系统按钮或监听全局键盘。

<!-- example:loading-button -->
```python
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui_center.theme import apply_theme
from ui_center.loading import LoadingButton

root = tk.Tk()
root.title('忙碌按钮')
palette = apply_theme(root, tokens_path=Path(__file__).parent / 'tokens' / 'design-tokens.json')

def on_start():
    action.set_busy(True)
    status.configure(text='等待调用方的完成、失败或取消回调')

status = ttk.Label(root, text='点击开始；完成按钮代表调用方回调')
status.pack(padx=24, pady=12)
action = LoadingButton(root, palette=palette, text='开始处理', command=on_start)
action.pack(pady=12)
ttk.Button(root, text='任务已结束', command=lambda: action.set_busy(False)).pack(pady=12)
root.mainloop()
```

## page-loader

**用途：** 为一个页面或局部 stage 呈现加载遮罩，显示可选真实进度及取消入口。

**不适用条件：** 不用作整个应用的模态锁、权限边界或不可绕过的输入阻挡。组件无 `Toplevel`、无全局 grab、不会关闭其他窗口；若业务需要禁止底层快捷键或输入，消费应用应管理对应控件状态及焦点。不要遮挡全应用导航和取消入口。

**参数：** `PageLoader(master, *, palette, text='正在加载页面', value=None, maximum=100, on_cancel=None, ...)`。`master` 必须是要遮住的局部容器；`start()` 通过 `place` 覆盖此容器，`stop()` 撤下遮罩；`set_progress(value, maximum=None)` 更新实际进度，`None` 显示“进度未知”；`set_text()` 更新说明。取消按钮只调用 `on_cancel`，是否停止任务与遮罩由调用者决定；`cancel_button` 在无回调时为 `None`。

**接入：** 先创建局部页面内容，再在同一容器创建 loader；不要把 loader pack/grid 到页面内容中。业务开始/结束时调用 `start()` / `stop()`；外层页面隐藏用 `set_visible(False)`，恢复后保留原加载状态与进度。遮罩不会清空容器中的输入。

**依赖：** Python 标准库 Tk/ttk/Canvas；无窗口管理器或系统权限依赖。

<!-- example:page-loader -->
```python
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui_center.theme import apply_theme
from ui_center.loading import PageLoader

root = tk.Tk()
root.title('局部页面加载')
root.geometry('620x420')
palette = apply_theme(root, tokens_path=Path(__file__).parent / 'tokens' / 'design-tokens.json')
ttk.Label(root, text='应用导航仍可使用').pack(pady=12)
stage = ttk.Frame(root, padding=20)
stage.pack(fill='both', expand=True)
entry = ttk.Entry(stage)
entry.insert(0, '遮罩结束后保留此输入')
entry.pack(pady=12)
loader = PageLoader(stage, palette=palette, text='正在加载列表', value=3,
                    maximum=8, on_cancel=lambda: loader.stop())
loader.start()
root.mainloop()
```

实际验证见 `tests/test_loading_widgets.py`：真实 Tk 状态、30轮组件与预览销毁重建、重复开始、隐藏/减少动画、真实进度、主题保留输入、局部遮罩边界和可独立运行的预览代码。此测试不等同于所有系统主题、读屏软件或每一种 DPI 已实机覆盖。

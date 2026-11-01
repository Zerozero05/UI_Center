# v1.3.0 原生界面设计记录

本轮按已确认范围调整工作台、18个现有组件和3个旧Tk预览。保留组件ID、公开构造器/方法/回调、中文用法、当前参数示例、三字段偏好和两端源码。代码以Tk/ttk/Canvas实现，未批量引入Web组件或安装上游工具。

## 实际阅读与取舍

2026-11-01核对用户的“界面与设计”列表，包含以下三个仓库。核对仓库说明、目录、许可、当前提交及选定设计文件/示例；没有声称逐一运行或审阅Galaxy的全部3802个HTML示例。

| 标记 | 固定来源与阅读文件 | 采用与边界 |
| --- | --- | --- |
| I | [Impeccable](https://github.com/pbakaus/impeccable/tree/4f956490f0056ae1ff5ea80372cf56e83c001d3c)：README、`.agents/skills/impeccable/reference/audit.native.md`、`critique.md`、`component-review.md`；Apache-2.0 | 借鉴层次、留白、状态一致性、平台适配和验证维度；没有安装技能、hooks或检测器，其Web检测结果不能证明Tk界面可用。 |
| A | [awesome-design-md / Figma DESIGN.md](https://github.com/VoltAgent/awesome-design-md/blob/fcc70284932276d085f01ef9f83edde90b1258cb/design-md/figma/DESIGN.md)，另读README/目录；MIT | 借鉴语义颜色、字号、间距、圆角及组件状态分开记录的方法；重新制定桌面尺寸。未复制品牌字体、图形、营销页面大字号或整套色值。 |
| A2 | [Linear.app DESIGN.md](https://github.com/VoltAgent/awesome-design-md/blob/fcc70284932276d085f01ef9f83edde90b1258cb/design-md/linear.app/DESIGN.md)；MIT | 阅读分层表面、网格/容器、产品展示面板、间距与导航说明；用面板分工替代原来一整块空白。未照搬营销页尺寸。 |
| A3 | [Raycast DESIGN.md](https://github.com/VoltAgent/awesome-design-md/blob/fcc70284932276d085f01ef9f83edde90b1258cb/design-md/raycast/DESIGN.md)；MIT | 阅读搜索输入、command-palette-card/row、扩展卡片与导航说明，借鉴搜索和紧凑列表、标题/说明/操作分工。 |
| G1 | [Galaxy / 0x-Sarthak 按钮](https://github.com/uiverse-io/galaxy/blob/adbd2adde0a299a3956ea288fb444ec01891ca41/Buttons/0x-Sarthak_hungry-penguin-30.html)；MIT | 参考圆角和清晰hover/pressed区别，使用原生按钮重新实现；未采用位移、缩放、箭头、CSS或紫色品牌配色。 |
| G2 | [Galaxy / AHMED-MIT spinner](https://github.com/uiverse-io/galaxy/blob/adbd2adde0a299a3956ea288fb444ec01891ca41/loaders/AHMED-MIT_cold-ape-73.html)；MIT | 原生样式改编：保留圆环与两个错相圆点，将CSS边框/阴影/关键帧转换为Canvas几何；重写尺寸与语义配色、2秒周期及生命周期。完整MIT版权随包保留。 |
| G3 | [Galaxy / Cksunandh tooltip](https://github.com/uiverse-io/galaxy/blob/adbd2adde0a299a3956ea288fb444ec01891ca41/Tooltips/Cksunandh_afraid-snail-51.html)；MIT | 参考触发点与提示的空间关系；原生提示采用280px初始换行和8px间隙，保留键盘触发、取消和不抢焦点。 |

同一Galaxy提交的 [0xnihilism loader](https://github.com/uiverse-io/galaxy/blob/adbd2adde0a299a3956ea288fb444ec01891ca41/loaders/0xnihilism_brown-puma-30.html) 与 [ActiveIceDigital notification](https://github.com/uiverse-io/galaxy/blob/adbd2adde0a299a3956ea288fb444ec01891ca41/Notifications/ActiveIceDigital_fuzzy-fly-47.html) 也已阅读；强闪烁、扫描线、阴影和持续上下移动不符合本轮风格，未采用。Galaxy对应提交日期为2024-09-02；另外两项分别为2026-10-31和2026-10-28。维护活跃度不等于原生兼容性。

G2为**原生样式改编**并保留MIT版权与完整许可；其余为方法/视觉参考，没有复制外部资源或上游指令。新增Python实现和文档沿用AGPL-3.0-only。原有PDF项目代码改编及其来源声明继续保留。

## 工作台布局重做

用户明确要求页面结构也重新优化后，本轮进一步采用A2/A3的面板与检索组织方法：

1. 顶栏保留应用、外观入口和帮助，外观按需展开；左栏采用搜索、三项导航与条目列表，筛选按需展开。
2. 主区依次显示场景路径、标题与平台标记、用途摘要、紧凑复用操作和内容页；复制等操作移到标题附近。
3. 实时预览拆为组件展示面板和参数检查器，宽窗口左右排列；检查器中参数逐行排列。窄窗口上下排列，参数组恢复自动换行。
4. 展示面板保留真实主题背景，单独设置面板标题与细边界；可用空间由组件展示承担。按真实内容显示滚动条。
5. 缩放和重排复用原控件；不清空参数、进度、焦点或代码内容。新增视口监听随预览销毁解绑。

这两份上游材料主要分析网站与产品展示，不提供可直接运行的Tk桌面页面模板；本项目按组件工具的任务重新组合布局，不冒称完整移植Linear或Raycast应用。

## 组件逐项落实

| 组件ID / 中文名 | 本轮实际改动 | 参考与保留行为 |
| --- | --- | --- |
| spinner / 旋转加载 | 改编Galaxy双相圆点/圆环；尺寸、2秒旋转与静态状态明确 | I/A/G2；文字与开始/停止保持 |
| progress-bar / 条形进度 | 10px圆角轨道及真实填充，完成使用成功色，未知进度保留明确文字 | I/A；不估计任务进度 |
| circular-progress / 环形进度 | 细轨道、圆头进度弧、加粗且适配尺寸的百分比；完成使用成功色 | I/A/G2；中心百分比保持 |
| skeleton / 骨架屏 | 列表占位长短分层、圆角轮廓和温和整体脉动 | I/A；列表/卡片、数量与静态模式保持 |
| shimmer / 扫光骨架 | 圆角占位与末层圆角裁剪，亮带仅在占位内移动 | I/A；与骨架脉动区分，减少动画时静态 |
| loading-button / 加载按钮 | 圆角主按钮、独立浅色忙碌外观，圆头忙碌标记收在按钮内 | I/A/G1/G2；原生空格/禁用、防重入保持 |
| page-loader / 区域加载层 | 区域底色和居中提示卡、圆环/说明/取消分层；已知值显示真实圆环且停装饰计时 | I/A；限制在stage内，不创建全局模态 |
| dialog / 普通弹窗 | 原生矢量信息标记、标题/正文分区、明确主关闭按钮 | I/A/G1；模态/Esc/焦点恢复保持 |
| confirm-dialog / 确认弹窗 | 决策标记、标题及操作分隔、主确认与次取消层次 | I/A/G1；初始焦点和默认Return仍为取消 |
| drawer / 抽屉 | 面板标记与标题区、紧凑关闭面板、统一留白 | I/A；左右方向、有界动画和减少动画保持 |
| popover / 气泡面板 | 独立内容表面、次要关闭操作，靠近触发点并在窗口边缘翻转/调整位置 | I/A/G1；非模态、外点与Esc关闭保持 |
| tooltip / 工具提示 | 反色高对比气泡、紧凑换行、8px间隙，窗口边缘调整位置 | I/A/G3；延迟、悬浮/焦点与销毁取消保持 |
| tabs / 标签页 | 选中下划线和强调文字，页签间距与键盘焦点分开表达 | I/A；方向键跳过禁用项，页面输入保持 |
| accordion / 折叠面板 | 每个折叠项采用独立圆角面板，标题与内容分层，保留状态与焦点 | I/A；单项/多项、键盘和内容保持 |
| segmented-control / 分段选择 | 统一圆角外框、内部分段和浅色选中，互斥选择清晰 | I/A；互斥值、禁用项、单一Tab入口保持 |
| inline-alert / 行内提示 | 矢量状态标记、加粗标题、安静外框、紧凑动作 | I/A；Text复制、长文滚动、状态文字保持 |
| toast / 轻通知 | 矢量状态标记、细框与次要关闭操作，暂停计时范围包含标记 | I/A/G1；计时、悬浮/焦点暂停、不抢焦点保持 |
| empty-state / 空状态 | 按原因绘制更清晰的Canvas图形，加大标题、说明/主操作分层 | I/A；首次/无结果/无数据及调用方动作保持 |

3个旧Tk预览同步新的主题、圆角按钮和进度轨道；ActionBar重置降一级，原模拟任务、取消、结果和当前参数代码继续保留。工作台自身统一页签、侧栏选中、平台标记、中文参数和工具操作样式。

## 采用与后续维护

完整规则见 [DESIGN.md](../DESIGN.md)。复制整个组件目录和tokens；辅助绘图模块是标准库实现，不是新增第三方依赖。旧参数文件读取时仅在内存补齐装饰角色。每次改变核心参数或公共行为时按影响核对状态、消费示例和主题/字号；实际检查结果与未测范围见 [验证记录](../VALIDATION.md)。

当前为v1.3.0候选，公开最新运行版仍是v1.2.3。开发源码推送与候选CI不等于公开发行授权；具体附件准备好后按本次版本单独确认。

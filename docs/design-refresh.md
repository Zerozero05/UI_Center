# v1.3.0 原生界面设计记录

本轮按已确认范围调整工作台、18个现有组件和3个旧Tk预览。保留组件ID、公开构造器/方法/回调、中文用法、当前参数示例、三字段偏好和两端源码。代码以Tk/ttk/Canvas实现，未批量引入Web组件或安装上游工具。

## 实际阅读与取舍

2026-11-01核对用户的“界面与设计”列表，包含以下三个仓库。核对仓库说明、目录、许可、当前提交及选定设计文件/示例；没有声称逐一运行或审阅Galaxy的全部3802个HTML示例。

| 标记 | 固定来源与阅读文件 | 采用与边界 |
| --- | --- | --- |
| I | [Impeccable](https://github.com/pbakaus/impeccable/tree/4f956490f0056ae1ff5ea80372cf56e83c001d3c)：README、`.agents/skills/impeccable/reference/audit.native.md`、`critique.md`、`component-review.md`；Apache-2.0 | 借鉴层次、留白、状态一致性、平台适配和验证维度；没有安装技能、hooks或检测器，其Web检测结果不能证明Tk界面可用。 |
| A | [awesome-design-md / Figma DESIGN.md](https://github.com/VoltAgent/awesome-design-md/blob/fcc70284932276d085f01ef9f83edde90b1258cb/design-md/figma/DESIGN.md)，另读README/目录；MIT | 借鉴语义颜色、字号、间距、圆角及组件状态分开记录的方法；重新制定桌面尺寸。未复制品牌字体、图形、营销页面大字号或整套色值。 |
| G1 | [Galaxy / 0x-Sarthak 按钮](https://github.com/uiverse-io/galaxy/blob/adbd2adde0a299a3956ea288fb444ec01891ca41/Buttons/0x-Sarthak_hungry-penguin-30.html)；MIT | 参考圆角和清晰hover/pressed区别，使用原生按钮重新实现；未采用位移、缩放、箭头、CSS或紫色品牌配色。 |
| G2 | [Galaxy / AHMED-MIT spinner](https://github.com/uiverse-io/galaxy/blob/adbd2adde0a299a3956ea288fb444ec01891ca41/loaders/AHMED-MIT_cold-ape-73.html)；MIT | 参考单色环形等待和旋转意图，自行绘制一条轨道与圆头弧线；未照搬双环、CSS或时序。 |
| G3 | [Galaxy / Cksunandh tooltip](https://github.com/uiverse-io/galaxy/blob/adbd2adde0a299a3956ea288fb444ec01891ca41/Tooltips/Cksunandh_afraid-snail-51.html)；MIT | 参考触发点与提示的空间关系；原生提示采用280px初始换行和8px间隙，保留键盘触发、取消和不抢焦点。 |

同一Galaxy提交的 [0xnihilism loader](https://github.com/uiverse-io/galaxy/blob/adbd2adde0a299a3956ea288fb444ec01891ca41/loaders/0xnihilism_brown-puma-30.html) 与 [ActiveIceDigital notification](https://github.com/uiverse-io/galaxy/blob/adbd2adde0a299a3956ea288fb444ec01891ca41/Notifications/ActiveIceDigital_fuzzy-fly-47.html) 也已阅读；强闪烁、扫描线、阴影和持续上下移动不符合本轮风格，未采用。Galaxy对应提交日期为2024-09-02；另外两项分别为2026-10-31和2026-10-28。维护活跃度不等于原生兼容性。

以上均为**方法/视觉参考**；没有复制或转换HTML/CSS源码、资源或上游指令。新增Python、Canvas图形和文档由本项目编写，沿用AGPL-3.0-only。原有PDF项目代码改编及其来源声明继续保留。

## 组件逐项落实

| 组件ID / 中文名 | 本轮实际改动 | 参考与保留行为 |
| --- | --- | --- |
| spinner / 旋转加载 | 更细轨道、圆头弧线、单色有界旋转 | I/A/G2；文字与开始/停止保持 |
| progress-bar / 条形进度 | 10px圆角轨道及真实填充，未知进度保留明确文字 | I/A；不估计任务进度 |
| circular-progress / 环形进度 | 低强调轨道、圆头进度弧；0与100完整绘制 | I/A/G2；中心百分比保持 |
| skeleton / 骨架屏 | 列表占位长短有节奏变化，沿用温和整体脉动 | I/A；列表/卡片、数量与静态模式保持 |
| shimmer / 扫光骨架 | 同一占位布局，亮带继续裁在各形状内 | I/A；与骨架脉动区分，减少动画时静态 |
| loading-button / 加载按钮 | 新主按钮外观，细圆头忙碌标记收在按钮内 | I/A/G1/G2；原生空格/禁用、防重入保持 |
| page-loader / 区域加载层 | 同一圆环语言、紧凑取消操作；已知值显示真实圆环且停装饰计时 | I/A；限制在stage内，不创建全局模态 |
| dialog / 普通弹窗 | 标题细分隔、明确主关闭按钮 | I/A/G1；模态/Esc/焦点恢复保持 |
| confirm-dialog / 确认弹窗 | 标题分区、主确认与次取消层次 | I/A/G1；初始焦点和默认Return仍为取消 |
| drawer / 抽屉 | 标题分隔、紧凑关闭面板、统一留白 | I/A；左右方向、有界动画和减少动画保持 |
| popover / 气泡面板 | 新次要关闭操作与统一中性表面 | I/A/G1；非模态、外点与Esc关闭保持 |
| tooltip / 工具提示 | 紧凑换行、触发控件与提示留8px空隙 | I/A/G3；延迟、悬浮/焦点与销毁取消保持 |
| tabs / 标签页 | 更轻分隔和页签间隙，状态配色统一 | I/A；方向键跳过禁用项，页面输入保持 |
| accordion / 折叠面板 | 标题采用统一轻边界、选中/悬浮/焦点语言 | I/A；单项/多项、键盘和内容保持 |
| segmented-control / 分段选择 | 选项间留细空隙、边界与状态统一 | I/A；互斥值、禁用项、单一Tab入口保持 |
| inline-alert / 行内提示 | 语义色窄侧线、加粗标题、安静外框、紧凑动作 | I/A；Text复制、长文滚动、状态文字保持 |
| toast / 轻通知 | 同一语义侧线、细框与次要关闭操作 | I/A/G1；计时、悬浮/焦点暂停、不抢焦点保持 |
| empty-state / 空状态 | Canvas按原因绘制小图形，标题/说明/主操作分层，主要行动明确强调 | I/A；首次/无结果/无数据及调用方动作保持 |

3个旧Tk预览同步新的主题、圆角按钮和进度轨道；ActionBar重置降一级，原模拟任务、取消、结果和当前参数代码继续保留。工作台自身统一页签、侧栏选中、平台标记、中文参数和工具操作样式。

## 采用与后续维护

完整规则见 [DESIGN.md](../DESIGN.md)。复制整个组件目录和tokens；辅助绘图模块是标准库实现，不是新增第三方依赖。旧参数文件读取时仅在内存补齐装饰角色。每次改变核心参数或公共行为时按影响核对状态、消费示例和主题/字号；实际检查结果与未测范围见 [验证记录](../VALIDATION.md)。

当前为v1.3.0候选，公开最新运行版仍是v1.2.3。开发源码推送与候选CI不等于公开发行授权；具体附件准备好后按本次版本单独确认。

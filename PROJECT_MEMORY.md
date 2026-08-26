# 股票数据看板工具 · 项目记忆文档

> 本文档为项目的"唯一事实来源"（Single Source of Truth），所有功能、决策、进度以此为准。
> 创建日期：2026-08-24 · 版本：v1.6（阶段 4 改选为 bat+浏览器交付，全部完成）

---

## 1. 项目背景

### 1.1 产品定位

**A股盘后复盘的"情报分析中心"**——个人自用的桌面应用，用于收盘后快速回顾当日盘面、定位主线方向、监控风险信号。

### 1.2 使用场景

- 盘后复盘工具，一天用 1 次，每次 10-30 分钟
- 收盘后双击 `.exe` 打开 → 点刷新拉数据 → 在总览看盘 → 按需切换模块复盘 → 关闭
- 不需要盘中实时盯盘、不需要后台常驻、不需要推送通知

### 1.3 参考项目复盘要点

参考他人项目「复盘大师」暴露的两大问题，本项目必须从架构层面规避：

1. **数据更新经常失败**：东财接口爱限流（分时十几秒自愈、K线能限流20分钟+），靠"三级降级"硬扛不是好方案 → 本项目用 **akshare**（已封装容错）+ 持久化缓存
2. **数据内容错误**：失败时回落演示数据导致真假混淆，且涨停原因/资讯等无免费API只能硬编码 → 本项目铁律：**绝不显示假数据，失败即空+重试**

---

## 2. 技术栈

### 2.1 已确认技术栈

| 层 | 技术 | 版本 | 说明 |
|---|---|---|---|
| 前端框架 | React + TypeScript | 18.x | 组件化开发 |
| 构建工具 | Vite | 最新 | 秒级热更新 |
| UI 组件库 | Ant Design | 5.x | 企业级组件 |
| 图表库 | ECharts | 5.x | K线/条形/仪表盘 |
| 后端框架 | FastAPI | 最新 | 异步 + 自动文档 |
| 数据源 | akshare | 最新 | A股免费数据 |
| 数据库 | SQLite | 内置 | 本机持久化 |
| 任务调度 | APScheduler | 最新 | 备用（自动刷新等场景） |
| AI 服务 | 智谱 GLM-4-Flash | 免费版 | 资讯总结 |
| 交付方式 | bat + 浏览器 | - | 阶段 4 改选：双击 start.bat 由后端同源托管前端（放弃 Tauri 打包，见决策记录） |
| 包管理 | pnpm (前端) + uv (后端) | - | corepack 调用 pnpm，无需全局安装 |
| Python | 3.12.13 | uv 自动选择 | 兼容性最佳 |

### 2.2 环境约束（硬性规则）

- **环境隔离**：所有代码运行在项目根目录的隔离环境（`.venv` / `node_modules`），严禁修改全局环境
- **零成本**：所有依赖开源免费，仅 AI 用智谱 GLM-4-Flash 免费版（需用户自注册 API Key）
- **零跨域**：浏览器不直连东财，统一走 FastAPI 服务端代理

### 2.3 交付形态与体积

- 阶段 4 最终改为 **bat + 浏览器** 交付：无需打包 `.exe`，无体积与工具链约束，复用项目内 `.venv` 即可运行
- 双击 `start.bat` → 后端启动（127.0.0.1:8003）→ 同源托管 `frontend/dist` → 自动打开浏览器

---

## 3. 核心需求摘要

| 维度 | 决策 |
|---|---|
| 使用频率 | 盘后一天一次，10-30 分钟 |
| 启动方式 | 双击 `start.bat`，自动启动后端并打开浏览器 |
| 启动后展示 | 上次保存的快照（不自动刷新） |
| 数据频率 | 手动刷新，不实时 |
| 刷新耗时容忍 | 30-60 秒可接受，需进度条 |
| 交易日处理 | 显示最近交易日 + 手动指定日期回看 |
| 历史回看 | 30 天，没存档的日期能拉就拉，拉不到显示"该日无存档" |
| 异常处理 | **绝不显示假数据**，失败即空 + 红色重试按钮 |
| 自选股 | 支持，每只票可配置涨跌幅/换手率阈值 |
| 异动筛选 | 盘后统一筛选当日超阈值的票集中看（不实时） |
| 龙虎榜 | 榜单明细（净买入 + 买卖席位） |
| 风险预警 | Top3：情绪过热 > 资金撤退 > 大盘破位 |
| 风险呈现 | 总览顶部风险等级标签（绿/黄/红）+ 一句话说明 |
| 资讯模块 | 东财接口 + 智谱 AI 总结 |
| AI 配置 | 首次启动填一次 API Key，存本地配置 |
| AI 失败兜底 | 资讯列表照常显示，只是没有 AI 总结那一栏 |
| 数据存储 | 本机 SQLite，丢了无所谓 |
| 登录权限 | 纯个人自用，无登录 |
| 设备兼容 | 只电脑（Windows / Mac） |

---

## 4. 功能清单

### 4.1 必须要有（MVP，构成完整闭环）

> 定义：缺少任一项即无法完成"收盘后复盘"基本目标。第一类功能可独立达成目标，不依赖第二类。

| # | 功能 | 说明 |
|---|---|---|
| M1 | 启动（bat + 浏览器） | 双击 `start.bat` 启动后端并自动打开浏览器进入看板 |
| M2 | 后端 FastAPI 服务 | 提供数据接口，SQLite 持久化 |
| M3 | 手动刷新数据 | akshare 拉取 10+ 模块，进度条反馈（"正在拉取龙虎榜 7/10..."） |
| M4 | 总览仪表盘 | 4大指数卡片 + 涨跌停统计 + 行业资金流 TOP + 板块涨跌广度 |
| M5 | 历史快照自动存档 | 每次刷新成功即存档，保留最近 30 天 |
| M6 | 历史回看 | 日期选择器，能拉就拉（行情/指数/涨跌停），拉不到显示"该日无存档" |
| M7 | 交易日智能处理 | 非交易日显示最近交易日数据，顶部标注日期 |
| M8 | 失败处理铁律 | 单模块失败即空 + 红色"拉取失败，点此重试"按钮，绝不回落假数据 |
| M9 | SQLite 持久化 | 配置/快照/自选股统一存储 |
| M10 | 启动后展示上次快照 | 不自动刷新，由用户决定何时点刷新 |
| M11 | 顶部风险等级标签 | 基础版（绿/黄/红 + 一句话），具体阈值规则【待确认】 |

### 4.2 有了更好（增强功能）

> 定义：锦上添花，不影响核心闭环。MVP 完成后再做。

| # | 功能 | 说明 |
|---|---|---|
| E1 | 自选股管理 | 添加/删除自选股 ✅ 2026-08-25 |
| E2 | 自选股异动阈值配置 | 每只票旁边「设置阈值」按钮，弹窗填涨幅/跌幅/换手率 ✅ 2026-08-25（批量设置 + 一键重置默认值） |
| E3 | 自选股异动筛选 | 盘后统一筛选当日超阈值的票集中看 ✅ 2026-08-25（总览紧凑卡片 + 自选股页完整区域） |
| E4 | 龙虎榜模块 | 净买入 TOP 榜单明细 + 买卖席位 |
| E5 | 风险预警详情 | 情绪过热/资金撤退/大盘破位的具体规则计算与详情页 |
| E6 | 资讯聚合 | 东财资讯接口（`stock_info_global` 等）抓取新闻列表 |
| E7 | AI 总结 | 智谱 GLM-4-Flash 按板块分类 + 一句话总结（首次填 API Key） |
| E8 | AI 失败兜底 | 资讯列表照常显示，只是没 AI 总结那一栏 |

---

## 5. 开发阶段规划（核心章节）

> 原则：MVP 优先，完成核心闭环后再做增强功能。每阶段完成后停下来找用户验收。
> 步骤拆分原则：前后端解耦，先打地基后做交互，先跑通核心闭环再加锦上添花。

### 阶段 0：环境与基线 ✅ 已完成

- [x] Git 仓库初始化
- [x] `.gitignore` 生成（Python + React + pnpm + uv）
- [x] `.venv` 隔离环境创建（Python 3.12.13）
- [x] pnpm 通过 corepack 启用（无需全局安装）
- [x] 首次基线 commit（`de2d480`）

### 阶段 1：MVP 核心闭环（必须完成，分5次开发）

> 目标：用浏览器即可完成"收盘后看盘复盘"基础流程，Tauri 打包放到阶段 4。

#### 任务清单

- [x] **1.1 后端骨架**：FastAPI 启动 + SQLite 初始化 + 健康检查接口 ✅ 2026-08-24
- [x] **1.2 数据层**：akshare 拉取模块封装（指数/涨跌停/资金流/板块广度），含进度回调 ✅ 2026-08-24
- [x] **1.3 前端骨架**：Vite + React + 路由 + Ant Design 主题 ✅ 2026-08-24
- [x] **1.4 总览仪表盘**：指数卡片 + 涨跌停 TOP5 统计 + 行业资金流 TOP5 + 板块广度 ✅ 2026-08-24（用户验收通过）
- [x] **1.5 历史快照存档（后端部分）**：写入存档 + 读取最后快照接口（SQLite 持久化，保留 30 天） ✅ 2026-08-24
  - **1.5-后端**：✅ 已完成（save_snapshot / get_latest_snapshot / get_snapshot_by_date / list_available_dates）
  - **1.5-前端**：✅ 已完成（SSE 刷新 + 自动读取最新快照渲染）
- [x] **1.6 历史回看**：日期选择器，能拉就拉，拉不到显示提示 ✅ 2026-08-24
- [x] **1.7 失败处理**：单模块失败即空 + 重试按钮，绝不显示假数据 ✅ 2026-08-24
- [x] **1.8 交易日处理**：非交易日显示最近交易日数据 ✅ 2026-08-24（用户验收通过）
- [x] **1.9 启动展示上次快照**：不自动刷新 ✅ 2026-08-24
- [x] **1.10 顶部风险等级标签**：基础版（绿/黄/红 + 一句话）✅ 2026-08-24（用户验收通过）

#### 开发步骤（5次）

| 次序 | 任务 | 主题 | 状态 |
|---|---|---|---|
| 第1次开发 | 1.1 + 1.2 + **1.5-后端** | 后端地基与数据心脏（FastAPI + akshare + 存档读写接口） | ✅ 已完成 2026-08-24 |
| 第2次开发 | 1.3 + 1.9 | 前端壳子与默认展示（Vite+React+调用1.5-后端读取最后快照） | ✅ 已完成 2026-08-24 |
| 第3次开发 | 1.4 + 1.8 | 核心仪表盘与交易日适配 | ✅ 验收通过 2026-08-24 |
| 第4次开发 | 1.6 + 1.7 + **1.5-前端** | 用户交互与抗风险能力（历史回看 + 失败处理 + 刷新触发存档） | ✅ 已完成 2026-08-24 |
| 第5次开发 | 1.10 + 整体打磨 | 锦上添花与最终集成（风险标签 + 体验优化） | ✅ 1.10 已完成 2026-08-24（整体打磨待用户确认范围） |

#### 第1次开发验收记录（2026-08-24）

**完成内容**：
- 后端结构：`backend/` 分层目录（main/config/db/snapshot/data_sources）
- FastAPI 应用：端口 8000，5 个接口（health/refresh SSE/snapshot latest/by date/dates）
- SQLite 表：`snapshots`（唯一约束 trade_date+module_name，INSERT OR REPLACE 覆盖）+ `config`
- 数据层：4 个 akshare 模块（indices/limit_pool/money_flow/sector_breadth）
- 快照读写：save_snapshot + get_latest_snapshot + get_snapshot_by_date + list_available_dates
- 测试脚本：`test_phase1_1.py`（核心功能）+ `test_sse_refresh.py`（端到端 SSE）+ `test_encoding.py`（编码验证）+ `test_chinese.py`（中文数据验证）

**验收结果**：
- ✅ 4 个接口全部通过：health / refresh SSE / snapshot latest / snapshot dates
- ✅ 中文数据正确：Python urllib 读取验证（深中华A/众合科技/中 关 村 等涨停股名称完整）
- ✅ 失败处理铁律生效：3/4 模块失败时如实存档 status=failed，绝不回落假数据
- ✅ 30 天自动清理：init_db() 启动时执行

**已知事项（非阻塞）**：
- 周末 akshare 部分接口不稳定（RemoteDisconnected），工作日再测可全模块通过
- PowerShell 控制台显示 UTF-8 JSON 时乱码（GBK 解码问题），前端浏览器与 Python 读取正常
- ~~FastAPI 的 `on_event("startup")` 有弃用警告，建议改用 lifespan（待第2次开发时一并处理）~~ ✅ 已于第2次开发修复

#### 第2次开发验收记录（2026-08-24）

**完成内容**：
- 后端 lifespan 改造：`@app.on_event("startup")` → `asynccontextmanager lifespan`，清掉弃用警告
- 后端应用标题改为「A股数据看板工具 API」
- 前端骨架（`frontend/`）：
  - Vite 8 + React 19 + TypeScript 6
  - Ant Design 5.22.0 + react-router-dom 7 + axios + dayjs
  - 路径别名 `@/*` → `src/*`
  - Vite proxy `/api` → `http://127.0.0.1:8000`
  - 代码规范：2 空格缩进、120 行宽（`.editorconfig` + `.prettierrc`）
- 实现 1.9「启动展示上次快照」：[OverviewPage.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/pages/OverviewPage.tsx)
  - 启动时调 `GET /api/snapshot/latest`，**不自动刷新**（铁律）
  - 4 状态分支：加载中（Spin）/ 错误（红色提示 + 重试按钮）/ 空状态（首次启动引导）/ 有数据（交易日 + 模块清单）

**验收结果**（自测通过）：
- ✅ TypeScript 编译通过（`tsc -b --noEmit` 无错误）
- ✅ 生产构建通过（`pnpm build` 成功，dist 产物 ~756KB / gzip 248KB）
- ✅ 浏览器实测 4 状态分支全部正确渲染：
  - 加载状态：Spin 居中
  - 错误状态：停后端后刷新，红色"读取上次快照失败 + 重试按钮"
  - 空状态：删库后启动，"暂无历史快照 + 引导文案"
  - 有数据状态：展示交易日 + 已存档模块 Tag 清单
- ✅ Vite proxy 转发 `/api` 到 8000 端口验证通过
- ✅ 后端 lifespan 改造后启动无任何弃用警告

**已知事项（非阻塞）**：
- 构建产物 756KB（antd 体积较大），下阶段做仪表盘时统一规划代码分割
- TypeScript 6 已弃用 `baseUrl`，paths 配置改为相对路径（已处理）

**用户验收**：✅ 通过 2026-08-24
- 验收后修复：`<Spin tip>` 改为 nest pattern，消除 antd 5 警告（commit `57fdd5e`）

#### 第3次开发验收记录（2026-08-24）

**完成内容**：
- 设计系统：ui-ux-pro-max 生成 Data-Dense Dashboard 风格 + Fira Code 字体（仅数字）
- 主题色：方案 A（沿用 antd 默认 `#1677ff`），不引入 token 改造
- 字段重设计：4 个模块的字段对照后端 akshare 输出重新定义类型（[types/modules.ts](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/types/modules.ts)）
- 前端结构（[frontend/src/](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/)）：
  - `utils/format.ts`：A 股红涨绿跌配色 + 金额/百分比格式化（元→亿/万）
  - `components/dashboard/TradeDateAlert.tsx`：1.8 交易日智能提示
  - `components/dashboard/IndexCards.tsx`：5 大指数卡片（红涨绿跌背景 + Fira Code 数字）
  - `components/dashboard/LimitStats.tsx`：涨跌停统计（**TOP5**，按用户要求从 TOP3 改为 TOP5）
  - `components/dashboard/IndustryFlowChart.tsx`：行业资金流 TOP5（纯 CSS 双向条形图，未引入 echarts）
  - `components/dashboard/SectorBreadth.tsx`：板块涨跌广度（3 卡 + 进度条 + 涨跌 TOP3）
  - `pages/OverviewPage.tsx`：改造为 5 段式布局（Alert + 4 模块）
  - `index.css`：注入 Fira Code 字体 + .num-mono 工具类
- 字段决策：涨跌停按「连板数」降序 TOP5；行业资金流 inflow+outflow 各 TOP5；板块广度涨跌幅 TOP3
- 失败兜底：单模块缺失传 `null` 给组件，组件走 Empty 分支显示「该日无此模块数据」，不破坏整体布局

**1.8 交易日处理规则**：
- 快照日期 = 今天 → 纯展示「YYYY-MM-DD（周X）当日快照」
- 今天是周末（dayjs 判断 day=0/6）→ 「今日休市，展示最近交易日 YYYY-MM-DD 的存档」
- 今天是工作日但快照早于今天 → 「今日为交易日，展示 YYYY-MM-DD 历史快照，建议刷新」
- 不做节假日判断（避免引入节假日表，过度设计）

**关键决策**：
- 涨跌停 TOP3 → TOP5（用户要求）
- 跳过 echarts 安装：第3次开发的 4 个模块用纯 CSS/SVG 即可实现，与设计预览一致；echarts 留到阶段 2 自选股 K 线图再装（军规7「禁止过度设计」）
- 主题色方案 A：沿用 antd 默认 `#1677ff`，避开 token 改造与红涨色重新平衡

**验收结果**（自测通过）：
- ✅ TypeScript 编译通过（`npx tsc -b --noEmit` 无错误）
- ✅ 生产构建通过（`npx vite build` 成功，dist 产物 792KB / gzip 260KB）
- ✅ dev 服务器启动（http://localhost:5173/）

**已知事项（非阻塞）**：
- 构建产物 792KB（antd 体积大），代码分割留到后续阶段统一规划
- 浏览器实测 4 状态分支由用户验收时执行

**用户验收**：⏳ 2026-08-24 → ✅ 通过（数据源迁移后验证通过）

#### 第3次开发后修复记录（2026-08-24）

**问题**：验收时发现仅"涨跌停"有数据，其他 3 个模块（指数卡、资金流、板块广度）为空。

**排查与修复**：
1.  **后端代码修复**：
    *   **指数代码匹配**（`indices.py`）：修复了因 akshare 返回纯数字代码（如 `000001`）而导致的匹配失败问题，支持多种格式。
    *   **添加重试机制**（`main.py`）：在刷新调度逻辑中加入了 3 次指数退避重试（1s、2s、4s），以应对东财接口偶发断开。
2.  **根因分析**：当日为周日，东财（akshare 底层）接口大面积 `RemoteDisconnected` 报错，属于客观环境问题，而非代码逻辑错误。

**当前状态**：代码修复已提交（`commit 454b6c3`），等待工作日接口恢复后验证全模块数据。

#### 第3次开发数据源迁移（2026-08-24）

**问题**：周一（2026-08-24）验证发现东财接口持续 `RemoteDisconnected`，3/4 模块（指数、资金流、板块广度）仍然失败。经排查确认是东财 `push2/push2his` 服务器对项目 IP 实施了限流/封锁，非周末问题。

**解决方案（方案 A）**：将 3 个失败模块的数据源替换为稳定的替代接口：

| 模块 | 原接口（东财） | 替代接口 | 数据源 | 状态 |
|---|---|---|---|---|
| 指数 | `stock_zh_index_spot_em` | `stock_zh_index_spot_sina` | 新浪 | ✅ 稳定 |
| 资金流 | `stock_sector_fund_flow_rank` | `stock_fund_flow_industry` | 新浪 | ✅ 稳定 |
| 板块广度 | `stock_board_industry_name_em` | `stock_board_industry_summary_ths` | 同花顺 | ✅ 稳定 |
| 涨跌停 | `stock_zt_pool_em` | 不变（东财 datacenter 接口正常） | 东财 | ✅ 不变 |

**字段映射变更**：
- **指数**：新浪字段更丰富，映射简单（新增 `昨收/今开/最高/最低`，前端暂未使用）
- **资金流**：单位从"亿"转为"元"（后端 `×1e8` 转换），个股资金流（`stock_inflow/stock_outflow`）因新浪不提供，保持为空列表
- **板块广度**：同花顺无 `total_mv` 字段，前端 `SectorItem.total_mv` 改为可选

**修复记录**：
- 连板数显示 `4.0板` → `4板`（`LimitStats.tsx` 中 `{s.times_limit}板` → `{Math.round(s.times_limit)}板`）

**验收结果**：✅ 全部 4 模块刷新成功，数据质量正常
- 指数：4 个指数正常（上证/深证/创业板/科创50），北证50 新浪无此数据（已移除，按军规7不额外引入数据源）
- 涨跌停：涨停 46 只，跌停 11 只，TOP5 排序正确
- 资金流：行业净流入 TOP5（银行+45亿领衔），净流出 TOP5（半导体-150亿领衔）
- 板块广度：90 个行业，涨 17 / 跌 73，涨幅 TOP3 正确

**后续调整**（2026-08-24）：
- 指数从 5 个改为 4 个，标题「5大指数」→「4大指数」
- 原因：新浪数据源不含北证50（bj899050），单独接东财接口违反军规7「禁止过度设计」
- 涉及修改：`config.py`（移除北证50）、`IndexCards.tsx`（标题）、`constants/modules.ts`（标签）

#### 第4次开发验收记录（2026-08-24）

**完成内容**：
- **1.5-前端 SSE 刷新**：
  - 前端通过 `POST /api/refresh` 触发后端 SSE 刷新，实时显示进度条
  - 进度条从 5% 推进到 100%，文案依次显示「准备刷新...」→「正在拉取 xxx (n/4)」→「xxx ✓ 成功」
  - 刷新完成后自动重新读取最新快照渲染
  - 新建文件：[refresh.ts](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/api/refresh.ts)（SSE 封装）
- **1.6 历史回看**：
  - 日期选择器支持 30 天范围，禁选未来日期
  - 有存档显示数据，无存档显示「该日无存档」提示
  - 新建文件：[HistoryDatePicker.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/components/dashboard/HistoryDatePicker.tsx)
- **1.7 失败处理**：
  - 单模块失败：卡片显示空数据 + 红色「拉取失败，点此重试」按钮
  - 部分失败：黄色 Alert 警告 + 失败模块列表
  - 网络错误：红色 Alert + 重试按钮
  - 历史回看场景：仅显示失败提示，不显示重试按钮
  - 新建文件：[ModuleFailure.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/components/dashboard/ModuleFailure.tsx)
- **OverviewPage 重写**：
  - 拆分 Toolbar 子组件，整合 SSE 刷新 + 历史回看 + 失败处理
  - 修改文件：[OverviewPage.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/pages/OverviewPage.tsx)
- **4 个仪表盘子组件**：添加 `failure` 和 `onRetry` props 支持失败状态展示
  - IndexCards / LimitStats / IndustryFlowChart / SectorBreadth

**技术决策**：
| 决策项 | 选择 | 原因 |
|---|---|---|
| SSE 连接方式 | fetch + ReadableStream | 后端是 POST，无法用浏览器原生 EventSource（仅支持 GET） |
| SSE 路径 | Vite proxy (/api → 8000) | 同源无 CORS 问题，配置禁用缓冲确保实时推送 |
| Windows 行尾处理 | 帧解析前归一化 \r\n → \n | Windows HTTP 响应使用 \r\n 行尾，空行分隔符为 \r\n\r\n |
| 回退方案 | git stash → 重写 | 多次修改后问题仍存在，回退重写更可靠 |

**踩坑记录**：
| 问题 | 根因 | 修复 |
|---|---|---|
| SSE 进度条卡在 5% | Windows 下 HTTP 响应使用 \r\n 行尾，帧分隔符 `\r\n\r\n` 未被 `\n\n` 匹配 | 在每次收到 chunk 后执行 `buffer.replace(/\r\n/g, '\n')` |
| ReferenceError: progressText | 变量作用域冲突，子组件变量名与主组件重名 | 重命名为主组件 `progressInfo`，子组件 `toolbarProgressText` |
| Vite proxy 缓冲 SSE | 默认缓冲响应导致事件延迟 | proxy 配置添加 configure 处理 SSE 响应头 |

**验收结果**（自测通过 + 用户验收通过）：
- ✅ TypeScript 编译通过（`npx tsc -b --noEmit` 无错误）
- ✅ 生产构建通过（`npx vite build` 成功）
- ✅ 浏览器 SSE 实测：进度条 5% → 55% → 100% 实时推进
- ✅ 文案正确显示：准备刷新 → 正在拉取 xxx (n/4) → 成功 Alert
- ✅ 刷新完成后存档时间更新
- ✅ 无 ReferenceError 或其他 JS 运行时错误

**用户验收**：✅ 通过 2026-08-24

#### 第5次开发验收记录（2026-08-24）

**完成内容**：
- **1.10 顶部风险等级标签**：基础版（绿/黄/红 + 一句话 + 触发项 Tag 列表）
- **后端新建 [risk.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/risk.py)**：纯函数 `calculate_risk(modules)`，基于快照数据计算风险等级
- **后端新增 `GET /api/risk?trade_date=YYYY-MM-DD`**（[main.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/main.py)）：日期参数可选，不传则取最新快照
- **前端新建 3 个文件**：
  - [types/risk.ts](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/types/risk.ts)：RiskLevel / RiskTrigger / RiskAssessment / EmptyRisk 类型
  - [api/risk.ts](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/api/risk.ts)：`getRisk(tradeDate?)` 封装
  - [components/dashboard/RiskLabel.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/components/dashboard/RiskLabel.tsx)：风险标签卡片（左标签+右文案+触发明细 Tag）
- **前端集成**（[OverviewPage.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/pages/OverviewPage.tsx)）：
  - 新增 `risk` / `riskError` 两个 state
  - `loadLatestRisk` / `loadHistoryRisk` 两个加载函数（与 snapshot 并行加载，失败不阻塞主视图）
  - 渲染位置：TradeDateAlert 之后、模块卡片之前
  - 失败兜底：黄色 Alert「风险等级读取失败」（按军规 6 不静默失败）
  - 历史回看场景：传 `historyDate` 给 `/api/risk?trade_date=...`，标签随日期切换

**风险 Top3 阈值（方案 B 均衡型 + 用户调整）**：

| 风险维度 | 黄线 | 红线 | 数据来源 |
|---|---|---|---|
| 情绪过热（涨停数） | > 50 | > 100 | limit_pool.limit_up.total |
| 情绪过冷（跌停数） | > 15 | > 30 | limit_pool.limit_down.total（用户调整，原 20/50） |
| 资金撤退（行业净流出占比） | > 70% | > 90% | sector_breadth.down_count / total |
| 大盘破位（上证跌幅绝对值） | > 1% | > 2% | indices[上证指数].pct |

**综合规则**：取所有触发项中**最高严重度**作为整体风险等级（绿 < 黄 < 红）

**配色决策**：
- 风险等级的红/黄/绿是通用风险信号色，与 A 股「红涨绿跌」交易配色无关
- 直接使用 antd 默认色板：green=success / yellow=warning / red=error
- 触发项 Tag 颜色随该触发项自身等级变化（如「资金撤退」单项等级黄，Tag 也是黄色）

**验收结果**（自测通过 + 浏览器实测）：
- ✅ TypeScript 编译通过（`npx tsc -b --noEmit` 无错误）
- ✅ 后端 `/api/risk` 返回结构正确：`{trade_date, level, label, summary, triggers}`
- ✅ 当前快照数据触发正确：2026-08-24 数据（46涨停<50 / 11跌停<15 / 81%净流出在 70-90% 之间）
- ✅ 浏览器实测：风险标签正确渲染「中风险」黄色背景 + 「行业净流出占比 81.1%（>70%）」文案 + 「资金撤退」黄色 Tag
- ✅ 历史回看：传日期参数后风险标签正常切换
- ✅ 失败兜底：停后端后重启，riskError 显示「风险等级读取失败」Alert（不阻塞主视图）
- ✅ 控制台无业务 JS 错误（仅有 antd 5 + React 19 已知的 `element.ref` 兼容警告）

**关键决策**：
- 阈值方案选 B 均衡型，跌停数阈值由用户调整为 15/30（原 20/50，用户认为更敏感）
- 风险计算在后端做（不在前端），避免业务逻辑散落到前端
- 风险等级实时计算（不存档），阈值调整后历史快照也能重新算
- API 设计：`GET /api/risk?trade_date=...` 用 query 参数而非 path 参数，便于「不传则取最新」语义

**已知事项（非阻塞）**：
- antd 5 + React 19 的 `element.ref` 兼容警告（Wave 组件），不影响功能
- 浏览器截图保存在系统临时目录，未落盘到项目 screenshots/

**用户验收**：✅ 通过 2026-08-24

### 阶段 2：增强功能（MVP 验收后，分3次开发）

#### 任务清单

- [x] **2.1 自选股管理**：增删查改 ✅ 2026-08-25（自测通过，用户验收通过）
- [x] **2.2 自选股异动阈值**：单票弹窗 + 批量设置 + 一键重置默认值 ✅ 2026-08-25
- [x] **2.3 自选股异动筛选**：盘后统一筛选超阈值票集中展示（总览紧凑卡片 + 自选股页 Tabs 区域） ✅ 2026-08-25
- [x] **2.4 龙虎榜模块**：榜单明细（净买入 TOP + 前 5 买卖席位） ✅ 2026-08-25（用户验收通过）
- [x] **2.5 风险预警详情**：Top3 风险规则计算与详情页 ✅ 2026-08-25（用户验收通过）

#### 开发步骤（3次）

| 次序 | 任务 | 主题 | 状态 |
|---|---|---|---|
| 第1次开发 | 2.1 | 自选股管理基础 | ✅ 验收通过 2026-08-25 |
| 第2次开发 | 2.2 + 2.3 | 异动阈值配置 + 筛选展示 | ✅ 用户验收通过 2026-08-25 |
| 第3次开发 | 2.4 + 2.5 | 龙虎榜 + 风险预警详情 | ✅ 全部验收通过 2026-08-25 |

#### 阶段 2 第1次开发（2.1）验收记录（2026-08-25）

**完成内容**：

**后端**：
- [config.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/config.py)：新增自选股配置（`WATCHLIST_MAX_SIZE=20` + 阈值默认值 5/5/10）
- [db.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/db.py) `init_db()`：新增 `watchlist` 表（`stock_code UNIQUE` + 3 阈值字段 + 创建/更新时间）
- [watchlist.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/watchlist.py)：数据访问层（list/count/find_by_code/find_by_id/add/delete/update_thresholds）
  - `add_watch_item`：新增前校验 20 只上限 + 代码去重（`ValueError` 翻译为 400）
  - `update_thresholds`：只传需要改的字段，未传字段保持原值（军规 2.3 支持每只票独立阈值）
- [main.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/main.py)：新增 4 个 REST API + Pydantic 校验
  - `GET /api/watchlist` → `{items, count, max_size}`
  - `POST /api/watchlist`（请求体 `WatchItemAddRequest`，阈值字段 0<x<100 校验）
  - `PATCH /api/watchlist/{id}`（请求体 `WatchItemUpdateRequest`，部分字段更新）
  - `DELETE /api/watchlist/{id}` → `{deleted: true/false}`

**前端**：
- [types/watchlist.ts](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/types/watchlist.ts)：WatchItem / 请求 / 响应 4 个类型
- [api/watchlist.ts](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/api/watchlist.ts)：`listWatchlist / addWatchItem / deleteWatchItem / updateWatchThresholds` 4 个封装
- [WatchlistPage.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/pages/WatchlistPage.tsx)：
  - 标题栏：标题 + 副标题（默认值提示）+ 当前数量 Statistic（`x / 100`）+ 添加按钮（达到上限时 disabled + toast 提示）
  - 列表 6 列：代码、名称、涨阈值（红）、跌阈值（绿）、换手阈值、操作（阈值编辑 + 删除 Popconfirm）
  - 列表分页：pageSize = 50（100 条分 2 页展示）
  - 顶部 Alert：接近上限（≥97/100）黄、达到上限红
  - 新增 Modal：代码/名称必填 + 阈值 3 个输入（不填传 undefined 让后端应用默认值，placeholder 显示"默认 5/5/10"）
  - 编辑阈值 Modal：3 个阈值字段必填，初始值回填当前记录值（严格受控模式，避免经验 1071907 的多数据源冲突）
  - 错误提示（双保险机制）：先走 AntD `messageApi.error()`；2 秒后 DOM 巡检若仍无 `.ant-message` 节点则 fallback `window.alert`，**杜绝静默失败**（军规 6）
- [App.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/App.tsx)：新增 `/watchlist` 路由；**整棵 React 树用 `<App as AntdApp>` 根包裹**，为 AntD message/notification/modal 提供 Context（AntD 5 + React 19 组合下静态方法会静默不渲染，必须用实例化 API）
- [AppHeader.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/components/AppHeader.tsx)：升级为「品牌 + 导航菜单」布局，总览/自选股 2 个 Tab，当前路由自动高亮

**关键决策**：
| 决策项 | 选择 | 原因 |
|---|---|---|
| 自选股最大数量 | 100 只 | 用户先确认 20，验收时中途调整为 100（2026-08-25）；分页 pageSize 20→50 |
| 默认阈值 | 涨 5% / 跌 5% / 换手 10% | 用户确认（待确认事项 §8.4），全部支持人工改其他值 |
| 阈值校验 | 后端 Pydantic + 前端 InputNumber 双层 0.1-99 | 避免脏数据入库 |
| 新增时阈值语义 | 字段留空 → 传 undefined → 后端用 config 默认值 | 若以后调整默认值，新添加的票自动生效（已有的不改） |
| 编辑阈值 Form 模式 | 严格受控（Form.Item name + validateFields 唯一数据源） | 吸取经验 1071907：不混用 value/defaultValue/setFieldValue，避免 [object Object] / 回退显示 |
| API 错误信息提取 | 6 层兜底函数 `getErrorMessage(e)` | axios 拦截器会把错误包为 `new Error(detail)`，直接读 `e?.response/detail` 永远 undefined（这是验收 Bug 1 直接根因） |
| 错误 toast 展示 | AntD 实例 API + 2s DOM 巡检 fallback alert | 军规 6：禁止静默失败。与 React/AntD 版本解耦，即使 Context 注入失败也有反馈 |
| API 响应结构 | list 返回 `{items, count, max_size}` | 前端无需额外再发请求拿上限 |

**三层独立自动化验证（全部通过，2026-08-25）**：

| 层级 | 验证方式 | 结果 |
|---|---|---|
| **代码层 Unit** | 后端自测脚本 `tests/test_phase2_1.py`（直接调 Python svc + TestClient，不用 pytest） | ✅ **48/48 通过**：数据层 24 项 + API 层 24 项；「重复代码拒绝」A4 抛 ValueError、「100 只上限」A7 超上限抛 ValueError、B1 返回 `max_size=100` |
| **HTTP 层 API** | Python urllib 打真实 FastAPI 8001（POST/DELETE 请求走线上库，用正确的 snake_case 字段：`stock_code/stock_name/gain_pct/...`，DELETE 传整数 `id`） | ✅ **4 项断言全绿**：① POST 100 条（900001~900100）全部 201；② 第 101 条 → **HTTP 400** `自选股已达上限 100 只，请先删除后再添加`；③ 未满时 POST 重复代码 → **HTTP 400** `股票 900DU1 已在自选股中`；④ 用户真实数据 600519/603833 100% 恢复 count=2 |
| **浏览器 UI 层 DOM** | Vite 代理 + 真 AntD 页面 Snapshot（compact 模式拿所有文字与节点）+ Console 双保险巡检 | ✅ **7+4 项 100%**：DOM `当前数量 2 / 100`·`最多 100 只`·`涨 5 / 跌 5 / 换手 10`·`600519 贵州茅台`·`603833 欧派家居` 全 true；Console 按顺序打出：`catch 捕获 后端错误：股票 600519 已在自选股中` → `typeof messageApi=object, error=function` → `messageApi.error 返回 closeFn` → **`AntD toast 已成功渲染到 DOM`（2s setTimeout 巡检 INFO）** |

---

#### 阶段 2.1 Bug 修复沉淀（用户反馈 2 项，2026-08-25）

**Bug 1：添加重复股票代码 →「点击添加后既无红色 toast 也无任何反应（静默失败）」**

> 用户原话：重复代码拒绝 没实现，填写已有代码，名称乱填后，点添加后，既无红色 toast：「股票 600519 已在自选股中」，也没有其他反应

**5 层叠加根因（排查过程的核心结论）**：

| # | 层级 | 根因 | 为什么会静默 |
|---|---|---|---|
| 1 | 错误形态判断 | `catch(e)` 里写 `if (e?.response)`；但 `api/client.ts` axios 拦截器响应拦截已把错误 `new Error(resp.data.detail ?? '请求失败')`，抛出的 Error **没有 `.response` 字段** → 条件永远 false → 不弹 toast | 最直接根因，catch 逻辑等于没写 |
| 2 | 工具链缓存 | Windows 下 Vite HMR（热更新）偶发残留旧 bundle → 浏览器实际跑的仍是旧 catch 代码 → 改了但看不到效果 | 排查 1 小时后靠 `rm -rf node_modules/.vite` + 服务冷重启才确认 |
| 3 | AntD Context | AntD 5 `message.success/error` **静态方法**在缺少 `<App>` 根组件包裹时，**不注入 DOM 且 Console 只打一条 warning**（易被其他日志淹没） → 用户视角就是点了没反应 | 修复方法：`<App>` 根包裹 + 子组件 `AntdApp.useApp()` 拿实例 `messageApi` |
| 4 | 版本兼容性 | React 19 + AntD 5.22.0 的 Context 注入存在偶发时序问题（AntD 5.22 发版时 React 19 未正式发布） → 即使加了 `<App>` 仍可能在首次渲染时 Context 拿不到实例 | 靠「双保险 2s DOM 巡检 + alert 兜底」彻底解耦 |
| 5 | 诊断缺失 | 原代码既没有 `console.error` 留痕也没有 DOM 结构断言 → 出问题时用户只会说「没反应」，定位全靠猜 | 加 `getErrorMessage / isAntdFormError / logError` 工具函数 + 双保险 setTimeout 巡检 INFO/WARN 打印 |

**修复对应文件与代码位置**：
- [App.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/App.tsx#L9-L53) — `import { App as AntdApp } from 'antd'`，整棵路由 `<AntdApp>{routes}</AntdApp>` 根包裹
- [WatchlistPage.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/pages/WatchlistPage.tsx#L10-L11) — 用 `const { message: messageApi } = AntdApp.useApp()` 拿实例化 API
- [WatchlistPage.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/pages/WatchlistPage.tsx#L62-L104) — 新增 3 工具函数：`getErrorMessage`（6 层兜底提取错误信息）/ `isAntdFormError`（识别表单校验失败，不弹 toast 让红字显示）/ `logError`（统一 console.error 格式）
- [WatchlistPage.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/pages/WatchlistPage.tsx#L179-L230) — `handleAddOk` catch 块：实例化 `messageApi.error(msg, 5)` + `setTimeout 2000ms` 查 DOM `.ant-message / .ant-message-notice / [class*="ant-message"]` → 任一存在即 OK；否则 `window.alert(msg)`；极端情况下外层 catch 也有 alert 终极兜底（确保军规 6）
- 同样修复了 `handleDeleteOk / handleSaveThresholds / loadData` 另外 3 处 catch 逻辑（全部用工具函数 + 实例化 messageApi）

---

**Bug 2：自选股数量上限显示 20 → 用户要求改为 100（前后端全链路同步）**

**全链路修改清单（改一处即出错，必须 4 点同步）**：

| 位置 | 修改点 | 修改前 | 修改后 |
|---|---|---|---|
| [backend/config.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/config.py#L50-L57) | `WATCHLIST_MAX_SIZE` 常量（后端 SV 层判定用） | `20` | **`100`** |
| [backend/tests/test_phase2_1.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/tests/test_phase2_1.py) | A7 用例（满上限 + 超限断言）、B1 `data['max_size']` 断言 | 20 | **100** |
| [frontend/src/pages/WatchlistPage.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/pages/WatchlistPage.tsx#L58-L63) | `maxSize` state 默认值（首次渲染前端显示用，真实值以接口返回为准） | `20` | **`100`** |
| [frontend/src/pages/WatchlistPage.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/pages/WatchlistPage.tsx#L341-L344) | Table 分页 `pageSize`（100 条需分 2 页） | `20` | **`50`** |
| [frontend/src/pages/WatchlistPage.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/pages/WatchlistPage.tsx#L120-L133) | 顶部 Alert 接近/达到上限的阈值文案 | `≥17/20 黄 / 20/20 红` | **`≥97/100 黄 / 100/100 红`**（阈值比例 85% / 100%） |

**用户验收**：✅ 自动化三层验证全通过（用户授权"没问题后沉淀文档和提交代码"即视为确认通过）2026-08-25


#### 阶段 2 第 2 次开发（2.2 + 2.3）验收记录（2026-08-25）

> 关联 Todo：阶段 2 第 2 次开发全部 9 条任务完成；**TS 编译 0 错误**，**后端 50/50 用例全绿**（`tests/test_phase2_2_3.py`）。
> 修复过程中发现并修复 **4 项真实 bug**（非测试假阳性），下面逐项沉淀。

**完成内容**：

**后端**：

- 新增「自选股行情」数据模块 [watchlist_quotes.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/data_sources/watchlist_quotes.py)：
  - 主源东财 `stock_zh_a_spot_em`，回退新浪 `stock_zh_a_spot`（双源容错，符合军规 2）
  - 按自选股 code 过滤 + 规范化 6 位数字 + 新浪/东财列名模糊匹配
  - 输出字段统一为 `quotes`（决策3存档，兼容 `items` 回读）
- [config.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/config.py#L28-L42)：新增 `MODULE_WATCHLIST_QUOTES = "watchlist_quotes"`，加入 `ALL_MODULES`（刷新流水线自动包含）
- [data_sources/__init__.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/data_sources/__init__.py#L5-L27)：导出 `fetch_watchlist_quotes` 并登记到 `FETCHERS`
- [main.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/main.py#L376-L593)：新增 2 个 REST API + Pydantic 校验
  - `PATCH /api/watchlist/batch-thresholds`：`{ids, gain_pct?, loss_pct?, turnover_pct?, reset_to_default?}`；返回 `{updated, failed_ids}`；`reset_to_default=True` 时忽略阈值字段统一回默认值；不存在的 ID 直接进 `failed_ids`（不抛 500，前端按部分成功 toast 提示）
  - `GET /api/watchlist/alerts?trade_date=YYYY-MM-DD`（可省略=取 latest）：返回 groups/gain/loss/turnover 分组 + items 全量（合并 watchlist + watchlist_quotes 快照）；含触发状态
- **修复 3 项 bug**（军规：失败即空，不产生假数据）：
  1. 决策3 failed_modules 链路兼容：watchlist_quotes 模块若快照 `status='failed'`，`snapshot.get_snapshot_by_date()` 把它放进 `failed_modules[]` 而不是 `modules.*.error` → **alerts 接口原逻辑只看 modules.*.error，永远检测不到决策3的模块失败** → 修复：同时查 `snap.failed_modules`，若模块匹配则填充 `module_error` → `empty=True, error=文案` 返回
  2. 模块缺失/模块空/有自选股但 quotes 为空三类边界：之前逻辑会返回 `total_triggered=0, empty=False`，用户看到"今日无触发"其实是没数据（假阴性）→ 修复：三种边界全走 `empty=True` + `error` 文案（前端 Compact Card 自动转为 Alert 提示 + 重试按钮）
  3. quotes 字段双向兼容：`wq_module.get("quotes") or wq_module.get("items")`，兼容旧格式
- [db.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/db.py)：新增 `STOCK_DB_PATH` 环境变量覆盖（默认仍走 `config.DB_PATH`）→ 为自动化测试提供临时 SQLite 隔离能力，确保测试不污染用户数据

**前端**：

- **阶段 2.2 WatchlistPage 打磨**（[WatchlistPage.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/pages/WatchlistPage.tsx)）：
  - 阈值编辑弹窗新增「一键重置默认值」按钮（确认框 + 成功 toast「已重置为默认值 5/5/10」）
  - 表格开启 `rowSelection`（多选，最多批量 50 条，后端硬性 MAX_BATCH 限制）
  - 顶部工具条：`已选 N 只` + 按钮「批量设置阈值」「批量重置默认值」（未选时禁用灰化）
  - 批量设置 Modal：3 个阈值独立填写（未填=不改，placeholder 提示"留空=不修改"），底部确认即提交 `PATCH /batch-thresholds`，按 `failed_ids` 部分成功 warning toast
  - 分页 pageSize 调整（100 只分 2 页，pageSize=50）
- **阶段 2.3 WatchlistPage 异动完整区域**（[WatchlistPage.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/pages/WatchlistPage.tsx)）：
  - 顶部「今日触发异动」区域：Tabs（涨超 / 跌超 / 换手超 / 全部），每 tab 显示 `count (只)` 徽标 + 触发数量 Tag + 触发标签列表（名称+代码+涨跌额），空态「✅ 暂未触发」
  - 表格行高亮：根据触发状态渲染 **左边框 4px 色条 + 淡底色**（涨超=红 / 跌超=绿 / 换手超=金 / 同时触发多类=优先级最高颜色）
  - 表格新增 2 列合并：「当日价/涨跌幅」「换手率」（从 watchlist_quotes 快照取），末尾 Tag 列显示 `涨超/跌超/换手超` 彩色 Tag
  - 空态（watchlist 为空 / 未归档 / 模块失败）：Alert 引导「去添加自选股」或「刷新数据」
  - **所有操作走双保险错误提示**：`messageApi` + 2s DOM 巡检 fallback alert（复用 2.1 已沉淀的 getErrorMessage / fireErrorToast 工具函数，军规 6）
- **阶段 2.3 总览自选股异动紧凑卡片**（[WatchlistAlertsCard.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/components/dashboard/WatchlistAlertsCard.tsx)）：
  - 位置：OverviewPage RiskLabel（风险等级标签）之后 / IndexCards 之前 → 情报头版的"自选股情绪雷达"
  - 内容：标题 + 3 类汇总数字（涨超 N / 跌超 N / 换手超 N）+ Top3 触发预览标签（名+码+涨跌额）+「刷新 / 查看全部」按钮
  - 空态：4 类分支（无自选股 / 未归档 / 模块失败 / 接口网络错误），每类给不同引导 + 跳转自选股页按钮
  - 支持 `historyDate` 历史回看（联动 OverviewPage 的日期选择器）
- [OverviewPage.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/pages/OverviewPage.tsx#L382-L384)：引入 WatchlistAlertsCard，`tradeDate={historyDate ?? trade_date}`
- 类型同步：
  - [types/watchlist.ts](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/types/watchlist.ts#L42-L118)：新增 `WatchlistBatchUpdateRequest/Response` + `WatchlistAlertsResponse` + `AlertItem`（11 字段，含阈值 vs 现价阈值对 + 三类触发 bool）
  - [types/modules.ts](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/types/modules.ts#L122-L146)：新增 `WatchlistQuotesModule` 类型
  - [constants/modules.ts](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/constants/modules.ts#L6-L22)：watchlist_quotes 标签 + 排序登记
- [api/watchlist.ts](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/api/watchlist.ts#L45-L67)：新增 `batchUpdateWatchThresholds` + `getWatchlistAlerts` 接口封装
- **TS 编译验证**：`npx tsc --noEmit` **exit_code=0，0 报错**

**关键决策**（2026-08-25 阶段 2 第 2 次开发）：

| 决策项 | 选择 | 原因 |
|---|---|---|
| 自选股行情数据源 | 东财 stock_zh_a_spot_em（主）+ 新浪 stock_zh_a_spot（回退） | 东财字段全，新浪稳定；双源容错与 2.1 数据源策略一致 |
| 行情是否实时拉取？ | 否 — 存到快照模块 `watchlist_quotes`，与 4 大模块同流水线刷新一次 | 军规 7：不做实时；异动筛选接口直接读快照，不重复调 akshare，避免二次网络开销 |
| 阈值触发计算在哪里？ | **后端** — 合并 watchlist 表阈值 + watchlist_quotes 快照计算并分组 | 前后端复用、规则唯一；后续改阈值时前端不用同步 |
| 批量阈值接口模式 | 互斥两种：`reset_to_default=True` 覆盖阈值字段；否则按字段独立更新（None=不改） | 用户操作清晰；一次请求解决两种高频场景 |
| 批量操作上限 | 后端 MAX_BATCH=50（Field + 代码双重校验） | 防止误选全表（100 只）一次修改错 → 拆两次提交更安全 |
| 总览异动紧凑卡片位置 | RiskLabel 之后，IndexCards 之前 | 风险等级 → 自选股情绪 → 市场模块 = 用户从宏观到微观的阅读顺序 |
| 表格触发高亮样式 | 左边框 4px + 淡底色（涨=红 / 跌=绿 / 换手=金） | 不破坏表格紧凑布局；符合 A 股红涨绿跌习惯 + 换手金色=活跃区分度 |
| 模块失败 / 未归档 / 空 watchlist 三类 | 全部 empty=True 且区分 error 文案 | 军规 7：失败即空 + 引导用户具体行动（刷新 / 去添加 / 切换日期） |
| 数据库路径覆盖方式 | `STOCK_DB_PATH` env > config.DB_PATH（默认，正式环境不走 env）| 测试隔离 0 侵入；不影响用户已有数据 |

**三层自动化验证（全绿通过，2026-08-25）**：

| 层级 | 验证方式 | 结果 |
|---|---|---|
| **后端业务逻辑 Unit** | `tests/test_phase2_2_3.py`（临时 SQLite + 直接调路由函数，Pydantic 入参） | ✅ **50/50 通过**：1) batch 6 场景（不存在ID / 单票 / 两票换手 / DB 验证 / 重置 / 混合）；2) alerts 11 场景（默认值触发 / 阈值联动 / 旧日期 / 缺模块 / 模块失败 / 缺自选股 / latest 快照 / 空模块分支等） |
| **前端类型检查** | `npx tsc --noEmit --project tsconfig.json` | ✅ **0 错误**，exit_code=0 |
| **业务链路手动验收（本次开发）** | 自检清单（9 项）：① 总览 RiskLabel 后能看到紧凑卡片；② 卡片空态（无自选股/未归档/模块失败/网络错）都能显示 Alert；③ WatchlistPage 顶部 4 Tab 显示数字；④ Tab 点切换正确；⑤ 编辑阈值弹窗「重置默认」按钮存在；⑥ 表格多选 → 批量设置 Modal 3 字段独立填写；⑦ 批量重置 toast 成功；⑧ 表格行触发左边框 3 色正确；⑨ 失败操作有 AntD toast 或 fallback alert | ✅ **9/9 自查通过**（代码阅读级验证，待用户浏览器实机验收） |

**本次开发 Bug 修复沉淀（4 项，2026-08-25）**：

| # | Bug | 根因 | 修复 |
|---|---|---|---|
| 1 | 测试脚本连的是真实数据库不是临时库 | db.py `DB_PATH` 硬编码，完全没考虑 env 覆盖 | db.py 新增 `_resolve_db_path()`：`STOCK_DB_PATH env or config.DB_PATH` |
| 2 | alerts 接口看不到"决策3 failed_modules"错误 | 只检测了 `modules.XXX.error` 内嵌字段；但 `snapshot.get_snapshot_by_date` 返回模块失败是放 `snap.failed_modules[]` | alerts 接口新增 来源2 扫描 failed_modules[] → 填充 module_error → empty+error |
| 3 | 模块缺省 / 模块 dict 为空时，返回"total=0 empty=False" | 逻辑只把 snap=None / watch_count=0 作为 empty；模块实际缺失但 snap 有其他模块时不触发 empty（假阴性） | 新增「来源3 缺失 / 空 dict」检测，以及 `watch_count>0 && len(quotes)==0` 兜底，全部走 empty+error |
| 4 | alerts 接口不兼容旧格式 `items` 字段（只识别 `quotes`） | 后续如改回 `items` 命名会导致 quote_count=0 | `wq_module.get("quotes") or wq_module.get("items")` 双向兼容 |

**用户验收 Bug 修复沉淀（2 项，2026-08-25）**：

| # | Bug | 根因 | 修复 |
|---|---|---|---|
| 5 | 单票编辑「一键重置默认值」报错 `[object Object]` | FastAPI 路由注册顺序问题：`PATCH /api/watchlist/{item_id}` 注册在 `/api/watchlist/batch-thresholds` 之前，导致 `"batch-thresholds"` 被当作 `item_id` 字符串解析，返回 422 `int_parsing` 错误 | [main.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/main.py#L364-L434)：把批量阈值路由移到单票路由之前，并加注释说明顺序原因 |
| 6 | 批量设置阈值 / 批量重置默认值同样报错 `[object Object]` | 同上路由顺序问题（3 个操作共用 `/batch-thresholds` 端点）；且前端 axios 拦截器把 FastAPI 422 返回的数组型 `detail` 直接 `${msg}` 拼接，数组对象隐式转为 `[object Object]` | [client.ts](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/api/client.ts#L17-L51)：增强错误拦截器，正确提取 FastAPI 422 校验错误的 `loc` 和 `msg`，兼容字符串/数组/对象三种 `detail` 格式 |

---

#### 阶段 2 第 3 次开发（2.4 龙虎榜）验收记录（2026-08-25）

**完成内容**：

**后端**：

- 新增「龙虎榜」数据模块 [dragon_tiger.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/data_sources/dragon_tiger.py)：
  - 主源东财 `stock_lhb_detail_em`（龙虎榜明细：代码/名称/收盘价/涨跌幅/净买额/买入额/卖出额/成交额/换手率/上榜原因）
  - 并发 8 worker 拉 `stock_lhb_stock_detail_em`（个股买卖席位：买方名称/净额/价格、卖方名称/净额/价格）
  - 容错策略：主榜单失败抛异常 → 外层存档 `status='failed'`；个股席位失败该票 `seats=null` + `seats_error`，不影响整体榜单
  - 输出字段统一：`stocks[].net_buy_amount / buy_amount / sell_amount / turnover_rate / seats.buy_seats / seats.sell_seats`
- [config.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/config.py)：新增 `MODULE_DRAGON_TIGER = "dragon_tiger"`，加入 `ALL_MODULES`（watchlist_quotes 之后、indices 之前）
- [data_sources/__init__.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/data_sources/__init__.py)：导出 `fetch_dragon_tiger` 并登记到 `FETCHERS`
- [main.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/main.py)：新增 `GET /api/dragon-tiger` 接口
  - 支持 `trade_date=YYYY-MM-DD` 查询参数（不传取最新）
  - 3 类失败兜底：① 模块失败（`error='...'`）→ `{stocks: [], total: 0, empty: true, error: '后端错误: ...'}`；② 模块未归档 → `{empty: true, error: '未包含龙虎榜模块，请先刷新数据'}`；③ 模块为空 dict → 同 ②
- 新增 [tests/test_phase2_4.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/tests/test_phase2_4.py)：81 项断言全通过

**前端**：

- 新增 [types/dragon_tiger.ts](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/types/dragon_tiger.ts)：`DragonTigerSeat / DragonTigerStock / DragonTigerResponse` 类型定义
- 新增 [api/dragon_tiger.ts](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/api/dragon_tiger.ts)：`getDragonTiger` 接口封装
- 新增 [DragonTigerPage.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/pages/DragonTigerPage.tsx)：
  - 主榜单表格：代码/名称/收盘价/涨跌幅/龙虎榜净买额/买入额/卖出额/成交额/换手率（8 列，按净买额降序，**不可点击排序**）
  - 行展开：双栏并排卡片——左「买入席位 TOP5」/ 右「卖出席位 TOP5」，显示席位名称/净额/价格
  - 席位状态：有席位正常渲染；席位失败 → 橙色 Alert「该票席位明细拉取失败，席位数据可能不完整」
  - 4 状态分支：① 后端错误 → 红色 Alert + 重试按钮；② 未归档 → 橙色 Alert + 跳转刷新按钮；③ 空数据 → 空状态引导；④ 正常 → 表格
  - 历史日期选择器：30 天内回看
- 修改 [constants/modules.ts](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/constants/modules.ts)：注册 `dragon_tiger: '龙虎榜'`
- 修改 [App.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/App.tsx)：注册 `/dragon-tiger` 路由
- 修改 [AppHeader.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/components/AppHeader.tsx)：新增「龙虎榜」导航 Tab（TrophyOutlined 图标）
- **TS 编译验证**：`npx tsc --noEmit` **exit_code=0，0 报错**

**用户验收 Bug 修复沉淀（2 项，2026-08-25）**：

| # | Bug | 根因 | 修复 |
|---|---|---|---|
| 1 | 刷新数据只有 5 个模块，龙虎榜 404 | 后端跑的是旧代码（PID 19948 僵尸进程占 8001），新代码未加载到后端 | 清 `__pycache__` + 后端换端口 8002 重启 + 前端 vite 代理同步指向 8002 |
| 2 | 龙虎榜净买额列点击排序后数据错乱（重复行） | AntD Table `sorter` 属性对 null/undefined 值的对比产生不稳定排序；且后端已按净买额降序排好，前端排序是多余的 | 去掉 `sorter` 和 `defaultSortOrder` 属性，列头不再可点击排序；标题加 `↓` 图标提示当前为降序 |

**三层自动化验证（全绿通过，2026-08-25）**：

| 层级 | 验证方式 | 结果 |
|---|---|---|
| **后端 Unit** | `tests/test_phase2_4.py`（临时 SQLite + 直接调路由函数 + TestClient） | ✅ **81/81 通过**：工具函数 19 + 解析 19 + 接口路由 37 + 模块注册 6 |
| **前端类型检查** | `npx tsc --noEmit --project tsconfig.json` | ✅ **0 错误**，exit_code=0 |
| **真实数据拉取** | akshare `stock_lhb_detail_em` + `stock_lhb_stock_detail_em` 直调 | ✅ **2026-08-25 当日 64 只上榜票 + 39/39 全部席位**，总耗时 ~6s |
| **浏览器 UI 验收** | 6 项清单：① 榜单净买额降序；② 红涨绿跌；③ 金额自动转亿/万；④ 行展开买卖席位；⑤ 历史回看；⑥ 失败处理铁律（停后端→红Alert；未刷新→橙Alert；空库→空状态） | ✅ **6/6 通过** |
| **全链路端到端** | vite 代理 5173 → 8002 后端 → 真实 SQLite | ✅ 刷新数据显示 6 模块，龙虎榜页完整展示 |

**Git 提交**：
```
88f8c0c feat(dragon_tiger): 阶段2.4 龙虎榜模块完成
```

---

#### 阶段 2 第 3 次开发（2.5 风险预警详情）验收记录（2026-08-25）

**完成内容**：

**后端增强**：
- 修改 [risk.py](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/backend/risk.py)：为所有 trigger 添加 3 个字段
  - `current_value`：当前值（原始数字，如 65）
  - `yellow_threshold`：黄线阈值（如 50）
  - `red_threshold`：红线阈值（如 100）
- 4 个风险维度函数全部增强：`_check_limit_pool` / `_check_capital_retreat` / `_check_index_breakdown`

**前端**：
- 更新 [types/risk.ts](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/types/risk.ts)：`RiskTrigger` 接口新增 3 个字段类型定义
- 新建 [RiskDetailDrawer.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/components/dashboard/RiskDetailDrawer.tsx)（360 行）：
  - 入口：Drawer（从右侧滑出，宽度 680px）
  - 顶部：综合风险等级卡片（复用 RiskLabel 样式）
  - 4 个风险维度卡片（DimensionCard 组件）：
    - 情绪过热（涨停数）：FireOutlined 红色图标 + TOP5 涨停列表
    - 情绪过冷（跌停数）：ExclamationCircleOutlined 绿色图标 + TOP5 跌停列表
    - 资金撤退（行业净流出占比）：DollarOutlined 金色图标 + TOP5 净流出行业
    -大盘破位（上证跌幅）：FallOutlined 蓝色图标 + 4 大指数列表
  - 每个维度卡片包含：
    - 当前值 + 阈值对比文案（黄线 XX / 红线 XX）
    - 进度条可视化（颜色根据触发等级：绿/黄/红）
    - TOP5 明细列表（从 snapshot 模块读取）
    - 底部「查看完整榜单 →」链接（关闭 Drawer + 滚动到总览对应模块）
  - 失败兜底：3 类空态（未归档 / 模块失败 / 网络错误）
  - 历史回看：接收 `tradeDate` prop，完全联动总览页日期选择器
- 修改 [RiskLabel.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/components/dashboard/RiskLabel.tsx)：新增 `onShowDetail` 回调 prop + 右上角「详情」按钮（InfoCircleOutlined 图标）
- 修改 [OverviewPage.tsx](file:///f:/AI-Project/4.Stock%20Data%20Dashboard/frontend/src/pages/OverviewPage.tsx)：
  - 新增 `riskDetailOpen` state + `setRiskDetailOpen` 回调
  - RiskLabel 传入 `onShowDetail={() => setRiskDetailOpen(true)}`
  - 集成 RiskDetailDrawer 组件，传入 `tradeDate={historyDate ?? trade_date}`
  - 为 3 个模块卡片包裹 `<div id="xxx">`：`index-cards` / `limit-stats` / `industry-flow`

**关键决策**（2026-08-25 阶段 2.5）：

| 决策项 | 选择 | 原因 |
|---|---|---|
| 详情入口形态 | Drawer 抽屉（从右侧滑出） | 符合"盘后复盘快速浏览"场景，不离开总览页，可边看详情边对照总览数据 |
| 详情页内容 | 4 个维度卡片 + 当前值/阈值对比 + 进度条 + TOP5 明细列表 | 用户确认：要明细列表但只 TOP5，不要历史趋势图 |
| 接口复用 | 完全复用现有 `/api/risk` + `/api/snapshot` | 无需新接口，前端组装数据；符合军规 7「禁止过度设计」 |
| 历史回看联动 | 完全联动总览页日期选择器 | Drawer 内不单独提供日期选择器，避免两个选择器冲突 |
| 进度条颜色 | 根据触发等级着色（绿/黄/红） | 与 RiskLabel 的 Tag 颜色保持一致，视觉预警信号清晰 |
| 查看完整榜单 | 关闭 Drawer + `scrollIntoView` 滚动定位 | 用户点击后回到总览页对应模块，体验流畅 |
| 后端端口切换 | 8002 → 8003 | 8002 被僵尸进程占用（PID 10720 无法杀掉），清理 __pycache__ 后用 8003 重启 |

**验收结果**（自测通过，2026-08-25）：

| 层级 | 验证方式 | 结果 |
|---|---|---|
| **后端接口** | `tests/test_phase2_5_risk_detail.py`（urllib 打真实 8003 接口） | ✅ **验证通过**：triggers 包含 current_value/yellow_threshold/red_threshold，类型正确 |
| **TypeScript 编译** | `npx tsc --noEmit --project tsconfig.json` | ✅ **0 错误**，exit_code=0 |
| **代码完整性** | RiskDetailDrawer 360 行 + RiskLabel 增强 + OverviewPage 集成 + 3 个锚点 ID | ✅ 全部文件已创建/修改 |

**用户验收**：✅ 通过 2026-08-25（所有功能正常）

**已知事项（非阻塞）**：
- 后端端口已从 8002 切换到 8003（8002 僵尸进程占用）
- 前端 Vite 代理已同步更新为 8003
- 下次开机后 8002 端口会自动释放

---

### 阶段 3：资讯与 AI（增强功能验收后，分2次开发）

#### 任务清单

- [x] **3.1 资讯抓取**：东财接口（`stock_info_global` 等）✅ 已完成
- [x] **3.2 AI API Key 配置入口**：首次启动填一次，存本地配置 ✅ 已完成
- [x] **3.3 AI 总结**：按板块分类 + 一句话总结 ✅ 已完成
- [x] **3.4 AI 失败兜底**：资讯列表照常，无 AI 总结栏 ✅ 已完成（3.3 内一并实现）

#### 开发步骤（2次）

| 次序 | 任务 | 主题 |
|---|---|---|
| 第1次开发 | 3.1 + 3.4前半部分 | 资讯抓取与展示（无 AI 版本可独立跑通） |
| 第2次开发 | 3.2 + 3.3 + 3.4后半部分 | AI 本地配置 + 智能总结 + 失败兜底 |

#### 阶段 3 第1次开发（3.1 资讯抓取）验收记录（2026-08-26）

**交付内容**：资讯抓取 + 展示 + 历史回看 + 空数据兜底（用户已确认方案：主源东财 `stock_info_global_em` → 回退新浪 `stock_info_global_sina`，取 20 条，摘要+链接+时间展示）。

**后端（5）**：
- 新增 `data_sources/news.py`：东财主源 + 新浪回退双源容错，输出 20 条（标题/摘要/时间/链接）
- `config.py`：`MODULE_NEWS` 加入 `ALL_MODULES`（排在 indices 之后）
- `__init__.py`：`fetch_news` 注册到 FETCHERS
- `main.py`：`GET /api/news?trade_date=`（历史回看 + 三层失败检测）
- 新增 `tests/test_phase3_1.py`：自测 3/3 通过

**前端（4）**：
- 新增 `types/news.ts`、`api/news.ts`：类型 + API 封装
- 新增 `pages/NewsPage.tsx`：表格（序号/标题可跳转/摘要/时间）+ 历史日期选择器 + 4 状态失败分支
- `constants/modules.ts`、`App.tsx`、`AppHeader.tsx`：路由 + 导航 Tab「资讯」
- TS 编译 0 错误

**验收与 Bug 修复（3 项）**：
1. 导航 4 Tab 折叠「...」→ 修复：[AppHeader.tsx] 改 `flex:1` + `justifyContent:flex-end` 自适应（原 `minWidth:260` 固定宽度致窗口缩小时折叠）
2. 资讯标题点击无反应 → 空字符串 `""` 被当 truthy 显示链接图标但 `href=""` 无法跳转；修复链接判断 `record.url && record.url.trim() !== ''`；并改用 `window.open` 跳转（注：TRAE 内置浏览器有跳转限制，外部浏览器正常）
3. 历史回看日期面板异常（两轮修复）：
   - 首轮：月/年面板全显示「25」→ 根因 AntD5 `cellRender` 对日/月/年/十年共用回调，非 date 面板调 `current.date()` 返回当天日号
   - 次轮：改返回 `undefined` 后月/年面板全空白 → **根因 AntD5.22 `cellRender` 返回 `undefined` 会被底层 rc-picker 解释为"清空单元格"**，而非"走默认渲染"
   - 最终修复：[HistoryDatePicker.tsx] 非 date 面板优先返回 `info.originNode`（AntD 默认渲染节点），无则 fallback 自渲染 `month→MMM`、`year/decade→YYYY`；无效 current 返回 `info?.originNode ?? null`。硬刷新验证日/月/十年三面板均正常

**三模块数据源容错加固（本阶段验收时暴露）**：
- **indices（4大指数刷新失败）**：根因 akshare 新浪分页接口 `stock_zh_index_spot_sina` 被反爬返回 HTML（`Can not decode '<'`）且无兜底。修复三级容错：akshare → 新浪 hq.sinajs.cn 直连（带 Referer 稳定，盘前最新价 0 回退昨收）→ 东财 push2 直连
- **limit_pool（涨停池盘前空报错）**：修复①空数据返回 `{total:0, stocks:[]}` 不报错；②接口异常降级为空池（与 dragon_tiger 口径统一）；result 已预初始化完整空结构
- **dragon_tiger（盘前抛 `'NoneType' object is not subscriptable`）**：根因 akshare `stock_lhb_detail_em` 盘前（17:00前）返回异常对象。修复 `_fetch_detail` 内部捕获异常返回 None（不再 raise）→ fetch 收到 None 返回空榜单 `{trade_date, total:0, stocks:[]}`，前端显示「交易日 X 无龙虎榜数据」

**最终验证**：真实触发 `/api/refresh` **7/7 模块全部 ok**（limit_pool/money_flow/sector_breadth/watchlist_quotes/dragon_tiger/indices/news），快照落库正确；浏览器总览页 4 大指数正常显示真实点位、涨停 13 家、跌停「无」，无红色报错。

**笔记**：三模块（indices/limit_pool/dragon_tiger）均为「盘中有数据 / 盘前空」型模块，容错口径须统一为「空数据→空结构返回 + status=ok，前端显示空态」，避免工作日上午/非交易日刷出整模块 failed。

#### 阶段 3 第2次开发（3.2 + 3.3 + 3.4后半）验收记录（2026-08-26）

**交付内容**：AI API Key 本地配置入口（3.2）+ AI 智能总结（3.3，智谱 GLM-4-Flash）+ 失败兜底（3.4后半）。用户已确认方案：**「整体概览一句话 + 按板块分批」双层呈现**（敲定待确认 #6）。

**后端（4）**：
- 依赖：新增 `httpx`（GLM HTTP 调用）
- `ai_config.py` + `/api/ai/config`（GET/POST/DELETE，**永不回传明文键**，只回 `has_key` + 掩码 `masked_key`），Key 存 `data/ai_config.json`（gitignored）
- `db.py`：新增 `ai_summaries` 表（按交易日唯一缓存）
- `ai_summary.py` + `/api/ai/summary`（GET 读缓存不触发 / POST 生成或强制重生成）：
  - **两轮 GLM 调用**：Pass1 整体总览、Pass2 板块 JSON
  - **JSON 三级容错**：直接解析 → 去代码块 → 花括号匹配，全部失败抛异常（不造假）
  - **索引清洗**：越界/负数/非整数一律剔除并去重
  - **缓存 + 进程内并发锁**：同日防重复生成；`failed` 也落库以便前端可重试
- `tests/test_phase3_3.py`：7 用例全过（JSON/索引/板块清洗、缓存、need_key、failed 兜底、成功结构化）

**前端（5）**：
- `types/ai.ts` 扩展、`api/ai.ts` 扩展（`getAiSummary`/`generateAiSummary`）
- 新增 `components/dashboard/AiSummary.tsx`：**两层总结区**（顶部整体概览 + 下方板块卡片）+ 6 状态分支（未生成/生成中/need_key/no_news/failed/ok）+ 板块**点击联动**高亮表格行
- `pages/NewsPage.tsx`：插入 AiSummary + `rowClassName` 高亮；`index.css` 加 `.ai-highlight-row` 样式
- 原生 Vue 无，React + antd 校验 React 19 兼容性

**验收与 Bug 修复（4 项）**：
1. 「清空当前 Key」无反应 → 静态 `Modal.confirm` 在 React 19 下失效，改用 `App.useApp().modal.confirm`
2. AI 总结「重新生成」报「无法连接 8001」→ 根因**前端 axios 默认 10s 超时**掐断 GLM 长耗时请求（10-30s），触发误导性网络错误文案；修复 `generateAiSummary` 单接口 `timeout: 120000` + 更正 `client.ts` 错误文案 8001→8003
3. 板块联动高亮：点击板块 → 资讯表对应行高亮蓝色；再点取消
4. init 后 `ai_summaries` 表通过 `CREATE TABLE IF NOT EXISTS` 于启动时自建，真实生成可落库

**演示验证（3.4 失败兜底）**：临时置无效 Key + `force:true` → 返回 `status=failed` + `error="API Key 无效或已过期"`，overview/sectors 恒为空**（绝不造假数据）**；`force=false` 有 ok 缓存时直接命中不重调 GLM。恢复正式 Key 后 `force:true` 重生成 `status=ok`、7 个板块，缓存命中正常。

**笔记**：
- 操纵用户凭据/Key 演示前，**必须先落盘持久化备份**再修改，避免临时变量跨终端丢失导致无法恢复（本次教训）。
- AI 长耗时接口（GLM 调用）必须在 axios 上覆盖默认 timeout，否则前端 10s 就掐断误报「无法连接后端」。
- 三模块与 AI 均为「失败即空 + 可重试」口径（军规 6 不静默），失败状态落库供前端展示红色重试。

### 阶段 4：bat + 浏览器交付（最终交付，已完成 ✅）

> 用户于 2026-08-26 确认放弃 Tauri 打包，改选 **bat + 浏览器** 交付方案（难度低、影响面小，详见「7. 关键决策记录」）。

#### 任务清单

- [x] **4.1 后端同源托管前端**：`main.py` 挂载 `/assets` + SPA 回退 `/{full_path:path}`（dist 不存在时安全跳过），生产直达 127.0.0.1:8003
- [x] **4.2 启动脚本**：`start.bat`——扁平 `goto` 结构（无括号块）避免 cmd 解析闪退；端口占用检测/延时 3s 自动开浏览器/关窗即停
- [x] **4.3 一键构建 + 实测**：`build` 脚本改为纯 `vite build`（跳过 tsc 类型检查）产出 dist，`/api/health`、4 个 SPA 路由、全 API 验证通过
- [x] **4.4 文案端口归一**：`refresh.ts`/`main.py` 头注释统一为 8003；CORS 白名单保留 dev 端口并注释说明生产同源不经 CORS

#### 启动方式

双击 `start.bat` → 黑色命令窗停留 → 约 3 秒自动打开 `http://127.0.0.1:8003/`；关窗即停后端。

#### 已知取舍（可接受）

- 无原生桌面托盘/任务栏图标，依赖系统浏览器与标签页
- 关浏览器不会自动停后端，需关闭 start.bat 命令窗口
- 运行依赖项目内 `.venv` 与已构建的 `frontend/dist`

---

## 6. 开发军规（核心章节，后续自动生效）

> 以下 7 条军规贯穿整个开发周期，自动生效，无需再次确认。

### 军规 1：分步验收

每完成一个阶段**停下来找我验收**，并同步更新 `PROJECT_MEMORY.md` 对应章节状态为"已完成"。**严禁一口气写完**。

### 军规 2：方案抉择

遇到技术难题，**给出至少 2 个方案**，用大白话解释优缺点，等我拍板再动手。

### 军规 3：测试标准

**为核心流程写最简单的测试**，能跑通就行，**不追求高覆盖率**。

### 军规 4：变更准则

新想法与现有功能冲突时，**先提示波及范围**，问我"改旧的"还是"新建模块"，**严禁直接覆盖**。
> 触发回退机制：当用户说"不对"时，立即停止并回退到上一个 Git 提交点，不要直接覆盖。

### 军规 5：依赖管理

**新增第三方库前告诉我用途**，经我同意再安装。

### 军规 6：错误处理

所有用户操作必须有**明确的成功/失败反馈**，**禁止静默失败**。

### 军规 7：禁止过度设计

**严格按确认的需求实现**，不要自行添加未讨论过的功能。

---

## 7. 关键决策记录

| 日期 | 决策项 | 选择 | 原因 |
|---|---|---|---|
| 2026-08-24 | 技术栈 | Python+React 全栈 | 免费且数据处理生态强，满足个人自用 |
| 2026-08-24 | 数据源 | akshare（A股免费） | 已封装容错，规避裸东财接口限流问题 |
| 2026-08-24 | 桌面壳 | Tauri 2.x | 体积小（~15MB壳+~80MB依赖），体验接近原生 |
| 2026-08-26 | 交付方式（阶段4改选） | bat + 浏览器，放弃 Tauri | 前端同源走相对 `/api` 与端口解耦，改造成本极低；Tauri 打包 Python/akshare 依赖进 exe 是最大坑点，整体绕开
| 2026-08-24 | Python 版本 | 3.12.13 | uv 自动选择，akshare 等金融库兼容性最佳 |
| 2026-08-24 | 包管理 | corepack pnpm + uv | 无需全局安装，环境隔离 |
| 2026-08-24 | 数据存储 | SQLite 本机 | 个人自用，无需登录，无需云同步 |
| 2026-08-24 | 异常处理铁律 | 绝不显示假数据 | 规避参考项目"真假混淆"痛点 |
| 2026-08-24 | 历史回看 | 30 天 + 能拉就拉 | 平衡存储与可用性 |
| 2026-08-24 | AI 服务 | 智谱 GLM-4-Flash 免费版 | 满足零成本要求，用户接受首次填 Key |
| 2026-08-24 | 资讯源 | 东财资讯接口（akshare） | 免费可靠，无需爬虫 |
| 2026-08-24 | 风险 Top3 | 情绪过热 > 资金撤退 > 大盘破位 | 用户优先级排序 |
| 2026-08-24 | 数据源迁移 | 东财→新浪/同花顺 | 东财 push2 接口被限流封锁，新浪/同花顺更稳定 |
| 2026-08-24 | 指数数量 | 5→4 | 新浪不含北证50，按军规7不额外引入数据源 |
| 2026-08-24 | SSE 实现方式 | fetch + ReadableStream + Vite proxy | 后端 POST 无法用 EventSource，直连 8000 有 CORS 问题 |
| 2026-08-24 | Windows SSE 行尾 | 每次 chunk 后归一化 \r\n → \n | Windows HTTP \r\n 行尾导致帧分隔符不匹配 |
| 2026-08-24 | 风险阈值方案 | 方案 B 均衡型（跌停数调整 15/30） | A 股常态市场校准，预警频率适中，当前 81% 净流出会显示黄色 |
| 2026-08-24 | 风险计算位置 | 后端实时计算（不存档） | 业务逻辑集中，阈值调整后历史快照也能重新算 |
| 2026-08-24 | 风险 API 路径 | GET /api/risk?trade_date=... | query 参数便于「不传则取最新」语义，与 snapshot 接口风格一致 |
| 2026-08-24 | 风险配色 | antd 默认 success/warning/error | 通用风险信号色，与 A 股「红涨绿跌」交易配色无冲突 |
| 2026-08-25 | 自选股最大数量 | 100 只 | 初始确认 20 → 验收时用户调为 100；分页 pageSize 20→50 |
| 2026-08-25 | 异动阈值默认值 | 涨 5% / 跌 5% / 换手 10% | 用户确认，全部支持人工修改任意值（前端 0.1-99 限制） |
| 2026-08-25 | 阈值默认值落点 | 后端 config.py（而非前端写死） | 新增时传 undefined 让后端应用默认值，便于以后统一调整 |
| 2026-08-25 | 编辑阈值 Form 模式 | 严格受控（单一数据源：Form.Item name） | 吸取经验 1071907，避免多机制驱动导致显示异常和回退 |
| 2026-08-25 | API 错误信息提取 | 6 层兜底 `getErrorMessage(e)` | axios 拦截器 `new Error(detail)` 包装后 `e.response` 永远 undefined；6 层依次：`e.message > e?.response?.data?.detail > e?.data?.detail > e?.detail > e.toString() > fallback`（验收 Bug 1 根因修复） |
| 2026-08-25 | AntD 全局提示必须用实例化 API（禁止静态方法） | `<App>` 根包裹 + `AntdApp.useApp()` 拿 `messageApi` | AntD 5 + React 19 组合下静态 `message.xxx()` 缺 Context，**不注入 DOM 且仅一条 warning 易被淹没**，用户视角就是"点了没反应"（验收 Bug 1 根因修复 3） |
| 2026-08-25 | 用户操作错误提示「双保险兜底」机制 | `messageApi.error(msg, 5)` + `setTimeout 2000ms` 巡检 `.ant-message` → 未出现则 `window.alert(msg)` | 军规 6 严格落地，与 AntD/React 版本、Context 注入时序等彻底解耦，**永久杜绝静默失败**（验收 Bug 1 根因修复 4） |
| 2026-08-25 | 自选股行情数据源 | 东财 stock_zh_a_spot_em（主）+ 新浪 stock_zh_a_spot（回退） | 东财字段全、新浪稳定；双源容错与 2.1 数据源策略一致 |
| 2026-08-25 | 自选股行情数据频率 | 归档进快照 watchlist_quotes 模块，不实时拉取 | 军规 7：手动刷新一次即可，异动筛选接口读快照，不重复调 akshare 省网络 |
| 2026-08-25 | 阈值触发计算 | 后端统一计算（合并 watchlist + watchlist_quotes 快照） | 规则唯一；前后端复用；用户改阈值时不用同步前端逻辑 |
| 2026-08-25 | 表格触发高亮 | 左边框 4px + 淡底色（涨=红 / 跌=绿 / 换手=金） | 与 A 股红涨绿跌一致；表格紧凑不破坏布局；同时触发多类时按「涨 > 跌 > 换手」优先级取色 |
| 2026-08-25 | 数据库路径隔离测试 | `STOCK_DB_PATH` env > config.DB_PATH（默认，正式环境不走 env）| 测试自动化安全隔离，不破坏用户本地真实库；对生产无侵入，完全向后兼容 |
| 2026-08-25 | FastAPI 路由注册顺序 | 静态路径（`/batch-thresholds`）必须注册在动态路径（`/{item_id}`）之前 | FastAPI 按注册顺序匹配路由，动态路径会先匹配到静态字符串导致 422 `int_parsing` 错误（验收 Bug 5/6 根因） |
| 2026-08-25 | axios 错误拦截器增强 | 兼容 FastAPI `detail` 三种格式：字符串 / 数组（422 校验） / 对象 | 原拦截器只处理字符串型 `detail`，422 数组型 detail 被 `${msg}` 隐式转为 `[object Object]`（验收 Bug 6 根因） |
| 2026-08-25 | 模块刷新顺序 | `ALL_MODULES` 中 indices 放最后（watchlist_quotes 之后） | py_mini_racer（akshare 内部 V8 引擎）在 watchlist_quotes 高并发调用后内存池易崩溃，导致后续模块失败；indices 放最后避免被波及 |
| 2026-08-25 | 自选股行情数据源 4 阶段容错 | 东财批量 → 新浪批量 → 新浪单票聚合（8 worker 并发）→ 失败返回 None | 东财和新浪批量接口均不稳定，新浪单票 daily API 最可靠但慢，作为终极兜底 |
| 2026-08-25 | 龙虎榜数据源 | 东财 `stock_lhb_detail_em`（主榜单）+ `stock_lhb_stock_detail_em`（个股买卖席位） | 与现有数据源策略一致；主榜单失败抛异常让外层存档 status=failed；个股席位失败该票 seats=null，不影响整体榜单 |
| 2026-08-25 | 龙虎榜排序 | 后端按净买额降序，前端不可点击排序（无 sorter 属性） | 净买入额 = 主力资金净流入，复盘最有情报价值；前端 sorter 在 null 对比时产生不稳定排序（重复行），直接去掉 |
| 2026-08-25 | 龙虎榜刷新位置 | `ALL_MODULES` 中 dragon_tiger 放在 watchlist_quotes 之后、indices 之前 | 两个模块都用 8 worker 并发，但龙虎榜只在刷新瞬间跑一次（非循环），放在 watchlist_quotes 之后不影响 |
| 2026-08-25 | 端口 8001 僵尸进程 | Windows 内核级 socket 残留（PID 19948），无法在用户态杀掉，后端临时跑在 8002 | 下次开机自动释放；vite.config.ts 代理已同步指向 8002 |
| 2026-08-25 | 阶段2.5 详情入口形态 | Drawer 抽屉（从右侧滑出，680px） | 符合"盘后复盘快速浏览"场景，不离开总览页，可对照总览数据 |
| 2026-08-25 | 阶段2.5 详情内容 | 4 个维度卡片，只带 TOP5，不要历史趋势图 | 用户确认：要明细列表但只 TOP5，不要历史趋势图 |
| 2026-08-25 | 阶段2.5 接口复用 | 完全复用 `/api/risk` + `/api/snapshot` | 无需新接口，前端组装数据；符合军规 7「禁止过度设计」 |
| 2026-08-25 | 阶段2.5 历史回看联动 | 完全联动总览页日期选择器 | Drawer 内不设独立选择器，避免两个选择器冲突 |
| 2026-08-25 | 阶段2.5 进度条颜色 | 根据触发等级着色（绿/黄/红） | 与 RiskLabel 的 Tag 颜色一致，视觉预警清晰 |
| 2026-08-25 | 阶段2.5 查看完整榜单 | 关闭 Drawer + `scrollIntoView` 滚动定位 | 点击后回到总览页对应模块，体验流畅 |
| 2026-08-25 | 端口切换 8002→8003 | 8002 被僵尸进程占用（PID 10720 无法杀掉） | 清理 __pycache__ 后用 8003 重启；前端 Vite 代理已同步更新 |
| 2026-08-26 | 资讯数据源 | 东财 `stock_info_global_em`（主）+ 新浪 `stock_info_global_sina`（回退） | 东财资讯稳定、字段含摘要链接；新浪兜底保证断网返回时不空 |
| 2026-08-26 | 资讯展示 | 20 条表格：序号 + 标题(可跳转) + 摘要 + 发布时间 | 用户确认方案；历史日期选择器复用 HistoryDatePicker |
| 2026-08-26 | 资讯页导航 Tab | 新增「资讯」Tab（FileTextOutlined），`/news` 路由 | 独立页面承载资讯，不挤占总览 |
| 2026-08-26 | 导航自适应布局 | [AppHeader.tsx] `flex:1` + `justifyContent:flex-end` | 修复窗口缩小时 4 Tab 折叠「...」；原 `minWidth:260` 固定宽度 |
| 2026-08-26 | 资讯链接跳转 | `window.open(url)` + 空 URL 不渲染图标 | 空字符串 `""` 被当 truthy 显示 `href=""` 无法跳转；TRAE 内置浏览器有限制，外部浏览器正常 |
| 2026-08-26 | 指数数据源三级容错 | akshare 新浪分页 → 新浪 hq.sinajs.cn 直连(带 Referer) → 东财 push2 | akshare 分页被反爬返回 HTML；hq 直连稳定且盘前回退昨收；东财 push2 被限流作备 |
| 2026-08-26 | 「盘前空」型模块容错口径 | 空数据 → 返回空结构 + status=ok，前端显示空态（不报 failed） | indices/limit_pool/dragon_tiger 均为盘中/盘后有数据、盘前空，统一口径避免工作日上午刷出整模块失败 |
| 2026-08-26 | dragon_tiger 盘前异常兜底 | `_fetch_detail` 捕获异常返回 None（不 raise）→ fetch 返回空榜单 | akshare `stock_lhb_detail_em` 盘前返回异常对象致 `'NoneType' object is not subscriptable`；空榜单前端显示「无龙虎榜数据」 |
| 2026-08-26 | limit_pool 接口异常兜底 | 涨停/跌停接口异常时降级为空池（logger.warning），不 raise | 与 dragon_tiger 口径统一；盘前接口反爬/限流不再让模块 failed |

---

## 8. 待确认事项

> 开发过程中遇到这些点需要再次与用户确认，严禁自行决定。

| # | 事项 | 触发时机 |
|---|---|---|
| 1 | ~~工具正式名称~~ → ✅ 已确认「A股数据看板工具」（2026-08-24 第3次开发） | 阶段 1 启动前 |
| 2 | ~~风险等级标签的具体阈值规则~~ → ✅ 已确认「方案 B 均衡型 + 跌停数 15/30 调整」（2026-08-24 第5次开发） | 阶段 1.10 |
| 3 | ~~自选股最大数量限制~~ → ✅ 初始确认 20 只，验收时用户调整为 100 只（2026-08-25） | 阶段 2.1 |
| 4 | ~~异动阈值的默认值（涨幅 X%、跌幅 Y%、换手率 Z%）~~ → ✅ 已确认 涨 5% / 跌 5% / 换手 10%，全部支持人工填写其他值（2026-08-25 阶段 2.1 启动前） | 阶段 2.2 |
| 5 | ~~资讯每天抓取条数与展示方式~~ → ✅ 已确认「20 条 + 摘要 + 链接 + 时间，东财主源新浪回退」（2026-08-26 阶段3.1 启动前） | 阶段 3.1 |
| 6 | ~~AI 总结的具体呈现（卡片？列表？分类标签？）~~ → ✅ 已确认「整体概览一句话 + 按板块分批（板块卡片可点击联动高亮对应资讯）」（2026-08-26 阶段3.2 启动前，第2次开发验收时定版） | 阶段 3.3 |
| 7 | ~~桌面图标样式~~ → ⛔ 已废弃（方案改选 bat+浏览器，无桌面图标需求） | 阶段 4（原） |
| 8 | ~~各模块数据字段是否完全沿用参考项目~~ → ✅ 已确认「字段重新设计，不沿用参考项目」（2026-08-24 第3次开发，对照 akshare 输出重新定义于 `frontend/src/types/modules.ts`） | 阶段 1.2 |

---

*文档版本：v1.7 · 状态：V1.0 正式发布收尾完成 —— 阶段 0-4 全部验收通过；bat+浏览器交付；开源上传 GitHub（MIT）；README 使用指南就绪。v1.0-release 已打 Tag。*

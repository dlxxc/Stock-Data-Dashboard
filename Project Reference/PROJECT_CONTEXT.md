# 复盘大师 - A 股盘后复盘工具 · 项目上下文文档

> 本文档由 7 个独立文档合并而成，涵盖项目全部技术细节。新对话窗口发送此文件即可掌握完整项目上下文。

---

## 目录

1. [项目总览](#1-项目总览)
2. [架构设计](#2-架构设计)
3. [数据结构定义](#3-数据结构定义)
4. [函数 API 参考](#4-函数-api-参考)
5. [CSS 设计系统](#5-css-设计系统)
6. [v2 开发路线图](#6-v2-开发路线图)
7. [真实数据接入（已实现，v3.0 服务端代理架构）](#7-真实数据接入已实现-v30-服务端代理架构)

---

## 1. 项目总览

### 项目简介

「复盘大师」是一个 A 股每日盘后复盘仪表盘，涵盖市场环境、资金流向、涨跌停统计、情绪分析、主线板块、龙虎榜、北向资金、论坛热点等核心模块。适合短线/中线交易者收盘后快速回顾当日盘面、定位主线方向、监控情绪周期。

### 本地运行

- **本机运行**：双击 `start.bat`（Windows）或 `python server.py`，访问 http://127.0.0.1:8000
- v3.0 起数据拉取依赖本机 `server.py`（`/api/market` 接口），纯静态托管（CloudStudio / `python -m http.server`）**不再适用**，页面会回落演示数据并告警

### 技术栈

| 技术 | 用途 | 版本 |
|---|---|---|
| HTML5 | 页面结构 | - |
| CSS3 | 样式（自定义变量 + Grid 布局） | - |
| JavaScript (ES5+) | 交互逻辑 | 无框架依赖 |
| ECharts | 图表（K线/条形/仪表盘/折线） | 5.5.0 (CDN) |
| CloudStudio | 免费静态托管 | - |

### 功能模块

#### v1 核心功能

| 模块 | 导航入口 | 说明 |
|---|---|---|
| 一句话总结 | 总览 | 当日盘面核心结论 |
| 盘型/环境 | 市场环境 | 5 大指数卡片 + 情绪广度 + 方向广度 |
| 涨跌停统计 | 总览 | 涨停/跌停/最高连板/炸板率四宫格 |
| 资金流向 | 资金流向 | 行业净流入 TOP5 条形图 + 净流出 TOP5 表格 |
| 个股资金流 | 资金流向 | 净流入/净流出 TOP10 双表格 |
| 板块分析 | 板块分析 | 主线/次主线/观察/活口/资金撤退 5 类卡片 |
| 情绪分析 | 情绪分析 | 4 个仪表盘（发酵/扩散/偏离潮/综合） |
| 风险提示 | 风险提示 | 风险边界文字描述 |
| 连板梯队 | 连板梯队 | 5 板→2 板递降展示 |
| 股票筛选 | 股票筛选 | 方向+板块+关键词三重筛选，全局高亮 |
| 方向分析表 | 总览 | 完整方向/板块/领涨股/强度/状态表 |

#### v2 阶段一新增功能

| 模块 | 导航入口 | 说明 |
|---|---|---|
| 指数走势 | 指数走势 | 当日分时图（含均价线+昨收线）+ 60 日 K 线蜡烛图 |
| 涨停复盘 | 涨停复盘 | 涨停原因+题材归类表 + 昨日涨停今日晋级率监控 |
| 龙虎榜 | 龙虎榜 | 机构/游资席位买卖明细、净买入榜 |
| 北向/两融 | 北向/两融 | 北向资金近 8 日柱状图 + 融资余额趋势线 |
| 自选股 | 自选股 | 输入代码添加关注，localStorage 存储 |
| 历史复盘 | 历史复盘 | 每日快照存档，可回看往日页面，最多 90 天 |
| 热点聚焦 | 热点聚焦 | 国内外论坛热点 + 每日/每周总结 |

#### v2 阶段二（✅ 2026-08-20 完成）

- 接入东方财富公开接口，实现真实盘后数据
- 手动点「刷新」拉取当日数据（JSONP 绕跨域，无需代理）
- 详细实现见下文第 7 节 + `js/api.js`

### 文件结构

```
market-review/
├── index.html              # 主页面（布局骨架 + CDN 引入）
├── server.py               # ★ v3.0 本地服务：静态托管 + /api/market + 5分钟缓存（~180 行）
├── data_provider.py        # ★ v3.0 数据层：10 个数据模块服务端聚合 + 涨停晋级率 + K线三级容错（~770 行）
├── css/
│   └── style.css           # 全部样式（CSS 变量 + 响应式，~904 行）
├── js/
│   ├── data.js            # 演示数据兜底 + 全局数据结构（~540 行）
│   ├── api.js             # 数据接入层：请求本机 /api/market 并合并（~290 行）
│   └── app.js             # 全部交互逻辑（渲染+图表+筛选+存储+刷新，~1889 行）
├── test/                  # 测试脚本（e2e-v3.js 端到端 + cdp-verify.js 浏览器验证）
├── cache/                 # 运行时 K 线磁盘缓存（git 忽略）
├── start.bat              # 启动本地服务器（GBK+CRLF，勿改编码）
├── stop.bat               # 停止本地服务器（按 8000 端口杀进程）
├── docs/                   # 技术文档目录（本文件为其合并版）
│   └── PORTING_GUIDE.md   # ★ 移植部署与开发指南（换电脑/优化必读）
└── README.md              # 项目说明
```

### 配色说明

采用 A 股惯例：**红涨绿跌**（与美国市场相反）。

| 色彩 | 变量 | 用途 |
|---|---|---|
| 红色 `#f85149` | `--red` | 上涨 / 涨停 / 主线 |
| 绿色 `#3fb950` | `--green` | 下跌 / 跌停 / 资金撤退 |
| 橙色 `#f0883e` | `--orange` | 次主线 |
| 黄色 `#d29922` | `--amber` | 活口 / 风险提示 |
| 蓝色 `#58a6ff` | `--blue` | 观察 / 筛选高亮 |
| 紫色 `#bc8cff` | `--purple` | 历史回看 / 每周总结 |

### 当前数据状态

**双模式**：
- 打开页面默认展示**演示数据**（基于 2026-05-07 盘面复刻）
- 点击顶部「🔄 刷新数据」→ 前端单次 `fetch('/api/market')` → **Python 服务端**拉取东财当日数据（10 个数据模块），来源徽章显示「东财实时 HH:MM:SS · N项」，刷新成功自动存档
- **失败模块通过 `meta.warnings` 明确告警**（toast 展示），不再静默回落演示数据；连不上本地服务时提示「请双击 start.bat」
- 服务端 5 分钟缓存（成功≥5 模块才长缓存，否则 30 秒），`?refresh=1` 强制绕过
- 部分模块（涨停原因归类、论坛热点、主线板块归类）无公开 API，保留演示/人工标注，页面有明确提示

### 版本历史

- **v1.0**（2026-08-15）：初始版本，11 个核心模块
- **v1.1**（2026-08-15）：新增热点聚焦 + 修复筛选器交互
- **v2.0-阶段一**（2026-08-15）：新增 6 个模块（指数走势、涨停复盘、龙虎榜、北向两融、自选股、历史复盘）
- **v2.1**（2026-08-20）：接入东方财富真实数据（9 数据源）+ 刷新按钮 + 自动存档 + `start.bat`/`stop.bat`
- **v2.2**（2026-08-20）：主机切 `push2delay`、`trends2` 限流重试、失败模块自动重试一轮、`?v=N` 缓存修复；9/9 验证通过；配置开机自启动
- **v3.0**（2026-08-21）：**架构升级为 Python 服务端代理**（server.py + data_provider.py），根治浏览器风控限流；warnings 明确告警失败模块；5 分钟服务端缓存；K线三级容错（东财→腾讯→磁盘缓存）；git 基线管理（v2.2-baseline 标签可回滚）
- **v3.1**（2026-08-22）：涨停晋级率实时化（查昨日+今日涨停池交叉比对，11/79=13.9% 真实值）+ 涨停原因改用真实行业板块（`hybk`）；修复历史复盘存档日期同步（`meta.fetchedAt` 解析真实交易日写入 `MARKET_DATA.date`，告别演示日期 2026-05-07）；数据源模块 9→10，E2E 16/16 PASS

---

## 2. 架构设计

### 整体架构

本项目采用**纯前端静态网页**架构，无后端服务器、无数据库、无 API 层。

```
┌──────────────────────────────────────────────────┐
│                   浏览器                           │
│                                                    │
│  ┌─────────────┐   ┌──────────────┐   ┌────────┐ │
│  │ index.html  │──│  style.css   │   │ ECharts │ │
│  │ (布局骨架)   │   │  (样式系统)   │   │ (CDN)  │ │
│  └──────┬──────┘   └──────────────┘   └────┬───┘ │
│         │                                   │      │
│  ┌──────▼──────────────────────────────────▼────┐ │
│  │                 app.js                         │ │
│  │  ┌─────────┐  ┌──────────┐  ┌─────────────┐ │ │
│  │  │ 渲染层   │  │ 交互层    │  │  存储层      │ │ │
│  │  │ render* │  │ filter*  │  │ localStorage │ │ │
│  │  │ chart*  │  │ nav*     │  │ watchlist    │ │ │
│  │  │         │  │ watch*   │  │ archives     │ │ │
│  │  └─────────┘  └──────────┘  └─────────────┘ │ │
│  └───────────────────────┬─────────────────────┘ │
│                           │                       │
│                   ┌───────▼───────┐               │
│                   │   data.js     │               │
│                   │ (全部数据定义)  │               │
│                   └───────────────┘               │
└──────────────────────────────────────────────────────┘
```

### 三层分离设计

#### 数据层 (`data.js`)

所有数据以全局常量对象定义，不依赖任何异步请求：

| 全局常量 | 类型 | 说明 |
|---|---|---|
| `MARKET_DATA` | `Object` | 核心盘面数据（指数/涨跌停/板块/资金流/情绪等） |
| `SECTOR_LIST` | `Array<string>` | 板块名称列表（筛选下拉用） |
| `DIRECTION_LIST` | `Array<string>` | 方向分类列表 |
| `FORUM_DATA` | `Object` | 国内外论坛热点数据 |
| `INDEX_TREND` | `Object` | 指数分时+K 线数据 |
| `LIMITUP_REASONS` | `Array<Object>` | 涨停原因与题材归类 |
| `PROMOTION_DATA` | `Object` | 昨日涨停今日晋级率 |
| `DRAGON_TIGER` | `Object` | 龙虎榜数据 |
| `NORTH_MARGIN` | `Object` | 北向资金+两融数据 |

#### 渲染层 (`app.js` - render* 函数)

所有 UI 通过 JS 动态生成 DOM，渲染流程：

```
DOMContentLoaded
  ├── seedDemoArchive()       // 注入演示存档
  ├── initFilters()           // 初始化筛选下拉选项
  ├── renderAll()             // 渲染全部模块
  │   ├── renderFilterBanner()
  │   ├── renderStockDetailCard()
  │   ├── renderSummary()
  │   ├── renderIndexTrend()
  │   ├── renderEnvironment()
  │   ├── renderLimitStats()
  │   ├── renderLimitUpReview()
  │   ├── renderLadder()
  │   ├── renderIndustryFlow()
  │   ├── renderSectors()
  │   ├── renderRisk()
  │   ├── renderStockFlow()
  │   ├── renderDragonTiger()
  │   ├── renderNorthMargin()
  │   ├── renderSentiment()
  │   ├── renderDirections()
  │   ├── renderStockPool()
  │   ├── renderWatchlist()
  │   ├── renderHistory()
  │   ├── renderForumSection()
  │   └── setTimeout(initCharts, 100)  // 延迟初始化 ECharts
  └── initNavigation()        // 绑定侧边栏点击
```

#### 存储层 (`app.js` - localStorage)

| Key | 用途 | 容量 |
|---|---|---|
| `fupan_watchlist_v1` | 自选股列表 | 无硬限 |
| `fupan_archives_v1` | 每日复盘存档 | 最近 90 条 |

### 页面布局

```
┌──────────────────────────────────────────────────┐
│  Header (60px) - Logo + 日期 + 筛选器             │
├────────────┬─────────────────────────────────────┤
│            │                                      │
│  Sidebar   │       Main Content                   │
│  (200px)   │       (overflow-y: auto)              │
│            │                                      │
│  导航       │   模块1 → 模块2 → ... → 模块N        │
│  分两组     │   （全部纵向排列，侧边栏点击滚动定位）  │
│            │                                      │
└────────────┴─────────────────────────────────────┘
```

Grid 布局：`grid-template-columns: 200px 1fr; grid-template-rows: 60px 1fr;`

### 数据流

#### 筛选交互流

```
用户操作（下拉/输入）
  → currentFilter 更新
  → handleFilterChange()
    ├── updateFilterBanner()     // 顶部蓝色横幅
    ├── updateStockDetailCard() // 快捷详情卡
    ├── applyGlobalHighlights() // 板块卡片/表格行高亮+变暗
    ├── renderStockPool()       // 筛选结果表格
    └── 自动滚动到结果区
```

#### 图表初始化流

```
renderAll() 完成 DOM 渲染
  → setTimeout(100ms)
    ├── initIndustryChart()       // 行业资金流条形图
    ├── initSentimentGauges()     // 4 个情绪仪表盘
    ├── initIndexTrendChart()     // 指数分时/K线
    └── initNorthMarginCharts()  // 北向+融资趋势
```

图表实例缓存到 `trendCharts` 对象，切换时先 `dispose()` 旧实例再创建新的。

#### 历史回看流

```
点击「查看」
  → viewArchive(date)
    → 从 localStorage 读取存档
    → Object.keys(MARKET_DATA).forEach(delete)  // 清空当前
    → Object.assign(MARKET_DATA, arc.data)       // 替换为存档
    → renderAll()                                  // 重新渲染
    → 顶部插入紫色「历史回看模式」横幅

点击「返回今日」
  → exitArchive()
    → location.reload()  // 最稳妥的恢复方式
```

### ECharts 集成

- **CDN 引入**：`https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js`
- **图表类型**：bar（条形/柱状）、gauge（仪表盘）、line（折线/面积）、candlestick（K 线蜡烛图）
- **主题**：深色，所有颜色硬编码（未使用 ECharts 主题文件）
- **响应式**：`window.addEventListener("resize", () => chart.resize())`
- **实例管理**：`trendCharts` 对象缓存 indexTrend / nb / margin 实例

### 性能考量

| 关注点 | 当前方案 | 说明 |
|---|---|---|
| DOM 渲染 | 一次性全量渲染 | 模块数固定（约 20 个），渲染后无虚拟列表需求 |
| 图表延迟 | setTimeout 100ms | 确保 DOM 容器存在后再 init |
| localStorage | JSON 序列化 | 存档每条约 10-20KB，90 条约 1-2MB，远低于 5MB 上限 |
| 防抖 | 200ms | 筛选输入框搜索防抖 |
| 响应式图表 | resize 监听 | 每个图表实例注册 resize 回调 |

### 阶段二架构变更预览

接入真实数据后，数据层将从静态常量变为异步加载：

```
data.js (静态常量，作为 fallback)
  ↓
api.js (新增：封装免费公开接口请求)
  ├── fetchIndexData()        → 东方财富指数接口
  ├── fetchLimitStats()       → 东方财富涨跌停
  ├── fetchDragonTiger()      → 东方财富龙虎榜
  ├── fetchNorthbound()       → 东方财富北向资金
  ├── fetchMargin()           → 东方财富两融
  └── fetchForumHot()         → RSS / 手动维护
  ↓
app.js (渲染逻辑不变，数据来源切换)
```

可能需要 **云函数中转** 解决跨域问题（CORS），届时架构变更为：

```
浏览器 → CloudStudio 云函数 (CORS 代理) → 东方财富 API
```

---

## 3. 数据结构定义

> 记录 `data.js` 中所有数据结构的字段定义，方便阶段二接入真实数据时对照映射。

### 3.1 MARKET_DATA（核心盘面数据）

```javascript
const MARKET_DATA = {
  date: "2026-05-07",        // 日期 YYYY-MM-DD
  weekday: "周四",           // 星期

  // === 一句话总结 ===
  summary: "string",         // 当日核心结论

  // === 指数数据 ===
  indices: [
    {
      name: "上证指数",       // 指数名称
      code: "SH000001",      // 指数代码（SH/SZ/BJ 前缀）
      value: 3315.87,        // 收盘点位
      change: 17.53,         // 涨跌点数
      pct: 0.53,             // 涨跌幅 %
      volume: 3847,          // 成交量（亿）
      amount: 38470000       // 成交额（万元）
    }
    // ... 共 5 个：上证/深证/创业板/科创50/北证50
  ],

  // === 市场情绪广度 ===
  marketBreadth: {
    advancing: 2847,         // 上涨家数
    declining: 2153,         // 下跌家数
    flat: 156,               // 平盘家数
    advancingPct: 55.2,      // 上涨占比 %
    decliningPct: 41.8,      // 下跌占比 %
    breadthScore: 68         // 广度评分 0-100
  },

  // === 市场方向广度 ===
  marketDirection: {
    upSectors: 28,           // 上涨板块数
    downSectors: 12,         // 下跌板块数
    flatSectors: 3,          // 平盘板块数
    directionScore: 72       // 方向评分 0-100
  },

  // === 涨跌停统计 ===
  limitStats: {
    limitUp: {
      total: 47,             // 涨停总数
      first_board: 32,       // 首板数
      continuous: 15,        // 连板数
      max_height: 5,         // 最高连板高度
      broken: 6              // 炸板数
    },
    limitDown: {
      total: 8,
      first_board: 5,
      continuous: 3,
      max_height: 2,
      broken: 1
    },
    broken_rate: 12.8         // 炸板率 %
  },

  // === 连板梯队 ===
  continuousBoard: [
    {
      height: 5,             // 连板高度
      count: 1,              // 该高度家数
      stocks: ["华钰矿业"]   // 股票名称数组
    }
    // 从高到低排列：5板→4板→3板→2板
  ],

  // === 行业资金流 - 净流入 TOP5 ===
  industryInflow: [
    {
      name: "通信设备",       // 行业名称
      netInflow: 28.7,       // 净流入金额（亿）
      pct: 3.2,              // 行业涨跌幅 %
      leader: "中兴通讯",     // 领涨股
      leaderPct: 5.67         // 领涨股涨幅 %
    }
  ],

  // === 行业资金流 - 净流出 TOP5 ===
  industryOutflow: [
    {
      name: "房地产开发",
      netInflow: -15.2,      // 负值表示净流出
      pct: -1.8,
      leader: "万科A",
      leaderPct: -2.34
    }
  ],

  // === 主线 & 观察板块 ===
  sectors: [
    {
      type: "主线",           // 分类：主线/次主线/观察/活口/资金撤退
      typeColor: "red",      // 颜色标识：red/orange/blue/amber/green
      name: "AI算力",        // 板块名称
      note: "string",        // 板块说明
      strength: 85,          // 强度评分 0-100
      stocks: [
        {
          name: "中际旭创",
          code: "300308",    // 股票代码
          pct: 8.92,         // 涨跌幅 %
          price: 168.50      // 最新价
        }
      ]
    }
  ],

  // === 个股资金流 - 净流入 TOP10 ===
  stockInflow: [
    {
      code: "600519",
      name: "贵州茅台",
      netInflow: 8.72,      // 净流入（亿）
      pct: 2.34,             // 涨跌幅 %
      price: 1687.50,
      industry: "白酒"       // 所属行业
    }
  ],

  // === 个股资金流 - 净流出 TOP10 ===
  stockOutflow: [
    {
      code: "000002",
      name: "万科A",
      netOutflow: -4.56,    // 负值
      pct: -2.34,
      price: 9.87,
      industry: "房地产"
    }
  ],

  // === 情绪指标 ===
  sentiment: {
    fermentation: 72,       // 发酵度 0-100
    diffusion: 58,          // 扩散度 0-100
    polarization: 45,       // 偏离/分化度 0-100
    overall: 65             // 综合情绪温度 0-100
  },

  // === 情绪描述文字 ===
  sentimentDesc: "string",

  // === 风险边界 ===
  riskBoundary: "string",

  // === 方向分析表 ===
  directions: [
    {
      direction: "主线",     // 方向分类
      directionColor: "red",
      sector: "AI算力",      // 板块
      leader: "中际旭创(300308)", // 领涨股
      leaderPct: 8.92,
      strength: "强",        // 强弱描述
      status: "加速",        // 状态：加速/持续/活跃/观察/震荡/撤退/分歧/回落
      note: "string"         // 备注
    }
  ],

  // === 全部股票列表（用于筛选） ===
  allStocks: [
    {
      code: "300308",
      name: "中际旭创",
      industry: "通信设备",  // 申万行业
      pct: 8.92,             // 涨跌幅
      price: 168.50,
      sector: "AI算力",      // 概念板块
      direction: "主线"      // 方向分类
    }
  ]
};
```

### 3.2 SECTOR_LIST / DIRECTION_LIST

```javascript
const SECTOR_LIST = [
  "AI算力", "半导体设备", "低空经济", "通信设备", "人形机器人",
  "固态电池", "有色金属", "白酒", "房地产", "煤炭", "电池",
  "消费电子", "医药", "银行", "证券", "保险", "石油石化", "钢铁"
];

const DIRECTION_LIST = ["全部", "主线", "次主线", "活口", "资金撤退", "观察"];
```

### 3.3 FORUM_DATA（论坛热点）

```javascript
const FORUM_DATA = {
  updateTime: "2026-05-07 15:30",
  china: {                    // 国内论坛
    sources: [
      { name: "雪球", icon: "❄️", url: "https://xueqiu.com" }
      // ... 共 7 个
    ],
    dailySummary: "string",   // 每日热点总结
    weeklySummary: "string",  // 每周热点总结
    hotTopics: [
      {
        source: "雪球",
        title: "string",
        heat: 9856,           // 热度值
        comments: 2341,       // 评论数
        content: "string",    // 摘要
        tags: ["AI算力", "光模块"]
      }
    ]
  },
  international: {            // 海外论坛
    sources: [
      { name: "Reddit r/wallstreetbets", icon: "🚀", url: "..." }
      // ... 共 7 个
    ],
    dailySummary: "string",
    weeklySummary: "string",
    hotTopics: [/* 同上 */]
  }
};
```

### 3.4 INDEX_TREND（指数分时与 K 线）

```javascript
const INDEX_TREND = {
  indices: [
    {
      name: "上证指数",
      code: "SH000001",
      close: 3315.87,       // 今日收盘
      open: 3298.5,         // 今日开盘
      prevClose: 3298.34,   // 昨日收盘
      intraday: [           // 分时数据（49 个点，09:30~15:00 每 5 分钟）
        { time: "09:30", price: 3298.50, avg: 3298.50 }
      ],
      kline: [              // 60 日 K 线
        { date: "02-14", open: Number, close: Number, low: Number, high: Number, volume: Number }
      ]
    }
    // 共 3 个：上证/深证/创业板
  ]
};
```

数据生成函数（演示用）：`seededRand(seed)` / `genIntraday(startPrice, endPrice, prevClose)` / `genKline(endClose, seed)`

### 3.5 LIMITUP_REASONS（涨停原因）

```javascript
const LIMITUP_REASONS = [
  {
    name: "华钰矿业",
    code: "601020",
    boards: 5,              // 连板数
    reason: "锑价创历史新高+缅甸矿端收紧",  // 涨停原因
    theme: "有色金属",       // 题材归类
    type: "涨价"            // 类型：涨价/政策/板块联动/消息刺激/业绩/重组预期
  }
];
```

### 3.6 PROMOTION_DATA（晋级率，v3.1 起实时化）

> v3.1 起由 `data_provider.fetch_promotion()` 实时计算并覆盖（**不再硬编码 2026-05-06**）。`data.js` 中的 `PROMOTION_DATA` 仅作兜底默认值；`LIMITUP_REASONS` 已不再使用（原因改用接口返回的 `hybk` 行业板块字段）。

```javascript
const PROMOTION_DATA = {
  date: "2026-08-20",      // 昨日交易日（真实）
  total: 79,               // 昨日涨停总数
  stillLimitUp: 11,        // 今日继续涨停（晋级）
  up: 16,                  // 上涨未涨停
  flat: 2,                 // 平盘
  down: 50,               // 下跌
  promotionRate: 13.9,     // 晋级率 % = stillLimitUp / total
  avgPct: 1.85,            // 昨日涨停股今日平均涨幅 %
  comment: "string",       // 情绪研判文字（含明细）
  stocks: [                // 最多 20 只，按今日涨幅降序
    {
      name: "汉森制药",
      code: "002412",
      yBoards: 2,          // 昨日连板数
      todayPct: 10.02,     // 今日涨幅 %
      status: "晋级3板"     // 状态：晋级N板 / 上涨 / 平盘 / 下跌
    }
  ],
  limitupReasons: [        // 今日涨停原因（最多 15 只，按连板数降序）
    {
      name: "汉森制药",
      code: "002412",
      boards: 3,           // 连板数
      reason: "待补充（无免费API）",  // 真实原因需 NLP / 人工
      theme: "中药Ⅱ",       // 真实行业板块（hybk），替代假题材
      type: "连板"           // 连板 / 首板
    }
  ]
};
```

> **计算逻辑**：查昨日 + 今日 `getTopicZTPool`（`date=YYYYMMDD`）交叉比对得晋级数；非晋级股用 `push2delay` 的 `ulist` 批量查今日涨跌幅，分类涨/平/跌；非交易日按「数量 + 首尾代码」去重（API 对周末返回最近交易日的相同数据）。涨停原因文案无免费 API，显示行业板块 + "待补充"。

### 3.7 DRAGON_TIGER（龙虎榜）

```javascript
const DRAGON_TIGER = {
  date: "2026-05-07",
  total: 62,               // 上榜家数
  netBuyTotal: 18.7,       // 净买入合计（亿）
  items: [
    {
      name: "中际旭创",
      code: "300308",
      pct: 8.92,           // 涨跌幅
      netBuy: 4.32,        // 净买入（亿）
      buys: [              // 买入席位（字符串数组）
        "机构专用 (2.1亿)",
        "沪股通专用 (1.3亿)"
      ],
      sells: [             // 卖出席位（字符串数组）
        "机构专用 (0.6亿)"
      ],
      reason: "日涨幅偏离值达7%"  // 上榜原因
    }
  ]
};
```

### 3.8 NORTH_MARGIN（北向资金+两融）

```javascript
const NORTH_MARGIN = {
  northbound: {
    todayNet: 48.6,        // 今日净流入（亿）
    shNet: 27.3,          // 沪股通净流入
    szNet: 21.3,          // 深股通净流入
    ytdNet: 1892.4,       // 年内累计
    trendDays: ["04-24", ...],  // 近 8 日日期
    trendValues: [-12.4, 22.8, ...]  // 近 8 日净流入
  },
  margin: {
    balance: 18234,       // 融资余额（亿）
    balanceChange: 86.5,  // 今日变化
    buyAmount: 1124,      // 融资买入额（亿）
    trendDays: [...],     // 近 8 日日期
    trendValues: [...]     // 近 8 日余额
  }
};
```

### 3.9 localStorage 存储结构

**自选股 `fupan_watchlist_v1`**:
```javascript
[{ code: "300308", name: "中际旭创" }]
```

**历史复盘存档 `fupan_archives_v1`**:
```javascript
[{
  date: "2026-05-06",
  savedAt: "2026-05-06 17:30",
  data: { ...MARKET_DATA },  // 当日完整盘面数据快照
  tag: "演示存档"           // 演示存档/手动保存/自动保存
}]
// 最多保留最近 90 条
```

---

## 4. 函数 API 参考

> `app.js` 中所有函数的签名、参数、返回值、调用关系。

### 全局变量

| 变量 | 类型 | 说明 |
|---|---|---|
| `currentFilter` | `{direction, sector, keyword}` | 当前筛选条件 |
| `currentForumTab` | `"china"` / `"international"` | 当前论坛 Tab |
| `forumTopicFilter` | `string` | 话题搜索关键词 |
| `currentIndexIdx` | `number` | 当前选中的指数索引（0/1/2） |
| `trendMode` | `"intraday"` / `"kline"` | 指数走势模式 |
| `trendCharts` | `Object` | ECharts 实例缓存 |
| `WATCHLIST_KEY` | `"fupan_watchlist_v1"` | localStorage 键名 |
| `ARCHIVE_KEY` | `"fupan_archives_v1"` | localStorage 键名 |
| `window.__todayDate` | `string` | 记录今日日期（历史回看时用于恢复） |

### 初始化

| 函数 | 说明 |
|---|---|
| `DOMContentLoaded 回调` | 执行顺序：seedDemoArchive() → initFilters() → renderAll() → initNavigation() |
| `initFilters()` | 填充下拉选项，绑定输入事件（200ms 防抖） |
| `initNavigation()` | 绑定侧边栏点击，高亮+平滑滚动 |

### 渲染函数（均为 `renderXxx(container: HTMLElement)` 模式）

| 函数 | 渲染内容 |
|---|---|
| `renderAll()` | 清空 #mainContent 后按顺序调用所有 render 函数 |
| `renderFilterBanner(container)` | 筛选状态横幅 |
| `updateFilterBanner()` | 更新横幅内容（蓝色横幅+筛选条件标签+清除按钮） |
| `renderStockDetailCard(container)` | 股票快捷详情卡 |
| `updateStockDetailCard()` | 精确匹配1只→显示详情；按板块→显示龙头；模糊匹配→显示列表 |
| `applyGlobalHighlights()` | 全局高亮：板块卡片/表格行/连板行 `.matched` / `.dimmed` |
| `renderSummary(container)` | 一句话总结横幅 |
| `renderEnvironment(container)` | 5 指数卡片 + 情绪广度进度条 + 方向广度进度条 |
| `renderLimitStats(container)` | 涨跌停统计四宫格 |
| `renderIndustryFlow(container)` | 行业净流入 TOP5 条形图容器 + 净流出 TOP5 表格 |
| `renderSectors(container)` | 主线&观察板块卡片网格 |
| `renderRisk(container)` | 风险边界文字 |
| `renderStockFlow(container)` | 个股资金流 TOP10 双表格 |
| `renderSentiment(container)` | 4 个仪表盘 + 情绪描述 |
| `renderDirections(container)` | 方向分析表 |
| `renderLadder(container)` | 连板梯队 |
| `renderStockPool(container?)` | 股票筛选表格（有参数=创建，无参数=更新） |
| `renderForumSection(container)` | 热点聚焦（每日/每周总结+Tab切换+话题网格） |
| `renderForumTabs()` / `renderForumContent()` | 论坛 Tab 高亮+内容更新 |
| `getSourceIcon(source)` | 来源名称→emoji |
| `formatHeat(num)` | 热度值格式化（>=10000→X.Xw, >=1000→X.Xk） |
| `renderIndexTrend(container)` | 指数走势（指数Tab+模式Tab+摘要+图表容器） |
| `renderIndexTrendUpdate()` | 更新指数走势 Tab 高亮+摘要+图表 |
| `updateTrendSummary()` | 更新指数摘要（名称/代码/收盘/涨跌幅/昨收/今开） |
| `renderLimitUpReview(container)` | 涨停复盘（晋级率四宫格+进度条+研判+双表格） |
| `renderDragonTiger(container)` | 龙虎榜明细表 |
| `renderNorthMargin(container)` | 北向/两融（4 统计卡+柱状图+趋势线） |

### ECharts 图表函数

| 函数 | 图表类型 | 说明 |
|---|---|---|
| `initIndustryChart()` | 水平条形图 | 行业资金流，红色渐变 |
| `initSentimentGauges()` | 仪表盘 x4 | 颜色动态：>=70红, >=50橙, >=30黄, <30绿 |
| `initIndexTrendChart()` | 分时折线 / 蜡烛图 | intraday: 折线+均价+昨收虚线+面积; kline: 蜡烛图+成交量（双 grid） |
| `initNorthMarginCharts()` | 柱状图 + 折线 | nb: 正红负绿柱状; margin: 蓝色面积折线 |

### 自选股函数

| 函数 | 说明 |
|---|---|
| `getWatchlist()` | 从 localStorage 读取自选股列表 |
| `saveWatchlist(list)` | 保存到 localStorage |
| `renderWatchlist(container)` | 渲染输入框+添加按钮+卡片网格 |
| `addWatchStock()` | 查找匹配→检查重复→保存→重新渲染 |
| `removeWatchStock(code)` | 移除指定代码 |
| `renderWatchGrid()` | 渲染卡片网格内容 |

### 历史复盘存档函数

| 函数 | 说明 |
|---|---|
| `getArchives()` | 读取存档列表 |
| `saveArchives(list)` | 保存存档列表（只保留最近 90 条） |
| `seedDemoArchive()` | 首次访问注入 5月6日演示存档 |
| `renderHistory(container)` | 保存按钮+存档列表表格 |
| `saveTodayArchive()` | 深拷贝当前 MARKET_DATA→加时间戳→同日替换→保存 |
| `deleteArchive(date)` | 删除指定日期存档 |
| `viewArchive(date)` | 读取存档→替换 MARKET_DATA→renderAll()→插入紫色横幅 |
| `exitArchive()` | `location.reload()` 恢复 |
| `renderHistoryRefresh()` / `renderArchiveList()` | 局部刷新 |

### 筛选交互函数

| 函数 | 说明 |
|---|---|
| `handleFilterChange()` | 筛选变化时触发：更新横幅→详情卡→高亮→表格→自动滚动 |
| `clearFilter()` | 清空所有筛选条件 |

---

## 5. CSS 设计系统

### 色彩变量

#### 背景色系（深色主题）

| 变量 | 值 | 用途 |
|---|---|---|
| `--bg-primary` | `#0d1117` | 最深背景（body / 均价线起点） |
| `--bg-secondary` | `#161b22` | 次深背景（Header / Sidebar / Card） |
| `--bg-tertiary` | `#1c2330` | 卡片内嵌区域 / 输入框 |
| `--bg-hover` | `#21262d` | hover 态背景 |

#### 文字色系

| 变量 | 值 | 用途 |
|---|---|---|
| `--text-primary` | `#e6edf3` | 主文字 |
| `--text-secondary` | `#8b949e` | 次要文字 |
| `--text-muted` | `#6e7681` | 辅助/弱化文字 |

#### 涨跌色系（A 股惯例：红涨绿跌）

| 变量 | 值 | 用途 |
|---|---|---|
| `--red` | `#f85149` | 上涨 / 涨停 / 主线 |
| `--red-light` | `#ff6b6b` | 涨停高亮文字 |
| `--red-bg` | `rgba(248,81,73,0.1)` | 红色背景 |
| `--green` | `#3fb950` | 下跌 / 跌停 / 资金撤退 |
| `--green-light` | `#4ade80` | 跌停高亮文字 |
| `--green-bg` | `rgba(63,185,80,0.1)` | 绿色背景 |

#### 辅助色系

| 变量 | 值 | 用途 |
|---|---|---|
| `--orange` | `#f0883e` | 次主线 |
| `--amber` | `#d29922` | 活口 / 风险提示 |
| `--blue` | `#58a6ff` | 观察 / 筛选高亮 / 链接 |
| `--purple` | `#bc8cff` | 历史回看 / 每周总结 |
| 各 `-bg` 变量 | `rgba(...,0.1)` | 对应浅色背景 |

#### 渐变

| 变量 | 值 | 用途 |
|---|---|---|
| `--gradient-red` | `linear-gradient(135deg, #f85149, #ff7b54)` | Logo |
| `--gradient-blue` | `linear-gradient(135deg, #58a6ff, #388bfd)` | 预留 |

### 布局系统

```css
.app-layout {
  display: grid;
  grid-template-columns: 200px 1fr;
  grid-template-rows: 60px 1fr;
  height: 100vh;
}
```

常用 Grid 模板：

| 类名 | 列数 | 用途 |
|---|---|---|
| `.index-grid` | `repeat(5, 1fr)` | 5 个指数卡片 |
| `.stats-grid` | `repeat(4, 1fr)` | 统计四宫格 |
| `.sentiment-grid` | `repeat(4, 1fr)` | 4 个仪表盘 |
| `.sector-grid` | `auto-fill, minmax(280px, 1fr)` | 板块卡片自适应 |
| `.topic-grid` | `auto-fill, minmax(300px, 1fr)` | 话题卡片自适应 |
| `#watchGrid` | `auto-fill, minmax(210px, 1fr)` | 自选股卡片 |

### 关键组件样式

| 组件 | 核心样式 |
|---|---|
| `.sector-tag` + `.tag-red/orange/blue/amber/green` | 背景 `rgba(...,0.1)`, 文字对应色, 边框 `rgba(...,0.3)` |
| `.data-table` | 表头 `bg-tertiary`, 13px, hover `bg-hover` |
| `.strength-bar` | 60x4px 圆角, 底色 `bg-primary`, 填充 inline style |
| `.sector-card.matched` | border-blue + box-shadow blue |
| `.sector-card.dimmed` | opacity 0.35 |
| `.filter-banner` | sticky top:0, 蓝紫渐变背景, backdrop-filter blur(4px) |
| `.forum-tab` / `.trend-tab` | 8px 18px, active=blue-bg+blue-border+blue-text |
| `.fade-in` | `@keyframes fadeIn` 0.3s ease-out, translateY(10px→0) |

### ECharts 颜色硬编码

| 颜色 | 十六进制 | 用途 |
|---|---|---|
| 涨红 | `#f85149` | K 线阳线、正值柱、分时线（涨） |
| 跌绿 | `#3fb950` | K 线阴线、负值柱、分时线（跌） |
| 均价黄 | `#d29922` | 分时均价线 |
| 北向蓝 | `#58a6ff` | 融资余额趋势线 |
| 网格灰 | `#21262d` | splitLine |
| 轴线灰 | `#30363d` | axisLine |
| 标签灰 | `#6e7681` | axisLabel |
| tooltip 背景 | `#1c2330` | tooltip backgroundColor |
| tooltip 文字 | `#e6edf3` | tooltip textStyle |

### 响应式断点

| 断点 | 变化 |
|---|---|
| `max-width: 1024px` | index-grid → 3 列，stats-grid → 2 列，sentiment-grid → 2 列 |
| `max-width: 768px` | sidebar 隐藏，layout → 单列，index-grid → 2 列，filter-input → 120px，summary-grid/topic-grid → 单列，trend-toolbar → 纵向 |

### 字体

```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
```
基础字号 14px，行高 1.6。

---

## 6. v2 开发路线图

### 已完成

#### v2 阶段一（2026-08-15）✅

| 模块 | 状态 | 关键函数 |
|---|---|---|
| 指数走势 | ✅ | `renderIndexTrend` / `initIndexTrendChart` |
| 涨停复盘 | ✅ | `renderLimitUpReview` |
| 龙虎榜 | ✅ | `renderDragonTiger` |
| 北向/两融 | ✅ | `renderNorthMargin` / `initNorthMarginCharts` |
| 自选股 | ✅ | `renderWatchlist` / `addWatchStock` 等 |
| 历史复盘 | ✅ | `renderHistory` / `viewArchive` 等 |
| 热点聚焦 | ✅ | `renderForumSection` 等 |

数据文件变更：`data.js` 新增 INDEX_TREND / LIMITUP_REASONS / PROMOTION_DATA / DRAGON_TIGER / NORTH_MARGIN + 生成函数

#### v2 阶段二：接入真实数据（2026-08-20）✅

**交付内容**：

| 交付 | 说明 |
|---|---|
| `js/api.js` | 东财 9 数据源接入层：指数行情、涨跌家数、板块广度、指数分时/K线、行业资金流、个股资金流、涨停/跌停池、龙虎榜、两融余额（北向已停更） |
| 跨域方案 | `push2/push2his` 走 JSONP（cb 参数）绕 CORS；`datacenter-web` 支持 CORS 直连 fetch，失败自动降级 JSONP —— **无需代理服务器** |
| 刷新交互 | 顶部「🔄 刷新数据」按钮 + 进度浮层 + 完成 toast + 来源徽章（演示数据/东财实时） |
| 自动存档 | 刷新成功 ≥1 项即自动 `saveTodayArchiveAuto()`，存档标记「自动存档·真实数据」 |
| 实时化渲染 | 指数卡、涨跌停统计、行业/个股资金、龙虎榜、两融、情绪指标、一句话总结、风险边界均接入真实数据；无 API 的模块（涨停原因、热点、主线归类）保留演示并提示 |

**实测结论（2026-08-20 验证）**：
- 浏览器端到端 9/9 数据源全部更新成功，无 JS 错误
- 指数（上证/深成/创业板/科创50/北证50）行情 + 分时 + 60 日 K 线正常
- 涨停池（push2ex 专用接口）当日涨停 73 家、跌停 0 家
- 两融余额 26412 亿（近 8 日趋势）；北向资金自 2024-08-19 起交易所停止披露，页面已改为提示卡片
- 请求节流：串行队列 + 700ms 间隔 + 2 次重试，规避东财限流（短时间内大量请求会被临时封禁，需冷却 1-5 分钟）

**开发步骤回顾**：
1. ✅ 创建 api.js（接口封装层）→ fetch/JSONP 双通道 + 串行队列 + 重试
2. ✅ 验证东财接口可用性 → Node 脚本实测 9 个数据源，确认跨域与字段
3. ✅ app.js 集成 → 刷新按钮 → 进度 → toast → 徽章 → renderAll()
4. ✅ 历史存档自动化 → 刷新成功自动保存
5. ✅ 本地运行测试 → Node 模拟 DOM 端到端 + Edge headless CDP 真机验证

**用户确认事项**：

| 事项 | 用户选择 | 状态 |
|---|---|---|
| 数据来源 | 免费公开接口（东方财富等） | ✅ 已确认 |
| 更新方式 | 打开页面手动点「刷新」 | ✅ 已确认 |
| 历史存档 | 需要（每天保存快照） | ✅ 已确认 |
| 跨域中转 | JSONP 即可，无需代理 | ✅ 已解决 |

### v3 远期规划（未排期）

| 功能 | 依赖 |
|---|---|
| 盘中实时刷新 | 阶段二完成 + 定时器 |
| 多日对比 | 历史存档积累 |
| 情绪趋势图 | 历史存档积累 |
| 自定义复盘模板 | 配置系统 |
| 云端同步 | 需要后端服务 |
| 浅色主题 | CSS 变量扩展 |
| 通知推送 | Notification API |
| RSS 论坛接入 | RSS 解析 + CORS |

### 技术债务

| 项 | 说明 | 优先级 |
|---|---|---|
| ECharts 颜色硬编码 | 未提取为主题文件，无法跟随 CSS 变量 | 中 |
| MARKET_DATA 为 const 但历史回看需修改 | 用 `Object.keys().forEach(delete)` + `Object.assign()` 绕过 | 中 |
| 演示数据生成函数在 data.js | 接入真实数据后应移除 | 低 |
| 无错误边界 | 任一模块渲染失败会中断整个 renderAll | 中 |
| 无 TypeScript | 纯 JS，数据结构无类型约束 | 低 |

---

## 7. 真实数据接入（✅ 已实现，v3.0 服务端代理架构）

> **v3.0 架构（2026-08-21）**：浏览器**不再直连东财**，改为单次 `fetch('/api/market')` 请求本机 Python 服务；由 `server.py`（HTTP服务+缓存）+ `data_provider.py`（数据拉取+解析）完成服务端聚合。接口 URL 与字段映射沿用 v2.2 的 `js/api.js` 逻辑（1:1 移植到 Python），但请求发起方从浏览器变为服务端：
> - **根治风控**：服务端请求无浏览器特征（无 Sec-Fetch 头/localhost Referer），v2.2 一周的 push2 断连/trends2 限流问题全部消失
> - **真假可辨**：失败模块进 `meta.warnings`，前端 toast 明确展示，不再静默回落演示数据
> - **缓存**：服务端 5 分钟内存缓存（成功≥5 模块长缓存，否则 30 秒）；`?refresh=1` 强制绕过
> - **K线三级容错**：东财 `push2his` → 腾讯 `ifzq.gtimg.cn` 备源 → 当日磁盘缓存 `cache/kline.json`（日K历史数据当天不变，缓存有效）
> - v2.2 的实现（浏览器直连版）保留在 git 标签 `v2.2-baseline`，可随时 `git reset --hard v2.2-baseline` 回滚

### 7.0 v3.0 服务层结构

```
js/api.js (浏览器)          server.py (本机:8000)          data_provider.py
────────────────           ──────────────────────          ─────────────────
fetch('/api/market')  ──▶  路由 + 5分钟缓存  ──▶  collect_market() 聚合10个数据模块
  ↓ 响应结构                ├── 静态文件托管                  ├── 东财 push2delay / push2ex / datacenter-web
  { meta: {ok,time,         ├── /api/health                 ├── K线: push2his → 腾讯ifzq → 磁盘缓存
    okCount,failCount,      └── 目录穿越防护(403)             └── 每源独立容错 + warnings 记录
    warnings:[...] },
    data: { 指数行情, 涨跌家数, ... } }
```

`data` 键名（模块名）：`指数行情`（含 indices+breadth）、`涨跌家数`、`板块广度`、`指数分时`（{indices, klineNote}）、`行业资金`（{inflow,outflow}）、`个股资金`、`涨跌停池`、`涨停晋级`（{date,total,stillLimitUp,up,flat,down,promotionRate,avgPct,comment,stocks,limitupReasons}）、`龙虎榜`、`两融余额`、`北向资金`（停更说明）。

### 7.1 数据源总览（实际生效的主机矩阵）

**关键决策：行情类接口一律走延迟镜像 `push2delay`**（延迟 15 分钟，盘后复盘无影响；服务端请求同样稳定）。

| 数据源 | 实际主机 | 用途 | 说明 |
|---|---|---|---|
| 指数行情+涨跌家数 | `push2delay.eastmoney.com/api/qt/ulist.np/get` | 5 大指数 + 沪深涨跌家数 | 合并为一次请求（`fetchMarketBase`） |
| 板块广度 | `push2delay.eastmoney.com/api/qt/clist/get` | 行业板块涨跌家数（方向广度） | `fs=m:90+t:2`，`fid=f3` |
| 指数分时 | `push2delay.eastmoney.com/api/qt/stock/trends2/get` | 3 大指数当日分时 | 内部 4 次递增重试（偶发限流） |
| 指数 K 线 | `push2his.eastmoney.com/api/qt/stock/kline/get` | 3 大指数 60 日 K 线 | push2delay 无 K 线；**三级容错**：东财→腾讯 `web.ifzq.gtimg.cn/appstock/app/fqkline/get`→磁盘缓存 |
| 行业资金流 | `push2delay.eastmoney.com/api/qt/clist/get` | 行业净流入/流出 TOP5 | `fid=f62` |
| 个股资金流 | `push2delay.eastmoney.com/api/qt/clist/get` | 个股净流入/流出 TOP10 | 两次请求（`po=1` 降序 / `po=0` 升序） |
| 涨跌停池 | `push2ex.eastmoney.com` | 涨停/跌停股票池 | `getTopicZTPool` / `getTopicDTPool` |
| 涨停晋级率 | `push2ex.eastmoney.com` | 昨日涨停→今日晋级率 | 查昨日+今日 `getTopicZTPool`（`date=YYYYMMDD`）交叉比对；非晋级股用 `push2delay` 的 `ulist` 查今日涨跌幅分类涨/平/跌；非交易日按数量+首尾代码去重（API 对周末返回最近交易日数据） |
| 龙虎榜 | `datacenter-web.eastmoney.com` | 龙虎榜明细（净买额 TOP8） | `reportName=RPT_DAILYBILLBOARD_DETAILSNEW` |
| 两融余额 | `datacenter-web.eastmoney.com` | 融资余额近 8 交易日 | `reportName=RPTA_RZRQ_LSHJ` |
| 北向资金 | —（已停更） | 2024-08-19 起交易所停止披露 | 返回 `discontinued: true`，页面显示说明 |

**备选数据源**：腾讯行情（`web.ifzq.gtimg.cn`，✅ 已用作 K 线备源）、新浪财经（hq.sinajs.cn）、akshare（Python）——其余尚未使用。

### 7.2 接口详情与字段映射

#### 1. 指数实时行情（实际实现）

```
https://push2delay.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=1.000001,0.399001,0.399006,1.000688,0.899050&fields=f2,f3,f4,f5,f6,f12,f14,f104,f105,f106&ut=fa5fd1943c7b386f172d6893dbfba10b
```

secid 编码：上证 `1.000001` / 深证 `0.399001` / 创业板 `0.399006` / 科创50 `1.000688` / 北证50 `0.899050`（注意：北证50 实际用 `0.899050`，非 `0.BJ...`）

| 接口字段 | 含义 | 映射到 |
|---|---|---|
| `f2` | 最新价 | `indices[].value` |
| `f3` | 涨跌幅% | `indices[].pct` |
| `f4` | 涨跌点数 | `indices[].change` |
| `f5` | 成交量 | - |
| `f6` | 成交额 | `indices[].amount`（`/1e4` 转亿） |
| `f12` | 代码 | `indices[].code` |
| `f14` | 名称 | `indices[].name` |
| `f104` | 上涨家数 | `breadth.advancing` |
| `f105` | 下跌家数 | `breadth.declining` |
| `f106` | 平盘家数 | `breadth.flat` |

> 涨跌家数由上证+深证的 f104/f105/f106 求和得到；`breadthScore = min(100, advPct * 1.25)`。

#### 2. 指数分时数据（实际实现）

```
https://push2delay.eastmoney.com/api/qt/stock/trends2/get?secid=1.000001&fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13&fields2=f51,f53,f56,f58&ndays=1&iscr=0
```

| 接口字段 | 映射到 |
|---|---|
| `f51` 时间 | `intraday[].time`（截取 HH:MM 部分） |
| `f52` 价格 | `intraday[].price` |
| `f53` 均价 | `intraday[].avg` |
| `preClose` | `INDEX_TREND.indices[].prevClose` |

> ⚠️ `trends2` 在 push2delay 偶发瞬时限流（空响应，十几秒自愈）：`fetchIntraday` 内部重试 4 次（间隔 1.5s/2.5s/3.5s 递增），仍失败由 `fetchIndexTrend` 用 K 线兜底或返回空数组。

#### 3. 指数日 K 线（实际实现）

```
https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.000001&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&beg=20260512&end=20500101&lmt=60
```

参数：`klt=101` 日K, `fqt=1` 前复权；`beg` 为当前日期前推 100 天（动态计算），`end=20500101` 取最新 60 根

| 接口字段 | 映射到 |
|---|---|
| `f51` 日期 | `kline[].date`（截取 MM-DD） |
| `f52` 开盘 | `kline[].open` |
| `f53` 收盘 | `kline[].close` |
| `f54` 最高 | `kline[].high` |
| `f55` 最低 | `kline[].low` |
| `f56` 成交量(手) | - |
| `f57` 成交额(元) | `kline[].volume`（`/1e8` 转亿，与演示量纲一致） |

> K 线是唯一保留 `push2his` 的数据：`push2delay` 镜像不提供 K 线（返回空）。

#### 4. 行业板块资金流（实际实现）

```
https://push2delay.eastmoney.com/api/qt/clist/get?pn=1&pz=200&po=1&np=1&fltt=2&invt=2&fid=f62&fs=m:90+t:2&fields=f12,f14,f2,f3,f62,f128,f136
```

参数：`fs=m:90+t:2` 行业板块, `fid=f62` 按主力净流入排序；取前 200 个板块再排序取 TOP5/后5

| 接口字段 | 映射到 |
|---|---|
| `f14` 板块名称 | `industryInflow[].name` |
| `f62` 主力净流入 | `industryInflow[].netInflow`（`/1e8` 转亿） |
| `f3` 涨跌幅 | `industryInflow[].pct` |
| `f128` 领涨股名称 | `industryInflow[].leader` |
| `f136` 领涨股涨幅 | `industryInflow[].leaderPct` |

净流出 TOP5：从全部板块中取 `netInflow < 0` 的最末 5 个再反转。

#### 5. 个股资金流排名（实际实现）

```
https://push2delay.eastmoney.com/api/qt/clist/get?pn=1&pz=200&np=1&fltt=2&invt=2&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048&fields=f12,f14,f2,f3,f62,f100
```

参数：`fs` 覆盖沪深京 A 股（含北交所 `m:0+t:81+s:2048`）；**需两次请求**：`po=1&fid=f62`（净流入 TOP10）+ `po=0&fid=f62`（净流出 TOP10，净额最负在前）

| 接口字段 | 映射到 |
|---|---|
| `f12` 代码 | `stockInflow[].code` |
| `f14` 名称 | `stockInflow[].name` |
| `f62` 主力净流入 | `stockInflow[].netInflow`（`/1e8` 转亿） |
| `f3` 涨跌幅 | `stockInflow[].pct` |
| `f2` 最新价 | `stockInflow[].price` |
| `f100` 所属行业 | `stockInflow[].industry` |

#### 6. 涨跌停池（实际实现）

```
https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=300&sort=fbt:asc&date=20260820
https://push2ex.eastmoney.com/getTopicDTPool?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.dtzt&Pageindex=0&pagesize=200&sort=fund:asc&date=20260820
```

> `date=YYYYMMDD`（当日）；`ut` 用 `7eea3edcaed734bea9cbfc24409ed989`（与行情接口的 `ut` 不同）。相比 5 页 clist 分页，请求量从 5 次降到 2 次，且数据更精确。

| 接口字段 | 映射到 |
|---|---|
| `c` 代码 | `limitStats.limitUpStocks[].code` |
| `n` 名称 | `limitStats.limitUpStocks[].name` |
| `zdp` 涨跌幅 | `limitStats.limitUpStocks[].pct` |

> 涨停原因 (`reason`) 无公开 API 字段，需人工维护或 NLP 分析。免费接口无法区分首板/连板/炸板率，对应卡片显示 `-` 不伪造数据。

#### 7. 龙虎榜（实际实现）

```
https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_DAILYBILLBOARD_DETAILSNEW&columns=ALL&filter=(TRADE_DATE>='2026-08-06')&pageNumber=1&pageSize=30&sortColumns=TRADE_DATE&sortTypes=-1&source=WEB&client=WEB
```

> filter 为「近 14 天」，取最新交易日的全部记录，按 `BILLBOARD_NET_AMT` 降序取 TOP8。席位字段 `BUY_SEAT_NEW`/`SELL_SEAT_NEW` 为 `"营业部名:金额"` 逗号分隔串，解析后取前 3 席。

| 接口字段 | 映射到 |
|---|---|
| `SECURITY_CODE` | `DRAGON_TIGER.items[].code` |
| `SECURITY_NAME_ABBR` | `DRAGON_TIGER.items[].name` |
| `CHANGE_RATE` | `DRAGON_TIGER.items[].pct` |
| `BILLBOARD_NET_AMT` | `DRAGON_TIGER.items[].netBuy`（`/1e8` 转亿） |
| `EXPLANATION` | `DRAGON_TIGER.items[].reason` |
| `BUY_SEAT_NEW` / `SELL_SEAT_NEW` | `DRAGON_TIGER.items[].buys/sells` |

#### 8. 北向资金（已停更）

```
自 2024-08-19 起，沪深港交易所不再披露北向资金实时净买入数据。
fetchNorthbound() 直接返回 { discontinued: true, note: "..." }，页面显示说明文案。
```

#### 9. 两融余额（实际实现）

```
https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPTA_RZRQ_LSHJ&columns=ALL&pageNumber=1&pageSize=8&sortColumns=dim_date&sortTypes=-1&source=WEB&client=WEB
```

| 接口字段 | 映射到 |
|---|---|
| `DIM_DATE` | `margin.trendDays[]`（截取 MM-DD） |
| `RZYE` 融资余额 | `margin.balance` / `margin.trendValues[]`（`/1e8` 转亿） |
| `RZMRE` 融资买入额 | `margin.buyAmount` |
| `RZRQYE` 两融余额 | `margin.rzrqBalance` |

### 7.3 跨域处理方案（实际实现）

| 方案 | 说明 | 状态 |
|---|---|---|
| fetch + JSONP 降级 | `fetchJson()` 先 fetch（带 `Referer: https://quote.eastmoney.com/` + 浏览器 UA 头），失败自动降级 JSONP（`cb`/`callback` 参数） | ✅ 已实现，无需代理 |
| push2delay 镜像 | 行情接口改走延迟 15 分钟镜像，浏览器可直连 | ✅ 已实现 |
| 本地/云代理 | `cors-anywhere`、CloudBase 等 | 未采用（当前无需） |

### 7.4 api.js 实际结构（v2.2）

> 原「设计草案」已废弃，以下为 `js/api.js` 实际实现（~734 行，IIFE 封装）。

```javascript
const API = (() => {
  // 常量：HOST_PUSH=push2delay / HOST_HIS=push2his / UT=fa5fd1943c...
  // 工具：sleep / jsonp / fetchJson（fetch→JSONP 降级）/ enqueue（串行队列，间隔900ms）
  //       / queued（指数退避重试 1.2s/2.4s/3.6s）/ num
  // 数据源：fetchMarketBase（指数+涨跌家数合并）/ fetchMarketDirection / fetchIntraday（4次重试）
  //        / fetchKline / fetchIndexTrend（分时K线解耦）/ fetchIndustryFlow / fetchStockFlow
  //        / fetchLimitStats（push2ex 涨停+跌停池）/ fetchDragonTiger / fetchMargin / fetchNorthbound
  // 文本生成：buildSummaryText / buildSentiment / buildRiskBoundary
  // 合并：applyEnv(env) → 写回 MARKET_DATA / INDEX_TREND / DRAGON_TIGER / NORTH_MARGIN
  // 主入口：refreshAll(onProgress) → { ok: [], fail: [] }
})();
```

**刷新流程（实际）**：

```
用户点击「刷新数据」
  ├── 第一轮：9 个模块【串行】执行（每模块独立 try-catch，间隔 900ms）
  │   ├── 指数行情+涨跌家数（合并1次请求）
  │   ├── 板块广度 / 指数分时 / 行业资金 / 个股资金（2次请求）
  │   ├── 涨跌停池（2次请求）/ 龙虎榜 / 两融余额
  │   └── 成功的记入 ok[]，失败的记入 fail[]
  ├── 第二轮：若 fail 非空，等 3 秒后自动重试失败模块一轮（限流多为瞬时窗口）
  ├── applyEnv() 合并到全局数据
  ├── 刷新成功 ≥1 项 → saveTodayArchiveAuto() 自动存档
  ├── 返回 { ok, fail } → 页面 toast 显示结果
  └── 更新数据来源标签（"真实数据 · HH:MM" / "演示数据"）
```

### 7.5 容错设计（实际）

```
真实数据接口 ──失败──> 保留演示数据（不空白、不报错、不影响其他模块）
指数分时 ──失败──> 用 K 线最后一日的开/收兜底，图表不空白
三个指数分时全挂 ──返回 []──> toast 不误报失败
涨停晋级 ──失败──> PROMOTION_DATA 保留演示默认值，warnings 标注，不阻断其他模块
历史复盘日期 ──v3.1 修复──> applyEnv 从 meta.fetchedAt/龙虎榜日期解析真实交易日写入 MARKET_DATA.date，存档与保存按钮不再显示演示日期
全部模块成功 <1 ──不存档──> 页面提示"行情源偶发限流，等 1-2 分钟重试"
```

### 7.6 注意事项（实际踩坑记录）

1. **`push2` 实时主机断连**：浏览器带 `Sec-Fetch` 头请求 `push2.eastmoney.com` 被直接断开（`ERR_EMPTY_RESPONSE`），curl 正常；**所有行情接口必须走 `push2delay`**。
2. **`trends2` 瞬时限流**：push2delay 的 trends2 偶发空响应（十几秒自愈），需内部重试（已实现 4 次）。
3. **K 线不走 delay**：push2delay 不提供 K 线，K 线保留 `push2his`。
4. **浏览器缓存**：修改 js 后更新 `index.html` 的 `api.js?v=N` 版本号；用户侧 `Ctrl+F5`。
5. **数据延迟**：行情为延迟 15 分钟镜像，盘后约 15:30 后数据完整；北向资金 2024-08-19 起停更。
6. **接口变更风险**：东财接口非官方公开 API，字段可能调整；解析全部集中在 `api.js` 单文件，便于维护。
7. **Node 测试**：需模拟 `document`（JSONP 用）、`data.js` 显式导出 `globalThis.MARKET_DATA`、请求带浏览器 UA。
8. **bat 编码**：`start.bat`/`stop.bat` 必须 GBK + CRLF，UTF-8/LF 会导致 `goto` 失效无法运行。

---

*本文档为 `market-review/docs/` 下 7 个独立文档 + README.md 的合并版，最近同步至 v3.1（2026-08-22）。*

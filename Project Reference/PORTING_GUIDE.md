# 复盘大师 · 移植部署与开发指南

> 本文档面向「在其他电脑 / 平台继续开发或部署」的场景，涵盖环境依赖、部署步骤、数据源架构、编码规范、踩坑记录与优化建议。
>
> 适用版本：**v3.1（2026-08-22）** —— 服务端代理架构完成，浏览器不再直连东财，K线三级容错（东财→腾讯→本地缓存）实测通过；涨停晋级率实时化 + 历史复盘日期同步修复完成。

---

## 1. 项目速览

| 项目 | 说明 |
|---|---|
| 名称 | 复盘大师（market-review） |
| 形态 | **Python 本地服务 + 前端静态页面**（`server.py` 服务端代理拉取东财数据，前端只调 `/api/market`） |
| 数据源 | 东方财富公开接口（**服务端 urllib 拉取**，不走系统代理）+ 腾讯 K 线备源 + 磁盘缓存兜底 |
| 后端 | `server.py`（ThreadingHTTPServer，静态托管 + `/api/market` + `/api/health` + 5 分钟缓存） |
| 依赖 | **零 npm、零 pip、零框架、零构建**；Python 标准库 + 1 个 CDN：ECharts 5.5.0 |
| 运行端口 | 本地 8000（`start.bat` / `server.py` 固定） |
| 当前状态 | ✅ v3.1 服务端代理上线，10/10 模块验证通过，Node E2E 16/16 PASS |

### 核心文件（7 个）

| 文件 | 行数 | 职责 |
|---|---|---|
| `server.py` | ~180 | HTTP 服务：静态托管（`Cache-Control: no-cache`）+ `/api/market`（线程安全 5 分钟缓存）+ `/api/health` |
| `data_provider.py` | ~770 | **数据层核心**（东财 10 个数据模块服务端拉取 + 涨停晋级率 + 重试 + K线三级容错 + warnings 告警 + 磁盘缓存） |
| `index.html` | ~105 | 页面骨架 + 导航 + 引入顺序 |
| `css/style.css` | ~904 | 全部样式（CSS 变量 + Grid 布局，深色主题） |
| `js/data.js` | ~530 | 演示数据兜底 + 全局数据结构定义（末尾 globalThis 暴露，兼容 Node 测试） |
| `js/api.js` | ~290 | **前端接入层**（单次 `fetch('/api/market')` + warnings 映射 + 数据加工，渲染契约与 v2.2 完全一致） |
| `js/app.js` | ~1889 | 全部交互逻辑（渲染 + 图表 + 筛选 + 存储 + 刷新，v3.0 零改动） |

> 关键设计：**API 契约不变**。`api.js` 对 `app.js` 暴露的 `API.refreshAll(onProgress) → Promise<{ok, fail}>` 与 `globalThis.__dataSource` 保持原样，渲染层完全不用改。

---

## 2. 环境依赖清单

| 依赖 | 版本要求 | 说明 |
|---|---|---|
| Python | 3.6+（任意 3.x） | **运行 `server.py`（数据代理 + 静态托管），仅用标准库** |
| 浏览器 | Chrome / Edge 等现代浏览器 | 需支持 `fetch`、`Promise`、`async/await` |
| ECharts | 5.5.0（CDN 引入） | 首次加载需联网；之后走浏览器缓存 |
| 网络 | 需能访问东方财富 / 腾讯行情域名 | 见第 4 节主机列表 |

> **结论：换电脑只需「一个 Python + 整个 `market-review/` 文件夹」，无任何安装步骤。** 与 v2.2 不同，v3.0 **不再支持**用其他静态服务器替代（数据接口在 `server.py` 里，静态服务器无法提供 `/api/market`）。

---

## 3. 部署步骤（换电脑 / 换平台）

### 3.1 Windows（推荐方式，与现有环境一致）

1. **拷贝项目**：整个 `market-review/` 文件夹复制到新电脑（`test/` 目录可删，含浏览器测试临时文件约 570MB）。
2. **检查 Python**：新电脑需有 Python 3。`start.bat` 会自动探测：
   - 环境变量中的 `python`
   - `C:\Users\dl297\AppData\Local\Programs\Python\Python39\python.exe`
   - `C:\Users\dl297\.workbuddy\binaries\python\versions\3.13.12\python.exe`
3. **启动**：双击 `start.bat`（自动检测 8000 端口占用，随后启动 `server.py` 并打开浏览器），访问 `http://127.0.0.1:8000`。关闭服务用 `stop.bat`（按端口杀进程）。
4. **（可选）开机自启动**：把 `start.bat` 的快捷方式放入：
   ```
   C:\Users\<用户名>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\
   ```
   注意：快捷方式需改为**直接指向 `start.bat`**（本机用的是调用器 `复盘大师-开机启动.bat`，其内部 `pushd "F://ZL//AI test//market-review"` 路径需按新位置改写）。

> ⚠️ **换电脑必须改路径**：开机启动器的 `pushd` 路径写死了 `F://ZL//AI test//market-review`，新电脑若路径不同需修改。

### 3.2 macOS / Linux

```bash
cd market-review
python3 server.py
# 浏览器访问 http://127.0.0.1:8000
```

`start.bat` 是 Windows 专用；macOS/Linux 直接跑上面的命令即可，无需改任何代码（`server.py` 纯标准库，跨平台）。

### 3.3 无 Python 环境

**v3.0 不再支持。** 数据拉取逻辑在 `server.py` 中，Node `npx serve` / Live Server 等纯静态服务器**没有 `/api/market` 接口**，页面会提示"无法连接本地服务"并回落演示数据（页面顶部有明确告警，可辨真假）。换电脑请先装 Python 3（零第三方依赖，装完即用）。

### 3.4 云端部署（注意）

可以把 `server.py` 部署到任意支持 Python 的平台（Render / Fly.io / 云服务器等），但注意：

1. `server.py` 当前绑定 `127.0.0.1`（仅本机），云端需改成 `0.0.0.0` 并自行加访问控制；
2. 东财接口对海外 IP 可能限流，境内服务器更稳；
3. 服务端 5 分钟缓存天然适合多人共享场景（一次拉取、多人复用）。

---

## 4. 数据源架构（核心知识）

### 4.1 主机矩阵（必须记住这张表）

| 主机 | 用途 | v3.0 请求方 | 说明 |
|---|---|---|---|
| `push2delay.eastmoney.com` | 行情类（指数/涨跌家数/板块/资金流/分时） | 服务端 | **延迟 15 分钟的行情镜像**；服务端请求完全放行，盘后复盘无影响 |
| `push2his.eastmoney.com` | 历史 K 线（东财主源） | 服务端 | 延迟镜像不提供 K 线，**K 线必须走此主机**；偶发对本机长时间限流（见 4.6 备源） |
| `push2ex.eastmoney.com` | 涨停池/跌停池专用接口 | 服务端 | `getTopicZTPool` / `getTopicDTPool` |
| `datacenter-web.eastmoney.com` | 龙虎榜 / 两融（报表类） | 服务端 | `reportName=RPT_DAILYBILLBOARD_DETAILSNEW` / `RPTA_RZRQ_LSHJ` |
| `web.ifzq.gtimg.cn` | **K 线备源（腾讯）** | 服务端 | `appstock/app/fqkline/get`；东财K线限流时的第一备源，收盘价与东财分时完全吻合 |

### 4.2 v3.0 为什么把请求挪到服务端（架构动机）

v2.2 时代浏览器直连东财存在两类问题，v3.0 全部根治：

1. **风控断连**：`push2.eastmoney.com` 对浏览器请求（带 `Sec-Fetch` 头）直接断连 `net::ERR_EMPTY_RESPONSE`；`push2his` 也会偶发对浏览器限流。Python urllib 服务端请求没有这些浏览器特征，实测稳定。
2. **静默回落演示数据**：v2.2 拉取失败时直接保留演示数据且不报错，用户**真假难辨**（这正是 v3.0 改造的直接起因）。v3.0 每个模块失败都会进 `meta.warnings`，前端 toast 明确展示"哪个模块、什么原因"。

**架构链路**：

```
浏览器 ──fetch──> server.py /api/market ──缓存命中──> 直接返回（<10ms）
                        │ 未命中
                        ▼
                 data_provider.py ──urllib──> 东财 9 数据源（REQ_GAP=0.35s 串行 + 重试）
                        │ K线失败时
                        ▼
                 腾讯备源 → 当日磁盘缓存（cache/kline.json）兜底
```

### 4.3 请求策略（防限流关键，均在 `data_provider.py`）

1. **串行 + 间隔**：所有东财请求按模块顺序执行，**请求间隔 `REQ_GAP = 0.35s`**，宁慢勿快。
2. **指数退避重试**：`get_json_retry` 失败后等 1.2s / 2.4s / 3.6s 再试（`RETRIES = 3`）。
3. **K 线主源快速放弃**：`_fetch_kline_live` 重试 2 次即失败（限流时烧 25 秒重试不如快速切备源）。
4. **服务端 5 分钟缓存**：`CACHE_TTL_OK = 300s`（成功 ≥5 模块才长缓存；`CACHE_OK_THRESHOLD = 5`），失败时短缓存 `CACHE_TTL_FAIL = 30s`；`?refresh=1` 强制绕过。
5. **不走系统代理**：`urllib.request.build_opener(ProxyHandler({}))`，避免本机代理软件劫持行情请求（与 curl 直连行为一致）。
6. **请求合并**：指数行情 + 涨跌家数合并为一次 `ulist` 请求；涨跌停池用专用接口（2 次请求替代 5 页分页）。

### 4.4 关键请求头（`data_provider.py`）

```python
req = urllib.request.Request(url, headers={
    "Referer": "https://quote.eastmoney.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...",
})
```

- `Referer: https://quote.eastmoney.com/`：伪装来源，降低风控概率。
- **浏览器 UA**：Python urllib 默认 UA 易被风控，必须带浏览器 UA。
- **浏览器侧只剩一个请求**（`/api/market`），无任何跨域/风控问题。

### 4.5 告警与容错设计（真假可辨）

```
东财某模块失败 ──> meta.warnings 上报 {module, error} ──> 前端 toast 展示（不静默回落）
K 线东财失败 ──> 腾讯备源（成交额为估算值 vol×100×均价，warning 如实标注）
K 线全失败 ──> 当日磁盘缓存 cache/kline.json（日K当天不变，7 天内有效，warning 标注缓存日期）
前端连不上 server ──> 明确提示"请确认已双击 start.bat 启动服务器"
磁盘缓存 ──> cache/ 目录已加入 .gitignore，删除不影响功能
```

### 4.6 K 线三级容错（实测价值）

开发期间 `push2his` 对本机持续限流 20 分钟以上，三级容错链完整触发并验证：

| 级别 | 数据源 | 触发条件 | 告警文案 |
|---|---|---|---|
| 1 | 东财 `push2his` | 默认主源 | 无（成功时） |
| 2 | 腾讯 `web.ifzq.gtimg.cn` | 东财重试 2 次失败 | "东财K线限流，已切换腾讯备用源（成交额为估算值）" |
| 3 | 磁盘缓存 | 腾讯也失败 | "行情源限流，使用 X月X日 本地缓存" |

三级全失败才抛错进 warnings。腾讯源只有成交量（手）没有成交额，按 `vol_hand × 100 × (open+close+high+low)/4` 估算并如实告警。

### 4.7 涨停晋级率（v3.1 新增，真实计算）

`fetch_promotion()` 实时计算「昨日涨停 → 今日晋级率」，替代 v2.2 硬编码的演示数据（2026-05-06 / 36.6%）：

```
1. 今日涨停池: getTopicZTPool(date=今日)
2. 昨日涨停池: getTopicZTPool(date=往前找最近交易日)
   └─ 非交易日去重: API 对周末返回最近交易日相同数据，按「数量+首尾代码」(_pool_key) 比对跳过
3. 交叉比对: 昨日涨停股今日仍在涨停池 → 晋级(stillLimitUp)
4. 非晋级股: 用 push2delay 的 ulist 批量查今日涨跌幅(f3)，分类 涨/平/跌
5. 涨停原因: 用真实 hybk(行业板块) 替代假题材，原因文案标注"待补充"(无免费 API)
```

| 字段 | 含义 |
|---|---|
| `promotionRate` | 晋级率% = stillLimitUp / 昨日涨停总数 |
| `up` / `flat` / `down` | 非晋级股中上涨 / 平盘 / 下跌的家数 |
| `avgPct` | 昨日涨停股今日平均涨幅% |
| `stocks[]` | 最多 20 只（按今日涨幅降序）：name/code/yBoards(昨日连板数)/todayPct/status(晋级N板\|上涨\|平盘\|下跌) |
| `limitupReasons[]` | 今日涨停原因（最多 15 只，按连板数降序）：name/code/boards/reason(待补充)/theme(真实行业板块)/type(连板\|首板) |

> 实测示例：昨日(08-20)涨停 79 家 → 今日晋级 11 家（**晋级率 13.9%**），上涨 16、平盘 2、下跌 50。失败时 `PROMOTION_DATA` 保留演示默认值，warnings 标注，不阻断其他模块。

---

## 5. 编码规范与踩坑记录（务必遵守）

### 5.1 bat 文件编码（Windows 专属坑）

| 规范 | 说明 |
|---|---|
| **编码** | `start.bat` / `stop.bat` 必须为 **GBK（ANSI）编码** |
| **换行** | 必须为 **CRLF**（Windows 换行） |
| 后果 | 若为 UTF-8 / LF：中文注释乱码、`goto` 标签失效、脚本无法运行 |

修改 bat 后用此命令重新生成（Python 一行搞定）：

```bash
# 从 UTF-8 源转 GBK + CRLF
python -c "open('start.bat','wb').write(open('start.bat',encoding='utf-8').read().replace('\n','\r\n').encode('gbk'))"
```

### 5.2 浏览器缓存（v3.0 已根治）

- `server.py` 对所有静态资源统一返回 `Cache-Control: no-cache`，浏览器每次都拿最新版 JS/CSS。
- **改完前端代码刷新页面即可生效，不再需要版本号 +1 或 `Ctrl+F5`**（v2.2 的 `?v=N` 参数已废弃，index.html 中保留无害）。

### 5.3 Node 测试环境（test/ 目录）

`api.js` 在 Node 中测试需注意（参考 `test/e2e-v3.js`）：

```js
// data.js 顶层 const 不进间接 eval 的全局作用域，末尾已加显式暴露：
//   if (typeof globalThis !== "undefined") { globalThis.MARKET_DATA = MARKET_DATA; ... }
// api.js 用 (0, eval) 按顺序加载 data.js → api.js
// Node 环境下 API_URL 自动取绝对地址 http://127.0.0.1:8000/api/market
// （需先启动 server.py；Node 默认 UA 无关紧要，请求发往本地服务而非东财）
```

### 5.4 全局变量暴露

```js
// api.js 末尾，兼容浏览器 + Node 双环境
if (typeof window !== "undefined") window.API = API;
if (typeof globalThis !== "undefined") globalThis.API = API;
// data.js 末尾同样暴露 MARKET_DATA 等 9 个全局（Node 测试依赖）
```

### 5.5 代码风格约定

- ES5+ 语法（`var`/`function`/`Promise`），无模块化、无打包，保持单文件可读。
- 每个数据源函数独立 `try-catch`，**单模块失败不拖垮整体**。
- 中文注释，标注接口用途与量纲转换（如 `/1e8` 转亿）。

---

## 6. 已知问题与规避策略

| # | 问题 | 现象 | 规避策略 |
|---|---|---|---|
| 1 | `push2.eastmoney.com` 断连 | 浏览器 `net::ERR_EMPTY_RESPONSE` | 已根治：v3.0 服务端请求，不再从浏览器直连东财 |
| 2 | `push2his` 长时间限流 | K 线接口对本机持续空响应 20 分钟以上 | 三级容错：腾讯备源 → 当日磁盘缓存（见 4.6） |
| 3 | 浏览器缓存旧代码 | 更新后页面行为仍旧 | 已根治：`server.py` 静态资源统一 `no-cache` |
| 4 | bat 文件打不开 | 双击无反应 / goto 失效 | GBK + CRLF（见 5.1） |
| 5 | 北向资金停更 | 2024-08-19 起交易所停止披露北向实时净买入 | 接口返回 `discontinued: true`，页面显示说明文案 |
| 6 | 涨停原因无免费 API | 涨停复盘模块的"涨停原因/题材归类"无法自动获取 | **v3.1 已改善**：晋级率已实时化（查昨日+今日涨停池交叉比对）；涨停原因改用真实 `hybk` 行业板块替代假题材，原因文案标注"待补充"，需 NLP/人工补充 |
| 7 | 免费接口变更风险 | 东财接口非官方公开 API，字段可能调整 | 数据解析集中封装在 `data_provider.py`，改动只在单文件 |
| 8 | 首板/连板/炸板率无法区分 | 免费接口只有涨停总数 | 对应卡片置空并显示 `-`，不伪造数据 |
| 9 | 盘中数据为延迟镜像 | 实时用户看到的行情有 15 分钟延迟 | 产品定位是**盘后复盘**，影响可忽略 |
| 10 | 端口 8000 多进程并存 | 旧 server 未退出，新 server 又启动（SO_REUSEADDR 允许并存），行为诡异 | 重启前用 `stop.bat`（按端口杀进程）或任务管理器清理；排查时 `netstat -ano | findstr :8000` 应只见一个 PID |
| 11 | 演示数据与真实数据混淆 | 拉取失败时前端回落演示数据，真假难辨（v2.2 的核心痛点） | v3.0 已根治：失败模块进 `meta.warnings` + toast 明确展示；徽章显示"东财实时"（真）/回落时可见告警 |

---

## 7. 优化建议清单（后续开发方向）

按优先级排列，已标注收益与成本：

| 优先级 | 优化项 | 收益 | 成本 | 说明 |
|---|---|---|---|---|
| 🔴 P0 | 数据本地缓存 | 刷新失败时有上次成功数据可用 | 低 | localStorage/IndexedDB 存最近一次成功 JSON，失败时回退 |
| 🔴 P0 | 定时自动刷新 | 不用手动点 | 低 | `setInterval` 每 5-10 分钟自动刷新 |
| 🟠 P1 | 首板/连板区分 | 涨跌停卡片信息更完整 | 中 | 用涨停池 `pool` 的 `days`/`lbc` 字段统计连板数 |
| 🟠 P1 | 炸板率计算 | 完整四宫格 | 中 | 对比 `getTopicZTPool`（当前涨停）与盘中曾涨停数据 |
| 🟠 P1 | 涨停原因归类 | 涨停复盘模块真正可用 | 高 | 需接第三方题材数据或 NLP，成本高 |
| ✅ 已完成 | ~~行情只读代理~~ | 缓解限流、支持云端部署 | — | **v3.0 已实现**：`server.py` + `data_provider.py` 服务端代理 + 5 分钟缓存 + K 线腾讯备源 |
| ✅ 已完成 | ~~浏览器缓存治理~~ | 改代码即生效 | — | **v3.0 已实现**：静态资源统一 `no-cache` |
| ✅ 已完成 | ~~涨停晋级率实时化~~ | 晋级率/涨平跌分类真实计算 | — | **v3.1 已实现**：`fetch_promotion()` 查昨日+今日涨停池交叉比对，替代硬编码演示数据 |
| ✅ 已完成 | ~~历史复盘日期同步~~ | 存档/保存按钮显示真实交易日 | — | **v3.1 已实现**：`applyEnv` 从 `meta.fetchedAt` 解析真实日期写入 `MARKET_DATA.date` |
| 🟡 P2 | 移动端适配 | 手机查看 | 低 | 当前 Grid 布局已基本自适应，微调即可 |
| 🟡 P2 | 自选股数据实时化 | 自选股模块接入真实行情 | 低 | `data_provider.py` 加 `ulist` 查询即可（服务端无跨域问题） |
| 🟡 P2 | akshare 数据源二期 | 更多免费数据维度 | 中 | 已批准的方案C第二期：逐模块验证 akshare 接口替换/补充东财 |
| 🟢 P3 | 导出复盘报告 | 生成 Markdown/图片存档 | 中 | 把当日数据渲染成文本报告 |
| 🟢 P3 | 多日对比 | 近 5 日涨跌停/资金流趋势 | 中 | 复用存档数据做趋势图 |

### 7.1 架构演进路径（v3.0 更新）

```
v2.2：纯前端 + 东财直连 + 演示数据兜底（真假难辨）
   │
   ▼
v3.0（已完成）：Python 服务端代理 + warnings 告警 + K线三级容错 + no-cache
   │
   ├─ 演进 1（低成本）：localStorage 缓存 + 自动刷新 → 体验完整闭环
   ├─ 演进 2（中成本）：连板/炸板计算 → 涨跌停模块信息补全
   ├─ 演进 3（已批准二期）：akshare 数据源逐模块验证 → 数据维度扩展
   └─ 演进 4（可选）：server.py 改绑 0.0.0.0 + 访问控制 → 局域网/云端多人使用
```

---

## 8. 测试清单

| 测试 | 命令 / 方式 | 验证点 |
|---|---|---|
| 数据层独立测试 | `python data_provider.py` | 10/10 模块成功，打印抽样数据（上证指数、涨停家数、涨停晋级率、龙虎榜日期等） |
| 服务端点 | `curl http://127.0.0.1:8000/api/health` | 服务存活、缓存状态 |
| 统一数据接口 | `curl "http://127.0.0.1:8000/api/market"` | `meta.okCount=10`、warnings 空；`?refresh=1` 强制重拉 |
| 缓存命中 | 连续两次请求 `/api/market` | 第二次 `cached:true` 且耗时 <10ms |
| 目录穿越防护 | `curl --path-as-is "http://127.0.0.1:8000/../server.py"` | 返回 403（注意 curl 默认归一化路径，必须 `--path-as-is`） |
| 端到端（Node） | `node test/e2e-v3.js` | 16 项校验全 PASS（需先启动 `server.py`） |
| 端到端（浏览器） | 打开页面 → 点「刷新数据」 | 徽章"东财实时 + 时间 + 10项"、各模块数据更新（含晋级率与真实日期）、无 JS 报错 |

> `test/.edge-profile*` 为浏览器测试产生的临时文件（约 570MB），**可安全删除**，不影响项目。

---

*文档版本：v3.0 · 2026-08-22 · 与 v3.1 代码同步（服务端代理架构）*

# 股票数据看板工具（A-Share Data Dashboard）

A股盘后复盘的「情报分析中心」——收盘后快速回顾当日盘面、定位主线方向、监控风险信号。

前端 `React + Vite`，后端 `Python FastAPI`，数据源 `akshare`（免费），AI 资讯总结 `智谱 GLM-4-Flash（免费版）`。交付形态为 **bat + 浏览器**：后端同源托管前端构建产物，自动拉起默认浏览器。

---

## 功能概览

| 模块 | 说明 |
|---|---|
| 总览仪表盘 | 4 大指数卡片 + 涨跌停统计 + 行业资金流 TOP + 板块涨跌广度 |
| 历史快照 | 每次刷新成功自动存档（保留最近 30 天），支持按日期回看 |
| 交易日处理 | 非交易日自动显示最近交易日数据，可手动指定日期回看 |
| 自选股 | 支持每只票配置涨跌幅 / 换手率阈值 |
| 异动筛选 | 盘后统一筛选当日超阈值的票集中查看 |
| 龙虎榜 | 榜单明细（净买入 + 买卖席位） |
| 风险预警 | 情绪过热 / 资金撤退 / 大盘破位，总览顶部绿/黄/红等级标签 |
| 资讯 + AI 总结 | 东财资讯接口抓取，可配置智谱 GLM Key 生成智能总结 |

**容错铁律**：单模块失败即显示空态 + 红色重试按钮，**绝不回落演示假数据**。

---

## 环境要求

- Python **3.12.x**（akshare / pandas 依赖需 3.9+，推荐 3.12）
- Node.js **≥ 20**（构建前端用）
- 包管理器任选：Python 侧可用 `pip` 或 `uv`；前端可用 `npm`/`pnpm`

---

## 安装与运行（Windows）

```bat
:: 1. 克隆仓库后，进入项目根目录，创建并激活后端虚拟环境
python -m venv .venv
.venv\Scripts\activate

:: 2. 安装后端依赖
cd backend
pip install -r requirements.txt
cd ..

:: 3. 安装前端依赖并构建（生成 frontend\dist）
cd frontend
npm install
npm run build
cd ..

:: 4. 一键启动
start.bat
```

启动后约 3 秒会自动打开浏览器 `http://127.0.0.1:8003/`。关闭 `start.bat` 的命令窗口即停止后端。

> 使用 `uv` 的用户：`uv venv` + `uv pip install -r backend\requirements.txt` 即可，其余步骤相同。

---

### 不使用 start.bat 的手动启动

```bat
:: 终端 1：后端（会自动托管 frontend\dist）
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8003

:: 手动打开浏览器访问 http://127.0.0.1:8003/
```

---

## AI 智能总结配置（可选）

资讯列表默认可用；AI 总结需要个人 API Key（免费）：

1. 到 [智谱 AI 开放平台](https://open.bigmodel.cn/) 注册并创建 API Key（免费额度）。
2. 打开工具 → 右上角 **AI 设置** → 粘贴 API Key 保存。
3. Key 仅保存在本地 `backend/data/ai_config.json`，不联网上传，**不会被提交到 git**。

未配置 Key 时，资讯照常显示，只是缺少 AI 总结卡片。

---

## 目录结构

```
├── backend/               # FastAPI 后端
│   ├── main.py            # 入口：API 路由 + 静态托管 frontend/dist
│   ├── config.py          # 端口(默认 8003)等配置
│   ├── data_sources/      # 各数据源抓取（akshare）
│   ├── ai_summary.py      # 智谱 GLM 资讯总结
│   └── requirements.txt   # 后端依赖清单
├── frontend/              # React + Vite 前端
│   └── src/               # 源码
├── start.bat              # 一键启动脚本（启动后端 + 自动开浏览器）
├── LICENSE                # MIT
└── PROJECT_MEMORY.md      # 项目开发记忆文档（决策 / 进度 / 军规）
```

运行后自动生成（已被 git 忽略，不入库）：`frontend/dist/`、`backend/data/`（SQLite + 快照 + AI Key）。

---

## 常见问题

**Q1：双击 start.bat 提示 "Python virtualenv not found"**
尚未执行依赖安装。按上文「安装与运行」第 1、2 步先建 `.venv` 并装依赖。

**Q2：提示 "frontend\dist\index.html not found"**
前端未构建。执行 `cd frontend && npm install && npm run build`。

**Q3：提示 "Port 8003 is already in use"**
端口被占用。关闭占用进程，或改 `start.bat` 顶部 `PORT` 与 `backend/config.py` 的 `PORT` 一起改成其他端口。

**Q4：浏览器打不开 / 假数据 / 刷新失败**
数据源来自 akshare（东财等公开接口），可能被限流。失败即空，点击红色「重试」按钮即可，**不会显示假数据**。

**Q5：控制台中文乱码**
历史已知：cmd/控制台 GBK 显示中文源码日志会乱码，浏览器页面（UTF-8）显示正常，不影响功能。

---

## 许可证

[MIT License](LICENSE)

- 数据来源：akshare（公开免费数据接口）
- AI 总结：智谱 GLM-4-Flash（可免费注册获取 Key，个人可选配置）
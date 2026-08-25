"""FastAPI 后端入口

提供以下接口：
- GET  /api/health          健康检查
- POST /api/refresh          触发数据刷新（SSE 流式推送进度）
- GET  /api/snapshot/latest  读取最后一次成功快照
- GET  /api/snapshot/{date}  读取指定日期快照
- GET  /api/snapshot/dates   列出所有有存档的日期
- GET  /api/risk?date=...    计算风险等级（默认最新快照）

启动：uvicorn main:app --host 127.0.0.1 --port 8000 --reload
"""
import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from config import ALL_MODULES, HOST, PORT
from data_sources import FETCHERS
from db import init_db
from risk import calculate_risk
from snapshot import (
    get_latest_snapshot,
    get_snapshot_by_date,
    list_available_dates,
    save_snapshot,
)

# ========== 日志配置 ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("stock_dashboard")


# ========== 生命周期 ==========
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时初始化数据库，停止时无需特殊处理。"""
    init_db()
    logger.info("数据库初始化完成")
    yield


# ========== FastAPI 应用 ==========
app = FastAPI(
    title="A股数据看板工具 API",
    version="0.1.0",
    description="A股盘后复盘工具后端",
    lifespan=lifespan,
)

# 允许前端跨域（开发期 Vite 跑在 5173/5174/5175 等端口）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:5175", "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 健康检查 ==========
@app.get("/api/health")
def health_check() -> dict:
    """健康检查接口

    Returns:
        {"status": "ok", "time": "...", "db": "ok"}
    """
    return {
        "status": "ok",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "db": "ok",
    }


# ========== 获取最近交易日 ==========
def get_today_str() -> str:
    """返回今天的日期字符串 YYYY-MM-DD"""
    return datetime.now().strftime("%Y-%m-%d")


# ========== 数据刷新（SSE 推送进度）==========
@app.post("/api/refresh")
async def refresh_data() -> EventSourceResponse:
    """触发数据刷新，通过 SSE 推送进度。

    每个 SSE 事件格式：
        event: progress
        data: {"module": "indices", "index": 1, "total": 4, "status": "ok|failed", "error": "..."}

    最后一个事件：
        event: done
        data: {"trade_date": "...", "ok_count": 3, "fail_count": 1, "fail_modules": ["..."]}
    """
    trade_date = get_today_str()

    async def event_generator() -> AsyncGenerator[dict, None]:
        ok_count = 0
        fail_count = 0
        fail_modules = []
        total = len(ALL_MODULES)

        # 第1个事件：开始
        yield {
            "event": "progress",
            "data": json.dumps({
                "module": "_start",
                "index": 0,
                "total": total,
                "status": "start",
                "trade_date": trade_date,
            }, ensure_ascii=False),
        }

        for idx, module_name in enumerate(ALL_MODULES, start=1):
            fetcher = FETCHERS[module_name]
            error_msg = None
            status = "ok"
            max_retries = 3  # 最多重试 3 次
            retry_delay = 1  # 初始延迟 1 秒，指数递增

            # 推送"开始拉取"事件
            yield {
                "event": "progress",
                "data": json.dumps({
                    "module": module_name,
                    "index": idx,
                    "total": total,
                    "status": "fetching",
                    "message": f"正在拉取 {module_name} ({idx}/{total})",
                }, ensure_ascii=False),
            }

            # 在线程池中执行同步的 akshare 调用，避免阻塞事件循环
            for attempt in range(1, max_retries + 1):
                try:
                    loop = asyncio.get_event_loop()
                    data = await loop.run_in_executor(None, fetcher, trade_date)
                    # 存档
                    save_snapshot(trade_date, module_name, data, status="ok")
                    ok_count += 1
                    break  # 成功则跳出重试循环
                except Exception as e:
                    error_msg = str(e)
                    status = "failed"
                    if attempt < max_retries:
                        # 还有重试机会，等待后重试
                        logger.warning(
                            f"模块 {module_name} 第{attempt}次失败，"
                            f"{retry_delay}s 后重试: {error_msg}"
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                    else:
                        # 全部重试失败
                        save_snapshot(
                            trade_date, module_name, {"error": error_msg},
                            status="failed", error_msg=error_msg,
                        )
                        fail_count += 1
                        fail_modules.append(module_name)
                        logger.warning(
                            f"模块 {module_name} 全部{max_retries}次重试失败: {error_msg}"
                        )

            # 推送"完成"事件
            yield {
                "event": "progress",
                "data": json.dumps({
                    "module": module_name,
                    "index": idx,
                    "total": total,
                    "status": status,
                    "error": error_msg,
                }, ensure_ascii=False),
            }

        # 最后推送"全部完成"事件
        yield {
            "event": "done",
            "data": json.dumps({
                "trade_date": trade_date,
                "ok_count": ok_count,
                "fail_count": fail_count,
                "fail_modules": fail_modules,
            }, ensure_ascii=False),
        }

    return EventSourceResponse(event_generator())


# ========== 快照接口 ==========
@app.get("/api/snapshot/latest")
def get_latest() -> dict:
    """读取最后一次成功快照

    Returns:
        {
            "trade_date": "...",
            "modules": {...},
            "fetched_at": "..."
        }
    或 {"empty": true} 当无任何存档时
    """
    snap = get_latest_snapshot()
    if snap is None:
        return {"empty": True}
    return snap


@app.get("/api/snapshot/dates")
def get_dates() -> dict:
    """列出所有有存档的日期

    Returns:
        {"dates": ["2026-08-22", "2026-08-21", ...]}
    """
    return {"dates": list_available_dates()}


@app.get("/api/snapshot/{trade_date}")
def get_by_date(trade_date: str) -> dict:
    """读取指定日期的快照

    Args:
        trade_date: YYYY-MM-DD

    Returns:
        快照 dict 或 {"empty": true}
    """
    snap = get_snapshot_by_date(trade_date)
    if snap is None:
        return {"empty": True, "trade_date": trade_date}
    return snap


# ========== 风险等级接口（需求 1.10）==========
@app.get("/api/risk")
def get_risk(trade_date: str | None = None) -> dict:
    """计算风险等级（绿/黄/红 + 一句话）

    Args:
        trade_date: 可选 YYYY-MM-DD；不传则取最新成功快照

    Returns:
        {
            "trade_date": "...",
            "level": "green" | "yellow" | "red",
            "label": "低风险" | "中风险" | "高风险",
            "summary": "...",
            "triggers": [{...}, ...]
        }
        或 {"empty": true} 当无存档时
    """
    if trade_date:
        snap = get_snapshot_by_date(trade_date)
    else:
        snap = get_latest_snapshot()

    if snap is None:
        return {"empty": True}

    risk = calculate_risk(snap["modules"])
    return {"trade_date": snap["trade_date"], **risk}


# ========== 入口 ==========
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=True,  # 开发期热重载
        log_level="info",
    )

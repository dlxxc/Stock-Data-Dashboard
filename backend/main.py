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
from typing import AsyncGenerator, AsyncIterator, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
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
import watchlist as watchlist_svc
from config import (
    WATCHLIST_MAX_SIZE,
    MODULE_WATCHLIST_QUOTES,
    MODULE_DRAGON_TIGER,
    WATCHLIST_DEFAULT_GAIN_PCT,
    WATCHLIST_DEFAULT_LOSS_PCT,
    WATCHLIST_DEFAULT_TURNOVER_PCT,
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

    return EventSourceResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


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


# ========== 自选股接口（阶段 2.1）==========

class WatchItemAddRequest(BaseModel):
    """新增自选股请求体。"""
    stock_code: str = Field(..., description="股票代码，如 600519 或 sh600519")
    stock_name: str = Field(..., description="股票名称")
    gain_pct: float | None = Field(None, gt=0, lt=100, description="涨幅阈值%，默认5")
    loss_pct: float | None = Field(None, gt=0, lt=100, description="跌幅阈值%（绝对值），默认5")
    turnover_pct: float | None = Field(None, gt=0, lt=100, description="换手率阈值%，默认10")


class WatchItemUpdateRequest(BaseModel):
    """修改阈值请求体（只传要改的字段）。"""
    gain_pct: float | None = Field(None, gt=0, lt=100)
    loss_pct: float | None = Field(None, gt=0, lt=100)
    turnover_pct: float | None = Field(None, gt=0, lt=100)


@app.get("/api/watchlist")
def api_list_watchlist() -> dict:
    """列出全部自选股 + 当前数量/上限。

    Returns:
        {
            "items": [{id, stock_code, stock_name, gain_pct, loss_pct, turnover_pct, ...}],
            "count": 10,
            "max_size": 20
        }
    """
    items = watchlist_svc.list_watchlist()
    return {
        "items": [it.to_dict() for it in items],
        "count": len(items),
        "max_size": WATCHLIST_MAX_SIZE,
    }


@app.post("/api/watchlist", status_code=201)
def api_add_watch_item(req: WatchItemAddRequest) -> dict:
    """新增自选股。

    Raises:
        HTTPException 400: 已达上限 或 重复代码
    """
    try:
        item = watchlist_svc.add_watch_item(
            stock_code=req.stock_code.strip(),
            stock_name=req.stock_name.strip(),
            gain_pct=req.gain_pct,
            loss_pct=req.loss_pct,
            turnover_pct=req.turnover_pct,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return item.to_dict()


@app.delete("/api/watchlist/{item_id}")
def api_delete_watch_item(item_id: int) -> dict:
    """删除指定自选股。

    Returns:
        {"deleted": true} 或 {"deleted": false}（id 不存在）
    """
    deleted = watchlist_svc.delete_watch_item(item_id)
    return {"deleted": deleted}


# ========== 批量阈值修改（阶段 2.2 批量设置功能）==========
# 注意：批量路由必须注册在 /{item_id} 之前，否则 FastAPI 会把 "batch-thresholds"
# 当成 item_id 字符串，导致 422 int_parsing 错误。

class WatchlistBatchUpdateRequest(BaseModel):
    """批量设置阈值请求体（支持部分字段）。"""
    ids: List[int] = Field(..., min_length=1, description="要更新的自选股 id 列表")
    gain_pct: float | None = Field(None, gt=0, lt=100, description="涨幅阈值%，None=不改")
    loss_pct: float | None = Field(None, gt=0, lt=100, description="跌幅阈值%，None=不改")
    turnover_pct: float | None = Field(None, gt=0, lt=100, description="换手率阈值%，None=不改")
    reset_to_default: bool = Field(False, description="True 时忽略 3 个阈值字段，全部重置为 config 默认值")


class WatchlistBatchUpdateResponse(BaseModel):
    updated: int
    failed_ids: List[int] = []


@app.patch("/api/watchlist/batch-thresholds", response_model=WatchlistBatchUpdateResponse)
def api_batch_update_thresholds(req: WatchlistBatchUpdateRequest) -> dict:
    """批量修改多只自选股的阈值。

    两种模式（互斥）：
      - reset_to_default=True：忽略 3 个阈值字段，统一重置为 config 默认值（5/5/10）
      - reset_to_default=False：按传入的 gain_pct / loss_pct / turnover_pct 更新（只传需要改的）

    Returns:
        {"updated": N, "failed_ids": [id1, id2, ...]}
    """
    updated = 0
    failed_ids: List[int] = []

    gain = req.gain_pct
    loss = req.loss_pct
    turnover = req.turnover_pct
    if req.reset_to_default:
        gain = WATCHLIST_DEFAULT_GAIN_PCT
        loss = WATCHLIST_DEFAULT_LOSS_PCT
        turnover = WATCHLIST_DEFAULT_TURNOVER_PCT

    for iid in req.ids:
        try:
            watchlist_svc.update_thresholds(
                item_id=iid,
                gain_pct=gain,
                loss_pct=loss,
                turnover_pct=turnover,
            )
            updated += 1
        except ValueError:
            failed_ids.append(iid)
    return {"updated": updated, "failed_ids": failed_ids}


@app.patch("/api/watchlist/{item_id}")
def api_update_watch_thresholds(item_id: int, req: WatchItemUpdateRequest) -> dict:
    """修改指定自选股的阈值。

    Raises:
        HTTPException 404: id 不存在
    """
    try:
        item = watchlist_svc.update_thresholds(
            item_id=item_id,
            gain_pct=req.gain_pct,
            loss_pct=req.loss_pct,
            turnover_pct=req.turnover_pct,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return item.to_dict()


# ========== 自选股异动筛选接口（阶段 2.3）==========

def _normalize_code_6(raw: str) -> str:
    """把 sh600519 / sz000001 / 600519 一律规范成 6 位数字字符串。"""
    if not raw:
        return ""
    s = str(raw).strip().lower()
    for prefix in ("sh", "sz", "bj"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    digits = "".join(ch for ch in s if ch.isdigit())
    return digits.zfill(6) if digits else ""


@app.get("/api/watchlist/alerts")
def api_watchlist_alerts(trade_date: str | None = None) -> dict:
    """按自选股阈值计算当日异动触发票。

    数据来源：当日快照的 `watchlist_quotes` 模块（刷新时统一存档，避免此接口再次调 akshare）。

    Args:
        trade_date: 可选 YYYY-MM-DD；不传则取最新快照

    Returns:
        {
            "trade_date": "...",
            "watch_count": 12,            # 自选股总数
            "quote_count": 10,            # 有行情数据的数量
            "total_triggered": 3,         # 触发任意阈值的数量
            "groups": {
                "gain":     {"count": 1, "items": [AlertItem, ...]},
                "loss":     {"count": 1, "items": [AlertItem, ...]},
                "turnover": {"count": 1, "items": [AlertItem, ...]},
            },
            "items": [AlertItem, ...],    # 全部自选股（含触发状态，便于前端自选股页渲染）
            "empty": false,               # true 当 watchlist 为空 或 无 watchlist_quotes 存档
        }
    """
    # 1. 拿快照（含 watchlist_quotes 模块）
    if trade_date:
        snap = get_snapshot_by_date(trade_date)
    else:
        snap = get_latest_snapshot()

    # 2. 拿 watchlist
    watch_items = watchlist_svc.list_watchlist()
    watch_count = len(watch_items)

    # 3. 任一为空 → 返回 empty
    if snap is None or watch_count == 0:
        return {
            "trade_date": snap["trade_date"] if snap else (trade_date or ""),
            "watch_count": watch_count,
            "quote_count": 0,
            "total_triggered": 0,
            "groups": {
                "gain": {"count": 0, "items": []},
                "loss": {"count": 0, "items": []},
                "turnover": {"count": 0, "items": []},
            },
            "items": [],
            "empty": True,
        }

    modules = snap.get("modules", {}) or {}
    wl_module_in_snap = MODULE_WATCHLIST_QUOTES in modules
    wq_module = modules.get(MODULE_WATCHLIST_QUOTES) or {}

    # 失败检测（军规：失败即空）
    # 来源1：模块返回本身包含 error 字段（数据源层直接失败）
    module_error = wq_module.get("error") if isinstance(wq_module, dict) else None
    # 来源2：决策3的 snapshots 表 status=failed → error 存在于 snap["failed_modules"] 列表中
    if module_error is None:
        failed_list = snap.get("failed_modules") or []
        for fm in failed_list:
            if fm.get("module") == MODULE_WATCHLIST_QUOTES:
                module_error = fm.get("error") or "自选股行情模块拉取失败（快照标记为 failed）"
                break
    # 来源3：模块本身不存在（刷新时未运行此模块）或模块 dict 为空 → 视为"未归档"，返回 empty
    if module_error is None and not wl_module_in_snap:
        module_error = f"快照日期 {snap['trade_date']} 未包含自选股行情模块（watchlist_quotes 尚未归档），请先刷新数据。"
    elif module_error is None and isinstance(wq_module, dict) and len(wq_module) == 0:
        module_error = f"快照日期 {snap['trade_date']} 自选股行情模块为空（无行情数据），请稍后重试或刷新。"

    # 如果 watchlist_quotes 模块失败或未归档 → empty（军规：绝不造数据）
    if module_error:
        return {
            "trade_date": snap["trade_date"],
            "watch_count": watch_count,
            "quote_count": 0,
            "total_triggered": 0,
            "groups": {
                "gain": {"count": 0, "items": []},
                "loss": {"count": 0, "items": []},
                "turnover": {"count": 0, "items": []},
            },
            "items": [],
            "empty": True,
            "error": module_error,
        }

    quotes: list = wq_module.get("quotes", []) or []
    # 兼容旧格式/其他模块用 items 作为字段名
    if not quotes:
        quotes = wq_module.get("items", []) or []
    trade_date_out = snap["trade_date"]

    # 自选股 > 0，但 quotes 全空 → 仍然按 empty（没行情就没阈值判断依据）
    if watch_count > 0 and len(quotes) == 0:
        return {
            "trade_date": trade_date_out,
            "watch_count": watch_count,
            "quote_count": 0,
            "total_triggered": 0,
            "groups": {
                "gain": {"count": 0, "items": []},
                "loss": {"count": 0, "items": []},
                "turnover": {"count": 0, "items": []},
            },
            "items": [],
            "empty": True,
            "error": f"快照日期 {trade_date_out} 自选股行情模块未返回任何报价（watchlist {watch_count} 只全部缺行情）。",
        }

    # 建立 规范 code → quote 映射
    code_to_quote: Dict[str, dict] = {}
    for q in quotes:
        nc = _normalize_code_6(q.get("code", ""))
        if nc:
            code_to_quote[nc] = q
    quote_count = len(code_to_quote)

    # 4. 合并 watchlist + quote，计算触发
    all_items: list = []
    gain_group: list = []
    loss_group: list = []
    turnover_group: list = []
    total_triggered = 0

    for wi in watch_items:
        nc = _normalize_code_6(wi.stock_code)
        q = code_to_quote.get(nc, {})

        pct_chg = q.get("pct_chg")           # None / float
        turnover_rate = q.get("turnover_rate")  # None / float
        price = q.get("price")

        # 触发判断（None 视为未达阈值，不误触发）
        gain_triggered = (
            pct_chg is not None and pct_chg >= wi.gain_pct
        )
        loss_triggered = (
            pct_chg is not None and pct_chg <= (-1.0 * abs(wi.loss_pct))
        )
        turnover_triggered = (
            turnover_rate is not None and turnover_rate >= wi.turnover_pct
        )
        any_triggered = gain_triggered or loss_triggered or turnover_triggered
        if any_triggered:
            total_triggered += 1

        item = {
            "id": wi.id,
            "code": wi.stock_code,
            "code_norm": nc,
            "name": q.get("name") or wi.stock_name,
            "price": price,
            "pct_chg": pct_chg,
            "turnover_rate": turnover_rate,
            "gain_pct_threshold": wi.gain_pct,
            "loss_pct_threshold": wi.loss_pct,
            "turnover_pct_threshold": wi.turnover_pct,
            "gain_triggered": gain_triggered,
            "loss_triggered": loss_triggered,
            "turnover_triggered": turnover_triggered,
            "any_triggered": any_triggered,
        }
        all_items.append(item)
        if gain_triggered:
            gain_group.append(item)
        if loss_triggered:
            loss_group.append(item)
        if turnover_triggered:
            turnover_group.append(item)

    # 5. any_triggered 排序：触发的放最前
    all_items.sort(key=lambda x: (0 if x["any_triggered"] else 1, -x["id"]))

    return {
        "trade_date": trade_date_out,
        "watch_count": watch_count,
        "quote_count": quote_count,
        "total_triggered": total_triggered,
        "groups": {
            "gain": {"count": len(gain_group), "items": gain_group},
            "loss": {"count": len(loss_group), "items": loss_group},
            "turnover": {"count": len(turnover_group), "items": turnover_group},
        },
        "items": all_items,
        "empty": False,
    }


# ========== 龙虎榜接口（阶段 2.4）==========

@app.get("/api/dragon-tiger")
def api_dragon_tiger(trade_date: str | None = None) -> dict:
    """读取龙虎榜快照（当日上榜股票 + 前 5 买/卖出席位）。

    数据来源：当日快照的 `dragon_tiger` 模块（刷新时统一存档，避免此接口再次调 akshare）。

    Args:
        trade_date: 可选 YYYY-MM-DD；不传则取最新快照

    Returns:
        成功：
            {
                "trade_date": "2026-08-25",
                "total": 30,
                "stocks": [{code, name, close, pct_chg, net_buy, ..., seats: {...}}, ...]
            }
        失败 / 未归档：
            {
                "trade_date": "...",
                "total": 0,
                "stocks": [],
                "empty": true,
                "error": "..."
            }
        无任何存档：
            {"empty": true}
    """
    # 1. 拿快照
    if trade_date:
        snap = get_snapshot_by_date(trade_date)
    else:
        snap = get_latest_snapshot()

    if snap is None:
        return {"empty": True}

    modules = snap.get("modules", {}) or {}
    dt_module_in_snap = MODULE_DRAGON_TIGER in modules
    dt_module = modules.get(MODULE_DRAGON_TIGER) or {}

    # 2. 失败检测（军规：失败即空，绝不造数据）
    # 来源1：模块返回本身包含 error 字段（数据源层直接失败）
    module_error = dt_module.get("error") if isinstance(dt_module, dict) else None
    # 来源2：snapshots 表 status=failed → error 存在于 snap["failed_modules"]
    if module_error is None:
        failed_list = snap.get("failed_modules") or []
        for fm in failed_list:
            if fm.get("module") == MODULE_DRAGON_TIGER:
                module_error = fm.get("error") or "龙虎榜模块拉取失败（快照标记为 failed）"
                break
    # 来源3：模块本身不存在（刷新时未运行此模块）→ 视为"未归档"
    if module_error is None and not dt_module_in_snap:
        module_error = (
            f"快照日期 {snap['trade_date']} 未包含龙虎榜模块（dragon_tiger 尚未归档），"
            f"请先刷新数据。"
        )
    elif module_error is None and isinstance(dt_module, dict) and len(dt_module) == 0:
        module_error = f"快照日期 {snap['trade_date']} 龙虎榜模块为空（无上榜数据），请稍后重试或刷新。"

    if module_error:
        return {
            "trade_date": snap["trade_date"],
            "total": 0,
            "stocks": [],
            "empty": True,
            "error": module_error,
        }

    # 3. 成功 → 返回标准化结构（后端 fetch 已经把 stocks 排好序，前端直接用）
    stocks = dt_module.get("stocks", []) or []
    total = dt_module.get("total", len(stocks))

    return {
        "trade_date": snap["trade_date"],
        "total": total,
        "stocks": stocks,
    }


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

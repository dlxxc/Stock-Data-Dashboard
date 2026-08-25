"""自选股数据访问层（阶段 2.1）

提供增删改查（CRUD）操作，在 FastAPI 路由层调用。
数据库表结构定义见 db.init_db()。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Optional

from config import (
    WATCHLIST_MAX_SIZE,
    WATCHLIST_DEFAULT_GAIN_PCT,
    WATCHLIST_DEFAULT_LOSS_PCT,
    WATCHLIST_DEFAULT_TURNOVER_PCT,
)
from db import get_db


@dataclass
class WatchItem:
    """单条自选股记录（业务对象）。"""
    id: int
    stock_code: str
    stock_name: str
    gain_pct: float
    loss_pct: float
    turnover_pct: float
    created_at: str
    updated_at: str

    def to_dict(self) -> dict:
        return asdict(self)


# ========== 查询 ==========
def list_watchlist() -> List[WatchItem]:
    """列出全部自选股（按创建时间正序）。

    Returns:
        [WatchItem, ...]，无记录时返回空列表
    """
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM watchlist ORDER BY created_at ASC"
        ).fetchall()
    return [_row_to_item(r) for r in rows]


def count_watchlist() -> int:
    """返回当前自选股数量。"""
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM watchlist").fetchone()
    return int(row["n"])


def find_by_code(stock_code: str) -> Optional[WatchItem]:
    """按股票代码查询，找不到返回 None。"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM watchlist WHERE stock_code = ?",
            (stock_code,),
        ).fetchone()
    return _row_to_item(row) if row else None


def find_by_id(item_id: int) -> Optional[WatchItem]:
    """按 id 查询，找不到返回 None。"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM watchlist WHERE id = ?",
            (item_id,),
        ).fetchone()
    return _row_to_item(row) if row else None


# ========== 新增 ==========
def add_watch_item(
    stock_code: str,
    stock_name: str,
    gain_pct: Optional[float] = None,
    loss_pct: Optional[float] = None,
    turnover_pct: Optional[float] = None,
) -> WatchItem:
    """新增自选股。

    Args:
        stock_code: 股票代码，如 "600519" 或 "sh600519"，入库原样保留
        stock_name: 股票名称
        gain_pct:  涨幅阈值（%），None 用默认值
        loss_pct:  跌幅阈值（%，绝对值），None 用默认值
        turnover_pct: 换手率阈值（%），None 用默认值

    Returns:
        插入后的 WatchItem（含自增 id）

    Raises:
        ValueError: 超过最大数量限制 或 代码重复
    """
    if count_watchlist() >= WATCHLIST_MAX_SIZE:
        raise ValueError(
            f"自选股已达上限 {WATCHLIST_MAX_SIZE} 只，请先删除后再添加"
        )
    if find_by_code(stock_code) is not None:
        raise ValueError(f"股票 {stock_code} 已在自选股中")

    gain = gain_pct if gain_pct is not None else WATCHLIST_DEFAULT_GAIN_PCT
    loss = loss_pct if loss_pct is not None else WATCHLIST_DEFAULT_LOSS_PCT
    turnover = (
        turnover_pct if turnover_pct is not None else WATCHLIST_DEFAULT_TURNOVER_PCT
    )

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO watchlist
            (stock_code, stock_name, gain_pct, loss_pct, turnover_pct)
            VALUES (?, ?, ?, ?, ?)
            """,
            (stock_code, stock_name, gain, loss, turnover),
        )
        item_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM watchlist WHERE id = ?", (item_id,)
        ).fetchone()

    return _row_to_item(row)


# ========== 删除 ==========
def delete_watch_item(item_id: int) -> bool:
    """按 id 删除自选股。

    Returns:
        True 实际删除，False 记录不存在
    """
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM watchlist WHERE id = ?", (item_id,))
    return cursor.rowcount > 0


# ========== 修改阈值 ==========
def update_thresholds(
    item_id: int,
    gain_pct: Optional[float] = None,
    loss_pct: Optional[float] = None,
    turnover_pct: Optional[float] = None,
) -> WatchItem:
    """修改指定记录的阈值。

    只传需要修改的字段，未传字段保持原值。

    Raises:
        ValueError: 记录不存在
    """
    existing = find_by_id(item_id)
    if existing is None:
        raise ValueError(f"自选股 id={item_id} 不存在")

    new_gain = gain_pct if gain_pct is not None else existing.gain_pct
    new_loss = loss_pct if loss_pct is not None else existing.loss_pct
    new_turnover = (
        turnover_pct if turnover_pct is not None else existing.turnover_pct
    )

    with get_db() as conn:
        conn.execute(
            """
            UPDATE watchlist
            SET gain_pct = ?,
                loss_pct = ?,
                turnover_pct = ?,
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
            """,
            (new_gain, new_loss, new_turnover, item_id),
        )
        row = conn.execute(
            "SELECT * FROM watchlist WHERE id = ?", (item_id,)
        ).fetchone()

    return _row_to_item(row)


# ========== 工具函数 ==========
def _row_to_item(row) -> WatchItem:
    """sqlite3.Row → WatchItem。"""
    return WatchItem(
        id=int(row["id"]),
        stock_code=str(row["stock_code"]),
        stock_name=str(row["stock_name"]),
        gain_pct=float(row["gain_pct"]),
        loss_pct=float(row["loss_pct"]),
        turnover_pct=float(row["turnover_pct"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )

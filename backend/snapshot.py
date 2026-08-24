"""历史快照存档读写

按模块分条存储到 SQLite snapshots 表。
- 写入：INSERT OR REPLACE（同日同模块覆盖旧数据）
- 读取最后快照：取最大 trade_date 的所有模块记录
"""
import json
from typing import Any

from db import get_db


def save_snapshot(
    trade_date: str,
    module_name: str,
    data: dict[str, Any],
    status: str = "ok",
    error_msg: str | None = None,
) -> None:
    """保存单个模块的快照。

    同日同模块会覆盖旧数据（INSERT OR REPLACE）。

    Args:
        trade_date: 交易日 YYYY-MM-DD
        module_name: 模块名（如 "indices"）
        data: 模块数据 dict（会序列化为 JSON）
        status: "ok" 或 "failed"
        error_msg: 失败时的错误信息
    """
    data_json = json.dumps(data, ensure_ascii=False)
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO snapshots
                (trade_date, module_name, data_json, status, error_msg)
            VALUES (?, ?, ?, ?, ?)
            """,
            (trade_date, module_name, data_json, status, error_msg),
        )


def get_latest_snapshot() -> dict[str, Any] | None:
    """读取最后一次成功快照。

    取最大 trade_date 的所有模块记录，组装为：
    {
        "trade_date": "2026-08-22",
        "modules": {
            "indices": {...},
            "limit_pool": {...},
            ...
        }
    }

    Returns:
        快照 dict；无任何存档时返回 None
    """
    with get_db() as conn:
        # 找出最大的 trade_date（有 status='ok' 记录的日期）
        row = conn.execute(
            """
            SELECT MAX(trade_date) as max_date
            FROM snapshots
            WHERE status = 'ok'
            """
        ).fetchone()

        if not row or not row["max_date"]:
            return None

        max_date = row["max_date"]

        # 读取该日所有 ok 模块
        rows = conn.execute(
            """
            SELECT module_name, data_json, created_at
            FROM snapshots
            WHERE trade_date = ? AND status = 'ok'
            ORDER BY module_name
            """,
            (max_date,),
        ).fetchall()

        if not rows:
            return None

        modules = {}
        for r in rows:
            try:
                modules[r["module_name"]] = json.loads(r["data_json"])
            except json.JSONDecodeError:
                continue

        return {
            "trade_date": max_date,
            "modules": modules,
            "fetched_at": rows[0]["created_at"] if rows else None,
        }


def get_snapshot_by_date(trade_date: str) -> dict[str, Any] | None:
    """读取指定日期的快照（供历史回看用）。

    Args:
        trade_date: 交易日 YYYY-MM-DD

    Returns:
        快照 dict；该日无存档返回 None
    """
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT module_name, data_json, status, error_msg, created_at
            FROM snapshots
            WHERE trade_date = ?
            ORDER BY module_name
            """,
            (trade_date,),
        ).fetchall()

        if not rows:
            return None

        modules = {}
        failed_modules = []
        for r in rows:
            try:
                modules[r["module_name"]] = json.loads(r["data_json"])
                if r["status"] == "failed":
                    failed_modules.append({
                        "module": r["module_name"],
                        "error": r["error_msg"] or "未知错误",
                    })
            except json.JSONDecodeError:
                continue

        return {
            "trade_date": trade_date,
            "modules": modules,
            "failed_modules": failed_modules,
            "fetched_at": rows[0]["created_at"] if rows else None,
        }


def list_available_dates() -> list[str]:
    """列出所有有存档的日期（供前端日期选择器用）。

    Returns:
        日期列表，降序排列（最新在前）
    """
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT trade_date
            FROM snapshots
            WHERE status = 'ok'
            ORDER BY trade_date DESC
            """
        ).fetchall()

        return [row["trade_date"] for row in rows]

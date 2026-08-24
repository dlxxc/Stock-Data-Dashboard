"""板块广度数据模块

拉取行业板块涨跌家数（方向广度）。
akshare 接口：stock_board_industry_name_em()
"""
from typing import Any

import akshare as ak


def fetch(trade_date: str) -> dict[str, Any]:
    """拉取板块广度数据。

    Args:
        trade_date: 交易日 YYYY-MM-DD（仅用于存档标记）

    Returns:
        {
            "trade_date": "2026-08-22",
            "total": 86,
            "up_count": 28,
            "down_count": 52,
            "flat_count": 6,
            "up_pct": 32.6,
            "down_pct": 60.5,
            "sectors": [
                {"name": "通信设备", "pct": 3.2, "leader": "...", "leader_pct": 5.67},
                ...
            ]
        }

    Raises:
        RuntimeError: akshare 调用失败或数据为空
    """
    try:
        df = ak.stock_board_industry_name_em()
    except Exception as e:
        raise RuntimeError(f"板块广度拉取失败: {e}") from e

    if df is None or df.empty:
        raise RuntimeError("板块广度返回空数据")

    def to_float(val, default=0.0):
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    sectors = []
    up_count = 0
    down_count = 0
    flat_count = 0

    for _, row in df.iterrows():
        pct = to_float(row.get("涨跌幅"))
        if pct > 0:
            up_count += 1
        elif pct < 0:
            down_count += 1
        else:
            flat_count += 1

        sectors.append({
            "name": str(row.get("板块名称", "")),
            "pct": pct,
            "leader": str(row.get("领涨股票", "")),
            "leader_pct": to_float(row.get("领涨股票-涨跌幅")),
            "total_mv": to_float(row.get("总市值")),
        })

    total = len(sectors)
    return {
        "trade_date": trade_date,
        "total": total,
        "up_count": up_count,
        "down_count": down_count,
        "flat_count": flat_count,
        "up_pct": round(up_count / total * 100, 2) if total > 0 else 0,
        "down_pct": round(down_count / total * 100, 2) if total > 0 else 0,
        "sectors": sectors,
    }

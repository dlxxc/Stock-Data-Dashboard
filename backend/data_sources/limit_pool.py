"""涨跌停池数据模块

拉取当日涨停/跌停股票池。
akshare 接口：
- stock_zt_pool_em(date)：涨停池
- stock_zt_pool_dtgc_em(date)：跌停池
"""
import logging
from datetime import datetime
from typing import Any

import akshare as ak

logger = logging.getLogger(__name__)


def fetch(trade_date: str) -> dict[str, Any]:
    """拉取涨跌停池。

    Args:
        trade_date: 交易日 YYYY-MM-DD（akshare 需 YYYYMMDD 格式）

    Returns:
        {
            "trade_date": "2026-08-22",
            "limit_up": {
                "total": 47,
                "stocks": [{"name": "...", "code": "...", "pct": 10.01, ...}, ...]
            },
            "limit_down": {
                "total": 8,
                "stocks": [...]
            }
        }

    Raises:
        RuntimeError: akshare 调用失败或数据为空
    """
    # akshare 日期格式：YYYYMMDD
    date_str = trade_date.replace("-", "")

    result: dict[str, Any] = {
        "trade_date": trade_date,
        "limit_up": {"total": 0, "stocks": []},
        "limit_down": {"total": 0, "stocks": []},
    }

    # ---- 涨停池 ----
    try:
        df_up = ak.stock_zt_pool_em(date=date_str)
    except Exception as e:
        # 接口异常（反爬/限流/盘前），降级为涨停池空，而非让整个模块 failed
        #（与 dragon_tiger 容错口径一致：盘前无涨停属正常业务态，前端显示「无涨停股」）
        logger.warning(f"涨停池接口异常，降级为空池: {e}")
        df_up = None

    if df_up is not None and not df_up.empty:
        up_stocks = []
        for _, row in df_up.iterrows():
            def to_float(val, default=0.0):
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return default

            up_stocks.append({
                "name": str(row.get("名称", "")),
                "code": str(row.get("代码", "")),
                "pct": to_float(row.get("涨跌幅")),
                "price": to_float(row.get("最新价")),
                "amount": to_float(row.get("成交额")),  # 单位：元
                "circ_mv": to_float(row.get("流通市值")),  # 流通市值
                "total_mv": to_float(row.get("总市值")),
                "times_limit": to_float(row.get("连板数"), 1),  # 连板数
                "first_limit_time": str(row.get("首次封板时间", "")),
                "last_limit_time": str(row.get("最后封板时间", "")),
                "break_count": to_float(row.get("炸板次数"), 0),
                "industry": str(row.get("所属行业", "")),
            })
        result["limit_up"] = {"total": len(up_stocks), "stocks": up_stocks}
    # else: 涨停池为空（盘前/非交易日/当日无涨停）→ 返回空数组而非报错，
    #       让前端显示「暂无涨停」而非「刷新失败」

    # ---- 跌停池 ----
    try:
        df_down = ak.stock_zt_pool_dtgc_em(date=date_str)
    except Exception as e:
        logger.warning(f"跌停池接口异常，降级为空池: {e}")
        df_down = None

    if df_down is not None and not df_down.empty:
        down_stocks = []
        for _, row in df_down.iterrows():
            def to_float(val, default=0.0):
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return default

            down_stocks.append({
                "name": str(row.get("名称", "")),
                "code": str(row.get("代码", "")),
                "pct": to_float(row.get("涨跌幅")),
                "price": to_float(row.get("最新价")),
                "amount": to_float(row.get("成交额")),
                "industry": str(row.get("所属行业", "")),
            })
        result["limit_down"] = {"total": len(down_stocks), "stocks": down_stocks}

    return result

"""资金流数据模块

拉取行业资金流和个股资金流 TOP。
akshare 接口：
- stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")
- stock_individual_fund_flow_rank(indicator="今日")
"""
from typing import Any

import akshare as ak


def fetch(trade_date: str) -> dict[str, Any]:
    """拉取资金流数据。

    Args:
        trade_date: 交易日 YYYY-MM-DD（akshare 此接口返回当日数据，
                    trade_date 仅用于存档标记）

    Returns:
        {
            "trade_date": "2026-08-22",
            "industry_inflow": [{"name": "...", "net_inflow": 28.7, ...}, ...],  # TOP5
            "industry_outflow": [...],  # TOP5
            "stock_inflow": [{"name": "...", "code": "...", ...}, ...],  # TOP10
            "stock_outflow": [...],  # TOP10
        }

    Raises:
        RuntimeError: akshare 调用失败或数据为空
    """
    result: dict[str, Any] = {
        "trade_date": trade_date,
        "industry_inflow": [],
        "industry_outflow": [],
        "stock_inflow": [],
        "stock_outflow": [],
    }

    def to_float(val, default=0.0):
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    # ---- 行业资金流 ----
    try:
        df_industry = ak.stock_sector_fund_flow_rank(
            indicator="今日", sector_type="行业资金流"
        )
    except Exception as e:
        raise RuntimeError(f"行业资金流拉取失败: {e}") from e

    if df_industry is None or df_industry.empty:
        raise RuntimeError("行业资金流返回空数据")

    # akshare 列名：名称/今日主力净流入-净额/今日主力净流入-净占比/今日涨跌幅/...
    # 转换为列表并按净额排序
    industry_list = []
    for _, row in df_industry.iterrows():
        net_inflow = to_float(row.get("今日主力净流入-净额"))
        industry_list.append({
            "name": str(row.get("名称", "")),
            "net_inflow": net_inflow,  # 单位：元（前端展示时转亿）
            "pct": to_float(row.get("今日涨跌幅")),
            "leader": str(row.get("今日主力净流入最大股", "")),
        })

    # 净流入 TOP5（按净额降序）
    sorted_by_inflow = sorted(
        industry_list, key=lambda x: x["net_inflow"], reverse=True
    )
    result["industry_inflow"] = sorted_by_inflow[:5]

    # 净流出 TOP5（按净额升序，即最负的在前）
    sorted_by_outflow = sorted(
        industry_list, key=lambda x: x["net_inflow"]
    )
    result["industry_outflow"] = sorted_by_outflow[:5]

    # ---- 个股资金流 ----
    try:
        df_stock = ak.stock_individual_fund_flow_rank(indicator="今日")
    except Exception as e:
        raise RuntimeError(f"个股资金流拉取失败: {e}") from e

    if df_stock is None or df_stock.empty:
        raise RuntimeError("个股资金流返回空数据")

    stock_list = []
    for _, row in df_stock.iterrows():
        stock_list.append({
            "code": str(row.get("代码", "")),
            "name": str(row.get("名称", "")),
            "net_inflow": to_float(row.get("今日主力净流入-净额")),
            "pct": to_float(row.get("今日涨跌幅")),
            "price": to_float(row.get("最新价")),
        })

    # 净流入 TOP10
    sorted_stock_in = sorted(
        stock_list, key=lambda x: x["net_inflow"], reverse=True
    )
    result["stock_inflow"] = sorted_stock_in[:10]

    # 净流出 TOP10
    sorted_stock_out = sorted(
        stock_list, key=lambda x: x["net_inflow"]
    )
    result["stock_outflow"] = sorted_stock_out[:10]

    return result

"""资金流数据模块

拉取行业资金流 TOP（净流入/流出）。
akshare 接口：stock_fund_flow_industry()（新浪数据源，稳定性更好）

注：新浪数据源仅提供行业资金流，不提供个股资金流。
个股资金流字段（stock_inflow/stock_outflow）保留为空列表。
"""
from typing import Any

import akshare as ak


def fetch(trade_date: str) -> dict[str, Any]:
    """拉取资金流数据。

    Args:
        trade_date: 交易日 YYYY-MM-DD（仅用于存档标记）

    Returns:
        {
            "trade_date": "2026-08-22",
            "industry_inflow": [{"name": "...", "net_inflow": 2.87e9, ...}, ...],  # TOP5
            "industry_outflow": [...],  # TOP5
            "stock_inflow": [],  # 新浪无此数据
            "stock_outflow": [],  # 新浪无此数据
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

    # 新浪数据源：行业资金流
    # 返回列：序号/行业/行业指数/行业-涨跌幅/流入资金/流出资金/净额/公司家数/领涨股/领涨股-涨跌幅/当前价
    try:
        df_industry = ak.stock_fund_flow_industry()
    except Exception as e:
        raise RuntimeError(f"行业资金流拉取失败: {e}") from e

    if df_industry is None or df_industry.empty:
        raise RuntimeError("行业资金流返回空数据")

    # 新浪净额单位为"亿"，需转换为"元"（×1e8）
    YI_TO_YUAN = 1e8

    industry_list = []
    for _, row in df_industry.iterrows():
        net_inflow_yi = to_float(row.get("净额"))
        industry_list.append({
            "name": str(row.get("行业", "")),
            "net_inflow": net_inflow_yi * YI_TO_YUAN,
            "pct": to_float(row.get("行业-涨跌幅")),
            "leader": str(row.get("领涨股", "")),
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

    return result
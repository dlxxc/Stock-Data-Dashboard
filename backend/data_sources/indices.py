"""指数行情数据模块

拉取 5 大指数（上证/深证/创业板/科创50/北证50）实时行情。
akshare 接口：stock_zh_index_spot_em()
"""
from typing import Any

import akshare as ak

from config import INDEX_CODES


def fetch(trade_date: str) -> dict[str, Any]:
    """拉取指数行情。

    Args:
        trade_date: 交易日 YYYY-MM-DD（akshare 此接口返回实时数据，
                    非交易日会返回最近交易日数据，trade_date 仅用于存档标记）

    Returns:
        {
            "indices": [
                {"name": "上证指数", "code": "sh000001", "value": 3315.87,
                 "change": 17.53, "pct": 0.53, "volume": 3847, "amount": 38470000},
                ...
            ]
        }

    Raises:
        RuntimeError: akshare 调用失败或数据为空
    """
    try:
        # 一次性拉取所有指数实时行情
        df = ak.stock_zh_index_spot_em(symbol="指数成份")
    except Exception as e:
        raise RuntimeError(f"akshare 调用失败: {e}") from e

    if df is None or df.empty:
        raise RuntimeError("akshare 返回空数据")

    # akshare 返回的代码格式：sh000001 / sz399001 / bj899050
    # 过滤出我们需要的 5 大指数
    df_filtered = df[df["代码"].isin(INDEX_CODES.values())]

    if df_filtered.empty:
        raise RuntimeError("未匹配到任何目标指数，检查代码格式")

    indices = []
    for _, row in df_filtered.iterrows():
        # 反查名称（用我们的字典，确保顺序一致）
        name = None
        for n, code in INDEX_CODES.items():
            if code == row["代码"]:
                name = n
                break

        # 安全转换数值（akshare 可能返回字符串类型）
        def to_float(val, default=0.0):
            try:
                return float(val)
            except (TypeError, ValueError):
                return default

        indices.append({
            "name": name,
            "code": row["代码"],
            "value": to_float(row.get("最新价")),
            "change": to_float(row.get("涨跌额")),
            "pct": to_float(row.get("涨跌幅")),
            "volume": to_float(row.get("成交量")),
            "amount": to_float(row.get("成交额")),
        })

    # 按 INDEX_CODES 顺序排序（保证前端展示稳定）
    order_map = {code: i for i, code in enumerate(INDEX_CODES.values())}
    indices.sort(key=lambda x: order_map.get(x["code"], 999))

    return {"indices": indices}

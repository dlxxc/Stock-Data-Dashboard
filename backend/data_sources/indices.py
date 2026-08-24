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

    # akshare 返回的代码格式可能是 sh000001 / sz399001 / bj899050
    # 也可能是纯数字 000001 / 399001 / 899050（无前缀）
    # 构建多格式映射：原始代码 → 中文名
    code_to_name: dict[str, str] = {}
    for n, code in INDEX_CODES.items():
        code_to_name[code] = n  # sh000001 → 上证
        # 纯数字版本（去掉 sh/sz/bj 前缀）
        digits = ''.join(c for c in code if c.isdigit())
        code_to_name[digits] = n  # 000001 → 上证

    # 先精确匹配（用我们的原始格式）
    df_filtered = df[df["代码"].isin(INDEX_CODES.values())]

    if df_filtered.empty:
        # 再尝试纯数字匹配
        digit_codes = {''.join(c for c in v if c.isdigit()) for v in INDEX_CODES.values()}
        df_filtered = df[df["代码"].isin(digit_codes)]

    if df_filtered.empty:
        # 打印 akshare 实际返回的代码格式，便于调试
        sample_codes = df["代码"].head(10).tolist()
        raise RuntimeError(f"未匹配到任何目标指数，akshare 返回的代码样例: {sample_codes}")

    indices = []
    for _, row in df_filtered.iterrows():
        raw_code = str(row["代码"])
        # 用多格式映射反查名称
        name = code_to_name.get(raw_code)
        if name is None:
            # 尝试纯数字匹配
            digits = ''.join(c for c in raw_code if c.isdigit())
            name = code_to_name.get(digits)
        if name is None:
            continue  # 跳过不认识的指数

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
    # 用名称排序（因为 code 格式可能不同，但 name 是我们统一的）
    name_order = {n: i for i, n in enumerate(INDEX_CODES.keys())}
    indices.sort(key=lambda x: name_order.get(x["name"], 999))

    return {"indices": indices}

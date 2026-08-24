"""指数行情数据模块

拉取 5 大指数（上证/深证/创业板/科创50/北证50）实时行情。
akshare 接口：stock_zh_index_spot_sina()（新浪数据源，稳定性更好）

注：新浪数据源不含北证50（bj899050），该指数可能缺失。
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
        df = ak.stock_zh_index_spot_sina()
    except Exception as e:
        raise RuntimeError(f"akshare 调用失败: {e}") from e

    if df is None or df.empty:
        raise RuntimeError("akshare 返回空数据")

    # 新浪返回字段：代码/名称/最新价/涨跌额/涨跌幅/昨收/今开/最高/最低/成交量/成交额
    # 构建多格式映射：原始代码 → 中文名
    code_to_name: dict[str, str] = {}
    for n, code in INDEX_CODES.items():
        code_to_name[code] = n
        # 纯数字版本（去掉 sh/sz/bj 前缀）
        digits = ''.join(c for c in code if c.isdigit())
        code_to_name[digits] = n

    # 精确匹配（用新浪的代码格式）
    df_filtered = df[df["代码"].isin(INDEX_CODES.values())]

    if df_filtered.empty:
        # 再尝试纯数字匹配
        digit_codes = {''.join(c for c in v if c.isdigit()) for v in INDEX_CODES.values()}
        df_filtered = df[df["代码"].isin(digit_codes)]

    if df_filtered.empty:
        sample_codes = df["代码"].head(10).tolist()
        raise RuntimeError(f"未匹配到任何目标指数，akshare 返回的代码样例: {sample_codes}")

    def to_float(val, default=0.0):
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    indices = []
    for _, row in df_filtered.iterrows():
        raw_code = str(row["代码"])
        name = code_to_name.get(raw_code)
        if name is None:
            digits = ''.join(c for c in raw_code if c.isdigit())
            name = code_to_name.get(digits)
        if name is None:
            continue

        indices.append({
            "name": name,
            "code": raw_code,
            "value": to_float(row.get("最新价")),
            "change": to_float(row.get("涨跌额")),
            "pct": to_float(row.get("涨跌幅")),
            "volume": to_float(row.get("成交量")),
            "amount": to_float(row.get("成交额")),
        })

    # 按 INDEX_CODES 顺序排序
    name_order = {n: i for i, n in enumerate(INDEX_CODES.keys())}
    indices.sort(key=lambda x: name_order.get(x["name"], 999))

    return {"indices": indices}
"""指数行情数据模块

拉取 4 大指数（上证/深证/创业板/科创50）实时行情。
三级数据源（容错）：
  1. akshare stock_zh_index_spot_sina()：新浪分页接口，完整但反爬敏感，
     工作日上午/晚间时段常被拒（返回 HTML → demjson 报 Can not decode '<'）
  2. 东财 push2 直连（主兜底）：官方实时行情接口，稳定、盘中数据完整，
     返回最新价/昨收/涨跌额
  3. 新浪 hq.sinajs.cn 直连（备兜底）：官方实时行情接口（必须带 Referer，
     否则 403 Forbidden）
"""
import logging
import re
from typing import Any

import requests

from config import INDEX_CODES

logger = logging.getLogger(__name__)

# 东财 push2 实时行情接口（字段值放大 100 倍：92401 → 924.01）
EM_URL = "https://push2.eastmoney.com/api/qt/stock/get"
EM_FIELDS = "f43,f44,f45,f46,f47,f48,f57,f58,f60,f170"
# 指数 secid 映射：交易所前缀 1=上证/深主板 000，0=深市 399
EM_SECIDS = {
    "上证指数": "1.000001",
    "深证成指": "0.399001",
    "创业板指": "0.399006",
    "科创50": "1.000688",
}
EM_HEADERS = {
    "Referer": "https://quote.eastmoney.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# 新浪 hq 实时行情接口（需带 Referer，否则 403）
HQ_URL = "https://hq.sinajs.cn/list="
HQ_HEADERS = {
    "Referer": "https://finance.sina.com.cn",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def _to_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _fetch_from_em() -> list[dict[str, Any]]:
    """通过东财 push2 直连拉取 INDEX_CODES 指定指数（主兜底，稳定）。

    push2 返回 JSON，f43=最新价(×100)、f60=昨收(×100)、f170=涨跌额(×100)。
    """
    indices = []
    for name, secid in EM_SECIDS.items():
        if name not in INDEX_CODES:
            continue
        try:
            res = requests.get(
                EM_URL,
                params={"secid": secid, "fields": EM_FIELDS},
                headers=EM_HEADERS,
                timeout=15,
            )
        except Exception as e:
            raise RuntimeError(f"东财 push2 请求失败: {e}") from e
        if res.status_code != 200:
            raise RuntimeError(f"东财 push2 返回 HTTP {res.status_code}")
        try:
            data = res.json().get("data") or {}
        except ValueError as e:
            raise RuntimeError(f"东财 push2 返回非 JSON: {e}") from e
        if not data.get("f43"):
            raise RuntimeError(f"东财 push2 未返回 {name} 数据")
        # 值 ×100，转回真实值
        value = _to_float(data.get("f43")) / 100.0
        prev_close = _to_float(data.get("f60")) / 100.0
        change = _to_float(data.get("f170")) / 100.0
        pct = (change / prev_close * 100) if prev_close else 0.0
        indices.append({
            "name": name,
            "code": str(data.get("f57", "")),
            "value": value,
            "change": round(change, 4),
            "pct": round(pct, 4),
            "volume": _to_float(data.get("f47")) / 100.0,
            "amount": _to_float(data.get("f48")) / 100.0,
        })

    if not indices:
        raise RuntimeError("东财 push2 未解析到任何目标指数")
    # 按 INDEX_CODES 顺序排序
    name_order = {n: i for i, n in enumerate(INDEX_CODES.keys())}
    indices.sort(key=lambda x: name_order.get(x["name"], 999))
    return indices


def _fetch_from_hq() -> list[dict[str, Any]]:
    """通过新浪 hq.sinajs.cn 直连接口拉取 INDEX_CODES 指定指数（备兜底）。

    hq 返回 GBK 文本，每行格式（逗号分隔，index 对应含义）：
        var hq_str_sh000001="上证指数,今开,昨收,最新,最高,最低,...";
    字段位置（0-based）：0 名称 / 1 今开 / 2 昨收 / 3 最新价 / 8 成交量 / 9 成交额
    """
    codes = list(INDEX_CODES.values())
    url = HQ_URL + ",".join(codes)
    try:
        res = requests.get(url, headers=HQ_HEADERS, timeout=15)
    except Exception as e:
        raise RuntimeError(f"新浪 hq 接口请求失败: {e}") from e

    if res.status_code != 200:
        raise RuntimeError(f"新浪 hq 接口返回 HTTP {res.status_code}")
    text = res.content.decode("gbk", errors="replace")

    indices = []
    pattern = re.compile(r'var hq_str_(?P<sym>[a-z]{2}\d{6})="(?P<body>[^"]*)"')
    for m in pattern.finditer(text):
        sym = m.group("sym")
        body = m.group("body").split(",")
        if len(body) < 32 or not body[0]:
            continue
        name = body[0]
        if name not in INDEX_CODES:
            continue
        last = _to_float(body[3])
        prev_close = _to_float(body[2])
        # 盘中未开盘时最新价为 0，回退到昨收，避免显示 0；涨跌按昨收计为 0
        if last <= 0:
            last = prev_close
        change = (last - prev_close) if last else 0.0
        pct = (change / prev_close * 100) if prev_close else 0.0
        indices.append({
            "name": name,
            "code": sym,
            "value": last,
            "change": round(change, 4),
            "pct": round(pct, 4),
            "volume": _to_float(body[8]),
            "amount": _to_float(body[9]),
        })

    if not indices:
        raise RuntimeError(f"新浪 hq 接口未解析到目标指数，原始文本长度={len(text)}")

    name_order = {n: i for i, n in enumerate(INDEX_CODES.keys())}
    indices.sort(key=lambda x: name_order.get(x["name"], 999))
    return indices


def fetch(trade_date: str) -> dict[str, Any]:
    """拉取 4 大指数实时行情。

    优先 akshare 分页接口；失败（含被反爬返回 HTML）时依次降级到
    东财 push2、新浪 hq 直连。

    Args:
        trade_date: 交易日 YYYY-MM-DD（实时接口，trade_date 仅用于存档标记）

    Returns:
        {
            "indices": [
                {"name": "上证指数", "code": "sh000001", "value": 3315.87,
                 "change": 17.53, "pct": 0.53, "volume": 3847, "amount": 38470000},
                ...
            ]
        }

    Raises:
        RuntimeError: 三级数据源均失败
    """
    # 首选：akshare 新浪分页接口（完整，含成交量/成交额）
    try:
        import akshare as ak
        df = ak.stock_zh_index_spot_sina()
        if df is not None and not df.empty:
            code_to_name: dict[str, str] = {}
            for n, code in INDEX_CODES.items():
                code_to_name[code] = n
                digits = ''.join(c for c in code if c.isdigit())
                code_to_name[digits] = n

            df_filtered = df[df["代码"].isin(INDEX_CODES.values())]
            if df_filtered.empty:
                digit_codes = {''.join(c for c in v if c.isdigit()) for v in INDEX_CODES.values()}
                df_filtered = df[df["代码"].isin(digit_codes)]

            if not df_filtered.empty:
                indices = []
                for _, row in df_filtered.iterrows():
                    raw_code = str(row["代码"])
                    name = code_to_name.get(raw_code)
                    if name is None:
                        name = code_to_name.get(''.join(c for c in raw_code if c.isdigit()))
                    if name is None:
                        continue
                    indices.append({
                        "name": name,
                        "code": raw_code,
                        "value": _to_float(row.get("最新价")),
                        "change": _to_float(row.get("涨跌额")),
                        "pct": _to_float(row.get("涨跌幅")),
                        "volume": _to_float(row.get("成交量")),
                        "amount": _to_float(row.get("成交额")),
                    })
                if indices:
                    name_order = {n: i for i, n in enumerate(INDEX_CODES.keys())}
                    indices.sort(key=lambda x: name_order.get(x["name"], 999))
                    return {"indices": indices}
    except Exception as e:
        logger.warning(f"指数 akshare 接口失败，降级到新浪 hq: {e}")

    # 主兜底：新浪 hq 直连（带 Referer，稳定 200；盘中未开盘自动回退昨收）
    try:
        return {"indices": _fetch_from_hq()}
    except Exception as e:
        logger.warning(f"新浪 hq 失败，降级到东财 push2: {e}")

    # 备兜底：东财 push2（盘中数据完整，但可能被限流）
    return {"indices": _fetch_from_em()}
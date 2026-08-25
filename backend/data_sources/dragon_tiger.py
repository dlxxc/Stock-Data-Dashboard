"""龙虎榜数据模块（阶段 2.4）

拉取当日龙虎榜上榜股票清单 + 前 5 买/卖出席位明细。
akshare 接口：
- stock_lhb_detail_em(start_date, end_date)：龙虎榜详情（主榜单，21 字段）
  字段：代码/名称/收盘价/涨跌幅/龙虎榜净买额/龙虎榜买入额/龙虎榜卖出额/龙虎榜成交额/
        市场总成交额/净买额占总成交比/成交额占总成交比/换手率/流通市值/上榜原因/解读 等
  单位：净买额/买入额/卖出额/成交额/总成交额/流通市值 都是「元」
- stock_lhb_stock_detail_em(symbol, date, flag)：个股买卖席位详情（5 字段）
  flag="买入" 返回买入席位前 5；flag="卖出" 返回卖出席位前 5
  字段：序号/交易营业部名称/买入金额/买入金额-占总成交比例/卖出金额-占总成交比例/净额

数据源策略（军规：绝不显示假数据，失败抛异常由外层统一处理）：
1. 主榜单：stock_lhb_detail_em 当日窗口，失败抛异常让外层存档 status=failed
2. 席位详情：并发调 stock_lhb_stock_detail_em，单只票失败该票 seats=null
   不影响整体榜单（席位是可选详情，不影响上榜股票清单本身的真实性）

时间预算：假设 30 只上榜票 × 2 次调用 = 60 次，8 worker 并发约 15s。
"""
from __future__ import annotations

import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger("stock_dashboard.dragon_tiger")


# ========== 通用工具 ==========
def _safe_float(v) -> Optional[float]:
    """把任意值安全转 float；NaN/空字符串/None/inf/占位符统一转 None。"""
    if v is None:
        return None
    try:
        if isinstance(v, str):
            s = v.strip()
            if s == "" or s in ("-", "--", "---", "nan", "none", "null"):
                return None
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _safe_str(v) -> str:
    """转 str；NaN/None 返回空串。"""
    if v is None:
        return ""
    try:
        if isinstance(v, float) and math.isnan(v):
            return ""
        s = str(v).strip()
        return "" if s.lower() in ("nan", "none", "null") else s
    except Exception:
        return ""


def _retry(fn, *, max_attempts: int = 3, base_sleep_s: float = 1.0, tag: str = ""):
    """指数退避重试：max_attempts=3，失败后等 base_sleep_s * 2^(n-1) 再试。"""
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if attempt < max_attempts:
                wait = base_sleep_s * (2 ** (attempt - 1))
                logger.debug(
                    f"[dragon_tiger][retry] {tag} attempt{attempt} 失败，{wait:.1f}s 后重试: "
                    f"{type(e).__name__}: {str(e)[:120]}"
                )
                time.sleep(wait)
    raise last_exc if last_exc is not None else RuntimeError(f"{tag} retry exhausted")


# ========== 列查找（鲁棒版，与 watchlist_quotes.py 同思路）==========
def _find_col(columns, *, zh: Tuple[str, ...], en: Tuple[str, ...] = ()) -> Optional[str]:
    """从 DataFrame 列名中按中文/英文候选查找，找不到返回 None。

    查找顺序：精确 → 中文子串 → 英文子串（不区分大小写）。
    """
    cols = list(columns)
    if not cols:
        return None
    exact: dict = {str(c).strip(): c for c in cols}

    # 1. 中文/英文精确
    for cand in zh:
        if cand in exact:
            return exact[cand]
    for cand in en:
        c_low = cand.lower()
        for k, v in exact.items():
            if k.lower() == c_low:
                return v

    # 2. 中文子串
    for cand in zh:
        for k, v in exact.items():
            if cand in k:
                return v

    # 3. 英文子串（不区分大小写）
    for cand in en:
        c_low = cand.lower()
        for k, v in exact.items():
            if c_low in k.lower():
                return v

    return None


# ========== 数据源 1：主榜单 stock_lhb_detail_em ==========
def _fetch_detail(trade_date: str) -> pd.DataFrame:
    """拉取主榜单 DataFrame（指定日期的上榜股票清单）。"""
    import akshare as ak

    date_str = trade_date.replace("-", "")

    def _call():
        return ak.stock_lhb_detail_em(start_date=date_str, end_date=date_str)

    return _retry(_call, max_attempts=3, base_sleep_s=1.5, tag="lhb_detail")


def _parse_detail(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """解析主榜单 DataFrame，返回标准化的上榜股票列表（不含席位）。

    Args:
        df: akshare stock_lhb_detail_em 返回的 DataFrame

    Returns:
        [{code, name, close, pct_chg, net_buy, buy_amount, sell_amount,
          total_amount, market_total_amount, net_buy_pct, amount_pct,
          turnover_rate, circ_mv, reason, interpretation, seats: None}, ...]

    Raises:
        ValueError: 缺少「代码」列，无法解析
    """
    c_code = _find_col(df.columns, zh=("代码", "股票代码"), en=("code", "symbol"))
    c_name = _find_col(df.columns, zh=("名称",), en=("name",))
    c_close = _find_col(df.columns, zh=("收盘价",), en=("close",))
    c_pct = _find_col(df.columns, zh=("涨跌幅",), en=("pct_chg", "pctchange"))
    c_net = _find_col(df.columns, zh=("龙虎榜净买额", "净买额"), en=("net_buy",))
    c_buy = _find_col(df.columns, zh=("龙虎榜买入额", "买入额"), en=("buy_amount",))
    c_sell = _find_col(df.columns, zh=("龙虎榜卖出额", "卖出额"), en=("sell_amount",))
    c_total = _find_col(df.columns, zh=("龙虎榜成交额", "成交额"), en=("total_amount",))
    c_mkt = _find_col(df.columns, zh=("市场总成交额",), en=("market_total",))
    c_net_pct = _find_col(df.columns, zh=("净买额占总成交比",), en=("net_buy_pct",))
    c_amt_pct = _find_col(df.columns, zh=("成交额占总成交比",), en=("amount_pct",))
    c_turn = _find_col(df.columns, zh=("换手率",), en=("turnover_rate", "turnover"))
    c_circ_mv = _find_col(df.columns, zh=("流通市值",), en=("circ_mv",))
    c_reason = _find_col(df.columns, zh=("上榜原因",), en=("reason",))
    c_interp = _find_col(df.columns, zh=("解读",), en=("interpretation",))

    if c_code is None:
        raise ValueError(f"stock_lhb_detail_em 缺少「代码」列，无法解析。columns={list(df.columns)}")

    logger.debug(
        f"[dragon_tiger] 主榜单列映射：code={c_code!r} name={c_name!r} close={c_close!r} "
        f"pct={c_pct!r} net={c_net!r} buy={c_buy!r} sell={c_sell!r}"
    )

    stocks: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        code = _safe_str(row.get(c_code))
        if not code:
            continue
        stocks.append({
            "code": code,
            "name": _safe_str(row.get(c_name) if c_name else None),
            "close": _safe_float(row.get(c_close) if c_close else None),
            "pct_chg": _safe_float(row.get(c_pct) if c_pct else None),
            "net_buy": _safe_float(row.get(c_net) if c_net else None),
            "buy_amount": _safe_float(row.get(c_buy) if c_buy else None),
            "sell_amount": _safe_float(row.get(c_sell) if c_sell else None),
            "total_amount": _safe_float(row.get(c_total) if c_total else None),
            "market_total_amount": _safe_float(row.get(c_mkt) if c_mkt else None),
            "net_buy_pct": _safe_float(row.get(c_net_pct) if c_net_pct else None),
            "amount_pct": _safe_float(row.get(c_amt_pct) if c_amt_pct else None),
            "turnover_rate": _safe_float(row.get(c_turn) if c_turn else None),
            "circ_mv": _safe_float(row.get(c_circ_mv) if c_circ_mv else None),
            "reason": _safe_str(row.get(c_reason) if c_reason else None),
            "interpretation": _safe_str(row.get(c_interp) if c_interp else None),
            "seats": None,  # 占位，阶段2填充
        })
    return stocks


# ========== 数据源 2：单票买卖席位 stock_lhb_stock_detail_em ==========
def _fetch_one_seat_side(code: str, date_ymd: str, flag: str) -> List[Dict[str, Any]]:
    """拉单只票 + 单方向（买/卖）的前 5 席位。失败返回空列表。

    Args:
        code: 6 位股票代码（如 "600519"）
        date_ymd: YYYYMMDD 格式日期
        flag: "买入" 或 "卖出"
    """
    import akshare as ak

    def _call():
        return ak.stock_lhb_stock_detail_em(symbol=code, date=date_ymd, flag=flag)

    try:
        df = _retry(_call, max_attempts=2, base_sleep_s=0.6, tag=f"lhb_seat[{code}|{flag}]")
    except Exception as e:
        logger.debug(
            f"[dragon_tiger] 席位 {code}/{flag} 失败: {type(e).__name__}: {str(e)[:100]}"
        )
        return []
    if df is None or df.empty:
        return []

    c_name = _find_col(df.columns, zh=("交易营业部名称", "营业部名称", "名称"), en=("name",))
    c_buy = _find_col(df.columns, zh=("买入金额",), en=("buy_amount", "buy"))
    c_buy_pct = _find_col(df.columns, zh=("买入金额-占总成交比例",), en=("buy_pct",))
    c_sell_pct = _find_col(df.columns, zh=("卖出金额-占总成交比例",), en=("sell_pct",))
    c_net = _find_col(df.columns, zh=("净额",), en=("net",))

    if c_name is None:
        return []

    seats: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        name = _safe_str(row.get(c_name))
        if not name:
            continue
        seats.append({
            "name": name,
            "buy_amount": _safe_float(row.get(c_buy) if c_buy else None),
            "buy_pct": _safe_float(row.get(c_buy_pct) if c_buy_pct else None),
            "sell_pct": _safe_float(row.get(c_sell_pct) if c_sell_pct else None),
            "net": _safe_float(row.get(c_net) if c_net else None),
        })
    return seats


def _fetch_seats_for_stock(code: str, date_ymd: str) -> Optional[Dict[str, List[Dict[str, Any]]]]:
    """单只票拉买 + 卖两方向席位。完全失败返回 None。"""
    buy_seats = _fetch_one_seat_side(code, date_ymd, "买入")
    sell_seats = _fetch_one_seat_side(code, date_ymd, "卖出")
    if not buy_seats and not sell_seats:
        return None
    return {"buy": buy_seats, "sell": sell_seats}


def _fetch_seats_batch(
    stocks: List[Dict[str, Any]],
    date_ymd: str,
    *,
    max_workers: int = 8,
) -> None:
    """并发对榜单所有票拉买卖席位，原地填充 stocks[i]['seats']。

    单票失败 → seats 保持 None，不影响整体榜单（席位是可选详情）。
    """
    if not stocks:
        return
    codes = [s["code"] for s in stocks if s.get("code")]
    logger.info(f"[dragon_tiger] 阶段2：并发拉买卖席位 {len(codes)} 只（workers={max_workers}）")
    ok = 0
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="lhb_seat") as pool:
        future_map = {pool.submit(_fetch_seats_for_stock, code, date_ymd): code for code in codes}
        code_to_seats: Dict[str, Optional[Dict[str, List]]] = {}
        try:
            for fut in as_completed(future_map, timeout=120):
                code = future_map[fut]
                try:
                    seats = fut.result(timeout=10)
                except Exception:
                    seats = None
                code_to_seats[code] = seats
                if seats is not None:
                    ok += 1
        except TimeoutError:
            logger.warning("[dragon_tiger] 阶段2 整体超时，未完成的票席位保持 None")

    # 原地填充
    for s in stocks:
        code = s.get("code")
        if code and code in code_to_seats:
            s["seats"] = code_to_seats[code]
    logger.info(f"[dragon_tiger] 阶段2 完成：{ok}/{len(codes)} 只票拿到席位")


# ========== 对外统一 fetch 接口 ==========
def fetch(trade_date: str) -> Dict[str, Any]:
    """拉取龙虎榜（阶段 2.4）。

    Args:
        trade_date: 交易日 YYYY-MM-DD

    Returns:
        {
            "trade_date": "2026-08-25",
            "total": 30,
            "stocks": [{
                "code": "600519",
                "name": "贵州茅台",
                "close": 1500.00,
                "pct_chg": 5.21,
                "net_buy": 12345678.90,         # 龙虎榜净买额（元）
                "buy_amount": 23456789.00,      # 龙虎榜买入额（元）
                "sell_amount": 11111110.10,     # 龙虎榜卖出额（元）
                "total_amount": 34567899.10,    # 龙虎榜成交额（元）
                "market_total_amount": ...,     # 市场总成交额（元）
                "net_buy_pct": 1.25,             # 净买额占总成交比 %
                "amount_pct": 3.50,              # 成交额占总成交比 %
                "turnover_rate": 4.21,           # 换手率 %
                "circ_mv": 1880000000000.00,    # 流通市值（元）
                "reason": "日涨幅偏离值达7%的证券",
                "interpretation": "...",
                "seats": {
                    "buy": [{"name", "buy_amount", "buy_pct", "sell_pct", "net"}, ...5],
                    "sell": [{...}, ...5],
                } | None,
            }, ...]
        }

    Raises:
        RuntimeError: 主榜单 akshare 调用失败或返回空
    """
    date_ymd = trade_date.replace("-", "")

    # 阶段 1：主榜单
    logger.info(f"[dragon_tiger] 阶段1：主榜单 stock_lhb_detail_em({date_ymd})")
    df = _fetch_detail(trade_date)
    if df is None or df.empty:
        # 主榜单为空：可能非交易日 / 当日无票上榜 / 盘前未更新（17:00+ 才更新）
        # 选择抛异常让外层存档 status=failed，让用户感知「拉取失败，点此重试」
        # 而不是返回空榜单误导用户以为「当日无票上榜」（这可能是真的，也可能是接口问题）
        raise RuntimeError(
            f"龙虎榜主榜单返回空（{trade_date} 可能非交易日 / 接口异常 / 盘前未更新，17:00 后再试）"
        )

    stocks = _parse_detail(df)
    logger.info(f"[dragon_tiger] 阶段1：主榜单解析到 {len(stocks)} 只上榜票")

    # 阶段 2：买卖席位（并发，单票失败不影响整体）
    _fetch_seats_batch(stocks, date_ymd, max_workers=8)

    # 按净买入额降序排序（净买入 = 主力资金净流入，最有情报价值）
    # None 视为 0 处理（避免排序异常）
    stocks.sort(key=lambda s: -(s.get("net_buy") or 0.0))

    return {
        "trade_date": trade_date,
        "total": len(stocks),
        "stocks": stocks,
    }


if __name__ == "__main__":
    # 本地调试：cd backend; $env:PYTHONPATH="."; python data_sources/dragon_tiger.py
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    today = datetime.now().strftime("%Y-%m-%d")
    import json
    result = fetch(today)
    print(f"\ntrade_date={result['trade_date']} total={result['total']}")
    for s in result["stocks"][:5]:
        print(f"  {s['code']} {s['name']} 净买={s['net_buy']} 涨={s['pct_chg']}% 原因={s['reason']}")
        if s.get("seats"):
            for seat in s["seats"].get("buy", [])[:2]:
                print(f"    [买] {seat['name']} 净={seat['net']}")

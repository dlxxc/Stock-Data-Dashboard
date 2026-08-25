"""自选股当日行情模块（阶段 2.2/2.3，重写 v2）

拉取全部 A 股当日行情后，按自选股代码过滤。
字段：代码、名称、最新价、涨跌幅、换手率、成交量、成交额。

数据源三阶段策略（军规：绝不显示假数据，失败抛异常由外层统一处理）：

1. 主源：东财 `stock_zh_a_spot_em`（文档有23列含「换手率」；实际偶发服务端降级仅14列）
2. 回退：新浪 `stock_zh_a_spot`（仅14列，稳定但**不含换手率**）
3. 兜底（关键新增）：对 1+2 之后仍缺少 `turnover_rate` 的自选股，**按单票精确补换手率**
   - 优先：`stock_individual_info_em(symbol=code)` 东财单票基本面接口
   - 次优：`stock_zh_a_hist(symbol=code, period="daily", start=today, end=today, adjust="qfq")` 取当日K线行
   - 超时控制：单票 ≤ 3s，100 只总控 ≤ 60s

自选股为空时直接返回空列表（不算失败）。
"""
from __future__ import annotations

import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

import watchlist as watchlist_svc

logger = logging.getLogger("stock_dashboard.watchlist_quotes")


# ========== 标准化输出结构 ==========
class QuoteItem(dict):
    """单只票的标准化行情字典（便于 JSON 序列化）。"""
    pass


def _make_quote(
    *,
    code: str,
    name: Optional[str] = None,
    price: Optional[float] = None,
    pct_chg: Optional[float] = None,
    turnover_rate: Optional[float] = None,
    volume: Optional[float] = None,
    amount: Optional[float] = None,
) -> QuoteItem:
    """构造统一格式的行情条目，字段缺省用 None（异动筛选安全处理 None→视为未达阈值）。"""
    return QuoteItem(
        code=code,
        name=name,
        price=_safe_float(price),
        pct_chg=_safe_float(pct_chg),
        turnover_rate=_safe_float(turnover_rate),
        volume=_safe_float(volume),
        amount=_safe_float(amount),
    )


def _safe_float(v) -> Optional[float]:
    """把任意值安全转 float；NaN/空字符串/None/inf 统一转 None。"""
    if v is None:
        return None
    try:
        if isinstance(v, str) and v.strip() == "":
            return None
        # pandas 可能带 '-' 或 '--'
        if isinstance(v, str) and v.strip().lstrip('+-.,%').replace('.', '').isdigit() is False and not v.strip().replace('-', '', 1).replace('.', '', 1).isdigit():
            return None
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


# ========== 代码规范化（消除 sh/sz/bj 前缀，保留 6 位纯数字）==========
def _normalize_code(raw) -> str:
    """把 sh600519 / sz000001 / 600519 / 600519.SZ 一律规范成 6 位数字字符串。"""
    if raw is None:
        return ""
    s = str(raw).strip().lower()
    # 先剥类似 .SZ / .SH / .BJ 后缀（东财个别接口用）
    for suffix in (".sz", ".sh", ".bj"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
            break
    # 去常见前缀
    for prefix in ("sh", "sz", "bj"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    digits = "".join(ch for ch in s if ch.isdigit())
    return digits.zfill(6) if digits else ""


# ========== 通用列查找（鲁棒版：中文同义词 + 英文 + 位置兜底）==========
def _build_col_map(df_columns) -> Tuple[dict, dict]:
    """返回 (exact_lower_map, fuzzy_candidates_map)。
    exact_lower_map:  {列名小写.strip(): 原列名}
    fuzzy_candidates_map: 模糊索引，key=关键字（去空格/小写/简体），value=候选原列名列表
    """
    cols = list(df_columns)
    exact: dict = {}
    fuzzy: Dict[str, list] = {}
    for c in cols:
        raw = c
        s = str(c).strip()
        exact[s.lower()] = raw
        # 去空格/符号做模糊
        norm = "".join(ch for ch in s.lower() if ch.isalnum())
        if norm:
            fuzzy.setdefault(norm, []).append(raw)
        # 中文单字切分（按字）
        for ch in s:
            if "\u4e00" <= ch <= "\u9fff":
                fuzzy.setdefault(ch, []).append(raw)
    return exact, fuzzy


def _find_col(columns, *, zh: Tuple[str, ...], en: Tuple[str, ...] = (), position_hint: Optional[int] = None) -> Optional[str]:
    """鲁棒查找列。
    zh: 中文候选（精确），如 ("换手率", "换手")
    en: 英文候选（精确/子串），如 ("turnoverrate", "turnover")
    position_hint: 如果前面都没找到，文档给的位置索引兜底（如 14），超出范围跳过
    """
    cols = list(columns)
    if not cols:
        return None
    exact, fuzzy = _build_col_map(cols)

    # 1. 中文精确
    for cand in zh:
        if cand.lower() in exact:
            return exact[cand.lower()]
    # 2. 英文精确
    for cand in en:
        if cand.lower() in exact:
            return exact[cand.lower()]

    # 3. 中文模糊（列包含任一候选词）
    for cand in zh:
        key_cand = "".join(ch for ch in cand.lower() if ch.isalnum())
        if key_cand:
            # 找列名里包含所有字符的
            for k, candidates in fuzzy.items():
                if key_cand in k or all(ch in k for ch in cand.lower() if "\u4e00" <= ch <= "\u9fff"):
                    return candidates[0]
    # 3b. 英文模糊子串
    for cand in en:
        c_low = cand.lower()
        for k, candidates in fuzzy.items():
            if c_low in k:
                return candidates[0]

    # 4. 位置索引兜底（文档 outputs 给的位置，对 14/23 列降级版本很有用）
    if position_hint is not None and 0 <= position_hint < len(cols):
        return cols[position_hint]
    return None


# ========== 数据源 1：东财 stock_zh_a_spot_em（主源，加重试）==========
def _fetch_em() -> pd.DataFrame:
    import akshare as ak
    def _call():
        return ak.stock_zh_a_spot_em()
    return _retry(_call, max_attempts=3, base_sleep_s=1.5, tag="batch_em_spot")


def _parse_em(df: pd.DataFrame, code_set: set) -> Dict[str, QuoteItem]:
    """返回 {规范6位code: QuoteItem}。

    接口 outputs 文档（stock_zh_a_spot_em）：
      [1]代码 [2]名称 [3]最新价 [4]涨跌幅 [6]成交量 [7]成交额 [14]换手率
    但有时服务端降级为 14 列（无买入/卖出/量比/市盈率/市值/换手等），需鲁棒处理。
    """
    # 列名查找（文档位置索引兜底）
    c_code = _find_col(df.columns, zh=("代码", "证券代码", "股票代码"), en=("code", "symbol"), position_hint=1)
    c_name = _find_col(df.columns, zh=("名称", "证券简称", "股票名称"), en=("name",), position_hint=2)
    c_price = _find_col(df.columns, zh=("最新价", "现价", "最新"), en=("price", "trade", "close"), position_hint=3)
    c_pct = _find_col(df.columns, zh=("涨跌幅",), en=("pct_chg", "changepercent", "pctchange"), position_hint=4)
    # 换手率：文档位置索引 14（outputs 第 14 项）
    c_turn = _find_col(df.columns, zh=("换手率", "换手"), en=("turnoverrate", "turnover"), position_hint=14)
    c_vol = _find_col(df.columns, zh=("成交量",), en=("volume",), position_hint=6)
    c_amt = _find_col(df.columns, zh=("成交额",), en=("amount", "turnover"), position_hint=7)

    if c_code is None:
        raise ValueError("东财 stock_zh_a_spot_em 返回缺少「代码」列，无法匹配自选股")

    logger.debug(
        f"[watchlist_quotes] 东财解析：列映射 code={c_code!r} name={c_name!r} price={c_price!r} "
        f"pct={c_pct!r} turn={c_turn!r} vol={c_vol!r} amt={c_amt!r}"
    )

    result: Dict[str, QuoteItem] = {}
    for _, row in df.iterrows():
        code_raw = row.get(c_code)
        code = _normalize_code(code_raw)
        if not code or code not in code_set:
            continue
        result[code] = _make_quote(
            code=code,
            name=row.get(c_name) if c_name else None,
            price=row.get(c_price) if c_price else None,
            pct_chg=row.get(c_pct) if c_pct else None,
            turnover_rate=row.get(c_turn) if c_turn else None,
            volume=row.get(c_vol) if c_vol else None,
            amount=row.get(c_amt) if c_amt else None,
        )
    return result


# ========== 数据源 2：新浪 stock_zh_a_spot（回退，加重试）==========
def _fetch_sina() -> pd.DataFrame:
    import akshare as ak
    def _call():
        return ak.stock_zh_a_spot()
    return _retry(_call, max_attempts=3, base_sleep_s=1.5, tag="batch_sina_spot")


def _parse_sina(df: pd.DataFrame, code_set: set) -> Dict[str, QuoteItem]:
    """新浪 outputs 文档 14 列：[0]代码 [1]名称 [2]最新价 [3]涨跌额 [4]涨跌幅 [11]成交量 [12]成交额 [13]时间戳
    注意：新浪 stock_zh_a_spot **不含换手率**（14 列结构无该字段），需要第 3 阶段单票兜底。"""
    c_code = _find_col(df.columns, zh=("代码", "symbol"), en=("symbol", "code"), position_hint=0)
    c_name = _find_col(df.columns, zh=("名称",), en=("name",), position_hint=1)
    c_price = _find_col(df.columns, zh=("最新价", "现价", "trade"), en=("trade", "price"), position_hint=2)
    c_pct = _find_col(df.columns, zh=("涨跌幅",), en=("changepercent", "pct_chg"), position_hint=4)
    # 新浪 14 列文档明确没换手率；但万一接口变了，位置不兜底（避免拿错成交量/成交额）
    c_turn = _find_col(df.columns, zh=("换手率", "换手"), en=("turnoverrate", "turnoverratio"), position_hint=None)
    c_vol = _find_col(df.columns, zh=("成交量",), en=("volume",), position_hint=11)
    c_amt = _find_col(df.columns, zh=("成交额",), en=("amount",), position_hint=12)

    if c_code is None:
        raise ValueError("新浪 stock_zh_a_spot 返回缺少代码列（symbol）")

    result: Dict[str, QuoteItem] = {}
    for _, row in df.iterrows():
        code_raw = row.get(c_code)
        code = _normalize_code(code_raw)
        if not code or code not in code_set:
            continue
        result[code] = _make_quote(
            code=code,
            name=row.get(c_name) if c_name else None,
            price=row.get(c_price) if c_price else None,
            pct_chg=row.get(c_pct) if c_pct else None,
            turnover_rate=row.get(c_turn) if c_turn else None,
            volume=row.get(c_vol) if c_vol else None,
            amount=row.get(c_amt) if c_amt else None,
        )
    return result


# ========== 单票接口：重试工具（指数退避）==========
def _retry(fn, *, max_attempts: int = 3, base_sleep_s: float = 1.0, tag: str = ""):
    """max_attempts=3，失败后等 2s/4s/8s 再试（指数退避）。fn 抛异常→重试；无异常→返回值。"""
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if attempt < max_attempts:
                wait = base_sleep_s * (2 ** (attempt - 1))
                logger.debug(f"[watchlist_quotes][retry] {tag} attempt{attempt} 失败，{wait:.1f}s 后重试: {type(e).__name__}: {str(e)[:120]}")
                time.sleep(wait)
    # 最后一次也失败，向外抛最后一个异常
    raise last_exc if last_exc is not None else RuntimeError(f"{tag} retry exhausted")


# ========== 数据源 3：单票精确补换手率（兜底，v2）==========
def _code_to_sina_sh_sz_bj_prefix(code6: str) -> str:
    """把 6 位数字 code 转成新浪 stock_zh_a_daily 需要的 symbol 前缀：sh/sz/bj。"""
    if not code6 or len(code6) != 6:
        return "sz"
    # 北交所：4 开头 / 8 开头（83/87/88 等）/ 92 开头（新股）
    if code6.startswith("4") or code6.startswith("8") or code6.startswith("92"):
        return "bj"
    # 上交所主板：6 开头；科创板：688 开头
    # 上交所可转债/基金：11/511...，但我们自选股主要是 6/0/3 开头的票
    if code6.startswith(("5", "6", "9")):
        return "sh"
    # 深交所主板/创业板：0 开头 / 3 开头
    return "sz"


def _extract_percent_from_turnover_value(raw: float) -> float:
    """新浪/东财返回 turnover 有两种比例：
    - 新浪 stock_zh_a_daily 列 turnover：0.003097 = 0.31%  → *100
    - 东财 stock_zh_a_hist 列 换手率：3.097 = 3.10%       → 不用动
    - 东财 stock_individual_info_em 行 换手率：3.097 = 3.10% → 不用动
    边界 <1 视为小数形式。
    """
    v = _safe_float(raw)
    if v is None:
        return None
    return v * 100.0 if (-1.0 < v < 1.0) else v


def _fill_turnover_one(code6: str, trade_date_ymd: str) -> Optional[float]:
    """给一只 code 补当日（或最近交易日）换手率百分比；都失败返回 None。

    优先级 + 理由：
      1) 新浪 stock_zh_a_daily（主）：服务器稳定不崩，tail 行必含 turnover 列（小数 0.xx）
      2) 新浪 stock_zh_a_daily（adjust="" 兜底，避免 qfq 偶发缺数据）
      3) 东财 stock_individual_info_em（重试 3 次，偶尔通）
      4) 东财 stock_zh_a_hist 当日K线（重试 3 次，偶尔通）
    """
    import akshare as ak

    # —— 1) 新浪 stock_zh_a_daily，qfq，取最近日期行 ——
    prefix = _code_to_sina_sh_sz_bj_prefix(code6)
    symbol = f"{prefix}{code6}"
    try:
        dt = datetime.strptime(trade_date_ymd, "%Y%m%d")
        # start 往前 20 天（覆盖周末+节假日+数据 feed 延迟）
        start = (dt - timedelta(days=20)).strftime("%Y%m%d")
        end = trade_date_ymd

        def _src1():
            df = ak.stock_zh_a_daily(symbol=symbol, start_date=start, end_date=end, adjust="qfq")
            if df is None or len(df) == 0:
                raise ValueError(f"新浪 {symbol} 返回空")
            c_date = _find_col(df.columns, zh=("date", "日期"), en=("date",), position_hint=0)
            c_turn = _find_col(df.columns, zh=("换手率", "换手"), en=("turnover", "turnoverrate"), position_hint=None)
            if c_date is None or c_turn is None:
                raise ValueError(f"新浪 {symbol} 缺列，cols={list(df.columns)}")
            # 取最新日期行
            df2 = df.dropna(subset=[c_turn]).sort_values(c_date, ascending=True)
            if len(df2) == 0:
                raise ValueError(f"新浪 {symbol} turnover 全 NaN")
            raw = df2.iloc[-1][c_turn]
            return _extract_percent_from_turnover_value(raw)

        return _retry(_src1, max_attempts=3, base_sleep_s=0.8, tag=f"turn_sina_qfq[{symbol}]")
    except Exception as e:
        logger.debug(f"[watchlist_quotes] 补换手率 S1(qfq) {symbol} 最终失败: {type(e).__name__}: {e}")

    # —— 2) 新浪 stock_zh_a_daily，不复权 adjust="" ——
    try:
        def _src2():
            df = ak.stock_zh_a_daily(symbol=symbol, start_date=start, end_date=end, adjust="")
            if df is None or len(df) == 0:
                raise ValueError(f"新浪 {symbol} no_qfq 返回空")
            c_date = _find_col(df.columns, zh=("date", "日期"), en=("date",), position_hint=0)
            c_turn = _find_col(df.columns, zh=("换手率", "换手"), en=("turnover", "turnoverrate"), position_hint=None)
            if c_date is None or c_turn is None:
                raise ValueError(f"新浪 {symbol} no_qfq 缺列 cols={list(df.columns)}")
            df2 = df.dropna(subset=[c_turn]).sort_values(c_date, ascending=True)
            if len(df2) == 0:
                raise ValueError(f"新浪 {symbol} no_qfq turnover 全 NaN")
            raw = df2.iloc[-1][c_turn]
            return _extract_percent_from_turnover_value(raw)

        return _retry(_src2, max_attempts=3, base_sleep_s=0.8, tag=f"turn_sina_none[{symbol}]")
    except Exception as e:
        logger.debug(f"[watchlist_quotes] 补换手率 S2(no_qfq) {symbol} 最终失败: {type(e).__name__}: {e}")

    # —— 3) 东财 stock_individual_info_em（重试）——
    try:
        def _src3():
            df_info = ak.stock_individual_info_em(symbol=code6)
            if df_info is None or len(df_info) == 0:
                raise ValueError(f"东财个股信息 {code6} 返回空")
            cols = list(df_info.columns)
            c_item = _find_col(cols, zh=("item", "项目", "指标"), en=("item", "key"), position_hint=0)
            c_val = _find_col(cols, zh=("value", "数值"), en=("value",), position_hint=1)
            if c_item is None or c_val is None:
                raise ValueError(f"东财个股信息 {code6} 列异常 {cols}")
            for _, row in df_info.iterrows():
                item_s = str(row.get(c_item) or "")
                if "换手" in item_s or "turnover" in item_s.lower():
                    val = _safe_float(row.get(c_val))
                    if val is not None:
                        return _extract_percent_from_turnover_value(val)
            raise ValueError(f"东财个股信息 {code6} 没找到换手率行")

        return _retry(_src3, max_attempts=3, base_sleep_s=1.0, tag=f"turn_em_info[{code6}]")
    except Exception as e:
        logger.debug(f"[watchlist_quotes] 补换手率 S3(东财个股信息) {code6} 最终失败: {type(e).__name__}: {e}")

    # —— 4) 东财 stock_zh_a_hist（重试）——
    try:
        def _src4():
            df_hist = ak.stock_zh_a_hist(
                symbol=code6,
                period="daily",
                start_date=start,
                end_date=trade_date_ymd,
                adjust="qfq",
            )
            if df_hist is None or len(df_hist) == 0:
                raise ValueError(f"东财 hist {code6} 返回空")
            c_date = _find_col(df_hist.columns, zh=("日期",), en=("date",), position_hint=0)
            c_turn = _find_col(
                df_hist.columns,
                zh=("换手率", "换手"),
                en=("turnoverrate", "turnover"),
                position_hint=None,
            )
            if c_date is None or c_turn is None:
                raise ValueError(f"东财 hist {code6} 缺列 cols={list(df_hist.columns)}")
            df2 = df_hist.dropna(subset=[c_turn]).sort_values(c_date, ascending=True)
            if len(df2) == 0:
                raise ValueError(f"东财 hist {code6} turnover 全 NaN")
            val = _safe_float(df2.iloc[-1][c_turn])
            return _extract_percent_from_turnover_value(val)

        return _retry(_src4, max_attempts=3, base_sleep_s=1.0, tag=f"turn_em_hist[{code6}]")
    except Exception as e:
        logger.debug(f"[watchlist_quotes] 补换手率 S4(东财 hist) {code6} 最终失败: {type(e).__name__}: {e}")

    return None


def _fill_turnover_batch(matched: Dict[str, QuoteItem], trade_date: str, *, max_workers: int = 8) -> None:
    """原地把 matched 里 turnover_rate 是 None 的通过单票接口补齐。
    线程池并发加速，总超时 120s；阶段4一般已经把 turnover_rate 填满，这里是兜底。
    """
    need = [code for code, q in matched.items() if q.get("turnover_rate") is None]
    if not need:
        return
    trade_date_ymd = trade_date.replace("-", "")  # YYYYMMDD
    logger.info(f"[watchlist_quotes] 阶段3：单票补换手率 {len(need)} 只（workers={max_workers}）")
    ok = 0
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="turn_fill") as pool:
        future_map = {pool.submit(_fill_turnover_one, code, trade_date_ymd): code for code in need}
        try:
            for fut in as_completed(future_map, timeout=120):
                code = future_map[fut]
                try:
                    val = fut.result(timeout=8)
                except Exception:
                    val = None
                if val is not None:
                    matched[code]["turnover_rate"] = _safe_float(val)
                    ok += 1
        except TimeoutError:
            logger.warning("[watchlist_quotes] 阶段3：补换手率整体超时，未完成的票保持 None（安全不触发）")
    logger.info(f"[watchlist_quotes] 阶段3 完成：补齐 {ok}/{len(need)}")


# ========== 数据源 4：终极兜底（新浪单票 stock_zh_a_daily 聚合）—— 批量源全挂时用 ==========
def _fetch_one_sina_daily(code6: str, trade_date_ymd: str) -> Optional[QuoteItem]:
    """对单只票调新浪 stock_zh_a_daily，取最近 2 行，算出 price / pct_chg / turnover_rate / volume / amount。
    失败（重试 3 次）返回 None。

    返回的 QuoteItem:
      code（6位）、price（最新收盘价 float）、pct_chg（百分比,如 2.11 表示 2.11%）、
      turnover_rate（百分比数字）、volume、amount。
      name: 这里不填，由外层 merge 时从 watchlist 拿。
    """
    import akshare as ak

    prefix = _code_to_sina_sh_sz_bj_prefix(code6)
    symbol = f"{prefix}{code6}"
    dt = datetime.strptime(trade_date_ymd, "%Y%m%d")
    start = (dt - timedelta(days=25)).strftime("%Y%m%d")
    end = trade_date_ymd

    def _call(adj: str) -> QuoteItem:
        df = ak.stock_zh_a_daily(symbol=symbol, start_date=start, end_date=end, adjust=adj)
        if df is None or len(df) < 1:
            raise ValueError(f"{symbol}[{adj}] 无数据")
        c_date = _find_col(df.columns, zh=("date", "日期"), en=("date",), position_hint=0)
        c_close = _find_col(df.columns, zh=("close", "收盘"), en=("close",), position_hint=4)
        c_vol = _find_col(df.columns, zh=("volume", "成交量"), en=("volume",), position_hint=5)
        c_amt = _find_col(df.columns, zh=("amount", "成交额"), en=("amount",), position_hint=6)
        c_turn = _find_col(df.columns, zh=("换手率", "换手"), en=("turnover", "turnoverrate"), position_hint=None)
        if c_date is None or c_close is None:
            raise ValueError(f"{symbol}[{adj}] 缺必要列 cols={list(df.columns)}")
        df2 = df.dropna(subset=[c_close]).sort_values(c_date, ascending=True)
        if len(df2) < 1:
            raise ValueError(f"{symbol}[{adj}] close 全 NaN")
        last = df2.iloc[-1]
        price = _safe_float(last[c_close])
        if price is None:
            raise ValueError(f"{symbol}[{adj}] last close None")

        # pct_chg：若有昨收行则算；否则只给 price，pct_chg 留 None
        pct_chg: Optional[float] = None
        if len(df2) >= 2:
            prev = _safe_float(df2.iloc[-2][c_close])
            if prev is not None and abs(prev) > 1e-12:
                pct_chg = (price - prev) / prev * 100.0

        turnover_rate: Optional[float] = None
        if c_turn is not None:
            raw = _safe_float(last.get(c_turn))
            if raw is not None:
                turnover_rate = _extract_percent_from_turnover_value(raw)

        volume = _safe_float(last.get(c_vol)) if c_vol is not None else None
        amount = _safe_float(last.get(c_amt)) if c_amt is not None else None
        return _make_quote(
            code=code6,
            price=price,
            pct_chg=pct_chg,
            turnover_rate=turnover_rate,
            volume=volume,
            amount=amount,
        )

    # 先 qfq，失败再 no adjust
    try:
        return _retry(lambda: _call("qfq"), max_attempts=3, base_sleep_s=0.8, tag=f"sina_daily_qfq[{symbol}]")
    except Exception as e:
        logger.debug(f"[watchlist_quotes][stage4] {symbol}[qfq] 终败: {type(e).__name__}: {e}")
    try:
        return _retry(lambda: _call(""), max_attempts=3, base_sleep_s=0.8, tag=f"sina_daily_none[{symbol}]")
    except Exception as e:
        logger.debug(f"[watchlist_quotes][stage4] {symbol}[none] 终败: {type(e).__name__}: {e}")
    return None


def _fetch_sina_individual_aggregate(code_set: set, trade_date_ymd: str, *, max_workers: int = 8) -> Dict[str, QuoteItem]:
    """阶段4：新浪单票并行聚合；返回 {6位code: QuoteItem}。完全绕开批量接口，保证三字段齐全。"""
    result: Dict[str, QuoteItem] = {}
    codes = sorted(code_set)
    logger.info(f"[watchlist_quotes] 阶段4（终极兜底）：新浪单票 stock_zh_a_daily 聚合 {len(codes)} 只（workers={max_workers}）")
    ok = 0
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="sina_daily") as pool:
        future_map = {pool.submit(_fetch_one_sina_daily, code, trade_date_ymd): code for code in codes}
        try:
            for fut in as_completed(future_map, timeout=180):
                code = future_map[fut]
                try:
                    q = fut.result(timeout=8)
                except Exception:
                    q = None
                if q is not None:
                    result[code] = q
                    ok += 1
        except TimeoutError:
            logger.warning("[watchlist_quotes] 阶段4 整体超时，未完成的票保持缺失")
    logger.info(f"[watchlist_quotes] 阶段4 完成：聚合 {ok}/{len(codes)} 只")
    return result


# ========== 对外统一 fetch 接口 ==========
def fetch(trade_date: str) -> Dict:
    """拉取自选股当日行情（阶段 2.3 异动筛选的数据源）。

    Returns:
        {"trade_date": ..., "total": N, "watch_count": M, "quotes": [...]}
    """
    # ① 读 watchlist 表；如果是空的，直接返回空（不算失败）
    watch_items = watchlist_svc.list_watchlist()
    watch_count = len(watch_items)
    if watch_count == 0:
        return {"trade_date": trade_date, "total": 0, "watch_count": 0, "quotes": []}

    code_set: set = {_normalize_code(it.stock_code) for it in watch_items}
    code_to_item: Dict[str, object] = {}
    for it in watch_items:
        nc = _normalize_code(it.stock_code)
        if nc:
            code_to_item[nc] = it

    matched: Dict[str, QuoteItem] = {}
    last_err: Optional[Exception] = None

    # ② 阶段1：东财主源
    try:
        logger.info("[watchlist_quotes] 阶段1（主）：东财 stock_zh_a_spot_em")
        df_em = _fetch_em()
        em_map = _parse_em(df_em, code_set)
        matched.update(em_map)
        logger.info(f"[watchlist_quotes] 阶段1：东财匹配到 {len(em_map)}/{watch_count} 只")
    except Exception as e:
        last_err = e
        logger.warning(f"[watchlist_quotes] 阶段1 东财失败：{type(e).__name__}: {str(e)[:200]}")

    # ③ 阶段2：新浪回退
    missing_codes = code_set - set(matched.keys())
    missing_fields = any(q.get("price") is None or q.get("pct_chg") is None for q in matched.values())
    if (not matched or missing_codes or missing_fields) and True:
        try:
            logger.info(f"[watchlist_quotes] 阶段2（回退）：新浪 stock_zh_a_spot（填补 {len(missing_codes)} 缺失 + 字段补全）")
            df_sina = _fetch_sina()
            sina_map = _parse_sina(df_sina, code_set)
            for code, sq in sina_map.items():
                ex = matched.get(code)
                if ex is None:
                    matched[code] = sq
                else:
                    for k, v in sq.items():
                        if ex.get(k) is None and v is not None:
                            ex[k] = v
            logger.info(f"[watchlist_quotes] 阶段2：新浪贡献 {len(sina_map)} 只，当前总匹配 {len(matched)}/{watch_count}")
        except Exception as e2:
            if last_err is None:
                last_err = e2
            logger.warning(f"[watchlist_quotes] 阶段2 新浪也失败：{type(e2).__name__}: {str(e2)[:200]}")

    # ④ 阶段4（关键新增）：若批量源匹配率 < 80% 或 price/pct 仍有空字段 → 触发「新浪单票聚合终极兜底」
    watch_codes = sorted(code_set)
    matched_count = len(set(matched.keys()) & code_set)
    matched_rate = (matched_count / watch_count) if watch_count > 0 else 0.0
    still_missing_fields = any(
        (matched.get(c, {}).get("price") is None or matched.get(c, {}).get("pct_chg") is None)
        for c in watch_codes
    )
    trigger_stage4 = (watch_count > 0) and (matched_rate < 0.8 or still_missing_fields)
    if trigger_stage4:
        logger.info(
            f"[watchlist_quotes] 触发阶段4（终极兜底）：matched={matched_count}/{watch_count} rate={matched_rate*100:.0f}% "
            f"still_missing_fields={still_missing_fields}，用新浪 stock_zh_a_daily 逐票补全"
        )
        try:
            trade_date_ymd = trade_date.replace("-", "")
            agg_map = _fetch_sina_individual_aggregate(code_set, trade_date_ymd, max_workers=8)
            for code, aq in agg_map.items():
                ex = matched.get(code)
                if ex is None:
                    matched[code] = aq
                else:
                    for k, v in aq.items():
                        if ex.get(k) is None and v is not None:
                            ex[k] = v
            logger.info(f"[watchlist_quotes] 阶段4 后总匹配：{len(matched)}/{watch_count}")
        except Exception as e4:
            logger.error(f"[watchlist_quotes] 阶段4 执行出错: {type(e4).__name__}: {e4}")
            if last_err is None:
                last_err = e4

    # ⑤ 阶段3：单票补换手率（对 matched 里 turnover_rate 仍是 None 的再兜底一次，用 4 源优先级重试，一般阶段4已经填满，这里保险）
    _fill_turnover_batch(matched, trade_date, max_workers=8)

    # ⑥ 批量源 + 终极兜底都完全失败 且 0 匹配 → 抛异常让外层存档 status=failed
    if not matched and last_err is not None:
        raise RuntimeError(
            f"自选股行情两个批量源 + 新浪单票终极兜底均失败，未匹配任何票：最后错误 {last_err}"
        ) from last_err

    # ⑦ 兜底补全 name：行情返回没 name 的，用 watchlist 里存的 name（绝不造名字）
    for code, q in matched.items():
        if not q.get("name"):
            it = code_to_item.get(code)
            if it is not None:
                q["name"] = getattr(it, "stock_name", None)

    # ⑧ 去重并输出 list（按 code 排序，便于稳定对比）
    dedup: List[QuoteItem] = [matched[c] for c in sorted(matched.keys()) if c in code_set]

    return {
        "trade_date": trade_date,
        "total": len(dedup),
        "watch_count": watch_count,
        "quotes": dedup,
    }


if __name__ == "__main__":
    # 本地调试小脚本：cd backend; $env:PYTHONPATH="."; python data_sources/watchlist_quotes.py
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    today = datetime.now().strftime("%Y-%m-%d")
    import json
    result = fetch(today)
    print(f"\ntrade_date={result['trade_date']} total={result['total']} watch_count={result['watch_count']}")
    for q in result["quotes"]:
        print(" ", json.dumps(q, ensure_ascii=False))

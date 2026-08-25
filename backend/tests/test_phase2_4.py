# -*- coding: utf-8 -*-
"""
阶段 2.4 龙虎榜自测脚本（军规5：纯本地，不触外网，用临时 SQLite，不走 HTTP）。

直接调 main.py 的路由函数 + 直接调 dragon_tiger 模块的工具函数，
验证：
1. 工具函数：_safe_float / _safe_str / _find_col
2. _parse_detail：mock DataFrame → 标准化解析
3. /api/dragon-tiger 接口 4 种分支：
   - 无任何存档 → {empty: true}
   - 模块 status=ok → 返回 stocks
   - 模块 status=failed → empty + error
   - 模块未归档 → empty + error
   - 模块为空 dict → empty + error
   - 指定日期参数 + 历史回看

不依赖网络与真实 akshare；不污染用户数据。
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ========== 工具：mock 临时 SQLite 数据库 ==========
def make_temp_db_with_dragon_tiger(
    *,
    status: str = "ok",
    data: dict | None = None,
    trade_date: str | None = None,
    include_other_modules: bool = True,
    error_msg: str | None = None,
) -> tuple[str, str]:
    """创建临时 SQLite，按需写入 dragon_tiger 快照。

    Args:
        status: snapshots 表 status 字段；'ok' / 'failed' / 'absent'（不写模块）
        data: 模块 data_json 内容；None 时按 status 决定
        trade_date: YYYY-MM-DD；默认用今天
        include_other_modules: 是否同时写入其他模块的占位快照（用来测试「模块未归档」分支要存在 snap 但缺 dragon_tiger）
    """
    import datetime as _dt

    tmp = tempfile.NamedTemporaryFile(prefix="lhb_phase2_", suffix=".db", delete=False)
    tmp.close()
    os.environ["STOCK_DB_PATH"] = tmp.name

    conn = sqlite3.connect(tmp.name)
    c = conn.cursor()

    c.execute(
        """CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT NOT NULL,
            module_name TEXT NOT NULL,
            data_json TEXT NOT NULL,
            status TEXT DEFAULT 'ok',
            error_msg TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            UNIQUE(trade_date, module_name)
        )"""
    )

    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = trade_date or _dt.date.today().strftime("%Y-%m-%d")

    # 必要：先写一个占位 ok 模块，让 get_latest_snapshot() 能找到 trade_date
    if include_other_modules:
        c.execute(
            """INSERT OR REPLACE INTO snapshots(trade_date, module_name, data_json, status, error_msg, created_at)
               VALUES (?,?,?,?,?,?)""",
            (today, "indices", json.dumps({"indices": []}, ensure_ascii=False), "ok", None, now),
        )

    # 写 dragon_tiger 模块
    if status == "absent":
        # 不写 dragon_tiger，模拟「模块未归档」
        pass
    else:
        if data is None:
            if status == "ok":
                data = _MOCK_DRAGON_TIGER_OK_DATA
            elif status == "failed":
                data = {"error": "龙虎榜主榜单返回空"}
            elif status == "empty_dict":
                data = {}  # 空 dict（前端 interface 不应该出现这种）
            else:
                raise ValueError(f"unknown status: {status}")

        c.execute(
            """INSERT OR REPLACE INTO snapshots(trade_date, module_name, data_json, status, error_msg, created_at)
               VALUES (?,?,?,?,?,?)""",
            (
                today,
                "dragon_tiger",
                json.dumps(data, ensure_ascii=False),
                status if status != "empty_dict" else "ok",
                error_msg,
                now,
            ),
        )

    conn.commit()
    conn.close()
    return tmp.name, today


# ========== mock 数据 ==========
_MOCK_DRAGON_TIGER_OK_DATA = {
    "trade_date": "2026-08-25",
    "total": 3,
    "stocks": [
        {
            "code": "600519",
            "name": "贵州茅台",
            "close": 1700.50,
            "pct_chg": 5.21,
            "net_buy": 12345678.90,
            "buy_amount": 23456789.00,
            "sell_amount": 11111110.10,
            "total_amount": 34567899.10,
            "market_total_amount": 987654321.00,
            "net_buy_pct": 1.25,
            "amount_pct": 3.50,
            "turnover_rate": 4.21,
            "circ_mv": 1880000000000.00,
            "reason": "日涨幅偏离值达7%的证券",
            "interpretation": "机构席位买入净额较大",
            "seats": {
                "buy": [
                    {"name": "机构专用", "buy_amount": 5025114.99, "buy_pct": 0.028807, "sell_pct": None, "net": 5025114.99},
                    {"name": "国泰君安证券股份有限公司总部", "buy_amount": 3435790.02, "buy_pct": 0.019696, "sell_pct": None, "net": 3435790.02},
                ],
                "sell": [
                    {"name": "中银国际证券有限责任公司武汉黄孝河路证券营业部", "buy_amount": None, "buy_pct": None, "sell_pct": 0.020000, "net": -2000000.00},
                ],
            },
        },
        {
            "code": "000001",
            "name": "平安银行",
            "close": 12.00,
            "pct_chg": -3.50,
            "net_buy": -5000000.00,
            "buy_amount": 8000000.00,
            "sell_amount": 13000000.00,
            "total_amount": 21000000.00,
            "market_total_amount": 1000000000.00,
            "net_buy_pct": -0.50,
            "amount_pct": 2.10,
            "turnover_rate": 2.50,
            "circ_mv": 230000000000.00,
            "reason": "日跌幅偏离值达7%的证券",
            "interpretation": "",
            "seats": None,  # 测试席位拉取失败的兜底显示
        },
        {
            "code": "300750",
            "name": "宁德时代",
            "close": 220.00,
            "pct_chg": 1.20,
            "net_buy": 0.00,
            "buy_amount": 5000000.00,
            "sell_amount": 5000000.00,
            "total_amount": 10000000.00,
            "market_total_amount": 500000000.00,
            "net_buy_pct": 0.0,
            "amount_pct": 2.00,
            "turnover_rate": 1.50,
            "circ_mv": 950000000000.00,
            "reason": "日换手率达20%的证券",
            "interpretation": "",
            "seats": {"buy": [], "sell": []},  # 空席位
        },
    ],
}


# ========== 测试主入口 ==========
def run() -> int:
    failed = 0
    passed = 0

    def check(name: str, cond, detail: str = ""):
        nonlocal failed, passed
        if cond:
            passed += 1
            print(f"  [OK] {name}")
        else:
            failed += 1
            print(f"  [FAIL] {name}  {detail}")

    # =========================================================
    # Part A：工具函数测试
    # =========================================================
    print("\n========== Part A. 工具函数测试 ==========")
    from data_sources import dragon_tiger as dt

    print("\n-- A1. _safe_float --")
    check("None → None", dt._safe_float(None) is None)
    check("空串 → None", dt._safe_float("") is None)
    check("占位 '-' → None", dt._safe_float("-") is None)
    check("占位 '--' → None", dt._safe_float("--") is None)
    check("字符串数字 → float", dt._safe_float("12.5") == 12.5)
    check("负数字符串 → float", dt._safe_float("-3.14") == -3.14)
    check("数字 → float", dt._safe_float(42) == 42.0)
    check("NaN → None", dt._safe_float(float("nan")) is None)
    check("inf → None", dt._safe_float(float("inf")) is None)
    check("非数字串 → None", dt._safe_float("abc") is None)
    check("0 → 0.0", dt._safe_float(0) == 0.0)

    print("\n-- A2. _safe_str --")
    check("None → ''", dt._safe_str(None) == "")
    check("数字 → str", dt._safe_str(123) == "123")
    check("字符串 → trim", dt._safe_str("  abc  ") == "abc")
    check("NaN → ''", dt._safe_str(float("nan")) == "")
    check("'nan' → ''", dt._safe_str("nan") == "")
    check("'NULL' → ''", dt._safe_str("NULL") == "")
    check("正常串 → 不变", dt._safe_str("贵州茅台") == "贵州茅台")

    print("\n-- A3. _find_col --")
    cols = ["序号", "代码", "名称", "收盘价", "涨跌幅", "龙虎榜净买额", "上榜原因"]
    check("精确匹配", dt._find_col(cols, zh=("代码",)) == "代码")
    check("英文子串", dt._find_col(cols, zh=("代码",), en=("code",)) == "代码")
    check("中文子串", dt._find_col(cols, zh=("净买",)) == "龙虎榜净买额")
    check("找不到 → None", dt._find_col(cols, zh=("不存在的列",)) is None)
    check("空列表 → None", dt._find_col([], zh=("代码",)) is None)
    # 测试 akshare 实际可能输出的不同列名变体
    cols2 = ["symbol", "name", "close", "pct_chg", "net_buy", "buy_amount"]
    check("英文精确", dt._find_col(cols2, zh=("代码",), en=("code",)) is None)  # 没有 code 但有 symbol
    check("英文子串兜底", dt._find_col(cols2, zh=("代码",), en=("symbol",)) == "symbol")

    # =========================================================
    # Part B：_parse_detail 测试（mock DataFrame）
    # =========================================================
    print("\n========== Part B. _parse_detail 解析测试 ==========")
    import pandas as pd

    print("\n-- B1. 标准 21 列 DataFrame 解析 --")
    df = pd.DataFrame([
        {
            "序号": 1,
            "代码": "600519",
            "名称": "贵州茅台",
            "上榜日": "2026-08-25",
            "解读": "机构席位买入",
            "收盘价": 1700.50,
            "涨跌幅": 5.21,
            "龙虎榜净买额": 12345678.90,
            "龙虎榜买入额": 23456789.00,
            "龙虎榜卖出额": 11111110.10,
            "龙虎榜成交额": 34567899.10,
            "市场总成交额": 987654321.00,
            "净买额占总成交比": 1.25,
            "成交额占总成交比": 3.50,
            "换手率": 4.21,
            "流通市值": 1880000000000.00,
            "上榜原因": "日涨幅偏离值达7%的证券",
            "上榜后1日": -1.30,
            "上榜后2日": -0.19,
            "上榜后5日": -8.21,
            "上榜后10日": 1.88,
        },
        {
            "序号": 2,
            "代码": "000001",
            "名称": "平安银行",
            "上榜日": "2026-08-25",
            "解读": "",
            "收盘价": 12.00,
            "涨跌幅": -3.50,
            "龙虎榜净买额": -5000000.00,
            "龙虎榜买入额": 8000000.00,
            "龙虎榜卖出额": 13000000.00,
            "龙虎榜成交额": 21000000.00,
            "市场总成交额": 1000000000.00,
            "净买额占总成交比": -0.50,
            "成交额占总成交比": 2.10,
            "换手率": 2.50,
            "流通市值": 230000000000.00,
            "上榜原因": "日跌幅偏离值达7%的证券",
            "上榜后1日": None,
            "上榜后2日": None,
            "上榜后5日": None,
            "上榜后10日": None,
        },
    ])
    stocks = dt._parse_detail(df)
    check("解析出 2 只票", len(stocks) == 2, f"actual={len(stocks)}")
    if len(stocks) >= 2:
        s1 = stocks[0]
        check("code=600519", s1["code"] == "600519")
        check("name=贵州茅台", s1["name"] == "贵州茅台")
        check("close=1700.50", abs(s1["close"] - 1700.50) < 1e-6)
        check("pct_chg=5.21", abs(s1["pct_chg"] - 5.21) < 1e-6)
        check("net_buy=12345678.90", abs(s1["net_buy"] - 12345678.90) < 1e-6)
        check("buy_amount=23456789.00", abs(s1["buy_amount"] - 23456789.00) < 1e-6)
        check("sell_amount=11111110.10", abs(s1["sell_amount"] - 11111110.10) < 1e-6)
        check("turnover_rate=4.21", abs(s1["turnover_rate"] - 4.21) < 1e-6)
        check("reason=日涨幅偏离值达7%的证券", s1["reason"] == "日涨幅偏离值达7%的证券")
        check("interpretation=机构席位买入", s1["interpretation"] == "机构席位买入")
        check("seats 初始 None", s1["seats"] is None)

        s2 = stocks[1]
        check("第2只 code=000001", s2["code"] == "000001")
        check("第2只 net_buy=-5000000.00", abs(s2["net_buy"] - (-5000000.00)) < 1e-6)
        check("第2只 interpretation=空串", s2["interpretation"] == "")

    print("\n-- B2. 缺少「代码」列 → 抛 ValueError --")
    df_no_code = pd.DataFrame([{"名称": "测试", "收盘价": 10.0}])
    try:
        dt._parse_detail(df_no_code)
        check("缺代码列应抛错", False, "未抛异常")
    except ValueError as e:
        check("缺代码列抛 ValueError", "代码" in str(e) or "columns" in str(e))

    print("\n-- B3. 空行 + 部分字段为 None/NaN --")
    df_partial = pd.DataFrame([
        {"代码": "600519", "名称": "贵州茅台", "收盘价": None, "涨跌幅": float("nan"), "龙虎榜净买额": "-"},
    ])
    stocks2 = dt._parse_detail(df_partial)
    check("部分缺失 → 1 行", len(stocks2) == 1)
    if stocks2:
        check("close 缺失 → None", stocks2[0]["close"] is None)
        check("pct_chg NaN → None", stocks2[0]["pct_chg"] is None)
        check("net_buy 占位 → None", stocks2[0]["net_buy"] is None)
        check("name 仍正确", stocks2[0]["name"] == "贵州茅台")

    print("\n-- B4. 空代码行被过滤 --")
    df_empty_code = pd.DataFrame([
        {"代码": "", "名称": "无名", "收盘价": 10.0},
        {"代码": None, "名称": "无名2", "收盘价": 20.0},
        {"代码": "600519", "名称": "贵州茅台", "收盘价": 1700.0},
    ])
    stocks3 = dt._parse_detail(df_empty_code)
    check("空代码行被过滤 → 1 行", len(stocks3) == 1, f"actual={len(stocks3)}")

    # =========================================================
    # Part C：/api/dragon-tiger 接口路由测试（用临时 DB）
    # =========================================================
    print("\n========== Part C. /api/dragon-tiger 路由测试 ==========")
    import importlib

    # C1. 无任何存档 → {empty: true}
    print("\n-- C1. 无任何存档 → {empty: true} --")
    tmp1 = tempfile.NamedTemporaryFile(prefix="lhb_empty_", suffix=".db", delete=False)
    tmp1.close()
    os.environ["STOCK_DB_PATH"] = tmp1.name
    # 只 init 表结构，不写任何数据
    conn1 = sqlite3.connect(tmp1.name)
    conn1.execute(
        """CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT NOT NULL,
            module_name TEXT NOT NULL,
            data_json TEXT NOT NULL,
            status TEXT DEFAULT 'ok',
            error_msg TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            UNIQUE(trade_date, module_name)
        )"""
    )
    conn1.commit()
    conn1.close()
    import config as _cfg
    importlib.reload(_cfg)
    import db as _db
    importlib.reload(_db)
    _db.init_db()
    import snapshot as _snap
    importlib.reload(_snap)
    import main as _main
    importlib.reload(_main)

    res_c1 = _main.api_dragon_tiger(None)
    check("无存档 → empty=true", res_c1.get("empty") is True, f"actual={res_c1}")
    check("无存档 → 无 trade_date", "trade_date" not in res_c1)

    # 清掉临时文件
    Path(tmp1.name).unlink(missing_ok=True)

    # C2. 模块 status=ok → 返回 stocks
    print("\n-- C2. 模块 status=ok → 返回 stocks --")
    db2, today2 = make_temp_db_with_dragon_tiger(status="ok")
    importlib.reload(_cfg)
    importlib.reload(_db)
    importlib.reload(_snap)
    importlib.reload(_main)

    res_c2 = _main.api_dragon_tiger(None)
    check("ok → empty=false", res_c2.get("empty") is not True, f"actual={res_c2}")
    check("ok → trade_date", res_c2.get("trade_date") == today2, f"actual={res_c2.get('trade_date')}")
    check("ok → total=3", res_c2.get("total") == 3, f"actual={res_c2.get('total')}")
    check("ok → stocks 长度=3", len(res_c2.get("stocks", [])) == 3, f"actual={len(res_c2.get('stocks', []))}")
    if len(res_c2.get("stocks", [])) >= 1:
        first = res_c2["stocks"][0]
        check("ok → 第1只 code", first.get("code") == "600519")
        check("ok → 第1只 name", first.get("name") == "贵州茅台")
        check("ok → 第1只 net_buy", abs((first.get("net_buy") or 0) - 12345678.90) < 1e-6)
        check("ok → 第1只 seats 非空", first.get("seats") is not None)
        if first.get("seats"):
            check("ok → 第1只 buy seats 2 个", len(first["seats"].get("buy", [])) == 2)
            check("ok → 第1只 sell seats 1 个", len(first["seats"].get("sell", [])) == 1)

        # 验证排序：净买入降序
        codes_in_order = [s["code"] for s in res_c2["stocks"]]
        check("ok → 净买额降序 600519 在前", codes_in_order[0] == "600519")

    Path(db2).unlink(missing_ok=True)

    # C3. 模块 status=failed → empty + error
    print("\n-- C3. 模块 status=failed → empty + error --")
    db3, today3 = make_temp_db_with_dragon_tiger(
        status="failed", data={"error": "龙虎榜主榜单返回空"}, error_msg="接口限流：RemoteDisconnected"
    )
    importlib.reload(_cfg)
    importlib.reload(_db)
    importlib.reload(_snap)
    importlib.reload(_main)

    res_c3 = _main.api_dragon_tiger(None)
    check("failed → empty=true", res_c3.get("empty") is True, f"actual={res_c3}")
    check("failed → 含 error", bool(res_c3.get("error")), f"actual={res_c3.get('error')}")
    check("failed → stocks 为空", res_c3.get("stocks") == [])
    check("failed → trade_date 仍在", res_c3.get("trade_date") == today3)

    Path(db3).unlink(missing_ok=True)

    # C4. 模块未归档（snap 有其他模块，但无 dragon_tiger）→ empty + error
    print("\n-- C4. 模块未归档 → empty + error（区分 '未归档' 与 '失败'） --")
    db4, today4 = make_temp_db_with_dragon_tiger(status="absent")
    importlib.reload(_cfg)
    importlib.reload(_db)
    importlib.reload(_snap)
    importlib.reload(_main)

    res_c4 = _main.api_dragon_tiger(None)
    check("未归档 → empty=true", res_c4.get("empty") is True, f"actual={res_c4}")
    check("未归档 → 含 error", bool(res_c4.get("error")), f"actual={res_c4.get('error')}")
    check("未归档 → error 文案含「未包含龙虎榜」", "未包含龙虎榜" in (res_c4.get("error") or ""))
    check("未归档 → trade_date 仍在", res_c4.get("trade_date") == today4)

    Path(db4).unlink(missing_ok=True)

    # C5. 模块为空 dict（akshare 返回空 DataFrame 但 status=ok 写了 {}）→ empty + error
    print("\n-- C5. 模块为空 dict → empty + error --")
    db5, today5 = make_temp_db_with_dragon_tiger(status="empty_dict", data={})
    importlib.reload(_cfg)
    importlib.reload(_db)
    importlib.reload(_snap)
    importlib.reload(_main)

    res_c5 = _main.api_dragon_tiger(None)
    check("空 dict → empty=true", res_c5.get("empty") is True, f"actual={res_c5}")
    check("空 dict → 含 error", bool(res_c5.get("error")), f"actual={res_c5.get('error')}")
    check("空 dict → error 文案含「为空」", "为空" in (res_c5.get("error") or ""))

    Path(db5).unlink(missing_ok=True)

    # C6. 指定日期参数（历史回看）→ 验证路由接收 trade_date 参数
    print("\n-- C6. 指定日期参数（历史回看） --")
    history_date = "2026-08-20"
    db6, _ = make_temp_db_with_dragon_tiger(status="ok", trade_date=history_date)
    importlib.reload(_cfg)
    importlib.reload(_db)
    importlib.reload(_snap)
    importlib.reload(_main)

    # 不传参数 → 默认取 latest（应该是 history_date 因为它是最大日期）
    res_c6a = _main.api_dragon_tiger(None)
    check("latest 取到 trade_date=history", res_c6a.get("trade_date") == history_date, f"actual={res_c6a.get('trade_date')}")

    # 显式传 history_date 参数 → 应取该日期
    res_c6b = _main.api_dragon_tiger(history_date)
    check("传日期参数 → trade_date", res_c6b.get("trade_date") == history_date)
    check("传日期参数 → total=3", res_c6b.get("total") == 3)

    # 传一个不存在的日期 → empty=true
    res_c6c = _main.api_dragon_tiger("2025-01-01")
    check("传不存在日期 → empty=true", res_c6c.get("empty") is True, f"actual={res_c6c}")
    # 注意：snapshot.get_snapshot_by_date 对不存在日期返回 None → api_dragon_tiger 返回 {"empty": True}

    Path(db6).unlink(missing_ok=True)

    # =========================================================
    # Part D：FETCHERS 注册 & config 模块登记
    # =========================================================
    print("\n========== Part D. 模块注册 ==========")
    print("\n-- D1. FETCHERS 注册 --")
    from data_sources import FETCHERS
    check("FETCHERS 含 dragon_tiger", "dragon_tiger" in FETCHERS)
    check("FETCHERS[dragon_tiger] 可调用", callable(FETCHERS.get("dragon_tiger")))

    print("\n-- D2. config.py 模块登记 --")
    import config as _cfg2
    check("MODULE_DRAGON_TIGER 定义", hasattr(_cfg2, "MODULE_DRAGON_TIGER"))
    check("MODULE_DRAGON_TIGER 值='dragon_tiger'", _cfg2.MODULE_DRAGON_TIGER == "dragon_tiger")
    check("ALL_MODULES 含 dragon_tiger", "dragon_tiger" in _cfg2.ALL_MODULES)
    check("ALL_MODULES 顺序：dragon_tiger 在 indices 之前",
          _cfg2.ALL_MODULES.index("dragon_tiger") < _cfg2.ALL_MODULES.index("indices"))

    # =========================================================
    # 汇总
    # =========================================================
    print("\n" + "=" * 60)
    print(f"汇总：通过 {passed} 项 / 失败 {failed} 项 / 共 {passed + failed} 项")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())

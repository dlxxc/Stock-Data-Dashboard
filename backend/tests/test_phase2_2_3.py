# -*- coding: utf-8 -*-
"""
阶段 2.2/2.3 联调自测脚本（军规5：纯本地，不触外网，用临时 SQLite，不走 HTTP）。
直接调 main.py 的路由函数，验证批量阈值更新 & 异动筛选分组逻辑。
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


def make_temp_db() -> tuple[str, str]:
    tmp = tempfile.NamedTemporaryFile(prefix="wl_phase2_", suffix=".db", delete=False)
    tmp.close()
    os.environ["STOCK_DB_PATH"] = tmp.name

    conn = sqlite3.connect(tmp.name)
    c = conn.cursor()

    # —— 和 db.py 表结构对齐（决策3：快照按模块分条） ——
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
    c.execute(
        """CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT NOT NULL UNIQUE,
            stock_name TEXT NOT NULL,
            gain_pct REAL NOT NULL DEFAULT 5.0,
            loss_pct REAL NOT NULL DEFAULT 5.0,
            turnover_pct REAL NOT NULL DEFAULT 10.0,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )"""
    )

    import datetime as _dt

    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = _dt.date.today().strftime("%Y-%m-%d")
    seed = [
        ("000001", "平安银行", 5.0, 5.0, 10.0),
        ("600519", "贵州茅台", 5.0, 5.0, 10.0),
        ("300750", "宁德时代", 5.0, 5.0, 10.0),
    ]
    for row in seed:
        c.execute(
            "INSERT INTO watchlist(stock_code,stock_name,gain_pct,loss_pct,turnover_pct,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            (row[0], row[1], row[2], row[3], row[4], now, now),
        )

    # —— 快照按模块分条写入（决策3）——
    mock_quotes = {
        "trade_date": today, "fetched_at": now,
        "module_meta": {"source": "em", "fallback_used": False, "raw_count": 3},
        "watch_count": 3, "total": 3,
        "quotes": [
            {
                "code": "000001", "name": "平安银行", "price": 12.0, "pct_chg": 6.5,
                "turnover_rate": 2.1, "volume": 1000000, "amount": 12000000,
            },
            {
                "code": "600519", "name": "贵州茅台", "price": 1700.0, "pct_chg": -5.8,
                "turnover_rate": 0.42, "volume": 200000, "amount": 340000000,
            },
            {
                "code": "300750", "name": "宁德时代", "price": 220.0, "pct_chg": 1.2,
                "turnover_rate": 15.3, "volume": 1500000, "amount": 330000000,
            },
        ],
    }

    # 只写 watchlist_quotes 模块一条；其他模块缺省是 None（api_watchlist_alerts 里兼容）
    c.execute(
        """INSERT OR REPLACE INTO snapshots(trade_date, module_name, data_json, status, error_msg, created_at)
           VALUES (?,?,?,?,?,?)""",
        (today, "watchlist_quotes", json.dumps(mock_quotes, ensure_ascii=False), "ok", None, now),
    )

    conn.commit()
    conn.close()
    return tmp.name, today


def run() -> int:
    db_path, today = make_temp_db()
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

    try:
        import importlib

        # 1) 先 import config，让 config.DB_PATH 读到刚刚设的 STOCK_DB_PATH 环境变量
        import config as _cfg

        importlib.reload(_cfg)
        import db as _db

        importlib.reload(_db)
        # init_db 不会破坏现有列，只是补全表结构
        _db.init_db()
        import watchlist as watchlist_svc

        importlib.reload(watchlist_svc)
        import snapshot as _snap

        importlib.reload(_snap)
        import main as _main

        importlib.reload(_main)
    except Exception as e:
        print(f"[FATAL] import 失败：{type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # 取 IDs
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, stock_code FROM watchlist ORDER BY id").fetchall()
    ids = [r["id"] for r in rows]
    id1, id2, id3 = ids
    check("自选股数量=3", len(ids) == 3, f"{len(ids)}")

    # 先验证快照系统 OK（决策3格式）
    snap = _snap.get_snapshot_by_date(today)
    check("快照读取成功（决策3分条）", snap is not None)
    if snap is not None:
        check("snap.modules.watchlist_quotes 存在", "watchlist_quotes" in (snap.get("modules") or {}))

    print("\n=== 1. api_batch_update_thresholds（路由函数直接调用）===")
    Req = _main.WatchlistBatchUpdateRequest

    # 1.1 不存在的 ID
    req = Req(ids=[99999], gain_pct=3.0)
    out = _main.api_batch_update_thresholds(req)
    check("不存在 id → updated=0, failed_ids=[99999]",
          out["updated"] == 0 and out["failed_ids"] == [99999],
          str(out))

    # 1.2 单票更新
    req = Req(ids=[id1], gain_pct=3.0)
    out = _main.api_batch_update_thresholds(req)
    check("id1 涨阈值 updated=1", out["updated"] == 1, str(out))
    check("id1 failed_ids=[]", out["failed_ids"] == [])

    req = Req(ids=[id2, id3], turnover_pct=8.0)
    out = _main.api_batch_update_thresholds(req)
    check("id2/id3 换手 updated=2", out["updated"] == 2, str(out))
    check("id2/id3 failed_ids=[]", out["failed_ids"] == [])

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rs = conn.execute(
            "SELECT id, gain_pct, loss_pct, turnover_pct FROM watchlist ORDER BY id"
        ).fetchall()
    check("id1: gain=3 loss=5 turnover=10",
          (rs[0]["gain_pct"], rs[0]["loss_pct"], rs[0]["turnover_pct"]) == (3.0, 5.0, 10.0),
          f"actual={(rs[0]['gain_pct'],rs[0]['loss_pct'],rs[0]['turnover_pct'])}")
    check("id2: gain=5 loss=5 turnover=8",
          (rs[1]["gain_pct"], rs[1]["loss_pct"], rs[1]["turnover_pct"]) == (5.0, 5.0, 8.0))
    check("id3: gain=5 loss=5 turnover=8",
          (rs[2]["gain_pct"], rs[2]["loss_pct"], rs[2]["turnover_pct"]) == (5.0, 5.0, 8.0))

    # 1.3 一键重置默认值
    req = Req(ids=[id1, id2, id3], reset_to_default=True)
    out = _main.api_batch_update_thresholds(req)
    check("3 票重置 updated=3", out["updated"] == 3, str(out))
    check("3 票重置 failed_ids=[]", out["failed_ids"] == [])
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rs = conn.execute(
            "SELECT id, gain_pct, loss_pct, turnover_pct FROM watchlist ORDER BY id"
        ).fetchall()
    for i, r in enumerate(rs):
        check(f"票{i+1} 重置后 5/5/10",
              (r["gain_pct"], r["loss_pct"], r["turnover_pct"]) == (5.0, 5.0, 10.0))

    # 1.4 混合 ids
    req = Req(ids=[id1, 99998, id2], gain_pct=4.0)
    out = _main.api_batch_update_thresholds(req)
    check("混合 updated=2", out["updated"] == 2)
    check("混合 failed_ids=[99998]", out["failed_ids"] == [99998], str(out))

    print("\n=== 2. api_watchlist_alerts 异动筛选 ===")

    # 2.1 默认阈值 3 只全部触发
    body = _main.api_watchlist_alerts(today)
    check("trade_date 正确", body["trade_date"] == today)
    check("watch_count=3", body["watch_count"] == 3, f"actual={body.get('watch_count')}")
    check("quote_count=3", body["quote_count"] == 3, f"actual={body.get('quote_count')}")
    check("empty=False", body["empty"] is False)
    check("total_triggered=3", body["total_triggered"] == 3, f"actual={body.get('total_triggered')}")
    check("items 长度=3", len(body["items"]) == 3)
    check("涨超组 count=1", body["groups"]["gain"]["count"] == 1)
    check("跌超组 count=1", body["groups"]["loss"]["count"] == 1)
    check("换手超组 count=1", body["groups"]["turnover"]["count"] == 1)

    gain_item = body["groups"]["gain"]["items"][0]
    loss_item = body["groups"]["loss"]["items"][0]
    turnover_item = body["groups"]["turnover"]["items"][0]
    check("涨超=000001 平安银行", gain_item["code"] == "000001" and gain_item["name"] == "平安银行")
    check("涨超 pct=6.5", abs(gain_item["pct_chg"] - 6.5) < 1e-6, f"{gain_item.get('pct_chg')}")
    check("涨超: G=T L=F T=F",
          gain_item["gain_triggered"] and not gain_item["loss_triggered"] and not gain_item["turnover_triggered"])
    check("跌超=600519 茅台", loss_item["code"] == "600519")
    check("跌超 pct=-5.8", abs(loss_item["pct_chg"] - (-5.8)) < 1e-6, f"{loss_item.get('pct_chg')}")
    check("换手超=300750 宁德", turnover_item["code"] == "300750")
    check("换手超=15.3", abs(turnover_item["turnover_rate"] - 15.3) < 1e-6, f"{turnover_item.get('turnover_rate')}")

    any_flags = [it["any_triggered"] for it in body["items"]]
    check("items 全触发", all(any_flags), str(any_flags))

    # 2.2 调 id3 换手阈值到 20% → 不触发
    req = Req(ids=[id3], turnover_pct=20.0)
    _main.api_batch_update_thresholds(req)
    body = _main.api_watchlist_alerts(today)
    check("换手阈值 20% → 总数=2", body["total_triggered"] == 2, f"actual={body.get('total_triggered')}")
    check("换手超组 count=0", body["groups"]["turnover"]["count"] == 0)

    # 2.3 旧日期(无快照)
    body = _main.api_watchlist_alerts("2000-01-01")
    check("旧日期 empty=True", body["empty"] is True)
    check("旧日期 total=0", body["total_triggered"] == 0)
    check("旧日期 watch_count=3", body["watch_count"] == 3)
    check("旧日期 quote_count=0", body["quote_count"] == 0)
    check("旧日期 error 为空", body.get("error") in (None, ""), f"error={body.get('error')}")

    # 2.4 快照有 day 记录，但 watchlist_quotes 模块不存在（其他模块都写了，wl 没写）
    with sqlite3.connect(db_path) as conn:
        now = "2026-01-01 00:00:00"
        conn.execute("DELETE FROM snapshots WHERE trade_date = ?", (today,))
        conn.execute(
            """INSERT OR REPLACE INTO snapshots(trade_date, module_name, data_json, status, error_msg, created_at)
               VALUES (?,?,?,?,?,?)""",
            (today, "indices", "{}", "ok", None, now),
        )
        conn.commit()
    body = _main.api_watchlist_alerts(today)
    check("缺 wl 模块 empty=True", body["empty"] is True)
    check("缺 wl 模块 total=0", body["total_triggered"] == 0)

    # 2.5 模块失败：status='failed' + error_msg 填充（决策3格式，存入 failed_modules）
    with sqlite3.connect(db_path) as conn:
        now = "2026-01-01 00:00:00"
        conn.execute("DELETE FROM snapshots WHERE trade_date = ?", (today,))
        # watchlist_quotes 模块：status=failed, error_msg 非空
        conn.execute(
            """INSERT OR REPLACE INTO snapshots(trade_date, module_name, data_json, status, error_msg, created_at)
               VALUES (?,?,?,?,?,?)""",
            (today, "watchlist_quotes", "{}", "failed", "Timeout: 东财+新浪都失败了", now),
        )
        conn.commit()
    body = _main.api_watchlist_alerts(today)
    check("模块失败 empty=True", body["empty"] is True)
    check("模块失败 error 非空", isinstance(body.get("error"), str) and len(body["error"]) > 0,
          f"error={body.get('error')}")

    # 2.6 恢复 watchlist_quotes OK 状态（后续 latest 验证用）
    with sqlite3.connect(db_path) as conn:
        import datetime as _dt
        now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("DELETE FROM snapshots WHERE trade_date = ?", (today,))
        quotes_data = {
            "trade_date": today, "fetched_at": now, "watch_count": 3, "total": 3,
            "quotes": [
                {"code": "000001", "name": "平安银行", "price": 12.0, "pct_chg": 6.5,
                 "turnover_rate": 2.1, "volume": 10, "amount": 120},
                {"code": "600519", "name": "贵州茅台", "price": 1700.0, "pct_chg": -5.8,
                 "turnover_rate": 0.4, "volume": 3, "amount": 5100},
                {"code": "300750", "name": "宁德时代", "price": 220.0, "pct_chg": 1.2,
                 "turnover_rate": 15.3, "volume": 5, "amount": 1100},
            ],
        }
        conn.execute(
            """INSERT OR REPLACE INTO snapshots(trade_date, module_name, data_json, status, error_msg, created_at)
               VALUES (?,?,?,?,?,?)""",
            (today, "watchlist_quotes", json.dumps(quotes_data, ensure_ascii=False), "ok", None, now),
        )
        conn.commit()

    # 2.7 无自选股
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM watchlist")
    body = _main.api_watchlist_alerts(today)
    check("无自选股 watch_count=0", body["watch_count"] == 0)
    check("无自选股 total=0", body["total_triggered"] == 0)
    check("无自选股 empty=True", body["empty"] is True)

    # 2.8 latest 快照（不传 date），同时恢复 1 只自选股
    with sqlite3.connect(db_path) as conn:
        import datetime as _dt
        now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO watchlist(stock_code,stock_name,gain_pct,loss_pct,turnover_pct,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            ("000001", "平安银行", 5.0, 5.0, 10.0, now, now),
        )
        conn.commit()
    body = _main.api_watchlist_alerts(None)
    check("latest date 取 today 快照 OK (total=1)",
          body["total_triggered"] == 1 and body["watch_count"] == 1,
          f"total={body.get('total_triggered')}, watch={body.get('watch_count')}")

    try:
        os.unlink(db_path)
    except Exception:
        pass

    print(f"\n======================")
    print(f"结果：passed={passed}  failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())

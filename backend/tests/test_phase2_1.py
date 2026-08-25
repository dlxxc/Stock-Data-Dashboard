"""阶段 2.1 自测脚本：自选股 CRUD

不依赖 httpx2。拆成两部分：
1. Part A：直接测 watchlist 数据层（list/add/delete/update + 20只上限 + 重复代码拒绝）
2. Part B：启动 uvicorn 进程，用 urllib 标准库调 REST API（GET/POST/PATCH/DELETE）

用法（backend 目录下）：
    uv run python tests/test_phase2_1.py
    或用 .venv 的 python
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))
os.chdir(BACKEND_ROOT)

# 临时 DB，避免污染真实数据
_TEMP_DB = PROJECT_ROOT / "data" / "_test_watchlist.db"
if _TEMP_DB.exists():
    _TEMP_DB.unlink()

import config  # noqa: E402

config.DB_PATH = _TEMP_DB  # 在 import db / watchlist 之前生效

import watchlist as svc  # noqa: E402
from config import (  # noqa: E402
    WATCHLIST_MAX_SIZE,
    WATCHLIST_DEFAULT_GAIN_PCT,
    WATCHLIST_DEFAULT_LOSS_PCT,
    WATCHLIST_DEFAULT_TURNOVER_PCT,
)
from db import init_db  # noqa: E402

assert WATCHLIST_MAX_SIZE == 100, "最大数量应为 100"
assert WATCHLIST_DEFAULT_GAIN_PCT == 5.0
assert WATCHLIST_DEFAULT_LOSS_PCT == 5.0
assert WATCHLIST_DEFAULT_TURNOVER_PCT == 10.0

passed = 0
failed = 0


def check(name: str, cond: bool, detail: str = ""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}  {detail}")


# =========================================================
# Part A：数据层
# =========================================================
def part_a_data_layer():
    print("\n========== Part A. 数据层测试 ==========")
    init_db()

    print("\n-- A1. 初始空表 --")
    check("list 空", svc.list_watchlist() == [])
    check("count 0", svc.count_watchlist() == 0)
    check("find_by_code None", svc.find_by_code("600519") is None)

    print("\n-- A2. 新增 + 默认阈值 --")
    it = svc.add_watch_item(stock_code="600519", stock_name="贵州茅台")
    check("id 分配", it.id > 0)
    check("code 正确", it.stock_code == "600519")
    check("name 正确", it.stock_name == "贵州茅台")
    check("gain 默认 5", it.gain_pct == 5.0, f"实际 {it.gain_pct}")
    check("loss 默认 5", it.loss_pct == 5.0)
    check("turnover 默认 10", it.turnover_pct == 10.0)
    check("count → 1", svc.count_watchlist() == 1)
    check("find_by_code 命中", svc.find_by_code("600519") is not None)
    check("find_by_id 命中", svc.find_by_id(it.id) is not None)

    print("\n-- A3. 新增（自定义阈值） --")
    it2 = svc.add_watch_item(
        stock_code="000001", stock_name="平安银行",
        gain_pct=3.0, loss_pct=7.0, turnover_pct=15.0,
    )
    check("gain=3", it2.gain_pct == 3.0)
    check("loss=7", it2.loss_pct == 7.0)
    check("turnover=15", it2.turnover_pct == 15.0)

    print("\n-- A4. 重复代码拒绝 --")
    err = None
    try:
        svc.add_watch_item(stock_code="600519", stock_name="重复")
    except ValueError as e:
        err = e
    check("ValueError raised", err is not None)
    check("错误消息含已在自选", err and "已在自选股中" in str(err))

    print("\n-- A5. 修改阈值（部分字段） --")
    upd = svc.update_thresholds(it2.id, gain_pct=4.0, turnover_pct=20.0)
    check("gain 3→4", upd.gain_pct == 4.0)
    check("loss 保持 7", upd.loss_pct == 7.0)
    check("turnover 15→20", upd.turnover_pct == 20.0)
    err2 = None
    try:
        svc.update_thresholds(99999, gain_pct=1)
    except ValueError as e:
        err2 = e
    check("无效 id 抛 ValueError", err2 is not None)

    print("\n-- A6. 删除 --")
    ok = svc.delete_watch_item(it2.id)
    check("delete True", ok)
    check("count → 1", svc.count_watchlist() == 1)
    check("find_by_id 返回 None", svc.find_by_id(it2.id) is None)
    check("重复删除 False", svc.delete_watch_item(it2.id) is False)

    print("\n-- A7. 100 只上限 --")
    for i in range(2, 101):
        svc.add_watch_item(
            stock_code=f"T{i:06d}", stock_name=f"股票{i}",
        )
    check("满 100 只", svc.count_watchlist() == 100)
    err3 = None
    try:
        svc.add_watch_item(stock_code="T999999", stock_name="超上限")
    except ValueError as e:
        err3 = e
    check("超上限抛 ValueError", err3 is not None and "上限 100 只" in str(err3))

    # 清理，仅保留 600519（后面 API 测试用）
    for i in range(2, 101):
        found = svc.find_by_code(f"T{i:06d}")
        if found:
            svc.delete_watch_item(found.id)
    check("清理后 count=1", svc.count_watchlist() == 1)


# =========================================================
# Part B：API 层（启动 uvicorn 进程 + urllib）
# =========================================================
def api_request(method: str, path: str, json_body: dict | None = None) -> tuple[int, dict | str]:
    """向 http://127.0.0.1:8765/api/... 发送请求。返回 (status_code, body_json_or_text)。"""
    url = f"http://127.0.0.1:8765/api{path}"
    headers = {"Accept": "application/json"}
    data = None
    if json_body is not None:
        data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def part_b_api_layer():
    global passed, failed
    print("\n========== Part B. REST API 测试 ==========")

    # 启动子进程 uvicorn，端口用 8765 避免跟已有的 8000 冲突
    # 关键：给子进程传 DB_PATH 环境变量 / 或通过 -c 指定？ 最稳妥：生成一个临时入口脚本
    # 因为我们已通过 config.DB_PATH = _TEMP_DB 修改了运行时路径，但子进程不会继承这个修改。
    # 做法：写一个临时的 _test_entry.py，把 config.DB_PATH patch 好再 import main
    entry_path = BACKEND_ROOT / "_test_entry.py"
    entry_path.write_text(
        "\n".join([
            "from pathlib import Path",
            "import sys, os",
            "sys.path.insert(0, str(Path(__file__).parent))",
            "import config",
            f"config.DB_PATH = Path(r'{str(_TEMP_DB)}')",
            "from main import app  # noqa",
            "",
        ]),
        encoding="utf-8",
    )
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    python_exe = str(venv_python) if venv_python.exists() else "python"
    proc = subprocess.Popen(
        [
            python_exe, "-m", "uvicorn",
            "_test_entry:app",
            "--host", "127.0.0.1", "--port", "8765",
            "--log-level", "warning",
        ],
        cwd=str(BACKEND_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        # 等待服务起来（最多 15s）
        up = False
        for _ in range(30):
            try:
                st, _ = api_request("GET", "/health")
                if st == 200:
                    up = True
                    break
            except Exception:
                pass
            time.sleep(0.5)
        if not up:
            check("uvicorn 启动", False, "15s 内未就绪")
            return

        print("\n-- B1. GET /api/watchlist --")
        st, body = api_request("GET", "/watchlist")
        check("200", st == 200, f"status={st}")
        if isinstance(body, dict):
            check("count=1", body.get("count") == 1)
            check("max_size=100", body.get("max_size") == 100)
            check("items 长度 1", len(body.get("items", [])) == 1)

        print("\n-- B2. POST /api/watchlist（自定义 gain） --")
        st, body = api_request("POST", "/watchlist", {
            "stock_code": "300750",
            "stock_name": "宁德时代",
            "gain_pct": 8,
        })
        check("201 Created", st == 201, f"status={st} body={body}")
        new_id = None
        if isinstance(body, dict):
            new_id = body.get("id")
            check("返回 id", isinstance(new_id, int) and new_id > 0)
            check("gain=8", body.get("gain_pct") == 8)
            check("loss 默认 5", body.get("loss_pct") == 5)
            check("turnover 默认 10", body.get("turnover_pct") == 10)

        print("\n-- B3. POST 重复代码（400） --")
        st, body = api_request("POST", "/watchlist", {
            "stock_code": "300750", "stock_name": "宁德时代",
        })
        check("status 400", st == 400, f"status={st}")
        if isinstance(body, dict):
            check("detail 含已在自选", "已在自选股中" in str(body.get("detail", "")))

        print("\n-- B4. PATCH /api/watchlist/{id}（改 loss） --")
        if new_id:
            st, body = api_request("PATCH", f"/watchlist/{new_id}", {"loss_pct": 9})
            check("PATCH 200", st == 200, f"status={st}")
            if isinstance(body, dict):
                check("loss → 9", body.get("loss_pct") == 9)
                check("gain 保持 8", body.get("gain_pct") == 8)

        print("\n-- B5. PATCH 无效 id（404） --")
        st, _ = api_request("PATCH", "/watchlist/99999", {"gain_pct": 1})
        check("PATCH 404", st == 404, f"status={st}")

        print("\n-- B6. DELETE /api/watchlist/{id} --")
        if new_id:
            st, body = api_request("DELETE", f"/watchlist/{new_id}")
            check("DELETE 200", st == 200)
            check("deleted=true", isinstance(body, dict) and body.get("deleted") is True)
            st2, body2 = api_request("DELETE", f"/watchlist/{new_id}")
            check("再次删除 deleted=false", isinstance(body2, dict) and body2.get("deleted") is False)

        print("\n-- B7. Pydantic 阈值范围校验 --")
        st1, _ = api_request("POST", "/watchlist", {
            "stock_code": "NEG", "stock_name": "负数", "gain_pct": -1,
        })
        check("负阈值 422", st1 == 422, f"status={st1}")
        st2, _ = api_request("POST", "/watchlist", {
            "stock_code": "BIG", "stock_name": "超100", "gain_pct": 101,
        })
        check(">100 阈值 422", st2 == 422, f"status={st2}")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        if entry_path.exists():
            entry_path.unlink()


def main():
    part_a_data_layer()
    part_b_api_layer()

    print("\n====================")
    print(f"通过: {passed}  失败: {failed}")
    if failed == 0:
        print("🎉 阶段 2.1 自测全部通过")
    else:
        print("⚠️ 有失败项，请检查")

    # 清理临时 DB
    if _TEMP_DB.exists():
        _TEMP_DB.unlink()
        print(f"🧹 临时测试库已删除")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

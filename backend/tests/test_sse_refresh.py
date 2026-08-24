"""SSE 刷新端到端测试（PowerShell 友好）

运行方式（在另一个终端）：
    .venv\Scripts\python.exe backend\tests\test_sse_refresh.py
"""
import json
import sys
import urllib.request

REFRESH_URL = "http://127.0.0.1:8000/api/refresh"
HEALTH_URL = "http://127.0.0.1:8000/api/health"
LATEST_URL = "http://127.0.0.1:8000/api/snapshot/latest"
DATES_URL = "http://127.0.0.1:8000/api/snapshot/dates"


def test_health() -> bool:
    print("\n[1] 健康检查...")
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print(f"  响应: {data}")
            return data.get("status") == "ok"
    except Exception as e:
        print(f"  失败: {e}")
        return False


def test_sse_refresh() -> bool:
    print("\n[2] SSE 刷新测试（约需 30-60 秒）...")
    print("  触发 POST /api/refresh，监听 SSE 事件流...\n")

    req = urllib.request.Request(REFRESH_URL, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            event_type = None
            data_lines = []
            ok_count = 0
            fail_count = 0
            module_count = 0

            for raw_line in resp:
                line = raw_line.decode("utf-8").rstrip("\n").rstrip("\r")

                if line.startswith("event:"):
                    event_type = line[6:].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[5:].strip())
                elif line == "" and event_type:
                    # 事件结束
                    data_str = "\n".join(data_lines)
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        data = {"raw": data_str}

                    if event_type == "progress":
                        module = data.get("module", "?")
                        status = data.get("status", "?")
                        idx = data.get("index", 0)
                        total = data.get("total", 0)

                        if status == "fetching":
                            print(f"  [{idx}/{total}] 正在拉取 {module}...")
                        elif status == "ok":
                            print(f"  [{idx}/{total}] {module} ✓ 成功")
                            module_count += 1
                            ok_count += 1
                        elif status == "failed":
                            err = data.get("error", "未知错误")
                            print(f"  [{idx}/{total}] {module} ✗ 失败: {err[:80]}")
                            module_count += 1
                            fail_count += 1
                        elif status == "start":
                            print(f"  开始刷新，交易日: {data.get('trade_date')}")

                    elif event_type == "done":
                        print(f"\n  ========== 刷新完成 ==========")
                        print(f"  交易日: {data.get('trade_date')}")
                        print(f"  成功: {data.get('ok_count')} 个模块")
                        print(f"  失败: {data.get('fail_count')} 个模块")
                        if data.get("fail_modules"):
                            print(f"  失败模块: {data['fail_modules']}")
                        return True

                    event_type = None
                    data_lines = []

            print("  未收到 done 事件")
            return False
    except Exception as e:
        print(f"  请求失败: {e}")
        return False


def test_latest_snapshot() -> bool:
    print("\n[3] 读取最后快照...")
    try:
        with urllib.request.urlopen(LATEST_URL, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if data.get("empty"):
                print(f"  无快照（首次使用符合预期）")
                return True
            print(f"  快照日期: {data.get('trade_date')}")
            modules = data.get("modules", {})
            print(f"  模块数: {len(modules)}")
            for name in modules:
                print(f"    - {name}")
            return True
    except Exception as e:
        print(f"  失败: {e}")
        return False


def test_dates() -> bool:
    print("\n[4] 列出存档日期...")
    try:
        with urllib.request.urlopen(DATES_URL, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            dates = data.get("dates", [])
            print(f"  存档日期数: {len(dates)}")
            for d in dates[:5]:
                print(f"    - {d}")
            return True
    except Exception as e:
        print(f"  失败: {e}")
        return False


def main():
    print("=" * 60)
    print("  SSE 刷新端到端测试")
    print("=" * 60)

    results = []
    results.append(("健康检查", test_health()))
    results.append(("SSE 刷新", test_sse_refresh()))
    results.append(("读取最后快照", test_latest_snapshot()))
    results.append(("列出存档日期", test_dates()))

    print("\n" + "=" * 60)
    print("  测试总结")
    print("=" * 60)
    for name, ok in results:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")

    all_pass = all(ok for _, ok in results)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

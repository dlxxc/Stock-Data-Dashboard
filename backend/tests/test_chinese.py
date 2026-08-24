"""验证 FastAPI 返回的 JSON 中文是否正确"""
import json
import urllib.request

url = "http://127.0.0.1:8000/api/snapshot/latest"
with urllib.request.urlopen(url, timeout=5) as resp:
    raw_bytes = resp.read()
    # FastAPI 默认返回 UTF-8
    text_utf8 = raw_bytes.decode("utf-8")
    data = json.loads(text_utf8)

print("=" * 50)
print("Python urllib 读取（UTF-8 解码）")
print("=" * 50)
print(f"trade_date: {data['trade_date']}")
modules = data.get("modules", {})
print(f"modules: {list(modules.keys())}")

if "limit_pool" in modules:
    lp = modules["limit_pool"]
    print(f"\n涨停总数: {lp['limit_up']['total']}")
    print("前5只涨停股:")
    for i, s in enumerate(lp["limit_up"]["stocks"][:5], 1):
        print(f"  {i}. {s['name']}({s['code']}) 涨幅={s['pct']:.2f}% 行业={s['industry']}")

    print(f"\n跌停总数: {lp['limit_down']['total']}")
    print("前3只跌停股:")
    for i, s in enumerate(lp["limit_down"]["stocks"][:3], 1):
        print(f"  {i}. {s['name']}({s['code']}) 跌幅={s['pct']:.2f}% 行业={s['industry']}")

print("\n" + "=" * 50)
print("结论: 中文是否正确？")
print("=" * 50)
first_name = lp["limit_up"]["stocks"][0]["name"]
if "深中华" in first_name or "A" in first_name:
    print(f"✓ 正确: 第1只涨停股名称 = {first_name}")
else:
    print(f"✗ 异常: 第1只涨停股名称 = {first_name}")

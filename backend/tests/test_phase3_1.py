"""阶段 3.1 资讯模块自测脚本

验证内容：
1. 数据源 fetch() 函数（东财主源 + 新浪回退）
2. GET /api/news 接口（读快照 + 历史回看 + 失败检测）

运行方式：
    cd backend
    ..\.venv\Scripts\python.exe tests\test_phase3_1.py
"""
import json
import os
import sys
from pathlib import Path

# 添加 backend 到模块搜索路径
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

# 临时覆盖数据库路径（避免污染用户真实数据）
test_db_path = backend_root / "tests" / "test_phase3_1.db"
os.environ["STOCK_DB_PATH"] = str(test_db_path)

import db
import snapshot
from config import MODULE_NEWS
from data_sources.news import fetch as fetch_news

# 测试 3 需要导入 main 模块前先确保 config 常量可用
import config


def test_1_fetch_news():
    """测试数据源 fetch() 函数（真实调用 akshare）"""
    print("\n=== 测试 1：数据源 fetch_news() ===")
    
    result = fetch_news()
    
    assert "articles" in result, "缺少 articles 字段"
    assert "source" in result, "缺少 source 字段"
    assert "total" in result, "缺少 total 字段"
    
    articles = result["articles"]
    source = result["source"]
    total = result["total"]
    
    assert isinstance(articles, list), "articles 必须是列表"
    assert len(articles) > 0, "articles 不能为空"
    assert len(articles) <= 20, f"articles 超过 20 条：{len(articles)}"
    assert source in ["eastmoney", "sina"], f"source 必须是 eastmoney 或 sina，实际：{source}"
    assert total == len(articles), f"total 与 articles 长度不一致：{total} != {len(articles)}"
    
    # 验证 article 结构
    first = articles[0]
    assert "title" in first, "article 缺少 title"
    assert "summary" in first, "article 缺少 summary"
    assert "publish_time" in first, "article 缺少 publish_time"
    assert "url" in first, "article 缺少 url"
    
    assert isinstance(first["title"], str), "title 必须是字符串"
    assert len(first["title"]) > 0, "title 不能为空"
    
    print(f"✅ fetch_news() 成功：source={source}, total={total}")
    print(f"   第1条：{first['title'][:50]}...")
    print(f"   时间：{first['publish_time']}")
    return result


def test_2_snapshot_save_read():
    """测试快照存取（本地 SQLite）"""
    print("\n=== 测试 2：快照存取 ===")
    
    # 初始化测试数据库
    if test_db_path.exists():
        test_db_path.unlink()
    db.init_db()
    
    # 构造测试数据
    test_data = {
        "articles": [
            {
                "title": "测试标题1",
                "summary": "测试摘要1",
                "publish_time": "2026-08-25 22:00:00",
                "url": "https://example.com/1"
            },
            {
                "title": "测试标题2",
                "summary": "测试摘要2",
                "publish_time": "2026-08-25 21:00:00",
                "url": "https://example.com/2"
            }
        ],
        "source": "eastmoney",
        "total": 2
    }
    
    # 存档
    snapshot.save_snapshot(
        trade_date="2026-08-25",
        module_name=MODULE_NEWS,
        data=test_data,
        status="ok"
    )
    print("✅ 快照存档成功")
    
    # 读取最新快照
    snap = snapshot.get_latest_snapshot()
    assert snap is not None, "快照读取失败"
    assert snap["trade_date"] == "2026-08-25", "trade_date 不匹配"
    assert MODULE_NEWS in snap["modules"], "modules 中缺少 news"
    
    news_module = snap["modules"][MODULE_NEWS]
    assert news_module["total"] == 2, "total 不匹配"
    assert len(news_module["articles"]) == 2, "articles 长度不匹配"
    assert news_module["articles"][0]["title"] == "测试标题1", "title 不匹配"
    
    print("✅ 快照读取验证通过")
    
    # 读取指定日期
    snap2 = snapshot.get_snapshot_by_date("2026-08-25")
    assert snap2 is not None, "按日期读取失败"
    assert snap2["trade_date"] == "2026-08-25", "trade_date 不匹配"
    print("✅ 按日期读取验证通过")
    
    return test_data


def test_3_api_news():
    """测试 GET /api/news 接口（通过 main.py 直接调用）"""
    print("\n=== 测试 3：GET /api/news 接口 ===")
    
    from main import api_news
    
    # 场景1：读取最新快照
    result = api_news()
    assert "trade_date" in result, "缺少 trade_date"
    assert "total" in result, "缺少 total"
    assert "articles" in result, "缺少 articles"
    assert "source" in result, "缺少 source"
    assert result["total"] == 2, f"total 应为 2，实际：{result['total']}"
    assert len(result["articles"]) == 2, f"articles 长度应为 2，实际：{len(result['articles'])}"
    print(f"✅ 场景1：读取最新快照成功，trade_date={result['trade_date']}, total={result['total']}")
    
    # 场景2：按日期读取
    result2 = api_news(trade_date="2026-08-25")
    assert result2["trade_date"] == "2026-08-25", "trade_date 不匹配"
    assert result2["total"] == 2, "total 不匹配"
    print("✅ 场景2：按日期读取成功")
    
    # 场景3：读取不存在的日期
    result3 = api_news(trade_date="2026-01-01")
    assert result3.get("empty") is True, "应返回 empty=True"
    print("✅ 场景3：不存在日期返回 empty")
    
    # 场景4：模拟失败状态（手动存一个 failed 快照）
    snapshot.save_snapshot(
        trade_date="2026-08-26",
        module_name=MODULE_NEWS,
        data={},
        status="failed",
        error_msg="测试失败"
    )
    result4 = api_news(trade_date="2026-08-26")
    assert result4.get("empty") is True, "失败快照应返回 empty=True"
    assert "error" in result4, "失败快照应包含 error 字段"
    print(f"✅ 场景4：失败快照返回 empty + error：{result4['error'][:50]}...")
    
    return result


def main():
    print("=" * 60)
    print("阶段 3.1 资讯模块自测")
    print("=" * 60)
    
    passed = 0
    total = 3
    
    try:
        test_1_fetch_news()
        passed += 1
    except Exception as e:
        print(f"❌ 测试 1 失败：{e}")
    
    try:
        test_2_snapshot_save_read()
        passed += 1
    except Exception as e:
        print(f"❌ 测试 2 失败：{e}")
    
    try:
        test_3_api_news()
        passed += 1
    except Exception as e:
        print(f"❌ 测试 3 失败：{e}")
    
    print("\n" + "=" * 60)
    print(f"测试结果：{passed}/{total} 通过")
    print("=" * 60)
    
    # 清理测试数据库
    if test_db_path.exists():
        test_db_path.unlink()
        print(f"已清理测试数据库：{test_db_path}")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

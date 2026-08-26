"""阶段 3.3 AI 总结模块自测脚本

验证内容（Mock GLM，不真实调用）：
1. JSON 容错解析（直接/代码块/花括号）
2. 索引清洗（越界/非整数/去重）
3. 板块清洗（坏结构丢弃）
4. 缓存读写

运行方式：
    cd backend
    ..\.venv\Scripts\python.exe tests/test_phase3_3.py
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

# 添加 backend 到模块搜索路径
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

# 临时覆盖数据库路径
test_db_path = backend_root / "tests" / "test_phase3_3.db"
os.environ["STOCK_DB_PATH"] = str(test_db_path)

# 清理旧测试库
if test_db_path.exists():
    test_db_path.unlink()

import db
from ai_summary import _extract_json, _clean_indices, _clean_sectors, _save_cache, _load_cache


def test_1_json_extraction():
    """测试 JSON 容错解析。"""
    print("\n=== 测试 1：JSON 容错解析 ===")

    # 1. 直接 JSON
    assert _extract_json('{"a": 1}') == {"a": 1}, "直接 JSON 解析失败"

    # 2. 代码块包裹
    text = '```json\n{"overview": "测试", "sectors": []}\n```'
    result = _extract_json(text)
    assert result == {"overview": "测试", "sectors": []}, f"代码块 JSON 解析失败：{result}"

    # 3. 花括号匹配
    text = '这是 AI 的回答：\n{"name": "科技", "summary": "走强"}\n以上是总结。'
    result = _extract_json(text)
    assert result == {"name": "科技", "summary": "走强"}, f"花括号匹配解析失败：{result}"

    # 4. 数组
    assert _extract_json('[{"a": 1}, {"b": 2}]') == [{"a": 1}, {"b": 2}], "数组解析失败"

    # 5. 失败 → 抛异常
    try:
        _extract_json("不是 JSON 的纯文本")
        assert False, "应抛异常"
    except ValueError:
        pass

    print("✅ JSON 容错解析通过")


def test_2_index_cleaning():
    """测试索引清洗。"""
    print("\n=== 测试 2：索引清洗 ===")
    total = 5

    # 正常
    assert _clean_indices([0, 2, 4], total) == [0, 2, 4], "正常索引失败"

    # 越界（负数 + 超出）
    assert _clean_indices([-1, 0, 5, 3], total) == [0, 3], "越界索引未剔除"

    # 非整数
    assert _clean_indices([0, "1", 2.0, "abc", None], total) == [0, 1, 2], "非整数索引未清洗"

    # 去重
    assert _clean_indices([0, 0, 1, 1, 2], total) == [0, 1, 2], "重复索引未去重"

    # 非列表
    assert _clean_indices("abc", total) == [], "非列表应返回空"
    assert _clean_indices(None, total) == [], "None 应返回空"

    print("✅ 索引清洗通过")


def test_3_sectors_cleaning():
    """测试板块清洗。"""
    print("\n=== 测试 3：板块清洗 ===")
    total = 3

    raw = [
        {"name": "科技", "summary": "半导体走强", "article_indices": [0, 1]},
        {"name": "消费", "summary": "板块回调", "article_indices": [2, 5]},  # 5 越界
        {"summary": "无板块名"},  # 无 name → 丢弃
        "not_a_dict",  # 坏结构 → 丢弃
        {"name": "金融", "summary": "震荡", "article_indices": "not_list"},  # indices 非 list
    ]
    result = _clean_sectors(raw, total)

    assert len(result) == 3, f"应保留 3 个板块，实际 {len(result)}"
    assert result[0]["name"] == "科技", "板块 0 名称不对"
    assert result[0]["article_indices"] == [0, 1], "板块 0 索引不对"
    assert result[1]["article_indices"] == [2], "板块 1 越界索引未剔除"
    assert result[2]["article_indices"] == [], "板块 2 非列表 indices 应为空"

    print("✅ 板块清洗通过")


def test_4_cache_read_write():
    """测试缓存读写。"""
    print("\n=== 测试 4：缓存读写 ===")
    db.init_db()

    # 写入
    overview = "今日市场震荡分化"
    sectors = [{"name": "科技", "summary": "走强", "article_indices": [0, 1]}]
    _save_cache("2026-01-01", overview, sectors, "ok")

    # 读取
    cached = _load_cache("2026-01-01")
    assert cached is not None, "缓存读取为 None"
    assert cached["overview"] == overview, "overview 不一致"
    assert cached["sectors"] == sectors, "sectors 不一致"
    assert cached["status"] == "ok", "status 不对"

    # 不存在
    assert _load_cache("2099-01-01") is None, "不存在的日期应返回 None"

    print("✅ 缓存读写通过")


def test_5_generate_need_key():
    """测试无 Key 时 generate 返回 need_key（不真实调 GLM）。"""
    print("\n=== 测试 5：无 Key → need_key ===")
    from ai_summary import generate_summary

    # 临时清空 Key
    with patch("ai_summary.get_api_key", return_value=""):
        # 也需要一个有 news 的快照（用不同日期避免命中 test_4 缓存）
        with patch("ai_summary.get_latest_snapshot") as mock_snap:
            mock_snap.return_value = {
                "trade_date": "2099-01-01",
                "modules": {"news": {"articles": [{"title": "测试", "summary": "内容"}]}},
            }
            result = generate_summary()
            assert result["status"] == "need_key", f"期望 need_key，实际 {result['status']}"
            assert "API Key" in result["error"], "error 应提及 Key"

    print("✅ need_key 通过")


def test_6_generate_glm_failed():
    """测试 GLM 调用失败时正确标 failed 不造数据。"""
    print("\n=== 测试 6：GLM 失败 → failed ===")
    from ai_summary import generate_summary

    with patch("ai_summary.get_api_key", return_value="fake_key"):
        with patch("ai_summary.get_latest_snapshot") as mock_snap:
            mock_snap.return_value = {
                "trade_date": "2026-01-02",
                "modules": {"news": {"articles": [{"title": "测试", "summary": "内容"}]}},
            }
            # mock GLM 调用失败
            with patch("ai_summary._call_glm", side_effect=Exception("模拟超时")):
                result = generate_summary()
                assert result["status"] == "failed", f"期望 failed，实际 {result['status']}"
                assert result["overview"] == "", "失败时 overview 应为空"
                assert result["sectors"] == [], "失败时 sectors 应为空"
                assert "模拟超时" in result["error"], "error 应包含失败原因"

    print("✅ GLM 失败兜底通过")


def test_7_generate_success():
    """测试 GLM 成功时返回结构化数据。"""
    print("\n=== 测试 7：GLM 成功 → 结构化结果 ===")
    from ai_summary import generate_summary

    articles = [{"title": f"资讯{i}", "summary": f"内容{i}"} for i in range(5)]

    with patch("ai_summary.get_api_key", return_value="fake_key"):
        with patch("ai_summary.get_latest_snapshot") as mock_snap:
            mock_snap.return_value = {
                "trade_date": "2026-01-03",
                "modules": {"news": {"articles": articles}},
            }
            # mock GLM 返回
            with patch("ai_summary._call_glm") as mock_glm:
                # Pass 1 返回 overview，Pass 2 返回 sectors JSON
                mock_glm.side_effect = [
                    "今日市场整体震荡分化",
                    json.dumps([
                        {"name": "科技", "summary": "半导体走强", "article_indices": [0, 2, 4]},
                        {"name": "消费", "summary": "回调", "article_indices": [1, 3]},
                    ]),
                ]
                result = generate_summary()
                assert result["status"] == "ok", f"期望 ok，实际 {result['status']}"
                assert "震荡分化" in result["overview"], "overview 内容不对"
                assert len(result["sectors"]) == 2, f"板块数应为 2，实际 {len(result['sectors'])}"
                assert result["sectors"][0]["article_indices"] == [0, 2, 4], "板块索引不对"

    print("✅ 结构化生成通过")


if __name__ == "__main__":
    test_1_json_extraction()
    test_2_index_cleaning()
    test_3_sectors_cleaning()
    test_4_cache_read_write()
    test_5_generate_need_key()
    test_6_generate_glm_failed()
    test_7_generate_success()
    # 清理
    if test_db_path.exists():
        test_db_path.unlink()
    print("\n✅ 阶段 3.3 全部测试通过")
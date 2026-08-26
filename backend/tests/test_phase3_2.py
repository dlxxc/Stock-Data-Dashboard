"""阶段 3.2 AI 配置模块自测脚本

验证内容：
1. save/get/clear/mask 基本存取
2. 传空串清空
3. 掩码不回传明文

运行方式：
    cd backend
    ..\.venv\Scripts\python.exe tests/test_phase3_2.py
"""
import sys
from pathlib import Path

# 添加 backend 到模块搜索路径
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

import config
import ai_config

# 将配置文件指向测试临时文件，避免污染用户真实配置
config.AI_CONFIG_PATH = backend_root / "tests" / "test_ai_config.json"


def _reset():
    """清理测试配置文件（若存在）"""
    p = config.AI_CONFIG_PATH
    if p.exists():
        p.unlink()


def test_1_save_get_clear():
    """测试基本存取与清空。"""
    print("\n=== 测试 1：save / get / clear ===")
    _reset()

    assert ai_config.has_api_key() is False, "初始应无 Key"
    assert ai_config.get_api_key() == "", "初始 get 应为空串"
    assert ai_config.mask_key("") == "", "空串掩码应为空"

    ai_config.save_api_key("sk-abc123456789")
    assert ai_config.has_api_key() is True, "保存后应 has_key"
    assert ai_config.get_api_key() == "sk-abc123456789", "get 应返回原值"

    ai_config.clear_api_key()
    assert ai_config.has_api_key() is False, "清空后应无 Key"
    assert ai_config.get_api_key() == "", "清空后 get 应为空串"
    print("✅ save / get / clear 通过")
    _reset()


def test_2_empty_save_clears():
    """测试传空串等价于清空。"""
    print("\n=== 测试 2：传空串清空 ===")
    _reset()
    ai_config.save_api_key("sk-xyz")
    assert ai_config.has_api_key() is True, "先保存"
    ai_config.save_api_key("   ")
    assert ai_config.has_api_key() is False, "传空白应清空"
    print("✅ 传空串清空通过")
    _reset()


def test_3_mask():
    """测试掩码：长度判定 + 前后缀打码。"""
    print("\n=== 测试 3：掩码 ===")
    assert ai_config.mask_key("sk-1234567890abcd") == "sk-****abcd", "长 Key 应前后缀打码"
    assert ai_config.mask_key("short") == "****", "短 Key 应整体打码"
    # 掩码绝不包含完整明文
    assert "1234567890" not in ai_config.mask_key("sk-1234567890abcd"), "掩码不得泄露明文"
    print("✅ 掩码通过")
    _reset()


if __name__ == "__main__":
    test_1_save_get_clear()
    test_2_empty_save_clears()
    test_3_mask()
    print("\n✅ 阶段 3.2 全部测试通过")
    _reset()
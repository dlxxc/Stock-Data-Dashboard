"""AI 配置管理（阶段 3.2）

智谱 API Key 的本地存取，存储在 `data/ai_config.json`（本地明文配置文件）：

    { "api_key": "xxxxxxxxxxxxxxxx" }

安全约定：
- API 层永不回传明文 Key，只返回 has_key / masked_key
- data/ 目录已在 .gitignore 中，Key 不会被提交到仓库
- 支持保存、清空（传空串或调用 clear_api_key 删除字段）
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from config import AI_CONFIG_PATH

logger = logging.getLogger("stock_dashboard.ai_config")

# ai_config.json 中存 Key 的字段名
KEY_FIELD = "api_key"


def _read() -> dict:
    """读取配置文件；不存在或损坏时返回空 dict（不抛异常）。"""
    try:
        with open(AI_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        logger.warning("AI 配置文件损坏，按空配置处理: %s", AI_CONFIG_PATH)
        return {}


def _write(data: dict) -> None:
    """写入配置文件（自动建目录）。"""
    AI_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AI_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_api_key() -> str:
    """读取 API Key，未配置返回空串。"""
    return str(_read().get(KEY_FIELD, "") or "").strip()


def has_api_key() -> bool:
    """是否已配置 API Key。"""
    return bool(get_api_key())


def save_api_key(api_key: str) -> None:
    """保存 API Key；传空串等价于清空。"""
    key = (api_key or "").strip()
    data = _read()
    if key:
        data[KEY_FIELD] = key
    else:
        data.pop(KEY_FIELD, None)
    _write(data)
    logger.info("AI API Key 已%s", "保存" if key else "清空")


def clear_api_key() -> None:
    """清空 API Key（删除字段）。"""
    save_api_key("")


def mask_key(api_key: str) -> str:
    """对 Key 做掩码，供前端展示状态（不回传明文）。

    - 空串 → ""
    - 长度 <= 8 → "****"
    - 否则 → 前 3 位 + "****" + 后 4 位（如 sk-****abcd）
    """
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:3]}****{api_key[-4:]}"
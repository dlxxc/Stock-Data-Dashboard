"""AI 智能总结模块（阶段 3.3）

读当日资讯快照 → 调智谱 GLM-4-Flash → 结构化总结（整体概览 + 板块分组）→ 落库缓存。

两轮调用（用户确认：整体 + 板块分批都要）：
  Pass 1（整体总览）：一次调用，输出 overview（一句话）
  Pass 2（板块分组）：一次调用，输出 sectors[]（name + summary + article_indices）

军规铁律：
- 绝不显示假数据：AI 失败/超时/解析失败 → status=failed + error_msg，不落正常数据
- 失败即空 + 可重试：前端拿到 failed 状态显示红色重试按钮（军规 6 不静默）
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import httpx

from ai_config import get_api_key
from config import MODULE_NEWS
from db import get_db
from snapshot import get_latest_snapshot, get_snapshot_by_date

logger = logging.getLogger("stock_dashboard.ai_summary")

# ========== 智谱 GLM 配置 ==========
GLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
GLM_MODEL = "glm-4-flash"
GLM_TIMEOUT = 60.0          # 单次请求超时（秒）
GLM_MAX_RETRIES = 1        # 失败重试次数（不含首次，共 1+1=2 次）

# ========== 进程内并发锁（防同日重复生成）==========
_generating_locks: dict[str, bool] = {}


def _is_generating(trade_date: str) -> bool:
    """检查某日是否正在生成中（进程内简单锁）。"""
    return _generating_locks.get(trade_date, False)


def _set_generating(trade_date: str, value: bool) -> None:
    _generating_locks[trade_date] = value


# ========== 缓存读写 ==========

def _save_cache(trade_date: str, overview: str, sectors: list[dict], status: str, error_msg: str = "") -> None:
    """保存/更新 AI 总结缓存。"""
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO ai_summaries (trade_date, overview, sectors_json, status, error_msg, generated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
        """, (
            trade_date,
            overview,
            json.dumps(sectors, ensure_ascii=False),
            status,
            error_msg,
        ))


def _load_cache(trade_date: str) -> dict[str, Any] | None:
    """读取缓存的 AI 总结；无缓存返回 None。"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT trade_date, overview, sectors_json, status, error_msg, generated_at FROM ai_summaries WHERE trade_date = ?",
            (trade_date,),
        ).fetchone()
    if row is None:
        return None
    sectors_raw = row["sectors_json"] or "[]"
    try:
        sectors = json.loads(sectors_raw)
    except json.JSONDecodeError:
        sectors = []
    return {
        "trade_date": row["trade_date"],
        "overview": row["overview"] or "",
        "sectors": sectors,
        "status": row["status"] or "ok",
        "error": row["error_msg"] or "",
        "generated_at": row["generated_at"] or "",
    }


# ========== GLM 调用 ==========

def _call_glm(api_key: str, user_prompt: str, system_prompt: str = "") -> str:
    """调用智谱 GLM-4-Flash，返回 content 文本。

    Raises:
        Exception: 网络/超时/鉴权/HTTP 错误等
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    payload = {
        "model": GLM_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 2000,
    }

    last_err: Exception | None = None
    for attempt in range(GLM_MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=GLM_TIMEOUT) as client:
                resp = client.post(GLM_API_URL, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                if not content or not content.strip():
                    raise ValueError("GLM 返回空内容")
                return content.strip()
        except httpx.TimeoutException:
            last_err = Exception(f"GLM 请求超时（{GLM_TIMEOUT}s）")
            logger.warning(f"GLM 超时，尝试 {attempt + 1}/{GLM_MAX_RETRIES + 1}")
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code in (401, 403):
                raise Exception("API Key 无效或已过期，请检查 AI 设置") from e
            last_err = Exception(f"GLM HTTP {status_code}：{e.response.text[:200]}")
            logger.warning(f"GLM HTTP {status_code}，尝试 {attempt + 1}/{GLM_MAX_RETRIES + 1}")
        except (KeyError, IndexError, ValueError) as e:
            last_err = Exception(f"GLM 响应解析失败：{e}")
            logger.warning(f"GLM 响应异常，尝试 {attempt + 1}/{GLM_MAX_RETRIES + 1}")
        except Exception as e:
            last_err = e
            logger.warning(f"GLM 调用异常：{e}，尝试 {attempt + 1}/{GLM_MAX_RETRIES + 1}")
        if attempt < GLM_MAX_RETRIES:
            time.sleep(1)

    raise last_err or Exception("GLM 调用失败（未知原因）")


# ========== JSON 容错解析 ==========

def _extract_json(text: str) -> Any:
    """从 GLM 返回文本中提取 JSON。

    策略（军规：绝不静默失败）：
    1. 直接 json.loads
    2. 去除 ```json ... ``` 代码块后解析
    3. 花括号匹配提取子串后解析
    全部失败则抛异常
    """
    text = text.strip()

    # 1. 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. 去除代码块
    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if code_block:
        try:
            return json.loads(code_block.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. 花括号匹配
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"无法从 GLM 响应中提取有效 JSON：{text[:200]}...")


# ========== 索引清洗 ==========

def _clean_indices(raw_indices: Any, total: int) -> list[int]:
    """清洗板块的 article_indices：只保留合法非负整数索引。"""
    if not isinstance(raw_indices, list):
        return []
    cleaned: list[int] = []
    for idx in raw_indices:
        try:
            n = int(idx)
            if 0 <= n < total and n not in cleaned:
                cleaned.append(n)
        except (ValueError, TypeError):
            continue
    return cleaned


def _clean_sectors(raw: Any, total: int) -> list[dict]:
    """清洗板块列表：保留 name/summary/indices，丢弃坏数据。"""
    if not isinstance(raw, list):
        return []
    sectors: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        summary = str(item.get("summary", "")).strip()
        if not name:
            continue
        indices = _clean_indices(item.get("article_indices", []), total)
        sectors.append({
            "name": name,
            "summary": summary,
            "article_indices": indices,
        })
    return sectors


# ========== Prompt 构建 ==========

def _build_overview_prompt(articles: list[dict]) -> tuple[str, str]:
    """Pass 1：整体总览 prompt。"""
    system = "你是一名专业的A股市场分析师。请根据提供的财经资讯，给出今日市场整体概览。"
    lines = []
    for i, a in enumerate(articles):
        title = a.get("title", "")
        summary = a.get("summary", "")
        lines.append(f"{i}. {title}：{summary}")
    user = (
        f"以下是今日 {len(articles)} 条财经资讯：\n\n"
        + "\n".join(lines)
        + "\n\n请用一句话（不超过100字）概括今日市场整体动向。"
        "仅输出纯文本，不要任何标记或格式。"
    )
    return user, system


def _build_sectors_prompt(articles: list[dict]) -> tuple[str, str]:
    """Pass 2：板块分组 prompt。"""
    system = "你是一名专业的A股市场分析师。请根据提供的财经资讯，按板块分类并给出每个板块的动向摘要。"
    lines = []
    for i, a in enumerate(articles):
        title = a.get("title", "")
        summary = a.get("summary", "")
        lines.append(f"[{i}] {title}：{summary}")
    user = (
        f"以下是今日 {len(articles)} 条财经资讯（编号 0-{len(articles) - 1}）：\n\n"
        + "\n".join(lines)
        + "\n\n请按板块分类，输出 JSON 数组，每个元素包含：\n"
        '- "name": 板块名称（如"科技""消费""金融"等）\n'
        '- "summary": 该板块动向的一句话描述（不超过50字）\n'
        '- "article_indices": 相关资讯编号数组（对应上面的 [0]-[N] 编号）\n\n'
        "仅输出 JSON 数组，不要任何额外文本或代码块标记。"
    )
    return user, system


# ========== 主入口 ==========

def generate_summary(trade_date: str | None = None, force: bool = False) -> dict[str, Any]:
    """生成或读取 AI 总结。

    Args:
        trade_date: 指定日期；None 取最新快照
        force: True 强制重新生成（忽略缓存）

    Returns:
        {
            "trade_date": "...",
            "overview": "...",
            "sectors": [{name, summary, article_indices}, ...],
            "status": "ok" | "failed" | "not_generated" | "need_key" | "no_news" | "generating",
            "error": "...",
            "generated_at": "..."
        }
    """
    # 1. 拿快照日期
    if trade_date:
        snap = get_snapshot_by_date(trade_date)
    else:
        snap = get_latest_snapshot()

    if snap is None:
        return {"status": "no_news", "error": "无快照数据，请先刷新", "trade_date": "", "overview": "", "sectors": [], "generated_at": ""}

    snap_date = snap["trade_date"]

    # 2. 非强制时先读缓存
    if not force:
        cached = _load_cache(snap_date)
        if cached and cached["status"] == "ok":
            return cached
        # failed 缓存也返回（让前端知道上次失败过，可重试）
        if cached and cached["status"] == "failed":
            return cached

    # 3. 检查并发锁
    if _is_generating(snap_date):
        return {"status": "generating", "error": "正在生成中，请稍候", "trade_date": snap_date, "overview": "", "sectors": [], "generated_at": ""}

    # 4. 检查 Key
    api_key = get_api_key()
    if not api_key:
        return {"status": "need_key", "error": "未配置 AI API Key，请先在 AI 设置中填写", "trade_date": snap_date, "overview": "", "sectors": [], "generated_at": ""}

    # 5. 读资讯快照
    modules = snap.get("modules", {}) or {}
    news_module = modules.get(MODULE_NEWS) or {}
    articles = news_module.get("articles", []) or []
    if not articles:
        return {"status": "no_news", "error": "当日无资讯数据，请先刷新", "trade_date": snap_date, "overview": "", "sectors": [], "generated_at": ""}

    # 6. 加锁 → 调 GLM
    _set_generating(snap_date, True)
    try:
        # Pass 1：整体总览
        user_prompt, system_prompt = _build_overview_prompt(articles)
        overview_text = _call_glm(api_key, user_prompt, system_prompt)

        # Pass 2：板块分组
        user_prompt2, system_prompt2 = _build_sectors_prompt(articles)
        sectors_text = _call_glm(api_key, user_prompt2, system_prompt2)

        # 解析板块 JSON
        sectors_raw = _extract_json(sectors_text)
        sectors = _clean_sectors(sectors_raw, len(articles))

        # 校验：overview 或 sectors 全空 → 视为失败
        if not overview_text and not sectors:
            raise ValueError("AI 返回空内容（overview 和 sectors 均为空）")

        # 7. 落库缓存
        _save_cache(snap_date, overview_text, sectors, "ok")
        logger.info(f"AI 总结生成成功：trade_date={snap_date}, sectors={len(sectors)}")
        return {
            "trade_date": snap_date,
            "overview": overview_text,
            "sectors": sectors,
            "status": "ok",
            "error": "",
            "generated_at": "",
        }

    except Exception as e:
        err_msg = str(e)
        logger.error(f"AI 总结生成失败：trade_date={snap_date}, error={err_msg}")
        _save_cache(snap_date, "", [], "failed", err_msg)
        return {
            "trade_date": snap_date,
            "overview": "",
            "sectors": [],
            "status": "failed",
            "error": err_msg,
            "generated_at": "",
        }
    finally:
        _set_generating(snap_date, False)


def get_cached_summary(trade_date: str | None = None) -> dict[str, Any]:
    """读取缓存的 AI 总结（不触发生成）。"""
    if trade_date:
        snap = get_snapshot_by_date(trade_date)
    else:
        snap = get_latest_snapshot()
    if snap is None:
        return {"status": "not_generated", "trade_date": "", "overview": "", "sectors": [], "error": "", "generated_at": ""}

    cached = _load_cache(snap["trade_date"])
    if cached is None:
        return {"status": "not_generated", "trade_date": snap["trade_date"], "overview": "", "sectors": [], "error": "", "generated_at": ""}
    return cached
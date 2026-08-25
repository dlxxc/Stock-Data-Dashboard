"""资讯数据模块（阶段 3.1）

拉取东财全球财经快讯，最新 20 条。
akshare 接口：
- stock_info_global_em()：东财全球快讯（200 条）
  字段：标题/摘要/发布时间/链接，时间倒序
- stock_info_global_sina()：新浪全球快讯（20 条）
  字段：时间/内容，时间倒序

数据源策略（双源容错）：
1. 主源：stock_info_global_em 取前 20 条
2. 回退：主源失败时用 stock_info_global_sina 取 20 条（字段不同需统一输出）
3. 全失败：抛异常，让外层存档 status=failed

输出结构：
{
  "articles": [
    {
      "title": "美国8月谘商会消费者信心指数89.4",
      "summary": "美国8月谘商会消费者信心指数89.4，预期90.2...",
      "publish_time": "2026-08-25 22:01:18",
      "url": "https://finance.eastmoney.com/a/202608253853345568.html"
    },
    ...
  ],
  "source": "eastmoney" | "sina",
  "total": 20
}
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import pandas as pd

logger = logging.getLogger("stock_dashboard.news")

# 取最新 N 条（用户确认 20 条）
NEWS_LIMIT = 20


def _safe_str(v) -> str:
    """安全转字符串，None/NaN 转空串"""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


def _normalize_time(time_str: str) -> str:
    """时间统一格式化为 YYYY-MM-DD HH:MM:SS"""
    if not time_str:
        return ""
    try:
        # 尝试解析多种格式
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S"]:
            try:
                dt = datetime.strptime(time_str, fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        return time_str
    except Exception:
        return time_str


def _fetch_eastmoney() -> list[dict[str, Any]]:
    """拉取东财全球快讯（主源）"""
    import akshare as ak

    logger.info("拉取东财资讯 stock_info_global_em...")
    df = ak.stock_info_global_em()
    
    if df is None or df.empty:
        raise ValueError("东财资讯返回空数据")
    
    # 取前 20 条（已按时间倒序）
    df = df.head(NEWS_LIMIT)
    
    articles = []
    for _, row in df.iterrows():
        articles.append({
            "title": _safe_str(row.get("标题", "")),
            "summary": _safe_str(row.get("摘要", "")),
            "publish_time": _normalize_time(_safe_str(row.get("发布时间", ""))),
            "url": _safe_str(row.get("链接", "")),
        })
    
    logger.info(f"东财资讯成功拉取 {len(articles)} 条")
    return articles


def _fetch_sina() -> list[dict[str, Any]]:
    """拉取新浪全球快讯（回退源）"""
    import akshare as ak

    logger.info("拉取新浪资讯 stock_info_global_sina（回退源）...")
    df = ak.stock_info_global_sina()
    
    if df is None or df.empty:
        raise ValueError("新浪资讯返回空数据")
    
    # 新浪只返回 20 条，全部取
    articles = []
    for _, row in df.iterrows():
        content = _safe_str(row.get("内容", ""))
        articles.append({
            "title": content[:50] + ("..." if len(content) > 50 else ""),  # 截取前 50 字作标题
            "summary": content,
            "publish_time": _normalize_time(_safe_str(row.get("时间", ""))),
            "url": "",  # 新浪接口无链接字段
        })
    
    logger.info(f"新浪资讯成功拉取 {len(articles)} 条")
    return articles


def fetch(trade_date: str | None = None) -> dict[str, Any]:
    """资讯模块主入口（双源容错）
    
    Args:
        trade_date: 交易日（资讯实时拉取，不按日期过滤，此参数保留兼容）
    
    Returns:
        {
          "articles": [...],
          "source": "eastmoney" | "sina",
          "total": 20
        }
    
    Raises:
        Exception: 双源全失败时抛出，由外层存档 status=failed
    """
    # 尝试主源东财
    try:
        articles = _fetch_eastmoney()
        return {
            "articles": articles,
            "source": "eastmoney",
            "total": len(articles),
        }
    except Exception as e:
        logger.warning(f"东财资讯失败: {e}，回退新浪...")
    
    # 回退新浪
    try:
        articles = _fetch_sina()
        return {
            "articles": articles,
            "source": "sina",
            "total": len(articles),
        }
    except Exception as e:
        logger.error(f"新浪资讯也失败: {e}")
        raise Exception("资讯双源均失败（东财+新浪）") from e

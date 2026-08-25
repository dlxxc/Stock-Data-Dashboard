"""akshare 数据源模块包

每个子模块封装一个数据维度，对外暴露统一的 fetch() 接口。
"""
from .dragon_tiger import fetch as fetch_dragon_tiger
from .indices import fetch as fetch_indices
from .limit_pool import fetch as fetch_limit_pool
from .money_flow import fetch as fetch_money_flow
from .news import fetch as fetch_news
from .sector_breadth import fetch as fetch_sector_breadth
from .watchlist_quotes import fetch as fetch_watchlist_quotes

# 模块名 -> fetch 函数的映射（供 main.py 调度）
FETCHERS = {
    "indices": fetch_indices,
    "limit_pool": fetch_limit_pool,
    "money_flow": fetch_money_flow,
    "sector_breadth": fetch_sector_breadth,
    "watchlist_quotes": fetch_watchlist_quotes,
    "dragon_tiger": fetch_dragon_tiger,
    "news": fetch_news,
}

__all__ = [
    "FETCHERS",
    "fetch_indices",
    "fetch_limit_pool",
    "fetch_money_flow",
    "fetch_sector_breadth",
    "fetch_watchlist_quotes",
    "fetch_dragon_tiger",
    "fetch_news",
]

"""配置常量

集中管理所有可配置项，避免散落在各模块。
"""
from pathlib import Path

# ========== 路径配置 ==========
# 项目根目录（backend/ 的上一级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = Path(__file__).resolve().parent

# 数据库文件路径（项目根目录下，便于 Tauri 打包后定位）
DB_PATH = PROJECT_ROOT / "data" / "stock_dashboard.db"

# ========== 服务配置 ==========
HOST = "127.0.0.1"
PORT = 8001

# ========== 数据源配置 ==========
# 4 大指数代码（新浪数据源不含北证50，后续可扩展）
INDEX_CODES = {
    "上证指数": "sh000001",
    "深证成指": "sz399001",
    "创业板指": "sz399006",
    "科创50": "sh000688",
}

# 数据模块名称（与 snapshots 表 module_name 字段对应）
MODULE_INDICES = "indices"
MODULE_LIMIT_POOL = "limit_pool"
MODULE_MONEY_FLOW = "money_flow"
MODULE_SECTOR_BREADTH = "sector_breadth"
MODULE_WATCHLIST_QUOTES = "watchlist_quotes"
MODULE_DRAGON_TIGER = "dragon_tiger"

# 所有模块列表（顺序即刷新顺序）
# 说明：py_mini_racer（akshare 内部 V8 引擎）在 watchlist_quotes 长时间高并发调用后
# 容易出现内存池崩溃，导致排在它后面的模块跟着失败。因此把 indices 放在 watchlist_quotes
# 之后，让 indices 不会因为 py_mini_racer 崩溃而失败；watchlist_quotes 自身有 4 阶段兜底，
# 即使 py_mini_racer 崩溃也会返回新浪单票聚合数据。
# dragon_tiger 也用 8 worker 并发拉席位，放在 watchlist_quotes 之后 + indices 之前，
# 与现有模块刷新流水线一致。
ALL_MODULES = [
    MODULE_LIMIT_POOL,
    MODULE_MONEY_FLOW,
    MODULE_SECTOR_BREADTH,
    MODULE_WATCHLIST_QUOTES,
    MODULE_DRAGON_TIGER,
    MODULE_INDICES,
]

# ========== 快照配置 ==========
# 历史快照保留天数
SNAPSHOT_RETENTION_DAYS = 30

# ========== 交易日处理 ==========
# A股市场固定休市日（周6、周日）；节假日需 akshare 交易日历判断
WEEKEND_DAYS = {5, 6}  # Python weekday(): 0=周一 ... 5=周六, 6=周日

# ========== 自选股配置（阶段 2）==========
# 自选股最大数量限制（用户确认：100 只）
WATCHLIST_MAX_SIZE = 100

# 异动阈值默认值（用户确认：涨幅 5% / 跌幅 5% / 换手率 10%）
WATCHLIST_DEFAULT_GAIN_PCT = 5.0      # 涨幅阈值 %
WATCHLIST_DEFAULT_LOSS_PCT = 5.0      # 跌幅阈值 %（绝对值）
WATCHLIST_DEFAULT_TURNOVER_PCT = 10.0  # 换手率阈值 %

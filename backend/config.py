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
PORT = 8000

# ========== 数据源配置 ==========
# 5 大指数代码（akshare 格式，sh/sz/bj 前缀）
INDEX_CODES = {
    "上证指数": "sh000001",
    "深证成指": "sz399001",
    "创业板指": "sz399006",
    "科创50": "sh000688",
    "北证50": "bj899050",
}

# 数据模块名称（与 snapshots 表 module_name 字段对应）
MODULE_INDICES = "indices"
MODULE_LIMIT_POOL = "limit_pool"
MODULE_MONEY_FLOW = "money_flow"
MODULE_SECTOR_BREADTH = "sector_breadth"

# 所有模块列表（顺序即刷新顺序）
ALL_MODULES = [
    MODULE_INDICES,
    MODULE_LIMIT_POOL,
    MODULE_MONEY_FLOW,
    MODULE_SECTOR_BREADTH,
]

# ========== 快照配置 ==========
# 历史快照保留天数
SNAPSHOT_RETENTION_DAYS = 30

# ========== 交易日处理 ==========
# A股市场固定休市日（周6、周日）；节假日需 akshare 交易日历判断
WEEKEND_DAYS = {5, 6}  # Python weekday(): 0=周一 ... 5=周六, 6=周日

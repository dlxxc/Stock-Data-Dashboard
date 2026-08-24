"""SQLite 数据库连接与初始化

使用 Python 标准库 sqlite3，无需额外依赖。
表结构按决策3实现：snapshots 表按模块分条存储 + config 表存配置。
"""
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """获取数据库连接。

    每次调用返回新连接，调用方负责关闭（用 with 语法）。
    row_factory 设置为 Row，支持按列名访问。
    """
    # 确保数据目录存在
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    # 开启外键约束
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """数据库连接上下文管理器。

    用法：
        with get_db() as conn:
            conn.execute("SELECT ...")

    自动提交事务 + 关闭连接。
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """初始化数据库表结构。

    幂等操作：重复调用无副作用。
    在 FastAPI 启动时调用一次。
    """
    with get_db() as conn:
        # 快照表：按模块分条存储
        # 唯一约束 (trade_date, module_name)：同日同模块覆盖旧数据（INSERT OR REPLACE）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL,
                module_name TEXT NOT NULL,
                data_json TEXT NOT NULL,
                status TEXT DEFAULT 'ok',
                error_msg TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                UNIQUE(trade_date, module_name)
            )
        """)

        # 索引：加速按日期查询
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_trade_date
            ON snapshots(trade_date)
        """)

        # 配置表：自选股、AI Key 等（后续阶段用）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # 清理过期快照（保留 SNAPSHOT_RETENTION_DAYS 天）
        from config import SNAPSHOT_RETENTION_DAYS
        conn.execute(
            """
            DELETE FROM snapshots
            WHERE created_at < datetime('now', 'localtime', ?)
            """,
            (f"-{SNAPSHOT_RETENTION_DAYS} days",),
        )

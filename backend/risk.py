"""风险等级计算模块（需求 1.10）

基于快照数据计算风险等级（绿/黄/红）+ 一句话说明。

风险 Top3（按优先级）：
1. 情绪过热：涨停数过多（>50 黄 / >100 红）
2. 情绪过冷：跌停数过多（>15 黄 / >30 红）  ← 用户调整后
3. 资金撤退：行业净流出占比过高（>70% 黄 / >90% 红）
4. 大盘破位：上证指数跌幅过大（>1% 黄 / >2% 红）

综合规则：取所有触发项中最高严重度作为整体风险等级（绿 < 黄 < 红）
"""
from typing import Any

# ========== 风险阈值（方案 B 均衡型 + 用户调整） ==========
# 用户在第 5 次开发启动前确认：跌停数黄线 15、红线 30（原 20/50）
THRESHOLDS = {
    # 情绪过热：涨停数过多
    "limit_up_hot":     {"yellow": 50,  "red": 100},
    # 情绪过冷：跌停数过多（用户调整）
    "limit_down_cold":  {"yellow": 15,  "red": 30},
    # 资金撤退：行业净流出占比（百分比）
    "capital_retreat":  {"yellow": 70,  "red": 90},
    # 大盘破位：上证指数跌幅绝对值（百分比）
    "index_breakdown":  {"yellow": 1.0, "red": 2.0},
}

# 维度优先级（数字越小优先级越高，用于一句话排序）
DIMENSION_PRIORITY = {
    "情绪过热": 1,
    "情绪过冷": 2,
    "资金撤退": 3,
    "大盘破位": 4,
}

# 等级标签
LEVEL_LABEL = {
    "green":  "低风险",
    "yellow": "中风险",
    "red":    "高风险",
}

# 严重度：绿=0, 黄=1, 红=2
_SEVERITY = {"green": 0, "yellow": 1, "red": 2}


def _severity(level: str) -> int:
    return _SEVERITY.get(level, 0)


def _level_from_severity(sev: int) -> str:
    if sev >= 2:
        return "red"
    if sev == 1:
        return "yellow"
    return "green"


def _to_float(val: Any, default: float = 0.0) -> float:
    """安全转 float（akshare 可能返回 None 或字符串）"""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _check_limit_pool(modules: dict[str, Any]) -> list[dict[str, Any]]:
    """检查情绪过热 / 情绪过冷"""
    triggers: list[dict[str, Any]] = []
    limit_pool = modules.get("limit_pool")
    if not isinstance(limit_pool, dict):
        return triggers

    limit_up = limit_pool.get("limit_up") or {}
    limit_down = limit_pool.get("limit_down") or {}
    up_total = int(limit_up.get("total", 0) or 0)
    down_total = int(limit_down.get("total", 0) or 0)

    # 情绪过热
    if up_total > THRESHOLDS["limit_up_hot"]["red"]:
        triggers.append({
            "dimension": "情绪过热", "level": "red",
            "detail": f"涨停 {up_total} 家（>{THRESHOLDS['limit_up_hot']['red']}）",
            "current_value": up_total,
            "yellow_threshold": THRESHOLDS["limit_up_hot"]["yellow"],
            "red_threshold": THRESHOLDS["limit_up_hot"]["red"],
        })
    elif up_total > THRESHOLDS["limit_up_hot"]["yellow"]:
        triggers.append({
            "dimension": "情绪过热", "level": "yellow",
            "detail": f"涨停 {up_total} 家（>{THRESHOLDS['limit_up_hot']['yellow']}）",
            "current_value": up_total,
            "yellow_threshold": THRESHOLDS["limit_up_hot"]["yellow"],
            "red_threshold": THRESHOLDS["limit_up_hot"]["red"],
        })

    # 情绪过冷（用户调整后阈值）
    if down_total > THRESHOLDS["limit_down_cold"]["red"]:
        triggers.append({
            "dimension": "情绪过冷", "level": "red",
            "detail": f"跌停 {down_total} 家（>{THRESHOLDS['limit_down_cold']['red']}）",
            "current_value": down_total,
            "yellow_threshold": THRESHOLDS["limit_down_cold"]["yellow"],
            "red_threshold": THRESHOLDS["limit_down_cold"]["red"],
        })
    elif down_total > THRESHOLDS["limit_down_cold"]["yellow"]:
        triggers.append({
            "dimension": "情绪过冷", "level": "yellow",
            "detail": f"跌停 {down_total} 家（>{THRESHOLDS['limit_down_cold']['yellow']}）",
            "current_value": down_total,
            "yellow_threshold": THRESHOLDS["limit_down_cold"]["yellow"],
            "red_threshold": THRESHOLDS["limit_down_cold"]["red"],
        })

    return triggers


def _check_capital_retreat(modules: dict[str, Any]) -> list[dict[str, Any]]:
    """检查资金撤退（行业净流出占比）"""
    triggers: list[dict[str, Any]] = []
    sb = modules.get("sector_breadth")
    if not isinstance(sb, dict):
        return triggers

    total = int(sb.get("total", 0) or 0)
    down_count = int(sb.get("down_count", 0) or 0)
    if total <= 0:
        return triggers

    retreat_pct = round(down_count / total * 100, 1)
    if retreat_pct > THRESHOLDS["capital_retreat"]["red"]:
        triggers.append({
            "dimension": "资金撤退", "level": "red",
            "detail": f"行业净流出占比 {retreat_pct}%（>{THRESHOLDS['capital_retreat']['red']}%）",
            "current_value": retreat_pct,
            "yellow_threshold": THRESHOLDS["capital_retreat"]["yellow"],
            "red_threshold": THRESHOLDS["capital_retreat"]["red"],
        })
    elif retreat_pct > THRESHOLDS["capital_retreat"]["yellow"]:
        triggers.append({
            "dimension": "资金撤退", "level": "yellow",
            "detail": f"行业净流出占比 {retreat_pct}%（>{THRESHOLDS['capital_retreat']['yellow']}%）",
            "current_value": retreat_pct,
            "yellow_threshold": THRESHOLDS["capital_retreat"]["yellow"],
            "red_threshold": THRESHOLDS["capital_retreat"]["red"],
        })

    return triggers


def _check_index_breakdown(modules: dict[str, Any]) -> list[dict[str, Any]]:
    """检查大盘破位（上证指数跌幅）"""
    triggers: list[dict[str, Any]] = []
    indices_mod = modules.get("indices")
    if not isinstance(indices_mod, dict):
        return triggers

    idx_list = indices_mod.get("indices") or []
    if not isinstance(idx_list, list):
        return triggers

    for idx in idx_list:
        if not isinstance(idx, dict):
            continue
        if idx.get("name") != "上证指数":
            continue
        pct = _to_float(idx.get("pct"))
        drop = abs(min(pct, 0))
        if drop > THRESHOLDS["index_breakdown"]["red"]:
            triggers.append({
                "dimension": "大盘破位", "level": "red",
                "detail": f"上证跌幅 {pct:.2f}%（跌幅>{THRESHOLDS['index_breakdown']['red']}%）",
                "current_value": drop,
                "yellow_threshold": THRESHOLDS["index_breakdown"]["yellow"],
                "red_threshold": THRESHOLDS["index_breakdown"]["red"],
            })
        elif drop > THRESHOLDS["index_breakdown"]["yellow"]:
            triggers.append({
                "dimension": "大盘破位", "level": "yellow",
                "detail": f"上证跌幅 {pct:.2f}%（跌幅>{THRESHOLDS['index_breakdown']['yellow']}%）",
                "current_value": drop,
                "yellow_threshold": THRESHOLDS["index_breakdown"]["yellow"],
                "red_threshold": THRESHOLDS["index_breakdown"]["red"],
            })
        break

    return triggers


def calculate_risk(modules: dict[str, Any]) -> dict[str, Any]:
    """基于快照 modules 计算风险等级。

    Args:
        modules: 快照中的 modules 字段（key 为模块名，value 为模块数据 dict）

    Returns:
        {
            "level": "green" | "yellow" | "red",
            "label": "低风险" | "中风险" | "高风险",
            "summary": "情绪过冷，跌停 23 家；资金撤退，行业净流出占比 81%",
            "triggers": [
                {"dimension": "情绪过冷", "level": "yellow", "detail": "..."},
                ...
            ]
        }
        无任何触发项时：
        {
            "level": "green", "label": "低风险",
            "summary": "市场运行平稳，无明显风险信号",
            "triggers": []
        }
    """
    triggers: list[dict[str, Any]] = []
    triggers.extend(_check_limit_pool(modules))
    triggers.extend(_check_capital_retreat(modules))
    triggers.extend(_check_index_breakdown(modules))

    if not triggers:
        return {
            "level": "green",
            "label": LEVEL_LABEL["green"],
            "summary": "市场运行平稳，无明显风险信号",
            "triggers": [],
        }

    # 综合等级 = 最高严重度
    max_sev = max(_severity(t["level"]) for t in triggers)
    level = _level_from_severity(max_sev)

    # 一句话：按优先级排序拼接
    triggers_sorted = sorted(
        triggers,
        key=lambda t: DIMENSION_PRIORITY.get(t["dimension"], 99),
    )
    summary = "；".join(t["detail"] for t in triggers_sorted)

    return {
        "level": level,
        "label": LEVEL_LABEL[level],
        "summary": summary,
        "triggers": triggers_sorted,
    }

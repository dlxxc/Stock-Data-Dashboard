/**
 * 风险等级相关类型定义
 *
 * 与后端 backend/risk.py + backend/main.py 的 /api/risk 接口返回结构保持一致。
 */

/** 风险等级 */
export type RiskLevel = 'green' | 'yellow' | 'red';

/** 单个风险触发项 */
export interface RiskTrigger {
  /** 风险维度名（如「情绪过热」） */
  dimension: string;
  /** 该项的等级（综合等级取所有触发项最高） */
  level: RiskLevel;
  /** 一句话明细（如「跌停 23 家（>15）」） */
  detail: string;
}

/** GET /api/risk 返回结构 */
export interface RiskAssessment {
  /** 交易日 YYYY-MM-DD */
  trade_date: string;
  /** 综合风险等级 */
  level: RiskLevel;
  /** 中文标签（低风险 / 中风险 / 高风险） */
  label: string;
  /** 一句话总结（已按优先级排序拼接） */
  summary: string;
  /** 触发项列表 */
  triggers: RiskTrigger[];
}

/** 后端在无存档时返回的占位结构 */
export interface EmptyRisk {
  empty: true;
}

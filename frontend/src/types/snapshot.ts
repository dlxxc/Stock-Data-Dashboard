/**
 * 快照相关类型定义
 *
 * 与后端 backend/snapshot.py 返回结构保持一致。
 */

/** 单模块状态：成功 / 失败 */
export type ModuleStatus = 'ok' | 'failed';

/** 单模块数据（任意结构，由各模块自行约定） */
export type ModuleData = Record<string, unknown>;

/** 失败模块信息（get_snapshot_by_date 接口返回） */
export interface FailedModule {
  module: string;
  error: string;
}

/** GET /api/snapshot/latest 返回结构 */
export interface LatestSnapshot {
  /** 交易日 YYYY-MM-DD */
  trade_date: string;
  /** 各模块数据，key 为 module_name */
  modules: Record<string, ModuleData>;
  /** 后端记录的存档时间 */
  fetched_at: string | null;
}

/** 后端在无存档时返回的占位结构 */
export interface EmptySnapshot {
  empty: true;
}

/** GET /api/snapshot/{date} 返回结构 */
export interface DatedSnapshot {
  trade_date: string;
  modules: Record<string, ModuleData>;
  failed_modules: FailedModule[];
  fetched_at: string | null;
}

/** GET /api/snapshot/dates 返回结构 */
export interface SnapshotDates {
  dates: string[];
}

/**
 * 自选股相关类型定义
 */

/** 单条自选股记录（对应后端 WatchItem dataclass） */
export interface WatchItem {
  id: number;
  stock_code: string;
  stock_name: string;
  /** 涨幅阈值 % */
  gain_pct: number;
  /** 跌幅阈值 %（绝对值） */
  loss_pct: number;
  /** 换手率阈值 % */
  turnover_pct: number;
  created_at: string;
  updated_at: string;
}

/** GET /api/watchlist 响应 */
export interface WatchListResponse {
  items: WatchItem[];
  count: number;
  max_size: number;
}

/** POST /api/watchlist 请求 */
export interface WatchItemAddRequest {
  stock_code: string;
  stock_name: string;
  gain_pct?: number;
  loss_pct?: number;
  turnover_pct?: number;
}

/** PATCH /api/watchlist/{id} 请求（只传要改的字段） */
export interface WatchItemUpdateRequest {
  gain_pct?: number;
  loss_pct?: number;
  turnover_pct?: number;
}

// ========== 阶段 2.2 批量设置 ==========

/** PATCH /api/watchlist/batch-thresholds 请求 */
export interface WatchlistBatchUpdateRequest {
  /** 要更新的自选股 id 列表 */
  ids: number[];
  /** 涨幅阈值%，None=不改（reset_to_default=true 时忽略） */
  gain_pct?: number;
  /** 跌幅阈值%，None=不改（reset_to_default=true 时忽略） */
  loss_pct?: number;
  /** 换手率阈值%，None=不改（reset_to_default=true 时忽略） */
  turnover_pct?: number;
  /** True 时忽略 3 个阈值字段，全部重置为 config 默认值 */
  reset_to_default?: boolean;
}

/** PATCH /api/watchlist/batch-thresholds 响应 */
export interface WatchlistBatchUpdateResponse {
  updated: number;
  failed_ids: number[];
}

// ========== 阶段 2.3 异动筛选 ==========

/** 单只票的触发状态（合并 watchlist + watchlist_quotes 快照） */
export interface AlertItem {
  id: number;
  /** 原始代码（原样入库值） */
  code: string;
  /** 规范化 6 位数字代码 */
  code_norm: string;
  name: string;
  /** 最新价 */
  price: number | null;
  /** 涨跌幅%（正数涨/负数跌） */
  pct_chg: number | null;
  /** 换手率% */
  turnover_rate: number | null;
  /** 该股涨幅阈值 */
  gain_pct_threshold: number;
  /** 该股跌幅阈值（绝对值） */
  loss_pct_threshold: number;
  /** 该股换手率阈值 */
  turnover_pct_threshold: number;
  gain_triggered: boolean;
  loss_triggered: boolean;
  turnover_triggered: boolean;
  /** 任意一项触发 */
  any_triggered: boolean;
}

interface AlertGroup {
  count: number;
  items: AlertItem[];
}

/** GET /api/watchlist/alerts 响应 */
export interface WatchlistAlertsResponse {
  trade_date: string;
  /** 自选股总数 */
  watch_count: number;
  /** 有行情数据的数量 */
  quote_count: number;
  /** 触发任意阈值的数量 */
  total_triggered: number;
  groups: {
    gain: AlertGroup;
    loss: AlertGroup;
    turnover: AlertGroup;
  };
  /** 全部自选股（含触发状态，触发的排最前） */
  items: AlertItem[];
  empty: boolean;
  /** 模块失败时附加的错误文案（军规：失败即空） */
  error?: string;
}


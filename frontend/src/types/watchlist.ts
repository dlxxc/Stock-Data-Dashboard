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

/**
 * 自选股接口封装
 *
 * 对应后端 backend/main.py 的自选股相关接口。
 */
import client from './client';
import type {
  WatchItem,
  WatchListResponse,
  WatchItemAddRequest,
  WatchItemUpdateRequest,
  WatchlistBatchUpdateRequest,
  WatchlistBatchUpdateResponse,
  WatchlistAlertsResponse,
} from '@/types/watchlist';

/** GET /api/watchlist —— 列出全部自选股（含当前数量和上限） */
export async function listWatchlist(): Promise<WatchListResponse> {
  const res = await client.get<WatchListResponse>('/watchlist');
  return res.data;
}

/** POST /api/watchlist —— 新增自选股 */
export async function addWatchItem(
  payload: WatchItemAddRequest,
): Promise<WatchItem> {
  const res = await client.post<WatchItem>('/watchlist', payload);
  return res.data;
}

/** DELETE /api/watchlist/{item_id} —— 删除指定自选股 */
export async function deleteWatchItem(itemId: number): Promise<{ deleted: boolean }> {
  const res = await client.delete<{ deleted: boolean }>(`/watchlist/${itemId}`);
  return res.data;
}

/** PATCH /api/watchlist/{item_id} —— 修改阈值 */
export async function updateWatchThresholds(
  itemId: number,
  payload: WatchItemUpdateRequest,
): Promise<WatchItem> {
  const res = await client.patch<WatchItem>(`/watchlist/${itemId}`, payload);
  return res.data;
}

/** PATCH /api/watchlist/batch-thresholds —— 批量设置阈值（含一键重置默认值） */
export async function batchUpdateWatchThresholds(
  payload: WatchlistBatchUpdateRequest,
): Promise<WatchlistBatchUpdateResponse> {
  const res = await client.patch<WatchlistBatchUpdateResponse>(
    '/watchlist/batch-thresholds',
    payload,
  );
  return res.data;
}

/** GET /api/watchlist/alerts —— 自选股异动筛选结果（按阈值计算触发票）
 *
 * @param tradeDate 可选 YYYY-MM-DD；不传则取最新快照
 */
export async function getWatchlistAlerts(
  tradeDate?: string,
): Promise<WatchlistAlertsResponse> {
  const url = tradeDate ? `/watchlist/alerts?trade_date=${encodeURIComponent(tradeDate)}` : '/watchlist/alerts';
  const res = await client.get<WatchlistAlertsResponse>(url);
  return res.data;
}


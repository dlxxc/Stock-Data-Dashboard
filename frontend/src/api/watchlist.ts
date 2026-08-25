/**
 * 自选股接口封装
 *
 * 对应后端 backend/main.py 的 4 个接口。
 */
import client from './client';
import type {
  WatchItem,
  WatchListResponse,
  WatchItemAddRequest,
  WatchItemUpdateRequest,
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

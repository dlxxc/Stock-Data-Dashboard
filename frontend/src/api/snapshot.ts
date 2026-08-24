/**
 * 快照接口封装
 *
 * 对应后端 backend/main.py 的 4 个接口。
 */
import client from './client';
import type {
  EmptySnapshot,
  LatestSnapshot,
  SnapshotDates,
  DatedSnapshot,
} from '@/types/snapshot';

/** GET /api/snapshot/latest —— 读取最后一次成功快照 */
export async function getLatestSnapshot(): Promise<LatestSnapshot | EmptySnapshot> {
  const res = await client.get<LatestSnapshot | EmptySnapshot>('/snapshot/latest');
  return res.data;
}

/** GET /api/snapshot/dates —— 列出所有有存档的日期（最新在前） */
export async function listSnapshotDates(): Promise<string[]> {
  const res = await client.get<SnapshotDates>('/snapshot/dates');
  return res.data.dates;
}

/** GET /api/snapshot/{trade_date} —— 读取指定日期快照 */
export async function getSnapshotByDate(tradeDate: string): Promise<DatedSnapshot | EmptySnapshot> {
  const res = await client.get<DatedSnapshot | EmptySnapshot>(`/snapshot/${tradeDate}`);
  return res.data;
}

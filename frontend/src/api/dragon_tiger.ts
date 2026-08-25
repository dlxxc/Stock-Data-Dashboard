/**
 * 龙虎榜接口封装（阶段 2.4）
 *
 * 对应后端 backend/main.py 的 /api/dragon-tiger 接口。
 */
import client from './client';
import type { DragonTigerApiResponse } from '@/types/dragon_tiger';

/** GET /api/dragon-tiger —— 读取龙虎榜快照（当日上榜股票 + 前 5 买/卖出席位）
 *
 * @param tradeDate 可选 YYYY-MM-DD；不传则取最新快照
 */
export async function getDragonTiger(tradeDate?: string): Promise<DragonTigerApiResponse> {
  const url = tradeDate
    ? `/dragon-tiger?trade_date=${encodeURIComponent(tradeDate)}`
    : '/dragon-tiger';
  const res = await client.get<DragonTigerApiResponse>(url);
  return res.data;
}

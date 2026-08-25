/**
 * 风险等级接口封装
 *
 * 对应后端 backend/main.py 的 GET /api/risk 接口。
 */
import client from './client';
import type { EmptyRisk, RiskAssessment } from '@/types/risk';

/**
 * GET /api/risk —— 计算风险等级
 *
 * @param tradeDate 可选 YYYY-MM-DD；不传则取最新成功快照
 */
export async function getRisk(tradeDate?: string): Promise<RiskAssessment | EmptyRisk> {
  const params = tradeDate ? { trade_date: tradeDate } : undefined;
  const res = await client.get<RiskAssessment | EmptyRisk>('/risk', { params });
  return res.data;
}

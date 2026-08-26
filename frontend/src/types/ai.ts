/**
 * AI 配置相关类型（阶段 3.2 + 3.3）
 */

/** 后端 /api/ai/config 返回的配置状态（永不包含明文 Key） */
export interface AIConfigResponse {
  ok?: boolean;
  has_key: boolean;
  masked_key: string;
}

/** 保存 AI Key 的请求体 */
export interface AiConfigSavePayload {
  api_key: string;
}

/** AI 总结板块项 */
export interface AISector {
  name: string;
  summary: string;
  article_indices: number[];
}

/** AI 总结状态 */
export type AISummaryStatus =
  | 'ok'
  | 'failed'
  | 'not_generated'
  | 'need_key'
  | 'no_news'
  | 'generating';

/** 后端 /api/ai/summary 返回结构 */
export interface AISummaryResponse {
  trade_date: string;
  overview: string;
  sectors: AISector[];
  status: AISummaryStatus;
  error: string;
  generated_at: string;
}

/** 生成 AI 总结请求体 */
export interface AiSummaryGeneratePayload {
  trade_date?: string;
  force?: boolean;
}
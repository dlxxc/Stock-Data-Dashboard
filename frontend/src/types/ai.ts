/**
 * AI 配置相关类型（阶段 3.2）
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
import client from "./client";
import type { AIConfigResponse, AiConfigSavePayload, AISummaryResponse, AiSummaryGeneratePayload } from "@/types/ai";

/** 获取 AI 配置状态（has_key + masked_key，无明文） */
export const getAiConfig = async (): Promise<AIConfigResponse> => {
  const { data } = await client.get<AIConfigResponse>("/ai/config");
  return data;
};

/** 保存（或传空串清空）AI Key */
export const saveAiConfig = async (payload: AiConfigSavePayload): Promise<AIConfigResponse> => {
  const { data } = await client.post<AIConfigResponse>("/ai/config", payload);
  return data;
};

/** 清空 AI Key */
export const clearAiConfig = async (): Promise<AIConfigResponse> => {
  const { data } = await client.delete<AIConfigResponse>("/ai/config");
  return data;
};

/** 读取缓存的 AI 总结（不触发生成） */
export const getAiSummary = async (tradeDate?: string): Promise<AISummaryResponse> => {
  const params = tradeDate ? { trade_date: tradeDate } : {};
  const { data } = await client.get<AISummaryResponse>("/ai/summary", { params });
  return data;
};

/** 生成或强制重新生成 AI 总结（GLM 调用耗时较长，需覆盖默认 10s 超时） */
export const generateAiSummary = async (payload: AiSummaryGeneratePayload = {}): Promise<AISummaryResponse> => {
  const { data } = await client.post<AISummaryResponse>("/ai/summary", payload, {
    timeout: 120000,
  });
  return data;
};
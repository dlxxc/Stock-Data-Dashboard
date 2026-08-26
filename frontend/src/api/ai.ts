import client from "./client";
import type { AIConfigResponse, AiConfigSavePayload } from "@/types/ai";

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
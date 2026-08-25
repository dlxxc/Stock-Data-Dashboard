import client from "./client";
import type { NewsResponse } from "@/types/news";

export const getNews = async (tradeDate?: string): Promise<NewsResponse> => {
  const params = tradeDate ? { trade_date: tradeDate } : {};
  const { data } = await client.get<NewsResponse>("/news", { params });
  return data;
};

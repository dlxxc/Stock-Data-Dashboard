export interface NewsArticle {
  title: string;
  summary: string;
  publish_time: string;
  url: string;
}

export interface NewsResponse {
  trade_date: string;
  total: number;
  articles: NewsArticle[];
  source: "eastmoney" | "sina";
  empty?: boolean;
  error?: string;
}

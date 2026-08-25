/**
 * 龙虎榜模块类型定义（阶段 2.4）
 *
 * 与后端 backend/data_sources/dragon_tiger.py 返回结构保持一致。
 * 字段单位与 akshare stock_lhb_detail_em 一致：净买额/买入额/卖出额/成交额/总成交额/流通市值都是「元」。
 */

/** 单个席位（前 5 买 / 前 5 卖） */
export interface DragonTigerSeat {
  /** 营业部名称 */
  name: string;
  /** 买入金额（元） */
  buy_amount: number | null;
  /** 买入金额占总成交比例（%） */
  buy_pct: number | null;
  /** 卖出金额占总成交比例（%） */
  sell_pct: number | null;
  /** 净额（元，正=净买入，负=净卖出） */
  net: number | null;
}

/** 单只票的买卖席位 */
export interface DragonTigerSeats {
  /** 前 5 买入席位 */
  buy: DragonTigerSeat[];
  /** 前 5 卖出席位 */
  sell: DragonTigerSeat[];
}

/** 上榜股票条目 */
export interface DragonTigerStock {
  /** 6 位股票代码 */
  code: string;
  /** 股票名称 */
  name: string;
  /** 收盘价（元） */
  close: number | null;
  /** 涨跌幅（%） */
  pct_chg: number | null;
  /** 龙虎榜净买额（元，正=净买入，负=净卖出） */
  net_buy: number | null;
  /** 龙虎榜买入额（元） */
  buy_amount: number | null;
  /** 龙虎榜卖出额（元） */
  sell_amount: number | null;
  /** 龙虎榜成交额（元） */
  total_amount: number | null;
  /** 市场总成交额（元） */
  market_total_amount: number | null;
  /** 净买额占总成交比（%） */
  net_buy_pct: number | null;
  /** 成交额占总成交比（%） */
  amount_pct: number | null;
  /** 换手率（%） */
  turnover_rate: number | null;
  /** 流通市值（元） */
  circ_mv: number | null;
  /** 上榜原因 */
  reason: string;
  /** 解读（东财原文） */
  interpretation: string;
  /** 买卖席位详情；后端拉取失败时为 null */
  seats: DragonTigerSeats | null;
}

/** 成功响应 */
export interface DragonTigerResponse {
  trade_date: string;
  total: number;
  stocks: DragonTigerStock[];
  empty?: false;
}

/** 失败 / 未归档响应 */
export interface DragonTigerEmptyResponse {
  empty: true;
  trade_date?: string;
  total?: number;
  stocks?: never[];
  error?: string;
}

/** 后端 GET /api/dragon-tiger 总返回类型（成功 | 失败） */
export type DragonTigerApiResponse = DragonTigerResponse | DragonTigerEmptyResponse;

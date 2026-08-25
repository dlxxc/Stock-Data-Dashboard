/**
 * 各数据模块的具体类型定义
 *
 * 与后端 backend/data_sources/*.py 返回结构保持一致。
 * 替代通用 ModuleData = Record<string, unknown>，让仪表盘组件有强类型保障。
 */

// ---------- indices：5 大指数 ----------
export interface IndexItem {
  /** 指数名称（如「上证指数」） */
  name: string | null;
  /** 代码（如 sh000001） */
  code: string;
  /** 最新点位 */
  value: number;
  /** 涨跌额 */
  change: number;
  /** 涨跌幅（百分比） */
  pct: number;
  /** 成交量（手） */
  volume: number;
  /** 成交额（元） */
  amount: number;
}

export interface IndicesModule {
  indices: IndexItem[];
}

// ---------- limit_pool：涨跌停池 ----------
export interface LimitUpStock {
  name: string;
  code: string;
  /** 涨跌幅（涨停通常接近 10% 或 20%） */
  pct: number;
  /** 最新价 */
  price: number;
  /** 成交额（元） */
  amount: number;
  /** 流通市值 */
  circ_mv: number;
  /** 总市值 */
  total_mv: number;
  /** 连板数（1=首板） */
  times_limit: number;
  /** 首次封板时间 */
  first_limit_time: string;
  /** 最后封板时间 */
  last_limit_time: string;
  /** 炸板次数 */
  break_count: number;
  /** 所属行业 */
  industry: string;
}

export interface LimitDownStock {
  name: string;
  code: string;
  pct: number;
  price: number;
  amount: number;
  industry: string;
}

export interface LimitPoolModule {
  trade_date: string;
  limit_up: { total: number; stocks: LimitUpStock[] };
  limit_down: { total: number; stocks: LimitDownStock[] };
}

// ---------- money_flow：资金流 ----------
export interface IndustryFlowItem {
  name: string;
  /** 主力净流入（元，正为流入，负为流出） */
  net_inflow: number;
  /** 今日涨跌幅 */
  pct: number;
  /** 主力净流入最大股 */
  leader: string;
}

export interface StockFlowItem {
  code: string;
  name: string;
  net_inflow: number;
  pct: number;
  price: number;
}

export interface MoneyFlowModule {
  trade_date: string;
  industry_inflow: IndustryFlowItem[];
  industry_outflow: IndustryFlowItem[];
  stock_inflow: StockFlowItem[];
  stock_outflow: StockFlowItem[];
}

// ---------- sector_breadth：板块涨跌广度 ----------
export interface SectorItem {
  name: string;
  /** 板块涨跌幅 */
  pct: number;
  /** 领涨股票 */
  leader: string;
  /** 领涨股涨跌幅 */
  leader_pct: number;
  /** 总市值（可选，部分数据源不提供） */
  total_mv?: number;
}

export interface SectorBreadthModule {
  trade_date: string;
  total: number;
  up_count: number;
  down_count: number;
  flat_count: number;
  up_pct: number;
  down_pct: number;
  sectors: SectorItem[];
}

// ---------- watchlist_quotes：自选股当日行情 ----------
export interface WatchlistQuote {
  /** 6 位规范代码（不含 sh/sz 前缀） */
  code: string;
  name: string | null;
  /** 最新价（元） */
  price: number | null;
  /** 涨跌幅（百分比，正数涨/负数跌） */
  pct_chg: number | null;
  /** 换手率（百分比） */
  turnover_rate: number | null;
  /** 成交量（手） */
  volume: number | null;
  /** 成交额（元） */
  amount: number | null;
}

export interface WatchlistQuotesModule {
  trade_date: string;
  /** 匹配到的自选股行情数量 */
  total: number;
  /** 当前自选股总数（前端展示对齐用） */
  watch_count: number;
  quotes: WatchlistQuote[];
}

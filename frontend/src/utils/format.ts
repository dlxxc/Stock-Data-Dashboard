/**
 * 数据格式化工具
 *
 * A 股配色铁律：红涨绿跌（与设计系统 CTA 琥珀色无冲突）
 * 金额单位：akshare 返回元，前端展示按数量级转 亿 / 万
 */

/** A 股配色（与 antd 的 colorSuccess/colorError 不同，A股是反的） */
export const STOCK_COLORS = {
  /** 上涨 / 涨停 / 流入 */
  up: '#cf1322',
  upBg: '#fff1f0',
  upBorder: '#ffa39e',
  /** 下跌 / 跌停 / 流出 */
  down: '#389e0d',
  downBg: '#f6ffed',
  downBorder: '#b7eb8f',
  /** 平盘 */
  flat: '#8c8c8c',
  flatBg: '#fafafa',
} as const;

/** 根据涨跌幅返回颜色 */
export function pctColor(pct: number): string {
  if (pct > 0) return STOCK_COLORS.up;
  if (pct < 0) return STOCK_COLORS.down;
  return STOCK_COLORS.flat;
}

/** 涨跌符号：正数前加 +，负数自然带 -，0 不加 */
export function pctSign(val: number): string {
  if (val > 0) return '+';
  return '';
}

/** 金额格式化：元 → 亿 / 万，返回数值 + 单位 */
export function formatAmount(yuan: number): { value: string; unit: string } {
  const abs = Math.abs(yuan);
  if (abs >= 1e8) return { value: (yuan / 1e8).toFixed(2), unit: '亿' };
  if (abs >= 1e4) return { value: (yuan / 1e4).toFixed(2), unit: '万' };
  return { value: yuan.toFixed(0), unit: '元' };
}

/** 金额带正负号格式化（如 +28.70亿 / -23.80亿） */
export function formatSignedAmount(yuan: number): string {
  const { value, unit } = formatAmount(yuan);
  const sign = yuan > 0 ? '+' : '';
  return `${sign}${value}${unit}`;
}

/** 指数点位格式化（千分位 + 2 位小数） */
export function formatIndex(value: number): string {
  return value.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** 普通数字千分位（默认 2 位小数） */
export function formatNumber(n: number, decimals = 2): string {
  return n.toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/** 涨跌幅格式化（带 + 号和 % 后缀） */
export function formatPct(pct: number, decimals = 2): string {
  const sign = pct > 0 ? '+' : '';
  return `${sign}${pct.toFixed(decimals)}%`;
}

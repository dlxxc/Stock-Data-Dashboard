/**
 * 后端模块名 ↔ 中文标签映射
 *
 * 与 backend/config.py 中 ALL_MODULES 保持同步。
 */
export const MODULE_LABELS: Record<string, string> = {
  indices: '4大指数',
  limit_pool: '涨跌停池',
  money_flow: '行业资金流',
  sector_breadth: '板块涨跌广度',
};

/** 模块展示顺序（与后端 ALL_MODULES 一致） */
export const MODULE_ORDER = ['indices', 'limit_pool', 'money_flow', 'sector_breadth'];

/** 取模块中文名，未知模块回退原 key */
export function getModuleLabel(name: string): string {
  return MODULE_LABELS[name] ?? name;
}

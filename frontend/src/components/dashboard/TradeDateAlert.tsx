/**
 * 交易日智能提示（需求 1.8）
 *
 * 三种场景：
 * - 快照日期 = 今天：纯展示「YYYY-MM-DD（周X）当日快照」
 * - 今天是周末（周六/周日）：标注「今日休市，展示最近交易日 YYYY-MM-DD 的存档」
 * - 今天是工作日但快照早于今天：标注「今日为交易日，建议刷新」
 *
 * 不做节假日判断（避免引入节假日表，过度设计）。
 */
import { Alert, Tag } from 'antd';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
import type { ReactNode } from 'react';

dayjs.locale('zh-cn');

interface TradeDateAlertProps {
  /** 交易日 YYYY-MM-DD */
  tradeDate: string;
  /** 存档时间（后端 created_at） */
  fetchedAt: string | null;
}

export default function TradeDateAlert({ tradeDate, fetchedAt }: TradeDateAlertProps) {
  const today = dayjs();
  const snapshotDate = dayjs(tradeDate);
  const isToday = snapshotDate.isSame(today, 'day');
  const isWeekendToday = today.day() === 0 || today.day() === 6;

  const dateStr = snapshotDate.format('YYYY-MM-DD');
  const weekday = snapshotDate.format('ddd');

  let type: 'info' | 'warning' = 'info';
  let message: ReactNode;

  if (isToday) {
    message = (
      <>
        展示 <strong>{dateStr}（{weekday}）</strong> 当日快照
      </>
    );
  } else if (isWeekendToday) {
    type = 'warning';
    message = (
      <>
        今日休市，展示最近交易日 <strong>{dateStr}（{weekday}）</strong> 的存档快照
      </>
    );
  } else {
    type = 'warning';
    message = (
      <>
        今日为交易日，展示 <strong>{dateStr}（{weekday}）</strong> 历史快照，建议刷新获取最新数据
      </>
    );
  }

  return (
    <Alert
      type={type}
      showIcon
      message={message}
      description={
        fetchedAt ? <Tag color="default">存档时间：{fetchedAt}</Tag> : null
      }
    />
  );
}

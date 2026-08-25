/**
 * 历史回看日期选择器（需求 1.6）
 *
 * 职责：
 * - 列出所有有存档的日期，在 DatePicker 上用蓝点高亮
 * - 用户可自由选 30 天内任意日期，选了无存档日期 → 显示「该日无存档」
 * - allowClear：清空选择即返回最新快照
 * - disabledFuture：禁选未来日期
 *
 * 不做节假日判断（军规 7：避免引入节假日表）。
 */
import { Badge, DatePicker, Typography } from 'antd';
import { useEffect, useState } from 'react';
import dayjs, { type Dayjs } from 'dayjs';
import { listSnapshotDates } from '@/api/snapshot';

const { Text } = Typography;

interface HistoryDatePickerProps {
  value: string | null;
  onChange: (date: string | null) => void;
}

export default function HistoryDatePicker({ value, onChange }: HistoryDatePickerProps) {
  const [availableDates, setAvailableDates] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    listSnapshotDates()
      .then((dates) => {
        if (!cancelled) setAvailableDates(new Set(dates));
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const disabledDate = (current: Dayjs | null): boolean => {
    if (!current) return false;
    return current.isAfter(dayjs(), 'day');
  };

  const cellRender = (
    current: Dayjs | string | number,
    info: { type: 'date' | 'month' | 'year' | 'decade'; originNode?: React.ReactNode }
  ): React.ReactNode => {
    if (!current || typeof current === 'string' || typeof current === 'number') {
      return info?.originNode ?? null;
    }

    // date 面板（日粒度）：自定义蓝点高亮
    if (info.type === 'date') {
      const dateStr = current.format('YYYY-MM-DD');
      if (availableDates.has(dateStr)) {
        return (
          <Badge
            dot
            color="#1677ff"
            offset={[-2, 2]}
            style={{ width: '100%', justifyContent: 'center', display: 'inline-flex' }}
          >
            <span>{current.date()}</span>
          </Badge>
        );
      }
      return current.date();
    }

    // 非 date 面板（month / year / decade）：
    // 优先返回 AntD 默认渲染 originNode；没有时自己按类型渲染对应文本，避免空白
    if (info.originNode !== undefined && info.originNode !== null) {
      return info.originNode;
    }
    switch (info.type) {
      case 'month':
        return current.format('MMM');
      case 'year':
        return current.format('YYYY');
      case 'decade':
        return current.format('YYYY');
      default:
        return null;
    }
  };

  const handleChange = (d: Dayjs | null) => {
    onChange(d ? d.format('YYYY-MM-DD') : null);
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <Text type="secondary" style={{ fontSize: 12 }}>历史回看：</Text>
      <DatePicker
        value={value ? dayjs(value) : null}
        onChange={handleChange}
        disabledDate={disabledDate}
        cellRender={cellRender}
        allowClear
        disabled={loading}
        placeholder="选日期回看（30 天内存档）"
        style={{ width: 240 }}
        status={error ? 'error' : undefined}
      />
      {error && (
        <Text type="danger" style={{ fontSize: 11 }}>读取存档日期列表失败：{error}</Text>
      )}
    </div>
  );
}

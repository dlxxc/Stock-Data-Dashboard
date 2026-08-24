/**
 * 行业资金流 TOP5（需求 1.4 - 模块 3）
 *
 * 字段：industry_inflow / industry_outflow 各取 TOP5
 * 字段：name / net_inflow / pct / leader
 * 布局：纯 CSS 双向条形图，红涨流入靠右，绿跌流出靠左
 *
 * 不引入 ECharts：双向条形用 div + 绝对定位即可，与 widget 预览一致。
 */
import { Card, Empty, Typography } from 'antd';
import { formatSignedAmount, STOCK_COLORS } from '@/utils/format';
import type { MoneyFlowModule, IndustryFlowItem } from '@/types/modules';

const { Text } = Typography;

interface IndustryFlowChartProps {
  data: MoneyFlowModule | null;
}

export default function IndustryFlowChart({ data }: IndustryFlowChartProps) {
  if (!data) {
    return (
      <Card title="行业资金流 TOP5" size="small">
        <Empty description="该日无资金流数据" />
      </Card>
    );
  }

  const inflow = data.industry_inflow ?? [];
  const outflow = data.industry_outflow ?? [];

  if (inflow.length === 0 && outflow.length === 0) {
    return (
      <Card title="行业资金流 TOP5" size="small">
        <Empty description="无资金流数据" />
      </Card>
    );
  }

  // 计算标尺：所有 |净额| 的最大值（用于条形宽度比例）
  const maxAbs = Math.max(
    ...inflow.map((x) => Math.abs(x.net_inflow)),
    ...outflow.map((x) => Math.abs(x.net_inflow)),
    1,
  );

  const renderRow = (item: IndustryFlowItem, key: string) => {
    const isInflow = item.net_inflow > 0;
    const color = isInflow ? STOCK_COLORS.up : STOCK_COLORS.down;
    // 半宽 50%，按比例缩放
    const widthPct = (Math.abs(item.net_inflow) / maxAbs) * 50;
    return (
      <div
        key={key}
        style={{
          display: 'grid',
          gridTemplateColumns: '80px 1fr 70px',
          alignItems: 'center',
          gap: 12,
          fontSize: 12,
          padding: '4px 0',
        }}
      >
        <Text ellipsis style={{ color: '#475569' }}>
          {item.name}
        </Text>
        <div
          style={{
            height: 14,
            background: '#f8fafc',
            borderRadius: 999,
            position: 'relative',
            border: '1px solid #e5e7eb',
          }}
        >
          {/* 中线 */}
          <div
            style={{
              position: 'absolute',
              left: '50%',
              top: -2,
              bottom: -2,
              width: 1,
              background: '#d1d5db',
            }}
          />
          {/* 条形 */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              bottom: 0,
              borderRadius: 999,
              background: color,
              ...(isInflow
                ? { left: '50%', width: `${widthPct}%` }
                : { right: '50%', width: `${widthPct}%` }),
            }}
          />
        </div>
        <Text
          style={{
            fontFamily: "'Fira Code', 'JetBrains Mono', monospace",
            color,
            textAlign: 'right',
            fontWeight: 500,
          }}
        >
          {formatSignedAmount(item.net_inflow)}
        </Text>
      </div>
    );
  };

  return (
    <Card
      title="行业资金流 TOP5"
      size="small"
      extra={<Text type="secondary" style={{ fontSize: 11 }}>红=流入 · 绿=流出</Text>}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {inflow.map((item) => renderRow(item, `in-${item.name}`))}
        {outflow.map((item) => renderRow(item, `out-${item.name}`))}
      </div>
    </Card>
  );
}

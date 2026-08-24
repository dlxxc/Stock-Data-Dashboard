/**
 * 4 大指数卡片（需求 1.4 - 模块 1）
 *
 * 字段：name / value / change / pct / amount
 * 布局：4 列响应式网格，每张卡含指数名 + 大字点位 + 涨跌额 + 涨跌幅 + 成交额
 * 配色：红涨绿跌，Fira Code 字体强化数字感
 */
import { Card, Col, Empty, Row, Typography } from 'antd';
import { formatAmount, formatIndex, formatPct, pctColor, pctSign, STOCK_COLORS } from '@/utils/format';
import type { IndicesModule } from '@/types/modules';

const { Text } = Typography;

interface IndexCardsProps {
  data: IndicesModule | null;
}

export default function IndexCards({ data }: IndexCardsProps) {
  if (!data || !data.indices || data.indices.length === 0) {
    return (
      <Card title="4 大指数" size="small">
        <Empty description="该日无指数数据" />
      </Card>
    );
  }

  return (
    <Card title="4 大指数" size="small">
      <Row gutter={[12, 12]}>
        {data.indices.map((idx) => {
          const color = pctColor(idx.pct);
          const { value: amountVal, unit: amountUnit } = formatAmount(idx.amount);
          return (
            <Col key={idx.code} xs={12} sm={8} md={6} lg={4} xl={4}>
              <div
                style={{
                  padding: 12,
                  borderRadius: 8,
                  background: idx.pct >= 0 ? STOCK_COLORS.upBg : STOCK_COLORS.downBg,
                  border: `1px solid ${idx.pct >= 0 ? STOCK_COLORS.upBorder : STOCK_COLORS.downBorder}`,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 4,
                }}
              >
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {idx.name ?? idx.code}
                </Text>
                <div
                  style={{
                    fontFamily: "'Fira Code', 'JetBrains Mono', Consolas, monospace",
                    fontSize: 20,
                    fontWeight: 700,
                    color,
                    lineHeight: '28px',
                    letterSpacing: '-0.5px',
                  }}
                >
                  {formatIndex(idx.value)}
                </div>
                <div
                  style={{
                    display: 'flex',
                    gap: 8,
                    fontFamily: "'Fira Code', 'JetBrains Mono', Consolas, monospace",
                    fontSize: 12,
                  }}
                >
                  <span style={{ color }}>
                    {pctSign(idx.change)}
                    {idx.change.toFixed(2)}
                  </span>
                  <span style={{ color }}>{formatPct(idx.pct)}</span>
                </div>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  成交 {amountVal}{amountUnit}
                </Text>
              </div>
            </Col>
          );
        })}
      </Row>
    </Card>
  );
}

/**
 * 涨跌停统计（需求 1.4 - 模块 2）
 *
 * 1.7 失败处理：data=null + failure → 显示「拉取失败」+ 重试按钮
 */
import { ArrowDownOutlined, ArrowUpOutlined } from '@ant-design/icons';
import { Card, Col, Empty, Row, Statistic, Typography } from 'antd';
import { formatPct, STOCK_COLORS } from '@/utils/format';
import type { LimitPoolModule } from '@/types/modules';
import ModuleFailure, { type ModuleFailureInfo } from './ModuleFailure';

const { Text } = Typography;
const TOP_N = 5;

interface LimitStatsProps {
  data: LimitPoolModule | null;
  failure?: ModuleFailureInfo | null;
  onRetry?: () => void;
}

export default function LimitStats({ data, failure, onRetry }: LimitStatsProps) {
  if (!data) {
    return (
      <Card title="涨跌停统计" size="small">
        {failure ? <ModuleFailure error={failure.error} onRetry={onRetry} /> : <Empty description="该日无涨跌停数据" />}
      </Card>
    );
  }

  const upStocks = data.limit_up?.stocks ?? [];
  const downStocks = data.limit_down?.stocks ?? [];
  const topUp = [...upStocks].sort((a, b) => b.times_limit - a.times_limit).slice(0, TOP_N);
  const topDown = [...downStocks].sort((a, b) => a.pct - b.pct).slice(0, TOP_N);

  return (
    <Card title="涨跌停统计" size="small">
      <Row gutter={[24, 16]}>
        <Col xs={24} md={12}>
          <div style={{ borderBottom: '1px dashed #e5e7eb', paddingBottom: 12, marginBottom: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Text type="secondary">涨停池</Text>
            <Statistic
              value={data.limit_up?.total ?? 0}
              valueStyle={{ color: STOCK_COLORS.up, fontFamily: "'Fira Code', monospace", fontSize: 24, fontWeight: 700 }}
              prefix={<ArrowUpOutlined />}
            />
          </div>
          {topUp.length === 0 ? (
            <Text type="secondary">无涨停股</Text>
          ) : (
            topUp.map((s, i) => (
              <div
                key={s.code}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '20px 1fr auto',
                  alignItems: 'center',
                  gap: 8,
                  padding: '6px 0',
                  borderBottom: i === topUp.length - 1 ? 'none' : '1px dashed #f0f0f0',
                }}
              >
                <Text type="secondary" style={{ fontFamily: "'Fira Code', monospace" }}>{i + 1}</Text>
                <Text ellipsis style={{ fontSize: 13 }}>{s.name}</Text>
                <span
                  style={{
                    color: STOCK_COLORS.up,
                    fontFamily: "'Fira Code', monospace",
                    fontSize: 12,
                    fontWeight: 500,
                    padding: '1px 6px',
                    background: STOCK_COLORS.upBg,
                    borderRadius: 4,
                  }}
                >
                  {Math.round(s.times_limit)}板
                </span>
              </div>
            ))
          )}
        </Col>

        <Col xs={24} md={12}>
          <div style={{ borderBottom: '1px dashed #e5e7eb', paddingBottom: 12, marginBottom: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Text type="secondary">跌停池</Text>
            <Statistic
              value={data.limit_down?.total ?? 0}
              valueStyle={{ color: STOCK_COLORS.down, fontFamily: "'Fira Code', monospace", fontSize: 24, fontWeight: 700 }}
              prefix={<ArrowDownOutlined />}
            />
          </div>
          {topDown.length === 0 ? (
            <Text type="secondary">无跌停股</Text>
          ) : (
            topDown.map((s, i) => (
              <div
                key={s.code}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '20px 1fr auto',
                  alignItems: 'center',
                  gap: 8,
                  padding: '6px 0',
                  borderBottom: i === topDown.length - 1 ? 'none' : '1px dashed #f0f0f0',
                }}
              >
                <Text type="secondary" style={{ fontFamily: "'Fira Code', monospace" }}>{i + 1}</Text>
                <Text ellipsis style={{ fontSize: 13 }}>{s.name}</Text>
                <span
                  style={{
                    color: STOCK_COLORS.down,
                    fontFamily: "'Fira Code', monospace",
                    fontSize: 12,
                    fontWeight: 500,
                    padding: '1px 6px',
                    background: STOCK_COLORS.downBg,
                    borderRadius: 4,
                  }}
                >
                  {formatPct(s.pct)}
                </span>
              </div>
            ))
          )}
        </Col>
      </Row>
    </Card>
  );
}

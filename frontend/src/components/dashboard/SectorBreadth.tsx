/**
 * 板块涨跌广度（需求 1.4 - 模块 4）
 *
 * 字段：total / up_count / down_count / flat_count + sectors[].name/pct
 * 布局：3 个统计卡（上/平/下）+ 进度条 + TOP3 涨幅 / TOP3 跌幅 双栏列表
 */
import { Card, Col, Empty, Row, Typography } from 'antd';
import { formatPct, STOCK_COLORS } from '@/utils/format';
import type { SectorBreadthModule } from '@/types/modules';

const { Text } = Typography;
const TOP_N = 3;

interface SectorBreadthProps {
  data: SectorBreadthModule | null;
}

export default function SectorBreadth({ data }: SectorBreadthProps) {
  if (!data) {
    return (
      <Card title="板块涨跌广度" size="small">
        <Empty description="该日无板块广度数据" />
      </Card>
    );
  }

  const sectors = data.sectors ?? [];
  const total = data.total || sectors.length || 1;
  const topUp = [...sectors].sort((a, b) => b.pct - a.pct).slice(0, TOP_N);
  const topDown = [...sectors].sort((a, b) => a.pct - b.pct).slice(0, TOP_N);

  const upPct = ((data.up_count ?? 0) / total) * 100;
  const flatPct = ((data.flat_count ?? 0) / total) * 100;
  const downPct = ((data.down_count ?? 0) / total) * 100;

  if (sectors.length === 0) {
    return (
      <Card title="板块涨跌广度" size="small">
        <Empty description="无板块数据" />
      </Card>
    );
  }

  return (
    <Card
      title={`板块涨跌广度（共 ${data.total ?? sectors.length} 个行业）`}
      size="small"
    >
      <Row gutter={[12, 12]}>
        <Col xs={8}>
          <div
            style={{
              padding: 12,
              borderRadius: 8,
              border: `1px solid ${STOCK_COLORS.up}`,
              background: STOCK_COLORS.upBg,
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
            }}
          >
            <Text type="secondary" style={{ fontSize: 11 }}>上涨板块</Text>
            <div
              style={{
                fontFamily: "'Fira Code', monospace",
                fontSize: 22,
                fontWeight: 700,
                color: STOCK_COLORS.up,
                lineHeight: '28px',
              }}
            >
              {data.up_count ?? 0}
            </div>
            <Text type="secondary" style={{ fontFamily: "'Fira Code', monospace", fontSize: 11 }}>
              {upPct.toFixed(1)}%
            </Text>
          </div>
        </Col>
        <Col xs={8}>
          <div
            style={{
              padding: 12,
              borderRadius: 8,
              border: `1px solid ${STOCK_COLORS.flat}`,
              background: STOCK_COLORS.flatBg,
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
            }}
          >
            <Text type="secondary" style={{ fontSize: 11 }}>平盘板块</Text>
            <div
              style={{
                fontFamily: "'Fira Code', monospace",
                fontSize: 22,
                fontWeight: 700,
                color: STOCK_COLORS.flat,
                lineHeight: '28px',
              }}
            >
              {data.flat_count ?? 0}
            </div>
            <Text type="secondary" style={{ fontFamily: "'Fira Code', monospace", fontSize: 11 }}>
              {flatPct.toFixed(1)}%
            </Text>
          </div>
        </Col>
        <Col xs={8}>
          <div
            style={{
              padding: 12,
              borderRadius: 8,
              border: `1px solid ${STOCK_COLORS.down}`,
              background: STOCK_COLORS.downBg,
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
            }}
          >
            <Text type="secondary" style={{ fontSize: 11 }}>下跌板块</Text>
            <div
              style={{
                fontFamily: "'Fira Code', monospace",
                fontSize: 22,
                fontWeight: 700,
                color: STOCK_COLORS.down,
                lineHeight: '28px',
              }}
            >
              {data.down_count ?? 0}
            </div>
            <Text type="secondary" style={{ fontFamily: "'Fira Code', monospace", fontSize: 11 }}>
              {downPct.toFixed(1)}%
            </Text>
          </div>
        </Col>
      </Row>

      {/* 进度条 */}
      <div
        style={{
          display: 'flex',
          height: 10,
          borderRadius: 999,
          overflow: 'hidden',
          border: '1px solid #e5e7eb',
          marginTop: 12,
          marginBottom: 12,
          background: '#fafafa',
        }}
      >
        <div style={{ width: `${upPct}%`, background: STOCK_COLORS.up }} />
        <div style={{ width: `${flatPct}%`, background: STOCK_COLORS.flat }} />
        <div style={{ width: `${downPct}%`, background: STOCK_COLORS.down }} />
      </div>

      <Row gutter={24}>
        <Col xs={12}>
          <Text type="secondary" style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5 }}>
            涨幅 TOP3
          </Text>
          {topUp.map((s) => (
            <div
              key={s.name}
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr auto',
                alignItems: 'center',
                gap: 8,
                padding: '6px 0',
                borderBottom: '1px dashed #f0f0f0',
              }}
            >
              <Text ellipsis style={{ fontSize: 13 }}>{s.name}</Text>
              <span style={{ color: STOCK_COLORS.up, fontFamily: "'Fira Code', monospace", fontSize: 12 }}>
                {formatPct(s.pct)}
              </span>
            </div>
          ))}
        </Col>
        <Col xs={12}>
          <Text type="secondary" style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5 }}>
            跌幅 TOP3
          </Text>
          {topDown.map((s) => (
            <div
              key={s.name}
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr auto',
                alignItems: 'center',
                gap: 8,
                padding: '6px 0',
                borderBottom: '1px dashed #f0f0f0',
              }}
            >
              <Text ellipsis style={{ fontSize: 13 }}>{s.name}</Text>
              <span style={{ color: STOCK_COLORS.down, fontFamily: "'Fira Code', monospace", fontSize: 12 }}>
                {formatPct(s.pct)}
              </span>
            </div>
          ))}
        </Col>
      </Row>
    </Card>
  );
}

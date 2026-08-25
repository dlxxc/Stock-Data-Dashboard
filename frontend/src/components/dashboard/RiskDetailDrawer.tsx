import { Drawer, Alert, Card, Progress, List, Typography, Space, Button, Spin } from 'antd';
import { FireOutlined, ExclamationCircleOutlined, DollarOutlined, FallOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import type { RiskAssessment, RiskTrigger, RiskLevel } from '@/types/risk';
import type { SnapshotData } from '@/types/snapshot';
import { getRisk } from '@/api/risk';
import { getSnapshotByDate, getLatestSnapshot } from '@/api/snapshot';
import { formatPct, formatAmount, pctColor } from '@/utils/format';

const { Title, Text } = Typography;

interface RiskDetailDrawerProps {
  open: boolean;
  onClose: () => void;
  tradeDate?: string;
}

interface DimensionCardProps {
  icon: React.ReactNode;
  title: string;
  trigger?: RiskTrigger;
  detailData: React.ReactNode;
  viewAllText: string;
  onViewAll: () => void;
}

const getProgressColor = (level: RiskLevel): string => {
  if (level === 'red') return '#ff4d4f';
  if (level === 'yellow') return '#faad14';
  return '#52c41a';
};

const getProgressPercent = (current: number, yellow: number, red: number): number => {
  const max = red * 1.2;
  return Math.min((current / max) * 100, 100);
};

function DimensionCard({ icon, title, trigger, detailData, viewAllText, onViewAll }: DimensionCardProps) {
  if (!trigger) {
    return (
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space>
            {icon}
            <Title level={5} style={{ margin: 0 }}>{title}</Title>
          </Space>
          <Alert message="未触发" type="success" showIcon />
        </Space>
      </Card>
    );
  }

  const { current_value, yellow_threshold, red_threshold, level, detail } = trigger;
  const percent = getProgressPercent(current_value, yellow_threshold, red_threshold);
  const color = getProgressColor(level);

  return (
    <Card size="small" style={{ marginBottom: 16 }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Space>
          {icon}
          <Title level={5} style={{ margin: 0 }}>{title}</Title>
        </Space>

        <div>
          <Space direction="vertical" style={{ width: '100%' }} size={4}>
            <Text strong style={{ fontSize: 16 }}>
              当前值：
              <span style={{ color }}>{detail}</span>
            </Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              黄线 {yellow_threshold} / 红线 {red_threshold}
            </Text>
            <Progress
              percent={percent}
              strokeColor={color}
              showInfo={false}
              style={{ marginTop: 8 }}
            />
          </Space>
        </div>

        {detailData}

        <Button type="link" size="small" onClick={onViewAll} style={{ padding: 0 }}>
          {viewAllText} →
        </Button>
      </Space>
    </Card>
  );
}

export default function RiskDetailDrawer({ open, onClose, tradeDate }: RiskDetailDrawerProps) {
  const [loading, setLoading] = useState(false);
  const [risk, setRisk] = useState<RiskAssessment | null>(null);
  const [snapshot, setSnapshot] = useState<SnapshotData | null>(null);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (!open) return;

    const loadData = async () => {
      setLoading(true);
      setError('');
      try {
        const [riskData, snapData] = await Promise.all([
          getRisk(tradeDate),
          tradeDate ? getSnapshotByDate(tradeDate) : getLatestSnapshot()
        ]);

        if ('empty' in riskData) {
          setError('风险数据未归档，请先刷新数据');
          setRisk(null);
          setSnapshot(null);
        } else {
          setRisk(riskData);
          setSnapshot(snapData);
        }
      } catch (err: any) {
        setError(err?.message || '加载失败');
        setRisk(null);
        setSnapshot(null);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [open, tradeDate]);

  const getTriggerByDimension = (dimension: string): RiskTrigger | undefined => {
    return risk?.triggers.find(t => t.dimension === dimension);
  };

  const scrollToElement = (elementId: string) => {
    onClose();
    setTimeout(() => {
      const el = document.getElementById(elementId);
      el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 300);
  };

  const renderLimitUpDetail = () => {
    const limitPool = snapshot?.modules?.limit_pool;
    if (!limitPool || typeof limitPool !== 'object' || 'error' in limitPool) {
      return <Alert message="涨停数据未归档" type="warning" showIcon size="small" />;
    }
    const stocks = (limitPool.limit_up?.stocks || []).slice(0, 5);
    if (stocks.length === 0) {
      return <Text type="secondary">今日无涨停</Text>;
    }
    return (
      <List
        size="small"
        dataSource={stocks}
        renderItem={(item: any) => (
          <List.Item>
            <Text>{item.code} {item.name}</Text>
            <Space>
              <Text style={{ color: pctColor(item.pct || 0) }}>
                {formatPct(item.pct || 0)}
              </Text>
              <Text type="secondary">{Math.round(item.times_limit || 0)}板</Text>
            </Space>
          </List.Item>
        )}
      />
    );
  };

  const renderLimitDownDetail = () => {
    const limitPool = snapshot?.modules?.limit_pool;
    if (!limitPool || typeof limitPool !== 'object' || 'error' in limitPool) {
      return <Alert message="跌停数据未归档" type="warning" showIcon size="small" />;
    }
    const stocks = (limitPool.limit_down?.stocks || []).slice(0, 5);
    if (stocks.length === 0) {
      return <Text type="secondary">今日无跌停</Text>;
    }
    return (
      <List
        size="small"
        dataSource={stocks}
        renderItem={(item: any) => (
          <List.Item>
            <Text>{item.code} {item.name}</Text>
            <Text style={{ color: pctColor(item.pct || 0) }}>
              {formatPct(item.pct || 0)}
            </Text>
          </List.Item>
        )}
      />
    );
  };

  const renderCapitalRetreatDetail = () => {
    const moneyFlow = snapshot?.modules?.money_flow;
    if (!moneyFlow || typeof moneyFlow !== 'object' || 'error' in moneyFlow) {
      return <Alert message="资金流数据未归档" type="warning" showIcon size="small" />;
    }
    const outflows = (moneyFlow.net_outflow || []).slice(0, 5);
    if (outflows.length === 0) {
      return <Text type="secondary">暂无净流出数据</Text>;
    }
    return (
      <List
        size="small"
        dataSource={outflows}
        renderItem={(item: any) => (
          <List.Item>
            <Text>{item.name}</Text>
            <Text style={{ color: '#52c41a' }}>
              {formatAmount(item.net_amount || 0)}
            </Text>
          </List.Item>
        )}
      />
    );
  };

  const renderIndexBreakdownDetail = () => {
    const indices = snapshot?.modules?.indices;
    if (!indices || typeof indices !== 'object' || 'error' in indices) {
      return <Alert message="指数数据未归档" type="warning" showIcon size="small" />;
    }
    const indexList = indices.indices || [];
    if (indexList.length === 0) {
      return <Text type="secondary">暂无指数数据</Text>;
    }
    return (
      <List
        size="small"
        dataSource={indexList}
        renderItem={(item: any) => (
          <List.Item>
            <Text>{item.name}</Text>
            <Space>
              <Text style={{ color: pctColor(item.pct || 0) }}>
                {formatPct(item.pct || 0)}
              </Text>
              <Text type="secondary">{item.close?.toFixed(2)}</Text>
            </Space>
          </List.Item>
        )}
      />
    );
  };

  return (
    <Drawer
      title={`${tradeDate || risk?.trade_date || ''} 风险评估详情`}
      placement="right"
      width={680}
      onClose={onClose}
      open={open}
    >
      {loading && (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin tip="加载中..." />
        </div>
      )}

      {error && !loading && (
        <Alert message={error} type="error" showIcon style={{ marginBottom: 16 }} />
      )}

      {!loading && !error && risk && (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Card size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Title level={5} style={{ margin: 0 }}>综合风险等级</Title>
              <Alert
                message={risk.label}
                description={risk.summary || '市场运行平稳，无明显风险信号'}
                type={risk.level === 'red' ? 'error' : risk.level === 'yellow' ? 'warning' : 'success'}
                showIcon
              />
            </Space>
          </Card>

          <DimensionCard
            icon={<FireOutlined style={{ color: '#ff4d4f', fontSize: 18 }} />}
            title="情绪过热（涨停数）"
            trigger={getTriggerByDimension('情绪过热')}
            detailData={renderLimitUpDetail()}
            viewAllText="查看完整涨停榜单"
            onViewAll={() => scrollToElement('limit-stats')}
          />

          <DimensionCard
            icon={<ExclamationCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />}
            title="情绪过冷（跌停数）"
            trigger={getTriggerByDimension('情绪过冷')}
            detailData={renderLimitDownDetail()}
            viewAllText="查看完整跌停榜单"
            onViewAll={() => scrollToElement('limit-stats')}
          />

          <DimensionCard
            icon={<DollarOutlined style={{ color: '#faad14', fontSize: 18 }} />}
            title="资金撤退（行业净流出占比）"
            trigger={getTriggerByDimension('资金撤退')}
            detailData={renderCapitalRetreatDetail()}
            viewAllText="查看完整资金流榜单"
            onViewAll={() => scrollToElement('industry-flow')}
          />

          <DimensionCard
            icon={<FallOutlined style={{ color: '#1890ff', fontSize: 18 }} />}
            title="大盘破位（上证跌幅）"
            trigger={getTriggerByDimension('大盘破位')}
            detailData={renderIndexBreakdownDetail()}
            viewAllText="查看完整指数列表"
            onViewAll={() => scrollToElement('index-cards')}
          />
        </Space>
      )}
    </Drawer>
  );
}

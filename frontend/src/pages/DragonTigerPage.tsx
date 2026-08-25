/**
 * 龙虎榜页（阶段 2.4）
 *
 * 设计要点：
 * - 数据来源：GET /api/dragon-tiger（读快照，不主动刷新）
 * - 表格行展开显示前 5 买 + 前 5 卖出席位
 * - 失败 / 未归档：红色 Alert + 重试按钮（军规 6 不静默）
 * - 历史回看：HistoryDatePicker 选日期 → GET /api/dragon-tiger?trade_date=...
 * - 4 状态分支：loading / error / empty / success
 *
 * 铁律：绝不显示假数据，失败即空 + 红色重试按钮（与军规一致）
 */
import { useCallback, useEffect, useState } from 'react';
import { Alert, Button, Card, Empty, Space, Spin, Table, Tag, Typography } from 'antd';
import { ReloadOutlined, TrophyOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';
import { getDragonTiger } from '@/api/dragon_tiger';
import HistoryDatePicker from '@/components/dashboard/HistoryDatePicker';
import {
  STOCK_COLORS,
  formatAmount,
  formatPct,
  formatSignedAmount,
  pctColor,
  pctSign,
} from '@/utils/format';
import type {
  DragonTigerApiResponse,
  DragonTigerResponse,
  DragonTigerSeat,
  DragonTigerStock,
} from '@/types/dragon_tiger';

const { Title, Text } = Typography;

// ========== 类型定义 ==========

type LoadStatus = 'loading' | 'success' | 'error' | 'empty';

// ========== 工具函数 ==========

/** 净买额带颜色 + 单位 + 正负号 */
function renderNetBuy(value: number | null): JSX.Element {
  if (value === null || value === undefined) {
    return <Text type="secondary">-</Text>;
  }
  const color = value > 0 ? STOCK_COLORS.up : value < 0 ? STOCK_COLORS.down : STOCK_COLORS.flat;
  return (
    <span className="num-mono" style={{ color, fontWeight: 600 }}>
      {formatSignedAmount(value)}
    </span>
  );
}

/** 涨跌幅带颜色 + 正负号 + % */
function renderPct(value: number | null): JSX.Element {
  if (value === null || value === undefined) {
    return <Text type="secondary">-</Text>;
  }
  return (
    <span className="num-mono" style={{ color: pctColor(value), fontWeight: 500 }}>
      {pctSign(value)}
      {formatPct(value)}
    </span>
  );
}

/** 普通金额（不带正负号） */
function renderAmount(value: number | null): JSX.Element {
  if (value === null || value === undefined) {
    return <Text type="secondary">-</Text>;
  }
  const { value: v, unit } = formatAmount(value);
  return <span className="num-mono">{v}{unit}</span>;
}

/** 百分比（不带颜色，中性） */
function renderPercent(value: number | null): JSX.Element {
  if (value === null || value === undefined) {
    return <Text type="secondary">-</Text>;
  }
  return <span className="num-mono">{value.toFixed(2)}%</span>;
}

// ========== 席位表格子组件 ==========

function SeatsTable({
  seats,
  side,
}: {
  seats: DragonTigerSeat[];
  side: 'buy' | 'sell';
}): JSX.Element {
  const isBuy = side === 'buy';
  const columns: ColumnsType<DragonTigerSeat> = [
    {
      title: '#',
      dataIndex: 'idx',
      width: 36,
      render: (_, __, idx) => idx + 1,
    },
    {
      title: '营业部名称',
      dataIndex: 'name',
      ellipsis: true,
      render: (name: string) => <Text style={{ fontSize: 12 }}>{name}</Text>,
    },
    {
      title: isBuy ? '买入金额' : '净额',
      dataIndex: isBuy ? 'buy_amount' : 'net',
      width: 110,
      align: 'right',
      render: (val: number | null) => {
        if (val === null || val === undefined) {
          return <Text type="secondary" style={{ fontSize: 12 }}>-</Text>;
        }
        const { value: v, unit } = formatAmount(val);
        const color = isBuy
          ? STOCK_COLORS.up
          : val > 0
            ? STOCK_COLORS.up
            : val < 0
              ? STOCK_COLORS.down
              : STOCK_COLORS.flat;
        return (
          <span className="num-mono" style={{ color, fontSize: 12 }}>
            {isBuy ? `${v}${unit}` : formatSignedAmount(val)}
          </span>
        );
      },
    },
    {
      title: '占总成交比',
      dataIndex: isBuy ? 'buy_pct' : 'sell_pct',
      width: 90,
      align: 'right',
      render: (val: number | null) => {
        if (val === null || val === undefined) {
          return <Text type="secondary" style={{ fontSize: 12 }}>-</Text>;
        }
        return <span className="num-mono" style={{ fontSize: 12 }}>{val.toFixed(2)}%</span>;
      },
    },
  ];

  return (
    <Table<DragonTigerSeat>
      columns={columns}
      dataSource={seats}
      rowKey={(r, idx) => `${side}-${idx}`}
      pagination={false}
      size="small"
      locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无席位数据" /> }}
      style={{ width: '100%' }}
    />
  );
}

// ========== 主组件 ==========

function DragonTigerPage() {
  const navigate = useNavigate();

  // ---- 视图状态 ----
  const [historyDate, setHistoryDate] = useState<string | null>(null);

  // ---- 数据状态 ----
  const [data, setData] = useState<DragonTigerResponse | null>(null);
  const [loadStatus, setLoadStatus] = useState<LoadStatus>('loading');
  const [loadError, setLoadError] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null); // 后端返回的失败/未归档 error

  // ---- 加载逻辑 ----
  const loadData = useCallback(async (date: string | null) => {
    setLoadStatus('loading');
    setLoadError('');
    setErrorMsg(null);
    try {
      const res: DragonTigerApiResponse = await getDragonTiger(date ?? undefined);
      if (res.empty) {
        setData(null);
        setErrorMsg(res.error ?? null);
        setLoadStatus('empty');
      } else {
        setData(res as DragonTigerResponse);
        setLoadStatus('success');
      }
    } catch (e) {
      const err = e as Error;
      setLoadError(err?.message || '读取龙虎榜快照失败');
      setLoadStatus('error');
    }
  }, []);

  useEffect(() => {
    loadData(historyDate);
  }, [historyDate, loadData]);

  // ---- 表格列定义 ----
  const columns: ColumnsType<DragonTigerStock> = [
    {
      title: '代码',
      dataIndex: 'code',
      width: 90,
      fixed: 'left',
      render: (code: string) => <Text className="num-mono" copyable={false}>{code}</Text>,
    },
    {
      title: '名称',
      dataIndex: 'name',
      width: 110,
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: '收盘价',
      dataIndex: 'close',
      width: 90,
      align: 'right',
      render: (v: number | null) => (v === null ? <Text type="secondary">-</Text> : <span className="num-mono">{v.toFixed(2)}</span>),
    },
    {
      title: '涨跌幅',
      dataIndex: 'pct_chg',
      width: 90,
      align: 'right',
      render: renderPct,
    },
    {
      title: '龙虎榜净买额 ↓',
      dataIndex: 'net_buy',
      width: 140,
      align: 'right',
      render: renderNetBuy,
    },
    {
      title: '买入额',
      dataIndex: 'buy_amount',
      width: 100,
      align: 'right',
      render: renderAmount,
    },
    {
      title: '卖出额',
      dataIndex: 'sell_amount',
      width: 100,
      align: 'right',
      render: renderAmount,
    },
    {
      title: '成交额',
      dataIndex: 'total_amount',
      width: 100,
      align: 'right',
      render: renderAmount,
    },
    {
      title: '换手率',
      dataIndex: 'turnover_rate',
      width: 80,
      align: 'right',
      render: renderPercent,
    },
    {
      title: '净买占比',
      dataIndex: 'net_buy_pct',
      width: 90,
      align: 'right',
      render: renderPercent,
    },
    {
      title: '上榜原因',
      dataIndex: 'reason',
      ellipsis: true,
      render: (reason: string) =>
        reason ? <Text style={{ fontSize: 12 }}>{reason}</Text> : <Text type="secondary">-</Text>,
    },
  ];

  // ---- 行展开：前 5 买 + 前 5 卖 双栏 ----
  const expandedRowRender = (record: DragonTigerStock): JSX.Element => {
    if (!record.seats) {
      return (
        <Alert
          type="warning"
          showIcon
          message="该票席位明细拉取失败"
          description="后端拉取买卖席位时失败或返回空，可能是接口限流。可重新刷新数据再试一次。"
          style={{ margin: 0 }}
        />
      );
    }
    const buySeats = record.seats.buy ?? [];
    const sellSeats = record.seats.sell ?? [];
    return (
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
          <Card
            size="small"
            title={<span style={{ color: STOCK_COLORS.up, fontWeight: 600 }}><TrophyOutlined /> 买入前 5 席位（共 {buySeats.length} 个）</span>}
            style={{ flex: 1, minWidth: 0 }}
            bodyStyle={{ padding: 8 }}
          >
            <SeatsTable seats={buySeats} side="buy" />
          </Card>
          <Card
            size="small"
            title={<span style={{ color: STOCK_COLORS.down, fontWeight: 600 }}><TrophyOutlined /> 卖出前 5 席位（共 {sellSeats.length} 个）</span>}
            style={{ flex: 1, minWidth: 0 }}
            bodyStyle={{ padding: 8 }}
          >
            <SeatsTable seats={sellSeats} side="sell" />
          </Card>
        </div>
        {record.interpretation ? (
          <Alert
            type="info"
            showIcon
            message={<Text style={{ fontSize: 12 }}><strong>东财解读：</strong>{record.interpretation}</Text>}
            style={{ margin: 0 }}
          />
        ) : null}
      </Space>
    );
  };

  // ---- 顶部工具栏 ----
  const toolbar = (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
      <Space>
        <Title level={4} style={{ margin: 0 }}>
          龙虎榜
        </Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          盘后复盘 · 按净买额降序 · 点击行查看前5买卖席位
        </Text>
      </Space>
      <Space>
        <HistoryDatePicker
          value={historyDate}
          onChange={(d) => setHistoryDate(d)}
          onClear={() => setHistoryDate(null)}
        />
        <Button icon={<ReloadOutlined />} onClick={() => loadData(historyDate)} loading={loadStatus === 'loading'}>
          刷新视图
        </Button>
      </Space>
    </div>
  );

  // ---- 4 状态分支渲染 ----

  // ① 加载中
  if (loadStatus === 'loading') {
    return (
      <div>
        {toolbar}
        <Card>
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <Spin tip="正在读取龙虎榜快照..." size="large" />
          </div>
        </Card>
      </div>
    );
  }

  // ② 错误（网络层 / 后端抛 5xx）
  if (loadStatus === 'error') {
    return (
      <div>
        {toolbar}
        <Card>
          <Alert
            type="error"
            showIcon
            message="读取龙虎榜快照失败"
            description={loadError || '未知错误'}
            action={
              <Button size="small" danger icon={<ReloadOutlined />} onClick={() => loadData(historyDate)}>
                重试
              </Button>
            }
          />
        </Card>
      </div>
    );
  }

  // ③ 空状态（无任何存档 / 模块失败 / 模块未归档）
  if (loadStatus === 'empty') {
    return (
      <div>
        {toolbar}
        <Card>
          {errorMsg ? (
            <Alert
              type="warning"
              showIcon
              message="龙虎榜暂不可用"
              description={
                <Space direction="vertical" size={4}>
                  <Text>{errorMsg}</Text>
                  <Space>
                    <Button
                      size="small"
                      type="primary"
                      icon={<ReloadOutlined />}
                      onClick={() => navigate('/')}
                    >
                      前往总览页刷新数据
                    </Button>
                    <Button size="small" icon={<ReloadOutlined />} onClick={() => loadData(historyDate)}>
                      重新读取
                    </Button>
                  </Space>
                </Space>
              }
            />
          ) : (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                <Space direction="vertical" align="center">
                  <Text>暂无龙虎榜存档</Text>
                  <Button type="primary" icon={<ReloadOutlined />} onClick={() => navigate('/')}>
                    前往总览页刷新数据
                  </Button>
                </Space>
              }
            />
          )}
        </Card>
      </div>
    );
  }

  // ④ 成功 → 表格
  const tradeDate = data?.trade_date ?? '';
  const total = data?.total ?? 0;
  const stocks = data?.stocks ?? [];

  return (
    <div>
      {toolbar}
      <Card bodyStyle={{ padding: 0 }}>
        <div style={{ padding: '8px 16px', background: '#fafafa', borderBottom: '1px solid #f0f0f0' }}>
          <Space size="large">
            <Text strong>交易日：</Text>
            <Text className="num-mono">{tradeDate || '-'}</Text>
            <Tag color="blue">上榜 {total} 只</Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>
              数据来源：东方财富龙虎榜（净买额单位：元）
            </Text>
          </Space>
        </div>
        <Table<DragonTigerStock>
          columns={columns}
          dataSource={stocks}
          rowKey={(r) => r.code}
          size="small"
          scroll={{ x: 1100, y: 'calc(100vh - 280px)' }}
          pagination={{
            pageSize: 50,
            showSizeChanger: false,
            showTotal: (t) => `共 ${t} 条`,
            size: 'small',
          }}
          expandable={{
            expandedRowRender,
            rowExpandable: () => true,
          }}
          rowClassName={(record) =>
            (record.net_buy ?? 0) > 0 ? 'lhb-row-net-inflow' : (record.net_buy ?? 0) < 0 ? 'lhb-row-net-outflow' : ''
          }
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={`交易日 ${tradeDate} 无龙虎榜数据`}
              />
            ),
          }}
        />
      </Card>
    </div>
  );
}

export default DragonTigerPage;

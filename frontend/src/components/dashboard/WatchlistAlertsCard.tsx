/**
 * 阶段 2.3 · 总览仪表盘 —— 自选股异动紧凑卡片
 *
 * 位置：RiskLabel 之后，模块卡片之前（放在"情报头版"区，风险与自选股最前一起看）。
 * 风格：紧凑（不占滚动条高度），1 行信息 + Top3 触发标签 + 「查看全部」跳转到 /watchlist。
 *
 * 军规：失败即空（empty/error 分支走 Alert 提示，绝不显示假数据）。
 */
import { useEffect, useState } from 'react';
import { Alert, Button, Card, Skeleton, Space, Tag, Typography } from 'antd';
import {
  RiseOutlined,
  FallOutlined,
  SwapOutlined,
  ThunderboltOutlined,
  ArrowRightOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { getWatchlistAlerts } from '@/api/watchlist';
import type { AlertItem } from '@/types/watchlist';
import { pctColor as colorPct, formatPct } from '@/utils/format';

const { Text } = Typography;

interface Props {
  /** 历史回看日期（YYYY-MM-DD）；不传则取最新快照 */
  tradeDate?: string;
}

function WatchlistAlertsCard({ tradeDate }: Props) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [data, setData] = useState<{
    empty: boolean;
    totalTriggered: number;
    snapshotDate: string;
    watchCount: number;
    gainCount: number;
    lossCount: number;
    turnoverCount: number;
    gainList: AlertItem[];
    lossList: AlertItem[];
    turnoverList: AlertItem[];
    moduleError?: string;
  }>({
    empty: true,
    totalTriggered: 0,
    snapshotDate: '',
    watchCount: 0,
    gainCount: 0,
    lossCount: 0,
    turnoverCount: 0,
    gainList: [],
    lossList: [],
    turnoverList: [],
  });

  async function load() {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await getWatchlistAlerts(tradeDate);
      if (res.empty) {
        setData({
          empty: true,
          totalTriggered: 0,
          snapshotDate: res.trade_date,
          watchCount: res.watch_count,
          gainCount: 0,
          lossCount: 0,
          turnoverCount: 0,
          gainList: [],
          lossList: [],
          turnoverList: [],
          moduleError: res.error,
        });
      } else {
        setData({
          empty: false,
          totalTriggered: res.total_triggered,
          snapshotDate: res.trade_date,
          watchCount: res.watch_count,
          gainCount: res.groups.gain.count,
          lossCount: res.groups.loss.count,
          turnoverCount: res.groups.turnover.count,
          gainList: res.groups.gain.items.slice(0, 3),
          lossList: res.groups.loss.items.slice(0, 3),
          turnoverList: res.groups.turnover.items.slice(0, 3),
        });
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setErrorMsg(msg);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // 依赖 tradeDate：历史回看切换时自动重拉
  }, [tradeDate]);

  // ========== Skeleton ==========
  if (loading) {
    return (
      <Card size="small" style={{ marginBottom: 16 }} bodyStyle={{ padding: '12px 18px' }}>
        <Skeleton active title paragraph={{ rows: 1 }} />
      </Card>
    );
  }

  // ========== 接口级错误（网络/404/500 等）==========
  if (errorMsg) {
    return (
      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
        message="自选股异动读取失败"
        description={errorMsg}
        action={
          <Button size="small" type="primary" ghost icon={<ReloadOutlined />} onClick={() => load()}>
            重试
          </Button>
        }
      />
    );
  }

  // ========== 模块失败 / 空数据 ==========
  if (data.empty) {
    if (data.moduleError) {
      return (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="自选股行情模块拉取失败（未存档）"
          description={data.moduleError}
          action={
            <Space>
              <Button size="small" icon={<ReloadOutlined />} onClick={() => load()}>
                刷新
              </Button>
              <Button size="small" type="primary" onClick={() => navigate('/watchlist')}>
                去管理自选股
              </Button>
            </Space>
          }
        />
      );
    }
    if (data.watchCount === 0) {
      return (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="暂无自选股"
          description="先添加自选股，再点击总览顶部「刷新数据」拉行情，此处会显示异动预警。"
          action={
            <Button size="small" type="primary" onClick={() => navigate('/watchlist')}>
              去添加
            </Button>
          }
        />
      );
    }
    // watchCount > 0 但没行情存档 → 提示去刷新
    return (
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="自选股行情尚未归档"
        description={
          tradeDate
            ? `日期 ${tradeDate} 无自选股行情存档，仅支持回看当日快照生成后的数据。`
            : '点击总览顶部「刷新数据」，系统会同步拉取并归档自选股当日行情。'
        }
        action={
          <Button size="small" type="primary" onClick={() => navigate('/watchlist')}>
            去自选股页
          </Button>
        }
      />
    );
  }

  // ========== 有数据：紧凑卡片 ==========
  const triggeredList = [
    ...data.gainList,
    ...data.lossList.filter((l) => !data.gainList.find((g) => g.id === l.id)),
    ...data.turnoverList.filter(
      (t) => !data.gainList.find((g) => g.id === t.id) && !data.lossList.find((l) => l.id === t.id),
    ),
  ].slice(0, 3);

  const hasTrigger = data.totalTriggered > 0;

  return (
    <Card
      size="small"
      style={{
        marginBottom: 16,
        borderLeft: `4px solid ${hasTrigger ? '#d4380d' : '#52c41a'}`,
        background: hasTrigger ? '#fff2f0' : '#f6ffed',
      }}
      bodyStyle={{ padding: '12px 18px' }}
    >
      <Space size="large" style={{ width: '100%', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
        {/* 左：标题 + 汇总数字 */}
        <div>
          <Space size={8} align="center">
            <ThunderboltOutlined style={{ color: hasTrigger ? '#d4380d' : '#52c41a', fontSize: 16 }} />
            <Text strong style={{ fontSize: 14 }}>自选股异动</Text>
            {data.snapshotDate && (
              <Text type="secondary" style={{ fontSize: 12 }}>· {data.snapshotDate}</Text>
            )}
          </Space>

          <div style={{ marginTop: 6, display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
            <Tag color={data.gainCount > 0 ? 'red' : 'default'} icon={<RiseOutlined />}>
              涨超 <b className="num-mono">{data.gainCount}</b>
            </Tag>
            <Tag color={data.lossCount > 0 ? 'green' : 'default'} icon={<FallOutlined />}>
              跌超 <b className="num-mono">{data.lossCount}</b>
            </Tag>
            <Tag color={data.turnoverCount > 0 ? 'gold' : 'default'} icon={<SwapOutlined />}>
              换手超 <b className="num-mono">{data.turnoverCount}</b>
            </Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>
              共 <b>{data.totalTriggered}</b> / {data.watchCount} 触发
            </Text>
          </div>
        </div>

        {/* 中：Top3 触发预览标签 */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {triggeredList.length === 0 ? (
            <Text type="secondary" style={{ fontSize: 13 }}>
              ✅ 今日无触发 · 持仓情绪平稳
            </Text>
          ) : (
            <Space size={8} wrap style={{ marginTop: 2 }}>
              {triggeredList.map((it) => {
                const color = it.gain_triggered ? 'red' : it.loss_triggered ? 'green' : 'gold';
                return (
                  <Tag key={it.id} color={color} style={{ padding: '2px 8px', fontSize: 12 }}>
                    <b>{it.name}</b>
                    <span className="num-mono" style={{ marginLeft: 4, opacity: 0.85 }}>{it.code}</span>
                    {it.pct_chg !== null && it.pct_chg !== undefined && (
                      <span
                        className="num-mono"
                        style={{
                          marginLeft: 6,
                          color: colorPct(it.pct_chg),
                          fontWeight: 700,
                        }}
                      >
                        {formatPct(it.pct_chg)}
                      </span>
                    )}
                  </Tag>
                );
              })}
              {data.totalTriggered > triggeredList.length && (
                <Tag style={{ padding: '2px 8px', fontSize: 12 }}>
                  +{data.totalTriggered - triggeredList.length} 只...
                </Tag>
              )}
            </Space>
          )}
        </div>

        {/* 右：查看全部 / 刷新 */}
        <Space>
          <Button size="small" icon={<ReloadOutlined />} onClick={() => load()}>
            刷新
          </Button>
          <Button
            size="small"
            type={hasTrigger ? 'primary' : 'default'}
            icon={<ArrowRightOutlined />}
            onClick={() => navigate('/watchlist')}
          >
            查看全部
          </Button>
        </Space>
      </Space>
    </Card>
  );
}

export default WatchlistAlertsCard;

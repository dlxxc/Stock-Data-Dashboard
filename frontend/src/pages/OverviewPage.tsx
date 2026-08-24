/**
 * 总览页（阶段 1 第 3 次开发）
 *
 * 实现需求 M4 / 1.4 / 1.8：
 * - 启动时调 GET /api/snapshot/latest 读取上次快照（不自动刷新，铁律）
 * - 顶部 TradeDateAlert 智能提示交易日（1.8）
 * - 4 大模块仪表盘（1.4）：
 *   - 5 大指数卡片（IndexCards）
 *   - 涨跌停 TOP5 统计（LimitStats）
 *   - 行业资金流 TOP5（IndustryFlowChart）
 *   - 板块涨跌广度（SectorBreadth）
 * - 单模块缺失：模块内显示「该日无此模块数据」占位（不破坏整体布局）
 *
 * 错误处理（军规 6）：
 * - 网络错误：红色错误提示 + 重试按钮，绝不静默
 */
import { useCallback, useEffect, useState } from 'react';
import { Button, Result, Space, Spin } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { getLatestSnapshot } from '@/api/snapshot';
import TradeDateAlert from '@/components/dashboard/TradeDateAlert';
import IndexCards from '@/components/dashboard/IndexCards';
import LimitStats from '@/components/dashboard/LimitStats';
import IndustryFlowChart from '@/components/dashboard/IndustryFlowChart';
import SectorBreadth from '@/components/dashboard/SectorBreadth';
import type {
  IndicesModule,
  LimitPoolModule,
  MoneyFlowModule,
  SectorBreadthModule,
} from '@/types/modules';
import type { LatestSnapshot } from '@/types/snapshot';

/** 加载状态 */
type LoadStatus = 'loading' | 'success' | 'error';

interface State {
  status: LoadStatus;
  data: LatestSnapshot | null;
  error: string;
}

const INITIAL_STATE: State = {
  status: 'loading',
  data: null,
  error: '',
};

function OverviewPage() {
  const [state, setState] = useState<State>(INITIAL_STATE);

  /** 拉取最后一次快照（不自动刷新，仅启动/手动重试时调一次） */
  const loadLatest = useCallback(async () => {
    setState({ status: 'loading', data: null, error: '' });
    try {
      const res = await getLatestSnapshot();
      if ('empty' in res) {
        setState({ status: 'success', data: null, error: '' });
      } else {
        setState({ status: 'success', data: res, error: '' });
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setState({ status: 'error', data: null, error: msg });
    }
  }, []);

  useEffect(() => {
    void loadLatest();
  }, [loadLatest]);

  // ---- 加载中 ----
  if (state.status === 'loading') {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Spin tip="正在读取上次快照..." size="large">
          <div style={{ padding: '30px' }} />
        </Spin>
      </div>
    );
  }

  // ---- 错误 ----
  if (state.status === 'error') {
    return (
      <Result
        status="error"
        title="读取上次快照失败"
        subTitle={state.error}
        extra={
          <Button type="primary" icon={<ReloadOutlined />} onClick={loadLatest}>
            重试
          </Button>
        }
      />
    );
  }

  // ---- 空状态（首次启动或数据库空） ----
  if (state.data === null) {
    return (
      <Result
        status="info"
        title="暂无历史快照"
        subTitle="这是首次启动或数据库为空。下次开发会接入刷新按钮，点刷新即可拉取最新盘后数据"
      />
    );
  }

  // ---- 成功：组装仪表盘 ----
  const { trade_date, modules, fetched_at } = state.data;
  // 各模块独立 cast，缺失时传 null 给组件，组件内部走 Empty 分支
  // 经 unknown 中转：ModuleData 是 Record<string, unknown>，无法直接断言到具体类型
  const indices = (modules.indices ?? null) as unknown as IndicesModule | null;
  const limitPool = (modules.limit_pool ?? null) as unknown as LimitPoolModule | null;
  const moneyFlow = (modules.money_flow ?? null) as unknown as MoneyFlowModule | null;
  const sectorBreadth = (modules.sector_breadth ?? null) as unknown as SectorBreadthModule | null;

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <TradeDateAlert tradeDate={trade_date} fetchedAt={fetched_at} />
      <IndexCards data={indices} />
      <LimitStats data={limitPool} />
      <IndustryFlowChart data={moneyFlow} />
      <SectorBreadth data={sectorBreadth} />
    </Space>
  );
}

export default OverviewPage;

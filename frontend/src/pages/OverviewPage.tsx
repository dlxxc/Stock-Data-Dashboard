/**
 * 总览页（阶段 1 第 4 次开发）
 *
 * 整合三大需求：
 * - 1.5-前端：刷新按钮触发 SSE /api/refresh，done 后重新读 latest snapshot 渲染
 * - 1.6 历史回看：DatePicker 选日期 → GET /api/snapshot/{date}，能拉就拉，拉不到显示提示
 * - 1.7 失败处理：单模块失败即空 + 红色「拉取失败，点此重试」按钮，绝不显示假数据
 *
 * 错误处理（军规 6）：
 * - 网络错误：红色错误提示 + 重试按钮
 * - 部分模块失败：黄色 Alert 警告 + 失败模块卡片显示重试按钮
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Button, Card, Progress, Result, Space, Spin, Typography } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { getLatestSnapshot, getSnapshotByDate } from '@/api/snapshot';
import { refreshData, type RefreshDoneEvent, type RefreshProgressEvent } from '@/api/refresh';
import TradeDateAlert from '@/components/dashboard/TradeDateAlert';
import HistoryDatePicker from '@/components/dashboard/HistoryDatePicker';
import IndexCards from '@/components/dashboard/IndexCards';
import LimitStats from '@/components/dashboard/LimitStats';
import IndustryFlowChart from '@/components/dashboard/IndustryFlowChart';
import SectorBreadth from '@/components/dashboard/SectorBreadth';
import type { ModuleFailureInfo } from '@/components/dashboard/ModuleFailure';
import type {
  IndicesModule,
  LimitPoolModule,
  MoneyFlowModule,
  SectorBreadthModule,
} from '@/types/modules';
import type { DatedSnapshot, LatestSnapshot } from '@/types/snapshot';
import { getModuleLabel } from '@/constants/modules';

const { Text } = Typography;

// ========== 类型定义 ==========

type LoadStatus = 'loading' | 'success' | 'error' | 'empty';

interface RefreshProgress {
  current: number;
  total: number;
  moduleName: string;
  status: RefreshProgressEvent['status'];
}

interface RefreshOutcome {
  okCount: number;
  failCount: number;
  failModules: string[];
}

// ========== 进度条文案与百分比 ==========

function progressText(p: RefreshProgress): { text: string; isError: boolean } {
  const label = getModuleLabel(p.moduleName);
  switch (p.status) {
    case 'start':   return { text: '准备刷新...', isError: false };
    case 'fetching': return { text: `正在拉取 ${label} (${p.current}/${p.total})`, isError: false };
    case 'ok':      return { text: `${label} ✓ 成功`, isError: false };
    case 'failed':  return { text: `${label} ✗ 失败`, isError: true };
    default:        return { text: label, isError: false };
  }
}

function progressPercent(p: RefreshProgress): number {
  if (p.total <= 0) return 0;
  switch (p.status) {
    case 'start':     return 5;
    case 'fetching':  return Math.round(((p.current - 1) / p.total) * 100 + 5);
    case 'ok':
    case 'failed':    return Math.round((p.current / p.total) * 100);
    default:          return 0;
  }
}

// ========== 主组件 ==========

function OverviewPage() {
  // ---- 视图状态 ----
  const [historyDate, setHistoryDate] = useState<string | null>(null);

  // ---- 快照数据 ----
  const [snapshot, setSnapshot] = useState<LatestSnapshot | DatedSnapshot | null>(null);
  const [loadStatus, setLoadStatus] = useState<LoadStatus>('loading');
  const [loadError, setLoadError] = useState('');

  // ---- 刷新状态 ----
  const [refreshing, setRefreshing] = useState(false);
  const [refreshProgress, setRefreshProgress] = useState<RefreshProgress | null>(null);
  const [refreshOutcome, setRefreshOutcome] = useState<RefreshOutcome | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [failedModuleErrors, setFailedModuleErrors] = useState<Record<string, string>>({});

  // ========== 数据加载 ==========

  const loadLatest = useCallback(async () => {
    setLoadStatus('loading');
    setLoadError('');
    try {
      const res = await getLatestSnapshot();
      if ('empty' in res) {
        setSnapshot(null);
        setLoadStatus('empty');
      } else {
        setSnapshot(res);
        setLoadStatus('success');
      }
    } catch (e) {
      setLoadStatus('error');
      setLoadError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  const loadHistory = useCallback(async (date: string) => {
    setLoadStatus('loading');
    setLoadError('');
    try {
      const res = await getSnapshotByDate(date);
      if ('empty' in res) {
        setSnapshot(null);
        setLoadStatus('empty');
      } else {
        setSnapshot(res);
        setLoadStatus('success');
      }
    } catch (e) {
      setLoadStatus('error');
      setLoadError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  // 启动时读最新快照
  useEffect(() => { void loadLatest(); }, [loadLatest]);

  // 历史日期变更 → 加载对应快照
  useEffect(() => {
    if (historyDate === null) return;
    void loadHistory(historyDate);
  }, [historyDate, loadHistory]);

  // ========== 刷新 ==========

  const handleRefresh = useCallback(async () => {
    if (historyDate !== null) {
      setHistoryDate(null);
      void loadLatest();
    }

    setRefreshing(true);
    setRefreshError(null);
    setRefreshOutcome(null);
    setFailedModuleErrors({});
    setRefreshProgress({ current: 0, total: 4, moduleName: '', status: 'start' });

    const collected: Record<string, string> = {};

    await refreshData({
      onProgress: (e: RefreshProgressEvent) => {
        setRefreshProgress({
          current: e.index,
          total: e.total,
          moduleName: e.module,
          status: e.status,
        });
        if (e.status === 'failed' && e.error) {
          collected[e.module] = e.error;
          setFailedModuleErrors({ ...collected });
        }
      },
      onDone: (e: RefreshDoneEvent) => {
        setRefreshOutcome({
          okCount: e.ok_count,
          failCount: e.fail_count,
          failModules: e.fail_modules,
        });
        setRefreshing(false);
        setRefreshProgress(null);
        void loadLatest();
      },
      onError: (err: Error) => {
        setRefreshError(err.message);
        setRefreshing(false);
        setRefreshProgress(null);
      },
    });
  }, [historyDate, loadLatest]);

  // ========== 派生数据 ==========

  /** 各模块失败信息（传给子组件） */
  const failureMap = useMemo(() => {
    const map: Record<string, ModuleFailureInfo> = {};
    if (historyDate !== null) {
      // 历史回看：从 DatedSnapshot.failed_modules 取
      if (snapshot && 'failed_modules' in snapshot) {
        for (const fm of (snapshot as DatedSnapshot).failed_modules ?? []) {
          map[fm.module] = { error: fm.error };
        }
      }
    } else if (refreshOutcome) {
      // 最新视图 + 刚刷新完
      for (const m of refreshOutcome.failModules) {
        map[m] = { error: failedModuleErrors[m] ?? '拉取失败' };
      }
    }
    return map;
  }, [snapshot, historyDate, refreshOutcome, failedModuleErrors]);

  const getFailure = useCallback(
    (moduleName: string): ModuleFailureInfo | null => failureMap[moduleName] ?? null,
    [failureMap],
  );

  /** 今日刷新场景才传 onRetry */
  const retryHandler = historyDate === null ? handleRefresh : undefined;

  /** 进度条派生值 */
  const progressInfo = refreshProgress ? progressText(refreshProgress) : { text: '', isError: false };
  const barPercent = refreshProgress ? progressPercent(refreshProgress) : 0;

  // ========== 渲染：加载中 ==========

  if (loadStatus === 'loading') {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Spin tip="正在读取上次快照..." size="large">
          <div style={{ padding: '30px' }} />
        </Spin>
      </div>
    );
  }

  // ========== 渲染：读取错误 ==========

  if (loadStatus === 'error') {
    return (
      <Result
        status="error"
        title={historyDate ? `读取 ${historyDate} 历史快照失败` : '读取上次快照失败'}
        subTitle={loadError}
        extra={
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={() => (historyDate ? loadHistory(historyDate) : loadLatest())}
          >
            重试
          </Button>
        }
      />
    );
  }

  // ========== 渲染：空状态 ==========

  if (loadStatus === 'empty' || !snapshot) {
    return (
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Toolbar
          historyDate={historyDate}
          onHistoryChange={setHistoryDate}
          refreshing={refreshing}
          refreshProgress={refreshProgress}
          progressInfo={progressInfo}
          barPercent={barPercent}
          onRefresh={handleRefresh}
          refreshError={refreshError}
        />
        <Result
          status="info"
          title={historyDate ? `${historyDate} 该日无存档` : '暂无历史快照'}
          subTitle={
            historyDate
              ? '该日期没有保存的快照数据。可尝试选择其他日期，或点上方「刷新数据」拉取今日数据'
              : '这是首次启动或数据库为空。点击上方「刷新数据」按钮即可拉取最新盘后数据'
          }
          extra={
            !historyDate && (
              <Button type="primary" icon={<ReloadOutlined />} onClick={handleRefresh} loading={refreshing}>
                立即刷新
              </Button>
            )
          }
        />
      </Space>
    );
  }

  // ========== 渲染：成功 ==========

  const { trade_date, modules, fetched_at } = snapshot;

  const indices = (modules.indices ?? null) as unknown as IndicesModule | null;
  const limitPool = (modules.limit_pool ?? null) as unknown as LimitPoolModule | null;
  const moneyFlow = (modules.money_flow ?? null) as unknown as MoneyFlowModule | null;
  const sectorBreadth = (modules.sector_breadth ?? null) as unknown as SectorBreadthModule | null;

  // 刷新结果 Alert
  const partialAlert = refreshOutcome && refreshOutcome.failCount > 0 ? (
    <Alert
      type="warning"
      showIcon
      message={`刷新完成，${refreshOutcome.failCount} 个模块失败：${refreshOutcome.failModules.map(getModuleLabel).join('、')}`}
      description="失败的模块已显示「拉取失败，点此重试」按钮。"
      action={
        <Button size="small" danger icon={<ReloadOutlined />} onClick={handleRefresh} loading={refreshing}>
          重新拉取
        </Button>
      }
    />
  ) : null;

  const successAlert =
    refreshOutcome && refreshOutcome.failCount === 0 ? (
      <Alert
        type="success"
        showIcon
        message={`刷新成功，${refreshOutcome.okCount} 个模块全部拉取成功`}
        closable
        onClose={() => setRefreshOutcome(null)}
      />
    ) : null;

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Toolbar
        historyDate={historyDate}
        onHistoryChange={setHistoryDate}
        refreshing={refreshing}
        refreshProgress={refreshProgress}
        progressInfo={progressInfo}
        barPercent={barPercent}
        onRefresh={handleRefresh}
        refreshError={refreshError}
      />
      {partialAlert}
      {successAlert}
      <TradeDateAlert tradeDate={trade_date} fetchedAt={fetched_at} />
      <IndexCards data={indices} failure={getFailure('indices')} onRetry={retryHandler} />
      <LimitStats data={limitPool} failure={getFailure('limit_pool')} onRetry={retryHandler} />
      <IndustryFlowChart data={moneyFlow} failure={getFailure('money_flow')} onRetry={retryHandler} />
      <SectorBreadth data={sectorBreadth} failure={getFailure('sector_breadth')} onRetry={retryHandler} />
    </Space>
  );
}

// ========== 工具栏子组件 ==========

interface ToolbarProps {
  historyDate: string | null;
  onHistoryChange: (d: string | null) => void;
  refreshing: boolean;
  refreshProgress: RefreshProgress | null;
  progressInfo: { text: string; isError: boolean };
  barPercent: number;
  onRefresh: () => void;
  refreshError: string | null;
}

function Toolbar({
  historyDate, onHistoryChange, refreshing, refreshProgress,
  progressInfo, barPercent, onRefresh, refreshError,
}: ToolbarProps) {
  return (
    <Card size="small" style={{ background: '#fafafa' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <HistoryDatePicker value={historyDate} onChange={onHistoryChange} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 320 }}>
          {refreshing && refreshProgress ? (
            <div style={{ flex: 1, minWidth: 240 }}>
              <Progress percent={barPercent} size="small" status="active" format={(p) => `${p}%`} />
              <Text
                type="secondary"
                style={{ fontSize: 11, color: progressInfo.isError ? '#cf1322' : undefined }}
              >
                {progressInfo.text}
              </Text>
            </div>
          ) : null}
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={onRefresh}
            loading={refreshing}
            disabled={refreshing}
          >
            {refreshing ? '刷新中...' : '刷新数据'}
          </Button>
        </div>
      </div>
      {refreshError ? (
        <Alert
          type="error"
          showIcon
          message="刷新失败"
          description={refreshError}
          style={{ marginTop: 12 }}
          action={
            <Button size="small" danger icon={<ReloadOutlined />} onClick={onRefresh}>
              重试
            </Button>
          }
        />
      ) : null}
    </Card>
  );
}

export default OverviewPage;

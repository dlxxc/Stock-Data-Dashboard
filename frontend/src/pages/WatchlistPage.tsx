/**
 * 自选股管理页面（阶段 2.2 阈值打磨 + 阶段 2.3 异动筛选展示）
 *
 * 2.2 新增：
 * - 单票编辑弹窗：「一键重置为默认值」按钮
 * - 表格多选 + 顶部批量操作（批量设置阈值 / 批量重置默认值）
 * - 批量设置 Modal：3 阈值独立可填（未填=不改），全选/多选
 *
 * 2.3 新增：
 * - 顶部「今日触发异动」区域（Tabs：涨超 / 跌超 / 换手超 / 全部）
 * - 表格行根据触发状态显示高亮条（左 border，红/绿/黄，多重不冲突）
 */
import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  App as AntdApp,
  Button,
  Checkbox,
  Divider,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Space,
  Spin,
  Statistic,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import type { ColumnsType, TableRowSelection } from 'antd/es/table/interface';
import {
  PlusOutlined,
  SettingOutlined,
  DeleteOutlined,
  ReloadOutlined,
  SettingTwoTone,
  ThunderboltOutlined,
  RiseOutlined,
  FallOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import {
  addWatchItem,
  batchUpdateWatchThresholds,
  deleteWatchItem,
  getWatchlistAlerts,
  listWatchlist,
  updateWatchThresholds,
} from '@/api/watchlist';
import type { AlertItem, WatchItem } from '@/types/watchlist';
import { pctColor as colorPct, formatPct } from '@/utils/format';

const { Title } = Typography;

/** 默认阈值常量（与后端 config 保持一致） */
const DEFAULT_GAIN_PCT = 5;
const DEFAULT_LOSS_PCT = 5;
const DEFAULT_TURNOVER_PCT = 10;

/** 从任意 catch 对象提取可读错误信息（6 层兜底，杜绝静默失败） */
function getErrorMessage(e: unknown, fallback = '操作失败'): string {
  if (!e) return fallback;
  const err = e as Record<string, any>;
  if (typeof err.message === 'string' && err.message) return err.message;
  const d1 = err?.response?.data?.detail;
  if (typeof d1 === 'string' && d1) return d1;
  const status = err?.response?.status;
  const statusText = err?.response?.statusText;
  if (typeof statusText === 'string' && statusText) {
    return status ? `请求失败 (${status} ${statusText})` : `请求失败 (${statusText})`;
  }
  const d2 = err?.data?.detail;
  if (typeof d2 === 'string' && d2) return d2;
  try {
    const s = typeof err.toString === 'function' ? err.toString() : String(e);
    if (s && s !== '[object Object]') return s;
  } catch { /* ignore */ }
  try {
    const j = JSON.stringify(e);
    if (j && j !== '{}') return j;
  } catch { /* ignore */ }
  return fallback;
}

/** 判断是不是 antd Form.validateFields 抛的错误（这类错误 antd 表单自己会显示红字，不弹 toast） */
function isAntdFormError(e: unknown): boolean {
  if (!e || typeof e !== 'object') return false;
  const obj = e as Record<string, any>;
  return ('errorFields' in obj && Array.isArray(obj.errorFields)) || 'outOfDate' in obj;
}

/** 把错误打到浏览器控制台，方便定位静默失败真因 */
function logError(tag: string, e: unknown) {
  try {
    // eslint-disable-next-line no-console
    console.error(`[WatchlistPage][${tag}]`, e);
  } catch { /* ignore */ }
}

type AddFormValues = {
  stock_code: string;
  stock_name: string;
  gain_pct?: number;
  loss_pct?: number;
  turnover_pct?: number;
};

type EditFormValues = {
  gain_pct: number;
  loss_pct: number;
  turnover_pct: number;
};

/** 批量设置阈值 Form 值（所有字段可选，未填=不改） */
type BatchEditFormValues = {
  gain_pct?: number;
  loss_pct?: number;
  turnover_pct?: number;
};

type TabKey = 'gain' | 'loss' | 'turnover' | 'all';

function WatchlistPage() {
  const { message: messageApi } = AntdApp.useApp();

  // ============== 自选股列表 state ==============
  const [loading, setLoading] = useState(true);
  const [list, setList] = useState<WatchItem[]>([]);
  const [count, setCount] = useState(0);
  const [maxSize, setMaxSize] = useState(100);

  // ============== 新增弹窗 state ==============
  const [addOpen, setAddOpen] = useState(false);
  const [addSubmitting, setAddSubmitting] = useState(false);
  const [addForm] = Form.useForm<AddFormValues>();

  // ============== 单票编辑弹窗 state ==============
  const [editItem, setEditItem] = useState<WatchItem | null>(null);
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editForm] = Form.useForm<EditFormValues>();

  // ============== 多选 + 批量设置 state ==============
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchEditOpen, setBatchEditOpen] = useState(false);
  const [batchEditSubmitting, setBatchEditSubmitting] = useState(false);
  const [batchEditForm] = Form.useForm<BatchEditFormValues>();

  // ============== 异动筛选 state ==============
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [alerts, setAlerts] = useState<{
    totalTriggered: number;
    tradeDate: string;
    groups: { gain: AlertItem[]; loss: AlertItem[]; turnover: AlertItem[] };
    alertMap: Record<number, AlertItem>;
    empty: boolean;
    errorMsg?: string;
  }>({
    totalTriggered: 0,
    tradeDate: '',
    groups: { gain: [], loss: [], turnover: [] },
    alertMap: {},
    empty: true,
  });
  const [activeTab, setActiveTab] = useState<TabKey>('all');

  // ============== 工具：错误 toast（双保险）==============
  function fireErrorToast(e: unknown, fallback: string) {
    if (isAntdFormError(e)) return;
    const msg = getErrorMessage(e, fallback);
    try {
      const closeFn = messageApi.error(msg, 5);
      const sentinel = `__antd_check_${Date.now()}`;
      // eslint-disable-next-line no-console
      console.error('[WatchlistPage][error-toast] fired', { msg, retType: typeof closeFn });
      setTimeout(() => {
        try {
          const found = document.querySelector('.ant-message, .ant-message-notice, [class*="ant-message"]');
          if (!found) window.alert(msg);
        } catch { window.alert(msg); }
        try { delete (window as any)[sentinel]; } catch { /* ignore */ }
      }, 2000);
    } catch {
      window.alert(msg);
    }
  }

  // ============== 数据加载 ==============
  async function loadData() {
    try {
      setLoading(true);
      const data = await listWatchlist();
      setList(data.items);
      setCount(data.count);
      setMaxSize(data.max_size);
    } catch (e) {
      logError('loadData', e);
      fireErrorToast(e, '加载自选股失败');
    } finally {
      setLoading(false);
    }
  }

  async function loadAlerts() {
    try {
      setAlertsLoading(true);
      const res = await getWatchlistAlerts();
      if (res.empty) {
        setAlerts({
          totalTriggered: 0,
          tradeDate: res.trade_date,
          groups: { gain: [], loss: [], turnover: [] },
          alertMap: {},
          empty: true,
          errorMsg: res.error,
        });
        return;
      }
      const map: Record<number, AlertItem> = {};
      for (const it of res.items) map[it.id] = it;
      setAlerts({
        totalTriggered: res.total_triggered,
        tradeDate: res.trade_date,
        groups: {
          gain: res.groups.gain.items,
          loss: res.groups.loss.items,
          turnover: res.groups.turnover.items,
        },
        alertMap: map,
        empty: false,
      });
    } catch (e) {
      logError('loadAlerts', e);
      fireErrorToast(e, '加载异动筛选结果失败');
    } finally {
      setAlertsLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
    void loadAlerts();
  }, []);

  // ============== 新增 ==============
  function openAddModal() {
    if (count >= maxSize) {
      messageApi.warning(`自选股已达上限 ${maxSize} 只，请先删除后再添加`);
      return;
    }
    addForm.resetFields();
    addForm.setFieldsValue({
      gain_pct: undefined,
      loss_pct: undefined,
      turnover_pct: undefined,
    });
    setAddOpen(true);
  }

  async function handleAddOk() {
    try {
      const values = await addForm.validateFields();
      setAddSubmitting(true);
      const payload: AddFormValues = {
        stock_code: values.stock_code,
        stock_name: values.stock_name,
        ...(values.gain_pct !== undefined && values.gain_pct !== null ? { gain_pct: values.gain_pct } : {}),
        ...(values.loss_pct !== undefined && values.loss_pct !== null ? { loss_pct: values.loss_pct } : {}),
        ...(values.turnover_pct !== undefined && values.turnover_pct !== null ? { turnover_pct: values.turnover_pct } : {}),
      };
      await addWatchItem(payload);
      messageApi.success('添加成功');
      setAddOpen(false);
      addForm.resetFields();
      await loadData();
      await loadAlerts();
    } catch (e) {
      logError('handleAddOk', e);
      fireErrorToast(e, '添加失败');
    } finally {
      setAddSubmitting(false);
    }
  }

  // ============== 单票编辑阈值（含一键重置默认）==============
  function openEditModal(item: WatchItem) {
    setEditItem(item);
    editForm.setFieldsValue({
      gain_pct: item.gain_pct,
      loss_pct: item.loss_pct,
      turnover_pct: item.turnover_pct,
    });
  }

  async function handleEditOk() {
    if (!editItem) return;
    try {
      const values = await editForm.validateFields();
      setEditSubmitting(true);
      await updateWatchThresholds(editItem.id, {
        gain_pct: values.gain_pct,
        loss_pct: values.loss_pct,
        turnover_pct: values.turnover_pct,
      });
      messageApi.success('阈值更新成功');
      setEditItem(null);
      await loadData();
      await loadAlerts();
    } catch (e) {
      logError('handleEditOk', e);
      fireErrorToast(e, '更新失败');
    } finally {
      setEditSubmitting(false);
    }
  }

  /** 一键重置为默认值（当前编辑单票） */
  async function handleResetSingleDefault() {
    if (!editItem) return;
    try {
      setEditSubmitting(true);
      await batchUpdateWatchThresholds({
        ids: [editItem.id],
        reset_to_default: true,
      });
      messageApi.success(`已重置为默认值（涨 ${DEFAULT_GAIN_PCT}% / 跌 ${DEFAULT_LOSS_PCT}% / 换手 ${DEFAULT_TURNOVER_PCT}%）`);
      setEditItem(null);
      await loadData();
      await loadAlerts();
    } catch (e) {
      logError('handleResetSingleDefault', e);
      fireErrorToast(e, '重置默认值失败');
    } finally {
      setEditSubmitting(false);
    }
  }

  // ============== 删除 ==============
  async function handleDelete(itemId: number) {
    try {
      const res = await deleteWatchItem(itemId);
      if (res.deleted) {
        messageApi.success('删除成功');
        setSelectedRowKeys((ks) => ks.filter((k) => k !== itemId));
        await loadData();
        await loadAlerts();
      } else {
        messageApi.warning('记录不存在');
      }
    } catch (e) {
      logError('handleDelete', e);
      fireErrorToast(e, '删除失败');
    }
  }

  // ============== 批量设置 ==============
  function openBatchEdit() {
    if (selectedRowKeys.length === 0) {
      messageApi.warning('请先勾选要设置的自选股');
      return;
    }
    batchEditForm.resetFields();
    setBatchEditOpen(true);
  }

  async function handleBatchEditOk() {
    if (selectedRowKeys.length === 0) {
      messageApi.warning('请先勾选要设置的自选股');
      return;
    }
    try {
      setBatchEditSubmitting(true);
      // 3 个都未填 → 提示用户
      const values = await batchEditForm.validateFields();
      const hasAny = (
        values.gain_pct !== undefined && values.gain_pct !== null
      ) || (
        values.loss_pct !== undefined && values.loss_pct !== null
      ) || (
        values.turnover_pct !== undefined && values.turnover_pct !== null
      );
      if (!hasAny) {
        messageApi.warning('请至少填写一个阈值字段，或点击「批量重置为默认值」');
        return;
      }
      const ids = selectedRowKeys.map((k) => Number(k));
      const res = await batchUpdateWatchThresholds({
        ids,
        gain_pct: values.gain_pct,
        loss_pct: values.loss_pct,
        turnover_pct: values.turnover_pct,
      });
      if (res.failed_ids?.length) {
        messageApi.warning(`成功 ${res.updated} / ${ids.length}，失败 ${res.failed_ids.length} 条`);
      } else {
        messageApi.success(`批量修改成功（${res.updated} 只）`);
      }
      setBatchEditOpen(false);
      batchEditForm.resetFields();
      setSelectedRowKeys([]);
      await loadData();
      await loadAlerts();
    } catch (e) {
      logError('handleBatchEditOk', e);
      fireErrorToast(e, '批量修改失败');
    } finally {
      setBatchEditSubmitting(false);
    }
  }

  /** 批量重置为默认值（对选中项） */
  async function handleBatchResetDefault() {
    if (selectedRowKeys.length === 0) {
      messageApi.warning('请先勾选要重置的自选股');
      return;
    }
    try {
      const ids = selectedRowKeys.map((k) => Number(k));
      const res = await batchUpdateWatchThresholds({ ids, reset_to_default: true });
      messageApi.success(`已批量重置为默认值（${res.updated} 只）`);
      setSelectedRowKeys([]);
      if (batchEditOpen) setBatchEditOpen(false);
      await loadData();
      await loadAlerts();
    } catch (e) {
      logError('handleBatchResetDefault', e);
      fireErrorToast(e, '批量重置失败');
    }
  }

  // ============== 表格多选配置 ==============
  const rowSelection: TableRowSelection<WatchItem> = useMemo(() => ({
    selectedRowKeys,
    onChange: (keys) => setSelectedRowKeys(keys),
    columnWidth: 48,
  }), [selectedRowKeys]);

  // ============== 表格列 ==============
  const columns: ColumnsType<WatchItem> = [
    {
      title: '股票代码',
      dataIndex: 'stock_code',
      key: 'stock_code',
      width: 120,
      render: (v: string) => <span className="num-mono">{v}</span>,
    },
    {
      title: '股票名称',
      dataIndex: 'stock_name',
      key: 'stock_name',
      width: 130,
    },
    {
      title: '当日行情',
      key: 'today_quote',
      width: 220,
      render: (_, record) => {
        const al = alerts.alertMap[record.id];
        if (!al) return <span style={{ color: '#999' }}>—</span>;
        return (
          <Space size={10} direction="vertical" style={{ lineHeight: 1.6 }}>
            <span>
              <span style={{ color: '#999', marginRight: 6 }}>价</span>
              <span className="num-mono">{al.price !== null && al.price !== undefined ? al.price.toFixed(2) : '—'}</span>
              <span style={{ color: '#999', marginLeft: 12, marginRight: 6 }}>涨跌</span>
              <span
                className="num-mono"
                style={{
                  color: colorPct(al.pct_chg ?? 0),
                  fontWeight: 600,
                }}
              >
                {al.pct_chg !== null && al.pct_chg !== undefined ? formatPct(al.pct_chg) : '—'}
              </span>
            </span>
            <span>
              <span style={{ color: '#999', marginRight: 6 }}>换手</span>
              <span className="num-mono">
                {al.turnover_rate !== null && al.turnover_rate !== undefined
                  ? `${al.turnover_rate.toFixed(2)}%`
                  : '—'}
              </span>
              {al.any_triggered && (
                <Tag color="error" style={{ marginLeft: 8 }} icon={<ThunderboltOutlined />}>
                  异动
                </Tag>
              )}
            </span>
          </Space>
        );
      },
    },
    {
      title: '涨幅阈值',
      dataIndex: 'gain_pct',
      key: 'gain_pct',
      width: 110,
      align: 'right',
      render: (v: number, record) => {
        const al = alerts.alertMap[record.id];
        const triggered = !!al?.gain_triggered;
        return (
          <span className="num-mono" style={{ color: triggered ? '#cf1322' : '#cf1322', fontWeight: triggered ? 700 : 400 }}>
            ≥ {v}%{triggered ? ' ✓' : ''}
          </span>
        );
      },
    },
    {
      title: '跌幅阈值',
      dataIndex: 'loss_pct',
      key: 'loss_pct',
      width: 110,
      align: 'right',
      render: (v: number, record) => {
        const al = alerts.alertMap[record.id];
        const triggered = !!al?.loss_triggered;
        return (
          <span className="num-mono" style={{ color: triggered ? '#3f8600' : '#3f8600', fontWeight: triggered ? 700 : 400 }}>
            ≥ {v}%{triggered ? ' ✓' : ''}
          </span>
        );
      },
    },
    {
      title: '换手率阈值',
      dataIndex: 'turnover_pct',
      key: 'turnover_pct',
      width: 120,
      align: 'right',
      render: (v: number, record) => {
        const al = alerts.alertMap[record.id];
        const triggered = !!al?.turnover_triggered;
        return (
          <span className="num-mono" style={{ fontWeight: triggered ? 700 : 400 }}>
            ≥ {v}%{triggered ? ' ✓' : ''}
          </span>
        );
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<SettingOutlined />}
            onClick={() => openEditModal(record)}
          >
            阈值
          </Button>
          <Popconfirm
            title={`确定删除「${record.stock_name}」？`}
            description="删除后不可恢复"
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
            onConfirm={() => handleDelete(record.id)}
          >
            <Button
              type="link"
              danger
              size="small"
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // ============== 今日触发 Tabs 渲染 ==============
  function renderTriggerList(items: AlertItem[]) {
    if (items.length === 0) {
      return (
        <div style={{ padding: '12px 8px', color: '#999', fontSize: 13 }}>
          ✅ 暂无触发
        </div>
      );
    }
    return (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, padding: '8px 4px 4px' }}>
        {items.map((it) => (
          <Tag
            key={it.id}
            color={
              it.gain_triggered ? 'red' :
              it.loss_triggered ? 'green' : 'gold'
            }
            style={{ padding: '4px 10px', fontSize: 13 }}
          >
            <b>{it.name}</b>
            <span className="num-mono" style={{ marginLeft: 6, opacity: 0.85 }}>
              {it.code}
            </span>
            {it.pct_chg !== null && it.pct_chg !== undefined && (
              <span
                className="num-mono"
                style={{
                  marginLeft: 6,
                  color: colorPct(it.pct_chg),
                  fontWeight: 600,
                }}
              >
                {formatPct(it.pct_chg)}
              </span>
            )}
            {it.turnover_rate !== null && it.turnover_rate !== undefined && it.turnover_triggered && !it.gain_triggered && !it.loss_triggered && (
              <span className="num-mono" style={{ marginLeft: 6 }}>
                换手 {it.turnover_rate.toFixed(2)}%
              </span>
            )}
          </Tag>
        ))}
      </div>
    );
  }

  const triggeredTabItems = [
    {
      key: 'all' as TabKey,
      label: (
        <span>
          <ThunderboltOutlined style={{ color: '#d4380d' }} /> 全部触发
          <Tag color="red" style={{ marginLeft: 6 }}>{alerts.totalTriggered}</Tag>
        </span>
      ),
      children: (() => {
        const all = [
          ...alerts.groups.gain,
          ...alerts.groups.loss.filter((x) => !alerts.groups.gain.find((g) => g.id === x.id)),
          ...alerts.groups.turnover.filter(
            (x) => !alerts.groups.gain.find((g) => g.id === x.id) && !alerts.groups.loss.find((l) => l.id === x.id),
          ),
        ];
        return renderTriggerList(all);
      })(),
    },
    {
      key: 'gain' as TabKey,
      label: (
        <span>
          <RiseOutlined style={{ color: '#cf1322' }} /> 涨超
          <Tag color="red" style={{ marginLeft: 6 }}>{alerts.groups.gain.length}</Tag>
        </span>
      ),
      children: renderTriggerList(alerts.groups.gain),
    },
    {
      key: 'loss' as TabKey,
      label: (
        <span>
          <FallOutlined style={{ color: '#3f8600' }} /> 跌超
          <Tag color="green" style={{ marginLeft: 6 }}>{alerts.groups.loss.length}</Tag>
        </span>
      ),
      children: renderTriggerList(alerts.groups.loss),
    },
    {
      key: 'turnover' as TabKey,
      label: (
        <span>
          <SwapOutlined style={{ color: '#d48806' }} /> 换手超
          <Tag color="gold" style={{ marginLeft: 6 }}>{alerts.groups.turnover.length}</Tag>
        </span>
      ),
      children: renderTriggerList(alerts.groups.turnover),
    },
  ];

  // ============== 表格行高亮（触发状态，左边框）==============
  function rowClassName(_record: WatchItem): string {
    return 'watchlist-row';
  }

  const rowBorderStyle = (record: WatchItem): React.CSSProperties => {
    const al = alerts.alertMap[record.id];
    if (!al?.any_triggered) return {};
    // 多重触发：优先涨（红） > 跌（绿） > 换手（黄）
    const color = al.gain_triggered ? '#cf1322' : al.loss_triggered ? '#3f8600' : '#d48806';
    return {
      borderLeft: `4px solid ${color}`,
      background: `${color}10`,
    };
  };

  return (
    <div style={{ maxWidth: 1160, margin: '0 auto' }}>
      {/* 标题栏 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-end',
          marginBottom: 20,
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div>
          <Title level={3} style={{ margin: 0 }}>
            自选股管理
          </Title>
          <div style={{ color: '#666', fontSize: 13, marginTop: 4 }}>
            最多 {maxSize} 只 · 新增时不填阈值将使用默认值（涨 {DEFAULT_GAIN_PCT}% / 跌 {DEFAULT_LOSS_PCT}% / 换手 {DEFAULT_TURNOVER_PCT}%）
          </div>
        </div>
        <Space size={16}>
          <Statistic
            title="当前数量"
            value={count}
            suffix={`/ ${maxSize}`}
            valueStyle={{ fontSize: 18 }}
          />
          <Button
            type="primary"
            icon={<PlusOutlined />}
            disabled={count >= maxSize}
            onClick={openAddModal}
          >
            添加自选股
          </Button>
        </Space>
      </div>

      {/* 数量接近上限提示 */}
      {count > 0 && count >= maxSize - 3 && count < maxSize && (
        <Alert type="warning" showIcon message={`已添加 ${count}/${maxSize} 只，接近上限`} style={{ marginBottom: 16 }} />
      )}
      {count >= maxSize && (
        <Alert type="error" showIcon message={`已达上限 ${maxSize} 只，无法继续添加`} style={{ marginBottom: 16 }} />
      )}

      {/* ====================== 2.3 今日触发异动 Tabs 区 ====================== */}
      <Spin spinning={alertsLoading} tip="加载异动筛选结果...">
        <div
          style={{
            border: '1px solid #f0f0f0',
            borderRadius: 8,
            padding: '8px 16px 12px',
            marginBottom: 18,
            background: alerts.totalTriggered > 0 ? '#fff2f0' : '#fafafa',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 4,
              flexWrap: 'wrap',
              gap: 8,
            }}
          >
            <div style={{ fontSize: 14, fontWeight: 600 }}>
              <ThunderboltOutlined style={{ color: alerts.totalTriggered > 0 ? '#d4380d' : '#8c8c8c', marginRight: 6 }} />
              今日触发异动
              {alerts.tradeDate && (
                <span style={{ color: '#8c8c8c', fontWeight: 400, fontSize: 12, marginLeft: 10 }}>
                  数据日期 {alerts.tradeDate}
                </span>
              )}
            </div>
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => loadAlerts()}
            >
              刷新
            </Button>
          </div>

          {alerts.errorMsg && (
            <Alert
              type="error"
              showIcon
              style={{ margin: '8px 0' }}
              message={`行情模块失败：${alerts.errorMsg}`}
              description="请返回「总览」点击顶部「刷新数据」重新拉取自选股行情后再试"
            />
          )}
          {alerts.empty && !alerts.errorMsg && (
            <Alert
              type="info"
              showIcon
              style={{ margin: '8px 0' }}
              message={count === 0 ? '暂无自选股，请先添加' : '暂无自选股行情数据'}
              description={
                count === 0
                  ? '添加后刷新总览数据即可做异动筛选'
                  : '请先在「总览」页面点击「刷新数据」，系统会同步拉取自选股当日行情用于筛选'
              }
            />
          )}

          {!alerts.empty && (
            <Tabs
              activeKey={activeTab}
              onChange={(k) => setActiveTab(k as TabKey)}
              items={triggeredTabItems}
              size="small"
              style={{ marginTop: 4 }}
            />
          )}
        </div>
      </Spin>

      {/* ====================== 批量操作工具条 ====================== */}
      {count > 0 && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 8,
            padding: '8px 12px',
            marginBottom: 12,
            border: '1px dashed #d9d9d9',
            borderRadius: 6,
            background: '#fafafa',
          }}
        >
          <Space size={8} wrap>
            <Checkbox
              checked={list.length > 0 && selectedRowKeys.length === list.length}
              indeterminate={selectedRowKeys.length > 0 && selectedRowKeys.length < list.length}
              onChange={(e) => {
                if (e.target.checked) {
                  setSelectedRowKeys(list.map((x) => x.id));
                } else {
                  setSelectedRowKeys([]);
                }
              }}
            >
              全选
            </Checkbox>
            <span style={{ color: '#8c8c8c', fontSize: 12 }}>
              已选 <b>{selectedRowKeys.length}</b> / {count}
            </span>
            {selectedRowKeys.length > 0 && (
              <Button
                size="small"
                onClick={() => setSelectedRowKeys([])}
              >
                清空
              </Button>
            )}
          </Space>

          <Space size={8} wrap>
            <Button
              size="small"
              icon={<SettingTwoTone />}
              disabled={selectedRowKeys.length === 0}
              onClick={openBatchEdit}
            >
              批量设置阈值
            </Button>
            <Popconfirm
              title={`确定将已选 ${selectedRowKeys.length} 只票的阈值重置为默认值？`}
              description={`涨 ${DEFAULT_GAIN_PCT}% / 跌 ${DEFAULT_LOSS_PCT}% / 换手 ${DEFAULT_TURNOVER_PCT}%`}
              okText="重置"
              cancelText="取消"
              disabled={selectedRowKeys.length === 0}
              onConfirm={handleBatchResetDefault}
            >
              <Button
                size="small"
                icon={<ReloadOutlined />}
                disabled={selectedRowKeys.length === 0}
              >
                批量重置默认值
              </Button>
            </Popconfirm>
          </Space>
        </div>
      )}

      {/* 表格 */}
      <Spin spinning={loading}>
        <Table<WatchItem>
          rowKey="id"
          columns={columns}
          dataSource={list}
          rowSelection={count > 0 ? rowSelection : undefined}
          locale={{ emptyText: '暂无自选股，点击右上角「添加自选股」开始管理' }}
          pagination={{
            pageSize: 50,
            showSizeChanger: false,
            hideOnSinglePage: true,
          }}
          scroll={{ x: 1000 }}
          rowClassName={rowClassName}
          onRow={(record) => ({
            style: rowBorderStyle(record),
          })}
        />
      </Spin>

      {/* 底部说明 Tag */}
      <div style={{ marginTop: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <Tag color="red">涨幅阈值：当日涨幅 ≥ 该值即视为异动</Tag>
        <Tag color="green">跌幅阈值：当日跌幅绝对值 ≥ 该值即视为异动</Tag>
        <Tag color="gold">换手率阈值：当日换手率 ≥ 该值即视为异动</Tag>
        <Tag>行情来源：刷新总览数据时统一拉取并归档</Tag>
      </div>

      {/* ========== 新增弹窗 ========== */}
      <Modal
        title="添加自选股"
        open={addOpen}
        onCancel={() => setAddOpen(false)}
        onOk={handleAddOk}
        confirmLoading={addSubmitting}
        okText="添加"
        cancelText="取消"
        destroyOnClose
      >
        <Form<AddFormValues>
          form={addForm}
          layout="vertical"
          preserve={false}
          style={{ marginTop: 8 }}
        >
          <Form.Item
            name="stock_code"
            label="股票代码"
            rules={[{ required: true, message: '请输入股票代码' }]}
            style={{ marginBottom: 14 }}
          >
            <Input placeholder="如 600519 或 sh600519" maxLength={12} />
          </Form.Item>
          <Form.Item
            name="stock_name"
            label="股票名称"
            rules={[{ required: true, message: '请输入股票名称' }]}
            style={{ marginBottom: 14 }}
          >
            <Input placeholder="如 贵州茅台" maxLength={16} />
          </Form.Item>
          <div style={{
            border: '1px solid #f0f0f0',
            borderRadius: 6,
            padding: '12px 16px',
            background: '#fafafa',
            marginBottom: 8,
          }}>
            <div style={{ color: '#666', fontSize: 12, marginBottom: 12 }}>
              阈值配置（不填则使用默认值：<b>涨 {DEFAULT_GAIN_PCT}% / 跌 {DEFAULT_LOSS_PCT}% / 换手 {DEFAULT_TURNOVER_PCT}%</b>）
            </div>
            <Space.Compact block style={{ gap: 8, flexWrap: 'wrap' }}>
              <Form.Item name="gain_pct" label="涨幅阈值 %" style={{ margin: 0, flex: 1, minWidth: 180 }}>
                <InputNumber min={0.1} max={99} step={0.5} placeholder={`默认 ${DEFAULT_GAIN_PCT}`} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="loss_pct" label="跌幅阈值 %" style={{ margin: 0, flex: 1, minWidth: 180 }}>
                <InputNumber min={0.1} max={99} step={0.5} placeholder={`默认 ${DEFAULT_LOSS_PCT}`} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="turnover_pct" label="换手率阈值 %" style={{ margin: 0, flex: 1, minWidth: 180 }}>
                <InputNumber min={0.1} max={99} step={0.5} placeholder={`默认 ${DEFAULT_TURNOVER_PCT}`} style={{ width: '100%' }} />
              </Form.Item>
            </Space.Compact>
          </div>
        </Form>
      </Modal>

      {/* ========== 编辑阈值弹窗（含一键重置默认） ========== */}
      <Modal
        title={editItem ? `编辑阈值 · ${editItem.stock_name}（${editItem.stock_code}）` : '编辑阈值'}
        open={!!editItem}
        onCancel={() => setEditItem(null)}
        onOk={handleEditOk}
        confirmLoading={editSubmitting}
        okText="保存"
        cancelText="取消"
        destroyOnClose
        footer={(_, { OkBtn, CancelBtn }) => (
          <>
            <Popconfirm
              title="确定重置为默认值？"
              description={`涨 ${DEFAULT_GAIN_PCT}% / 跌 ${DEFAULT_LOSS_PCT}% / 换手 ${DEFAULT_TURNOVER_PCT}%`}
              okText="重置"
              cancelText="取消"
              onConfirm={handleResetSingleDefault}
            >
              <Button icon={<ReloadOutlined />} loading={editSubmitting}>
                一键重置默认值
              </Button>
            </Popconfirm>
            <div style={{ flex: 1 }} />
            <CancelBtn />
            <OkBtn />
          </>
        )}
      >
        <Form<EditFormValues>
          form={editForm}
          layout="vertical"
          preserve={false}
          style={{ marginTop: 8 }}
        >
          <Form.Item name="gain_pct" label="涨幅阈值 %" rules={[{ required: true, message: '请输入涨幅阈值' }]}>
            <InputNumber min={0.1} max={99} step={0.5} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="loss_pct" label="跌幅阈值 %（绝对值）" rules={[{ required: true, message: '请输入跌幅阈值' }]}>
            <InputNumber min={0.1} max={99} step={0.5} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="turnover_pct" label="换手率阈值 %" rules={[{ required: true, message: '请输入换手率阈值' }]}>
            <InputNumber min={0.1} max={99} step={0.5} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* ========== 批量设置阈值弹窗 ========== */}
      <Modal
        title={`批量设置阈值（已选 ${selectedRowKeys.length} 只）`}
        open={batchEditOpen}
        onCancel={() => setBatchEditOpen(false)}
        onOk={handleBatchEditOk}
        confirmLoading={batchEditSubmitting}
        okText="批量修改"
        cancelText="取消"
        destroyOnClose
        footer={(_, { OkBtn, CancelBtn }) => (
          <>
            <Popconfirm
              title={`确定将已选 ${selectedRowKeys.length} 只票全部重置为默认值？`}
              description={`涨 ${DEFAULT_GAIN_PCT}% / 跌 ${DEFAULT_LOSS_PCT}% / 换手 ${DEFAULT_TURNOVER_PCT}%`}
              okText="全部重置"
              cancelText="取消"
              onConfirm={async () => {
                await handleBatchResetDefault();
              }}
            >
              <Button icon={<ReloadOutlined />} loading={batchEditSubmitting}>
                全部重置为默认值
              </Button>
            </Popconfirm>
            <div style={{ flex: 1 }} />
            <CancelBtn />
            <OkBtn />
          </>
        )}
      >
        <div style={{
          border: '1px solid #f0f0f0',
          borderRadius: 6,
          padding: '12px 16px',
          background: '#fafafa',
          marginTop: 4,
          marginBottom: 8,
        }}>
          <div style={{ color: '#666', fontSize: 12, marginBottom: 12 }}>
            已选 <b>{selectedRowKeys.length}</b> 只票 · 只填需要改的阈值（未填的字段保持不变）
          </div>
          <Form<BatchEditFormValues>
            form={batchEditForm}
            layout="vertical"
            preserve={false}
          >
            <Space.Compact block style={{ gap: 8, flexWrap: 'wrap' }}>
              <Form.Item name="gain_pct" label="涨幅阈值 %" style={{ margin: 0, flex: 1, minWidth: 180 }}>
                <InputNumber min={0.1} max={99} step={0.5} placeholder="不填则不改" style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="loss_pct" label="跌幅阈值 %" style={{ margin: 0, flex: 1, minWidth: 180 }}>
                <InputNumber min={0.1} max={99} step={0.5} placeholder="不填则不改" style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="turnover_pct" label="换手率阈值 %" style={{ margin: 0, flex: 1, minWidth: 180 }}>
                <InputNumber min={0.1} max={99} step={0.5} placeholder="不填则不改" style={{ width: '100%' }} />
              </Form.Item>
            </Space.Compact>
          </Form>
        </div>
        <Divider style={{ margin: '8px 0 12px' }} />
        <Alert
          type="info"
          showIcon
          message="提示"
          description={`默认值 = 涨 ${DEFAULT_GAIN_PCT}% / 跌 ${DEFAULT_LOSS_PCT}% / 换手 ${DEFAULT_TURNOVER_PCT}%，可点左下角「全部重置为默认值」一键应用。`}
        />
      </Modal>
    </div>
  );
}

export default WatchlistPage;

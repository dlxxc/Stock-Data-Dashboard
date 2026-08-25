/**
 * 自选股管理页面（阶段 2.1）
 *
 * 功能：
 * - 列表展示：代码、名称、3 个阈值（涨/跌/换手）、操作
 * - 新增：按钮 → Modal（代码/名称 必填，阈值可选填，默认 5/5/10）
 * - 删除：按钮 → Popconfirm 确认
 * - 编辑阈值：按钮 → Modal（只显示 3 个阈值输入框，当前值为初始值）
 */
import { useEffect, useState } from 'react';
import {
  Alert,
  App as AntdApp,
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
import { PlusOutlined, SettingOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  addWatchItem,
  deleteWatchItem,
  listWatchlist,
  updateWatchThresholds,
} from '@/api/watchlist';
import type { WatchItem } from '@/types/watchlist';

const { Title } = Typography;

/** 默认阈值常量（与后端 config 保持一致） */
const DEFAULT_GAIN_PCT = 5;
const DEFAULT_LOSS_PCT = 5;
const DEFAULT_TURNOVER_PCT = 10;

/** 从任意 catch 对象提取可读错误信息（6 层兜底，杜绝静默失败） */
function getErrorMessage(e: unknown, fallback = '操作失败'): string {
  if (!e) return fallback;
  const err = e as Record<string, any>;
  // ① 标准 Error.message（axios 拦截器 new Error('后端错误：...') 会命中）
  if (typeof err.message === 'string' && err.message) return err.message;
  // ② AxiosError.response.data.detail（绕过拦截器时）
  const d1 = err?.response?.data?.detail;
  if (typeof d1 === 'string' && d1) return d1;
  // ③ AxiosError 状态码 + 文案
  const status = err?.response?.status;
  const statusText = err?.response?.statusText;
  if (typeof statusText === 'string' && statusText) {
    return status ? `请求失败 (${status} ${statusText})` : `请求失败 (${statusText})`;
  }
  // ④ 对象直接带 data.detail
  const d2 = err?.data?.detail;
  if (typeof d2 === 'string' && d2) return d2;
  // ⑤ toString()
  try {
    const s = typeof err.toString === 'function' ? err.toString() : String(e);
    if (s && s !== '[object Object]') return s;
  } catch { /* ignore */ }
  // ⑥ JSON.stringify
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
  // antd 5 validateFields reject: { values, errorFields, outOfDate }
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

function WatchlistPage() {
  // 通过 antd <App> 上下文拿到 message 实例（必须在外层 <ConfigProvider><App> 包裹内使用）
  // 静态方法 messageApi.xxx() 在缺少上下文时会发出警告且可能不实际渲染 DOM 节点
  const { message: messageApi } = AntdApp.useApp();

  const [loading, setLoading] = useState(true);
  const [list, setList] = useState<WatchItem[]>([]);
  const [count, setCount] = useState(0);
  // 兜底默认值会被 loadData() 拿到的接口返回覆盖；接口失败时 fallback 用 100
  const [maxSize, setMaxSize] = useState(100);

  const [addOpen, setAddOpen] = useState(false);
  const [addSubmitting, setAddSubmitting] = useState(false);
  const [addForm] = Form.useForm<AddFormValues>();

  const [editItem, setEditItem] = useState<WatchItem | null>(null);
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editForm] = Form.useForm<EditFormValues>();

  /** 加载列表数据 */
  async function loadData() {
    try {
      setLoading(true);
      const data = await listWatchlist();
      setList(data.items);
      setCount(data.count);
      setMaxSize(data.max_size);
    } catch (e) {
      logError('loadData', e);
      if (!isAntdFormError(e)) {
        messageApi.error(getErrorMessage(e, '加载自选股失败'));
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  /** 打开新增弹窗 */
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

  /** 提交新增 */
  async function handleAddOk() {
    try {
      const values = await addForm.validateFields();
      setAddSubmitting(true);
      // 若用户未填阈值字段，传 undefined 让后端用默认值；如果填了就传用户值
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
    } catch (e) {
      logError('handleAddOk', e);
      // antd 表单校验失败（有 errorFields/outOfDate）不弹 toast，让 antd 在表单里显示红字；
      // 其他任何错误（接口、网络、业务 4xx 等）一律弹 toast，文案走 6 层兜底提取
      if (!isAntdFormError(e)) {
        const msg = getErrorMessage(e, '添加失败');
        // eslint-disable-next-line no-console
        console.error('[DEBUG:handleAddOk]', {
          typeofMessageApi: typeof messageApi,
          hasErrorFn: typeof messageApi?.error,
          messageText: msg,
        });
        // ====== 双保险错误提示机制 ======
        // 先尝试 AntD message（视觉体验好），但因 React19 <-> antd5.22 App 上下文
        // 存在注入不生效风险，所以 2 秒后检查 DOM：如果根本没渲染出 message 节点，
        // 立即回退到原生 window.alert，确保用户"点了按钮一定有反馈"，杜绝静默失败。
        const sentinelId = `__antd_msg_check_${Date.now()}`;
        try {
          window[sentinelId] = true;
          const closeFn = messageApi.error(msg, 5 /* duration 5s */);
          // eslint-disable-next-line no-console
          console.error('[DEBUG:handleAddOk] messageApi.error 返回值类型:', typeof closeFn);
          // 2 秒后检测 AntD toast 是否真的写入 DOM；没写入就用 alert 兜底
          setTimeout(() => {
            try {
              delete window[sentinelId];
              const domHasMessage = (
                document.querySelector('.ant-message') ||
                document.querySelector('[class*="ant-message"]') ||
                document.querySelector('.ant-message-notice')
              );
              if (!domHasMessage) {
                // eslint-disable-next-line no-console
                console.warn('[DEBUG:handleAddOk] AntD toast 未注入 DOM，fallback 到 window.alert');
                window.alert(msg);
              } else {
                // eslint-disable-next-line no-console
                console.info('[DEBUG:handleAddOk] AntD toast 已成功渲染到 DOM');
              }
            } catch (_) { /* ignore */ }
          }, 2000);
        } catch (err2) {
          // eslint-disable-next-line no-console
          console.error('[DEBUG:handleAddOk] messageApi.error 调用本身抛异常:', err2);
          try { delete window[sentinelId]; } catch (_) {}
          // 终极兜底：原生 alert，极端情况下用户也能看到
          window.alert(msg);
        }
      }
    } finally {
      setAddSubmitting(false);
    }
  }

  /** 打开编辑阈值弹窗 */
  function openEditModal(item: WatchItem) {
    setEditItem(item);
    editForm.setFieldsValue({
      gain_pct: item.gain_pct,
      loss_pct: item.loss_pct,
      turnover_pct: item.turnover_pct,
    });
  }

  /** 提交编辑阈值 */
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
    } catch (e) {
      logError('handleEditOk', e);
      if (!isAntdFormError(e)) {
        messageApi.error(getErrorMessage(e, '更新失败'));
      }
    } finally {
      setEditSubmitting(false);
    }
  }

  /** 删除 */
  async function handleDelete(itemId: number) {
    try {
      const res = await deleteWatchItem(itemId);
      if (res.deleted) {
        messageApi.success('删除成功');
        await loadData();
      } else {
        messageApi.warning('记录不存在');
      }
    } catch (e) {
      logError('handleDelete', e);
      if (!isAntdFormError(e)) {
        messageApi.error(getErrorMessage(e, '删除失败'));
      }
    }
  }

  const columns: ColumnsType<WatchItem> = [
    {
      title: '股票代码',
      dataIndex: 'stock_code',
      key: 'stock_code',
      width: 140,
      render: (v: string) => <span className="num-mono">{v}</span>,
    },
    {
      title: '股票名称',
      dataIndex: 'stock_name',
      key: 'stock_name',
      width: 140,
    },
    {
      title: '涨幅阈值',
      dataIndex: 'gain_pct',
      key: 'gain_pct',
      width: 110,
      align: 'right',
      render: (v: number) => (
        <span className="num-mono" style={{ color: '#cf1322' }}>
          ≥ {v}%
        </span>
      ),
    },
    {
      title: '跌幅阈值',
      dataIndex: 'loss_pct',
      key: 'loss_pct',
      width: 110,
      align: 'right',
      render: (v: number) => (
        <span className="num-mono" style={{ color: '#3f8600' }}>
          ≥ {v}%
        </span>
      ),
    },
    {
      title: '换手率阈值',
      dataIndex: 'turnover_pct',
      key: 'turnover_pct',
      width: 120,
      align: 'right',
      render: (v: number) => (
        <span className="num-mono">
          ≥ {v}%
        </span>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
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

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
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
            最多 {maxSize} 只 · 新增时不填阈值将使用默认值（涨 5% / 跌 5% / 换手 10%）
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
        <Alert
          type="warning"
          showIcon
          message={`已添加 ${count}/${maxSize} 只，接近上限`}
          style={{ marginBottom: 16 }}
        />
      )}
      {count >= maxSize && (
        <Alert
          type="error"
          showIcon
          message={`已达上限 ${maxSize} 只，无法继续添加`}
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 表格 */}
      <Spin spinning={loading}>
        <Table<WatchItem>
          rowKey="id"
          columns={columns}
          dataSource={list}
          locale={{ emptyText: '暂无自选股，点击右上角「添加自选股」开始管理' }}
          pagination={{
            pageSize: 50,
            showSizeChanger: false,
            hideOnSinglePage: true,
          }}
          scroll={{ x: 820 }}
        />
      </Spin>

      {/* 底部说明 Tag */}
      <div style={{ marginTop: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <Tag color="red">涨幅阈值：当日涨幅 ≥ 该值即视为异动</Tag>
        <Tag color="green">跌幅阈值：当日跌幅绝对值 ≥ 该值即视为异动</Tag>
        <Tag>换手率阈值：当日换手率 ≥ 该值即视为异动</Tag>
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
              阈值配置（不填则使用默认值：<b>涨 5% / 跌 5% / 换手 10%</b>）
            </div>
            <Space.Compact block style={{ gap: 8, flexWrap: 'wrap' }}>
              <Form.Item name="gain_pct" label="涨幅阈值 %" style={{ margin: 0, flex: 1, minWidth: 180 }}>
                <InputNumber
                  min={0.1}
                  max={99}
                  step={0.5}
                  placeholder={`默认 ${DEFAULT_GAIN_PCT}`}
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item name="loss_pct" label="跌幅阈值 %" style={{ margin: 0, flex: 1, minWidth: 180 }}>
                <InputNumber
                  min={0.1}
                  max={99}
                  step={0.5}
                  placeholder={`默认 ${DEFAULT_LOSS_PCT}`}
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item name="turnover_pct" label="换手率阈值 %" style={{ margin: 0, flex: 1, minWidth: 180 }}>
                <InputNumber
                  min={0.1}
                  max={99}
                  step={0.5}
                  placeholder={`默认 ${DEFAULT_TURNOVER_PCT}`}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Space.Compact>
          </div>
        </Form>
      </Modal>

      {/* ========== 编辑阈值弹窗 ========== */}
      <Modal
        title={editItem ? `编辑阈值 · ${editItem.stock_name}（${editItem.stock_code}）` : '编辑阈值'}
        open={!!editItem}
        onCancel={() => setEditItem(null)}
        onOk={handleEditOk}
        confirmLoading={editSubmitting}
        okText="保存"
        cancelText="取消"
        destroyOnClose
      >
        <Form<EditFormValues>
          form={editForm}
          layout="vertical"
          preserve={false}
          style={{ marginTop: 8 }}
        >
          <Form.Item
            name="gain_pct"
            label="涨幅阈值 %"
            rules={[{ required: true, message: '请输入涨幅阈值' }]}
          >
            <InputNumber
              min={0.1}
              max={99}
              step={0.5}
              style={{ width: '100%' }}
            />
          </Form.Item>
          <Form.Item
            name="loss_pct"
            label="跌幅阈值 %（绝对值）"
            rules={[{ required: true, message: '请输入跌幅阈值' }]}
          >
            <InputNumber
              min={0.1}
              max={99}
              step={0.5}
              style={{ width: '100%' }}
            />
          </Form.Item>
          <Form.Item
            name="turnover_pct"
            label="换手率阈值 %"
            rules={[{ required: true, message: '请输入换手率阈值' }]}
          >
            <InputNumber
              min={0.1}
              max={99}
              step={0.5}
              style={{ width: '100%' }}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default WatchlistPage;

/**
 * 总览页（阶段 1 第 2 次开发版本）
 *
 * 实现需求 M10 / 1.9：
 * - 启动时调 GET /api/snapshot/latest 读取上次快照
 * - **不自动刷新**（铁律：由用户决定何时点刷新）
 * - 无快照：友好空状态，引导用户后续点刷新
 * - 有快照：展示交易日 + 已存档模块清单（具体数据卡片下阶段做）
 *
 * 错误处理（军规 6）：
 * - 网络错误：红色错误提示 + 重试按钮，绝不静默
 */
import { useCallback, useEffect, useState } from 'react';
import { Alert, Button, Card, Result, Space, Spin, Tag, Typography } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { getLatestSnapshot } from '@/api/snapshot';
import { MODULE_ORDER, getModuleLabel } from '@/constants/modules';
import type { LatestSnapshot } from '@/types/snapshot';

const { Paragraph, Text } = Typography;

/** 加载状态 */
type LoadStatus = 'loading' | 'success' | 'error';

/** 组件状态 */
interface State {
  status: LoadStatus;
  data: LatestSnapshot | null;
  error: string;
}

/** 初始状态：进入页面即加载 */
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
      // 后端在无快照时返回 {"empty": true}
      if ('empty' in res) {
        // 视为成功但无数据，交给空状态分支渲染
        setState({ status: 'success', data: null, error: '' });
      } else {
        setState({ status: 'success', data: res, error: '' });
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setState({ status: 'error', data: null, error: msg });
    }
  }, []);

  // 启动时只调一次（依赖空数组，loadLatest 引用稳定）
  useEffect(() => {
    void loadLatest();
  }, [loadLatest]);

  // ---- 渲染分支 ----
  if (state.status === 'loading') {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Spin tip="正在读取上次快照..." size="large">
          <div style={{ padding: '30px' }} />
        </Spin>
      </div>
    );
  }

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

  // 成功但无快照（首次启动或数据库空）
  if (state.data === null) {
    return (
      <Card>
        <Result
          status="info"
          title="暂无历史快照"
          subTitle="这是首次启动或数据库为空"
          extra={
            <Space direction="vertical" align="center">
              <Text type="secondary">下次开发会接入刷新按钮，点刷新即可拉取最新盘后数据</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                当前版本不会自动刷新，由用户决定何时点刷新
              </Text>
            </Space>
          }
        />
      </Card>
    );
  }

  // 成功且有快照：展示交易日 + 模块清单（占位，具体数据卡片下阶段做）
  const { trade_date, modules, fetched_at } = state.data;
  const moduleNames = MODULE_ORDER.filter((name) => name in modules);

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Alert
        type="info"
        showIcon
        message={`正在展示 ${trade_date} 的存档快照`}
        description={
          <Space size="large">
            <Text type="secondary">交易日：{trade_date}</Text>
            <Text type="secondary">存档时间：{fetched_at ?? '未知'}</Text>
            <Text type="secondary">已存档模块：{moduleNames.length} 个</Text>
          </Space>
        }
      />

      <Card title="已存档模块" size="small">
        <Paragraph type="secondary" style={{ marginBottom: 12 }}>
          阶段 1 第 3 次开发会接入完整仪表盘（指数卡片 / 涨跌停统计 / 资金流 / 板块广度）。
          当前仅列出模块清单。
        </Paragraph>
        <Space wrap>
          {moduleNames.map((name) => (
            <Tag key={name} color="blue">
              {getModuleLabel(name)}
            </Tag>
          ))}
        </Space>
      </Card>

      <Card size="small">
        <Paragraph type="secondary" style={{ margin: 0 }}>
          提示：刷新功能将在阶段 1 第 4 次开发中接入，当前版本仅展示已有快照，不会自动拉取数据。
        </Paragraph>
      </Card>
    </Space>
  );
}

export default OverviewPage;

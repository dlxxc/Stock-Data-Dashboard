/**
 * 资讯页（阶段 3.1）
 *
 * 设计要点：
 * - 数据来源：GET /api/news（读快照，不主动刷新）
 * - 表格展示：序号 / 标题（可点击跳转） / 发布时间 / 数据源
 * - 失败 / 未归档：红色 Alert + 重试按钮（军规 6 不静默）
 * - 历史回看：HistoryDatePicker 选日期 → GET /api/news?trade_date=...
 * - 4 状态分支：loading / error / empty / success
 *
 * 铁律：绝不显示假数据，失败即空 + 红色重试按钮（与军规一致）
 */
import { useCallback, useEffect, useState } from 'react';
import { Alert, Button, Card, Empty, Space, Spin, Table, Tag, Typography } from 'antd';
import { ReloadOutlined, FileTextOutlined, LinkOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';
import { getNews } from '@/api/news';
import HistoryDatePicker from '@/components/dashboard/HistoryDatePicker';
import AiSettings from '@/components/dashboard/AiSettings';
import AiSummary from '@/components/dashboard/AiSummary';
import type { NewsArticle, NewsResponse } from '@/types/news';

const { Title, Text } = Typography;

// ========== 类型定义 ==========

type LoadStatus = 'loading' | 'success' | 'error' | 'empty';

// ========== 主组件 ==========

export default function NewsPage() {
  const navigate = useNavigate();

  // ========== 状态 ==========
  const [status, setStatus] = useState<LoadStatus>('loading');
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [data, setData] = useState<NewsResponse | null>(null);
  const [historyDate, setHistoryDate] = useState<string | null>(null);
  const [highlightIndices, setHighlightIndices] = useState<Set<number>>(new Set());

  // ========== 加载数据 ==========

  const loadData = useCallback(async (tradeDate?: string) => {
    setStatus('loading');
    setErrorMsg('');
    try {
      const result = await getNews(tradeDate);

      // 失败检测（军规：失败即空）
      if (result.empty) {
        setStatus('empty');
        setErrorMsg(result.error || '该日无资讯数据');
        setData(null);
        return;
      }

      setData(result);
      setStatus('success');
    } catch (err: any) {
      setStatus('error');
      setErrorMsg(err?.message || '网络错误，请重试');
      setData(null);
    }
  }, []);

  // 初次加载
  useEffect(() => {
    loadData();
  }, [loadData]);

  // ========== 事件处理 ==========

  const handleRetry = () => {
    loadData(historyDate || undefined);
  };

  const handleDateChange = (date: string | null) => {
    setHistoryDate(date);
    loadData(date || undefined);
  };

  const handleBackToOverview = () => {
    navigate('/');
  };

  const handleSectorSelect = (indices: number[]) => {
    setHighlightIndices(new Set(indices));
  };

  // ========== 表格列定义 ==========

  const columns: ColumnsType<NewsArticle> = [
    {
      title: '#',
      key: 'index',
      width: 60,
      align: 'center',
      render: (_, __, index) => <Text className="num-mono">{index + 1}</Text>,
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (title: string, record: NewsArticle) => {
        const hasUrl = record.url && record.url.trim() !== '';
        if (hasUrl) {
          return (
            <a
              href={record.url}
              onClick={(e) => {
                e.preventDefault();
                window.open(record.url, '_blank', 'noopener,noreferrer');
              }}
              style={{ fontWeight: 500, cursor: 'pointer' }}
            >
              {title} <LinkOutlined style={{ fontSize: 12, marginLeft: 4 }} />
            </a>
          );
        }
        return <Text strong>{title}</Text>;
      },
    },
    {
      title: '摘要',
      dataIndex: 'summary',
      key: 'summary',
      width: 400,
      ellipsis: true,
      render: (summary: string) => (
        <Text type="secondary" style={{ fontSize: 13 }}>
          {summary}
        </Text>
      ),
    },
    {
      title: '发布时间',
      dataIndex: 'publish_time',
      key: 'publish_time',
      width: 180,
      align: 'center',
      render: (time: string) => <Text className="num-mono">{time}</Text>,
    },
  ];

  // ========== 渲染：标题栏 ==========

  const renderToolbar = () => (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 16,
      }}
    >
      <Space>
        <FileTextOutlined style={{ fontSize: 24 }} />
        <Title level={3} style={{ margin: 0 }}>
          财经资讯
        </Title>
        {data && (
          <Tag color="blue">
            {data.source === 'eastmoney' ? '东方财富' : '新浪财经'}
          </Tag>
        )}
      </Space>

      <Space>
        <AiSettings />
        <HistoryDatePicker value={historyDate} onChange={handleDateChange} />
        <Button icon={<ReloadOutlined />} onClick={handleRetry}>
          刷新
        </Button>
      </Space>
    </div>
  );

  // ========== 渲染：4 状态分支 ==========

  // 1. 加载中
  if (status === 'loading') {
    return (
      <div>
        {renderToolbar()}
        <Card>
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <Spin size="large" tip="加载资讯数据..." />
          </div>
        </Card>
      </div>
    );
  }

  // 2. 错误状态（网络错误）
  if (status === 'error') {
    return (
      <div>
        {renderToolbar()}
        <Alert
          type="error"
          message="资讯数据加载失败"
          description={errorMsg}
          showIcon
          action={
            <Button size="small" danger onClick={handleRetry}>
              点此重试
            </Button>
          }
          style={{ marginBottom: 16 }}
        />
      </div>
    );
  }

  // 3. 空状态（未归档 / 模块失败）
  if (status === 'empty') {
    const isHistoryMode = historyDate !== null;
    return (
      <div>
        {renderToolbar()}
        <Alert
          type="warning"
          message={isHistoryMode ? '该日无资讯数据' : '资讯模块未归档'}
          description={errorMsg}
          showIcon
          action={
            !isHistoryMode ? (
              <Button size="small" type="primary" onClick={handleBackToOverview}>
                去总览刷新
              </Button>
            ) : undefined
          }
          style={{ marginBottom: 16 }}
        />
        <Card>
          <Empty description="暂无资讯数据" />
        </Card>
      </div>
    );
  }

  // 4. 成功状态
  if (!data || data.articles.length === 0) {
    return (
      <div>
        {renderToolbar()}
        <Card>
          <Empty description="暂无资讯" />
        </Card>
      </div>
    );
  }

  return (
    <div>
      {renderToolbar()}

      <AiSummary tradeDate={historyDate} onSectorSelect={handleSectorSelect} />

      <Card
        size="small"
        title={
          <Space>
            <Text strong>资讯列表</Text>
            <Tag>{data.total} 条</Tag>
            <Text type="secondary" style={{ fontSize: 13 }}>
              交易日：{data.trade_date}
            </Text>
          </Space>
        }
      >
        <Table<NewsArticle>
          columns={columns}
          dataSource={data.articles}
          rowKey={(_, index) => `news-${index}`}
          size="small"
          rowClassName={(_, index) =>
            highlightIndices.has(index) ? 'ai-highlight-row' : ''
          }
          pagination={{
            pageSize: 20,
            showSizeChanger: false,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>
    </div>
  );
}

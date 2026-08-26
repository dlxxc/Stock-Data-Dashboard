/**
 * AI 总结展示区（阶段 3.3）
 *
 * 两层结构：
 * - 顶部：今日整体市场概览（一句话）
 * - 下方：按板块分组（板块名 + 一句话摘要），板块可点击联动高亮对应资讯
 *
 * 状态分支：
 * - not_generated：显示「生成 AI 总结」按钮
 * - generating：按钮 loading +「生成中约 10-30s」
 * - ok：两层总结
 * - failed：红色 Alert + 重试
 * - need_key：黄色提示去配置 Key
 * - no_news：灰色提示无资讯
 *
 * 军规：绝不显示假数据，失败即空 + 可重试（军规 6 不静默）
 */
import { useCallback, useEffect, useState } from 'react';
import { Alert, Button, Card, Space, Spin, Tag, Typography } from 'antd';
import { RobotOutlined, ReloadOutlined } from '@ant-design/icons';
import { App as AntdApp } from 'antd';
import { generateAiSummary, getAiSummary } from '@/api/ai';
import type { AISummaryResponse } from '@/types/ai';

const { Text, Paragraph } = Typography;

interface AiSummaryProps {
  /** 历史回看日期（null 取最新） */
  tradeDate?: string | null;
  /** 板块点击时回调，传 article_indices 给父组件高亮表格行 */
  onSectorSelect?: (indices: number[]) => void;
}

export default function AiSummary({ tradeDate, onSectorSelect }: AiSummaryProps) {
  const { message: messageApi } = AntdApp.useApp();
  const [summary, setSummary] = useState<AISummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [selectedSector, setSelectedSector] = useState<string | null>(null);

  // 加载缓存
  const loadSummary = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getAiSummary(tradeDate || undefined);
      setSummary(result);
    } catch {
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, [tradeDate]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  // 生成
  const handleGenerate = async (force = false) => {
    setGenerating(true);
    setSelectedSector(null);
    try {
      const result = await generateAiSummary({
        trade_date: tradeDate || undefined,
        force,
      });
      setSummary(result);
      if (result.status === 'ok') {
        messageApi.success('AI 总结生成成功');
      } else if (result.status === 'failed') {
        messageApi.error('AI 总结生成失败');
      } else if (result.status === 'need_key') {
        messageApi.warning('请先在 AI 设置中配置 Key');
      }
    } catch (err: any) {
      messageApi.error(err?.message || '生成失败，请重试');
    } finally {
      setGenerating(false);
    }
  };

  // 板块点击
  const handleSectorClick = (sectorName: string, indices: number[]) => {
    if (selectedSector === sectorName) {
      // 再次点击取消选中
      setSelectedSector(null);
      onSectorSelect?.([]);
    } else {
      setSelectedSector(sectorName);
      onSectorSelect?.(indices);
    }
  };

  // ========== 状态渲染 ==========

  // 加载中
  if (loading) {
    return (
      <Card size="small" style={{ marginBottom: 16 }}>
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          <Spin size="small" tip="检查 AI 总结状态..." />
        </div>
      </Card>
    );
  }

  const status = summary?.status || 'not_generated';

  // 1. 未生成
  if (status === 'not_generated') {
    return (
      <Card size="small" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <RobotOutlined style={{ fontSize: 18 }} />
            <Text strong>AI 智能总结</Text>
          </Space>
          <Button
            type="primary"
            icon={<RobotOutlined />}
            loading={generating}
            onClick={() => handleGenerate(false)}
          >
            生成 AI 总结
          </Button>
        </div>
      </Card>
    );
  }

  // 2. 生成中
  if (status === 'generating' || generating) {
    return (
      <Card size="small" style={{ marginBottom: 16 }}>
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          <Spin size="default" tip="AI 正在分析资讯，约 10-30 秒..." />
        </div>
      </Card>
    );
  }

  // 3. 需要 Key
  if (status === 'need_key') {
    return (
      <Card size="small" style={{ marginBottom: 16 }}>
        <Alert
          type="warning"
          message="未配置 AI API Key"
          description={summary?.error || '请先在右上角「AI 设置」中填写智谱 API Key'}
          showIcon
        />
      </Card>
    );
  }

  // 4. 无资讯
  if (status === 'no_news') {
    return (
      <Card size="small" style={{ marginBottom: 16 }}>
        <Alert
          type="info"
          message="暂无资讯数据"
          description={summary?.error || '请先刷新数据'}
          showIcon
        />
      </Card>
    );
  }

  // 5. 失败
  if (status === 'failed') {
    return (
      <Card size="small" style={{ marginBottom: 16 }}>
        <Alert
          type="error"
          message="AI 总结生成失败"
          description={summary?.error || '未知错误'}
          showIcon
          action={
            <Button
              size="small"
              danger
              icon={<ReloadOutlined />}
              loading={generating}
              onClick={() => handleGenerate(true)}
            >
              重试
            </Button>
          }
        />
      </Card>
    );
  }

  // 6. 成功 → 两层总结
  if (!summary) return null;

  return (
    <Card
      size="small"
      style={{ marginBottom: 16 }}
      title={
        <Space>
          <RobotOutlined />
          <Text strong>AI 智能总结</Text>
          {summary.generated_at && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {summary.generated_at}
            </Text>
          )}
        </Space>
      }
      extra={
        <Button
          size="small"
          icon={<ReloadOutlined />}
          loading={generating}
          onClick={() => handleGenerate(true)}
        >
          重新生成
        </Button>
      }
    >
      {/* 顶部：整体概览 */}
      <Paragraph style={{ marginBottom: 12, fontSize: 14 }}>
        <Text type="secondary">今日概览：</Text>
        {summary.overview || '（无概览内容）'}
      </Paragraph>

      {/* 下方：板块分组 */}
      {summary.sectors.length > 0 ? (
        <Space wrap size={[8, 8]}>
          {summary.sectors.map((sector, i) => (
            <div
              key={`${sector.name}-${i}`}
              onClick={() => handleSectorClick(sector.name, sector.article_indices)}
              style={{
                cursor: 'pointer',
                padding: '6px 12px',
                borderRadius: 6,
                border: '1px solid',
                borderColor: selectedSector === sector.name ? '#1677ff' : '#e8e8e8',
                background: selectedSector === sector.name ? '#e6f4ff' : '#fafafa',
                transition: 'all 0.2s',
              }}
            >
              <Tag color="blue" style={{ marginRight: 4 }}>
                {sector.name}
              </Tag>
              <Text style={{ fontSize: 13 }}>{sector.summary}</Text>
              {sector.article_indices.length > 0 && (
                <Text type="secondary" style={{ fontSize: 12, marginLeft: 4 }}>
                  ({sector.article_indices.length}条)
                </Text>
              )}
            </div>
          ))}
        </Space>
      ) : (
        <Text type="secondary" style={{ fontSize: 13 }}>
          （无板块分组）
        </Text>
      )}

      {selectedSector && (
        <div style={{ marginTop: 8 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            已选中板块，下方表格已高亮对应资讯
          </Text>
        </div>
      )}
    </Card>
  );
}
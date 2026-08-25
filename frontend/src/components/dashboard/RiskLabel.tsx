/**
 * 风险等级标签（需求 1.10）
 *
 * 顶部突出的风险提示卡片：左侧大标签（绿/黄/红）+ 右侧一句话总结 + 触发项明细。
 *
 * 配色说明：
 * - 风险等级的红/黄/绿是通用风险信号色，与 A 股「红涨绿跌」交易配色无关，不会混淆
 * - 直接使用 antd 默认色板：success / warning / error
 */
import { Card, Tag, Tooltip, Typography } from 'antd';
import type { RiskAssessment, RiskLevel } from '@/types/risk';

const { Text } = Typography;

/** 风险等级配色（背景 / 边框 / 文字 / Tag 颜色） */
interface RiskColorSet {
  bg: string;
  border: string;
  text: string;
  tagColor: string;
}

const RISK_COLORS: Record<RiskLevel, RiskColorSet> = {
  green: {
    bg: '#f6ffed',
    border: '#b7eb8f',
    text: '#389e0d',
    tagColor: 'success',
  },
  yellow: {
    bg: '#fffbe6',
    border: '#ffe58f',
    text: '#d48806',
    tagColor: 'warning',
  },
  red: {
    bg: '#fff1f0',
    border: '#ffa39e',
    text: '#cf1322',
    tagColor: 'error',
  },
};

/** 触发项等级对应 Tag 颜色 */
function triggerTagColor(level: RiskLevel): string {
  return RISK_COLORS[level].tagColor;
}

interface RiskLabelProps {
  /** 风险评估结果（来自 /api/risk） */
  data: RiskAssessment;
}

export default function RiskLabel({ data }: RiskLabelProps) {
  const { level, label, summary, triggers } = data;
  const color = RISK_COLORS[level];

  return (
    <Card size="small" style={{ background: color.bg, borderColor: color.border }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
        {/* 左侧：风险等级大标签 */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minWidth: 88,
            padding: '4px 12px',
            borderRight: `1px solid ${color.border}`,
          }}
        >
          <Text style={{ fontSize: 11, color: color.text, opacity: 0.8 }}>风险等级</Text>
          <Text
            strong
            style={{
              fontSize: 22,
              color: color.text,
              lineHeight: '30px',
              letterSpacing: '1px',
            }}
          >
            {label}
          </Text>
        </div>

        {/* 右侧：一句话总结 + 触发项明细 */}
        <div style={{ flex: 1, minWidth: 240, display: 'flex', flexDirection: 'column', gap: 6 }}>
          <Text style={{ fontSize: 14, color: color.text }}>
            {summary}
          </Text>
          {triggers.length > 0 ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {triggers.map((t, i) => (
                <Tooltip key={i} title={t.detail}>
                  <Tag color={triggerTagColor(t.level)} style={{ margin: 0 }}>
                    {t.dimension}
                  </Tag>
                </Tooltip>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </Card>
  );
}

/**
 * 单模块拉取失败展示（需求 1.7）
 *
 * 铁律：绝不显示假数据，失败即空 + 红色「拉取失败，点此重试」按钮。
 *
 * 用法：
 * - 今日刷新场景：传 onRetry，显示重试按钮（点击触发整体刷新）
 * - 历史回看场景：不传 onRetry，仅显示「该日该模块拉取失败」提示
 *   （重试只能拉今日数据，重试历史日无意义）
 */
import { Button, Typography } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';

const { Text } = Typography;

/** 失败信息（data=null 时若有，表示该模块拉取失败） */
export interface ModuleFailureInfo {
  error: string;
}

interface ModuleFailureProps {
  /** 错误信息 */
  error: string;
  /** 重试回调（不传则不显示重试按钮，如历史回看场景） */
  onRetry?: () => void;
}

export default function ModuleFailure({ error, onRetry }: ModuleFailureProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '12px 0' }}>
      <Text type="danger" style={{ fontSize: 13 }}>
        拉取失败：{error}
      </Text>
      {onRetry && (
        <Button
          danger
          size="small"
          icon={<ReloadOutlined />}
          onClick={onRetry}
          style={{ alignSelf: 'flex-start' }}
        >
          点此重试
        </Button>
      )}
    </div>
  );
}

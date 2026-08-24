/**
 * 应用头部
 *
 * 阶段 1 第 2 次开发：仅展示产品名与简短说明
 * 阶段 1 第 4 次开发：刷新按钮 + 进度条移到 OverviewPage 顶部工具栏
 */
import { Typography } from 'antd';

const { Title, Text } = Typography;

function AppHeader() {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: 16,
        height: '100%',
        color: '#fff',
      }}
    >
      <Title level={4} style={{ color: '#fff', margin: 0 }}>
        A股数据看板工具
      </Title>
      <Text style={{ color: 'rgba(255,255,255,0.65)', fontSize: 12 }}>
        盘后复盘 · 手动刷新
      </Text>
    </div>
  );
}

export default AppHeader;

/**
 * 应用头部（阶段 2 改造）
 *
 * 左侧：产品名 + 副标题
 * 右侧：导航菜单（总览 / 自选股 / 龙虎榜 / 资讯）
 */
import { Menu, Typography } from 'antd';
import type { MenuProps } from 'antd';
import { DashboardOutlined, StarOutlined, TrophyOutlined, FileTextOutlined } from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;

type MenuKey = '/' | '/watchlist' | '/dragon-tiger' | '/news';

function AppHeader() {
  const location = useLocation();
  const navigate = useNavigate();

  const menuItems: MenuProps['items'] = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: '总览',
    },
    {
      key: '/watchlist',
      icon: <StarOutlined />,
      label: '自选股',
    },
    {
      key: '/dragon-tiger',
      icon: <TrophyOutlined />,
      label: '龙虎榜',
    },
    {
      key: '/news',
      icon: <FileTextOutlined />,
      label: '资讯',
    },
  ];

  const selectedKey: MenuKey = location.pathname.startsWith('/watchlist')
    ? '/watchlist'
    : location.pathname.startsWith('/dragon-tiger')
      ? '/dragon-tiger'
      : location.pathname.startsWith('/news')
        ? '/news'
        : '/';

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '100%',
        color: '#fff',
      }}
    >
      {/* 左侧品牌区 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          gap: 16,
          flexShrink: 0,
        }}
      >
        <Title level={4} style={{ color: '#fff', margin: 0 }}>
          A股数据看板工具
        </Title>
        <Text style={{ color: 'rgba(255,255,255,0.65)', fontSize: 12 }}>
          盘后复盘 · 手动刷新
        </Text>
      </div>

      {/* 右侧导航菜单 */}
      <Menu
        mode="horizontal"
        theme="dark"
        selectedKeys={[selectedKey]}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
        style={{
          background: 'transparent',
          borderBottom: 'none',
          flex: 1,
          justifyContent: 'flex-end',
        }}
      />
    </div>
  );
}

export default AppHeader;

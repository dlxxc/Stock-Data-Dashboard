/**
 * 应用主入口
 *
 * 职责：
 * - ConfigProvider 注入 AntD 中文 + 主题
 * - BrowserRouter 路由
 * - 整体布局（Header + Content + Footer）
 */
import { ConfigProvider, Layout, theme, App as AntdApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import AppHeader from '@/components/AppHeader';
import OverviewPage from '@/pages/OverviewPage';
import WatchlistPage from '@/pages/WatchlistPage';

const { Header, Content, Footer } = Layout;

/**
 * 注意：Ant Design 5 推荐用 <App> 组件作为根包裹
 *       它会为所有子组件提供 message / modal / notification 的上下文实例；
 *       缺失时静态方法 message.xxx() 会警告且可能不实际渲染 DOM（造成"点了没反应"）。
 */
function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1677ff',
          borderRadius: 6,
        },
      }}
    >
      <AntdApp>
        <BrowserRouter>
          <Layout style={{ minHeight: '100vh' }}>
            <Header>
              <AppHeader />
            </Header>
            <Content style={{ padding: '24px' }}>
              <Routes>
                <Route path="/" element={<OverviewPage />} />
                <Route path="/watchlist" element={<WatchlistPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Content>
            <Footer style={{ textAlign: 'center', color: '#999', fontSize: 12 }}>
              A股数据看板工具 · 个人自用 · v0.1
            </Footer>
          </Layout>
        </BrowserRouter>
      </AntdApp>
    </ConfigProvider>
  );
}

export default App;

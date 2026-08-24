/**
 * 应用主入口
 *
 * 职责：
 * - ConfigProvider 注入 AntD 中文 + 主题
 * - BrowserRouter 路由
 * - 整体布局（Header + Content + Footer）
 */
import { ConfigProvider, Layout, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import AppHeader from '@/components/AppHeader';
import OverviewPage from '@/pages/OverviewPage';

const { Header, Content, Footer } = Layout;

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
      <BrowserRouter>
        <Layout style={{ minHeight: '100vh' }}>
          <Header>
            <AppHeader />
          </Header>
          <Content style={{ padding: '24px' }}>
            <Routes>
              <Route path="/" element={<OverviewPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Content>
          <Footer style={{ textAlign: 'center', color: '#999', fontSize: 12 }}>
            A股数据看板工具 · 个人自用 · v0.1
          </Footer>
        </Layout>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;

/**
 * axios 客户端
 *
 * - baseUrl 走 /api 前缀，开发期 vite proxy 转发到 FastAPI 8000
 * - 统一错误处理：网络错误抛出 Error，调用方按需 catch
 */
import axios, { type AxiosInstance } from 'axios';

const client: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 响应拦截：把后端错误统一成 Error 抛出
client.interceptors.response.use(
  (response) => response,
  (error) => {
    // 网络层错误（连不上后端）
    if (!error.response) {
      return Promise.reject(new Error('无法连接后端服务，请确认 8000 端口已启动'));
    }
    // HTTP 错误（4xx / 5xx）
    const msg = error.response?.data?.detail ?? error.response?.statusText ?? '请求失败';
    return Promise.reject(new Error(`后端错误：${msg}`));
  },
);

export default client;

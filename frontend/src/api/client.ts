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
      return Promise.reject(new Error('无法连接后端服务，请确认 8001 端口已启动'));
    }
    // HTTP 错误（4xx / 5xx）：提取后端 detail，兼容字符串 / 数组 / 对象
    const status = error.response?.status;
    const statusText = error.response?.statusText ?? '';
    const detail = error.response?.data?.detail;

    let msg: string;
    if (typeof detail === 'string') {
      msg = detail;
    } else if (Array.isArray(detail)) {
      // FastAPI 422 校验错误：{loc: [...], msg: ..., type: ...}[]
      msg = detail
        .map((it: Record<string, unknown>) => {
          const loc = Array.isArray(it.loc) ? it.loc.join('.') : '';
          return loc ? `${loc}: ${it.msg}` : String(it.msg ?? '');
        })
        .filter(Boolean)
        .join('; ');
    } else if (detail && typeof detail === 'object') {
      msg = JSON.stringify(detail);
    } else {
      msg = statusText || '请求失败';
    }

    const prefix = status ? `后端错误 (${status})` : '后端错误';
    return Promise.reject(new Error(`${prefix}：${msg || '未知错误'}`));
  },
);

export default client;

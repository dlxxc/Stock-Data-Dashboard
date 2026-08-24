/**
 * SSE 刷新接口封装（需求 1.5-前端 + 1.7 失败处理）
 *
 * 后端 POST /api/refresh 返回 SSE 流：
 *   event: progress
 *   data: {"module":"_start","index":0,"total":4,"status":"start","trade_date":"2026-08-24"}
 *
 *   event: progress
 *   data: {"module":"indices","index":1,"total":4,"status":"fetching","message":"正在拉取 indices (1/4)"}
 *
 *   event: progress
 *   data: {"module":"indices","index":1,"total":4,"status":"ok"}
 *
 *   event: done
 *   data: {"trade_date":"2026-08-24","ok_count":3,"fail_count":1,"fail_modules":["sector_breadth"]}
 *
 * 【关键设计决策】
 * - 后端是 POST，无法用浏览器原生 EventSource（仅支持 GET），改用 fetch + ReadableStream
 * - 开发期走 Vite proxy（/api → 8000），同源无 CORS；生产期直连后端
 * - Vite proxy 配置了 configure 禁用缓冲，确保 SSE 事件实时推送
 * - Windows 行尾 \r\n 在 parseSseFrame 中统一归一化为 \n
 *
 * 错误处理（军规 6）：
 * - 网络层错误 → onError 抛出，调用方按需展示
 * - 单模块失败 → onProgress 推送 status='failed'，由 onDone 汇总
 */

/** 开发期走 Vite proxy（同源无 CORS），生产期可改为直连 */
const REFRESH_URL = '/api/refresh';

/** 单条 progress 事件 payload */
export interface RefreshProgressEvent {
  module: string;
  index: number;
  total: number;
  status: 'start' | 'fetching' | 'ok' | 'failed';
  error?: string | null;
  message?: string;
  trade_date?: string;
}

/** done 事件 payload */
export interface RefreshDoneEvent {
  trade_date: string;
  ok_count: number;
  fail_count: number;
  fail_modules: string[];
}

/** SSE 回调集合 */
export interface RefreshCallbacks {
  onProgress?: (event: RefreshProgressEvent) => void;
  onDone?: (event: RefreshDoneEvent) => void;
  onError?: (error: Error) => void;
}

/**
 * 触发后端 SSE 刷新。
 *
 * 后端在 SSE 流中已自动 save_snapshot（每个模块成功即存档），
 * 调用方在 onDone 后只需重新 GET /api/snapshot/latest 即可拿到最新存档。
 */
export async function refreshData(callbacks: RefreshCallbacks): Promise<void> {
  let response: Response;
  try {
    response = await fetch(REFRESH_URL, {
      method: 'POST',
      headers: { Accept: 'text/event-stream' },
    });
  } catch (e) {
    callbacks.onError?.(
      e instanceof Error ? e : new Error('无法连接后端服务，请确认 8000 端口已启动'),
    );
    return;
  }

  if (!response.ok) {
    callbacks.onError?.(new Error(`后端返回 ${response.status} ${response.statusText}`));
    return;
  }
  if (!response.body) {
    callbacks.onError?.(new Error('后端未返回数据流'));
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

      let frameEnd: number;
      while ((frameEnd = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, frameEnd);
        buffer = buffer.slice(frameEnd + 2);
        parseSseFrame(frame, callbacks);
      }
    }
    if (buffer.trim()) {
      parseSseFrame(buffer, callbacks);
    }
  } catch (e) {
    callbacks.onError?.(e instanceof Error ? e : new Error(String(e)));
  }
}

/** 解析单个 SSE 帧（已处理 Windows \r\n 行尾） */
function parseSseFrame(frame: string, callbacks: RefreshCallbacks): void {
  let event = 'message';
  const dataLines: string[] = [];

  const normalized = frame.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

  for (const line of normalized.split('\n')) {
    const trimmed = line.trimEnd();
    if (trimmed.startsWith('event:')) {
      event = trimmed.slice(6).trim();
    } else if (trimmed.startsWith('data:')) {
      dataLines.push(trimmed.slice(5).replace(/^ /, ''));
    }
  }

  const data = dataLines.join('\n');
  if (!data) return;

  try {
    const payload = JSON.parse(data);
    if (event === 'progress') {
      callbacks.onProgress?.(payload as RefreshProgressEvent);
    } else if (event === 'done') {
      callbacks.onDone?.(payload as RefreshDoneEvent);
    }
  } catch {
    // 军规 6：解析失败不应静默，控制台可见便于调试
    console.warn('[SSE] 帧解析失败:', { event, data });
  }
}

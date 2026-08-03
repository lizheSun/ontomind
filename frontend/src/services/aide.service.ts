/**
 * AIDE — opencode web UI 嵌入服务.
 *
 * 后端 /opencode/web/* 会自动决策最佳嵌入源：
 *  - opencode ≥ 1.18 的 serve(4096) 已内置完整 UI → 直接嵌，零额外进程
 *  - 否则回退到独立 `opencode web`(4097)
 */
import api from './api';

export interface AideWebInstance {
  pid: number;
  port: number;
  url: string;
  started_at?: number;
  cmdline?: string;
}

export interface AideStatus {
  /** 是否有可嵌入的 URL */
  healthy: boolean;
  /** iframe 用的最终 URL（空串代表没有可用源） */
  embed_url: string;
  /** 嵌入源：serve(复用对话工作台) / web(独立进程) / none */
  embed_source: 'serve' | 'web' | 'none';
  cli_installed: boolean;
  cli_path: string;
  version: string;
  // serve（对话工作台复用）
  serve_base_url: string;
  serve_port: number;
  serve_healthy: boolean;
  serve_has_ui: boolean;
  // 独立 web（兜底）
  web_url: string;
  web_port: number;
  web_healthy: boolean;
  web_instances: AideWebInstance[];
}

export interface AideStartResult {
  already_running: boolean;
  pid?: number;
  port: number;
  url: string;
}

function unwrap<T>(resp: { data: { code?: string; message?: string; data: T } }): T {
  return resp.data.data;
}

export const aideService = {
  /**
   * 探活 + 拿到最佳嵌入 URL.
   *
   * @param opts.fast   只做端口探活（后端 ~2ms，不开子进程）。轮询/复查用。
   * @param opts.detail 额外拉进程明细（后端 +50ms）。仅诊断用。
   */
  status: (opts?: { fast?: boolean; detail?: boolean }) =>
    api
      .get('/opencode/web/status', {
        params: {
          ...(opts?.fast ? { fast: 1 } : {}),
          ...(opts?.detail ? { detail: 1 } : {}),
        },
      })
      .then((r) => unwrap<AideStatus>(r)),

  /** 拉起独立 opencode web（serve 没 UI 时的兜底） */
  start: (opts?: { port?: number; cors?: string; hostname?: string }) =>
    api
      .post('/opencode/web/start', {
        port: opts?.port,
        cors: opts?.cors ?? `${window.location.origin}`,
        hostname: opts?.hostname ?? '127.0.0.1',
      })
      .then((r) => unwrap<AideStartResult>(r)),

  /** 停掉独立 opencode web */
  stop: (port?: number) =>
    api
      .post('/opencode/web/stop', { port })
      .then((r) => unwrap<{ stopped: number[]; port: number }>(r)),
};

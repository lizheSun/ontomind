import axios, { AxiosError, type AxiosRequestConfig } from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * 网络错误自动重试
 *
 * 背景：开发时后端跑 `uvicorn --reload`，改任意 .py 都会触发热重载，
 * 期间有 1~3 秒的窗口会 ECONNREFUSED。用户恰好在这个窗口点操作，
 * 就会看到「无法连接后端服务」，但其实后端马上就恢复了。
 *
 * 策略：仅对「网络层失败」（无 response）重试，指数退避 300/600/1200ms。
 * 有 HTTP 响应的错误（4xx/5xx）一律不重试，避免重复提交。
 */
const MAX_RETRY = 3;
const RETRY_BASE_MS = 300;

/** 只有这些方法允许重试（幂等），POST/PATCH/PUT/DELETE 默认不重试避免重复副作用 */
const IDEMPOTENT_METHODS = new Set(['get', 'head', 'options']);

/** 明确安全可重试的非幂等端点（登录是纯查询语义，重试无副作用） */
const RETRY_SAFE_PATHS = ['/auth/login', '/auth/me'];

interface RetryConfig extends AxiosRequestConfig {
  __retryCount?: number;
}

function shouldRetry(error: AxiosError): boolean {
  // 有响应说明网络通了，是业务/HTTP 错误 → 不重试
  if (error.response) return false;
  // 用户主动取消 → 不重试
  if (axios.isCancel(error) || error.code === 'ERR_CANCELED') return false;

  const cfg = error.config as RetryConfig | undefined;
  if (!cfg) return false;

  const method = (cfg.method || 'get').toLowerCase();
  const url = cfg.url || '';
  const isIdempotent = IDEMPOTENT_METHODS.has(method);
  const isSafePath = RETRY_SAFE_PATHS.some((p) => url.includes(p));

  return isIdempotent || isSafePath;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// Response interceptor: 401 处理 + 网络错误重试
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    // ---- 401：清 token 跳登录 ----
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      // 已经在登录页就不跳，避免无限刷新
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }

    // ---- 网络错误：指数退避重试 ----
    if (shouldRetry(error)) {
      const cfg = error.config as RetryConfig;
      cfg.__retryCount = (cfg.__retryCount ?? 0) + 1;

      if (cfg.__retryCount <= MAX_RETRY) {
        const delay = RETRY_BASE_MS * 2 ** (cfg.__retryCount - 1);
        // eslint-disable-next-line no-console
        console.warn(
          `[api] 网络失败，${delay}ms 后重试 (${cfg.__retryCount}/${MAX_RETRY}): ` +
            `${(cfg.method || 'GET').toUpperCase()} ${cfg.url}`,
        );
        await sleep(delay);
        return api(cfg);
      }
    }

    return Promise.reject(error);
  },
);

export default api;

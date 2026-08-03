/**
 * aideStore — AIDE iframe 常驻状态
 *
 * 拆成独立 store 的原因：iframe 挂在 AppLayout（AideHost）里常驻，
 * 但控制它的工具条在 AidePage 里。两者不是父子关系，需要共享状态。
 *
 * 关键设计：
 * - `mounted`：进过一次 /aide 才为 true，之后永远保持（iframe 不卸载）
 * - `visible`：当前是否在 /aide 路由（切走 = false，仅 display:none）
 * - `reloadToken`：递增触发 iframe 手动 reload（不换 key，避免 DOM 重建）
 * - status 结果缓存进 sessionStorage，首屏直接渲染，不等网络
 */
import { create } from 'zustand';
import type { AideStatus } from '../services/aide.service';

const CACHE_KEY = 'ontomind_aide_status';

function readCache(): AideStatus | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    return raw ? (JSON.parse(raw) as AideStatus) : null;
  } catch {
    return null;
  }
}

function writeCache(s: AideStatus | null) {
  try {
    if (s) sessionStorage.setItem(CACHE_KEY, JSON.stringify(s));
    else sessionStorage.removeItem(CACHE_KEY);
  } catch {
    /* sessionStorage 不可用时静默降级 */
  }
}

interface AideState {
  /** 后端探活结果（首屏来自 sessionStorage 缓存，避免白屏） */
  status: AideStatus | null;
  /** iframe 的 src（只在真正变化时才更新，避免无谓重载） */
  embedUrl: string;
  /** 是否已挂载过 iframe（进过一次 /aide 就永久 true） */
  mounted: boolean;
  /** 当前是否显示（切走路由 = false，但 iframe 仍在后台活着） */
  visible: boolean;
  /** iframe 是否已 load 完（控制加载遮罩） */
  loaded: boolean;
  /** 全屏 */
  fullscreen: boolean;
  /** 递增以触发 iframe reload */
  reloadToken: number;

  setStatus: (s: AideStatus | null) => void;
  setVisible: (v: boolean) => void;
  setLoaded: (v: boolean) => void;
  setFullscreen: (v: boolean) => void;
  reload: () => void;
}

const cached = readCache();

export const useAideStore = create<AideState>((set, get) => ({
  status: cached,
  // 有缓存就直接给 embedUrl，让 iframe 首屏立刻开始加载
  embedUrl: cached?.healthy ? cached.embed_url : '',
  mounted: false,
  visible: false,
  loaded: false,
  fullscreen: false,
  reloadToken: 0,

  setStatus: (s) => {
    writeCache(s);
    const nextUrl = s?.healthy ? s.embed_url : '';
    const prevUrl = get().embedUrl;
    set({
      status: s,
      // URL 没变就不动 embedUrl，避免 iframe 无谓重载
      embedUrl: nextUrl || prevUrl,
      // 一旦拿到可用 URL 就永久挂载
      mounted: get().mounted || !!nextUrl,
      // URL 真变了才重置 loaded
      loaded: nextUrl && nextUrl !== prevUrl ? false : get().loaded,
    });
  },

  setVisible: (v) => set({ visible: v }),
  setLoaded: (v) => set({ loaded: v }),
  setFullscreen: (v) => set({ fullscreen: v }),
  reload: () => set((s) => ({ reloadToken: s.reloadToken + 1, loaded: false })),
}));

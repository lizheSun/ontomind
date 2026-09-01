/**
 * AideHost — AIDE iframe 的全局常驻宿主
 *
 * 为什么需要它：
 *   React Router 切走路由会卸载页面组件，iframe 随之销毁；再回到 /aide 时
 *   opencode UI 得从零重新加载（拉 JS bundle、建 SSE、恢复 session 列表），
 *   这就是「每次进 AIDE 都在加载」的根因。
 *
 * 做法：
 *   把 iframe 挂在 AppLayout 里（跟路由同级、常驻不卸载），只用 CSS
 *   `display: none` 控制显隐。切走时 iframe 仍在后台活着（SSE 不断），
 *   切回来是「瞬间显示」而不是「重新加载」。
 *
 * 定位：
 *   在 /aide 时 fixed 覆盖内容区（Header 56 + AIDE 工具条 40 = top 96）；
 *   全屏时 top 降到 40（只留工具条）。工具条本身仍由 AidePage 渲染。
 */
import { useEffect, useRef } from 'react';
import { useAideStore } from '../../stores/aideStore';

/** 无顶栏：工具条贴在内容区顶部 */
const HEADER_H = 0;
/** AIDE 工具条高度 */
const TOOLBAR_H = 40;

interface Props {
  /** 左侧侧边栏宽度，iframe 从该位置开始，占满右侧剩余空间 */
  sidebarW: number;
}

export default function AideHost({ sidebarW }: Props) {
  const embedUrl = useAideStore((s) => s.embedUrl);
  const mounted = useAideStore((s) => s.mounted);
  const visible = useAideStore((s) => s.visible);
  const fullscreen = useAideStore((s) => s.fullscreen);
  const reloadToken = useAideStore((s) => s.reloadToken);
  const setLoaded = useAideStore((s) => s.setLoaded);

  const iframeRef = useRef<HTMLIFrameElement>(null);

  const lastTokenRef = useRef(reloadToken);
  useEffect(() => {
    if (lastTokenRef.current === reloadToken) return;
    lastTokenRef.current = reloadToken;
    const el = iframeRef.current;
    if (!el || !embedUrl) return;
    setLoaded(false);
    el.src = embedUrl;
  }, [reloadToken, embedUrl, setLoaded]);

  if (!mounted || !embedUrl) return null;

  const top = fullscreen ? TOOLBAR_H : HEADER_H + TOOLBAR_H;
  const left = fullscreen ? 0 : sidebarW;

  return (
    <iframe
      ref={iframeRef}
      src={embedUrl}
      title="AIDE — opencode"
      onLoad={() => setLoaded(true)}
      style={{
        position: 'fixed',
        top,
        left,
        width: fullscreen ? '100%' : `calc(100% - ${sidebarW}px)`,
        height: `calc(100vh - ${top}px)`,
        border: 'none',
        display: visible ? 'block' : 'none',
        background: 'var(--bg-root)',
        zIndex: fullscreen ? 1000 : 1,
      }}
      allow="clipboard-read; clipboard-write; fullscreen"
      sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-downloads allow-modals"
    />
  );
}

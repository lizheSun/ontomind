/**
 * 对话工作台（OpenCode）— 视觉严格参考 opencode web/desktop v1.18.4.
 *
 * 布局策略：直接算 100vh - Header(56)，用 fixed height 传给 shell.
 * 挂载期间把外层 Content 的 24px margin / minHeight / overflow 打回 0.
 */
import { useEffect, useState } from 'react';
import { ChatWorkspaceShell, OpencodeGuard } from '../../features/opencode';

const HEADER_HEIGHT = 56;

export default function ChatWorkspacePage() {
  const [availableH, setAvailableH] = useState<number>(
    () => window.innerHeight - HEADER_HEIGHT,
  );

  useEffect(() => {
    const content = document.querySelector<HTMLElement>('.ant-layout-content');
    if (!content) return;
    const prev = {
      m: content.style.margin,
      p: content.style.padding,
      mh: content.style.minHeight,
      of: content.style.overflow,
      h: content.style.height,
    };
    content.style.margin = '0';
    content.style.padding = '0';
    content.style.minHeight = '0';
    content.style.overflow = 'hidden';
    content.style.height = `${availableH}px`;
    const onResize = () => {
      const h = window.innerHeight - HEADER_HEIGHT;
      setAvailableH(h);
      content.style.height = `${h}px`;
    };
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      content.style.margin = prev.m;
      content.style.padding = prev.p;
      content.style.minHeight = prev.mh;
      content.style.overflow = prev.of;
      content.style.height = prev.h;
    };
  }, [availableH]);

  return (
    <div style={{ height: availableH, width: '100%', overflow: 'hidden' }}>
      <OpencodeGuard>
        <ChatWorkspaceShell />
      </OpencodeGuard>
    </div>
  );
}

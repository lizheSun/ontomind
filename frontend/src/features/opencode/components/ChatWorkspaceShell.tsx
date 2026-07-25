/**
 * ChatWorkspaceShell — 两栏严格 flex 布局；header 右侧：Agent Mode + Settings.
 */
import { useMemo, useState } from 'react';
import AgentModeSwitcher from './AgentModeSwitcher';
import ChatComposer from './ChatComposer';
import ChatMessageList from './ChatMessageList';
import ExpertPicker from './ExpertPicker';
import PermissionDialog from './PermissionDialog';
import SessionListSidebar from './SessionListSidebar';
import SettingsDialog from './SettingsDialog';
import { useEventStream } from '../hooks/useEventStream';
import { useOpencodeStore } from '../stores/opencodeStore';

// 极简 6-齿齿轮 + 中心圆孔（比默认 8-齿更利落）
function IconSettings() {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="8" cy="8" r="2" />
      <path d="M8 1.6v1.7M8 12.7v1.7M14.4 8h-1.7M3.3 8H1.6M12.53 3.47l-1.2 1.2M4.67 11.33l-1.2 1.2M12.53 12.53l-1.2-1.2M4.67 4.67l-1.2-1.2" />
    </svg>
  );
}

export default function ChatWorkspaceShell() {
  useEventStream(true);

  const activeId = useOpencodeStore((s) => s.activeSessionId);
  const sessions = useOpencodeStore((s) => s.sessions);
  const active = useMemo(
    () => sessions.find((s) => s.id === activeId),
    [sessions, activeId],
  );

  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <div
      className="oc-scope oc-workspace"
      style={{
        display: 'flex',
        height: '100%',
        width: '100%',
        overflow: 'hidden',
        background: 'var(--oc-bg-base)',
      }}
    >
      <div style={{ width: 280, flexShrink: 0, height: '100%', overflow: 'hidden' }}>
        <SessionListSidebar />
      </div>
      <div
        style={{
          flex: 1,
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden',
        }}
      >
        <div className="oc-header" style={{ flexShrink: 0 }}>
          <span className="oc-header-title">
            {active?.title || (active ? '未命名会话' : '新会话')}
          </span>
          {active && <span className="oc-header-sub">{active.id.slice(0, 12)}</span>}
          <div
            style={{
              marginLeft: 'auto',
              display: 'flex',
              gap: 10,
              alignItems: 'center',
            }}
          >
            <ExpertPicker />
            <AgentModeSwitcher />
            <button
              type="button"
              className="oc-icon-btn"
              onClick={() => setSettingsOpen(true)}
              title="设置"
              aria-label="设置"
            >
              <IconSettings />
            </button>
          </div>
        </div>
        <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
          <ChatMessageList />
        </div>
        <div style={{ flexShrink: 0 }}>
          <ChatComposer />
        </div>
      </div>
      <PermissionDialog />
      <SettingsDialog open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}

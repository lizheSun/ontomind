import { useEffect } from 'react';
import { Button, Popconfirm } from 'antd';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { StatusDot } from '../../components/common/StatusDot';
import { useChatStore } from '../../stores/chatStore';
import type { PluginId } from '../../types/harness';

function relTime(iso?: string | null): string {
  if (!iso) return '';
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return '';
  const sec = Math.max(0, (Date.now() - t) / 1000);
  if (sec < 60) return '刚刚';
  if (sec < 3600) return `${Math.floor(sec / 60)} 分钟前`;
  if (sec < 86400) return `${Math.floor(sec / 3600)} 小时前`;
  if (sec < 86400 * 7) return `${Math.floor(sec / 86400)} 天前`;
  return new Date(iso).toLocaleDateString();
}

const PLUGIN_LABEL: Record<PluginId, string> = {
  opencode: 'OpenCode',
  dsh: 'DSH',
};

export function ChatSessionRail() {
  const sessions = useChatStore((s) => s.sessions);
  const activeId = useChatStore((s) => s.activeId);
  const plugins = useChatStore((s) => s.plugins);
  const loadSessions = useChatStore((s) => s.loadSessions);
  const loadPlugins = useChatStore((s) => s.loadPlugins);
  const select = useChatStore((s) => s.select);
  const createAndSelect = useChatStore((s) => s.createAndSelect);
  const remove = useChatStore((s) => s.remove);

  useEffect(() => {
    void loadPlugins();
    void loadSessions();
  }, [loadPlugins, loadSessions]);

  return (
    <div className="om-chat-rail">
      <div className="om-chat-rail-actions">
        <Button type="primary" icon={<PlusOutlined />} block onClick={() => void createAndSelect()}>
          新会话
        </Button>
      </div>
      <div className="om-chat-plugin-row">
        {plugins.map((p) => (
          <span key={p.id} className="om-chat-plugin-chip" title={p.detail}>
            <StatusDot tone={p.available ? 'ok' : 'err'} />
            {p.label}
          </span>
        ))}
      </div>
      <div className="om-chat-sess-list">
        {sessions.length === 0 ? (
          <div className="om-chat-sess-empty">还没有会话。点上方开始。</div>
        ) : (
          sessions.map((s) => {
            const active = s.id === activeId;
            return (
              <div key={s.id} className={active ? 'om-chat-sess active' : 'om-chat-sess'}>
                <button type="button" className="om-chat-sess-main" onClick={() => void select(s.id)}>
                  <span className="om-chat-sess-title">{s.title || '新会话'}</span>
                  <span className="om-chat-sess-meta">
                    {PLUGIN_LABEL[s.plugin_id] || s.plugin_id}
                    {s.updated_at || s.created_at ? ` · ${relTime(s.updated_at || s.created_at)}` : ''}
                  </span>
                </button>
                <Popconfirm
                  title="删除这个会话？"
                  okText="删除"
                  cancelText="取消"
                  onConfirm={() => void remove(s.id)}
                >
                  <button type="button" className="om-chat-sess-del" aria-label="删除会话">
                    <DeleteOutlined />
                  </button>
                </Popconfirm>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

/**
 * SessionListSidebar — opencode-style session list.
 */
import { useMemo, useState } from 'react';
import { message } from 'antd';
import { useSessions } from '../hooks/useSessions';

function IconPlus() {
  return (
    <svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" aria-hidden="true">
      <path d="M8 3.5v9M3.5 8h9" />
    </svg>
  );
}
// 精细开口箭头（不是双圆弧）
function IconRefresh() {
  return (
    <svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2.5 8a5.5 5.5 0 0 1 9.6-3.65" />
      <path d="M12.5 2.5v2.5H10" />
      <path d="M13.5 8a5.5 5.5 0 0 1-9.6 3.65" />
      <path d="M3.5 13.5V11H6" />
    </svg>
  );
}
// 铅笔（简洁 45° 一刀）
function IconEdit() {
  return (
    <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M10.5 2.5l3 3-7.5 7.5H3v-3l7.5-7.5z" />
      <path d="M9.5 3.5l3 3" />
    </svg>
  );
}
// 垃圾桶（editorial 极简：无桶身竖线）
function IconTrash() {
  return (
    <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 4.5h10" />
      <path d="M6.5 4.5V3.2c0-.4.3-.7.7-.7h1.6c.4 0 .7.3.7.7v1.3" />
      <path d="M4.5 4.5l.5 8.5c.05.7.6 1.2 1.3 1.2h3.4c.7 0 1.25-.5 1.3-1.2L11.5 4.5" />
    </svg>
  );
}

export default function SessionListSidebar() {
  const { sessions, activeSessionId, load, create, remove, rename, select } = useSessions();
  const [filter, setFilter] = useState('');
  const [renaming, setRenaming] = useState<{ id: string; value: string } | null>(null);

  const filtered = useMemo(() => {
    if (!filter) return sessions;
    const kw = filter.toLowerCase();
    return sessions.filter((s) => (s.title || s.id).toLowerCase().includes(kw));
  }, [sessions, filter]);

  const onCreate = async () => {
    try {
      await create('新对话');
    } catch (err) {
      message.error(err instanceof Error ? err.message : '创建失败');
    }
  };

  const onDelete = async (id: string) => {
    try {
      await remove(id);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '删除失败');
    }
  };

  const onRename = async (id: string, next: string) => {
    if (!next.trim()) return setRenaming(null);
    try {
      await rename(id, next.trim());
    } catch (err) {
      message.error(err instanceof Error ? err.message : '重命名失败');
    } finally {
      setRenaming(null);
    }
  };

  return (
    <div className="oc-sidebar">
      <div className="oc-sidebar-header">
        <div className="oc-sidebar-actions" style={{ justifyContent: 'space-between' }}>
          <span className="oc-sidebar-title">Sessions</span>
          <div className="oc-sidebar-actions">
            <button className="oc-icon-btn" onClick={() => void load()} title="刷新">
              <IconRefresh />
            </button>
            <button className="oc-icon-btn" onClick={() => void onCreate()} title="新建会话">
              <IconPlus />
            </button>
          </div>
        </div>
        <input
          type="text"
          className="oc-sidebar-search"
          placeholder="搜索会话"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      <div className="oc-sidebar-list">
        {filtered.length === 0 ? (
          <div className="oc-empty" style={{ padding: 24 }}>
            {filter ? '无匹配' : '暂无会话'}
          </div>
        ) : (
          filtered.map((s) => {
            const active = s.id === activeSessionId;
            const isRenaming = renaming?.id === s.id;
            return (
              <div
                key={s.id}
                className="oc-session-item"
                data-active={active}
                onClick={() => select(s.id)}
              >
                {isRenaming ? (
                  <input
                    autoFocus
                    className="oc-sidebar-search"
                    style={{ height: 24 }}
                    value={renaming.value}
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => setRenaming({ id: s.id, value: e.target.value })}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') void onRename(s.id, renaming.value);
                      if (e.key === 'Escape') setRenaming(null);
                    }}
                    onBlur={() => void onRename(s.id, renaming.value)}
                  />
                ) : (
                  <span
                    className="oc-session-item-title"
                    data-empty={!s.title || undefined}
                    title={s.title}
                  >
                    {s.title || '未命名'}
                  </span>
                )}
                <div className="oc-session-item-actions">
                  <button
                    className="oc-icon-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      setRenaming({ id: s.id, value: s.title || '' });
                    }}
                    title="重命名"
                  >
                    <IconEdit />
                  </button>
                  <button
                    className="oc-icon-btn"
                    data-danger="true"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm(`删除 "${s.title || s.id}" ?`)) void onDelete(s.id);
                    }}
                    title="删除"
                  >
                    <IconTrash />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

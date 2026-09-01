/**
 * 任务看板 — 对齐 Yao：列是工作流，卡片即会话。
 * 新任务 / 点卡片在本页打开对话层，不跳到 /chat。
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { App, Button, Input, Popconfirm, Select } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseOutlined,
  DeleteOutlined,
  PlusOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { EmptyState } from '../../components/common/EmptyState';
import { StatusDot } from '../../components/common/StatusDot';
import { kanbanService } from '../../services/kanban.service';
import { useChatStore } from '../../stores/chatStore';
import { useKanbanStore } from '../../stores/kanbanStore';
import type { KanbanColumn, KanbanTask } from '../../types/kanban';
import { ChatPane } from '../chat/ChatPane';

const FILTERS: { key: string; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'running', label: '运行中' },
  { key: 'waiting', label: '等待中' },
  { key: 'completed', label: '已完成' },
  { key: 'failed', label: '失败' },
];

const STATUS_META: Record<string, { label: string; tone: 'ok' | 'warn' | 'err' | 'idle' | 'run' }> = {
  pending: { label: '待处理', tone: 'idle' },
  running: { label: '运行中', tone: 'run' },
  waiting: { label: '等待中', tone: 'warn' },
  completed: { label: '已完成', tone: 'ok' },
  failed: { label: '失败', tone: 'err' },
};

const PLUGIN_LABEL: Record<string, string> = { opencode: 'OpenCode', dsh: 'DSH' };

function colIcon(name: string) {
  if (name.includes('完成') || name.includes('Done')) return <CheckCircleOutlined />;
  if (name.includes('进行') || name.includes('Progress')) return <SyncOutlined />;
  return <ClockCircleOutlined />;
}

export default function KanbanPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const { boardId } = useParams();
  const [params, setParams] = useSearchParams();
  const boards = useKanbanStore((s) => s.boards);
  const board = useKanbanStore((s) => s.board);
  const tasks = useKanbanStore((s) => s.tasks);
  const loading = useKanbanStore((s) => s.loading);
  const error = useKanbanStore((s) => s.error);
  const loadBoards = useKanbanStore((s) => s.loadBoards);
  const loadBoard = useKanbanStore((s) => s.loadBoard);
  const createBoard = useKanbanStore((s) => s.createBoard);
  const streaming = useChatStore((s) => s.streaming);
  const selectSession = useChatStore((s) => s.select);

  const [filter, setFilter] = useState('all');
  const [colDraft, setColDraft] = useState<string | null>(null);
  const taskId = Number(params.get('task') || 0) || null;
  const selected = tasks.find((t) => t.id === taskId) ?? null;
  const wasStreaming = useRef(false);

  useEffect(() => {
    void loadBoards();
  }, [loadBoards]);

  useEffect(() => {
    if (boardId) {
      void loadBoard(Number(boardId), filter);
      return;
    }
    void (async () => {
      const list = await loadBoards();
      if (list[0]) navigate(`/board/${list[0].id}`, { replace: true });
    })();
  }, [boardId, filter, loadBoard, loadBoards, navigate]);

  useEffect(() => {
    if (!selected?.session_id) return;
    const st = useChatStore.getState();
    if (st.activeId !== selected.session_id) void selectSession(selected.session_id);
    const want = selected.plugin_id;
    if (want === 'opencode' || want === 'dsh') {
      const p = st.plugins.find((x) => x.id === want);
      st.setPluginId(p?.available ? want : (st.plugins.find((x) => x.available)?.id ?? st.pluginId));
    }
  }, [selected?.session_id, selectSession]);

  useEffect(() => {
    if (wasStreaming.current && !streaming && boardId) {
      void loadBoard(Number(boardId), filter);
    }
    wasStreaming.current = streaming;
  }, [streaming, boardId, filter, loadBoard]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape' || !params.get('task')) return;
      setParams({}, { replace: true });
      void useChatStore.getState().select(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [params, setParams]);

  const byColumn = useMemo(() => {
    const map = new Map<number, KanbanTask[]>();
    for (const t of tasks) {
      if (t.column_id == null) continue;
      const arr = map.get(t.column_id) ?? [];
      arr.push(t);
      map.set(t.column_id, arr);
    }
    for (const arr of map.values()) arr.sort((a, b) => a.position - b.position);
    return map;
  }, [tasks]);

  const refresh = () => {
    if (boardId) void loadBoard(Number(boardId), filter);
  };

  const openTask = (task: KanbanTask) => {
    setParams({ task: String(task.id) }, { replace: true });
  };

  const closeTask = () => {
    setParams({}, { replace: true });
    void selectSession(null);
  };

  const spawnTask = async (columnId?: number) => {
    if (!board) return;
    try {
      const st = useChatStore.getState();
      const available = st.plugins.find((p) => p.available)?.id ?? st.pluginId;
      const pluginId = st.plugins.find((p) => p.id === st.pluginId)?.available ? st.pluginId : available;
      const task = await kanbanService.createTask(board.id, {
        title: '新任务',
        plugin_id: pluginId,
        column_id: columnId ?? board.columns[0]?.id,
      });
      st.setPluginId(pluginId);
      await loadBoard(board.id, filter);
      openTask(task);
    } catch (e) {
      const msg =
        (e as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        (e instanceof Error ? e.message : '创建失败');
      message.error(msg);
    }
  };

  const onDrop = async (column: KanbanColumn, position: number, ev: React.DragEvent) => {
    ev.preventDefault();
    const raw = ev.dataTransfer.getData('text/om-task') || ev.dataTransfer.getData('text/plain');
    const id = Number(raw);
    if (!id) return;
    try {
      await kanbanService.moveTask(id, column.id, position);
      refresh();
    } catch (e) {
      message.error(e instanceof Error ? e.message : '移动失败');
    }
  };

  const addColumn = async () => {
    if (!board || !colDraft?.trim()) return;
    await kanbanService.createColumn(board.id, colDraft.trim());
    setColDraft(null);
    refresh();
  };

  if (!boardId && boards.length === 0 && !loading) {
    return (
      <div className="om-page page-enter">
        <EmptyState title="还没有看板" description="创建一个看板，把会话做成可拖的任务卡。" />
      </div>
    );
  }

  return (
    <div className={selected ? 'om-kanban has-chat' : 'om-kanban'}>
      <div className="om-kanban-board">
        <div className="om-kanban-bar">
          <Select
            className="om-kanban-board-sel"
            value={board?.id}
            variant="borderless"
            popupMatchSelectWidth={false}
            options={boards.map((b) => ({ value: b.id, label: b.name }))}
            onChange={(id) => navigate(`/board/${id}`)}
          />
          <Button
            size="small"
            className="om-kanban-new-board"
            icon={<PlusOutlined />}
            onClick={async () => {
              const b = await createBoard('新看板');
              navigate(`/board/${b.id}`);
            }}
          >
            新看板
          </Button>
          <div className="om-kanban-filters" role="tablist" aria-label="运行状态">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                role="tab"
                aria-selected={filter === f.key}
                className={filter === f.key ? 'om-kanban-filter active' : 'om-kanban-filter'}
                onClick={() => setFilter(f.key)}
              >
                {f.label}
              </button>
            ))}
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => void spawnTask()}>
            新任务
          </Button>
        </div>
        {error ? <div className="om-chat-error om-chat-error-bar">{error}</div> : null}
        <div className="om-kanban-cols">
          {(board?.columns ?? []).map((col) => {
            const colTasks = byColumn.get(col.id) ?? [];
            return (
              <section
                key={col.id}
                className="om-kanban-col"
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => void onDrop(col, colTasks.length + 1, e)}
              >
                <header className="om-kanban-col-head">
                  <span className="om-kanban-col-ico" style={{ color: col.color || 'var(--accent)' }}>
                    {colIcon(col.name)}
                  </span>
                  <strong>{col.name}</strong>
                  <span className="om-kanban-col-n">{colTasks.length}</span>
                  {board && board.columns.length > 1 ? (
                    <Popconfirm
                      title="删除这一列？任务会移到第一列。"
                      okText="删除"
                      cancelText="取消"
                      onConfirm={async () => {
                        await kanbanService.deleteColumn(col.id);
                        refresh();
                      }}
                    >
                      <button type="button" className="om-kanban-col-del" aria-label={`删除${col.name}`}>
                        <DeleteOutlined />
                      </button>
                    </Popconfirm>
                  ) : null}
                </header>
                <div className="om-kanban-col-body">
                  {colTasks.map((t, idx) => (
                    <TaskCard
                      key={t.id}
                      task={t}
                      active={t.id === taskId}
                      onOpen={() => openTask(t)}
                      onDragOverCard={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                      }}
                      onDropCard={(e) => {
                        e.stopPropagation();
                        void onDrop(col, idx + 1, e);
                      }}
                      onDelete={async () => {
                        if (t.id === taskId) closeTask();
                        await kanbanService.deleteTask(t.id);
                        refresh();
                      }}
                    />
                  ))}
                  <button type="button" className="om-kanban-add-in" onClick={() => void spawnTask(col.id)}>
                    <PlusOutlined /> 添加任务
                  </button>
                </div>
              </section>
            );
          })}
          {colDraft != null ? (
            <div className="om-kanban-col om-kanban-col-draft">
              <Input
                autoFocus
                placeholder="列名称"
                value={colDraft}
                onChange={(e) => setColDraft(e.target.value)}
                onPressEnter={() => void addColumn()}
                onBlur={() => {
                  if (!colDraft.trim()) setColDraft(null);
                }}
              />
            </div>
          ) : (
            <button type="button" className="om-kanban-add-col" onClick={() => setColDraft('')}>
              <PlusOutlined /> 新分组
            </button>
          )}
        </div>
      </div>

      {selected ? (
        <aside className="om-kanban-chat" aria-label="任务会话">
          <header className="om-kanban-chat-head">
            <StatusDot tone={STATUS_META[selected.run_status]?.tone || 'idle'} />
            <div className="om-kanban-chat-title">{selected.title || '新任务'}</div>
            <span className="om-kanban-pill">{PLUGIN_LABEL[selected.plugin_id] || selected.plugin_id}</span>
            <button type="button" className="om-kanban-chat-close" aria-label="关闭会话" onClick={closeTask}>
              <CloseOutlined />
            </button>
          </header>
          <ChatPane allowEmptyCreate={false} />
        </aside>
      ) : null}
    </div>
  );
}

function TaskCard({
  task,
  active,
  onOpen,
  onDropCard,
  onDragOverCard,
  onDelete,
}: {
  task: KanbanTask;
  active: boolean;
  onOpen: () => void;
  onDropCard: (e: React.DragEvent) => void;
  onDragOverCard: (e: React.DragEvent) => void;
  onDelete: () => Promise<void>;
}) {
  const dragged = useRef(false);
  const st = STATUS_META[task.run_status] || STATUS_META.pending;
  return (
    <article
      className={active ? 'om-kanban-card active' : 'om-kanban-card'}
      draggable
      data-task-id={task.id}
      onDragStart={(e) => {
        dragged.current = true;
        e.dataTransfer.setData('text/om-task', String(task.id));
        e.dataTransfer.setData('text/plain', String(task.id));
        e.dataTransfer.effectAllowed = 'move';
      }}
      onDragEnd={() => {
        window.setTimeout(() => {
          dragged.current = false;
        }, 0);
      }}
      onDragOver={onDragOverCard}
      onDrop={onDropCard}
      onClick={() => {
        if (dragged.current) return;
        onOpen();
      }}
    >
      <div className="om-kanban-card-main">
        <div className="om-kanban-card-title">{task.title}</div>
        {task.summary ? <p className="om-kanban-card-sum">{task.summary}</p> : null}
        <div className="om-kanban-card-meta">
          <span className="om-kanban-pill">{PLUGIN_LABEL[task.plugin_id] || task.plugin_id}</span>
          <span className="om-kanban-pill">
            <StatusDot tone={st.tone} /> {st.label}
          </span>
        </div>
      </div>
      <div className="om-kanban-card-ops">
        <Popconfirm title="删除任务？" okText="删除" cancelText="取消" onConfirm={() => void onDelete()}>
          <button type="button" title="删除" onClick={(e) => e.stopPropagation()}>
            <DeleteOutlined />
          </button>
        </Popconfirm>
      </div>
    </article>
  );
}

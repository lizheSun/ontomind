import { useEffect, useMemo, useRef, useState, type DragEvent, type KeyboardEvent, type ReactNode } from 'react';
import { App as AntApp, Button, Dropdown, Input, Modal, Tooltip } from 'antd';
import {
  AudioOutlined,
  CloseOutlined,
  CodeOutlined,
  DownOutlined,
  FolderOpenOutlined,
  HighlightOutlined,
  HomeOutlined,
  PaperClipOutlined,
  RobotOutlined,
  SendOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { StatusDot } from '../../components/common/StatusDot';
import { harnessService } from '../../services/harness.service';
import { useChatStore } from '../../stores/chatStore';
import type { PluginId } from '../../types/harness';
import { AGENT_META } from './agentMeta';
import { useSpeechDictation } from './useSpeechDictation';

function baseName(path: string): string {
  const t = path.replace(/[/\\]+$/, '');
  const i = Math.max(t.lastIndexOf('/'), t.lastIndexOf('\\'));
  return i >= 0 ? t.slice(i + 1) || t : t;
}

function formatSize(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function appendDraft(el: HTMLTextAreaElement, chunk: string) {
  const t = chunk.trim();
  if (!t) return;
  const cur = el.value;
  const needSpace = cur.length > 0 && !/\s$/.test(cur);
  el.value = cur + (needSpace ? ' ' : '') + t;
  el.style.height = 'auto';
  el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  el.dispatchEvent(new Event('input', { bubbles: true }));
}

export function ChatComposer() {
  const { message } = AntApp.useApp();
  const plugins = useChatStore((s) => s.plugins);
  const pluginId = useChatStore((s) => s.pluginId);
  const streaming = useChatStore((s) => s.streaming);
  const uploading = useChatStore((s) => s.uploading);
  const workspacePath = useChatStore((s) => s.workspacePath);
  const workspaces = useChatStore((s) => s.workspaces);
  const attachments = useChatStore((s) => s.attachments);
  const switchPlugin = useChatStore((s) => s.switchPlugin);
  const setWorkspace = useChatStore((s) => s.setWorkspace);
  const loadWorkspaces = useChatStore((s) => s.loadWorkspaces);
  const uploadFiles = useChatStore((s) => s.uploadFiles);
  const removeAttachment = useChatStore((s) => s.removeAttachment);
  const send = useChatStore((s) => s.send);
  const stop = useChatStore((s) => s.stop);

  const ref = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const prevDraft = useRef('');
  const [hasText, setHasText] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [pathOpen, setPathOpen] = useState(false);
  const [pathDraft, setPathDraft] = useState('');

  const current = plugins.find((p) => p.id === pluginId);
  const meta = AGENT_META[pluginId];
  const pluginDown = current ? !current.available : false;
  const busy = streaming || uploading || optimizing;

  const { supported: speechOk, listening, toggle: toggleMic, stop: stopMic } = useSpeechDictation((chunk) => {
    if (ref.current) appendDraft(ref.current, chunk);
    setHasText(Boolean(ref.current?.value.trim()));
  });

  useEffect(() => {
    ref.current?.focus();
  }, [pluginId]);

  useEffect(() => {
    void loadWorkspaces();
  }, [loadWorkspaces]);

  const grow = () => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
    setHasText(Boolean(el.value.trim()));
  };

  const doSend = () => {
    const el = ref.current;
    if (!el || pluginDown || streaming || uploading) return;
    const v = el.value.trim();
    if (!v && attachments.length === 0) return;
    stopMic();
    el.value = '';
    el.style.height = 'auto';
    setHasText(false);
    prevDraft.current = '';
    void send(v);
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      doSend();
    }
  };

  const pickFiles = (list: FileList | File[] | null) => {
    if (!list || streaming) return;
    const files = Array.from(list);
    if (files.length) void uploadFiles(files);
  };

  const optimize = async () => {
    const el = ref.current;
    const draft = el?.value.trim() || '';
    if (!draft || optimizing) return;
    setOptimizing(true);
    try {
      const next = await harnessService.optimizePrompt(draft, pluginId);
      if (el) {
        prevDraft.current = draft;
        el.value = next;
        grow();
        el.focus();
      }
      message.success('已优化。再点一次可撤销。');
    } catch (e) {
      const msg =
        (e as { response?: { data?: { message?: string; code?: string } } }).response?.data?.message ||
        (e instanceof Error ? e.message : '优化失败');
      const code = (e as { response?: { data?: { code?: string } } }).response?.data?.code;
      message.error(code === 'LLM_NOT_CONFIGURED' ? '还没配置 LLM，去 GovOps → LLM 配置' : msg);
    } finally {
      setOptimizing(false);
    }
  };

  const undoOrOptimize = () => {
    const el = ref.current;
    if (el && prevDraft.current && el.value.trim() && el.value.trim() !== prevDraft.current) {
      el.value = prevDraft.current;
      prevDraft.current = '';
      grow();
      message.info('已还原上一稿');
      return;
    }
    void optimize();
  };

  const applyWorkspace = async (path: string) => {
    try {
      await setWorkspace(path);
      message.success(`工作区：${baseName(path) || path}`);
    } catch {
      /* store 已写 error */
    }
  };

  const confirmPath = async () => {
    const p = pathDraft.trim();
    if (!p) return;
    try {
      await setWorkspace(p);
      setPathOpen(false);
      message.success(`工作区：${baseName(p)}`);
    } catch (e) {
      message.error(e instanceof Error ? e.message : '路径无效');
    }
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    pickFiles(e.dataTransfer.files);
  };

  const agentItems = useMemo(
    () =>
      (plugins.length
        ? plugins
        : ([
            { id: 'opencode' as const, label: 'OpenCode', available: false, detail: '', binary: '' },
            { id: 'dsh' as const, label: 'DeepSeek Harness', available: false, detail: '', binary: '' },
          ] as const)
      ).map((p) => ({
        key: p.id,
        label: (
          <div className="om-chat-agent-item">
            <div className="om-chat-agent-item-head">
              <StatusDot tone={p.available ? 'ok' : 'err'} />
              <strong>{AGENT_META[p.id as PluginId]?.name ?? p.label}</strong>
              <span>{p.available ? '可用' : '未就绪'}</span>
            </div>
            <p>{AGENT_META[p.id as PluginId]?.blurb || p.detail}</p>
          </div>
        ),
      })),
    [plugins],
  );

  const wsItems = useMemo(() => {
    const items: { key: string; label: ReactNode }[] = [];
    if (workspacePath) {
      items.push({
        key: 'current',
        label: (
          <span>
            <FolderOpenOutlined /> 当前 · {baseName(workspacePath)}
          </span>
        ),
      });
    }
    if (workspaces?.home) {
      items.push({
        key: 'home',
        label: (
          <span>
            <HomeOutlined /> 主目录
          </span>
        ),
      });
    }
    for (const r of workspaces?.recents ?? []) {
      if (r.path === workspacePath || r.path === workspaces?.home) continue;
      items.push({
        key: r.path,
        label: (
          <span>
            <FolderOpenOutlined /> {r.label}
          </span>
        ),
      });
    }
    items.push({ key: 'other', label: '其他路径…' });
    return items;
  }, [workspacePath, workspaces]);

  const canSend = !pluginDown && !streaming && !uploading && (hasText || attachments.length > 0);

  return (
    <div className="om-chat-composer">
      <div
        className={dragOver ? 'om-chat-card om-chat-card-drag' : 'om-chat-card'}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        <div className="om-chat-card-head">
          <Dropdown
            trigger={['click']}
            menu={{
              items: agentItems,
              onClick: ({ key }) => void switchPlugin(key as PluginId),
            }}
          >
            <button type="button" className="om-chat-agent" aria-label="切换助手">
              <span className="om-chat-agent-mark">
                {pluginId === 'opencode' ? <CodeOutlined /> : <RobotOutlined />}
              </span>
              <span className="om-chat-agent-name">{meta.name}</span>
              <StatusDot tone={current?.available ? 'ok' : 'err'} title={current?.detail} />
              <DownOutlined className="om-chat-caret" />
            </button>
          </Dropdown>
        </div>

        <div className="om-chat-card-body">
          <textarea
            ref={ref}
            className="om-chat-input"
            rows={2}
            placeholder={meta.placeholder}
            disabled={streaming}
            onKeyDown={onKey}
            onInput={grow}
          />
          <div className="om-chat-card-actions">
            <Tooltip title={speechOk ? (listening ? '停止语音' : '语音输入，识别结果追加到草稿') : '当前浏览器不支持语音识别'}>
              <button
                type="button"
                className={listening ? 'om-chat-icon-btn om-chat-icon-btn-on' : 'om-chat-icon-btn'}
                disabled={!speechOk || streaming}
                aria-label="语音输入"
                aria-pressed={listening}
                onClick={toggleMic}
              >
                <AudioOutlined />
              </button>
            </Tooltip>
            {streaming ? (
              <Button danger shape="circle" icon={<StopOutlined />} onClick={stop} aria-label="停止" />
            ) : (
              <Button
                type="primary"
                shape="circle"
                icon={<SendOutlined />}
                onClick={doSend}
                disabled={!canSend}
                aria-label="发送"
              />
            )}
          </div>
        </div>

        {attachments.length ? (
          <div className="om-chat-chips">
            {attachments.map((f) => (
              <span key={f.rel} className="om-chat-chip">
                <PaperClipOutlined />
                <span className="om-chat-chip-name" title={f.rel}>
                  {f.name}
                </span>
                <span className="om-chat-chip-size">{formatSize(f.size)}</span>
                <button type="button" aria-label={`移除 ${f.name}`} onClick={() => removeAttachment(f.rel)}>
                  <CloseOutlined />
                </button>
              </span>
            ))}
          </div>
        ) : null}

        <div className="om-chat-card-bar">
          <Dropdown
            trigger={['click']}
            onOpenChange={(open) => {
              if (open) void loadWorkspaces();
            }}
            menu={{
              items: wsItems,
              onClick: ({ key }) => {
                if (key === 'current') return;
                if (key === 'other') {
                  setPathDraft(workspacePath);
                  setPathOpen(true);
                  return;
                }
                if (key === 'home' && workspaces?.home) {
                  void applyWorkspace(workspaces.home);
                  return;
                }
                void applyWorkspace(key);
              },
            }}
          >
            <button type="button" className="om-chat-ws" title={workspacePath || '选择工作区'}>
              <FolderOpenOutlined />
              <span>{workspacePath ? baseName(workspacePath) : '选择工作区'}</span>
              <DownOutlined className="om-chat-caret" />
            </button>
          </Dropdown>
          <span className="om-chat-card-bar-grow" />
          <Tooltip title={uploading ? '正在上传…' : '上传文件到工作区 inbox'}>
            <button
              type="button"
              className="om-chat-icon-btn"
              disabled={busy}
              aria-label="上传文件"
              onClick={() => fileRef.current?.click()}
            >
              <PaperClipOutlined />
            </button>
          </Tooltip>
          <Tooltip title={hasText ? '优化提示，写得更清楚；再点可撤销' : '先写一点草稿再优化'}>
            <button
              type="button"
              className="om-chat-icon-btn"
              disabled={busy || !hasText}
              aria-label="优化提示"
              onClick={undoOrOptimize}
            >
              <HighlightOutlined />
            </button>
          </Tooltip>
        </div>
        <input
          ref={fileRef}
          type="file"
          multiple
          hidden
          onChange={(e) => {
            pickFiles(e.target.files);
            e.target.value = '';
          }}
        />
      </div>
      {listening ? <div className="om-chat-hint">正在听… 说完再点一次麦克风结束</div> : null}
      {pluginDown && current?.detail ? <div className="om-chat-hint">{current.detail}</div> : null}

      <Modal
        title="工作区路径"
        open={pathOpen}
        onOk={() => void confirmPath()}
        onCancel={() => setPathOpen(false)}
        okText="使用"
        cancelText="取消"
        destroyOnHidden
        mask={{ closable: true }}
      >
        <p className="om-chat-path-help">填写本机绝对路径。插件会在这个目录里读写文件。</p>
        <Input
          value={pathDraft}
          placeholder="/Users/you/project"
          onChange={(e) => setPathDraft(e.target.value)}
          onPressEnter={() => void confirmPath()}
        />
      </Modal>
    </div>
  );
}

/**
 * 智能数开 IDE — Cursor-like 三栏工作台
 * 左：文件树 · 中：SQL 编辑器 + 执行结果/过程 · 右：Agent
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Editor from '@monaco-editor/react';
import {
  App as AntApp,
  Button,
  ConfigProvider,
  Empty,
  Input,
  Select,
  Spin,
  Table,
  theme,
} from 'antd';
import {
  CaretRightOutlined,
  CloseOutlined,
  FileTextOutlined,
  FolderOpenOutlined,
  LayoutOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  SendOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { Panel, PanelGroup, PanelResizeHandle, type ImperativePanelHandle } from 'react-resizable-panels';
import type { OpencodeClient } from '@opencode-ai/sdk/client';
import {
  discoverContainerServices,
  listContainerServices,
} from '../../../services/compute.service';
import { executeSql, listDataSources } from '../../../services/dataops.service';
import type { ContainerServiceInfo } from '../../../types/compute';
import type { DataSource, ExecuteSqlLog, ExecuteSqlResult } from '../../../types/dataops';
import type {
  AssistantPartUpdate,
  OpencodeAgent,
  OpencodeCommand,
  OpencodeEvent,
} from '../../../services/opencodeSdk';
import {
  abortSession,
  createChatSession,
  createServeClient,
  extractAssistantParts,
  extractSqlBlock,
  healthCheck,
  isSessionBusy,
  isSessionError,
  isSessionIdle,
  listAgents,
  listCommands,
  promptAsync,
  runCommand,
  subscribeSessionEvents,
} from '../../../services/opencodeSdk';
import { ETL_FILE_TREE, flattenEtlFiles, type EtlFileNode } from './etlFiles';
import './SmartDevPage.css';

const { TextArea } = Input;
const LOCAL_SERVE_URL = 'http://127.0.0.1:4096';

type ChatRole = 'user' | 'assistant' | 'system';
type PanelTab = 'result' | 'output';
type MentionsMode = 'none' | 'slash' | 'at';

interface ToolCallView {
  partId: string;
  tool: string;
  status: string;
  title?: string;
  input?: unknown;
  output?: string;
  error?: string;
}

interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  reasoning?: string;
  tools?: ToolCallView[];
  streaming?: boolean;
}

interface ServeOption {
  key: string;
  label: string;
  baseUrl: string;
  kind: 'local' | 'container';
  service?: ContainerServiceInfo;
}

export default function SmartDevPage() {
  const { message } = AntApp.useApp();

  const filesPanelRef = useRef<ImperativePanelHandle>(null);
  const agentPanelRef = useRef<ImperativePanelHandle>(null);
  const resultPanelRef = useRef<ImperativePanelHandle>(null);

  const [filesCollapsed, setFilesCollapsed] = useState(false);
  const [agentCollapsed, setAgentCollapsed] = useState(false);
  const [resultCollapsed, setResultCollapsed] = useState(false);
  const [panelTab, setPanelTab] = useState<PanelTab>('result');

  const files = useMemo(() => flattenEtlFiles(), []);
  const [fileContents, setFileContents] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const f of flattenEtlFiles()) init[f.id] = f.content || '';
    return init;
  });
  const [activeFileId, setActiveFileId] = useState<string>(files[0]?.id ?? '');
  const activeFile = files.find((f) => f.id === activeFileId) ?? null;
  const sql = activeFileId ? fileContents[activeFileId] ?? '' : '';

  const [sources, setSources] = useState<DataSource[]>([]);
  const [executorId, setExecutorId] = useState<number | undefined>();
  const [executing, setExecuting] = useState(false);
  const [execLogs, setExecLogs] = useState<ExecuteSqlLog[]>([]);
  const [execResult, setExecResult] = useState<ExecuteSqlResult | null>(null);

  const [services, setServices] = useState<ContainerServiceInfo[]>([]);
  const [servicesLoading, setServicesLoading] = useState(false);
  const [serveKey, setServeKey] = useState<string>('local');
  const [serveReady, setServeReady] = useState(false);
  const [serveVersion, setServeVersion] = useState<string>();

  const serveOptions = useMemo<ServeOption[]>(() => {
    const opts: ServeOption[] = [
      { key: 'local', label: 'local · 4096', baseUrl: LOCAL_SERVE_URL, kind: 'local' },
    ];
    for (const svc of services) {
      if (svc.kind !== 'opencode_serve' && svc.kind !== 'opencode_web') continue;
      if (!svc.access_url || !svc.host_reachable) continue;
      opts.push({
        key: `svc-${svc.id}`,
        label: `${svc.container_name}:${svc.host_port}`,
        baseUrl: svc.access_url.replace(/\/$/, ''),
        kind: 'container',
        service: svc,
      });
    }
    return opts;
  }, [services]);

  const currentServe = serveOptions.find((o) => o.key === serveKey) ?? serveOptions[0];

  const clientRef = useRef<OpencodeClient | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const unsubRef = useRef<(() => void) | null>(null);
  const assistantIdsRef = useRef<Set<string>>(new Set());
  const textSnapRef = useRef<Record<string, string>>({});
  const reasoningSnapRef = useRef<Record<string, string>>({});
  const toolsSnapRef = useRef<Record<string, ToolCallView>>({});
  const busySeenRef = useRef(false);
  const sendGenRef = useRef(0);

  const finishSending = useCallback((gen?: number) => {
    if (gen != null && gen !== sendGenRef.current) return;
    setSending(false);
    setChatMessages((prev) => prev.map((m) => (m.streaming ? { ...m, streaming: false } : m)));
    busySeenRef.current = false;
    textSnapRef.current = {};
    reasoningSnapRef.current = {};
    toolsSnapRef.current = {};
  }, []);

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState('');
  const [connecting, setConnecting] = useState(false);
  const [sending, setSending] = useState(false);
  const [commands, setCommands] = useState<OpencodeCommand[]>([]);
  const [agents, setAgents] = useState<OpencodeAgent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | undefined>();
  const [mentionMode, setMentionMode] = useState<MentionsMode>('none');
  const chatEndRef = useRef<HTMLDivElement>(null);

  const executorOptions = useMemo(
    () =>
      sources
        .filter((s) => s.source_type === 'doris' || s.source_type === 'mysql')
        .map((s) => ({
          value: s.id,
          label: `${s.name} (${s.source_type}${s.database ? `/${s.database}` : ''})`,
        })),
    [sources],
  );

  const loadSources = useCallback(async () => {
    try {
      const rows = await listDataSources();
      setSources(rows);
      setExecutorId((prev) => {
        if (prev && rows.some((r) => r.id === prev)) return prev;
        const preferred =
          rows.find((r) => r.is_default && (r.source_type === 'doris' || r.source_type === 'mysql')) ||
          rows.find((r) => r.source_type === 'doris') ||
          rows.find((r) => r.source_type === 'mysql');
        return preferred?.id;
      });
    } catch {
      /* ignore */
    }
  }, []);

  const fetchServices = useCallback(async (discover = true) => {
    setServicesLoading(true);
    try {
      const rows = discover
        ? (await discoverContainerServices()).services
        : await listContainerServices(undefined, true);
      setServices(rows.filter((r) => r.kind === 'opencode_serve' || r.kind === 'opencode_web'));
    } catch {
      try {
        const rows = await listContainerServices();
        setServices(rows.filter((r) => r.kind === 'opencode_serve' || r.kind === 'opencode_web'));
      } catch {
        /* ignore */
      }
    } finally {
      setServicesLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchServices(true);
    void loadSources();
  }, [fetchServices, loadSources]);

  const teardownClient = useCallback(() => {
    unsubRef.current?.();
    unsubRef.current = null;
    clientRef.current = null;
    sessionIdRef.current = null;
    assistantIdsRef.current = new Set();
    textSnapRef.current = {};
    reasoningSnapRef.current = {};
    toolsSnapRef.current = {};
    busySeenRef.current = false;
    setCommands([]);
    setAgents([]);
    setSelectedAgent(undefined);
  }, []);

  const applyPartUpdates = useCallback((updates: AssistantPartUpdate[]) => {
    if (!updates.length) return;
    for (const u of updates) {
      if (u.kind === 'text') textSnapRef.current[u.partId] = u.text;
      if (u.kind === 'reasoning') reasoningSnapRef.current[u.partId] = u.text;
      if (u.kind === 'tool') {
        toolsSnapRef.current[u.partId] = {
          partId: u.partId,
          tool: u.tool,
          status: u.status,
          title: u.title,
          input: u.input,
          output: u.output,
          error: u.error,
        };
      }
    }
    const full = Object.values(textSnapRef.current).join('\n');
    const reasoning = Object.values(reasoningSnapRef.current).join('\n');
    const tools = Object.values(toolsSnapRef.current);
    setChatMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last?.role === 'assistant' && last.streaming) {
        return [
          ...prev.slice(0, -1),
          { ...last, content: full, reasoning: reasoning || last.reasoning, tools },
        ];
      }
      return [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: 'assistant',
          content: full,
          reasoning: reasoning || undefined,
          tools,
          streaming: true,
        },
      ];
    });
  }, []);

  const connectServe = useCallback(
    async (baseUrl: string) => {
      setConnecting(true);
      teardownClient();
      setChatMessages([]);
      try {
        const health = await healthCheck(baseUrl);
        if (!health.ok) {
          setServeReady(false);
          setServeVersion(undefined);
          message.warning(`无法连接 ${baseUrl}：${health.error || '未就绪'}`);
          return;
        }
        setServeReady(true);
        setServeVersion(health.version);
        const client = createServeClient(baseUrl);
        clientRef.current = client;
        const sid = await createChatSession(client, '智能数开');
        sessionIdRef.current = sid;

        const [cmds, ags] = await Promise.all([listCommands(client), listAgents(client)]);
        setCommands(cmds);
        setAgents(ags);
        setSelectedAgent(ags.find((a) => a.mode === 'primary' || a.mode === 'all')?.name);

        unsubRef.current = await subscribeSessionEvents(client, sid, (evt: OpencodeEvent) => {
          if (isSessionBusy(evt)) busySeenRef.current = true;
          const updates = extractAssistantParts(evt, assistantIdsRef.current);
          if (updates.length) {
            busySeenRef.current = true;
            applyPartUpdates(updates);
          }
          if (isSessionError(evt) || isSessionIdle(evt)) finishSending(sendGenRef.current);
        });

        setChatMessages([
          {
            id: 'sys-1',
            role: 'system',
            content: `Connected · OpenCode ${health.version || ''} · ${sid.slice(0, 10)}…\n/ commands · @ agents · SQL context linked`,
          },
        ]);
      } catch (err) {
        setServeReady(false);
        message.error(err instanceof Error ? err.message : '连接失败');
      } finally {
        setConnecting(false);
      }
    },
    [applyPartUpdates, finishSending, message, teardownClient],
  );

  useEffect(() => {
    const url = currentServe?.baseUrl;
    if (!url) return;
    void connectServe(url);
    return () => teardownClient();
  }, [currentServe?.baseUrl, connectServe, teardownClient]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const buildLinkedPrompt = (userText: string) => {
    const fileLabel = activeFile?.path || '(未选择文件)';
    const sqlBody = sql.trim();
    if (!sqlBody) return userText;
    return [
      `【智能数开上下文】`,
      `当前 ETL 文件: ${fileLabel}`,
      '',
      '```sql',
      sqlBody,
      '```',
      '',
      `【用户请求】`,
      userText,
    ].join('\n');
  };

  const startAssistantTurn = (userContent: string) => {
    const gen = ++sendGenRef.current;
    setSending(true);
    busySeenRef.current = true;
    textSnapRef.current = {};
    reasoningSnapRef.current = {};
    toolsSnapRef.current = {};
    setChatMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: 'user', content: userContent },
      { id: `a-${Date.now()}`, role: 'assistant', content: '', streaming: true },
    ]);
    return gen;
  };

  const sendChat = async (text?: string) => {
    const content = (text ?? draft).trim();
    if (!content) return;
    const client = clientRef.current;
    const sid = sessionIdRef.current;
    if (!client || !sid || !serveReady) {
      message.warning('请先选择可用的 opencode serve');
      return;
    }

    if (content.startsWith('/')) {
      const match = content.match(/^\/([^\s]+)(?:\s+([\s\S]*))?$/);
      const cmdName = match?.[1] || '';
      const args = (match?.[2] || '').trim();
      if (!cmdName) return;
      setDraft('');
      setMentionMode('none');
      const gen = startAssistantTurn(content);
      try {
        await runCommand(client, sid, cmdName, args, { agent: selectedAgent });
      } catch (err) {
        finishSending(gen);
        setChatMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === 'assistant') {
            next[next.length - 1] = {
              ...last,
              streaming: false,
              content: `❌ ${err instanceof Error ? err.message : '命令失败'}`,
            };
          }
          return next;
        });
      }
      return;
    }

    let agentMentions: string[] = [];
    let promptText = content;
    const atMatch = content.match(/^@([^\s]+)\s*([\s\S]*)$/);
    if (atMatch) {
      agentMentions = [atMatch[1]];
      promptText = atMatch[2]?.trim() || '请协助处理当前 SQL';
    }

    setDraft('');
    setMentionMode('none');
    const gen = startAssistantTurn(content);
    try {
      await promptAsync(client, sid, buildLinkedPrompt(promptText), {
        agent: selectedAgent,
        agentMentions,
      });
      window.setTimeout(() => finishSending(gen), 180_000);
    } catch (err) {
      finishSending(gen);
      setChatMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === 'assistant') {
          next[next.length - 1] = {
            ...last,
            streaming: false,
            content: `❌ ${err instanceof Error ? err.message : '发送失败'}`,
          };
        }
        return next;
      });
    }
  };

  const stopChat = async () => {
    const client = clientRef.current;
    const sid = sessionIdRef.current;
    if (client && sid) {
      try {
        await abortSession(client, sid);
      } catch {
        /* ignore */
      }
    }
    finishSending();
  };

  const runSql = async () => {
    if (!executorId) {
      message.warning('请先选择 Doris/MySQL 执行器');
      return;
    }
    const body = sql.trim();
    if (!body) {
      message.warning('编辑器中没有可执行的 SQL');
      return;
    }
    setResultCollapsed(false);
    resultPanelRef.current?.expand();
    setPanelTab('result');
    setExecuting(true);
    setExecLogs([{ level: 'info', message: '准备执行…' }]);
    setExecResult(null);
    try {
      const src = sources.find((s) => s.id === executorId);
      const result = await executeSql(executorId, {
        sql: body,
        database: src?.database || undefined,
        max_rows: 200,
      });
      setExecLogs(
        result.logs?.length
          ? result.logs
          : [{ level: result.ok ? 'success' : 'error', message: result.message || (result.ok ? '完成' : '失败') }],
      );
      setExecResult(result);
      if (!result.ok) {
        setPanelTab('output');
        message.error(result.message || 'SQL 执行失败');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '执行失败';
      setExecLogs((prev) => [...prev, { level: 'error', message: msg }]);
      setPanelTab('output');
      message.error(msg);
    } finally {
      setExecuting(false);
    }
  };

  const applySqlFromAssistant = (content: string) => {
    const block = extractSqlBlock(content);
    if (!block) {
      message.info('回复中未检测到 ```sql 代码块');
      return;
    }
    if (!activeFileId) {
      message.warning('请先选择左侧 SQL 文件');
      return;
    }
    setFileContents((prev) => ({ ...prev, [activeFileId]: block }));
    message.success(`已写入 ${activeFile?.name}`);
  };

  const onDraftChange = (value: string) => {
    setDraft(value);
    if (value === '/' || /^\/[^\s]*$/.test(value)) setMentionMode('slash');
    else if (value === '@' || /^@[^\s]*$/.test(value)) setMentionMode('at');
    else if (value.endsWith(' /') || /\s\/[^\s]*$/.test(value)) setMentionMode('slash');
    else if (value.endsWith(' @') || /\s@[^\s]*$/.test(value)) setMentionMode('at');
    else setMentionMode('none');
  };

  const slashQuery = useMemo(() => {
    const m = draft.match(/(?:^|\s)\/([^\s]*)$/);
    return m ? m[1].toLowerCase() : '';
  }, [draft]);

  const atQuery = useMemo(() => {
    const m = draft.match(/(?:^|\s)@([^\s]*)$/);
    return m ? m[1].toLowerCase() : '';
  }, [draft]);

  const filteredCommands = useMemo(
    () => commands.filter((c) => !slashQuery || c.name.toLowerCase().includes(slashQuery)),
    [commands, slashQuery],
  );

  const filteredAgents = useMemo(
    () => agents.filter((a) => !atQuery || a.name.toLowerCase().includes(atQuery)),
    [agents, atQuery],
  );

  const pickSlash = (cmd: OpencodeCommand) => {
    setDraft(`/${cmd.name} `);
    setMentionMode('none');
  };

  const pickAt = (agent: OpencodeAgent) => {
    setDraft(`@${agent.name} `);
    setSelectedAgent(agent.name);
    setMentionMode('none');
  };

  const togglePanel = (
    ref: React.RefObject<ImperativePanelHandle | null>,
    collapsed: boolean,
    setCollapsed: (v: boolean) => void,
  ) => {
    if (collapsed) {
      ref.current?.expand();
      setCollapsed(false);
    } else {
      ref.current?.collapse();
      setCollapsed(true);
    }
  };

  const renderFileTree = (nodes: EtlFileNode[], depth = 0): React.ReactNode =>
    nodes.map((n) => {
      if (n.kind === 'folder') {
        return (
          <div key={n.id}>
            <div className="sd-tree-folder" style={{ ['--d' as string]: depth }}>
              <FolderOpenOutlined />
              {n.name}
            </div>
            {n.children ? renderFileTree(n.children, depth + 1) : null}
          </div>
        );
      }
      return (
        <button
          key={n.id}
          type="button"
          className={`sd-tree-file${n.id === activeFileId ? ' active' : ''}`}
          style={{ ['--d' as string]: depth }}
          onClick={() => setActiveFileId(n.id)}
        >
          <FileTextOutlined />
          {n.name}
        </button>
      );
    });

  const resultColumns = (execResult?.columns || []).map((c) => ({
    title: c,
    dataIndex: c,
    key: c,
    ellipsis: true,
    width: 120,
  }));

  const resultData = (execResult?.rows || []).map((row, i) => {
    const obj: Record<string, unknown> = { key: i };
    (execResult?.columns || []).forEach((col, idx) => {
      obj[col] = row[idx];
    });
    return obj;
  });

  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#0078d4',
          colorBgBase: '#ffffff',
          colorBgContainer: '#ffffff',
          colorBorder: '#e5e5e5',
          colorText: '#3b3b3b',
          fontSize: 12,
          borderRadius: 3,
          controlHeight: 22,
        },
      }}
    >
      <div className="sd-root">
        {/* Title bar */}
        <div className="sd-titlebar">
          <div className="sd-titlebar-left">
            <LayoutOutlined style={{ fontSize: 12, color: '#858585' }} />
            <span className="sd-product">智能数开</span>
            {activeFile ? <span className="sd-path">{activeFile.path}</span> : null}
            <button
              type="button"
              className={`sd-icon-btn${filesCollapsed ? '' : ' is-active'}`}
              title="Explorer"
              onClick={() => togglePanel(filesPanelRef, filesCollapsed, setFilesCollapsed)}
            >
              ☰
            </button>
            <button
              type="button"
              className={`sd-icon-btn${resultCollapsed ? '' : ' is-active'}`}
              title="Panel"
              onClick={() => togglePanel(resultPanelRef, resultCollapsed, setResultCollapsed)}
            >
              ▭
            </button>
            <button
              type="button"
              className={`sd-icon-btn${agentCollapsed ? '' : ' is-active'}`}
              title="Chat"
              onClick={() => togglePanel(agentPanelRef, agentCollapsed, setAgentCollapsed)}
            >
              ✦
            </button>
          </div>
          <div className="sd-titlebar-right">
            <Select
              className="sd-tb-select"
              style={{ width: 160 }}
              size="small"
              placeholder="Executor"
              value={executorId}
              onChange={setExecutorId}
              options={executorOptions}
              allowClear
            />
            <Button
              className="sd-tb-run"
              size="small"
              icon={<PlayCircleOutlined />}
              loading={executing}
              disabled={!executorId}
              onClick={() => void runSql()}
            >
              Run
            </Button>
            <Select
              className="sd-tb-select"
              style={{ width: 140 }}
              size="small"
              loading={servicesLoading || connecting}
              value={serveKey}
              onChange={setServeKey}
              options={serveOptions.map((o) => ({
                value: o.key,
                label: o.label,
                disabled: o.kind === 'container' && !o.service?.host_reachable,
              }))}
            />
            <button
              type="button"
              className="sd-icon-btn"
              title="Refresh services"
              onClick={() => void fetchServices(true)}
            >
              <ReloadOutlined />
            </button>
            <span className={`sd-dot ${serveReady ? 'on' : 'off'}`} title={serveReady ? 'connected' : 'disconnected'} />
          </div>
        </div>

        {/* Workbench: LEFT | CENTER | RIGHT */}
        <div className="sd-workbench">
          <PanelGroup direction="horizontal" autoSaveId="sd-cursor-h">
            {/* LEFT: explorer */}
            <Panel
              ref={filesPanelRef}
              defaultSize={16}
              minSize={10}
              collapsible
              collapsedSize={0}
              onCollapse={() => setFilesCollapsed(true)}
              onExpand={() => setFilesCollapsed(false)}
            >
              <div className="sd-pane sd-sidebar">
                <div className="sd-section-label">Explorer</div>
                <div className="sd-tree">{renderFileTree(ETL_FILE_TREE)}</div>
              </div>
            </Panel>

            <PanelResizeHandle className="sd-resize-v" />

            {/* CENTER: editor + panel */}
            <Panel defaultSize={54} minSize={30}>
              <PanelGroup direction="vertical" autoSaveId="sd-cursor-v">
                <Panel defaultSize={62} minSize={25}>
                  <div className="sd-pane">
                    <div className="sd-tabs">
                      {activeFile ? (
                        <div className="sd-tab active">
                          <FileTextOutlined />
                          {activeFile.name}
                        </div>
                      ) : (
                        <div className="sd-tab active">SQL</div>
                      )}
                      <div className="sd-tab-actions">
                        <button
                          type="button"
                          className="sd-icon-btn"
                          title="Explain"
                          onClick={() => void sendChat('请解释并评审当前 SQL，指出风险与优化点。')}
                        >
                          ?
                        </button>
                        <button
                          type="button"
                          className="sd-icon-btn"
                          title="Optimize"
                          onClick={() => void sendChat('请优化当前 SQL，输出完整可执行的 ```sql 代码块。')}
                        >
                          ✎
                        </button>
                        <button
                          type="button"
                          className="sd-icon-btn"
                          title="Run SQL"
                          disabled={!executorId || executing}
                          onClick={() => void runSql()}
                        >
                          <PlayCircleOutlined />
                        </button>
                      </div>
                    </div>
                    <div className="sd-editor-body">
                      {activeFile ? (
                        <Editor
                          height="100%"
                          language="sql"
                          theme="vs"
                          value={sql}
                          onChange={(v) => {
                            if (!activeFileId) return;
                            setFileContents((prev) => ({ ...prev, [activeFileId]: v ?? '' }));
                          }}
                          options={{
                            fontSize: 12,
                            fontFamily: "Menlo, Monaco, 'Cascadia Code', Consolas, monospace",
                            minimap: { enabled: false },
                            scrollBeyondLastLine: false,
                            wordWrap: 'on',
                            automaticLayout: true,
                            tabSize: 2,
                            padding: { top: 8 },
                            lineNumbers: 'on',
                            renderLineHighlight: 'line',
                            scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
                          }}
                        />
                      ) : (
                        <div className="sd-empty">Select a SQL file</div>
                      )}
                    </div>
                  </div>
                </Panel>

                <PanelResizeHandle className="sd-resize-h" />

                {/* Bottom panel — same width as editor */}
                <Panel
                  ref={resultPanelRef}
                  defaultSize={38}
                  minSize={15}
                  collapsible
                  collapsedSize={0}
                  onCollapse={() => setResultCollapsed(true)}
                  onExpand={() => setResultCollapsed(false)}
                >
                  <div className="sd-pane">
                    <div className="sd-panel-tabs">
                      <button
                        type="button"
                        className={`sd-panel-tab${panelTab === 'result' ? ' active' : ''}`}
                        onClick={() => setPanelTab('result')}
                      >
                        Result
                      </button>
                      <button
                        type="button"
                        className={`sd-panel-tab${panelTab === 'output' ? ' active' : ''}`}
                        onClick={() => setPanelTab('output')}
                      >
                        Output
                      </button>
                      <div className="sd-panel-meta">
                        {executing ? <Spin size="small" /> : null}
                        {execResult ? (
                          <span className={`sd-badge ${execResult.ok ? 'ok' : 'err'}`}>
                            {execResult.ok ? 'OK' : 'ERR'}
                            {execResult.latency_ms != null ? ` ${execResult.latency_ms}ms` : ''}
                            {execResult.truncated ? ' truncated' : ''}
                            {execResult.affected_rows != null ? ` · ${execResult.affected_rows} rows` : ''}
                          </span>
                        ) : null}
                        <button type="button" className="sd-icon-btn" title="Run" onClick={() => void runSql()}>
                          <PlayCircleOutlined />
                        </button>
                        <button
                          type="button"
                          className="sd-icon-btn"
                          title="Close panel"
                          onClick={() => togglePanel(resultPanelRef, false, setResultCollapsed)}
                        >
                          <CloseOutlined />
                        </button>
                      </div>
                    </div>

                    {panelTab === 'output' ? (
                      <div className="sd-panel-body">
                        <div className="sd-output" style={{ width: '100%' }}>
                          {execLogs.length === 0 && !executing ? (
                            <div className="sd-empty" style={{ padding: 16 }}>
                              No output yet — Run SQL to see process logs
                            </div>
                          ) : (
                            execLogs.map((log, i) => (
                              <div key={`${i}-${log.message}`} className={`sd-output-line ${log.level}`}>
                                [{log.level}] {log.message}
                              </div>
                            ))
                          )}
                          {execResult?.sql ? <pre className="sd-output-sql">{execResult.sql}</pre> : null}
                        </div>
                      </div>
                    ) : (
                      <div className="sd-panel-body">
                        <div className="sd-output">
                          <div style={{ color: '#858585', fontSize: 10, marginBottom: 4, letterSpacing: '0.06em' }}>
                            PROCESS
                          </div>
                          {execLogs.length === 0 ? (
                            <span style={{ color: '#858585' }}>—</span>
                          ) : (
                            execLogs.map((log, i) => (
                              <div key={`${i}-${log.message}`} className={`sd-output-line ${log.level}`}>
                                {log.message}
                              </div>
                            ))
                          )}
                        </div>
                        <div className="sd-result-grid">
                          {execResult && execResult.columns.length > 0 ? (
                            <Table
                              size="small"
                              pagination={{ pageSize: 50, size: 'small', showSizeChanger: true }}
                              columns={resultColumns}
                              dataSource={resultData}
                              scroll={{ x: true }}
                            />
                          ) : (
                            <Empty
                              image={Empty.PRESENTED_IMAGE_SIMPLE}
                              description={
                                <span style={{ color: '#858585', fontSize: 12 }}>
                                  {execResult?.ok
                                    ? 'Statement OK · no result set'
                                    : execResult
                                      ? execResult.message || 'Failed'
                                      : 'Results appear here'}
                                </span>
                              }
                              style={{ marginTop: 28 }}
                            />
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </Panel>
              </PanelGroup>
            </Panel>

            <PanelResizeHandle className="sd-resize-v" />

            {/* RIGHT: agent chat */}
            <Panel
              ref={agentPanelRef}
              defaultSize={30}
              minSize={18}
              collapsible
              collapsedSize={0}
              onCollapse={() => setAgentCollapsed(true)}
              onExpand={() => setAgentCollapsed(false)}
            >
              <div className="sd-pane sd-chat">
                <div className="sd-chat-header">
                  <span className="sd-chat-header-title">Agent</span>
                  <Select
                    className="sd-tb-select"
                    style={{ width: 110 }}
                    size="small"
                    placeholder="@agent"
                    value={selectedAgent}
                    onChange={setSelectedAgent}
                    allowClear
                    options={agents.map((a) => ({ value: a.name, label: a.name }))}
                  />
                  <span style={{ marginLeft: 'auto', fontSize: 10, color: '#858585' }}>/ · @</span>
                </div>

                <div className="sd-chat-messages">
                  {connecting ? (
                    <div className="sd-empty">
                      <Spin size="small" /> Connecting…
                    </div>
                  ) : chatMessages.length === 0 ? (
                    <div className="sd-empty">Start a chat · SQL context is linked</div>
                  ) : (
                    chatMessages.map((m) => (
                      <div key={m.id} className={`sd-msg ${m.role}`}>
                        <div className="sd-msg-role">
                          {m.role === 'user' ? 'You' : m.role === 'assistant' ? 'Agent' : 'System'}
                          {m.streaming ? ' …' : ''}
                        </div>
                        {m.reasoning ? (
                          <details className="sd-think">
                            <summary>
                              <CaretRightOutlined /> Thinking
                            </summary>
                            <pre>{m.reasoning}</pre>
                          </details>
                        ) : null}
                        {m.tools?.map((t) => (
                          <details key={t.partId} className="sd-tool">
                            <summary>
                              {t.tool} · {t.status}
                              {t.title ? ` · ${t.title}` : ''}
                            </summary>
                            {t.input != null ? (
                              <pre>{typeof t.input === 'string' ? t.input : JSON.stringify(t.input, null, 2)}</pre>
                            ) : null}
                            {t.output ? <pre>{t.output}</pre> : null}
                            {t.error ? <pre style={{ color: '#c72e0f' }}>{t.error}</pre> : null}
                          </details>
                        ))}
                        <p className="sd-msg-body">{m.content || (m.streaming ? 'Thinking…' : '')}</p>
                        {m.role === 'assistant' && !m.streaming && extractSqlBlock(m.content) ? (
                          <button type="button" className="sd-msg-link" onClick={() => applySqlFromAssistant(m.content)}>
                            Apply SQL to editor
                          </button>
                        ) : null}
                      </div>
                    ))
                  )}
                  <div ref={chatEndRef} />
                </div>

                <div className="sd-chat-input">
                  {mentionMode === 'slash' && filteredCommands.length > 0 ? (
                    <div className="sd-mention">
                      {filteredCommands.slice(0, 12).map((c) => (
                        <button key={c.name} type="button" onClick={() => pickSlash(c)}>
                          /{c.name}
                          {c.description ? <span className="desc">{c.description}</span> : null}
                        </button>
                      ))}
                    </div>
                  ) : null}
                  {mentionMode === 'at' && filteredAgents.length > 0 ? (
                    <div className="sd-mention">
                      {filteredAgents.slice(0, 12).map((a) => (
                        <button key={a.name} type="button" onClick={() => pickAt(a)}>
                          @{a.name}
                          {a.description ? <span className="desc">{a.description}</span> : null}
                        </button>
                      ))}
                    </div>
                  ) : null}
                  <TextArea
                    value={draft}
                    onChange={(e) => onDraftChange(e.target.value)}
                    placeholder="Ask Agent · / command · @ agent"
                    autoSize={{ minRows: 2, maxRows: 5 }}
                    disabled={!serveReady || sending}
                    onPressEnter={(e) => {
                      if (!e.shiftKey) {
                        e.preventDefault();
                        void sendChat();
                      }
                    }}
                  />
                  <div className="sd-chat-actions">
                    <span className="sd-hint">Enter send · Shift+Enter newline</span>
                    <div style={{ display: 'flex', gap: 4 }}>
                      {sending ? (
                        <Button size="small" danger icon={<StopOutlined />} onClick={() => void stopChat()}>
                          Stop
                        </Button>
                      ) : null}
                      <Button
                        size="small"
                        type="primary"
                        icon={<SendOutlined />}
                        loading={sending}
                        disabled={!serveReady}
                        onClick={() => void sendChat()}
                      >
                        Send
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </Panel>
          </PanelGroup>
        </div>

        {/* Status bar */}
        <div className="sd-statusbar">
          <span>
            {serveReady ? `OpenCode ${serveVersion || ''}`.trim() : 'OpenCode offline'}
            {selectedAgent ? ` · ${selectedAgent}` : ''}
          </span>
          <span>
            {activeFile?.name || '—'} · SQL
            {executorId
              ? ` · ${sources.find((s) => s.id === executorId)?.name || 'executor'}`
              : ' · no executor'}
          </span>
        </div>
      </div>
    </ConfigProvider>
  );
}

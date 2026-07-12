import { create } from 'zustand';
import { agentPlatformService } from '../services/agentPlatform.service';
import type {
  AgentPlatformEvent,
  AgentRun,
  AgentSession,
  AgentSummary,
  ComputeNode,
  RunTimelineState,
} from '../pages/agent-platform/types';
import {
  appendUserMessage,
  initialTimelineState,
  reduceTimeline,
} from '../pages/agent-platform/timelineReducer';
import type { AgentChatMessage } from '../components/common/AgentChatPanel';

interface AgentPlatformState {
  agents: AgentSummary[];
  sessions: AgentSession[];
  nodes: ComputeNode[];
  runs: AgentRun[];
  selectedAgentId: number | null;
  selectedSessionId: number | null;
  activeRunId: number | null;
  timeline: RunTimelineState;
  loading: boolean;
  error: string | null;
  loadAgents: () => Promise<void>;
  loadSessions: (agentId?: number | null) => Promise<void>;
  loadNodes: () => Promise<void>;
  loadRuns: () => Promise<void>;
  selectAgent: (id: number | null) => void;
  selectSession: (id: number | null) => Promise<void>;
  createSession: (agentId: number, title?: string) => Promise<AgentSession>;
  publishAgent: (agentId: number) => Promise<void>;
  sendMessage: (content: string) => Promise<number>;
  ingestEvent: (event: AgentPlatformEvent) => void;
  clearTimeline: () => void;
  reset: () => void;
}

const errorMessage = (error: unknown): string =>
  error instanceof Error ? error.message : 'Agent Platform 请求失败';

const historyToMessages = (
  rows: Array<{ id: number; role: string; content: string; created_at: string | null }>,
): AgentChatMessage[] =>
  rows.map((row) => ({
    id: String(row.id),
    role: (row.role === 'user' || row.role === 'assistant' || row.role === 'system' || row.role === 'tool'
      ? row.role
      : 'assistant') as AgentChatMessage['role'],
    parts: [{ kind: 'text', id: `${row.id}-text`, text: row.content, streaming: false }],
    createdAt: row.created_at ? Date.parse(row.created_at) || Date.now() : Date.now(),
    streaming: false,
  }));

export const useAgentPlatformStore = create<AgentPlatformState>((set, get) => ({
  agents: [],
  sessions: [],
  nodes: [],
  runs: [],
  selectedAgentId: null,
  selectedSessionId: null,
  activeRunId: null,
  timeline: initialTimelineState(),
  loading: false,
  error: null,

  async loadAgents() {
    set({ loading: true, error: null });
    try {
      const agents = await agentPlatformService.listAgents();
      set((state) => ({
        agents,
        loading: false,
        selectedAgentId: state.selectedAgentId ?? agents[0]?.id ?? null,
      }));
    } catch (error) {
      set({ error: errorMessage(error), loading: false });
    }
  },
  async loadSessions(agentId) {
    try {
      const all = await agentPlatformService.listSessions();
      const target = agentId ?? get().selectedAgentId;
      const sessions = target == null ? all : all.filter((item) => item.agent_id === target);
      set({ sessions });
    } catch (error) {
      set({ error: errorMessage(error) });
    }
  },
  async loadNodes() {
    set({ loading: true, error: null });
    try {
      set({ nodes: await agentPlatformService.listNodes(), loading: false });
    } catch (error) {
      set({ error: errorMessage(error), loading: false });
    }
  },
  async loadRuns() {
    set({ loading: true, error: null });
    try {
      set({ runs: await agentPlatformService.listRuns(), loading: false });
    } catch (error) {
      set({ error: errorMessage(error), loading: false });
    }
  },
  selectAgent(id) {
    set({
      selectedAgentId: id,
      selectedSessionId: null,
      activeRunId: null,
      timeline: initialTimelineState(),
      sessions: [],
    });
    if (id != null) {
      void get().loadSessions(id);
    }
  },
  async selectSession(id) {
    if (id == null) {
      set({ selectedSessionId: null, activeRunId: null, timeline: initialTimelineState() });
      return;
    }
    set({ selectedSessionId: id, activeRunId: null, loading: true, error: null });
    try {
      const detail = await agentPlatformService.getSession(id);
      set({
        loading: false,
        timeline: {
          ...initialTimelineState(),
          messages: historyToMessages(detail.messages),
        },
      });
    } catch (error) {
      set({ error: errorMessage(error), loading: false });
    }
  },
  async createSession(agentId, title) {
    const session = await agentPlatformService.createSession({ agent_id: agentId, title });
    set((state) => ({
      sessions: [session, ...state.sessions.filter((item) => item.id !== session.id)],
      selectedSessionId: session.id,
      timeline: initialTimelineState(),
      activeRunId: null,
    }));
    return session;
  },
  async publishAgent(agentId) {
    const versions = await agentPlatformService.listAgentVersions(agentId);
    if (!versions.length) throw new Error('该 Agent 尚无版本，请先在 Studio 保存草稿');
    const latest = versions[0];
    await agentPlatformService.publishAgentVersion(agentId, latest.id);
    await get().loadAgents();
  },
  async sendMessage(content) {
    let sessionId = get().selectedSessionId;
    const agentId = get().selectedAgentId;
    if (!agentId) throw new Error('请先选择 Agent');
    if (!sessionId) {
      sessionId = (await get().createSession(agentId, content.slice(0, 40))).id;
    }
    const localMessageId = `local-${Date.now()}`;
    set((state) => ({
      timeline: appendUserMessage(state.timeline, localMessageId, content),
      error: null,
    }));
    try {
      // 立即返回 run_id；OpenCode thinking/tools/文本经 SSE 实时推送
      const result = await agentPlatformService.sendMessage(sessionId, content);
      set({ activeRunId: result.run_id });
      return result.run_id;
    } catch (error) {
      set({ error: errorMessage(error) });
      throw error;
    }
  },
  ingestEvent(event) {
    set((state) => ({ timeline: reduceTimeline(state.timeline, event) }));
  },
  clearTimeline() {
    set({ activeRunId: null, timeline: initialTimelineState() });
  },
  reset() {
    set({
      agents: [],
      sessions: [],
      nodes: [],
      runs: [],
      selectedAgentId: null,
      selectedSessionId: null,
      activeRunId: null,
      timeline: initialTimelineState(),
      loading: false,
      error: null,
    });
  },
}));

export default useAgentPlatformStore;

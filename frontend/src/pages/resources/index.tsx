/**
 * ResourcesPage — 资源管理页 (T49 Wave 10)
 *
 * 5 层导航：计算节点 / 智能体容器 / 智能体 / Skill / MCP
 * 顶部统计大盘：7 个指标卡（5 层数量 + 运行中任务 + 发现错误）
 * 自动发现入口：调用 T46/T47/T48 的发现端点，一键同步本机 opencode 配置
 *
 * 每一层是一个自包含的可折叠面板，自己拉自己的 API，通过 `onCountChange`
 * 回调把最新条目数上报给统计大盘。折叠状态记忆到 localStorage。
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import { App, Button, Space, Tooltip, Typography } from 'antd';
import {
  ApiOutlined,
  BugOutlined,
  CaretDownOutlined,
  CaretRightOutlined,
  CloudServerOutlined,
  DownloadOutlined,
  LinkOutlined,
  MonitorOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { GlassPanel, PageHeader, StatCard } from '../../components/common';
import { resourcesAPI } from '../../services';
import { agentLooperService } from '../../services/agentLooper.service';
import type { AgentRun } from '../../types';
import ComputeNodePanel from './ComputeNodePanel';
import AgentContainerPanel from './AgentContainerPanel';
import AgentPanel from './AgentPanel';
import SkillPanel from './SkillPanel';
import MCPPanel from './MCPPanel';

const { Text } = Typography;

// -- 折叠状态持久化 ------------------------------------------------

const STORAGE_KEY = 'resources.panel.collapsed.v1';

type PanelKey = 'nodes' | 'containers' | 'agents' | 'skills' | 'mcps';

interface CollapseState {
  nodes: boolean;
  containers: boolean;
  agents: boolean;
  skills: boolean;
  mcps: boolean;
}

const DEFAULT_COLLAPSE: CollapseState = {
  nodes: false,
  containers: false,
  agents: false,
  skills: false,
  mcps: false,
};

function loadCollapse(): CollapseState {
  if (typeof window === 'undefined') return DEFAULT_COLLAPSE;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_COLLAPSE;
    const parsed = JSON.parse(raw) as Partial<CollapseState>;
    return { ...DEFAULT_COLLAPSE, ...parsed };
  } catch {
    return DEFAULT_COLLAPSE;
  }
}

function saveCollapse(state: CollapseState): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* localStorage disabled — 忽略 */
  }
}

// -- 面板容器（可折叠） --------------------------------------------

interface SectionProps {
  icon: React.ReactNode;
  title: string;
  subtitle?: string;
  count: number;
  collapsed: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

const sectionHeaderStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  cursor: 'pointer',
  userSelect: 'none',
  marginBottom: 8,
};

function CollapsibleSection({
  icon,
  title,
  subtitle,
  count,
  collapsed,
  onToggle,
  children,
}: SectionProps) {
  return (
    <GlassPanel padded style={{ marginBottom: 16 }}>
      <div
        style={sectionHeaderStyle}
        onClick={onToggle}
        role="button"
        aria-expanded={!collapsed}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onToggle();
          }
        }}
      >
        <Space size={12}>
          <span style={{ color: '#8895b4', fontSize: 12 }}>
            {collapsed ? <CaretRightOutlined /> : <CaretDownOutlined />}
          </span>
          <span style={{ fontSize: 18, color: '#60a5fa' }}>{icon}</span>
          <div>
            <div
              style={{
                fontSize: 15,
                fontWeight: 600,
                color: '#e8eef5',
                lineHeight: 1.3,
              }}
            >
              {title}
              <Text
                style={{
                  color: '#8895b4',
                  fontSize: 12,
                  marginLeft: 10,
                  fontWeight: 400,
                }}
              >
                {count}
              </Text>
            </div>
            {subtitle && (
              <Text style={{ color: '#8895b4', fontSize: 12 }}>{subtitle}</Text>
            )}
          </div>
        </Space>
      </div>
      {!collapsed && <div style={{ marginTop: 16 }}>{children}</div>}
    </GlassPanel>
  );
}

// -- 主页面 --------------------------------------------------------

interface Counts {
  nodes: number;
  containers: number;
  agents: number;
  skills: number;
  mcps: number;
  running: number;
  errors: number;
}

const INITIAL_COUNTS: Counts = {
  nodes: 0,
  containers: 0,
  agents: 0,
  skills: 0,
  mcps: 0,
  running: 0,
  errors: 0,
};

export default function ResourcesPage() {
  const { message } = App.useApp();
  const [counts, setCounts] = useState<Counts>(INITIAL_COUNTS);
  const [collapsed, setCollapsed] = useState<CollapseState>(loadCollapse);
  const [discovering, setDiscovering] = useState(false);

  // 更新单个 count（由子面板回调触发）
  const setCount = useCallback((key: keyof Counts, value: number) => {
    setCounts((prev) => (prev[key] === value ? prev : { ...prev, [key]: value }));
  }, []);

  // 运行中任务 & 错误数：单独从 runs 端点聚合
  const loadRunsStats = useCallback(async () => {
    try {
      const res = await resourcesAPI.listRuns({ skip: 0, limit: 200 });
      const runs: AgentRun[] = res.data?.data ?? [];
      const running = runs.filter(
        (r) => r.status === 'running' || r.status === 'initializing',
      ).length;
      const errors = runs.filter((r) => r.status === 'error').length;
      setCounts((prev) => ({ ...prev, running, errors }));
    } catch {
      /* 静默 — 大盘统计不阻塞页面渲染 */
    }
  }, []);

  useEffect(() => {
    loadRunsStats();
  }, [loadRunsStats]);

  // 折叠切换
  const toggleCollapse = useCallback((key: PanelKey) => {
    setCollapsed((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      saveCollapse(next);
      return next;
    });
  }, []);

  // 一键自动发现：并行触发本机注册 + agent 发现
  const handleAutoDiscover = async () => {
    setDiscovering(true);
    try {
      const [localRes, agentRes] = await Promise.allSettled([
        resourcesAPI.registerLocalInstance(),
        agentLooperService.discover(),
      ]);
      const parts: string[] = [];
      if (localRes.status === 'fulfilled') {
        const payload = localRes.value.data ?? {};
        parts.push(
          `本机 ${payload.hostname ?? ''} 已注册${
            payload.agent_count != null
              ? `（检测到 ${payload.agent_count} 个 Agent）`
              : ''
          }`,
        );
      } else {
        parts.push('本机注册失败');
      }
      if (agentRes.status === 'fulfilled') {
        parts.push(
          `已同步 ${agentRes.value.upserted_count ?? 0} 个本地 Agent`,
        );
      } else {
        parts.push('Agent 发现失败');
      }
      message.success(parts.join('；'));
      loadRunsStats();
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : '自动发现失败',
      );
    } finally {
      setDiscovering(false);
    }
  };

  const statCards = useMemo(
    () => [
      {
        key: 'nodes',
        icon: <CloudServerOutlined />,
        label: '计算节点',
        value: counts.nodes,
        accent: 'blue' as const,
      },
      {
        key: 'containers',
        icon: <ApiOutlined />,
        label: '智能体容器',
        value: counts.containers,
        accent: 'emerald' as const,
      },
      {
        key: 'agents',
        icon: <RobotOutlined />,
        label: '智能体',
        value: counts.agents,
        accent: 'purple' as const,
      },
      {
        key: 'skills',
        icon: <ToolOutlined />,
        label: 'Skill',
        value: counts.skills,
        accent: 'amber' as const,
      },
      {
        key: 'mcps',
        icon: <LinkOutlined />,
        label: 'MCP',
        value: counts.mcps,
        accent: 'cyan' as const,
      },
      {
        key: 'running',
        icon: <MonitorOutlined />,
        label: '正在运行的任务',
        value: counts.running,
        accent: 'blue' as const,
      },
      {
        key: 'errors',
        icon: <BugOutlined />,
        label: '发现错误',
        value: counts.errors,
        accent: 'rose' as const,
      },
    ],
    [counts],
  );

  return (
    <div style={{ maxWidth: 1400 }}>
      <PageHeader
        title="资源管理"
        subtitle="5 层资源体系：计算节点 → 智能体容器 → 智能体 → Skill → MCP"
        extra={
          <Space>
            <Tooltip title="扫描本机 opencode 配置，同步计算节点、智能体、Skill 和 MCP">
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                loading={discovering}
                onClick={handleAutoDiscover}
              >
                一键自动发现
              </Button>
            </Tooltip>
          </Space>
        }
      />

      {/* 统计大盘：7 个指标 */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 12,
          marginBottom: 24,
        }}
      >
        {statCards.map((s) => (
          <StatCard
            key={s.key}
            icon={s.icon}
            label={s.label}
            value={s.value}
            accent={s.accent}
          />
        ))}
      </div>

      {/* 5 层可折叠面板 */}
      <CollapsibleSection
        icon={<CloudServerOutlined />}
        title="计算节点"
        subtitle="物理机 / 虚拟机 / Docker Host / K8s Pod"
        count={counts.nodes}
        collapsed={collapsed.nodes}
        onToggle={() => toggleCollapse('nodes')}
      >
        <ComputeNodePanel onCountChange={(n) => setCount('nodes', n)} />
      </CollapsibleSection>

      <CollapsibleSection
        icon={<ApiOutlined />}
        title="智能体容器"
        subtitle="opencode / openclaw / harness 等 Agent runtime"
        count={counts.containers}
        collapsed={collapsed.containers}
        onToggle={() => toggleCollapse('containers')}
      >
        <AgentContainerPanel
          onCountChange={(n) => setCount('containers', n)}
        />
      </CollapsibleSection>

      <CollapsibleSection
        icon={<RobotOutlined />}
        title="智能体"
        subtitle="定制化 Agent，支持 ReAct / Plan-Execute / Reflect 策略"
        count={counts.agents}
        collapsed={collapsed.agents}
        onToggle={() => toggleCollapse('agents')}
      >
        <AgentPanel onCountChange={(n) => setCount('agents', n)} />
      </CollapsibleSection>

      <CollapsibleSection
        icon={<ToolOutlined />}
        title="Skill"
        subtitle="给智能体加载的能力模块（同步自 ~/.config/opencode/skills/）"
        count={counts.skills}
        collapsed={collapsed.skills}
        onToggle={() => toggleCollapse('skills')}
      >
        <SkillPanel onCountChange={(n) => setCount('skills', n)} />
      </CollapsibleSection>

      <CollapsibleSection
        icon={<LinkOutlined />}
        title="MCP 工具"
        subtitle="Model Context Protocol 工具连接（SSE / Stdio / HTTP）"
        count={counts.mcps}
        collapsed={collapsed.mcps}
        onToggle={() => toggleCollapse('mcps')}
      >
        <MCPPanel onCountChange={(n) => setCount('mcps', n)} />
      </CollapsibleSection>

      {/* 底部提示条 */}
      <div style={{ marginTop: 24, textAlign: 'center' }}>
        <Text style={{ color: '#8895b4', fontSize: 12 }}>
          <ThunderboltOutlined style={{ color: '#a78bfa' }} /> 提示：点击顶部
          「一键自动发现」自动扫描本机 opencode 配置并同步到平台
        </Text>
      </div>
    </div>
  );
}

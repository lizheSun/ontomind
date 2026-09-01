/**
 * 总览 — 对齐 Yao /dashboard/assistants：标题 + 筛选 + 专家卡片列表。
 */
import { useMemo, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Input } from 'antd';
import {
  ApiOutlined,
  AppstoreOutlined,
  CodeOutlined,
  DatabaseOutlined,
  DesktopOutlined,
  MessageOutlined,
  RobotOutlined,
  SafetyOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { PageHeader } from '../../components/common/PageHeader';
import { DOMAINS, domainHome } from '../../nav';

const ICONS: Record<string, ReactNode> = {
  overview: <SearchOutlined />,
  chat: <MessageOutlined />,
  board: <AppstoreOutlined />,
  codeops: <CodeOutlined />,
  dataops: <DatabaseOutlined />,
  modelops: <RobotOutlined />,
  agentops: <ApiOutlined />,
  govops: <SafetyOutlined />,
  infra: <DesktopOutlined />,
};

const TAGS: Record<string, { label: string; bg: string; color: string }[]> = {
  chat: [
    { label: 'OpenCode', bg: '#e6f7ff', color: '#0958d9' },
    { label: 'DSH', bg: '#f6ffed', color: '#389e0d' },
  ],
  board: [
    { label: 'Kanban', bg: '#e6f7ff', color: '#0958d9' },
    { label: 'Task', bg: '#fff7e6', color: '#d48806' },
  ],
  codeops: [
    { label: 'Workspace', bg: '#fff7e6', color: '#d48806' },
    { label: 'CI/CD', bg: '#e6f7ff', color: '#0958d9' },
  ],
  dataops: [
    { label: 'Warehouse', bg: '#f6ffed', color: '#389e0d' },
    { label: 'Ontology', bg: '#f9f0ff', color: '#531dab' },
    { label: 'Wiki', bg: '#fff7e6', color: '#d48806' },
  ],
  modelops: [
    { label: 'Gateway', bg: '#e6f7ff', color: '#0958d9' },
    { label: 'Eval', bg: '#fff0f6', color: '#c41d7f' },
  ],
  agentops: [
    { label: 'Agent', bg: '#fff7e6', color: '#d48806' },
    { label: 'Skill', bg: '#e6fffb', color: '#08979c' },
    { label: 'Deploy', bg: '#f6ffed', color: '#389e0d' },
  ],
  govops: [
    { label: 'LLM', bg: '#e6f7ff', color: '#0958d9' },
    { label: 'Security', bg: '#fff1f0', color: '#cf1322' },
  ],
  infra: [
    { label: 'AIDE', bg: '#e6f7ff', color: '#0958d9' },
    { label: 'Compute', bg: '#f6ffed', color: '#389e0d' },
  ],
};

const COPY: Record<string, string> = {
  chat: '原生会话。OpenCode 与 DeepSeek Harness 作为插件接入，输入框即可切换。',
  board: '任务看板。卡片绑定会话，列是工作流，运行状态单独过滤。',
  codeops: 'AI 辅助编码工作台与 CI/CD 流水线，把仓库、审查和发布放在同一处。',
  dataops: '数据仓库、知识库、元数据标注与本体建模，从资产到语义层一条链。',
  modelops: '实验对比、推理网关与模型监控，把服务质量和漂移看清楚。',
  agentops: '设计 Agent / Skill，编排方案并发布到算力节点。',
  govops: 'LLM 多套配置、资产目录、安全合规与成本归因。',
  infra: '电脑、容器与 AIDE。节点是执行环境，容器即工作区。',
};

const FILTERS = ['全部', '会话', '看板', 'CodeOps', 'DataOps', 'ModelOps', 'AgentOps', 'GovOps', 'Infra'];

export default function OverviewPage() {
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [tab, setTab] = useState('全部');

  const cards = useMemo(() => {
    return DOMAINS.filter((d) => d.key !== 'overview')
      .filter((d) => (tab === '全部' ? true : d.label === tab))
      .filter((d) => {
        if (!q.trim()) return true;
        const hay = `${d.label} ${d.hint} ${COPY[d.key] ?? ''}`.toLowerCase();
        return hay.includes(q.trim().toLowerCase());
      });
  }, [q, tab]);

  return (
    <div className="om-page page-enter">
      <PageHeader
        title={
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <MessageOutlined style={{ color: 'var(--accent)' }} />
            工作台
          </span>
        }
        desc="所有 Agent、工作区与数据能力集中在一处。从卡片进入对应域。"
      />

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <Input
          prefix={<SearchOutlined style={{ color: 'var(--text-tertiary)' }} />}
          placeholder="搜索域、能力…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          style={{ flex: 1, height: 40 }}
          allowClear
        />
        <Button type="primary" size="large" icon={<SearchOutlined />}>
          搜索
        </Button>
      </div>

      <div
        style={{
          display: 'flex',
          gap: 4,
          borderBottom: '1px solid var(--border-hairline)',
          marginBottom: 16,
          overflowX: 'auto',
        }}
      >
        {FILTERS.map((f) => {
          const active = tab === f;
          return (
            <button
              key={f}
              type="button"
              onClick={() => setTab(f)}
              style={{
                border: 'none',
                background: 'transparent',
                padding: '8px 12px',
                fontSize: 13,
                cursor: 'pointer',
                color: active ? 'var(--accent)' : 'var(--text-tertiary)',
                fontWeight: active ? 500 : 400,
                borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
                fontFamily: 'inherit',
                whiteSpace: 'nowrap',
              }}
            >
              {f}
            </button>
          );
        })}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {cards.map((d) => (
          <article key={d.key} className="om-card" style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: 8,
                background: 'var(--bg-subtle)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 22,
                color: d.color,
                flexShrink: 0,
              }}
            >
              {ICONS[d.key]}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>{d.label}</div>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, margin: '8px 0' }}>
                {(TAGS[d.key] ?? []).map((t) => (
                  <span
                    key={t.label}
                    className="om-chip"
                    style={{ background: t.bg, color: t.color }}
                  >
                    {t.label}
                  </span>
                ))}
              </div>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.55, margin: 0 }}>
                {COPY[d.key]}
              </p>
              <div style={{ marginTop: 12 }}>
                <Button type="primary" size="small" icon={<MessageOutlined />} onClick={() => navigate(domainHome(d))}>
                  进入
                </Button>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

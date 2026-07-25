/**
 * AgentModeSwitcher — Plan / Build primary agent 切换.
 * 视觉：极简线稿图标 + label；segmented pill 分组；置于 header 与 Settings 齿轮相邻.
 */
import { useMemo } from 'react';
import { useAgents } from '../hooks/useAgents';
import { useOpencodeStore } from '../stores/opencodeStore';

const HIDDEN = new Set(['compaction', 'summary', 'title']);

interface Props {
  disabled?: boolean;
}

// 「Build」= 简化的方形 hammer / anvil (锤形几何三角)，代表"打造"
function IconBuild() {
  return (
    <svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2.5 8l3-2.5v5L2.5 8z" />
      <path d="M5.5 8h5" />
      <path d="M10.5 6l3 2-3 2V6z" fill="currentColor" fillOpacity="0.18" />
    </svg>
  );
}

// 「Plan」= 极细「路径 + 圆点」，代表"规划路径"
function IconPlan() {
  return (
    <svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="3.5" cy="4" r="1.3" />
      <circle cx="12.5" cy="12" r="1.3" />
      <path d="M4.8 4h4.4a2 2 0 0 1 0 4H6.8a2 2 0 0 0 0 4h4.4" />
    </svg>
  );
}

function iconFor(name: string) {
  if (name === 'build') return <IconBuild />;
  if (name === 'plan') return <IconPlan />;
  return null;
}

function labelFor(name: string) {
  if (name === 'build') return 'Build';
  if (name === 'plan') return 'Plan';
  return name;
}

export default function AgentModeSwitcher({ disabled }: Props) {
  const { agents } = useAgents();
  const current = useOpencodeStore((s) => s.currentAgent);
  const setAgent = useOpencodeStore((s) => s.setCurrentAgent);

  const primary = useMemo(
    () =>
      agents
        .filter((a) => a.mode === 'primary' && !HIDDEN.has(a.name))
        .sort((a, b) => {
          const rank = (n: string) => (n === 'build' ? 0 : n === 'plan' ? 1 : 2);
          const r = rank(a.name) - rank(b.name);
          return r !== 0 ? r : a.name.localeCompare(b.name);
        }),
    [agents],
  );

  if (primary.length === 0) return null;

  return (
    <div className="oc-mode-group" role="group" aria-label="agent mode">
      {primary.map((a) => (
        <button
          key={a.name}
          type="button"
          className="oc-mode-pill"
          data-mode={a.name}
          data-active={current === a.name || undefined}
          disabled={disabled}
          title={a.description || a.name}
          onClick={() => setAgent(a.name)}
        >
          {iconFor(a.name)}
          <span>{labelFor(a.name)}</span>
        </button>
      ))}
    </div>
  );
}

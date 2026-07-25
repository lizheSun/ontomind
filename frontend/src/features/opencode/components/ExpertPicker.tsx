/**
 * ExpertPicker — Header 里的专家选择器
 *
 * 核心：选中专家 → 设置 currentAgent = expert.slug，用 opencode 原生 @agent 路由.
 * opencode 从 ~/.config/opencode/agent/{slug}.md 读取角色定义 & tools & model.
 *
 * ⚠️ opencode server 只在启动时扫描 agent 目录. 新增/编辑专家后需重启 opencode 才能通过 @agent 路由.
 * 未 discover 的专家会在下拉里灰显 + 提示"需重启 opencode".
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Dropdown, message, Tag, Tooltip } from 'antd';
import type { MenuProps } from 'antd';
import { expertService, type Expert } from '../../../services/expert.service';
import * as oc from '../client';
import type { OcAgent } from '../types';
import { useOpencodeStore } from '../stores/opencodeStore';

const LS_CACHE = 'oc:expert-list-cache';

function IconCaret() {
  return (
    <svg viewBox="0 0 16 16" width="10" height="10" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 6l4 4 4-4" />
    </svg>
  );
}

export default function ExpertPicker() {
  const [experts, setExperts] = useState<Expert[]>([]);
  const [ocAgents, setOcAgents] = useState<OcAgent[]>([]);
  const currentAgent = useOpencodeStore((s) => s.currentAgent);
  const setExpert = useOpencodeStore((s) => s.setCurrentExpert);
  const setCurrentModel = useOpencodeStore((s) => s.setCurrentModel);
  const setCurrentAgent = useOpencodeStore((s) => s.setCurrentAgent);
  const upsertSession = useOpencodeStore((s) => s.upsertSession);
  const setActiveSession = useOpencodeStore((s) => s.setActiveSession);

  const load = useCallback(async () => {
    try {
      const [list, agents] = await Promise.all([
        expertService.list(),
        oc.listAgents().catch(() => []),
      ]);
      setExperts(list);
      setOcAgents(agents);
      try { window.localStorage.setItem(LS_CACHE, JSON.stringify(list)); }
      catch { /* ignore */ }
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    void load();
    const t = window.setInterval(() => void load(), 15000);
    return () => window.clearInterval(t);
  }, [load]);

  // opencode 已 discover 的 agent 名字集合
  const ocAgentNames = useMemo(
    () => new Set(ocAgents.map((a) => a.name)),
    [ocAgents],
  );

  const current = useMemo(
    () => experts.find((e) => e.slug === currentAgent) || null,
    [experts, currentAgent],
  );
  const online = experts.filter((e) => e.status === 'online');

  const select = async (id: number | null) => {
    if (id == null) {
      setExpert(null, null);
      setCurrentModel(null);
      setCurrentAgent('build');
      message.success('已切回 Build 默认 agent');
      return;
    }
    const e = experts.find((x) => x.id === id);
    if (!e) return;
    if (!ocAgentNames.has(e.slug)) {
      message.warning(
        `opencode 尚未识别 ${e.slug}，请重启 opencode server：opencode serve --port 4096 --cors http://localhost:5173`,
        6,
      );
      return;
    }
    setCurrentAgent(e.slug);
    if (e.provider && e.model) {
      setCurrentModel({ providerID: e.provider, modelID: e.model });
    }
    setExpert(null, null);

    try {
      const session = await oc.createSession({ title: `${e.avatar || '🧑‍💼'} ${e.name}` });
      upsertSession(session);
      setActiveSession(session.id);
      message.success(`已切换到「${e.name}」`);
    } catch {
      message.success(`已切换到「${e.name}」`);
    }
  };

  const items: MenuProps['items'] = [
    {
      key: 'default',
      label: (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, minWidth: 260 }}>
          <span>⚡ Build (默认)</span>
          {currentAgent === 'build' && <Tag color="blue" style={{ margin: 0 }}>当前</Tag>}
        </div>
      ),
      onClick: () => void select(null),
    },
    { type: 'divider' },
    ...(online.length === 0
      ? [{
          key: 'empty',
          label: (
            <span style={{ color: 'var(--ink-40)', fontSize: 12 }}>
              暂无在线专家 — 先在专家团启动
            </span>
          ),
          disabled: true,
        }]
      : online.map((e) => {
          const discovered = ocAgentNames.has(e.slug);
          return {
            key: `expert-${e.id}`,
            label: (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, minWidth: 260, opacity: discovered ? 1 : 0.5 }}>
                <span>
                  {e.avatar || '🧑‍💼'} {e.name}
                  {!discovered && (
                    <Tag style={{ marginLeft: 6, fontSize: 10 }} color="orange">未加载</Tag>
                  )}
                </span>
                {currentAgent === e.slug && <Tag color="blue" style={{ margin: 0 }}>当前</Tag>}
              </div>
            ),
            onClick: () => void select(e.id),
          };
        })),
    { type: 'divider' },
    {
      key: 'manage',
      label: <span style={{ fontWeight: 500 }}>管理专家团 →</span>,
      onClick: () => { window.location.href = '/experts'; },
    },
  ];

  const isBuild = currentAgent === 'build';
  const hasUnloaded = online.some((e) => !ocAgentNames.has(e.slug));

  const button = (
    <button
      type="button"
      style={{
        height: 28,
        padding: '0 10px',
        borderRadius: 999,
        background: current ? 'var(--oc-selected)' : 'var(--oc-bg-layer-2)',
        border: current ? '1px solid var(--oc-blue-500)' : '1px solid var(--oc-border-muted)',
        color: current ? 'var(--oc-blue-500)' : 'var(--oc-text-base)',
        fontSize: 12,
        fontWeight: 500,
        cursor: 'pointer',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        maxWidth: 240,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        position: 'relative',
      }}
      title={current?.description || 'Build 默认 agent'}
    >
      <span style={{ fontSize: 14, lineHeight: 1 }}>
        {current?.avatar || (isBuild ? '⚡' : '🧑‍💼')}
      </span>
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {current?.name || 'Build (默认)'}
      </span>
      <IconCaret />
      {hasUnloaded && (
        <span
          style={{
            position: 'absolute',
            top: -2, right: -2,
            width: 8, height: 8, borderRadius: '50%',
            background: '#f59e0b',
            border: '1.5px solid var(--oc-bg-base, #fafaf7)',
          }}
        />
      )}
    </button>
  );

  return (
    <Dropdown menu={{ items }} placement="bottomRight" trigger={['click']}>
      {hasUnloaded ? (
        <Tooltip title="有专家尚未被 opencode 识别，请重启 opencode server" placement="bottomRight">
          {button}
        </Tooltip>
      ) : (
        button
      )}
    </Dropdown>
  );
}

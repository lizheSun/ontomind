/**
 * MentionPopover — opencode-style @ 面板.
 * 显示 agent + file 两类，供用户选择.
 * 选 agent → 插入 `@agent-name`（opencode 原生解释为 agent 路由）
 * 选 file → 插入 `@filepath`
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import * as oc from '../client';
import type { OcAgent } from '../types';

interface Props {
  visible: boolean;
  query: string;
  onSelect: (value: string) => void;
  onClose: () => void;
}

interface AgentItem {
  kind: 'agent';
  name: string;
  label: string;
  description?: string;
}

interface FileItem {
  kind: 'file';
  path: string;
  filename: string;
  dir: string;
}

type Item = AgentItem | FileItem;

export default function MentionPopover({ visible, query, onSelect, onClose }: Props) {
  const [agents, setAgents] = useState<OcAgent[]>([]);
  const [files, setFiles] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);
  const ref = useRef<HTMLDivElement | null>(null);

  // 加载 agents（仅首次）
  useEffect(() => {
    if (!visible) return;
    oc.listAgents().then(setAgents).catch(() => setAgents([]));
  }, [visible]);

  // 加载 files（debounce 200ms）
  useEffect(() => {
    if (!visible) return;
    const t = window.setTimeout(async () => {
      const q = query.trim();
      if (!q) { setFiles([]); return; }
      setLoading(true);
      try {
        const list = await oc.findFiles(q, { type: 'file', limit: 10 });
        setFiles(list);
      } catch { setFiles([]); }
      finally { setLoading(false); }
    }, 200);
    return () => window.clearTimeout(t);
  }, [query, visible]);

  const items: Item[] = useMemo(() => {
    const out: Item[] = [];
    const kw = query.trim().toLowerCase();
    // Agents: 匹配 name/description
    for (const a of agents) {
      const n = a.name.toLowerCase();
      const d = (a.description || '').toLowerCase();
      if (!kw || n.includes(kw) || d.includes(kw)) {
        out.push({ kind: 'agent', name: a.name, label: `@${a.name}`, description: a.description });
      }
    }
    // Files: 按路径匹配
    for (const f of files) {
      const parts = f.split('/');
      const filename = parts[parts.length - 1];
      const dir = parts.slice(0, -1).join('/');
      if (!kw || filename.toLowerCase().includes(kw) || f.toLowerCase().includes(kw)) {
        out.push({ kind: 'file', path: f, filename, dir });
      }
    }
    return out.slice(0, 16);
  }, [agents, files, query]);

  useEffect(() => setActiveIdx(0), [query, visible]);

  useEffect(() => {
    if (!visible) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIdx((i) => Math.min(items.length - 1, i + 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIdx((i) => Math.max(0, i - 1));
      } else if (e.key === 'Enter' || e.key === 'Tab') {
        if (items.length > 0) {
          e.preventDefault();
          e.stopPropagation();
          const item = items[activeIdx];
          const val = item.kind === 'agent' ? `@${item.name}` : `@${item.path}`;
          onSelect(val);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', handler, true);
    return () => window.removeEventListener('keydown', handler, true);
  }, [visible, items, activeIdx, onSelect, onClose]);

  useEffect(() => {
    ref.current
      ?.querySelector<HTMLDivElement>(`[data-idx="${activeIdx}"]`)
      ?.scrollIntoView({ block: 'nearest' });
  }, [activeIdx]);

  if (!visible) return null;

  return (
    <div className="oc-popover" ref={ref} onMouseDown={(e) => e.preventDefault()}>
      {loading ? (
        <div className="oc-popover-empty">Searching…</div>
      ) : items.length === 0 ? (
        <div className="oc-popover-empty">
          {query.trim() ? `No results for "${query}"` : 'Type to search agents & files…'}
        </div>
      ) : (
        items.map((item, idx) => {
          const active = idx === activeIdx;
          if (item.kind === 'agent') {
            return (
              <div
                key={`agent:${item.name}`}
                data-idx={idx}
                className="oc-popover-item"
                data-active={active || undefined}
                onMouseEnter={() => setActiveIdx(idx)}
                onClick={() => onSelect(item.label)}
              >
                <span className="oc-popover-item-primary">{item.label}</span>
                <span className="oc-popover-item-secondary" title={item.description}>
                  {item.description || ''}
                </span>
                <span className="oc-popover-item-badge" data-source="command">
                  agent
                </span>
              </div>
            );
          }
          return (
            <div
              key={`file:${item.path}`}
              data-idx={idx}
              className="oc-popover-item"
              data-active={active || undefined}
              onMouseEnter={() => setActiveIdx(idx)}
              onClick={() => onSelect(`@${item.path}`)}
            >
              <span className="oc-popover-item-primary">{item.filename}</span>
              <span className="oc-popover-item-secondary" title={item.dir}>
                {item.dir}
              </span>
              <span className="oc-popover-item-badge">file</span>
            </div>
          );
        })
      )}
    </div>
  );
}
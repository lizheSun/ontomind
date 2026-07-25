/**
 * SlashPopover — opencode-style command menu.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import type { OcCommand } from '../types';

interface Props {
  visible: boolean;
  query: string;
  commands: OcCommand[];
  loading?: boolean;
  onSelect: (cmd: OcCommand) => void;
  onClose: () => void;
}

function filter(list: OcCommand[], q: string): OcCommand[] {
  const kw = q.trim().toLowerCase();
  if (!kw) return list.slice(0, 12);
  const prefix: OcCommand[] = [];
  const contains: OcCommand[] = [];
  for (const c of list) {
    const n = (c.name || '').toLowerCase();
    const d = (c.description || '').toLowerCase();
    if (n.startsWith(kw)) prefix.push(c);
    else if (n.includes(kw) || d.includes(kw)) contains.push(c);
  }
  return [...prefix, ...contains].slice(0, 12);
}

export default function SlashPopover({
  visible,
  query,
  commands,
  loading,
  onSelect,
  onClose,
}: Props) {
  const filtered = useMemo(() => filter(commands, query), [commands, query]);
  const [activeIdx, setActiveIdx] = useState(0);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setActiveIdx(0);
  }, [query, visible]);

  useEffect(() => {
    if (!visible) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIdx((i) => Math.min(filtered.length - 1, i + 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIdx((i) => Math.max(0, i - 1));
      } else if (e.key === 'Enter' || e.key === 'Tab') {
        if (filtered.length > 0) {
          e.preventDefault();
          e.stopPropagation();
          onSelect(filtered[activeIdx]);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', handler, true);
    return () => window.removeEventListener('keydown', handler, true);
  }, [visible, filtered, activeIdx, onSelect, onClose]);

  useEffect(() => {
    ref.current
      ?.querySelector<HTMLDivElement>(`[data-idx="${activeIdx}"]`)
      ?.scrollIntoView({ block: 'nearest' });
  }, [activeIdx]);

  if (!visible) return null;

  return (
    <div className="oc-popover" ref={ref} onMouseDown={(e) => e.preventDefault()}>
      {loading ? (
        <div className="oc-popover-empty">Loading…</div>
      ) : filtered.length === 0 ? (
        <div className="oc-popover-empty">No match for "/{query}"</div>
      ) : (
        filtered.map((c, idx) => {
          const src = (c as { source?: string }).source;
          return (
            <div
              key={`${src || 'cmd'}-${c.name}-${idx}`}
              data-idx={idx}
              className="oc-popover-item"
              data-active={idx === activeIdx || undefined}
              onMouseEnter={() => setActiveIdx(idx)}
              onClick={() => onSelect(c)}
            >
              <span className="oc-popover-item-primary">/{c.name}</span>
              <span className="oc-popover-item-secondary" title={c.description}>
                {c.description || ''}
              </span>
              {src && (
                <span className="oc-popover-item-badge" data-source={src}>
                  {src}
                </span>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}

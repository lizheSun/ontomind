/**
 * ModelSwitcher — pill + popover 选模型.
 * Cmd/Ctrl+M 打开；Esc 关闭；点外面关闭；带搜索框.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useProviders } from '../hooks/useProviders';
import { useOpencodeStore } from '../stores/opencodeStore';

function IconCaret() {
  return (
    <svg className="oc-pill-caret" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function IconCheck() {
  return (
    <svg className="oc-model-item-check" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 8.5l3.5 3.5 6.5-8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

interface Props {
  openTrigger?: number;
}

export default function ModelSwitcher({ openTrigger }: Props) {
  const { providers, defaults, loading, reload } = useProviders();
  const current = useOpencodeStore((s) => s.currentModel);
  const setCurrent = useOpencodeStore((s) => s.setCurrentModel);

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement | null>(null);
  const popRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (openTrigger && openTrigger > 0) setOpen(true);
  }, [openTrigger]);

  useEffect(() => {
    if (open) {
      setQuery('');
      window.setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (popRef.current && !popRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const filtered = useMemo(() => {
    const kw = query.trim().toLowerCase();
    if (!kw) return providers;
    return providers
      .map((p) => ({
        ...p,
        models: p.models.filter(
          (m) => m.id.toLowerCase().includes(kw) || (m.name || '').toLowerCase().includes(kw),
        ),
      }))
      .filter((p) => p.models.length > 0 || p.name.toLowerCase().includes(kw));
  }, [providers, query]);

  const displayCurrent = () => {
    if (current) return `${current.providerID}/${current.modelID}`;
    const firstDefault = Object.entries(defaults)[0];
    if (firstDefault) return `${firstDefault[0]}/${firstDefault[1]}`;
    return 'Select model';
  };

  const totalModels = providers.reduce((a, p) => a + p.models.length, 0);

  return (
    <div style={{ position: 'relative', display: 'inline-flex' }}>
      <button
        type="button"
        className="oc-pill"
        onClick={() => setOpen((v) => !v)}
        title={displayCurrent()}
      >
        <span
          style={{
            fontFamily: 'var(--oc-font-mono)',
            fontSize: 11,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            maxWidth: 400,
          }}
        >
          {displayCurrent()}
        </span>
        <IconCaret />
      </button>

      {open && (
        <div className="oc-model-popover" ref={popRef} onMouseDown={(e) => e.stopPropagation()}>
          <div className="oc-model-popover-header">
            <input
              ref={inputRef}
              type="text"
              placeholder={`搜索 ${totalModels} 个模型…`}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div className="oc-model-popover-body">
            {loading ? (
              <div className="oc-model-empty">Loading…</div>
            ) : providers.length === 0 ? (
              <div className="oc-model-empty">
                <div>未检测到任何 provider</div>
                <div style={{ fontSize: 11, opacity: 0.7 }}>请在本机 opencode 配置后刷新</div>
                <button
                  className="oc-btn oc-btn-secondary"
                  onClick={() => window.open('http://127.0.0.1:4096/', '_blank')}
                >
                  打开 opencode UI 配置
                </button>
              </div>
            ) : filtered.length === 0 ? (
              <div className="oc-model-empty">无匹配</div>
            ) : (
              filtered.map((p) => {
                const defModel = defaults[p.id];
                return (
                  <div key={p.id} className="oc-model-group">
                    <div className="oc-model-group-header">
                      {p.name}
                      {defModel && (
                        <span className="oc-hint-chip" style={{ padding: '0 6px', fontSize: 9 }}>
                          default: {defModel}
                        </span>
                      )}
                    </div>
                    {p.models.map((m) => {
                      const isCurrent =
                        current?.providerID === p.id && current?.modelID === m.id;
                      return (
                        <div
                          key={`${p.id}/${m.id}`}
                          className="oc-model-item"
                          data-current={isCurrent || undefined}
                          onClick={() => {
                            setCurrent({ providerID: p.id, modelID: m.id });
                            setOpen(false);
                          }}
                        >
                          <IconCheck />
                          <span className="oc-model-item-id">{m.id}</span>
                          {m.name && m.name !== m.id && (
                            <span className="oc-model-item-name">{m.name}</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                );
              })
            )}
          </div>
          <div className="oc-model-popover-footer">
            <div style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
              <span className="oc-hint-chip">esc</span>
            </div>
            <div style={{ display: 'inline-flex', gap: 8 }}>
              {current && (
                <button
                  type="button"
                  className="oc-btn oc-btn-secondary"
                  style={{ height: 22, padding: '0 8px', fontSize: 11 }}
                  onClick={() => {
                    setCurrent(null);
                    setOpen(false);
                  }}
                >
                  使用默认
                </button>
              )}
              <button
                type="button"
                className="oc-btn oc-btn-secondary"
                style={{ height: 22, padding: '0 8px', fontSize: 11 }}
                onClick={() => void reload()}
              >
                ↻
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

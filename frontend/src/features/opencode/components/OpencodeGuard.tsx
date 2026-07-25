/**
 * Guard：opencode server 未就绪时显示引导页.
 */
import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { message } from 'antd';
import api from '../../../services/api';
import { useOpencodeHealth } from '../hooks/useOpencodeHealth';

interface Props {
  children: ReactNode;
}

export default function OpencodeGuard({ children }: Props) {
  const { loading, healthy, baseUrl, reason, refresh } = useOpencodeHealth(null);
  const [spawning, setSpawning] = useState(false);

  useEffect(() => {
    if (healthy) return;
    const t = window.setInterval(() => void refresh(), 5000);
    return () => window.clearInterval(t);
  }, [healthy, refresh]);

  const spawn = async () => {
    setSpawning(true);
    try {
      await api.post('/opencode/spawn', {
        port: 4096,
        cors: 'http://localhost:5173',
      });
      message.success('opencode server 已启动');
      setTimeout(() => void refresh(), 800);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '启动失败（可能未在 DEBUG 模式）');
    } finally {
      setSpawning(false);
    }
  };

  if (loading) {
    return (
      <div className="oc-scope" style={{ padding: 48 }}>
        <div className="oc-empty">Loading…</div>
      </div>
    );
  }

  if (!healthy) {
    return (
      <div
        className="oc-scope"
        style={{
          height: '100%',
          background: 'var(--oc-bg-base)',
          padding: '48px 24px',
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        <div style={{ maxWidth: 560, width: '100%', color: 'var(--oc-text-base)' }}>
          <h2 style={{ margin: 0, marginBottom: 16, fontSize: 20, fontWeight: 600 }}>
            OpenCode server 未就绪
          </h2>
          <p style={{ color: 'var(--oc-text-muted)', fontSize: 13, marginBottom: 24 }}>
            对话工作台通过本机 <code>opencode serve</code> 提供全部能力。目标{' '}
            <code>{baseUrl || 'http://127.0.0.1:4096'}</code>
            {reason ? ` — ${reason}` : ''}
          </p>
          <div
            style={{
              padding: 14,
              borderRadius: 10,
              background: 'var(--oc-bg-layer-1)',
              border: '1px solid var(--oc-border-base)',
              fontFamily: 'var(--oc-font-mono)',
              fontSize: 12,
              marginBottom: 12,
              color: 'var(--oc-text-base)',
            }}
          >
            opencode serve --port 4096 --cors http://localhost:5173
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="oc-btn" disabled={spawning} onClick={() => void spawn()}>
              {spawning ? 'Starting…' : 'Start opencode (dev)'}
            </button>
            <button className="oc-btn oc-btn-secondary" onClick={() => void refresh()}>
              Retry
            </button>
          </div>
          <p style={{ color: 'var(--oc-text-faint)', fontSize: 11, marginTop: 16 }}>
            未安装 CLI 请先执行:{' '}
            <code>curl -fsSL https://opencode.ai/install | bash</code>
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

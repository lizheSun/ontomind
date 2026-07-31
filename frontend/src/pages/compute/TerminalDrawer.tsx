/**
 * TerminalDrawer — 容器交互式终端（xterm.js + WebSocket）.
 *
 * 后端 WS 端点用 pty 桥接 docker exec -it，前端 xterm.js 渲染。
 * 协议（文本帧 JSON）：
 *   前端→后端: {"type":"stdin","data":"<str>"} | {"type":"resize","cols":int,"rows":int}
 *   后端→前端: {"type":"ready","shell":"bash"} | {"type":"output","data":"<base64>"}
 *              | {"type":"exit","code":int} | {"type":"error","content":"<str>"}
 */
import { useEffect, useRef, useState } from 'react';
import { Button, Drawer } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import * as srv from '../../services/compute.service';
import type { ComputeNode, ContainerInstance } from './types';

interface Props {
  open: boolean;
  onClose: () => void;
  node: ComputeNode | null;
  container: ContainerInstance | null;
}

type ConnStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

const STATUS_MAP: Record<ConnStatus, { dot: string; label: string }> = {
  connecting: { dot: '#eab308', label: '连接中' },
  connected: { dot: '#22c55e', label: '已连接' },
  disconnected: { dot: '#bfbcb5', label: '已断开' },
  error: { dot: '#dc4446', label: '错误' },
};

export default function TerminalDrawer({ open, onClose, node, container }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<any>(null);
  const fitRef = useRef<any>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [shell, setShell] = useState<string>('');
  const [status, setStatus] = useState<ConnStatus>('disconnected');
  const [reconnectKey, setReconnectKey] = useState(0);

  useEffect(() => {
    if (!open || !node || !container) return;
    setStatus('connecting');

    let cleanupFn: (() => void) | null = null;
    let disposed = false;
    let termDisposed = false;

    const init = async () => {
      if (disposed) return;

      const el = containerRef.current;
      if (!el) {
        console.error('[TerminalDrawer] containerRef is null, cannot open terminal');
        setStatus('error');
        return;
      }

      // 动态加载 xterm，避免页面加载时报 getBoundingClientRect 错误
      const [{ Terminal }, { FitAddon }] = await Promise.all([
        import('@xterm/xterm'),
        import('@xterm/addon-fit'),
      ]);
      await import('@xterm/xterm/css/xterm.css');
      if (disposed || termDisposed) return;

      console.log('[TerminalDrawer] opening terminal for:', container.name, 'node:', node.id, 'cid:', container.id);

      let term: any;
      try {
        term = new Terminal({
          fontFamily: 'var(--font-mono), Menlo, Consolas, monospace',
          fontSize: 13,
          theme: {
            background: '#16171f',
            foreground: '#c8cdf0',
            cursor: '#5b6fc4',
            selectionBackground: '#3b52af55',
          },
          cursorBlink: true,
          convertEol: true,
          scrollback: 5000,
        });
      } catch (e) {
        console.error('[TerminalDrawer] failed to create Terminal:', e);
        setStatus('error');
        return;
      }
      const fit = new FitAddon();
      term.loadAddon(fit);
      term.open(el);
      try { fit.fit(); } catch { /* ignore */ }
      termRef.current = term;
      fitRef.current = fit;
      term.focus();

      const wsUrl = srv.terminalWsUrl(node.id, container.id);
      console.log('[TerminalDrawer] connecting to WS:', wsUrl);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (termDisposed) return;
        const dims = fit.proposeDimensions();
        if (dims) {
          ws.send(JSON.stringify({ type: 'resize', cols: dims.cols, rows: dims.rows }));
        }
      };
      ws.onmessage = (ev) => {
        if (termDisposed) return;
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === 'ready') {
            setShell(msg.shell);
            setStatus('connected');
          } else if (msg.type === 'output') {
            const bytes = Uint8Array.from(atob(msg.data), (c) => c.charCodeAt(0));
            term.write(bytes);
          } else if (msg.type === 'exit') {
            term.write(`\r\n\x1b[33m[进程已退出 code=${msg.code}]\x1b[0m\r\n`);
            setStatus('disconnected');
          } else if (msg.type === 'error') {
            term.write(`\r\n\x1b[31m[错误] ${msg.content}\x1b[0m\r\n`);
            setStatus('error');
          }
        } catch {
          // 忽略非 JSON 帧
        }
      };
      ws.onclose = () => {
        setStatus((s) => (s === 'error' ? s : 'disconnected'));
      };
      ws.onerror = () => setStatus('error');

      const dataDisp = term.onData((data: string) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'stdin', data }));
        }
      });
      const resizeDisp = term.onResize(({ cols, rows }: { cols: number; rows: number }) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'resize', cols, rows }));
        }
      });

      const ro = new ResizeObserver(() => {
        if (termDisposed) return;
        try { fit.fit(); } catch { /* ignore */ }
      });
      ro.observe(el);

      cleanupFn = () => {
        termDisposed = true;
        dataDisp.dispose();
        resizeDisp.dispose();
        ro.disconnect();
        try { ws.close(); } catch { /* ignore */ }
        term.dispose();
        termRef.current = null;
        fitRef.current = null;
        wsRef.current = null;
      };
    };

    // antd Drawer renders via portal — wait one frame for DOM commit
    const raf = requestAnimationFrame(() => { void init(); });

    return () => {
      disposed = true;
      cancelAnimationFrame(raf);
      cleanupFn?.();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, node, container, reconnectKey]);

  useEffect(() => {
    if (!open) return;
    const handler = () => { try { fitRef.current?.fit(); } catch { /* ignore */ } };
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, [open]);

  const sm = STATUS_MAP[status];

  return (
    <Drawer
      title={
        <div className="term-drawer-header">
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5 }}>
            {container?.name}
          </span>
          {shell && <span className="term-drawer-shell">{shell}</span>}
          <span className="term-drawer-status">
            <span style={{
              width: 6, height: 6, borderRadius: '50%',
              background: sm.dot, display: 'inline-block',
            }} />
            {sm.label}
          </span>
          <Button
            size="small" type="text" icon={<ReloadOutlined />}
            onClick={() => setReconnectKey((k) => k + 1)}
          >
            重连
          </Button>
        </div>
      }
      open={open}
      onClose={onClose}
      size="large"
      styles={{ body: { padding: 12, background: '#16171f' } }}
      destroyOnHidden
    >
      <div className="term-container" ref={containerRef} />
    </Drawer>
  );
}

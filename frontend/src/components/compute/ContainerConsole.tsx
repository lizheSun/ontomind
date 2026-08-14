/**
 * 容器交互终端 — xterm.js + Docker PTY (WebSocket)。
 *
 * 相比原实现修复的问题：
 * - shell 不再硬编码 /bin/bash：进入时先探测容器内可用 shell 并自动选中
 *   （opencode / alpine 等镜像点「控制台」直接报错就是这个原因）
 * - 后端下发的 JSON 文本帧（error / notice）会解析并展示，不再被当成乱码写进终端
 * - 连接失败给出可执行的原因，而不是笼统的「终端连接失败」
 * - 自动连接：进入即建立会话，不用再手点一次「连接」
 *
 * 【交互重构】改为纯 props 组件：不再依赖 computeStore.consoleTarget，
 *   由父组件（DockerManagement 的 Drawer）直接传入容器身份。
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { Alert, Button, Card, Select, Space, Spin, Typography } from 'antd';
import {
  CloseOutlined,
  ContainerOutlined,
  DisconnectOutlined,
  ExpandOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { detectShells, getContainerConsoleUrl } from '../../services/compute.service';
import { extractErrMsg } from '../../stores/computeStore';

const { Text } = Typography;

const FALLBACK_SHELLS = [
  { label: 'bash', value: '/bin/bash' },
  { label: 'sh', value: '/bin/sh' },
  { label: 'ash (alpine)', value: '/bin/ash' },
];

interface ContainerConsoleProps {
  nodeId: number;
  containerId: string;
  containerName: string;
  onClose?: () => void;
}

export default function ContainerConsole({
  nodeId,
  containerId,
  containerName,
  onClose,
}: ContainerConsoleProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const clickHandlerRef = useRef<(() => void) | null>(null);
  /** 后端主动下发的错误：用来区分「正常断开」与「起不来」 */
  const serverErrorRef = useRef<string>('');

  const [shell, setShell] = useState<string>('');
  const [shellOptions, setShellOptions] = useState(FALLBACK_SHELLS);
  const [probing, setProbing] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string>('');
  const [notice, setNotice] = useState<string>('');

  // ---- 清理 ----
  const cleanup = useCallback(() => {
    const ws = wsRef.current;
    wsRef.current = null;
    if (ws) {
      ws.onclose = null;   // 主动关闭时不要触发「连接已断开」提示
      ws.onerror = null;
      ws.close();
    }
    resizeObserverRef.current?.disconnect();
    resizeObserverRef.current = null;
    if (clickHandlerRef.current && terminalRef.current) {
      terminalRef.current.removeEventListener('click', clickHandlerRef.current);
      clickHandlerRef.current = null;
    }
    if (termRef.current) {
      termRef.current.dispose();
      termRef.current = null;
    }
    setConnected(false);
    setConnecting(false);
  }, []);

  useEffect(() => cleanup, [cleanup]);

  // ---- 换容器：断开旧会话 + 重置状态，再探测新容器的 shell ----
  useEffect(() => {
    cleanup();
    setError('');
    setNotice('');
    setShell('');
    serverErrorRef.current = '';

    let alive = true;
    setProbing(true);
    detectShells(nodeId, containerId)
      .then((res) => {
        if (!alive) return;
        if (res.shells.length > 0) {
          setShellOptions(
            res.shells.map((s) => ({ label: s.replace('/bin/', ''), value: s })),
          );
          setShell(res.default || res.shells[0]);
        } else {
          setError(
            '容器内没有找到可用的 shell（已尝试 bash / ash / sh）。' +
              '该镜像可能是 distroless 类型，无法打开交互终端。',
          );
          setShellOptions(FALLBACK_SHELLS);
          setShell('/bin/sh');
        }
      })
      .catch((err) => {
        if (!alive) return;
        setNotice(`shell 探测失败（${extractErrMsg(err)}），已使用默认列表`);
        setShellOptions(FALLBACK_SHELLS);
        setShell('/bin/sh');
      })
      .finally(() => alive && setProbing(false));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodeId, containerId]);

  // ---- 连接 ----
  const connect = useCallback(() => {
    if (!terminalRef.current || !shell) return;
    cleanup();
    setError('');
    serverErrorRef.current = '';
    setConnecting(true);

    const term = new Terminal({
      cursorBlink: true,
      cursorStyle: 'bar',
      fontSize: 13,
      fontFamily: "'JetBrains Mono', 'Fira Code', 'SF Mono', Menlo, monospace",
      theme: {
        background: '#1e1e2e',
        foreground: '#cdd6f4',
        cursor: '#f5e0dc',
        selectionBackground: '#585b70',
        black: '#45475a',
        red: '#f38ba8',
        green: '#a6e3a1',
        yellow: '#f9e2af',
        blue: '#89b4fa',
        magenta: '#f5c2e7',
        cyan: '#94e2d5',
        white: '#bac2de',
        brightBlack: '#585b70',
        brightRed: '#f38ba8',
        brightGreen: '#a6e3a1',
        brightYellow: '#f9e2af',
        brightBlue: '#89b4fa',
        brightMagenta: '#f5c2e7',
        brightCyan: '#94e2d5',
        brightWhite: '#a6adc8',
      },
      allowProposedApi: true,
      smoothScrollDuration: 50,
    });
    termRef.current = term;

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    fitAddonRef.current = fitAddon;

    term.open(terminalRef.current);
    try {
      fitAddon.fit();
    } catch {
      /* 容器尚未布局完成，忽略 */
    }

    term.attachCustomKeyEventHandler((e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'c' && term.hasSelection()) {
        return false;
      }
      return true;
    });

    const handleContainerClick = () => term.focus();
    clickHandlerRef.current = handleContainerClick;
    terminalRef.current.addEventListener('click', handleContainerClick);

    const resizeObserver = new ResizeObserver(() => {
      try {
        fitAddon.fit();
      } catch {
        /* ignore */
      }
    });
    resizeObserver.observe(terminalRef.current);
    resizeObserverRef.current = resizeObserver;

    term.onResize(({ cols, rows }) => {
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'resize', cols, rows }));
      }
    });

    term.onData((data) => {
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(new TextEncoder().encode(data).buffer);
      }
    });

    const ws = new WebSocket(getContainerConsoleUrl(nodeId, containerId, shell));
    ws.binaryType = 'arraybuffer';
    wsRef.current = ws;

    ws.onopen = () => {
      setConnecting(false);
      setConnected(true);
      term.focus();
      ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
    };

    ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        term.write(new Uint8Array(event.data));
        return;
      }
      if (typeof event.data === 'string') {
        try {
          const msg = JSON.parse(event.data) as {
            error?: string;
            notice?: string;
            shell?: string;
          };
          if (msg.error) {
            serverErrorRef.current = msg.error;
            setError(msg.error);
            return;
          }
          if (msg.notice) {
            setNotice(msg.notice);
            if (msg.shell) setShell(msg.shell);
            return;
          }
        } catch {
          term.write(event.data);
        }
      }
    };

    ws.onerror = () => {
      setConnecting(false);
      setConnected(false);
      if (!serverErrorRef.current) {
        setError(
          'WebSocket 连接失败。请确认后端已启动（http://localhost:8000），' +
            '且该容器处于运行状态。',
        );
      }
    };

    ws.onclose = (ev) => {
      setConnecting(false);
      setConnected(false);
      if (serverErrorRef.current) return;
      if (termRef.current) {
        term.write('\r\n\x1b[33m[会话已结束]\x1b[0m\r\n');
      }
      if (ev.code !== 1000 && ev.code !== 1005) {
        setError(`连接异常关闭（code=${ev.code}）。可尝试点「重新连接」。`);
      }
    };
  }, [nodeId, containerId, shell, cleanup]);

  // shell 就绪后自动连接
  useEffect(() => {
    if (!shell || probing) return;
    connect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shell, probing, nodeId, containerId]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 顶部信息栏 */}
      <Card
        size="small"
        styles={{ body: { padding: '8px 14px' } }}
        style={{ borderRadius: 0, flexShrink: 0, borderBottom: '1px solid rgba(0,0,0,0.06)' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
          <Space size="middle">
            <ContainerOutlined style={{ color: '#0071e3' }} />
            <Space size={6}>
              <Text strong style={{ fontFamily: 'monospace' }}>
                {containerName || containerId.slice(0, 12)}
              </Text>
              <Text code style={{ fontSize: 11 }}>
                {containerId.slice(0, 12)}
              </Text>
            </Space>
            <Select
              size="small"
              value={shell || undefined}
              onChange={setShell}
              options={shellOptions}
              style={{ width: 140 }}
              loading={probing}
              placeholder="探测 shell…"
              popupMatchSelectWidth={false}
            />
            {(connecting || probing) && <Spin size="small" />}
            {connected && (
              <Text type="success" style={{ fontSize: 12 }}>
                已连接
              </Text>
            )}
          </Space>

          <Space size="small">
            {connected && (
              <Button size="small" icon={<ExpandOutlined />} onClick={() => fitAddonRef.current?.fit()}>
                自适应
              </Button>
            )}
            <Button
              size="small"
              icon={connected ? <DisconnectOutlined /> : <ReloadOutlined />}
              onClick={connected ? cleanup : connect}
              type={connected ? 'default' : 'primary'}
              danger={connected}
              loading={connecting}
              disabled={probing || !shell}
            >
              {connected ? '断开' : '重新连接'}
            </Button>
            {onClose && (
              <Button size="small" icon={<CloseOutlined />} onClick={onClose}>
                关闭
              </Button>
            )}
          </Space>
        </div>
      </Card>

      {notice && !error && (
        <Alert type="info" showIcon closable title={notice} style={{ borderRadius: 0 }} onClose={() => setNotice('')} />
      )}
      {error && (
        <Alert
          type="error"
          showIcon
          closable
          title="终端无法连接"
          description={error}
          style={{ borderRadius: 0 }}
          onClose={() => setError('')}
          action={
            <Button size="small" onClick={connect}>
              重试
            </Button>
          }
        />
      )}

      <div
        ref={terminalRef}
        style={{
          flex: 1,
          background: '#1e1e2e',
          borderRadius: '0 0 8px 8px',
          overflow: 'hidden',
          minHeight: 250,
          padding: '6px 8px',
        }}
      />
    </div>
  );
}

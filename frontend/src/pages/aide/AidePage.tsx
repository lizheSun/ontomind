/**
 * AidePage — AIDE（AI Development Environment）
 *
 * 只负责「工具条」+「未就绪引导」。
 * iframe 本体在 AppLayout 的 <AideHost /> 里常驻，路由切走不卸载
 * （否则每次进来 opencode UI 都要从零重新加载）。
 *
 * 性能设计：
 * 1. 首屏读 sessionStorage 缓存 → 有缓存时 iframe 立刻开始加载，不等接口
 * 2. status 接口带 fast=1（后端只做端口探活 ~2ms，不开子进程）
 * 3. 就绪后停止轮询
 * 4. iframe 常驻 + display 切换 → 二次进入是「瞬显」而非「重载」
 */
import { useCallback, useEffect, useState } from 'react';
import { App, Button, Result, Space, Spin, Tag, Tooltip, Typography } from 'antd';
import {
  ReloadOutlined,
  ExportOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  PlayCircleOutlined,
  PoweroffOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import { aideService } from '../../services/aide.service';
import { useAideStore } from '../../stores/aideStore';

const { Text } = Typography;

export default function AidePage() {
  const { message } = App.useApp();

  const status = useAideStore((s) => s.status);
  const embedUrl = useAideStore((s) => s.embedUrl);
  const loaded = useAideStore((s) => s.loaded);
  const fullscreen = useAideStore((s) => s.fullscreen);
  const setStatus = useAideStore((s) => s.setStatus);
  const setVisible = useAideStore((s) => s.setVisible);
  const setFullscreen = useAideStore((s) => s.setFullscreen);
  const reload = useAideStore((s) => s.reload);

  // 有缓存时不显示 loading（首屏直接渲染，iframe 已在加载）
  const [loading, setLoading] = useState(() => !useAideStore.getState().status);
  const [starting, setStarting] = useState(false);
  const [stopping, setStopping] = useState(false);

  // ---- 进出路由控制 iframe 显隐（不卸载）----
  useEffect(() => {
    setVisible(true);
    return () => {
      setVisible(false);
      // 离开时退出全屏，避免下次进来还是全屏态
      setFullscreen(false);
    };
  }, [setVisible, setFullscreen]);

  // ---- 探活（fast=1，后端 ~2ms）----
  const refresh = useCallback(
    async (opts?: { silent?: boolean; full?: boolean }) => {
      const silent = opts?.silent ?? false;
      if (!silent) setLoading(true);
      try {
        const s = await aideService.status({ fast: !opts?.full });
        setStatus(s);
      } catch (err) {
        if (!silent) {
          message.error(err instanceof Error ? err.message : '获取 AIDE 状态失败');
        }
      } finally {
        if (!silent) setLoading(false);
      }
    },
    [message, setStatus],
  );

  useEffect(() => {
    // 首次进来做一次完整探测（拿 version / cli_path），之后都走 fast
    void refresh({ silent: !!status, full: !status });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 未就绪时才轮询；就绪后完全停止
  useEffect(() => {
    if (status?.healthy) return;
    const t = window.setInterval(() => void refresh({ silent: true }), 5000);
    return () => window.clearInterval(t);
  }, [status?.healthy, refresh]);

  // ---- ESC 退出全屏 ----
  useEffect(() => {
    if (!fullscreen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setFullscreen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [fullscreen, setFullscreen]);

  // ---- 操作 ----
  const doStart = async () => {
    setStarting(true);
    try {
      const r = await aideService.start({ cors: window.location.origin });
      message.success(
        r.already_running ? `opencode web 已在运行：${r.url}` : `opencode web 已启动：${r.url}`,
      );
      await refresh({ full: true });
    } catch (err) {
      message.error(err instanceof Error ? err.message : '启动失败');
    } finally {
      setStarting(false);
    }
  };

  const doStop = async () => {
    if (!status) return;
    setStopping(true);
    try {
      await aideService.stop(status.web_port);
      message.success('opencode web 已停止');
      await refresh({ full: true });
    } catch (err) {
      message.error(err instanceof Error ? err.message : '停止失败');
    } finally {
      setStopping(false);
    }
  };

  const openNewWindow = () => {
    if (embedUrl) window.open(embedUrl, '_blank', 'noopener');
  };

  const ready = !!status?.healthy && !!embedUrl;

  const srcLabel =
    status?.embed_source === 'serve'
      ? '复用 serve'
      : status?.embed_source === 'web'
        ? '独立 web'
        : '未就绪';

  const shellStyle: React.CSSProperties = fullscreen
    ? {
        position: 'fixed',
        inset: 0,
        zIndex: 1001, // 比 AideHost 的 1000 高，工具条盖在 iframe 上方
        background: 'transparent',
        display: 'flex',
        flexDirection: 'column',
        pointerEvents: 'none', // 让 iframe 可点，只有工具条自己接事件
      }
    : {
        height: 'calc(100vh - 56px)',
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--paper-00, #fff)',
        overflow: 'hidden',
      };

  return (
    <div style={shellStyle}>
      {/* ---------- 工具条 ---------- */}
      <div
        style={{
          height: 40,
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '0 12px',
          borderBottom: '1px solid var(--border-hairline, rgba(26,25,24,0.08))',
          background: 'var(--paper-01, #fafaf7)',
          pointerEvents: 'auto',
        }}
      >
        <Space size={8} align="center">
          <CodeOutlined style={{ color: 'var(--accent, #3b52af)', fontSize: 14 }} />
          <span
            style={{
              fontFamily: "'Fraunces', var(--font-serif), serif",
              fontSize: 14,
              fontWeight: 500,
              fontStyle: 'italic',
              color: 'var(--ink-100, #1a1918)',
            }}
          >
            AIDE
          </span>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
              fontSize: 11,
              color: ready ? '#476a4b' : '#8f8b84',
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: ready ? '#22c55e' : '#bfbcb5',
                boxShadow: ready ? '0 0 0 3px rgba(34,197,94,0.13)' : 'none',
              }}
            />
            {ready ? '已连接' : '未就绪'}
          </span>
          {ready && (
            <Tag
              style={{
                fontSize: 10,
                margin: 0,
                color: 'var(--ink-60, #605c56)',
                background: 'var(--paper-02, #f3f2ee)',
                border: '1px solid var(--border-hairline, rgba(26,25,24,0.08))',
              }}
            >
              {srcLabel}
            </Tag>
          )}
          {embedUrl && (
            <Text
              style={{
                fontSize: 11,
                fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
                color: 'var(--ink-40, #8f8b84)',
              }}
            >
              {embedUrl}
            </Text>
          )}
          {status?.version && (
            <Text style={{ fontSize: 11, color: 'var(--ink-40, #8f8b84)' }}>
              v{status.version}
            </Text>
          )}
          {ready && !loaded && (
            <Space size={6}>
              <Spin size="small" />
              <Text style={{ fontSize: 11, color: 'var(--ink-40, #8f8b84)' }}>加载中…</Text>
            </Space>
          )}
        </Space>

        <div style={{ flex: 1 }} />

        <Space size={4}>
          <Tooltip title="重新加载 opencode UI">
            <Button size="small" type="text" icon={<ReloadOutlined />} onClick={reload} />
          </Tooltip>
          <Tooltip title="在新窗口打开">
            <Button
              size="small"
              type="text"
              icon={<ExportOutlined />}
              onClick={openNewWindow}
              disabled={!embedUrl}
            />
          </Tooltip>
          <Tooltip title={fullscreen ? '退出全屏 (Esc)' : '全屏'}>
            <Button
              size="small"
              type="text"
              icon={fullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
              onClick={() => setFullscreen(!fullscreen)}
            />
          </Tooltip>
          {/* 独立 web 才给停止；复用 serve 时不给（避免误关对话工作台） */}
          {status?.embed_source === 'web' ? (
            <Tooltip title="停止 opencode web">
              <Button
                size="small"
                type="text"
                danger
                icon={<PoweroffOutlined />}
                loading={stopping}
                onClick={() => void doStop()}
              />
            </Tooltip>
          ) : !ready ? (
            <Button
              size="small"
              type="primary"
              icon={<PlayCircleOutlined />}
              loading={starting}
              onClick={() => void doStart()}
            >
              启动
            </Button>
          ) : null}
        </Space>
      </div>

      {/* ---------- 主体 ----------
          就绪时这里是「占位空白」，真正的 iframe 由 AppLayout 里的
          <AideHost /> fixed 定位覆盖过来（常驻不卸载）。 */}
      <div style={{ flex: 1, minHeight: 0, position: 'relative', pointerEvents: 'auto' }}>
        {ready ? (
          // iframe 由 AideHost 渲染；这里只在它还没 load 完时给个遮罩
          !loaded ? (
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 12,
                background: 'var(--paper-00, #fff)',
              }}
            >
              <Spin />
              <Text style={{ fontSize: 12, color: 'var(--ink-40, #8f8b84)' }}>
                首次加载 opencode UI…（之后切换页面不会再重载）
              </Text>
            </div>
          ) : null
        ) : loading ? (
          <div
            style={{
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 12,
            }}
          >
            <Spin />
            <Text style={{ fontSize: 12, color: 'var(--ink-40, #8f8b84)' }}>
              探测 opencode…
            </Text>
          </div>
        ) : (
          <div
            style={{
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 24,
            }}
          >
            <Result
              status="info"
              icon={<CodeOutlined style={{ color: 'var(--accent, #3b52af)' }} />}
              title="opencode 未就绪"
              subTitle={
                <div style={{ textAlign: 'left', maxWidth: 560, margin: '0 auto' }}>
                  <p style={{ color: 'var(--ink-60, #605c56)', fontSize: 13 }}>
                    AIDE 需要本机跑着 opencode。两种方式任选其一：
                  </p>
                  <div
                    style={{
                      background: 'var(--paper-02, #f3f2ee)',
                      border: '1px solid var(--border-hairline, rgba(26,25,24,0.08))',
                      borderRadius: 8,
                      padding: '10px 12px',
                      fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
                      fontSize: 12,
                      lineHeight: 1.9,
                      color: 'var(--ink-80, #35322e)',
                    }}
                  >
                    <div style={{ color: 'var(--ink-40, #8f8b84)' }}>
                      # 方式 1：复用对话工作台的 serve（推荐，opencode ≥ 1.18 自带 UI）
                    </div>
                    <div>
                      opencode serve --port {status?.serve_port ?? 4096} --cors{' '}
                      {window.location.origin}
                    </div>
                    <div style={{ height: 8 }} />
                    <div style={{ color: 'var(--ink-40, #8f8b84)' }}>
                      # 方式 2：独立 web（点下面「一键启动」等价）
                    </div>
                    <div>
                      opencode web --port {status?.web_port ?? 4097} --cors{' '}
                      {window.location.origin}
                    </div>
                  </div>
                  {status && !status.cli_installed && (
                    <p style={{ color: '#a5361e', fontSize: 12, marginTop: 12 }}>
                      ⚠️ 本机未检测到 opencode CLI，请先安装：
                      <br />
                      <code>curl -fsSL https://opencode.ai/install | bash</code>
                    </p>
                  )}
                </div>
              }
              extra={
                <Space>
                  <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    loading={starting}
                    onClick={() => void doStart()}
                    disabled={status ? !status.cli_installed : false}
                  >
                    一键启动 opencode web
                  </Button>
                  <Button icon={<ReloadOutlined />} onClick={() => void refresh({ full: true })}>
                    重新探测
                  </Button>
                </Space>
              }
            />
          </div>
        )}
      </div>
    </div>
  );
}

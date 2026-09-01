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
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, App, Button, Result, Select, Space, Spin, Tag, Tooltip, Typography } from 'antd';
import {
  ReloadOutlined,
  ExportOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  PlayCircleOutlined,
  PoweroffOutlined,
  CodeOutlined,
  ApiOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { aideService } from '../../services/aide.service';
import { useAideStore } from '../../stores/aideStore';
import {
  discoverContainerServices,
  listContainerServices,
} from '../../services/compute.service';
import type { AideContainerSource, ContainerServiceInfo } from '../../types/compute';

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

  // ---- 容器服务源（从 MySQL container_services 读，不再实时扫容器）----
  const containerSource = useAideStore((s) => s.containerSource);
  const setContainerSource = useAideStore((s) => s.setContainerSource);
  /** 全部 opencode 类服务（含不可用的，便于告知原因） */
  const [services, setServices] = useState<ContainerServiceInfo[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(false);

  /**
   * 拉取可选服务列表。
   *
   * @param refresh  true 时让后端回探每个已登记服务的真实状态
   * @param discover true 时先扫描容器，把「在跑但 DB 未登记」的服务补录进来
   *
   * 为什么需要 discover：用户可能直接在容器控制台里敲 `opencode web`，
   * 平台没经手过、DB 里就没有这条登记。只 refresh 是发现不了的 ——
   * 这正是「我启动了 opencode web 但 AIDE 还是不可用」的原因之一。
   */
  const fetchServices = useCallback(
    async (refresh = false, discover = false) => {
      setSourcesLoading(true);
      try {
        const rows = discover
          ? (await discoverContainerServices()).services
          : await listContainerServices(undefined, refresh);
        // 只关心 opencode 类（other 类不能拿来嵌 AIDE）
        setServices(rows.filter((r) => r.kind !== 'other'));
      } catch {
        /* 静默：AIDE 主流程不依赖它 */
      } finally {
        setSourcesLoading(false);
      }
    },
    [],
  );

  // 首屏：扫描发现 + 回探，确保新起的服务也能立刻出现在下拉里
  useEffect(() => {
    void fetchServices(false, true);
  }, [fetchServices]);

  /**
   * 未就绪时自动轮询服务状态（10s）。
   * 覆盖「用户刚在容器里起了 opencode，回到 AIDE 页面等它自己亮起来」的场景。
   * 已选中并连上后停止轮询，避免无谓开销。
   */
  useEffect(() => {
    if (containerSource) return;
    const t = window.setInterval(() => {
      void fetchServices(false, true);
    }, 10_000);
    return () => window.clearInterval(t);
  }, [containerSource, fetchServices]);

  /** 把服务记录转成 store 需要的 AideContainerSource */
  const toAideSource = (svc: ContainerServiceInfo): AideContainerSource => ({
    node_id: svc.node_id,
    node_name: svc.node_name,
    container_id: svc.container_id,
    container_name: svc.container_name,
    port: svc.host_port ?? 0,
    container_port: svc.container_port,
    image: svc.image ?? '',
  });

  /** 选中某个服务前先确认它当前真的可用 */
  const pickService = async (serviceId: number) => {
    const svc = services.find((x) => x.id === serviceId);
    if (!svc) return;
    if (!svc.host_reachable || !svc.host_port) {
      // 把「为什么不能用 + 怎么修」一次说清，而不是笼统一句「不可用」
      const hint = !svc.host_port
        ? `容器内 ${svc.container_port} 端口没有映射到宿主，浏览器无法访问。` +
          `请到「电脑 → 容器」用「修改配置」给该端口加映射，或把服务改起在已映射的端口上。`
        : svc.status_detail || '宿主访问不到，请到「电脑 → 服务」页排查';
      message.warning(hint, 8);
      return;
    }
    setContainerSource(toAideSource(svc));
    message.success(`已切换到 ${svc.container_name} · ${svc.access_url}`);
  };

  /**
   * 手动「扫描并刷新」：先 discover（补录未登记的服务）再回探状态。
   * 刷新完给出可执行结论 —— 有几个可用、不可用的是什么原因。
   */
  const doRefreshServices = async () => {
    setSourcesLoading(true);
    try {
      const r = await discoverContainerServices();
      const oc = r.services.filter((x) => x.kind !== 'other');
      setServices(oc);
      const usable = oc.filter((x) => x.is_aide_source);
      if (usable.length > 0) {
        message.success(`发现 ${usable.length} 个可用 opencode 服务（共 ${oc.length} 个）`);
      } else if (oc.length > 0) {
        // 有服务但都不可用 —— 直接把最典型的原因说出来
        const blocked = oc.find((x) => x.status === 'running' && !x.host_reachable);
        message.warning(
          blocked
            ? `找到 ${oc.length} 个服务但都不可用。${blocked.container_name}：${blocked.status_detail ?? '宿主访问不到'}`
            : `找到 ${oc.length} 个服务但都未在运行，请到「电脑 → 服务」页启动`,
        );
      } else {
        message.info('未发现任何容器内的 opencode 服务');
      }
    } catch (err) {
      message.error(err instanceof Error ? err.message : '扫描服务失败');
    } finally {
      setSourcesLoading(false);
    }
  };

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

  /** 当前选中的服务 id（按 容器+容器端口 反查，容器重建后 id 会变） */
  const selectedServiceId = useMemo(() => {
    if (!containerSource) return undefined;
    const hit = services.find(
      (x) =>
        x.container_id === containerSource.container_id &&
        x.container_port === containerSource.container_port,
    );
    return hit?.id;
  }, [containerSource, services]);

  /** 选了容器源时，就绪判定走容器源（不依赖本机 opencode status） */
  const ready = containerSource ? !!embedUrl : !!status?.healthy && !!embedUrl;

  /** 可直接用的容器服务 */
  const usableServices = useMemo(
    () => services.filter((s) => s.is_aide_source && s.host_port),
    [services],
  );
  /** 在跑、但宿主访问不到的服务 —— 未就绪时要精准告诉用户卡在哪 */
  const blockedServices = useMemo(
    () => services.filter((s) => s.status === 'running' && !s.host_reachable),
    [services],
  );

  const currentService = selectedServiceId
    ? services.find((x) => x.id === selectedServiceId)
    : undefined;

  const srcLabel = containerSource
    ? `容器 ${containerSource.container_name}`
    : status?.embed_source === 'serve'
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
        height: '100%',
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
          background: 'var(--bg-surface)',
          pointerEvents: 'auto',
        }}
      >
        <Space size={8} align="center">
          <CodeOutlined style={{ color: 'var(--accent, #0071e3)', fontSize: 14 }} />{/* 【UI 重构】Apple Blue */}
          <span
            style={{
              fontFamily: 'var(--font-sans)',
              fontSize: 14,
              fontWeight: 600,
              color: 'var(--text-primary)',
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
          {!containerSource && status?.version && (
            <Text style={{ fontSize: 11, color: 'var(--ink-40, #8f8b84)' }}>
              v{status.version}
            </Text>
          )}
          {currentService?.last_checked_at && (
            <Tooltip
              title={`状态探测于 ${new Date(currentService.last_checked_at).toLocaleString()}（DB 中的状态是探测快照，点右侧刷新可回探）`}
            >
              <Text style={{ fontSize: 11, color: 'var(--ink-40, #8f8b84)' }}>
                容器端口 {currentService.container_port}
              </Text>
            </Tooltip>
          )}
          {ready && !loaded && (
            <Space size={6}>
              <Spin size="small" />
              <Text style={{ fontSize: 11, color: 'var(--ink-40, #8f8b84)' }}>加载中…</Text>
            </Space>
          )}
        </Space>

        {/* ---- 容器服务源选择器（选项来自 MySQL container_services）---- */}
        <Space size={4} align="center">
          <ApiOutlined style={{ color: 'var(--ink-40, #8f8b84)', fontSize: 13 }} />
          <Select
            size="small"
            placeholder="选择容器 opencode 服务"
            style={{ width: 300 }}
            allowClear
            loading={sourcesLoading}
            value={selectedServiceId}
            onChange={(val) => {
              if (val == null) {
                setContainerSource(null);
                message.info('已切回本机 opencode');
                return;
              }
              void pickService(val as number);
            }}
            onOpenChange={(open) => {
              // 打开下拉时做一次「扫描发现 + 回探」，
              // 这样用户刚在容器里起的服务能立刻出现在列表里
              if (open) void fetchServices(false, true);
            }}
            optionLabelProp="label"
            options={services.map((svc) => ({
              value: svc.id,
              // 不可用的置灰但仍展示，让用户知道「为什么这个不能选」
              disabled: !svc.host_reachable || !svc.host_port,
              label: `${svc.container_name} :${svc.host_port ?? '—'}`,
              title: svc.status_detail ?? '',
            }))}
            optionRender={(opt) => {
              const svc = services.find((x) => x.id === opt.value);
              if (!svc) return opt.label;
              const ok = svc.host_reachable && !!svc.host_port;
              return (
                <div style={{ lineHeight: 1.5, padding: '2px 0' }}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      fontSize: 12.5,
                    }}
                  >
                    <span
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: '50%',
                        background: ok ? '#22c55e' : '#faad14',
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ fontWeight: 500 }}>{svc.container_name}</span>
                    <Tag style={{ fontSize: 10, margin: 0 }}>
                      {svc.kind === 'opencode_serve' ? 'serve' : 'web'}
                    </Tag>
                    {!ok && <WarningOutlined style={{ color: '#faad14', fontSize: 11 }} />}
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: 'var(--ink-40, #8f8b84)',
                      fontFamily: "'JetBrains Mono', monospace",
                    }}
                  >
                    {svc.access_url ?? '未映射到宿主端口'}
                  </div>
                  {!ok && svc.status_detail && (
                    <div style={{ fontSize: 10.5, color: '#a86e12', maxWidth: 320 }}>
                      {svc.status_detail}
                    </div>
                  )}
                </div>
              );
            }}
            notFoundContent={
              <div style={{ padding: 10, textAlign: 'center' }}>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  暂无已登记的 opencode 服务
                  <br />
                  到「电脑 → 服务」页启动或扫描发现
                </Typography.Text>
              </div>
            }
          />
          <Tooltip title="扫描容器并回探服务状态（会把刚在容器里手工起的 opencode 也发现出来）">
            <Button
              size="small"
              type="text"
              icon={<ReloadOutlined />}
              loading={sourcesLoading}
              onClick={() => void doRefreshServices()}
            />
          </Tooltip>
          {/* 即使当前用的是本机 opencode，也要让用户知道容器里还有可选服务 ——
              否则「我起了容器 opencode 但 AIDE 看不到」会一直困扰用户 */}
          {!containerSource && usableServices.length > 0 && (
            <Tooltip
              title={`容器里有 ${usableServices.length} 个可用的 opencode 服务，点开左侧下拉可切换`}
            >
              <Tag
                color="blue"
                style={{ fontSize: 10, margin: 0, cursor: 'default' }}
              >
                容器可选 {usableServices.length}
              </Tag>
            </Tooltip>
          )}
          {!containerSource && usableServices.length === 0 && blockedServices.length > 0 && (
            <Tooltip
              title={
                blockedServices
                  .map((x) => `${x.container_name}: ${x.status_detail ?? '宿主访问不到'}`)
                  .join('；')
              }
            >
              <Tag color="warning" style={{ fontSize: 10, margin: 0, cursor: 'default' }}>
                {blockedServices.length} 个容器服务不可用
              </Tag>
            </Tooltip>
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
          {/* 容器源模式下这些按钮针对的是本机 opencode，与当前嵌入源无关，故隐藏 */}
          {containerSource ? null : status?.embed_source === 'web' ? (
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
              icon={<CodeOutlined style={{ color: 'var(--accent, #0071e3)' }} />}
              title="opencode 未就绪"
              subTitle={
                <div style={{ textAlign: 'left', maxWidth: 620, margin: '0 auto' }}>
                  {/* 容器里已有可用服务 → 直接引导去选，不要让用户以为必须起本机 opencode */}
                  {usableServices.length > 0 && (
                    <Alert
                      type="success"
                      showIcon
                      style={{ marginBottom: 14, textAlign: 'left' }}
                      title={`检测到 ${usableServices.length} 个可用的容器 opencode 服务`}
                      description={
                        <div style={{ fontSize: 12 }}>
                          <p style={{ margin: '0 0 6px' }}>
                            用上方的「选择容器 opencode 服务」下拉即可直接接入，无需在本机再起一个。
                          </p>
                          {usableServices.map((s) => (
                            <Button
                              key={s.id}
                              size="small"
                              type="primary"
                              style={{ marginRight: 6, marginTop: 2 }}
                              onClick={() => void pickService(s.id)}
                            >
                              接入 {s.container_name} :{s.host_port}
                            </Button>
                          ))}
                        </div>
                      }
                    />
                  )}

                  {/* 容器里有服务在跑但宿主访问不到 → 说清原因与修法 */}
                  {usableServices.length === 0 && blockedServices.length > 0 && (
                    <Alert
                      type="warning"
                      showIcon
                      style={{ marginBottom: 14, textAlign: 'left' }}
                      title={`容器里有 ${blockedServices.length} 个 opencode 在运行，但浏览器访问不到`}
                      description={
                        <div style={{ fontSize: 12 }}>
                          {blockedServices.map((s) => (
                            <div key={s.id} style={{ marginBottom: 6 }}>
                              <Text code style={{ fontSize: 11 }}>
                                {s.container_name} · 容器内 {s.container_port}
                              </Text>
                              <div style={{ color: '#a86e12', marginTop: 2 }}>
                                {s.status_detail ??
                                  '该端口未映射到宿主，浏览器无法访问'}
                              </div>
                            </div>
                          ))}
                          <p style={{ margin: '6px 0 0', color: 'var(--ink-60, #605c56)' }}>
                            两种修法：① 到「电脑 → 容器」用「修改配置」把该容器端口映射到宿主；
                            ② 到「电脑 → 服务」用「启动服务」在<b>已映射的端口</b>上重起（会自动绑 0.0.0.0）。
                          </p>
                        </div>
                      }
                    />
                  )}

                  <p style={{ color: 'var(--ink-60, #605c56)', fontSize: 13 }}>
                    也可以让 AIDE 用<b>本机</b>的 opencode。两种方式任选其一：
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
                    重新探测本机
                  </Button>
                  <Button
                    icon={<ApiOutlined />}
                    loading={sourcesLoading}
                    onClick={() => void doRefreshServices()}
                  >
                    扫描容器服务
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

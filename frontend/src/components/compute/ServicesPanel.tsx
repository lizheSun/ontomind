/**
 * 容器服务面板 — 展示容器内启动的常驻服务（opencode web/serve）及其真实状态。
 *
 * 解决的问题：容器内用「快速命令」起的服务是一个运行态，
 * 进程只活在容器里，页面刷新/后端重启后就看不见了。
 * 现在这些服务落库到 container_services，这里集中展示 + 维护状态真实性。
 *
 * 状态真实性设计：
 * - 表格里的状态是**后端最近一次探测的快照**，每行都显示「探测于 X 前」
 * - 提供「刷新状态」主动回探；默认进入面板自动探一次
 * - 可选开启 15s 自动刷新（长期停留时保持实时）
 * - 后端探测分四步：容器在吗 → 端口映射对吗 → 容器内端口在听吗（绑什么地址）→ 宿主连得上吗
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  App,
  Button,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Tooltip,
  Typography,
} from 'antd';
import {
  ApiOutlined,
  CloudServerOutlined,
  DeleteOutlined,
  ExportOutlined,
  PlayCircleOutlined,
  PoweroffOutlined,
  ReloadOutlined,
  SearchOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { EmptyState } from '../common/EmptyState';
import useComputeStore, { extractErrMsg } from '../../stores/computeStore';
import type { ContainerInfo, ContainerServiceInfo } from '../../types/compute';
import { serviceKindLabel, serviceStatusLabel } from '../../types/compute';
import {
  deleteContainerService,
  discoverContainerServices,
  launchContainerService,
  listContainerServices,
  refreshContainerService,
  refreshContainerServices,
  stopContainerService,
} from '../../services/compute.service';
import { AddrFoot, FilterTabs, HostCard, StatusPill, timeAgo } from './computerUi';

const { Text } = Typography;

/** 探测超过 60s 视为「可能已过期」，提示用户刷新 */
function isStale(iso?: string | null): boolean {
  if (!iso) return true;
  const t = new Date(iso).getTime();
  return Number.isNaN(t) || Date.now() - t > 60_000;
}

export default function ServicesPanel() {
  const { notification } = App.useApp();
  const { selectedNode, containers, fetchContainers } = useComputeStore();

  const [services, setServices] = useState<ContainerServiceInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const timerRef = useRef<number | null>(null);

  // 启动服务弹窗
  const [launchOpen, setLaunchOpen] = useState(false);
  const [launchContainer, setLaunchContainer] = useState<string | undefined>();
  const [launchKind, setLaunchKind] = useState<'opencode_web' | 'opencode_serve' | 'dsh_web'>('opencode_web');
  const [launchPort, setLaunchPort] = useState<number>(4096);
  const [launching, setLaunching] = useState(false);

  const load = useCallback(
    async (opts?: { refresh?: boolean; silent?: boolean }) => {
      if (!opts?.silent) setLoading(true);
      try {
        const rows = await listContainerServices(undefined, opts?.refresh ?? false);
        setServices(rows);
      } catch (err) {
        if (!opts?.silent) {
          notification.error({ title: '获取服务列表失败', description: extractErrMsg(err) });
        }
      } finally {
        if (!opts?.silent) setLoading(false);
      }
    },
    [notification],
  );

  // 进入面板：先快速拿列表，再后台探一次真实状态
  useEffect(() => {
    void (async () => {
      await load();
      await load({ refresh: true, silent: true });
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 自动刷新（长期停留时保持状态实时）
  useEffect(() => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (!autoRefresh) return;
    timerRef.current = window.setInterval(() => {
      void load({ refresh: true, silent: true });
    }, 15_000);
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, [autoRefresh, load]);

  const doRefreshAll = async () => {
    setLoading(true);
    try {
      const r = await refreshContainerServices();
      setServices(r.services);
      notification.success({
        title: '状态已刷新',
        description: `共 ${r.total} 个服务：运行 ${r.running} · 停止 ${r.stopped} · 不可达 ${r.unreachable}`,
        duration: 3,
      });
    } catch (err) {
      notification.error({ title: '刷新失败', description: extractErrMsg(err) });
    } finally {
      setLoading(false);
    }
  };

  const doDiscover = async () => {
    setLoading(true);
    try {
      const before = services.length;
      const r = await discoverContainerServices();
      setServices(r.services);
      const added = r.total - before;
      notification.success({
        title: added > 0 ? `发现 ${added} 个新服务` : '未发现新服务',
        description: `当前共 ${r.total} 个：运行 ${r.running} · 停止 ${r.stopped} · 不可达 ${r.unreachable}`,
        duration: 4,
      });
    } catch (err) {
      notification.error({ title: '扫描失败', description: extractErrMsg(err) });
    } finally {
      setLoading(false);
    }
  };

  const rowAction = async (id: number, label: string, fn: () => Promise<unknown>) => {
    setBusyId(id);
    try {
      await fn();
      await load({ silent: true });
      notification.success({ title: `${label}成功`, duration: 2 });
    } catch (err) {
      notification.error({
        title: `${label}失败`,
        description: extractErrMsg(err),
        duration: 8,
      });
    } finally {
      setBusyId(null);
    }
  };

  const openLaunch = () => {
    if (containers.length === 0) void fetchContainers();
    const running = containers.filter((c) => c.status === 'running');
    setLaunchContainer(running[0]?.id);
    setLaunchKind('opencode_web');
    setLaunchPort(4096);
    setLaunchOpen(true);
  };

  const doLaunch = async () => {
    if (!selectedNode || !launchContainer) {
      notification.warning({ title: '请选择容器' });
      return;
    }
    setLaunching(true);
    try {
      const svc = await launchContainerService(selectedNode.id, launchContainer, {
        kind: launchKind,
        container_port: launchPort,
        cors: window.location.origin,
      });
      await load({ silent: true });
      setLaunchOpen(false);
      if (svc.host_reachable) {
        notification.success({
          title: '服务已启动',
          description: `${svc.name} · ${svc.access_url}（AIDE 现在可以选它了）`,
          duration: 5,
        });
      } else {
        notification.warning({
          title: '服务已启动，但宿主访问不到',
          description: svc.status_detail || '请检查容器端口映射',
          duration: 10,
        });
      }
    } catch (err) {
      notification.error({
        title: '启动失败',
        description: extractErrMsg(err),
        duration: 10,
      });
    } finally {
      setLaunching(false);
    }
  };

  const runningContainers = useMemo(
    () => containers.filter((c: ContainerInfo) => c.status === 'running'),
    [containers],
  );

  const stats = useMemo(() => {
    const running = services.filter((s) => s.status === 'running').length;
    const aide = services.filter((s) => s.is_aide_source).length;
    const problem = services.filter(
      (s) => s.status === 'running' && !s.host_reachable,
    ).length;
    return { total: services.length, running, aide, problem };
  }, [services]);

  const [filter, setFilter] = useState<'running' | 'stopped' | 'all'>('all');

  const visible = useMemo(() => {
    return services.filter((s) => {
      if (filter === 'running') return s.status === 'running';
      if (filter === 'stopped') return s.status !== 'running';
      return true;
    });
  }, [services, filter]);

  const pillTone = (s: ContainerServiceInfo): 'ok' | 'off' | 'warn' => {
    if (s.status === 'running' && !s.host_reachable) return 'warn';
    if (s.status === 'running') return 'ok';
    return 'off';
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
        <Space size={4}>
          <Switch size="small" checked={autoRefresh} onChange={setAutoRefresh} />
          <Text style={{ fontSize: 12 }}>15s 自动刷新</Text>
        </Space>
        <Tooltip title="扫描所有容器，把已在跑但未登记的服务补录进来">
          <Button icon={<SearchOutlined />} loading={loading} onClick={() => void doDiscover()}>
            扫描发现
          </Button>
        </Tooltip>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void doRefreshAll()}>
          刷新
        </Button>
        <Button type="primary" icon={<PlayCircleOutlined />} onClick={openLaunch} disabled={!selectedNode}>
          添加服务
        </Button>
      </div>

      <FilterTabs
        value={filter}
        onChange={(k) => setFilter(k as typeof filter)}
        items={[
          { key: 'running', label: '运行中', count: stats.running },
          { key: 'stopped', label: '已停止', count: stats.total - stats.running },
          { key: 'all', label: '全部', count: stats.total },
        ]}
      />

      {stats.problem > 0 && (
        <Alert
          type="warning"
          showIcon
          closable
          style={{ marginBottom: 12 }}
          title={`${stats.problem} 个服务在容器内运行，但宿主访问不到`}
          description="最常见原因：服务绑在 127.0.0.1（容器 loopback），Docker 端口映射对它无效。用「启动服务」重新拉起会自动绑 0.0.0.0。"
        />
      )}

      {visible.length === 0 ? (
        <EmptyState
          title="暂无服务"
          description="点「添加服务」在容器里拉起 OpenCode 或 DeepSeek Harness，或点「扫描发现」把已在跑的服务补录进来。"
          action={
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={openLaunch} disabled={!selectedNode}>
              添加服务
            </Button>
          }
        />
      ) : (
        <div className="om-host-list">
          {visible.map((r) => {
            const busy = busyId === r.id;
            const stale = isStale(r.last_checked_at);
            const port = r.host_port ? `${r.host_port} → ${r.container_port}` : `— → ${r.container_port}`;
            return (
              <HostCard
                key={r.id}
                glyph={<ApiOutlined />}
                title={
                  <span>
                    {r.name}
                    {r.is_aide_source ? (
                      <span className="om-chip" style={{ marginLeft: 8, background: 'var(--accent-tint)', color: 'var(--accent)' }}>
                        AIDE
                      </span>
                    ) : null}
                  </span>
                }
                subtitle={`${serviceKindLabel[r.kind]} · ${r.container_name}`}
                pill={
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                    {r.status === 'running' && !r.host_reachable && (
                      <Tooltip title={r.status_detail || '宿主访问不到'}>
                        <WarningOutlined style={{ color: 'var(--warning)' }} />
                      </Tooltip>
                    )}
                    <StatusPill tone={pillTone(r)} label={serviceStatusLabel[r.status]} />
                  </span>
                }
                foot={
                  <AddrFoot
                    addr={port}
                    tag={r.node_name}
                    when={`探测于 ${timeAgo(r.last_checked_at)}${stale ? ' · 可能已过期' : ''}`}
                  />
                }
                actions={
                  <Space size={2}>
                    <Tooltip title="重新探测">
                      <Button
                        size="small"
                        type="text"
                        loading={busy}
                        icon={<ReloadOutlined />}
                        onClick={() => void rowAction(r.id, '探测', () => refreshContainerService(r.id))}
                      />
                    </Tooltip>
                    <Tooltip title={r.access_url ? `打开 ${r.access_url}` : '无宿主访问地址'}>
                      <Button
                        size="small"
                        type="text"
                        icon={<ExportOutlined />}
                        disabled={!r.access_url || !r.host_reachable}
                        onClick={() => window.open(r.access_url!, '_blank', 'noopener')}
                      />
                    </Tooltip>
                    <Popconfirm
                      title={`停止 ${r.name}？`}
                      description="仅停止容器内进程，登记会保留"
                      onConfirm={() => void rowAction(r.id, '停止', () => stopContainerService(r.id))}
                    >
                      <Button
                        size="small"
                        type="text"
                        danger
                        loading={busy}
                        icon={<PoweroffOutlined />}
                        disabled={r.status !== 'running'}
                      />
                    </Popconfirm>
                    <Popconfirm
                      title="删除这条服务登记？"
                      description="只是从平台移除记录，容器里的进程不会被停止"
                      onConfirm={() => void rowAction(r.id, '删除登记', () => deleteContainerService(r.id))}
                    >
                      <Button size="small" type="text" danger loading={busy} icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </Space>
                }
              />
            );
          })}
        </div>
      )}

      {/* 启动服务弹窗 */}
      <Modal
        title="在容器内启动服务"
        open={launchOpen}
        onOk={() => void doLaunch()}
        onCancel={() => setLaunchOpen(false)}
        confirmLoading={launching}
        okText="启动并登记"
        width={560}
        destroyOnHidden
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          title="会自动绑定 0.0.0.0"
          description="容器内服务若绑 127.0.0.1，Docker 端口映射会失效、宿主访问不到。平台启动时强制 --hostname 0.0.0.0，规避这个坑。"
        />

        <div style={{ marginBottom: 14 }}>
          <Text strong style={{ fontSize: 13 }}>
            目标容器 <Text type="danger">*</Text>
          </Text>
          <Select
            size="small"
            style={{ width: '100%', marginTop: 4 }}
            placeholder="选择一个运行中的容器"
            value={launchContainer}
            onChange={setLaunchContainer}
            options={runningContainers.map((c) => ({
              value: c.id,
              label: `${c.name} · ${c.ports || '无端口映射'}`,
            }))}
            notFoundContent={
              <div style={{ padding: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  没有运行中的容器，请先到「容器」页启动一个
                </Text>
              </div>
            }
          />
        </div>

        <div style={{ marginBottom: 14 }}>
          <Text strong style={{ fontSize: 13 }}>
            服务类型
          </Text>
          <Select
            size="small"
            style={{ width: '100%', marginTop: 4 }}
            value={launchKind}
            onChange={(v) => {
              setLaunchKind(v);
              setLaunchPort(v === 'dsh_web' ? 3080 : 4096);
            }}
            options={[
              { value: 'opencode_web', label: 'opencode web — 仅前端 UI，适合 AIDE 嵌入' },
              { value: 'opencode_serve', label: 'opencode serve — 内置 UI + API（1.18+）' },
              { value: 'dsh_web', label: 'DeepSeek Harness web — 默认 3080，适合 AIDE 嵌入' },
            ]}
          />
        </div>

        <div style={{ marginBottom: 6 }}>
          <Text strong style={{ fontSize: 13 }}>
            容器内端口
          </Text>
          <Text type="secondary" style={{ fontSize: 11.5, marginLeft: 8, fontFamily: 'monospace' }}>
            例：{launchKind === 'dsh_web' ? '3080' : '4096'}
          </Text>
          <Select
            size="small"
            style={{ width: '100%', marginTop: 4 }}
            value={launchPort}
            onChange={setLaunchPort}
            options={(launchKind === 'dsh_web' ? [3080, 3081] : [4096, 4097]).map((p) => ({
              value: p,
              label: String(p),
            }))}
          />
          <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 4 }}>
            该端口需已映射到宿主，否则浏览器访问不到。可在「容器」页用「修改配置」加映射。
          </Text>
        </div>

        {launchContainer && (
          <div
            style={{
              marginTop: 14,
              background: '#1a1918',
              color: '#a6e3a1',
              padding: '10px 12px',
              borderRadius: 8,
              fontSize: 11.5,
              fontFamily: "'JetBrains Mono', monospace",
              wordBreak: 'break-all',
            }}
          >
            <Text style={{ color: '#666', fontSize: 11, display: 'block', marginBottom: 4 }}>
              等价命令
            </Text>
            {launchKind === 'dsh_web'
              ? `dsh web --host 0.0.0.0 --port ${launchPort} --no-open`
              : `opencode ${launchKind === 'opencode_web' ? 'web' : 'serve'} --port ${launchPort} --hostname 0.0.0.0 --cors ${window.location.origin}`}
          </div>
        )}
      </Modal>

      {!selectedNode && (
        <div style={{ marginTop: 12 }}>
          <Space size={6}>
            <CloudServerOutlined style={{ color: '#8c8c8c' }} />
            <Text type="secondary" style={{ fontSize: 12 }}>
              未选择节点，「添加服务」不可用。请先到「电脑」页选一台机器。
            </Text>
          </Space>
        </div>
      )}
    </div>
  );
}

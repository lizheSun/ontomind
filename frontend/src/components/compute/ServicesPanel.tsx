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
  Empty,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  CloudServerOutlined,
  DeleteOutlined,
  ExportOutlined,
  PlayCircleOutlined,
  PoweroffOutlined,
  ReloadOutlined,
  SearchOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import useComputeStore, { extractErrMsg } from '../../stores/computeStore';
import type { ContainerInfo, ContainerServiceInfo } from '../../types/compute';
import {
  serviceKindLabel,
  serviceStatusColor,
  serviceStatusLabel,
} from '../../types/compute';
import {
  deleteContainerService,
  discoverContainerServices,
  launchContainerService,
  listContainerServices,
  refreshContainerService,
  refreshContainerServices,
  stopContainerService,
} from '../../services/compute.service';

const { Text } = Typography;

/** 把时间戳渲染成「X 前」，让用户一眼看出状态新鲜度 */
function timeAgo(iso?: string | null): string {
  if (!iso) return '从未探测';
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return '—';
  const sec = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (sec < 10) return '刚刚';
  if (sec < 60) return `${sec} 秒前`;
  if (sec < 3600) return `${Math.floor(sec / 60)} 分钟前`;
  if (sec < 86400) return `${Math.floor(sec / 3600)} 小时前`;
  return `${Math.floor(sec / 86400)} 天前`;
}

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
  const [launchKind, setLaunchKind] = useState<'opencode_web' | 'opencode_serve'>('opencode_web');
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

  const columns: ColumnsType<ContainerServiceInfo> = [
    {
      title: '服务',
      key: 'name',
      width: 190,
      render: (_, r) => (
        <Space orientation="vertical" size={0}>
          <Space size={6}>
            <Text strong>{r.name}</Text>
            {r.is_aide_source && (
              <Tooltip title="AIDE 页面可以选择这个服务作为嵌入源">
                <Tag color="blue" style={{ fontSize: 10, margin: 0 }}>
                  AIDE
                </Tag>
              </Tooltip>
            )}
          </Space>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {serviceKindLabel[r.kind]}
          </Text>
        </Space>
      ),
    },
    {
      title: '所在容器',
      key: 'container',
      width: 180,
      render: (_, r) => (
        <Space orientation="vertical" size={0}>
          <Text style={{ fontSize: 12.5 }}>{r.container_name}</Text>
          <Text type="secondary" style={{ fontSize: 10.5 }}>
            {r.node_name} · {r.container_id.slice(0, 12)}
          </Text>
        </Space>
      ),
    },
    {
      title: '端口（宿主→容器）',
      key: 'port',
      width: 150,
      render: (_, r) => (
        <Space orientation="vertical" size={0}>
          <Text style={{ fontFamily: 'monospace', fontSize: 12 }}>
            {r.host_port ? `${r.host_port} → ${r.container_port}` : `— → ${r.container_port}`}
          </Text>
          {r.bind_address && (
            <Text
              type={r.bind_address === '127.0.0.1' ? 'danger' : 'secondary'}
              style={{ fontSize: 10.5, fontFamily: 'monospace' }}
            >
              bind {r.bind_address}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: '状态',
      key: 'status',
      width: 190,
      render: (_, r) => {
        const stale = isStale(r.last_checked_at);
        return (
          <Space orientation="vertical" size={2}>
            <Space size={6}>
              <Tag color={serviceStatusColor[r.status]} style={{ margin: 0 }}>
                {serviceStatusLabel[r.status]}
              </Tag>
              {r.status === 'running' && !r.host_reachable && (
                <Tooltip title={r.status_detail || '宿主访问不到'}>
                  <WarningOutlined style={{ color: '#faad14' }} />
                </Tooltip>
              )}
            </Space>
            <Tooltip title={r.last_checked_at ? new Date(r.last_checked_at).toLocaleString() : ''}>
              <Text
                type={stale ? 'warning' : 'secondary'}
                style={{ fontSize: 10.5 }}
              >
                探测于 {timeAgo(r.last_checked_at)}
                {stale && ' · 可能已过期'}
              </Text>
            </Tooltip>
          </Space>
        );
      },
    },
    {
      title: '说明',
      dataIndex: 'status_detail',
      ellipsis: true,
      render: (v: string | null) =>
        v ? (
          <Tooltip title={v} styles={{ root: { maxWidth: 420 } }}>
            <Text style={{ fontSize: 11.5, color: 'var(--ink-60, #605c56)' }}>{v}</Text>
          </Tooltip>
        ) : (
          <Text type="secondary" style={{ fontSize: 11.5 }}>
            —
          </Text>
        ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 170,
      fixed: 'right',
      render: (_, r) => {
        const busy = busyId === r.id;
        return (
          <Space size={2}>
            <Tooltip title="重新探测该服务状态">
              <Button
                size="small"
                type="text"
                loading={busy}
                icon={<ReloadOutlined />}
                onClick={() => rowAction(r.id, '探测', () => refreshContainerService(r.id))}
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
            <Tooltip title="停止容器内该服务进程">
              <Popconfirm
                title={`停止 ${r.name}？`}
                description="仅停止容器内进程，登记会保留，之后可再启动"
                onConfirm={() => rowAction(r.id, '停止', () => stopContainerService(r.id))}
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
            </Tooltip>
            <Tooltip title="删除登记（不影响容器内进程）">
              <Popconfirm
                title="删除这条服务登记？"
                description="只是从平台移除记录，容器里的进程不会被停止"
                onConfirm={() => rowAction(r.id, '删除登记', () => deleteContainerService(r.id))}
              >
                <Button size="small" type="text" danger loading={busy} icon={<DeleteOutlined />} />
              </Popconfirm>
            </Tooltip>
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      {/* 工具条 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 12,
          gap: 12,
          flexWrap: 'wrap',
        }}
      >
        <Space size={12} wrap>
          <Text style={{ fontSize: 12, color: 'var(--ink-60, #605c56)' }}>
            共 {stats.total} 个服务 · 运行中 {stats.running} · 可作 AIDE 源 {stats.aide}
            {stats.problem > 0 && (
              <Text type="warning" style={{ fontSize: 12 }}>
                {' '}
                · {stats.problem} 个宿主访问不到
              </Text>
            )}
          </Text>
        </Space>
        <Space size={8}>
          <Space size={4}>
            <Switch size="small" checked={autoRefresh} onChange={setAutoRefresh} />
            <Text style={{ fontSize: 12 }}>15s 自动刷新</Text>
          </Space>
          <Tooltip title="扫描所有容器，把已在跑但未登记的服务补录进来">
            <Button size="small" icon={<SearchOutlined />} loading={loading} onClick={doDiscover}>
              扫描发现
            </Button>
          </Tooltip>
          <Button size="small" icon={<ReloadOutlined />} loading={loading} onClick={doRefreshAll}>
            刷新状态
          </Button>
          <Button
            type="primary"
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={openLaunch}
            disabled={!selectedNode}
          >
            启动服务
          </Button>
        </Space>
      </div>

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

      <Table<ContainerServiceInfo>
        size="middle"
        rowKey="id"
        columns={columns}
        dataSource={services}
        loading={loading}
        pagination={false}
        scroll={{ x: 1080 }}
        locale={{
          emptyText: (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                <span>
                  暂无已登记的服务
                  <br />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    点「启动服务」在容器里拉起 opencode，或点「扫描发现」把已在跑的服务补录进来
                  </Text>
                </span>
              }
            />
          ),
        }}
      />

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
              setLaunchPort(v === 'opencode_web' ? 4096 : 4096);
            }}
            options={[
              { value: 'opencode_web', label: 'opencode web — 仅前端 UI，适合 AIDE 嵌入' },
              { value: 'opencode_serve', label: 'opencode serve — 内置 UI + API（1.18+）' },
            ]}
          />
        </div>

        <div style={{ marginBottom: 6 }}>
          <Text strong style={{ fontSize: 13 }}>
            容器内端口
          </Text>
          <Text type="secondary" style={{ fontSize: 11.5, marginLeft: 8, fontFamily: 'monospace' }}>
            例：4096
          </Text>
          <Select
            size="small"
            style={{ width: '100%', marginTop: 4 }}
            value={launchPort}
            onChange={setLaunchPort}
            options={[4096, 4097].map((p) => ({ value: p, label: String(p) }))}
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
            opencode {launchKind === 'opencode_web' ? 'web' : 'serve'} --port {launchPort}{' '}
            --hostname 0.0.0.0 --cors {window.location.origin}
          </div>
        )}
      </Modal>

      {!selectedNode && (
        <div style={{ marginTop: 12 }}>
          <Space size={6}>
            <CloudServerOutlined style={{ color: '#8c8c8c' }} />
            <Text type="secondary" style={{ fontSize: 12 }}>
              未选择节点，「启动服务」不可用。请先到「节点管理」选一个节点。
            </Text>
          </Space>
        </div>
      )}
    </div>
  );
}

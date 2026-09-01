/** 容器列表 — Yao 电脑卡片布局；新建/启停/终端逻辑不变。 */
import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  App,
  Button,
  Drawer,
  Input,
  Modal,
  Popconfirm,
  Space,
  Tooltip,
} from 'antd';
import {
  BoxPlotOutlined,
  CloudDownloadOutlined,
  CodeOutlined,
  DeleteOutlined,
  EditOutlined,
  FileTextOutlined,
  InfoCircleOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  SyncOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { EmptyState } from '../common/EmptyState';
import useComputeStore, { extractErrMsg } from '../../stores/computeStore';
import type { ContainerInfo, ImageInfo } from '../../types/compute';
import { containerStatusLabel } from '../../types/compute';
import { getContainerLogs, inspectContainer } from '../../services/compute.service';
import ContainerConsole from './ContainerConsole';
import ContainerFormModal from './ContainerFormModal';
import ContainerExecModal from './ContainerExecModal';
import { AddrFoot, FilterTabs, HostCard, StatusPill } from './computerUi';

const LOG_BOX: React.CSSProperties = {
  background: 'var(--bg-subtle)',
  color: 'var(--text-primary)',
  padding: 16,
  borderRadius: 8,
  minHeight: 300,
  maxHeight: 500,
  overflow: 'auto',
  fontSize: 12,
  fontFamily: 'var(--font-mono)',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-all',
  margin: 0,
};

export default function DockerManagement() {
  const { notification } = App.useApp();
  const {
    selectedNode,
    nodes,
    selectNode,
    ensureLocalNode,
    fetchNodes,
    images,
    imagesLoading,
    containers,
    containersLoading,
    dockerError,
    fetchImages,
    fetchContainers,
    startContainer,
    stopContainer,
    restartContainer,
    removeContainer,
    pullImage,
  } = useComputeStore();

  const [consoleDrawerOpen, setConsoleDrawerOpen] = useState(false);
  const [consoleTarget, setConsoleTarget] = useState<{
    nodeId: number;
    containerId: string;
    containerName: string;
  } | null>(null);

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<ContainerInfo | null>(null);
  const [prefillImage, setPrefillImage] = useState<string | undefined>();
  const [execTarget, setExecTarget] = useState<ContainerInfo | null>(null);

  const [logsOpen, setLogsOpen] = useState(false);
  const [logsContent, setLogsContent] = useState('');
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsName, setLogsName] = useState('');

  const [inspectOpen, setInspectOpen] = useState(false);
  const [inspectData, setInspectData] = useState<Record<string, unknown>>({});

  const [pullImageName, setPullImageName] = useState('');
  const [pulling, setPulling] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const [pane, setPane] = useState<'containers' | 'images'>('containers');
  const [filter, setFilter] = useState<'running' | 'stopped' | 'all'>('all');
  const [q, setQ] = useState('');

  useEffect(() => {
    void (async () => {
      await ensureLocalNode();
      await fetchNodes();
      const store = useComputeStore.getState();
      if (!store.selectedNode && store.nodes[0]) selectNode(store.nodes[0]);
    })();
  }, [ensureLocalNode, fetchNodes, selectNode]);

  useEffect(() => {
    if (selectedNode) {
      void fetchContainers();
      void fetchImages();
    }
  }, [selectedNode?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const runAction = async (id: string, label: string, fn: () => Promise<void>) => {
    setBusyId(id);
    try {
      await fn();
      notification.success({ title: `${label}成功`, duration: 2 });
    } catch (err) {
      notification.error({ title: `${label}失败`, description: extractErrMsg(err), duration: 8 });
    } finally {
      setBusyId(null);
    }
  };

  const handleLogs = async (record: ContainerInfo) => {
    if (!selectedNode) return;
    setLogsName(record.name);
    setLogsOpen(true);
    setLogsLoading(true);
    try {
      const data = await getContainerLogs(selectedNode.id, record.id, 500);
      setLogsContent(data.logs || '(无日志输出)');
    } catch (err) {
      setLogsContent(`获取日志失败：${extractErrMsg(err)}`);
    } finally {
      setLogsLoading(false);
    }
  };

  const handleInspect = async (record: ContainerInfo) => {
    if (!selectedNode) return;
    try {
      const data = await inspectContainer(selectedNode.id, record.id);
      setInspectData(data.data);
      setInspectOpen(true);
    } catch (err) {
      notification.error({ title: '获取详情失败', description: extractErrMsg(err) });
    }
  };

  const handlePull = async () => {
    const img = pullImageName.trim();
    if (!img) {
      notification.warning({ title: '请输入镜像名', description: '例如 nginx:1.27-alpine' });
      return;
    }
    setPulling(true);
    try {
      await pullImage(img);
      notification.success({ title: `${img} 拉取成功` });
      setPullImageName('');
    } catch (err) {
      notification.error({ title: '拉取失败', description: extractErrMsg(err), duration: 10 });
    } finally {
      setPulling(false);
    }
  };

  const openConsole = (record: ContainerInfo) => {
    if (!selectedNode) return;
    setConsoleTarget({
      nodeId: selectedNode.id,
      containerId: record.id,
      containerName: record.name,
    });
    setConsoleDrawerOpen(true);
  };

  const runningN = containers.filter((c) => c.status === 'running').length;
  const stoppedN = containers.length - runningN;

  const visible = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return containers.filter((c) => {
      if (filter === 'running' && c.status !== 'running') return false;
      if (filter === 'stopped' && c.status === 'running') return false;
      if (!needle) return true;
      return `${c.name} ${c.image} ${c.id}`.toLowerCase().includes(needle);
    });
  }, [containers, filter, q]);

  const visibleImages = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return images;
    return images.filter((img) => img.tags.join(' ').toLowerCase().includes(needle) || img.id.includes(needle));
  }, [images, q]);

  if (!selectedNode && nodes.length === 0) {
    return <EmptyState title="暂无电脑" description="请先在「电脑」页添加或导入节点。" />;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginBottom: 8 }}>
        <Button
          icon={<ReloadOutlined />}
          loading={containersLoading || imagesLoading}
          onClick={() => {
            void fetchContainers();
            void fetchImages();
          }}
        >
          刷新
        </Button>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            setEditing(null);
            setPrefillImage(undefined);
            setFormOpen(true);
          }}
        >
          新建容器
        </Button>
      </div>

      <FilterTabs
        value={pane}
        onChange={(k) => setPane(k as typeof pane)}
        items={[
          { key: 'containers', label: '容器', count: containers.length },
          { key: 'images', label: '镜像', count: images.length },
        ]}
      />

      {dockerError && (
        <Alert
          type="error"
          showIcon
          closable
          style={{ marginBottom: 12 }}
          title="Docker 数据获取失败"
          description={dockerError}
        />
      )}

      <Input
        className="om-comp-search"
        placeholder="搜索电脑名称、镜像、标签…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        allowClear
        size="large"
      />

      {pane === 'containers' ? (
        <>
          <FilterTabs
            value={filter}
            onChange={(k) => setFilter(k as typeof filter)}
            items={[
              { key: 'running', label: '运行中', count: runningN },
              { key: 'stopped', label: '已停止', count: stoppedN },
              { key: 'all', label: '全部', count: containers.length },
            ]}
          />
          {visible.length === 0 ? (
            <EmptyState
              title="暂无容器"
              description="点右上角「新建容器」，可从预设一键创建。"
              action={
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => {
                    setEditing(null);
                    setFormOpen(true);
                  }}
                >
                  新建容器
                </Button>
              }
            />
          ) : (
            <div className="om-host-list">
              {visible.map((c) => {
                const on = c.status === 'running';
                const busy = busyId === c.id;
                return (
                  <HostCard
                    key={c.id}
                    glyph={<BoxPlotOutlined />}
                    title={c.name}
                    subtitle={c.image}
                    pill={
                      <StatusPill
                        tone={on ? 'ok' : 'off'}
                        label={containerStatusLabel[c.status] || c.status}
                      />
                    }
                    foot={<AddrFoot addr={c.ports || '无端口'} tag={c.network || 'bridge'} when={c.id.slice(0, 12)} />}
                    actions={
                      <Space size={2}>
                        {on ? (
                          <Tooltip title="停止">
                            <Button
                              size="small"
                              type="text"
                              loading={busy}
                              icon={<PauseCircleOutlined />}
                              onClick={() => void runAction(c.id, '停止', () => stopContainer(c.id))}
                            />
                          </Tooltip>
                        ) : (
                          <Tooltip title="启动">
                            <Button
                              size="small"
                              type="text"
                              loading={busy}
                              icon={<PlayCircleOutlined />}
                              onClick={() => void runAction(c.id, '启动', () => startContainer(c.id))}
                            />
                          </Tooltip>
                        )}
                        <Tooltip title="重启">
                          <Button
                            size="small"
                            type="text"
                            loading={busy}
                            icon={<SyncOutlined />}
                            onClick={() => void runAction(c.id, '重启', () => restartContainer(c.id))}
                          />
                        </Tooltip>
                        <Tooltip title="修改配置（会重建容器）">
                          <Button
                            size="small"
                            type="text"
                            icon={<EditOutlined />}
                            onClick={() => {
                              setEditing(c);
                              setFormOpen(true);
                            }}
                          />
                        </Tooltip>
                        <Tooltip title={on ? '打开交互终端' : '需先启动容器'}>
                          <Button
                            size="small"
                            type="text"
                            disabled={!on}
                            icon={<CodeOutlined />}
                            onClick={() => openConsole(c)}
                          />
                        </Tooltip>
                        <Tooltip title={on ? '执行命令' : '需先启动容器'}>
                          <Button
                            size="small"
                            type="text"
                            disabled={!on}
                            icon={<ThunderboltOutlined />}
                            onClick={() => setExecTarget(c)}
                          />
                        </Tooltip>
                        <Tooltip title="查看日志">
                          <Button
                            size="small"
                            type="text"
                            icon={<FileTextOutlined />}
                            onClick={() => void handleLogs(c)}
                          />
                        </Tooltip>
                        <Tooltip title="inspect">
                          <Button
                            size="small"
                            type="text"
                            icon={<InfoCircleOutlined />}
                            onClick={() => void handleInspect(c)}
                          />
                        </Tooltip>
                        <Popconfirm
                          title={`删除容器 ${c.name}？`}
                          description={on ? '容器正在运行，将强制删除' : undefined}
                          onConfirm={() => void runAction(c.id, '删除', () => removeContainer(c.id, true))}
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
        </>
      ) : (
        <>
          <Space.Compact style={{ marginBottom: 14, width: '100%', maxWidth: 520 }}>
            <Input
              placeholder="输入镜像名拉取，例如 nginx:1.27-alpine"
              value={pullImageName}
              onChange={(e) => setPullImageName(e.target.value)}
              onPressEnter={() => void handlePull()}
              style={{ fontFamily: 'var(--font-mono)' }}
            />
            <Button type="primary" icon={<CloudDownloadOutlined />} loading={pulling} onClick={() => void handlePull()}>
              拉取
            </Button>
          </Space.Compact>
          {visibleImages.length === 0 ? (
            <EmptyState title="暂无镜像" description="在上方输入镜像名拉取。" />
          ) : (
            <div className="om-host-list">
              {visibleImages.map((img: ImageInfo) => {
                const tag = img.tags.find((t) => t && !t.startsWith('<none>')) || img.tags[0] || img.id.slice(0, 12);
                return (
                  <HostCard
                    key={img.id}
                    title={tag}
                    subtitle={`${img.size} · ${img.id.slice(0, 12)}`}
                    pill={<StatusPill tone="off" label="镜像" />}
                    foot={<AddrFoot addr={img.created} tag={img.tags.length > 1 ? `${img.tags.length} tags` : undefined} />}
                    actions={
                      <Button
                        size="small"
                        type="link"
                        disabled={!img.tags.find((t) => t && !t.startsWith('<none>'))}
                        onClick={() => {
                          setEditing(null);
                          setPrefillImage(tag);
                          setFormOpen(true);
                        }}
                      >
                        用它建容器
                      </Button>
                    }
                  />
                );
              })}
            </div>
          )}
        </>
      )}

      <ContainerFormModal
        open={formOpen}
        editing={editing}
        prefillImage={prefillImage}
        onClose={() => {
          setFormOpen(false);
          setEditing(null);
          setPrefillImage(undefined);
        }}
      />
      <ContainerExecModal open={!!execTarget} container={execTarget} onClose={() => setExecTarget(null)} />
      <Modal
        title={`容器日志 · ${logsName}`}
        open={logsOpen}
        onCancel={() => setLogsOpen(false)}
        footer={null}
        width={860}
        destroyOnHidden
      >
        <pre style={LOG_BOX}>{logsLoading ? '加载中…' : logsContent}</pre>
      </Modal>
      <Modal
        title="容器完整详情"
        open={inspectOpen}
        onCancel={() => setInspectOpen(false)}
        footer={null}
        width={760}
        destroyOnHidden
      >
        <pre style={{ ...LOG_BOX, background: 'var(--bg-subtle)' }}>{JSON.stringify(inspectData, null, 2)}</pre>
      </Modal>
      <Drawer
        title={null}
        open={consoleDrawerOpen}
        onClose={() => setConsoleDrawerOpen(false)}
        width="50vw"
        styles={{ body: { padding: 0 }, wrapper: { minWidth: 480 } }}
        destroyOnHidden
      >
        {consoleTarget && (
          <ContainerConsole
            nodeId={consoleTarget.nodeId}
            containerId={consoleTarget.containerId}
            containerName={consoleTarget.containerName}
            onClose={() => setConsoleDrawerOpen(false)}
          />
        )}
      </Drawer>
    </div>
  );
}

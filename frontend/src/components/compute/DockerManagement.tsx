/** Docker 管理组件 — 容器列表 + 镜像列表 + 新建/修改/启停/命令/日志 */
import { useEffect, useState } from 'react';
import {
  Alert,
  App,
  Button,
  Drawer,
  Empty,
  Input,
  Modal,
  Popconfirm,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  BoxPlotOutlined,
  CloudDownloadOutlined,
  CloudServerOutlined,
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
import type { ColumnsType } from 'antd/es/table';
import useComputeStore, { extractErrMsg } from '../../stores/computeStore';
import type { ContainerInfo, ImageInfo } from '../../types/compute';
import { containerStatusColor, containerStatusLabel } from '../../types/compute';
import { getContainerLogs, inspectContainer } from '../../services/compute.service';
import ContainerConsole from './ContainerConsole';
import ContainerFormModal from './ContainerFormModal';
import ContainerExecModal from './ContainerExecModal';

const { Text } = Typography;

const LOG_BOX: React.CSSProperties = {
  background: '#1a1918',
  color: '#e0e0e0',
  padding: 16,
  borderRadius: 8,
  minHeight: 300,
  maxHeight: 500,
  overflow: 'auto',
  fontSize: 12,
  fontFamily: "'JetBrains Mono', monospace",
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-all',
  margin: 0,
};

export default function DockerManagement() {
  const { notification } = App.useApp();
  const {
    selectedNode,
    images,
    imagesLoading,
    containers,
    containersLoading,
    showAllContainers,
    dockerError,
    fetchImages,
    fetchContainers,
    toggleShowAll,
    startContainer,
    stopContainer,
    restartContainer,
    removeContainer,
    pullImage,
  } = useComputeStore();

  // 右侧半屏交互终端 Drawer
  const [consoleDrawerOpen, setConsoleDrawerOpen] = useState(false);
  const [consoleTarget, setConsoleTarget] = useState<{
    nodeId: number;
    containerId: string;
    containerName: string;
  } | null>(null);

  // 弹窗
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

  // 行级 loading，避免整表 loading 造成「点了没反应」的错觉
  const [busyId, setBusyId] = useState<string | null>(null);

  // 进入组件即拉取（节点已选中但数据未加载的情况）
  useEffect(() => {
    if (selectedNode && containers.length === 0 && !containersLoading) {
      void fetchContainers();
      void fetchImages();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedNode?.id]);

  /** 包裹容器操作：统一 loading + 错误提示（原来错误被 store 静默吞掉） */
  const runAction = async (
    id: string,
    label: string,
    fn: () => Promise<void>,
  ) => {
    setBusyId(id);
    try {
      await fn();
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
      notification.error({
        title: '拉取失败',
        description: extractErrMsg(err),
        duration: 10,
      });
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

  // ---- 表格列 ----

  const containerColumns: ColumnsType<ContainerInfo> = [
    {
      title: '名称',
      dataIndex: 'name',
      width: 170,
      render: (name: string, r) => (
        <Space orientation="vertical" size={0}>
          <Text strong>{name}</Text>
          <Text code style={{ fontSize: 10.5 }}>
            {r.id.slice(0, 12)}
          </Text>
        </Space>
      ),
    },
    { title: '镜像', dataIndex: 'image', width: 200, ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: string, r) => (
        <Space orientation="vertical" size={0}>
          <Tag color={containerStatusColor[status] || 'default'}>
            {containerStatusLabel[status] || status}
          </Tag>
          {status !== 'running' && r.exit_code != null && r.exit_code !== 0 && (
            <Text type="danger" style={{ fontSize: 10.5 }}>
              exit {r.exit_code}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: '端口（宿主→容器）',
      dataIndex: 'ports',
      width: 160,
      render: (ports: string) =>
        ports ? (
          <Text style={{ fontSize: 11.5, fontFamily: 'monospace' }}>{ports}</Text>
        ) : (
          <Text type="secondary" style={{ fontSize: 11.5 }}>
            无
          </Text>
        ),
    },
    {
      title: '挂载',
      dataIndex: 'volume_mappings',
      width: 150,
      render: (vols: ContainerInfo['volume_mappings']) =>
        vols && vols.length > 0 ? (
          <Tooltip
            title={vols
              .map((v) => `${v.host_path} → ${v.container_path}${v.read_only ? ' (ro)' : ''}`)
              .join('\n')}
          >
            <Text style={{ fontSize: 11.5, cursor: 'default' }}>{vols.length} 个挂载</Text>
          </Tooltip>
        ) : (
          <Text type="secondary" style={{ fontSize: 11.5 }}>
            无
          </Text>
        ),
    },
    {
      title: '网络',
      dataIndex: 'network',
      width: 84,
      render: (n: string) => <Tag style={{ fontSize: 10.5 }}>{n || 'bridge'}</Tag>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 300,
      fixed: 'right',
      render: (_, record) => {
        const isRunning = record.status === 'running';
        const busy = busyId === record.id;
        return (
          <Space size={2}>
            {isRunning ? (
              <Tooltip title="停止">
                <Button
                  size="small"
                  type="text"
                  loading={busy}
                  icon={<PauseCircleOutlined />}
                  onClick={() => runAction(record.id, '停止', () => stopContainer(record.id))}
                />
              </Tooltip>
            ) : (
              <Tooltip title="启动">
                <Button
                  size="small"
                  type="text"
                  loading={busy}
                  icon={<PlayCircleOutlined />}
                  onClick={() => runAction(record.id, '启动', () => startContainer(record.id))}
                />
              </Tooltip>
            )}
            <Tooltip title="重启">
              <Button
                size="small"
                type="text"
                loading={busy}
                icon={<SyncOutlined />}
                onClick={() => runAction(record.id, '重启', () => restartContainer(record.id))}
              />
            </Tooltip>
            <Tooltip title="修改端口 / 挂载 / 环境变量（会重建容器）">
              <Button
                size="small"
                type="text"
                icon={<EditOutlined />}
                onClick={() => {
                  setEditing(record);
                  setFormOpen(true);
                }}
              />
            </Tooltip>
            <Tooltip title={isRunning ? '打开交互终端' : '需先启动容器'}>
              <Button
                size="small"
                type="text"
                disabled={!isRunning}
                icon={<CodeOutlined />}
                onClick={() => openConsole(record)}
              />
            </Tooltip>
            <Tooltip title={isRunning ? '执行命令' : '需先启动容器'}>
              <Button
                size="small"
                type="text"
                disabled={!isRunning}
                icon={<ThunderboltOutlined />}
                onClick={() => setExecTarget(record)}
              />
            </Tooltip>
            <Tooltip title="查看日志">
              <Button
                size="small"
                type="text"
                icon={<FileTextOutlined />}
                onClick={() => void handleLogs(record)}
              />
            </Tooltip>
            <Tooltip title="完整详情 (inspect)">
              <Button
                size="small"
                type="text"
                icon={<InfoCircleOutlined />}
                onClick={() => void handleInspect(record)}
              />
            </Tooltip>
            <Popconfirm
              title={`删除容器 ${record.name}？`}
              description={isRunning ? '容器正在运行，将强制删除' : undefined}
              onConfirm={() => runAction(record.id, '删除', () => removeContainer(record.id, true))}
            >
              <Button size="small" type="text" danger loading={busy} icon={<DeleteOutlined />} />
            </Popconfirm>
          </Space>
        );
      },
    },
  ];

  const imageColumns: ColumnsType<ImageInfo> = [
    {
      title: '标签',
      dataIndex: 'tags',
      render: (tags: string[]) => (
        <Space size={4} wrap>
          {tags.map((t) => (
            <Tag key={t} style={{ fontFamily: 'monospace', fontSize: 11.5 }}>
              {t}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: 'ID',
      dataIndex: 'id',
      width: 130,
      render: (id: string) => <Text code style={{ fontSize: 11 }}>{id.slice(0, 12)}</Text>,
    },
    { title: '大小', dataIndex: 'size', width: 100 },
    { title: '创建时间', dataIndex: 'created', width: 170 },
    {
      title: '操作',
      key: 'act',
      width: 110,
      render: (_, img) => {
        const tag = img.tags.find((t) => t && !t.startsWith('<none>'));
        return (
          <Button
            size="small"
            type="link"
            disabled={!tag}
            onClick={() => {
              setEditing(null);
              setPrefillImage(tag!);
              setFormOpen(true);
            }}
          >
            用它建容器
          </Button>
        );
      },
    },
  ];

  if (!selectedNode) {
    return (
      <Empty
        description="请先在「节点管理」中选择一个节点"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  return (
    <div>
      {/* 节点信息条 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 14,
          padding: '10px 14px',
          background: 'rgba(0,113,227,0.04)',
          borderRadius: 12,
          border: '1px solid rgba(0,113,227,0.10)',
        }}
      >
        <Space>
          <CloudServerOutlined style={{ color: '#0071e3' }} />{/* 【UI 重构】Apple Blue */}
          <Text>
            当前节点：<Text strong>{selectedNode.name}</Text>
            <Text type="secondary" style={{ marginLeft: 8 }}>
              ({selectedNode.host}:{selectedNode.port})
            </Text>
          </Text>
        </Space>
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

      <Tabs
        defaultActiveKey="containers"
        tabBarExtraContent={
          <Space>
            <Switch checked={showAllContainers} onChange={toggleShowAll} size="small" />
            <Text style={{ fontSize: 12 }}>含已停止</Text>
            <Button
              size="small"
              icon={<ReloadOutlined />}
              loading={containersLoading || imagesLoading}
              onClick={() => {
                void fetchContainers();
                void fetchImages();
              }}
            >
              刷新
            </Button>
          </Space>
        }
        items={[
          {
            key: 'containers',
            label: (
              <Space size={4}>
                <BoxPlotOutlined />
                容器
                <Tag>{containers.length}</Tag>
              </Space>
            ),
            children: (
              <Table
                size="middle"
                rowKey="id"
                columns={containerColumns}
                dataSource={containers}
                loading={containersLoading}
                pagination={false}
                scroll={{ x: 1180 }}
                locale={{
                  emptyText: (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description={
                        <span>
                          该节点暂无容器
                          <br />
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            点右上角「新建容器」，可从预设一键创建
                          </Text>
                        </span>
                      }
                    />
                  ),
                }}
              />
            ),
          },
          {
            key: 'images',
            label: (
              <Space size={4}>
                <CloudServerOutlined />
                镜像
                <Tag>{images.length}</Tag>
              </Space>
            ),
            children: (
              <div>
                <Space.Compact style={{ marginBottom: 12, width: '100%', maxWidth: 460 }}>
                  <Input
                    size="small"
                    placeholder="输入镜像名拉取，例如 nginx:1.27-alpine"
                    value={pullImageName}
                    onChange={(e) => setPullImageName(e.target.value)}
                    onPressEnter={() => void handlePull()}
                    style={{ fontFamily: 'monospace' }}
                  />
                  <Button
                    size="small"
                    type="primary"
                    icon={<CloudDownloadOutlined />}
                    loading={pulling}
                    onClick={() => void handlePull()}
                  >
                    拉取
                  </Button>
                </Space.Compact>
                <Table
                  size="middle"
                  rowKey="id"
                  columns={imageColumns}
                  dataSource={images}
                  loading={imagesLoading}
                  pagination={false}
                  locale={{ emptyText: '暂无镜像，可在上方输入镜像名拉取' }}
                />
              </div>
            ),
          },
        ]}
      />

      {/* 新建 / 修改容器 */}
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

      {/* 快速命令 */}
      <ContainerExecModal
        open={!!execTarget}
        container={execTarget}
        onClose={() => setExecTarget(null)}
      />

      {/* 日志 */}
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

      {/* Inspect */}
      <Modal
        title="容器完整详情"
        open={inspectOpen}
        onCancel={() => setInspectOpen(false)}
        footer={null}
        width={760}
        destroyOnHidden
      >
        <pre
          style={{
            background: '#fafaf7',
            padding: 16,
            borderRadius: 8,
            maxHeight: 520,
            overflow: 'auto',
            fontSize: 11.5,
            fontFamily: "'JetBrains Mono', monospace",
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
            margin: 0,
          }}
        >
          {JSON.stringify(inspectData, null, 2)}
        </pre>
      </Modal>

      {/* 右侧半屏交互终端 */}
      <Drawer
        title={null}
        open={consoleDrawerOpen}
        onClose={() => setConsoleDrawerOpen(false)}
        width="50vw"
        styles={{
          body: { padding: 0 },
          wrapper: { minWidth: 480 },
        }}
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

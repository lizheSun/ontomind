/**
 * ResourcesPanel — Docker 服务.
 * 上层：算力节点卡片（本地 / SSH / Docker API 挂载）
 * 下层：选中节点的容器列表（启停 / 删除 / 日志 / 镜像搜索一键创建）
 */
import { useCallback, useEffect, useState } from 'react';
import {
  App, Alert, Button, Empty, Form, Input, Modal, Popconfirm,
  Radio, Select, Space, Spin, Table, Tag, Tooltip, Typography,
} from 'antd';
import {
  ApiOutlined, CloudServerOutlined, CloudDownloadOutlined, CodeOutlined,
  ConsoleSqlOutlined, DeleteOutlined, EditOutlined,
  FileTextOutlined, InboxOutlined, PlayCircleOutlined, PlusOutlined,
  PoweroffOutlined, ReloadOutlined, RocketOutlined, SaveOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import LogViewer from './LogViewer';
import TemplatesPanel from './TemplatesPanel';
import TerminalDrawer from './TerminalDrawer';
import ExecCommandModal from './ExecCommandModal';
import ContainerConfigFields, {
  emptyConfig, parseEnvs, parsePorts, parsePortsFromContainer, parseVolumes,
  parseVolumesFromContainer, serializeEnvs, serializePorts, serializeVolumes,
  type ContainerConfig,
} from './ContainerConfigFields';
import { fmtDateTime } from './mock';
import type {
  ComputeNode, ConnType, ContainerInstance, ContainerTemplate,
  HubImage, ImageListItem, LogLine,
} from './types';
import * as srv from '../../services/compute.service';

const { Text } = Typography;

const CONN_LABEL: Record<ConnType, string> = {
  local: '本机',
  ssh: 'SSH',
  'docker-api': 'Docker API',
};

const CONTAINER_STATUS: Record<ContainerInstance['status'], { color: string; dot: string; label: string }> = {
  running:    { color: '#476a4b', dot: '#22c55e', label: '运行中' },
  exited:     { color: '#8f8b84', dot: '#bfbcb5', label: '已退出' },
  created:    { color: '#a86e12', dot: '#eab308', label: '已创建' },
  restarting: { color: '#a86e12', dot: '#eab308', label: '重启中' },
  paused:     { color: '#8f8b84', dot: '#bfbcb5', label: '已暂停' },
  unknown:    { color: '#8f8b84', dot: '#bfbcb5', label: '未知' },
};

const SSH_HINT = '后端要求：对目标节点具备免密 SSH 能力（建议专用密钥对）。原理：后端经 docker CLI 的 SSH 通道（DOCKER_HOST=ssh://）执行远程容器管理，目标节点零额外配置，能 SSH 登录即可。';
const API_HINT = '后端要求：目标节点 dockerd 需开启远程 API。生产务必使用 TLS（2376 + 证书），切勿暴露未加密的 2375。原理：后端通过 Docker SDK 直连该节点 Daemon API。';

interface NodeFormValues {
  name: string;
  address: string;
  connType: Exclude<ConnType, 'local'>;
  sshPort?: number;
  sshUser?: string;
  tlsCerts?: string;
  remark?: string;
}

interface CreateFormValues {
  name: string;
  commandText?: string;
  templateId?: number;
}

export default function ResourcesPanel() {
  const { message } = App.useApp();
  const [nodes, setNodes] = useState<ComputeNode[]>([]);
  const [containers, setContainers] = useState<ContainerInstance[]>([]);
  const [selectedNode, setSelectedNode] = useState<number | null>(null);

  const [loadingNodes, setLoadingNodes] = useState(false);
  const [loadingContainers, setLoadingContainers] = useState(false);
  const [nodeModalOpen, setNodeModalOpen] = useState(false);
  const [testingNode, setTestingNode] = useState<number | null>(null);
  const [operatingCid, setOperatingCid] = useState<string | null>(null);
  const [mountingLocal, setMountingLocal] = useState(false);
  // 镜像管理
  const [detailTab, setDetailTab] = useState<'containers' | 'images' | 'templates'>('containers');
  const [images, setImages] = useState<ImageListItem[]>([]);
  const [loadingImages, setLoadingImages] = useState(false);
  const [pullingImage, setPullingImage] = useState('');
  // 创建容器表单
  const [containerConfig, setContainerConfig] = useState<ContainerConfig>(emptyConfig);
  const [commandText, setCommandText] = useState('');
  // 模板
  const [templates, setTemplates] = useState<ContainerTemplate[]>([]);

  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<HubImage[]>([]);
  const [searching, setSearching] = useState(false);
  const [usedBackendError, setUsedBackendError] = useState(false);

  const [createFor, setCreateFor] = useState<{
    image: string;
    /** 若存在则本次创建为「重新配置」，会先停止并删除该容器 */
    replacing?: ContainerInstance;
  } | null>(null);
  const [logsModal, setLogsModal] = useState<{ name: string; lines: LogLine[] } | null>(null);
  const [loadingLogs, setLoadingLogs] = useState(false);
  // 终端 / 执行命令
  const [terminalFor, setTerminalFor] = useState<ContainerInstance | null>(null);
  const [execFor, setExecFor] = useState<ContainerInstance | null>(null);

  const [nodeForm] = Form.useForm<NodeFormValues>();
  const [createForm] = Form.useForm<CreateFormValues>();
  const watchConn = Form.useWatch('connType', nodeForm) ?? 'ssh';
  const watchCreateName = Form.useWatch('name', createForm);

  const selectedNodeObj = nodes.find((n) => n.id === selectedNode);
  const nodeContainers = containers.filter((c) => c.nodeId === selectedNode);
  const runningCount = containers.filter((c) => c.status === 'running').length;

  // ===== 数据获取 =====

  const loadNodes = useCallback(async () => {
    setLoadingNodes(true);
    try {
      const list = await srv.fetchNodes();
      setNodes(list);
      if (!selectedNode && list.length > 0) setSelectedNode(list[0].id);
      if (list.length > 0) {
        const activeId = selectedNode && list.find((n) => n.id === selectedNode) ? selectedNode : list[0].id;
        setSelectedNode(activeId);
      }
    } catch {
      // 后端不可达时静默
    } finally {
      setLoadingNodes(false);
    }
  }, []);

  const loadContainers = useCallback(async (nodeId: number) => {
    setLoadingContainers(true);
    try {
      const list = await srv.fetchContainers(nodeId);
      setContainers(list);
    } catch {
      // 静默
    } finally {
      setLoadingContainers(false);
    }
  }, []);

  useEffect(() => {
    void loadNodes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedNode != null) {
      void loadContainers(selectedNode);
    }
  }, [selectedNode, loadContainers]);

  // ===== 节点操作 =====

  const submitNode = async () => {
    const v = await nodeForm.validateFields();
    try {
      const node = await srv.createNode({
        name: v.name, address: v.address, conn_type: v.connType,
        ssh_port: v.sshPort, ssh_user: v.sshUser, tls_certs: v.tlsCerts, remark: v.remark,
      });
      setNodes((prev) => [...prev, node]);
      setSelectedNode(node.id);
      setNodeModalOpen(false);
      message.success(`节点「${v.name}」已挂载`);
    } catch (e: any) {
      const msg = e?.response?.data?.message ?? e?.message ?? '创建失败';
      message.error(msg);
    }
  };

  const testNode = async (n: ComputeNode) => {
    setTestingNode(n.id);
    try {
      const result = await srv.testNode(n.id);
      setNodes((prev) => prev.map((x) => (x.id === n.id ? { ...x, online: result.success, remark: result.message } : x)));
      message.success(result.success ? `${n.name} 连接正常` : `连接失败：${result.message}`);
    } catch (e: any) {
      const msg = e?.response?.data?.message ?? e?.message ?? '测试失败';
      message.error(msg);
    } finally {
      setTestingNode(null);
    }
  };

  const autoMount = async () => {
    setMountingLocal(true);
    try {
      const node = await srv.autoMountLocal();
      setNodes((prev) => {
        const exists = prev.some((x) => x.id === node.id);
        return exists ? prev : [...prev, node];
      });
      setSelectedNode(node.id);
      message.success(`已自动挂载本机 Docker 节点「${node.name}」`);
    } catch (e: any) {
      const msg = e?.response?.data?.message ?? e?.message ?? '挂载失败';
      message.error(msg);
    } finally {
      setMountingLocal(false);
    }
  };

  const removeNode = async (n: ComputeNode) => {
    try {
      await srv.deleteNode(n.id);
      setNodes((prev) => prev.filter((x) => x.id !== n.id));
      setContainers((prev) => prev.filter((c) => c.nodeId !== n.id));
      if (selectedNode === n.id) {
        setSelectedNode(nodes.length > 1 ? nodes.find((x) => x.id !== n.id)?.id ?? null : null);
      }
      message.success(`节点「${n.name}」已删除`);
    } catch (e: any) {
      const msg = e?.response?.data?.message ?? e?.message ?? '删除失败';
      message.error(msg);
    }
  };

  // ===== 镜像搜索 =====

  const doSearch = async (q: string) => {
    if (!q.trim()) return;
    setSearching(true);
    setUsedBackendError(false);
    try {
      const imgs = await srv.searchHubImages(q, 15);
      setResults(imgs);
      if (imgs.length === 0) setUsedBackendError(true);
    } catch {
      setUsedBackendError(true);
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  const openSearch = (preset?: string) => {
    setSearchOpen(true);
    setQuery(preset ?? '');
    if (preset) void doSearch(preset);
  };

  const pickImage = (img: HubImage) => {
    setSearchOpen(false);
    setCreateFor({ image: img.name });
    const isOpencode = img.name.includes('opencode');
    const defaultCmd = isOpencode ? 'opencode web --port 4096' : '';
    createForm.setFieldsValue({
      name: img.name.replace(/[/.:]+/g, '-').replace(/^-+|-+$/g, '') || 'container',
      commandText: defaultCmd,
      templateId: undefined,
    });
    setContainerConfig({
      ports: isOpencode ? [{ hostPort: '4096', containerPort: '4096', protocol: 'tcp' }] : [],
      envs: [],
      volumes: [],
      network: 'bridge',
      restartPolicy: isOpencode ? 'unless-stopped' : 'no',
    });
    setCommandText(defaultCmd);
  };

  // ===== 容器操作 =====

  const submitCreate = async () => {
    const v = await createForm.validateFields();
    if (!createFor || selectedNode == null) return;
    const isHost = containerConfig.network === 'host';
    const ports = isHost ? [] : serializePorts(containerConfig.ports);
    const envVars = serializeEnvs(containerConfig.envs);
    const vols = serializeVolumes(containerConfig.volumes);
    try {
      // 若为「重新配置」，先停止 + 删除旧容器（Docker 不支持热改端口/网络/挂载）
      if (createFor.replacing) {
        const old = createFor.replacing;
        try {
          if (old.status === 'running') {
            await srv.stopContainer(selectedNode, old.id);
          }
        } catch {
          // 停止失败继续尝试强制删除
        }
        await srv.removeContainer(selectedNode, old.id, true);
        setContainers((prev) => prev.filter((x) => x.id !== old.id));
      }
      const c = await srv.createContainer(selectedNode, {
        name: v.name, image: createFor.image, ports, env_vars: envVars,
        volumes: vols.length > 0 ? vols : undefined,
        restart_policy: containerConfig.restartPolicy !== 'no' ? containerConfig.restartPolicy : undefined,
        network: containerConfig.network !== 'bridge' ? containerConfig.network : undefined,
        command: commandText || undefined,
      });
      setContainers((prev) => [...prev, c]);
      // 重新配置成功后立即启动（如原容器在跑）
      if (createFor.replacing && createFor.replacing.status === 'running') {
        try {
          await srv.startContainer(selectedNode, c.id);
          setContainers((prev) => prev.map((x) => (x.id === c.id ? { ...x, status: 'running' } : x)));
        } catch {
          // 启动失败不阻塞流程
        }
      }
      const wasReconfig = !!createFor.replacing;
      setCreateFor(null);
      setContainerConfig(emptyConfig());
      setCommandText('');
      message.success(wasReconfig ? `容器 ${v.name} 已按新配置重建` : `容器 ${v.name} 已创建`);
    } catch (e: any) {
      const msg = e?.response?.data?.message ?? e?.message ?? '创建失败';
      message.error(msg);
    }
  };

  // 「重新配置」入口：用现有容器的配置回填 Modal，提交后会 stop+remove+recreate
  const openReconfigure = (c: ContainerInstance) => {
    setCreateFor({ image: c.image, replacing: c });
    createForm.setFieldsValue({
      name: c.name,
      commandText: '',
      templateId: undefined,
    });
    const network = c.network && c.network !== 'default' ? c.network : 'bridge';
    setContainerConfig({
      ports: network === 'host' ? [] : parsePortsFromContainer(c.ports),
      envs: [], // docker ps 不返回 env，保留为空由用户重新指定
      volumes: parseVolumesFromContainer(c.volumes),
      network,
      restartPolicy: 'no',
    });
    setCommandText('');
  };

  const doStart = async (c: ContainerInstance) => {
    if (selectedNode == null) return;
    setOperatingCid(c.id);
    try {
      await srv.startContainer(selectedNode, c.id);
      setContainers((prev) => prev.map((x) => (x.id === c.id ? { ...x, status: 'running' } : x)));
    } catch (e: any) {
      message.error(e?.response?.data?.message ?? '启动失败');
    } finally {
      setOperatingCid(null);
    }
  };

  const doStop = async (c: ContainerInstance) => {
    if (selectedNode == null) return;
    setOperatingCid(c.id);
    try {
      await srv.stopContainer(selectedNode, c.id);
      setContainers((prev) => prev.map((x) => (x.id === c.id ? { ...x, status: 'exited' } : x)));
    } catch (e: any) {
      message.error(e?.response?.data?.message ?? '停止失败');
    } finally {
      setOperatingCid(null);
    }
  };

  const doRemove = async (c: ContainerInstance) => {
    if (selectedNode == null) return;
    setOperatingCid(c.id);
    try {
      await srv.removeContainer(selectedNode, c.id, c.status === 'running');
      setContainers((prev) => prev.filter((x) => x.id !== c.id));
      message.success(`已删除 ${c.name}`);
    } catch (e: any) {
      message.error(e?.response?.data?.message ?? '删除失败');
    } finally {
      setOperatingCid(null);
    }
  };

  // ===== 镜像管理 =====

  const loadImages = async () => {
    if (selectedNode == null) return;
    setLoadingImages(true);
    try {
      const imgs = await srv.listImages(selectedNode);
      setImages(imgs);
    } catch {
      setImages([]);
    } finally {
      setLoadingImages(false);
    }
  };

  const pullImg = async (img: string) => {
    if (selectedNode == null) return;
    setPullingImage(img);
    try {
      await srv.pullImage(selectedNode, img);
      message.success(`${img} 拉取成功`);
      await loadImages();
    } catch (e: any) {
      message.error(e?.response?.data?.message || '拉取失败');
    } finally {
      setPullingImage('');
    }
  };

  const removeImg = async (full: string) => {
    if (selectedNode == null) return;
    try {
      await srv.removeImage(selectedNode, full);
      setImages(prev => prev.filter(x => `${x.repository}:${x.tag}` !== full));
      message.success(`已删除 ${full}`);
    } catch (e: any) {
      message.error(e?.response?.data?.message || '删除失败');
    }
  };

  const createFromImage = (img: ImageListItem) => {
    const fullName = img.repository ? `${img.repository}:${img.tag}` : `${img.id}:${img.tag}`;
    setCreateFor({ image: fullName });
    createForm.setFieldsValue({
      name: (img.repository || img.id.split(':')[0] || 'container').replace(/[/.:]+/g, '-'),
      commandText: '',
      templateId: undefined,
    });
    setContainerConfig(emptyConfig());
    setCommandText('');
  };

  const showLogs = async (c: ContainerInstance) => {
    if (selectedNode == null) return;
    setLoadingLogs(true);
    setLogsModal({ name: c.name, lines: [] });
    try {
      const text = await srv.fetchContainerLogs(selectedNode, c.id, '500');
      const lines: LogLine[] = text.split('\n').map((raw, i) => {
        let level: LogLine['level'] = 'info';
        if (raw.startsWith('#')) level = 'event';
        else if (/error|Error/i.test(raw.slice(0, 40))) level = 'error';
        else if (/warn|WARN/i.test(raw.slice(0, 40))) level = 'warn';
        return { seq: i + 1, level, text: raw };
      });
      setLogsModal({ name: c.name, lines });
    } catch {
      setLogsModal({ name: c.name, lines: [{ seq: 1, level: 'error', text: '无法获取容器日志' }] });
    } finally {
      setLoadingLogs(false);
    }
  };

  // ===== 节点切换时加载镜像 =====
  useEffect(() => {
    if (selectedNode !== null && detailTab === 'images') {
      loadImages();
    }
  }, [selectedNode, detailTab]);

  // ===== 模板 =====

  const loadTemplates = useCallback(async () => {
    try {
      setTemplates(await srv.fetchTemplates());
    } catch {
      // 静默
    }
  }, []);

  useEffect(() => {
    if (detailTab === 'templates') void loadTemplates();
  }, [detailTab, loadTemplates]);

  const applyTemplate = (t: ContainerTemplate) => {
    // 从模板回填创建容器表单
    setCreateFor({ image: t.image });
    createForm.setFieldsValue({
      name: t.name.replace(/[^a-zA-Z0-9_.-]/g, '-').toLowerCase() || 'container',
      commandText: t.command || '',
      templateId: t.id,
    });
    setContainerConfig({
      ports: parsePorts(t.ports),
      envs: parseEnvs(t.env_vars),
      volumes: parseVolumes(t.volumes),
      network: t.network || 'bridge',
      restartPolicy: t.restart_policy || 'no',
    });
    setCommandText(t.command || '');
    setDetailTab('containers');
  };

  const saveAsTemplate = async () => {
    const v = await createForm.validateFields().catch(() => null);
    if (!v || !createFor) {
      message.warning('请先填写镜像与名称');
      return;
    }
    const name = window.prompt('模板名称', v.name);
    if (!name) return;
    const isHost = containerConfig.network === 'host';
    const ports = isHost ? [] : serializePorts(containerConfig.ports);
    const envVars = serializeEnvs(containerConfig.envs);
    const vols = serializeVolumes(containerConfig.volumes);
    try {
      const created = await srv.createTemplate({
        name,
        image: createFor.image,
        command: commandText || undefined,
        ports,
        env_vars: envVars,
        volumes: vols,
        restart_policy: containerConfig.restartPolicy !== 'no' ? containerConfig.restartPolicy : undefined,
        network: containerConfig.network !== 'bridge' ? containerConfig.network : undefined,
      });
      setTemplates((prev) => [...prev, created]);
      message.success(`已保存为模板「${name}」`);
    } catch (e: any) {
      message.error(e?.response?.data?.message ?? '保存失败');
    }
  };

  // ===== 容器表格 =====

  const containerColumns: ColumnsType<ContainerInstance> = [
    {
      title: '容器', dataIndex: 'name', key: 'name',
      render: (v: string, c) => (
        <Space size={8}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5 }}>{v}</span>
          {c.expertSlug && <Tag style={{ fontSize: 10 }}>@{c.expertSlug}</Tag>}
        </Space>
      ),
    },
    {
      title: '镜像', dataIndex: 'image', key: 'image',
      render: (v: string) => <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{v}</span>,
    },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s: string) => {
        const m = CONTAINER_STATUS[s as keyof typeof CONTAINER_STATUS] ?? CONTAINER_STATUS.unknown;
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: m.color }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%', background: m.dot,
              boxShadow: s === 'running' ? `0 0 0 3px ${m.dot}22` : 'none',
            }} />
            {m.label}
          </span>
        );
      },
    },
    {
      title: '端口', dataIndex: 'ports', key: 'ports', width: 130,
      render: (v: string) => <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11.5 }}>{v || '-'}</span>,
    },
    {
      title: '网络', dataIndex: 'network', key: 'network', width: 80,
      render: (v: string) => (
        <Tag style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5 }}>{v || '-'}</Tag>
      ),
    },
    {
      title: '挂载', dataIndex: 'volumes', key: 'volumes', ellipsis: true,
      render: (v: string) => v ? (
        <Tooltip title={v} overlayStyle={{ maxWidth: 480 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--ink-60)', cursor: 'default' }}>
            {v}
          </span>
        </Tooltip>
      ) : <span style={{ color: 'var(--ink-30)' }}>-</span>,
    },
    {
      title: '创建时间', dataIndex: 'createdAt', key: 'createdAt', width: 140,
      render: (v: string | Date) => (
        <span style={{ fontSize: 12, color: 'var(--ink-40)' }}>
          {typeof v === 'string' ? v : fmtDateTime(v)}
        </span>
      ),
    },
    {
      title: '操作', key: 'actions', width: 230,
      render: (_, c) => (
        <Space size={2}>
          {c.status === 'running' ? (
            <Tooltip title="停止">
              <Button size="small" type="text" danger loading={operatingCid === c.id}
                      icon={<PoweroffOutlined />} onClick={() => doStop(c)} />
            </Tooltip>
          ) : (
            <Tooltip title="启动">
              <Button size="small" type="text" loading={operatingCid === c.id}
                      icon={<PlayCircleOutlined />} onClick={() => doStart(c)} />
            </Tooltip>
          )}
          <Tooltip title={c.status === 'running' ? '终端' : '启动后可用'}>
            <Button size="small" type="text" disabled={c.status !== 'running'}
                    icon={<ConsoleSqlOutlined />} onClick={() => { console.log('[Terminal] button clicked, container:', c.name, c.id, 'status:', c.status); setTerminalFor(c); }} />
          </Tooltip>
          <Tooltip title={c.status === 'running' ? '执行命令' : '启动后可用'}>
            <Button size="small" type="text" disabled={c.status !== 'running'}
                    icon={<CodeOutlined />} onClick={() => setExecFor(c)} />
          </Tooltip>
          <Tooltip title="日志">
            <Button size="small" type="text" icon={<FileTextOutlined />} onClick={() => void showLogs(c)} />
          </Tooltip>
          <Popconfirm
            title={
              c.status === 'running'
                ? '重新配置将停止并删除该容器，再按新配置重建（容器内数据会随之丢失，除非有持久化挂载）。继续？'
                : '重新配置将删除该容器并按新配置重建，继续？'
            }
            onConfirm={() => openReconfigure(c)}
          >
            <Tooltip title="重新配置端口/网络/挂载">
              <Button size="small" type="text" icon={<EditOutlined />} />
            </Tooltip>
          </Popconfirm>
          <Popconfirm
            title={c.status === 'running' ? '容器运行中，将强制删除（-f）。继续？' : `删除容器 ${c.name}？`}
            onConfirm={() => doRemove(c)}
          >
            <Button size="small" type="text" danger loading={operatingCid === c.id} icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // ===== 镜像表格 =====

  const imageColumns: ColumnsType<ImageListItem> = [
    {
      title: '镜像', key: 'name',
      render: (_: any, img) => (
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13 }}>
          {img.repository || img.id} <Tag style={{ fontSize: 10 }}>{img.tag}</Tag>
        </span>
      ),
    },
    {
      title: '大小', dataIndex: 'size', key: 'size', width: 100,
      render: (v: string) => <span style={{ fontSize: 12 }}>{v || '-'}</span>,
    },
    {
      title: '操作', key: 'actions', width: 220,
      render: (_: any, img) => {
        const fullName = img.repository ? `${img.repository}:${img.tag}` : `${img.id}:${img.tag}`;
        return (
          <Space size={4}>
            <Button size="small" type="primary" ghost onClick={() => createFromImage(img)}>
              创建容器
            </Button>
            <Popconfirm title={`删除镜像 ${fullName}？`} onConfirm={() => removeImg(fullName)}>
              <Button size="small" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      {/* 工具条 */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 14, gap: 12, flexWrap: 'wrap',
      }}>
        <Text style={{ color: 'var(--ink-40)', fontSize: 12 }}>
          共 {nodes.length} 个节点 · {containers.length} 个容器 · 运行中 {runningCount}
          {nodes.some((n) => !n.online) && (
            <span style={{ color: '#a86e12' }}>　·　有节点离线</span>
          )}
        </Text>
        <Space size={8}>
          <Button size="small" icon={<ReloadOutlined />} loading={loadingNodes} onClick={() => void loadNodes()}>刷新</Button>
          <Button icon={<RocketOutlined />} loading={mountingLocal} onClick={autoMount}>一键挂载本机</Button>
          <Button icon={<PlusOutlined />} onClick={() => setNodeModalOpen(true)}>挂载节点</Button>
          <Button icon={<ApiOutlined />} onClick={() => openSearch()}>搜索镜像</Button>
          <Button type="primary" icon={<PlusOutlined />}
                  disabled={selectedNode == null}
                  onClick={() => openSearch('sst/opencode')}>
            新建容器
          </Button>
        </Space>
      </div>

      {/* 节点卡片 */}
      {loadingNodes && nodes.length === 0 ? (
        <div style={{ padding: 40, textAlign: 'center' }}><Spin /></div>
      ) : nodes.length === 0 ? (
        <div className="sched-empty">
          <div className="sched-empty-title">暂无算力节点</div>
          <div className="sched-empty-hint">点「挂载节点」接入本机或远程 Docker 服务器</div>
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
          gap: 14,
        }}>
          {nodes.map((n) => (
            <div
              key={n.id}
              className={[
                'node-card',
                selectedNode === n.id ? 'node-card--selected' : '',
                !n.online ? 'node-card--offline' : '',
              ].filter(Boolean).join(' ')}
              onClick={() => setSelectedNode(n.id)}
            >
              <div className="node-card-top">
                <span className="node-card-name">{n.name}</span>
                <Tag style={{ fontSize: 10 }}>{CONN_LABEL[n.connType]}</Tag>
                <span className="node-card-status">
                  <span style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: n.online ? '#22c55e' : '#bfbcb5',
                    boxShadow: n.online ? '0 0 0 3px #22c55e22' : 'none',
                  }} />
                  {n.online ? '在线' : '离线'}
                </span>
              </div>
              <div className="node-card-addr">{n.address}</div>
              <div className="node-card-specs">
                <span>CPU {n.cpu || '?'}</span>
                <span>内存 {n.mem || '?'}</span>
                <span>磁盘 {n.disk || '?'}</span>
              </div>
              {n.remark && <div style={{ fontSize: 11, color: 'var(--ink-40)' }}>{n.remark}</div>}
              <div className="node-card-actions" onClick={(ev) => ev.stopPropagation()}>
                <Button size="small" loading={testingNode === n.id} onClick={() => testNode(n)}>
                  测试连接
                </Button>
                <Popconfirm title={`移除节点「${n.name}」？其容器记录将一并清除`} onConfirm={() => removeNode(n)}>
                  <Button size="small" danger icon={<DeleteOutlined />}>移除</Button>
                </Popconfirm>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 节点详情：容器 / 镜像 tab */}
      {selectedNodeObj && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 20, marginBottom: 8 }}>
            <CloudServerOutlined style={{ color: 'var(--ink-40)' }} />
            <Text strong>{selectedNodeObj.name}</Text>
            <Space size={4}>
              <Button size="small" type={detailTab === 'containers' ? 'primary' : 'default'} ghost
                onClick={() => setDetailTab('containers')}>
                容器 <span style={{ opacity: 0.6 }}>{nodeContainers.length}</span>
              </Button>
              <Button size="small" type={detailTab === 'images' ? 'primary' : 'default'} ghost
                onClick={() => setDetailTab('images')}>
                <InboxOutlined /> 镜像管理
              </Button>
              <Button size="small" type={detailTab === 'templates' ? 'primary' : 'default'} ghost
                onClick={() => setDetailTab('templates')}>
                <SaveOutlined /> 模板 <span style={{ opacity: 0.6 }}>{templates.length}</span>
              </Button>
            </Space>
          </div>

          {detailTab === 'containers' && (
            <Table<ContainerInstance>
              rowKey="id"
              size="middle"
              loading={loadingContainers}
              columns={containerColumns}
              dataSource={nodeContainers}
              pagination={false}
              locale={{ emptyText: <Empty description="该节点暂无容器，点右上角「新建容器」" /> }}
            />
          )}

          {detailTab === 'images' && (
            <div>
              <div style={{ marginBottom: 10, display: 'flex', gap: 8 }}>
                <Input.Search size="small" placeholder="拉取镜像，如 python:3.12" style={{ maxWidth: 320 }}
                  enterButton={<><CloudDownloadOutlined /> 拉取</>} loading={!!pullingImage}
                  onSearch={v => v && pullImg(v)} />
                <Button size="small" icon={<ReloadOutlined />} loading={loadingImages} onClick={loadImages}>刷新</Button>
              </div>
              <Table<ImageListItem>
                rowKey="id"
                size="middle"
                loading={loadingImages}
                columns={imageColumns}
                dataSource={images}
                pagination={false}
                locale={{ emptyText: <Empty description="暂无镜像，在上方搜索框拉取新镜像" /> }}
              />
            </div>
          )}

          {detailTab === 'templates' && (
            <TemplatesPanel onUseTemplate={applyTemplate} />
          )}
        </>
      )}

      {/* 挂载节点 Modal */}
      <Modal
        title="挂载算力节点"
        open={nodeModalOpen}
        onCancel={() => setNodeModalOpen(false)}
        onOk={() => void submitNode()}
        okText="挂载"
        width={560}
        destroyOnHidden
      >
        <Form form={nodeForm} layout="vertical" initialValues={{ connType: 'ssh', sshPort: 22, sshUser: 'root' }}>
          <Form.Item name="name" label="节点名称" rules={[{ required: true, message: '请输入节点名称' }]}>
            <Input placeholder="gpu-node-01" />
          </Form.Item>
          <Form.Item name="address" label="节点地址" rules={[{ required: true, message: '请输入节点地址' }]}>
            <Input style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5 }} placeholder="192.168.1.23" />
          </Form.Item>
          <Form.Item name="connType" label="连接方式" style={{ marginBottom: 8 }}>
            <Radio.Group>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <Radio value="ssh">
                  <span style={{ fontWeight: 500 }}>SSH（推荐）</span>
                  <span style={{ fontSize: 12, color: 'var(--ink-40)', marginLeft: 8 }}>
                    目标节点只需可 SSH 登录，零额外配置
                  </span>
                </Radio>
                <Radio value="docker-api">
                  <span style={{ fontWeight: 500 }}>Docker API（TLS）</span>
                  <span style={{ fontSize: 12, color: 'var(--ink-40)', marginLeft: 8 }}>
                    需配置 dockerd 开启 2376 端口 + 证书
                  </span>
                </Radio>
              </div>
            </Radio.Group>
          </Form.Item>
          {watchConn === 'ssh' ? (
            <Space size={12} style={{ display: 'flex' }}>
              <Form.Item name="sshPort" label="SSH 端口" style={{ flex: 1 }}>
                <Input style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5 }} placeholder="22" />
              </Form.Item>
              <Form.Item name="sshUser" label="SSH 用户" style={{ flex: 2 }}>
                <Input style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5 }} placeholder="root" />
              </Form.Item>
            </Space>
          ) : (
            <Form.Item name="tlsCerts" label="TLS 证书目录（后端侧路径）">
              <Input style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5 }} placeholder="/etc/docker/certs/node-01/" />
            </Form.Item>
          )}
          <Alert
            type="info" showIcon style={{ marginBottom: 16 }}
            title={watchConn === 'ssh' ? SSH_HINT : API_HINT}
          />
          <Form.Item name="remark" label="备注（可选）" style={{ marginBottom: 0 }}>
            <Input placeholder="机房 / 用途 / 联系人" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 镜像搜索 Modal */}
      <Modal
        title="搜索 Docker 镜像"
        open={searchOpen}
        onCancel={() => setSearchOpen(false)}
        footer={null}
        width={720}
      >
        <Input.Search
          size="large"
          placeholder="搜索 Docker Hub，如 opencode / nginx / postgres …"
          enterButton="搜索"
          loading={searching}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onSearch={(v) => void doSearch(v)}
        />
        <div style={{ margin: '8px 2px', fontSize: 12, color: 'var(--ink-40)' }}>
          数据源：后端代理 Docker Hub 搜索 API（只读）
          {usedBackendError && <span style={{ color: '#a86e12' }}>　·　后端/Docker Hub 不可达</span>}
        </div>
        {searching ? (
          <div style={{ padding: '48px 0', textAlign: 'center' }}><Spin /></div>
        ) : results.length === 0 ? (
          <div className="img-results-empty">
            <Empty description={usedBackendError ? '搜索失败，请确认后端运行中且可访问 Docker Hub' : '输入关键词搜索镜像'} />
          </div>
        ) : (
          <div className="img-results">
            {results.map((img) => (
              <div key={img.name} className="img-result">
                <div className="img-result-main">
                  <div className="img-result-title">
                    <span className="img-result-name">{img.name}</span>
                    {img.official && <Tag color="blue" style={{ fontSize: 10 }}>Official</Tag>}
                  </div>
                  <div className="img-result-desc">{img.description || '（无描述）'}</div>
                </div>
                <div className="img-result-meta">
                  ★ {img.stars.toLocaleString()} · {img.pulls.toLocaleString()} pulls
                </div>
                <Button type="primary" size="small" onClick={() => pickImage(img)}>创建容器</Button>
              </div>
            ))}
          </div>
        )}
      </Modal>

      {/* 创建容器 Modal */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingRight: 40 }}>
            <span>{createFor?.replacing ? `重新配置容器 · ${createFor.replacing.name}` : '创建容器'}</span>
            <Button size="small" type="text" icon={<SaveOutlined />} onClick={() => void saveAsTemplate()}>
              另存为模板
            </Button>
          </div>
        }
        open={!!createFor}
        onCancel={() => setCreateFor(null)}
        onOk={() => void submitCreate()}
        okText={createFor?.replacing ? '停止并重建' : '创建'}
        width={560}
        destroyOnHidden
      >
        {createFor?.replacing && (
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 12 }}
            message="Docker 不支持热改端口/网络/挂载"
            description="提交后会先停止并删除现有容器，再按新配置重建。容器 rootfs 内的数据会丢失（挂载卷/命名卷不受影响）。"
          />
        )}
        <Space size={8} style={{ marginBottom: 16 }} wrap>
          <Tag icon={<CloudServerOutlined />}>{selectedNodeObj?.name}</Tag>
          <Tag style={{ fontFamily: 'var(--font-mono)' }}>{createFor?.image}</Tag>
        </Space>
        <Form form={createForm} layout="vertical">
          {templates.length > 0 && (
            <Form.Item name="templateId" label="从模板填充">
              <Select
                allowClear
                placeholder="选择模板快速填充配置"
                options={templates.map((t) => ({ value: t.id, label: `${t.name} · ${t.image}` }))}
                onChange={(val) => {
                  const t = templates.find((x) => x.id === val);
                  if (t) applyTemplate(t);
                }}
              />
            </Form.Item>
          )}
          <Form.Item name="name" label="容器名称" rules={[{ required: true, message: '请输入容器名称' }]}>
            <Input style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5 }} />
          </Form.Item>
          <Form.Item label="启动命令（覆盖镜像 CMD）" tooltip="追加在镜像名之后，如 opencode web --port 4096">
            <Input
              style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5 }}
              placeholder="opencode web --port 4096"
              value={commandText}
              onChange={(e) => setCommandText(e.target.value)}
            />
          </Form.Item>
          <ContainerConfigFields value={containerConfig} onChange={setContainerConfig} />
          <div style={{
            marginTop: 12,
            fontSize: 11, color: 'var(--ink-40)', fontFamily: 'var(--font-mono)', wordBreak: 'break-all',
          }}>
            预览：docker run -d --name {watchCreateName || '<name>'}
            {containerConfig.network === 'host'
              ? ''
              : serializePorts(containerConfig.ports).map((p) => ` -p ${p}`).join('')}
            {serializeVolumes(containerConfig.volumes).map((v) => ` -v ${v}`).join('')}
            {serializeEnvs(containerConfig.envs).map((e) => ` -e ${e}`).join('')}
            {containerConfig.network !== 'bridge' ? ` --network ${containerConfig.network}` : ''}
            {containerConfig.restartPolicy !== 'no' ? ` --restart ${containerConfig.restartPolicy}` : ''}
            {' '}{createFor?.image}
            {commandText ? ` ${commandText}` : ''}
          </div>
        </Form>
      </Modal>

      {/* 容器日志 Modal */}
      <Modal
        title={`容器日志 · ${logsModal?.name ?? ''}`}
        open={!!logsModal}
        onCancel={() => setLogsModal(null)}
        footer={null}
        width={860}
      >
        {loadingLogs ? <div style={{ padding: 40, textAlign: 'center' }}><Spin /></div> : (
          <LogViewer lines={logsModal?.lines ?? []} />
        )}
      </Modal>

      {/* 容器交互终端 Drawer */}
      <TerminalDrawer
        open={!!terminalFor}
        onClose={() => setTerminalFor(null)}
        node={selectedNodeObj ?? null}
        container={terminalFor}
      />

      {/* 容器内一次性命令执行 Modal */}
      <ExecCommandModal
        open={!!execFor}
        onClose={() => setExecFor(null)}
        nodeId={selectedNode}
        cid={execFor?.id ?? null}
        containerName={execFor?.name}
      />
    </div>
  );
}

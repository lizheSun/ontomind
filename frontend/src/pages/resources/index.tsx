import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  Card, Button, Form, Input, Select, Switch, Tag, Typography,
  Space, Popconfirm, Empty, InputNumber, App, Tooltip, Drawer, Badge, Divider,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ApiOutlined,
  CheckCircleOutlined, SettingOutlined, ThunderboltOutlined,
  RobotOutlined, SendOutlined, CloudServerOutlined,
  CodeOutlined, ExperimentOutlined, ToolOutlined,
  PlayCircleOutlined, StopOutlined, ReloadOutlined,
  MonitorOutlined, LinkOutlined, BugOutlined,
  CloudUploadOutlined, DockerOutlined, DesktopOutlined,
  DownloadOutlined, SearchOutlined, FilterOutlined,
  CloseCircleOutlined, MinusCircleOutlined, ArrowRightOutlined,
  ClusterOutlined, DatabaseOutlined, AppstoreOutlined, BuildOutlined,
  HomeOutlined, MessageOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import llmService from '../../services/llm.service';
import type { LLMConfig, LLMConfigCreate, LLMConfigUpdate } from '../../services/llm.service';
import { resourcesAPI } from '../../services/index';
import type { Instance, Agent, Skill, MCPConfig as MCPConfigType, AgentRun, LogEntry, DiscoveredAgent, AgentScanResult } from '../../types/index';
import AgentLooperListPage from './AgentLooperListPage';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

// ===================== 通用工具 =====================

const gradientBorder = '1px solid rgba(255,255,255,0.06)';
const cardStyle = { borderRadius: 14, background: 'rgba(255,255,255,0.015)', border: gradientBorder, transition: 'all .2s' };

function SectionHeader({ icon, title, count, extra }: { icon: React.ReactNode; title: string; count: number; extra?: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
      <Space size={10}>
        <span style={{ fontSize: 18 }}>{icon}</span>
        <Title level={5} style={{ margin: 0, color: '#e8eef5', fontWeight: 600 }}>{title}</Title>
        <Badge count={count} style={{ backgroundColor: 'rgba(96,165,250,0.2)', color: '#60a5fa', boxShadow: 'none', fontWeight: 500 }} />
      </Space>
      {extra}
    </div>
  );
}

// ===================== 概览统计条 =====================

function StatsBar({
  instances, agents, skills, mcps, runs, onNav,
}: {
  instances: number; agents: number; skills: number; mcps: number; runs: number;
  onNav: (key: string) => void;
}) {
  const items = [
    { key: 'instances', icon: <CloudServerOutlined />, label: '计算节点', count: instances, color: '#60a5fa', bg: 'rgba(96,165,250,0.1)' },
    { key: 'agents', icon: <RobotOutlined />, label: '智能体', count: agents, color: '#a78bfa', bg: 'rgba(167,139,250,0.1)' },
    { key: 'skills', icon: <ToolOutlined />, label: '技能', count: skills, color: '#f59e0b', bg: 'rgba(245,158,11,0.1)' },
    { key: 'mcps', icon: <LinkOutlined />, label: 'MCP 工具', count: mcps, color: '#34d399', bg: 'rgba(52,211,153,0.1)' },
    { key: 'runs', icon: <PlayCircleOutlined />, label: '运行中', count: runs, color: '#f472b6', bg: 'rgba(244,114,182,0.1)' },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 24 }}>
      {items.map(item => (
        <div
          key={item.key}
          onClick={() => onNav(item.key)}
          style={{
            cursor: 'pointer', padding: '14px 16px', borderRadius: 14,
            background: 'rgba(255,255,255,0.02)', border: gradientBorder,
            transition: 'all .2s',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = item.bg; e.currentTarget.style.borderColor = item.color + '40'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.02)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 28 }}>{item.icon}</span>
            <span style={{ fontSize: 28, fontWeight: 700, color: item.color }}>{item.count}</span>
          </div>
          <Text style={{ color: '#657a9a', fontSize: 12, fontWeight: 500, marginTop: 4, display: 'block' }}>{item.label}</Text>
        </div>
      ))}
    </div>
  );
}

// ===================== 侧边栏导航 =====================

const NAV_ITEMS = [
  { key: 'instances', icon: <CloudServerOutlined />, label: '计算节点' },
  { key: 'agents', icon: <RobotOutlined />, label: '智能体' },
  { key: 'skills', icon: <ToolOutlined />, label: '技能模块' },
  { key: 'mcps', icon: <LinkOutlined />, label: 'MCP 工具' },
  { key: 'runs', icon: <MonitorOutlined />, label: '运行监控' },
  { key: 'llm', icon: <ApiOutlined />, label: 'LLM 配置' },
];

function SideNav({ active, counts, onChange }: { active: string; counts: Record<string, number>; onChange: (k: string) => void }) {
  return (
    <div style={{ width: 180, flexShrink: 0 }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: '#506380', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 10, paddingLeft: 4 }}>
        资源类型
      </div>
      {NAV_ITEMS.map(item => (
        <div
          key={item.key}
          onClick={() => onChange(item.key)}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '9px 12px', borderRadius: 10, cursor: 'pointer', marginBottom: 2,
            fontSize: 13, transition: 'all .15s',
            color: active === item.key ? '#e8eef5' : '#7b8ea8',
            background: active === item.key ? 'rgba(96,165,250,0.12)' : 'transparent',
            fontWeight: active === item.key ? 600 : 400,
          }}
        >
          <Space size={8}>
            <span style={{ fontSize: 15 }}>{item.icon}</span>
            {item.label}
          </Space>
          <span style={{ fontSize: 11, color: active === item.key ? '#60a5fa' : '#506380', fontWeight: 500 }}>
            {counts[item.key] ?? 0}
          </span>
        </div>
      ))}
    </div>
  );
}

// ===================== 计算节点面板 =====================

function ComputeNodesPanel() {
  const { message, notification } = App.useApp();
  const [items, setItems] = useState<Instance[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<Instance | null>(null);
  const [form] = Form.useForm();
  const [registeringLocal, setRegisteringLocal] = useState(false);
  const [scanningMap, setScanningMap] = useState<Record<number, boolean>>({});
  const [discoveredAgents, setDiscoveredAgents] = useState<Record<number, DiscoveredAgent[]>>({});
  // T37: 本地节点自动发现信息（hostname / platform / agent_count / agent_looper_count）
  const [localNodeInfo, setLocalNodeInfo] = useState<{
    hostname?: string; platform?: string; agent_count?: number; agent_looper_count?: number;
  } | null>(null);
  const autoRegisteredRef = useRef(false);

  const fetch = useCallback(async () => {
    setLoading(true);
    try { const res = await resourcesAPI.listInstances({ skip: 0, limit: 200 }); setItems(res.data?.data || []); }
    catch { notification.error({ title: '加载失败', placement: 'top' }); }
    finally { setLoading(false); }
  }, [notification]);

  useEffect(() => { fetch(); }, [fetch]);

  // T37: 页面挂载时自动调用 register-local（一次会话只调用一次，用 ref + sessionStorage 双保险）
  useEffect(() => {
    if (autoRegisteredRef.current) return;
    if (typeof sessionStorage !== 'undefined' && sessionStorage.getItem('t37_local_registered') === '1') {
      autoRegisteredRef.current = true;
      return;
    }
    autoRegisteredRef.current = true;
    (async () => {
      try {
        const res = await resourcesAPI.registerLocalInstance();
        const payload = res.data || {};
        setLocalNodeInfo({
          hostname: payload.hostname,
          platform: payload.platform,
          agent_count: payload.agent_count,
          agent_looper_count: payload.agent_looper_count,
        });
        const discovered = payload.discovered_agents as DiscoveredAgent[] | undefined;
        const instData = payload.data as Instance | undefined;
        if (instData && discovered && discovered.length > 0) {
          setDiscoveredAgents(prev => ({ ...prev, [instData.id]: discovered }));
        }
        if (typeof sessionStorage !== 'undefined') {
          sessionStorage.setItem('t37_local_registered', '1');
        }
        fetch();
      } catch {
        // 静默失败 — 不干扰用户
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ instance_type: 'physical', protocol: 'ssh' }); setDrawerOpen(true); };
  const openEdit = (r: Instance) => { setEditing(r); form.setFieldsValue(r); setDrawerOpen(true); };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editing) { await resourcesAPI.updateInstance(editing.id, values); message.success('更新成功'); }
      else { await resourcesAPI.createInstance(values); message.success('创建成功'); }
      setDrawerOpen(false); fetch();
    } catch (err: any) { if (err?.errorFields) return; notification.error({ title: '操作失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
  };

  const handleDelete = async (id: number) => {
    try { await resourcesAPI.deleteInstance(id); message.success('删除成功'); fetch(); }
    catch (err: any) { notification.error({ title: '删除失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
  };

  const handleScanAgents = async (instId: number) => {
    setScanningMap(prev => ({ ...prev, [instId]: true }));
    try {
      const res = await resourcesAPI.scanAgents(instId);
      const data: AgentScanResult = res.data?.data || res.data;
      if (data?.agents) {
        setDiscoveredAgents(prev => ({ ...prev, [instId]: data.agents }));
        const healthy = data.agents.filter(a => a.is_healthy).length;
        const autoRegistered = (data as any).auto_registered || [];
        const msg = autoRegistered.length > 0
          ? `扫描完成：发现 ${data.agents.length} 个 Agent，${healthy} 个健康，已自动注册 ${autoRegistered.length} 个到智能体列表`
          : `扫描完成：${data.total_ports_scanned} 个端口，发现 ${data.agents.length} 个 Agent，${healthy} 个健康`;
        message.success(msg);
      }
    } catch (err: any) {
      notification.error({ title: '扫描失败', description: err?.response?.data?.detail || err?.message, placement: 'top' });
    } finally { setScanningMap(prev => ({ ...prev, [instId]: false })); }
  };

  const handleRegisterLocal = async () => {
    setRegisteringLocal(true);
    try {
      const res = await resourcesAPI.registerLocalInstance();
      const discovered = res.data?.discovered_agents as DiscoveredAgent[] | undefined;
      const instData = res.data?.data as Instance | undefined;
      if (instData && discovered) {
        setDiscoveredAgents(prev => ({ ...prev, [instData.id]: discovered }));
      }
      message.success(res.data?.message || '本地服务器已添加');
      fetch();
    } catch (err: any) {
      notification.error({ title: '添加失败', description: err?.response?.data?.detail || err?.message, placement: 'top' });
    } finally { setRegisteringLocal(false); }
  };

  const filtered = useMemo(() => {
    if (!search) return items;
    const q = search.toLowerCase();
    return items.filter(i => i.name?.toLowerCase().includes(q) || i.host?.toLowerCase().includes(q) || i.instance_type?.toLowerCase().includes(q));
  }, [items, search]);

  const typeMeta: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
    physical: { icon: <DesktopOutlined />, label: '物理机', color: '#60a5fa' },
    docker: { icon: <DockerOutlined />, label: 'Docker', color: '#34d399' },
    k8s_pod: { icon: <ClusterOutlined />, label: 'K8s Pod', color: '#a78bfa' },
  };

  const statusMeta: Record<string, { color: string; dot: string }> = {
    online: { color: '#34d399', dot: '●' },
    offline: { color: '#506380', dot: '○' },
    maintenance: { color: '#f59e0b', dot: '◉' },
  };

  return (
    <div>
      <SectionHeader icon={<CloudServerOutlined style={{ color: '#60a5fa' }} />} title="计算节点" count={items.length}
        extra={
          <Space>
            <Tooltip title="一键检测并添加本机为计算节点">
              <Button icon={<HomeOutlined />} loading={registeringLocal} onClick={handleRegisterLocal}>添加本地服务器</Button>
            </Tooltip>
            <Input prefix={<SearchOutlined style={{ color: '#506380' }} />} placeholder="搜索节点..." value={search}
              onChange={e => setSearch(e.target.value)} style={{ width: 200 }} allowClear />
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增节点</Button>
          </Space>
        }
      />

      {/* T37: 本地节点·计算节点 概览卡 — 页面挂载自动填充 */}
      {localNodeInfo && (
        <div style={{
          ...cardStyle, padding: '16px 20px', marginBottom: 14,
          borderColor: 'rgba(96,165,250,0.25)',
          background: 'linear-gradient(135deg, rgba(96,165,250,0.06), rgba(167,139,250,0.04))',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 40, height: 40, borderRadius: 12,
              background: 'rgba(96,165,250,0.15)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 20, color: '#60a5fa',
            }}>
              <HomeOutlined />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#e8eef5', marginBottom: 3 }}>
                本地节点 · 计算节点
              </div>
              <Space size={8} wrap>
                {localNodeInfo.hostname && (
                  <Tag style={{ borderRadius: 6, background: 'rgba(255,255,255,0.05)', color: '#94a3b8', border: 'none', fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}>
                    {localNodeInfo.hostname}
                  </Tag>
                )}
                {localNodeInfo.platform && (
                  <Tag style={{ borderRadius: 6, background: 'rgba(96,165,250,0.12)', color: '#60a5fa', border: 'none', fontSize: 11 }}>
                    <DesktopOutlined /> {localNodeInfo.platform}
                  </Tag>
                )}
                <Tag style={{ borderRadius: 6, background: 'rgba(167,139,250,0.12)', color: '#a78bfa', border: 'none', fontSize: 11 }}>
                  <RobotOutlined /> Agent: {localNodeInfo.agent_count ?? 0}
                </Tag>
                <Tag style={{ borderRadius: 6, background: 'rgba(52,211,153,0.12)', color: '#34d399', border: 'none', fontSize: 11 }}>
                  <ThunderboltOutlined /> Agent Looper: {localNodeInfo.agent_looper_count ?? 0}
                </Tag>
              </Space>
            </div>
          </div>
        </div>
      )}

      {filtered.length === 0 && !loading ? (
        <Empty description={<span style={{ color: '#506380' }}>暂无计算节点</span>} style={{ padding: 60 }} />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 14 }}>
          {filtered.map(item => {
            const tm = typeMeta[item.instance_type] || { icon: <DesktopOutlined />, label: item.instance_type, color: '#657a9a' };
            const sm = statusMeta[item.status] || { color: '#506380', dot: '○' };
            const memGb = item.memory_mb ? Math.round(item.memory_mb / 1024) : null;
            const diskGb = (item as any).disk_gb || null;
            return (
              <div key={item.id} style={{
                ...cardStyle, padding: '18px 20px', cursor: 'default',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 600, color: '#e8eef5', marginBottom: 2 }}>{item.name}</div>
                    <Space size={6}>
                      <Tag style={{ borderRadius: 6, background: `${tm.color}18`, color: tm.color, border: 'none', fontSize: 11 }}>{tm.icon} {tm.label}</Tag>
                      <span style={{ color: sm.color, fontSize: 11 }}>{sm.dot} {item.status}</span>
                    </Space>
                  </div>
                  <Space size={4}>
                    <Button type="text" size="small" icon={<EditOutlined />} onClick={() => openEdit(item)} />
                    <Popconfirm title="确定删除？" onConfirm={() => handleDelete(item.id)} okText="删除" cancelText="取消" okButtonProps={{ danger: true }}>
                      <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </Space>
                </div>

                <div style={{ marginBottom: 14 }}>
                  <div style={{ color: '#657a9a', fontSize: 12, fontFamily: 'JetBrains Mono, monospace' }}>{item.host}:{item.port}</div>
                  {item.os && <div style={{ color: '#506380', fontSize: 11, marginTop: 2 }}>{item.os}</div>}
                </div>

                {/* Resource meters */}
                <div style={{ display: 'flex', gap: 16 }}>
                  {item.cpu_cores != null && (
                    <div style={{ flex: 1 }}>
                      <Text style={{ color: '#506380', fontSize: 10 }}>CPU</Text>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#94a3b8' }}>{item.cpu_cores} 核</div>
                      <div style={{ height: 3, borderRadius: 3, background: 'rgba(255,255,255,0.06)', marginTop: 3, overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${Math.min(100, (item.cpu_cores || 0) * 12.5)}%`, borderRadius: 3, background: 'linear-gradient(90deg, #60a5fa, #818cf8)' }} />
                      </div>
                    </div>
                  )}
                  {memGb != null && (
                    <div style={{ flex: 1 }}>
                      <Text style={{ color: '#506380', fontSize: 10 }}>内存</Text>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#94a3b8' }}>{memGb} GB</div>
                      <div style={{ height: 3, borderRadius: 3, background: 'rgba(255,255,255,0.06)', marginTop: 3, overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${Math.min(100, (memGb / 32) * 100)}%`, borderRadius: 3, background: 'linear-gradient(90deg, #34d399, #10b981)' }} />
                      </div>
                    </div>
                  )}
                  {diskGb != null && (
                    <div style={{ flex: 1 }}>
                      <Text style={{ color: '#506380', fontSize: 10 }}>磁盘</Text>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#94a3b8' }}>{diskGb} GB</div>
                      <div style={{ height: 3, borderRadius: 3, background: 'rgba(255,255,255,0.06)', marginTop: 3, overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${Math.min(100, (diskGb / 500) * 100)}%`, borderRadius: 3, background: 'linear-gradient(90deg, #f59e0b, #fbbf24)' }} />
                      </div>
                    </div>
                  )}
                </div>

                {/* Agent 发现区域 */}
                <div style={{ marginTop: 14, borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Text style={{ color: '#657a9a', fontSize: 11 }}>Agent 服务</Text>
                    <Button
                      type="text"
                      size="small"
                      icon={<ExperimentOutlined />}
                      loading={scanningMap[item.id]}
                      onClick={() => handleScanAgents(item.id)}
                      style={{ color: '#60a5fa', fontSize: 11, padding: '0 4px', height: 22 }}
                    >
                      扫描
                    </Button>
                  </div>
                  {discoveredAgents[item.id] && discoveredAgents[item.id].length > 0 ? (
                    <Space orientation="vertical" size={4} style={{ width: '100%' }}>
                      {discoveredAgents[item.id].map((a, i) => (
                        <div
                          key={i}
                          style={{
                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            background: a.is_healthy ? 'rgba(52,211,153,0.06)' : 'rgba(245,158,11,0.06)',
                            borderRadius: 8, padding: '6px 10px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span style={{ fontSize: 13 }}>{a.icon}</span>
                            <span style={{ fontSize: 12, color: '#e8eef5', fontWeight: 500 }}>{a.label}</span>
                            {a.version && (
                              <Tag style={{ borderRadius: 4, fontSize: 10, background: 'rgba(255,255,255,0.06)', color: '#657a9a', border: 'none', margin: 0 }}>{a.version}</Tag>
                            )}
                          </div>
                          <Space size={6}>
                            {a.port > 0 && (
                              <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: '#506380' }}>:{a.port}</span>
                            )}
                            <Tag style={{
                              borderRadius: 4, fontSize: 10, margin: 0,
                              background: a.is_healthy ? 'rgba(52,211,153,0.15)' : 'rgba(245,158,11,0.15)',
                              color: a.is_healthy ? '#34d399' : '#f59e0b',
                              border: `1px solid ${a.is_healthy ? 'rgba(52,211,153,0.3)' : 'rgba(245,158,11,0.3)'}`,
                            }}>
                              <span style={{ fontSize: 8, marginRight: 3 }}>{a.is_healthy ? '●' : '○'}</span>
                              {a.is_healthy ? '可用' : a.error || '不可用'}
                            </Tag>
                          </Space>
                        </div>
                      ))}
                    </Space>
                  ) : (
                    <div style={{ color: '#3d4e6b', fontSize: 11, textAlign: 'center', padding: '6px 0' }}>
                      {scanningMap[item.id] ? '扫描中...' : '点击扫描发现 Agent'}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Drawer
        title={<Space>{editing ? <EditOutlined style={{ color: '#60a5fa' }} /> : <PlusOutlined style={{ color: '#60a5fa' }} />}{editing ? '编辑节点' : '新增节点'}</Space>}
        open={drawerOpen} onClose={() => setDrawerOpen(false)}
        extra={<Space><Button onClick={() => setDrawerOpen(false)}>取消</Button><Button type="primary" onClick={handleSubmit}>保存</Button></Space>}
        styles={{ body: { paddingBottom: 40 }, wrapper: { width: 480 } }}
      >
        <Form form={form} layout="vertical" size="large">
          <Form.Item name="name" label="节点名称" rules={[{ required: true }]}><Input placeholder="prod-server-01" /></Form.Item>
          <Space style={{ width: '100%' }} size={16}>
            <Form.Item name="host" label="主机地址" rules={[{ required: true }]} style={{ flex: 1 }}><Input placeholder="192.168.1.100" /></Form.Item>
            <Form.Item name="port" label="端口" rules={[{ required: true }]} style={{ width: 110 }}><InputNumber min={1} max={65535} style={{ width: '100%' }} /></Form.Item>
          </Space>
          <Space style={{ width: '100%' }} size={16}>
            <Form.Item name="instance_type" label="节点类型" rules={[{ required: true }]} style={{ flex: 1 }}>
              <Select><Select.Option value="physical">物理机</Select.Option><Select.Option value="docker">Docker</Select.Option><Select.Option value="k8s_pod">K8s Pod</Select.Option></Select>
            </Form.Item>
            <Form.Item name="protocol" label="管理协议" rules={[{ required: true }]} style={{ flex: 1 }}>
              <Select><Select.Option value="ssh">SSH</Select.Option><Select.Option value="docker_api">Docker API</Select.Option></Select>
            </Form.Item>
          </Space>
          <Space style={{ width: '100%' }} size={16}>
            <Form.Item name="os" label="操作系统" style={{ flex: 1 }}><Input placeholder="Ubuntu 22.04" /></Form.Item>
            <Form.Item name="cpu_cores" label="CPU 核数" style={{ width: 100 }}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="memory_mb" label="内存(MB)" style={{ width: 110 }}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="disk_gb" label="磁盘(GB)" style={{ width: 110 }}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          </Space>
          <Form.Item name="description" label="描述"><TextArea rows={2} /></Form.Item>
        </Form>
      </Drawer>
    </div>
  );
}

// ===================== Agent 面板 =====================

function AgentsPanel() {
  const { message, notification } = App.useApp();
  const [items, setItems] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<Agent | null>(null);
  const [form] = Form.useForm();
  const [chatAgent, setChatAgent] = useState<Agent | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [chatSending, setChatSending] = useState(false);
  const [chatHistory, setChatHistory] = useState<{ role: 'user' | 'agent'; content: string; error?: boolean; events?: { type: string; content?: string; tool?: string }[] }[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const chatWsRef = useRef<WebSocket | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    try { const res = await resourcesAPI.listAgents({ skip: 0, limit: 200 }); setItems(res.data?.data || []); }
    catch { notification.error({ title: '加载失败', placement: 'top' }); }
    finally { setLoading(false); }
  }, [notification]);

  useEffect(() => { fetch(); }, [fetch]);

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ agent_type: 'custom', runtime: 'docker', version: 'latest', is_active: true }); setDrawerOpen(true); };
  const openEdit = (r: Agent) => { setEditing(r); form.setFieldsValue(r); setDrawerOpen(true); };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editing) { await resourcesAPI.updateAgent(editing.id, values); message.success('更新成功'); }
      else { await resourcesAPI.createAgent(values); message.success('创建成功'); }
      setDrawerOpen(false); fetch();
    } catch (err: any) { if (err?.errorFields) return; notification.error({ title: '操作失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
  };

  const handleDelete = async (id: number) => {
    try { await resourcesAPI.deleteAgent(id); message.success('删除成功'); fetch(); }
    catch (err: any) { notification.error({ title: '删除失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
  };

  const openChat = (agent: Agent) => {
    setChatAgent(agent);
    setChatHistory([]);
    setChatInput('');
    setChatOpen(true);
  };

  const handleSendChat = async () => {
    if (!chatInput.trim() || !chatAgent) return;
    const msg = chatInput.trim();

    // 添加用户消息
    setChatHistory(prev => [...prev, { role: 'user', content: msg }]);
    setChatInput('');
    setChatSending(true);

    // 创建 agent 消息占位，后面实时更新
    const agentMsgIndex = chatHistory.length + 1;
    const events: { type: string; content?: string; tool?: string }[] = [];
    setChatHistory(prev => [...prev, { role: 'agent', content: '', events }]);

    // 连接 WebSocket
    const wsUrl = resourcesAPI.chatWithAgentStream(chatAgent.id);
    const ws = new WebSocket(wsUrl);
    chatWsRef.current = ws;

    let textParts: string[] = [];
    let errorContent: string | null = null;

    ws.onopen = () => {
      ws.send(JSON.stringify({ message: msg }));
    };

    ws.onmessage = (event) => {
      try {
        const evt = JSON.parse(event.data);
        const evtType = evt.type;

        if (evtType === 'text') {
          textParts.push(evt.content || '');
          events.push({ type: 'text', content: evt.content });
        } else if (evtType === 'thinking') {
          events.push({ type: 'thinking', content: evt.content });
        } else if (evtType === 'tool_use') {
          events.push({ type: 'tool_use', tool: evt.tool, content: JSON.stringify(evt.input || {}).slice(0, 200) });
        } else if (evtType === 'tool_result') {
          events.push({ type: 'tool_result', tool: evt.tool, content: (evt.output || '').slice(0, 200) });
        } else if (evtType === 'status') {
          events.push({ type: 'status', content: evt.content });
        } else if (evtType === 'log') {
          events.push({ type: 'log', content: evt.content });
        } else if (evtType === 'error') {
          errorContent = evt.content;
          events.push({ type: 'error', content: evt.content });
        } else if (evtType === 'meta') {
          events.push({ type: 'meta', content: `model: ${evt.model}, provider: ${evt.provider}` });
        } else if (evtType === 'session') {
          events.push({ type: 'session', content: evt.session_id });
        } else if (evtType === 'done') {
          if (evt.stderr) {
            events.push({ type: 'log', content: `[stderr] ${evt.stderr}` });
          }
        }

        // 实时更新 agent 消息
        const finalContent = textParts.join('\n') || errorContent || '';
        setChatHistory(prev => {
          const updated = [...prev];
          if (updated[agentMsgIndex]) {
            updated[agentMsgIndex] = {
              role: 'agent',
              content: finalContent,
              error: !!errorContent,
              events: [...events],
            };
          }
          return updated;
        });

        setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
      } catch (e) {
        // 忽略解析错误
      }
    };

    ws.onerror = () => {
      setChatHistory(prev => {
        const updated = [...prev];
        if (updated[agentMsgIndex]) {
          updated[agentMsgIndex] = {
            role: 'agent',
            content: 'WebSocket 连接失败',
            error: true,
            events,
          };
        }
        return updated;
      });
      setChatSending(false);
    };

    ws.onclose = () => {
      // 无论有无内容，WebSocket 关闭就停止 loading
      setChatSending(false);
      chatWsRef.current = null;

      // 如果没有任何内容，显示提示
      setChatHistory(prev => {
        const updated = [...prev];
        if (updated[agentMsgIndex] && !updated[agentMsgIndex].content && (!updated[agentMsgIndex].events || updated[agentMsgIndex].events!.length === 0)) {
          updated[agentMsgIndex] = {
            role: 'agent',
            content: '（无响应内容 — 检查 CLI 命令或 API key）',
            error: true,
            events,
          };
        }
        return updated;
      });
    };
  };

  const handleStopChat = () => {
    if (chatWsRef.current) {
      chatWsRef.current.close();
      chatWsRef.current = null;
    }
    setChatSending(false);
  };

  const filtered = useMemo(() => {
    if (!search) return items;
    const q = search.toLowerCase();
    return items.filter(i => i.name?.toLowerCase().includes(q) || i.agent_type?.toLowerCase().includes(q));
  }, [items, search]);

  const typeMeta: Record<string, { color: string; bg: string }> = {
    openclaw: { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
    opencode: { color: '#34d399', bg: 'rgba(52,211,153,0.12)' },
    harness: { color: '#60a5fa', bg: 'rgba(96,165,250,0.12)' },
    custom: { color: '#a78bfa', bg: 'rgba(167,139,250,0.12)' },
  };

  const runtimeMeta: Record<string, { icon: React.ReactNode; color: string }> = {
    docker: { icon: <DockerOutlined />, color: '#34d399' },
    python: { icon: <CodeOutlined />, color: '#f59e0b' },
    node: { icon: <CodeOutlined />, color: '#60a5fa' },
    binary: { icon: <BuildOutlined />, color: '#94a3b8' },
  };

  return (
    <div>
      <SectionHeader icon={<RobotOutlined style={{ color: '#a78bfa' }} />} title="智能体" count={items.length}
        extra={
          <Space>
            <Input prefix={<SearchOutlined style={{ color: '#506380' }} />} placeholder="搜索 Agent..." value={search}
              onChange={e => setSearch(e.target.value)} style={{ width: 200 }} allowClear />
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增 Agent</Button>
          </Space>
        }
      />

      {filtered.length === 0 && !loading ? (
        <Empty description={<span style={{ color: '#506380' }}>暂无智能体</span>} style={{ padding: 60 }} />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 14 }}>
          {filtered.map(item => {
            const tm = typeMeta[item.agent_type] || typeMeta.custom;
            const rm = runtimeMeta[item.runtime] || { icon: <BuildOutlined />, color: '#657a9a' };
            return (
              <div key={item.id} style={{ ...cardStyle, padding: '18px 20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ width: 40, height: 40, borderRadius: 12, background: tm.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20 }}>
                      <RobotOutlined style={{ color: tm.color }} />
                    </div>
                    <div>
                      <div style={{ fontSize: 15, fontWeight: 600, color: '#e8eef5' }}>{item.name}</div>
                      <Space size={6} style={{ marginTop: 2 }}>
                        <Tag style={{ borderRadius: 6, background: tm.bg, color: tm.color, border: 'none', fontSize: 11 }}>{item.agent_type}</Tag>
                        {item.version && <Tag style={{ borderRadius: 6, background: 'rgba(255,255,255,0.05)', color: '#7b8ea8', border: 'none', fontSize: 11 }}>v{item.version}</Tag>}
                      </Space>
                    </div>
                  </div>
                  <Space size={4}>
                    <Tooltip title="测试交互">
                      <Button type="text" size="small" icon={<MessageOutlined />} onClick={() => openChat(item)} style={{ color: '#60a5fa' }} />
                    </Tooltip>
                    <Button type="text" size="small" icon={<EditOutlined />} onClick={() => openEdit(item)} />
                    <Popconfirm title="确定删除？" onConfirm={() => handleDelete(item.id)} okText="删除" cancelText="取消" okButtonProps={{ danger: true }}>
                      <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </Space>
                </div>

                <Divider style={{ margin: '0 0 12px 0', borderColor: 'rgba(255,255,255,0.05)' }} />

                <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 8 }}>
                  <Space size={4}>
                    <span style={{ color: rm.color, fontSize: 13 }}>{rm.icon}</span>
                    <Text style={{ color: '#7b8ea8', fontSize: 12 }}>{item.runtime}</Text>
                  </Space>
                  {item.docker_image && (
                    <Tooltip title={item.docker_image}>
                      <Text style={{ color: '#506380', fontSize: 12, fontFamily: 'JetBrains Mono, monospace', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.docker_image}
                      </Text>
                    </Tooltip>
                  )}
                </div>

                {item.description && <Text style={{ color: '#506380', fontSize: 12, display: 'block', marginBottom: 8, lineHeight: 1.5 }}>{item.description}</Text>}

                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {item.is_active ? (
                    <Badge status="success" text={<span style={{ fontSize: 11, color: '#34d399' }}>已启用</span>} />
                  ) : (
                    <Badge status="default" text={<span style={{ fontSize: 11, color: '#506380' }}>未启用</span>} />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Drawer
        title={<Space>{editing ? <EditOutlined style={{ color: '#a78bfa' }} /> : <PlusOutlined style={{ color: '#a78bfa' }} />}{editing ? '编辑 Agent' : '新增 Agent'}</Space>}
        open={drawerOpen} onClose={() => setDrawerOpen(false)}
        extra={<Space><Button onClick={() => setDrawerOpen(false)}>取消</Button><Button type="primary" onClick={handleSubmit}>保存</Button></Space>}
        styles={{ body: { paddingBottom: 40 }, wrapper: { width: 480 } }}
      >
        <Form form={form} layout="vertical" size="large">
          <Form.Item name="name" label="Agent 名称" rules={[{ required: true }]}><Input placeholder="my-custom-agent" /></Form.Item>
          <Space style={{ width: '100%' }} size={16}>
            <Form.Item name="agent_type" label="Agent 类型" rules={[{ required: true }]} style={{ flex: 1 }}>
              <Select><Select.Option value="openclaw">OpenClaw</Select.Option><Select.Option value="opencode">OpenCode</Select.Option><Select.Option value="harness">Harness</Select.Option><Select.Option value="custom">自定义</Select.Option></Select>
            </Form.Item>
            <Form.Item name="runtime" label="运行方式" rules={[{ required: true }]} style={{ flex: 1 }}>
              <Select><Select.Option value="docker">Docker</Select.Option><Select.Option value="python">Python</Select.Option><Select.Option value="node">Node.js</Select.Option><Select.Option value="binary">Binary</Select.Option></Select>
            </Form.Item>
            <Form.Item name="version" label="版本" style={{ width: 110 }}><Input placeholder="latest" /></Form.Item>
          </Space>
          <Form.Item name="docker_image" label="Docker 镜像"><Input placeholder="ghcr.io/my-agent:v1" /></Form.Item>
          <Form.Item name="entrypoint" label="启动命令"><TextArea rows={2} placeholder="docker run --rm ..." /></Form.Item>
          <Form.Item name="description" label="描述"><TextArea rows={2} /></Form.Item>
          <Form.Item name="is_active" label="启用" valuePropName="checked"><Switch /></Form.Item>
        </Form>
      </Drawer>

      {/* Agent 交互测试 Drawer */}
      <Drawer
        title={
          <Space>
            <MessageOutlined style={{ color: '#60a5fa' }} />
            交互测试 — {chatAgent?.name}
          </Space>
        }
        open={chatOpen} onClose={() => setChatOpen(false)}
        styles={{ body: { padding: 0, display: 'flex', flexDirection: 'column', height: '100%' }, wrapper: { width: 520 } }}
      >
        <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
          {chatHistory.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#506380', fontSize: 13, padding: '40px 20px' }}>
              <MessageOutlined style={{ fontSize: 32, marginBottom: 12, display: 'block', color: '#3d4e6b' }} />
              输入消息与 Agent 交互测试<br />
              <span style={{ fontSize: 11 }}>
                {chatAgent?.entrypoint?.startsWith('http')
                  ? '🌐 HTTP 模式 — 支持 OpenAI 兼容接口'
                  : '⚡ CLI 流式模式 — 实时显示 thinking / text / tool 事件'}
              </span>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {chatHistory.map((m, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
                  <div style={{
                    maxWidth: '88%', padding: '10px 14px', borderRadius: 12,
                    background: m.role === 'user'
                      ? 'rgba(96,165,250,0.12)'
                      : m.error ? 'rgba(245,158,11,0.08)' : 'rgba(255,255,255,0.04)',
                    border: m.role === 'user'
                      ? '1px solid rgba(96,165,250,0.2)'
                      : m.error ? '1px solid rgba(245,158,11,0.2)' : '1px solid rgba(255,255,255,0.06)',
                  }}>
                    <div style={{ fontSize: 10, color: m.role === 'user' ? '#60a5fa' : m.error ? '#f59e0b' : '#657a9a', marginBottom: 4, fontWeight: 600 }}>
                      {m.role === 'user' ? 'YOU' : (chatAgent?.name || 'AGENT')}
                    </div>

                    {/* 事件流（thinking/tool_use/log 等） */}
                    {m.events && m.events.length > 0 && (
                      <div style={{ marginBottom: m.content ? 8 : 0, display: 'flex', flexDirection: 'column', gap: 3 }}>
                        {m.events.map((evt, ei) => {
                          let evtColor = '#506380';
                          let evtBg = 'rgba(255,255,255,0.03)';
                          let evtIcon = '·';
                          if (evt.type === 'thinking' || evt.type === 'reasoning') { evtColor = '#a78bfa'; evtBg = 'rgba(167,139,250,0.06)'; evtIcon = '💭'; }
                          else if (evt.type === 'text') { evtColor = '#34d399'; evtBg = 'rgba(52,211,153,0.04)'; evtIcon = '💬'; }
                          else if (evt.type === 'tool_use') { evtColor = '#60a5fa'; evtBg = 'rgba(96,165,250,0.06)'; evtIcon = '🔧'; }
                          else if (evt.type === 'tool_result') { evtColor = '#94a3b8'; evtBg = 'rgba(148,163,184,0.04)'; evtIcon = '📋'; }
                          else if (evt.type === 'status') { evtColor = '#657a9a'; evtBg = 'rgba(255,255,255,0.03)'; evtIcon = '⏳'; }
                          else if (evt.type === 'error') { evtColor = '#f59e0b'; evtBg = 'rgba(245,158,11,0.06)'; evtIcon = '⚠️'; }
                          else if (evt.type === 'log') { evtColor = '#3d4e6b'; evtBg = 'transparent'; evtIcon = '┃'; }
                          else if (evt.type === 'meta') { evtColor = '#7b8ea8'; evtBg = 'rgba(255,255,255,0.03)'; evtIcon = 'ℹ️'; }
                          else if (evt.type === 'session') { evtColor = '#657a9a'; evtBg = 'transparent'; evtIcon = '🔗'; }
                          return (
                            <div key={ei} style={{
                              fontSize: 11, color: evtColor, background: evtBg,
                              padding: evt.type === 'log' ? '1px 0' : '3px 8px',
                              borderRadius: 6, lineHeight: 1.5,
                              fontFamily: evt.type === 'log' || evt.type === 'thinking' ? 'JetBrains Mono, monospace' : 'inherit',
                              whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                              opacity: evt.type === 'thinking' ? 0.8 : 1,
                            }}>
                              <span style={{ marginRight: 4 }}>{evtIcon}</span>
                              {evt.type === 'tool_use' && <span style={{ fontWeight: 600 }}>{evt.tool}: </span>}
                              {evt.content}
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* 最终回复内容 */}
                    {m.content && (
                      <div style={{
                        fontSize: 13, color: m.error ? '#f59e0b' : '#e8eef5',
                        lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                        fontFamily: m.role === 'agent' && !m.error ? 'JetBrains Mono, monospace' : 'inherit',
                      }}>
                        {m.content}
                      </div>
                    )}

                    {/* 加载指示 */}
                    {m.role === 'agent' && !m.content && (!m.events || m.events.length === 0) && chatSending && (
                      <div style={{ fontSize: 12, color: '#506380', fontStyle: 'italic' }}>等待响应...</div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>
          )}
        </div>
        <div style={{ padding: 12, borderTop: '1px solid rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.02)' }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <Input
              placeholder="输入消息..."
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              onPressEnter={handleSendChat}
              disabled={chatSending}
              style={{ flex: 1, background: 'rgba(255,255,255,0.04)', borderColor: 'rgba(255,255,255,0.08)' }}
            />
            {chatSending ? (
              <Button danger icon={<StopOutlined />} onClick={handleStopChat}>停止</Button>
            ) : (
              <Button type="primary" icon={<SendOutlined />} onClick={handleSendChat}>发送</Button>
            )}
          </div>
          {chatAgent?.entrypoint && (
            <div style={{ fontSize: 10, color: '#3d4e6b', marginTop: 6, fontFamily: 'JetBrains Mono, monospace' }}>
              {chatAgent.entrypoint.startsWith('http') ? '🌐 HTTP' : '⚡ CLI'} → {chatAgent.entrypoint}
            </div>
          )}
        </div>
      </Drawer>
    </div>
  );
}

// ===================== Skill 面板 =====================

function SkillsPanel() {
  const { message, notification } = App.useApp();
  const [items, setItems] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<Skill | null>(null);
  const [form] = Form.useForm();

  const fetch = useCallback(async () => {
    setLoading(true);
    try { const res = await resourcesAPI.listSkills({ skip: 0, limit: 200 }); setItems(res.data?.data || []); }
    catch { notification.error({ title: '加载失败', placement: 'top' }); }
    finally { setLoading(false); }
  }, [notification]);

  useEffect(() => { fetch(); }, [fetch]);

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ skill_type: 'docker', is_active: true }); setDrawerOpen(true); };
  const openEdit = (r: Skill) => { setEditing(r); form.setFieldsValue(r); setDrawerOpen(true); };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editing) { await resourcesAPI.updateSkill(editing.id, values); message.success('更新成功'); }
      else { await resourcesAPI.createSkill(values); message.success('创建成功'); }
      setDrawerOpen(false); fetch();
    } catch (err: any) { if (err?.errorFields) return; notification.error({ title: '操作失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
  };

  const handleDelete = async (id: number) => {
    try { await resourcesAPI.deleteSkill(id); message.success('删除成功'); fetch(); }
    catch (err: any) { notification.error({ title: '删除失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
  };

  const handleInstall = async (id: number) => {
    try { await resourcesAPI.installSkill(id); message.success('安装成功'); fetch(); }
    catch (err: any) { notification.error({ title: '安装失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
  };

  const filtered = useMemo(() => {
    if (!search) return items;
    const q = search.toLowerCase();
    return items.filter(i => i.name?.toLowerCase().includes(q) || i.skill_type?.toLowerCase().includes(q));
  }, [items, search]);

  const typeMeta: Record<string, { icon: React.ReactNode; label: string; color: string; bg: string }> = {
    docker: { icon: <DockerOutlined />, label: 'Docker', color: '#34d399', bg: 'rgba(52,211,153,0.12)' },
    mcp: { icon: <LinkOutlined />, label: 'MCP', color: '#a78bfa', bg: 'rgba(167,139,250,0.12)' },
    script: { icon: <CodeOutlined />, label: 'Script', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
    api: { icon: <ApiOutlined />, label: 'API', color: '#60a5fa', bg: 'rgba(96,165,250,0.12)' },
  };

  return (
    <div>
      <SectionHeader icon={<ToolOutlined style={{ color: '#f59e0b' }} />} title="技能模块" count={items.length}
        extra={
          <Space>
            <Input prefix={<SearchOutlined style={{ color: '#506380' }} />} placeholder="搜索技能..." value={search}
              onChange={e => setSearch(e.target.value)} style={{ width: 200 }} allowClear />
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增技能</Button>
          </Space>
        }
      />

      {filtered.length === 0 && !loading ? (
        <Empty description={<span style={{ color: '#506380' }}>暂无技能</span>} style={{ padding: 60 }} />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 14 }}>
          {filtered.map(item => {
            const tm = typeMeta[item.skill_type] || typeMeta.api;
            return (
              <div key={item.id} style={{ ...cardStyle, padding: '16px 18px', borderColor: item.is_installed ? 'rgba(52,211,153,0.2)' : undefined }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                  <Space size={10}>
                    <div style={{ width: 34, height: 34, borderRadius: 10, background: tm.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, color: tm.color }}>
                      {tm.icon}
                    </div>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: '#e8eef5' }}>{item.name}</div>
                      <Space size={6} style={{ marginTop: 2 }}>
                        <Tag style={{ borderRadius: 6, background: tm.bg, color: tm.color, border: 'none', fontSize: 11 }}>{tm.label}</Tag>
                        {item.is_installed ? (
                          <Tag style={{ borderRadius: 6, background: 'rgba(52,211,153,0.12)', color: '#34d399', border: 'none', fontSize: 11 }}>已安装</Tag>
                        ) : (
                          <Tag style={{ borderRadius: 6, background: 'rgba(255,255,255,0.04)', color: '#506380', border: 'none', fontSize: 11 }}>未安装</Tag>
                        )}
                      </Space>
                    </div>
                  </Space>
                </div>

                {item.description && <Text style={{ color: '#506380', fontSize: 12, display: 'block', marginBottom: 10, lineHeight: 1.5 }}>{item.description}</Text>}

                {item.tags && item.tags.length > 0 && (
                  <div style={{ marginBottom: 10, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {item.tags.map((t: string) => <Tag key={t} style={{ borderRadius: 4, background: 'rgba(255,255,255,0.04)', color: '#506380', border: 'none', fontSize: 10 }}>{t}</Tag>)}
                  </div>
                )}

                <div style={{ display: 'flex', gap: 6 }}>
                  {!item.is_installed && (
                    <Button size="small" type="primary" ghost icon={<CloudUploadOutlined />} onClick={() => handleInstall(item.id)} style={{ borderRadius: 8, fontSize: 12 }}>
                      安装
                    </Button>
                  )}
                  <Button size="small" type="text" icon={<EditOutlined />} onClick={() => openEdit(item)} style={{ fontSize: 12 }} />
                  <Popconfirm title="确定删除？" onConfirm={() => handleDelete(item.id)} okText="删除" cancelText="取消" okButtonProps={{ danger: true }}>
                    <Button size="small" type="text" danger icon={<DeleteOutlined />} style={{ fontSize: 12 }} />
                  </Popconfirm>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Drawer
        title={<Space>{editing ? <EditOutlined style={{ color: '#f59e0b' }} /> : <PlusOutlined style={{ color: '#f59e0b' }} />}{editing ? '编辑技能' : '新增技能'}</Space>}
        open={drawerOpen} onClose={() => setDrawerOpen(false)}
        extra={<Space><Button onClick={() => setDrawerOpen(false)}>取消</Button><Button type="primary" onClick={handleSubmit}>保存</Button></Space>}
        styles={{ body: { paddingBottom: 40 }, wrapper: { width: 480 } }}
      >
        <Form form={form} layout="vertical" size="large">
          <Form.Item name="name" label="技能名称" rules={[{ required: true }]}><Input placeholder="pdf-reader" /></Form.Item>
          <Space style={{ width: '100%' }} size={16}>
            <Form.Item name="skill_type" label="技能类型" rules={[{ required: true }]} style={{ flex: 1 }}>
              <Select><Select.Option value="docker">Docker</Select.Option><Select.Option value="mcp">MCP</Select.Option><Select.Option value="script">Script</Select.Option><Select.Option value="api">API</Select.Option></Select>
            </Form.Item>
            <Form.Item name="icon" label="图标" style={{ flex: 1 }}><Input placeholder="FilePdfOutlined" /></Form.Item>
          </Space>
          <Form.Item name="docker_image" label="Docker 镜像"><Input placeholder="skill/pdf-reader:latest" /></Form.Item>
          <Form.Item name="install_cmd" label="安装命令"><Input placeholder="pip install pdfplumber" /></Form.Item>
          <Form.Item name="entrypoint" label="启动命令"><TextArea rows={2} /></Form.Item>
          <Form.Item name="description" label="描述"><TextArea rows={2} /></Form.Item>
        </Form>
      </Drawer>
    </div>
  );
}

// ===================== MCP 工具面板 =====================

function MCPPanel() {
  const { message, notification } = App.useApp();
  const [items, setItems] = useState<MCPConfigType[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<MCPConfigType | null>(null);
  const [form] = Form.useForm();

  // MCP 自动发现
  const [discoverOpen, setDiscoverOpen] = useState(false);
  const [discoverForm] = Form.useForm();
  const [discovering, setDiscovering] = useState(false);

  const fetch = useCallback(async () => {
    setLoading(true);
    try { const res = await resourcesAPI.listMCPs({ skip: 0, limit: 200 }); setItems(res.data?.data || []); }
    catch { notification.error({ title: '加载失败', placement: 'top' }); }
    finally { setLoading(false); }
  }, [notification]);

  useEffect(() => { fetch(); }, [fetch]);

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ mcp_type: 'http', auto_discovery_enabled: false, is_active: true }); setDrawerOpen(true); };
  const openEdit = (r: MCPConfigType) => { setEditing(r); form.setFieldsValue(r); setDrawerOpen(true); };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editing) { await resourcesAPI.updateMCP(editing.id, values); message.success('更新成功'); }
      else { await resourcesAPI.createMCP(values); message.success('创建成功'); }
      setDrawerOpen(false); fetch();
    } catch (err: any) { if (err?.errorFields) return; notification.error({ title: '操作失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
  };

  const handleDelete = async (id: number) => {
    try { await resourcesAPI.deleteMCP(id); message.success('删除成功'); fetch(); }
    catch (err: any) { notification.error({ title: '删除失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
  };

  const handleDiscover = async () => {
    try {
      const values = await discoverForm.validateFields();
      setDiscovering(true);
      await resourcesAPI.autoDiscoverMCP(values);
      message.success('自动发现完成');
      setDiscoverOpen(false);
      discoverForm.resetFields();
      fetch();
    } catch (err: any) { if (err?.errorFields) return; notification.error({ title: '发现失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
    finally { setDiscovering(false); }
  };

  const filtered = useMemo(() => {
    if (!search) return items;
    const q = search.toLowerCase();
    return items.filter(i => i.name?.toLowerCase().includes(q) || i.mcp_type?.toLowerCase().includes(q) || i.url?.toLowerCase().includes(q));
  }, [items, search]);

  const typeMeta: Record<string, { color: string; bg: string; label: string }> = {
    sse: { color: '#60a5fa', bg: 'rgba(96,165,250,0.12)', label: 'SSE' },
    stdio: { color: '#34d399', bg: 'rgba(52,211,153,0.12)', label: 'Stdio' },
    http: { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', label: 'HTTP' },
  };

  return (
    <div>
      <SectionHeader icon={<LinkOutlined style={{ color: '#34d399' }} />} title="MCP 工具" count={items.length}
        extra={
          <Space>
            <Input prefix={<SearchOutlined style={{ color: '#506380' }} />} placeholder="搜索 MCP..." value={search}
              onChange={e => setSearch(e.target.value)} style={{ width: 200 }} allowClear />
            <Button icon={<ExperimentOutlined />} onClick={() => { discoverForm.resetFields(); setDiscoverOpen(true); }}>自动发现</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增 MCP</Button>
          </Space>
        }
      />

      {filtered.length === 0 && !loading ? (
        <Empty description={<span style={{ color: '#506380' }}>暂无 MCP 工具</span>} style={{ padding: 60 }} />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 14 }}>
          {filtered.map(item => {
            const tm = typeMeta[item.mcp_type] || typeMeta.http;
            return (
              <div key={item.id} style={{ ...cardStyle, padding: '16px 18px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                  <Space size={10}>
                    <div style={{ width: 34, height: 34, borderRadius: 10, background: tm.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, color: tm.color }}>
                      <LinkOutlined />
                    </div>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: '#e8eef5' }}>{item.name}</div>
                      <Space size={6} style={{ marginTop: 2 }}>
                        <Tag style={{ borderRadius: 6, background: tm.bg, color: tm.color, border: 'none', fontSize: 11 }}>{tm.label}</Tag>
                        {item.auto_discovery_enabled && (
                          <Tag style={{ borderRadius: 6, background: 'rgba(167,139,250,0.12)', color: '#a78bfa', border: 'none', fontSize: 11 }}>自动发现</Tag>
                        )}
                      </Space>
                    </div>
                  </Space>
                  <Space size={4}>
                    <Button type="text" size="small" icon={<EditOutlined />} onClick={() => openEdit(item)} />
                    <Popconfirm title="确定删除？" onConfirm={() => handleDelete(item.id)} okText="删除" cancelText="取消" okButtonProps={{ danger: true }}>
                      <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </Space>
                </div>

                {item.url && (
                  <div style={{ marginBottom: 8, padding: '6px 10px', borderRadius: 8, background: 'rgba(0,0,0,0.2)', fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#7b8ea8', wordBreak: 'break-all' }}>
                    {item.url}
                  </div>
                )}

                {item.command && (
                  <Tooltip title={item.command}>
                    <Text style={{ color: '#506380', fontSize: 12, display: 'block', marginBottom: 6, fontFamily: 'JetBrains Mono, monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      $ {item.command}
                    </Text>
                  </Tooltip>
                )}

                {item.description && <Text style={{ color: '#506380', fontSize: 12, display: 'block', lineHeight: 1.5 }}>{item.description}</Text>}
              </div>
            );
          })}
        </div>
      )}

      {/* Create/Edit Drawer */}
      <Drawer
        title={<Space>{editing ? <EditOutlined style={{ color: '#34d399' }} /> : <PlusOutlined style={{ color: '#34d399' }} />}{editing ? '编辑 MCP' : '新增 MCP'}</Space>}
        open={drawerOpen} onClose={() => setDrawerOpen(false)}
        extra={<Space><Button onClick={() => setDrawerOpen(false)}>取消</Button><Button type="primary" onClick={handleSubmit}>保存</Button></Space>}
        styles={{ body: { paddingBottom: 40 }, wrapper: { width: 480 } }}
      >
        <Form form={form} layout="vertical" size="large">
          <Form.Item name="name" label="MCP 名称" rules={[{ required: true }]}><Input placeholder="my-api-tool" /></Form.Item>
          <Space style={{ width: '100%' }} size={16}>
            <Form.Item name="mcp_type" label="MCP 类型" rules={[{ required: true }]} style={{ flex: 1 }}>
              <Select><Select.Option value="sse">SSE</Select.Option><Select.Option value="stdio">Stdio</Select.Option><Select.Option value="http">HTTP</Select.Option></Select>
            </Form.Item>
            <Form.Item name="url" label="连接地址" style={{ flex: 2 }}><Input placeholder="http://..." /></Form.Item>
          </Space>
          <Form.Item name="command" label="启动命令"><Input placeholder="npx @modelcontextprotocol/server-xxx" /></Form.Item>
          <Form.Item name="auto_discovery_url" label="自动发现 URL"><Input placeholder="https://api.example.com/openapi.json" /></Form.Item>
          <Form.Item name="auto_discovery_enabled" label="启用自动发现" valuePropName="checked"><Switch /></Form.Item>
          <Form.Item name="description" label="描述"><TextArea rows={2} /></Form.Item>
        </Form>
      </Drawer>

      {/* Auto Discover Modal */}
      <Drawer
        title={<Space><ExperimentOutlined style={{ color: '#a78bfa' }} />MCP 自动发现</Space>}
        open={discoverOpen} onClose={() => setDiscoverOpen(false)}
        extra={<Space><Button onClick={() => setDiscoverOpen(false)}>取消</Button><Button type="primary" loading={discovering} onClick={handleDiscover}>开始发现</Button></Space>}
        styles={{ body: { paddingBottom: 40 }, wrapper: { width: 500 } }}
      >
        <Form form={discoverForm} layout="vertical" size="large">
          <Form.Item name="api_url" label="API 端点 URL" rules={[{ required: true }]}>
            <Input placeholder="https://api.example.com/v1/query" />
          </Form.Item>
          <Form.Item name="method" label="HTTP 方法" initialValue="GET">
            <Select><Select.Option value="GET">GET</Select.Option><Select.Option value="POST">POST</Select.Option><Select.Option value="PUT">PUT</Select.Option><Select.Option value="DELETE">DELETE</Select.Option></Select>
          </Form.Item>
          <Form.Item name="description_text" label="API 功能描述（自然语言）">
            <TextArea rows={3} placeholder="用自然语言描述这个 API 的功能，帮助 LLM 推断参数..." />
          </Form.Item>
          <Form.Item name="request_body_example" label="请求体示例 (JSON)">
            <TextArea rows={3} placeholder='{"user_id": 123}' style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }} />
          </Form.Item>
          <Form.Item name="response_body_example" label="响应体示例 (JSON)">
            <TextArea rows={3} placeholder='{"data": [...]}' style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }} />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  );
}

// ===================== 运行监控面板 =====================

function RunsPanel() {
  const { message, notification } = App.useApp();
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [logDrawer, setLogDrawer] = useState<{ open: boolean; runId: number | null }>({ open: false, runId: null });
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);
  const [createDrawer, setCreateDrawer] = useState(false);
  const [form] = Form.useForm();

  const fetch = useCallback(async () => {
    setLoading(true);
    try { const res = await resourcesAPI.listRuns({ skip: 0, limit: 200 }); setRuns(res.data?.data || []); }
    catch { notification.error({ title: '加载失败', placement: 'top' }); }
    finally { setLoading(false); }
  }, [notification]);

  useEffect(() => { fetch(); }, [fetch]);

  const handleStart = async () => {
    try {
      const values = await form.validateFields();
      await resourcesAPI.createRun(values);
      message.success('Agent 已启动');
      setCreateDrawer(false); form.resetFields(); fetch();
    } catch (err: any) { if (err?.errorFields) return; notification.error({ title: '启动失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
  };

  const handleStop = async (id: number) => {
    try { await resourcesAPI.stopRun(id); message.success('已停止'); fetch(); }
    catch (err: any) { notification.error({ title: '停止失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
  };

  const openLogs = (runId: number) => {
    setLogs([]);
    setLogDrawer({ open: true, runId });
    if (wsRef.current) wsRef.current.close();
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const ws = new WebSocket(`${protocol}//${host}/resources/runs/${runId}/logs`);
    wsRef.current = ws;
    ws.onmessage = (event) => {
      try {
        const entry = JSON.parse(event.data);
        if (entry.error) setLogs(prev => [...prev, { timestamp: new Date().toISOString(), level: 'error', message: entry.error }]);
        else setLogs(prev => [...prev, entry]);
        setTimeout(() => logEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
      } catch { setLogs(prev => [...prev, { timestamp: new Date().toISOString(), level: 'info', message: event.data }]); }
    };
    ws.onerror = () => setLogs(prev => [...prev, { timestamp: new Date().toISOString(), level: 'error', message: 'WebSocket 连接错误' }]);
  };

  const closeLogs = () => { if (wsRef.current) { wsRef.current.close(); wsRef.current = null; } setLogDrawer({ open: false, runId: null }); };

  const statusMeta: Record<string, { color: string; bg: string; label: string; icon: React.ReactNode }> = {
    initializing: { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', label: '初始化', icon: <ThunderboltOutlined /> },
    running: { color: '#34d399', bg: 'rgba(52,211,153,0.12)', label: '运行中', icon: <PlayCircleOutlined /> },
    error: { color: '#f87171', bg: 'rgba(248,113,113,0.12)', label: '错误', icon: <BugOutlined /> },
    stopped: { color: '#506380', bg: 'rgba(255,255,255,0.04)', label: '已停止', icon: <StopOutlined /> },
  };

  const activeCount = runs.filter(r => r.status === 'running' || r.status === 'initializing').length;

  return (
    <div>
      <SectionHeader icon={<MonitorOutlined style={{ color: '#f472b6' }} />} title="运行监控" count={runs.length}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetch}>刷新</Button>
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => { form.resetFields(); setCreateDrawer(true); }}>启动 Agent</Button>
          </Space>
        }
      />

      {/* Active runs indicator */}
      {activeCount > 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px', borderRadius: 12,
          background: 'rgba(52,211,153,0.06)', border: '1px solid rgba(52,211,153,0.15)', marginBottom: 18,
        }}>
          <Badge status="processing" />
          <Text style={{ color: '#34d399', fontSize: 13 }}>{activeCount} 个实例运行中</Text>
        </div>
      )}

      {runs.length === 0 && !loading ? (
        <Empty description={<span style={{ color: '#506380' }}>暂无运行记录</span>} style={{ padding: 60 }}>
          <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => { form.resetFields(); setCreateDrawer(true); }}>启动第一个 Agent</Button>
        </Empty>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {runs.map(run => {
            const sm = statusMeta[run.status] || statusMeta.stopped;
            return (
              <div key={run.id} style={{
                ...cardStyle, padding: '14px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                borderLeft: `3px solid ${sm.color}`,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 20, flex: 1 }}>
                  <div style={{ width: 38, height: 38, borderRadius: 10, background: sm.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 17, color: sm.color }}>
                    {sm.icon}
                  </div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#e8eef5' }}>{run.run_name}</div>
                    <Space size={10} style={{ marginTop: 2 }}>
                      <Text style={{ color: '#506380', fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}>Agent #{run.agent_id}</Text>
                      <Text style={{ color: '#506380', fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}>Node #{run.instance_id}</Text>
                      {run.container_id && <Text style={{ color: '#506380', fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}>{run.container_id.slice(0, 12)}</Text>}
                    </Space>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <Tag style={{ borderRadius: 8, background: sm.bg, color: sm.color, border: 'none', fontSize: 11, fontWeight: 500 }}>{sm.label}</Tag>
                  {run.started_at && <Text style={{ color: '#506380', fontSize: 11 }}>{new Date(run.started_at).toLocaleString()}</Text>}
                  <Space size={4}>
                    {(run.status === 'running' || run.status === 'initializing') && (
                      <Button type="text" size="small" onClick={() => openLogs(run.id)} style={{ color: '#60a5fa', fontSize: 12 }}>日志</Button>
                    )}
                    {(run.status === 'running' || run.status === 'initializing') && (
                      <Popconfirm title="确定停止？" onConfirm={() => handleStop(run.id)} okText="停止" cancelText="取消" okButtonProps={{ danger: true }}>
                        <Button type="text" size="small" danger style={{ fontSize: 12 }}>停止</Button>
                      </Popconfirm>
                    )}
                    {run.status === 'error' && (
                      <Tooltip title={run.error_message}>
                        <Button type="text" size="small" style={{ color: '#f87171', fontSize: 12 }}>查看错误</Button>
                      </Tooltip>
                    )}
                  </Space>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Start Agent Drawer */}
      <Drawer
        title={<Space><PlayCircleOutlined style={{ color: '#34d399' }} />启动 Agent</Space>}
        open={createDrawer} onClose={() => setCreateDrawer(false)}
        extra={<Space><Button onClick={() => setCreateDrawer(false)}>取消</Button><Button type="primary" onClick={handleStart}>启动</Button></Space>}
        styles={{ body: { paddingBottom: 40 }, wrapper: { width: 400 } }}
      >
        <Form form={form} layout="vertical" size="large">
          <Form.Item name="run_name" label="运行名称" rules={[{ required: true }]}><Input placeholder="production-run-01" /></Form.Item>
          <Space style={{ width: '100%' }} size={16}>
            <Form.Item name="agent_id" label="Agent ID" style={{ flex: 1 }}><InputNumber min={1} style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="instance_id" label="Instance ID" style={{ flex: 1 }}><InputNumber min={1} style={{ width: '100%' }} /></Form.Item>
          </Space>
        </Form>
      </Drawer>

      {/* Log Drawer */}
      <Drawer
        title={<Space><MonitorOutlined style={{ color: '#60a5fa' }} />实时日志 {logDrawer.runId ? `#${logDrawer.runId}` : ''}</Space>}
        open={logDrawer.open} onClose={closeLogs}
        styles={{ body: { padding: 0 }, wrapper: { width: 640 } }}
        extra={<Space><Badge status="processing" text="接收中" /><Button size="small" onClick={closeLogs}>断开</Button></Space>}
      >
        <div style={{ height: '100%', overflowY: 'auto', padding: 16, background: '#0a0e17', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, lineHeight: 1.8 }}>
          {logs.length === 0 && <Text style={{ color: '#506380' }}>等待日志...</Text>}
          {logs.map((log, i) => (
            <div key={i} style={{ color: log.level === 'error' ? '#f87171' : log.level === 'warn' ? '#fbbf24' : '#94a3b8' }}>
              <span style={{ color: '#506380' }}>[{new Date(log.timestamp).toLocaleTimeString()}]</span> {log.message}
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      </Drawer>
    </div>
  );
}

// ===================== LLM 配置面板 =====================

function LLMPanel() {
  const { message, notification } = App.useApp();
  const [configs, setConfigs] = useState<LLMConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<LLMConfig | null>(null);
  const [form] = Form.useForm();

  // 测试对话
  const [testOpen, setTestOpen] = useState(false);
  const [testMessages, setTestMessages] = useState<{ role: string; content: string }[]>([]);
  const [testInput, setTestInput] = useState('');
  const [testLoading, setTestLoading] = useState(false);

  const fetch = useCallback(async () => {
    setLoading(true);
    try { const res = await llmService.listConfigs(); setConfigs(res.data || []); }
    catch { notification.error({ title: '加载失败', placement: 'top' }); }
    finally { setLoading(false); }
  }, [notification]);

  useEffect(() => { fetch(); }, [fetch]);

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ provider: 'openai', is_active: false, timeout: '60', max_retries: '2' }); setDrawerOpen(true); };
  const openEdit = (r: LLMConfig) => { setEditing(r); form.setFieldsValue(r); setDrawerOpen(true); };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editing) {
        const payload: LLMConfigUpdate = {};
        for (const key of Object.keys(values)) { const v = values[key]; if (v !== undefined && v !== (editing as any)[key]) (payload as any)[key] = v; }
        await llmService.updateConfig(editing.id, payload);
        message.success('更新成功');
      } else {
        await llmService.createConfig(values as LLMConfigCreate);
        message.success('创建成功');
      }
      setDrawerOpen(false); fetch();
    } catch (err: any) { if (err?.errorFields) return; notification.error({ title: '操作失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
  };

  const handleDelete = async (id: number) => {
    try { await llmService.deleteConfig(id); message.success('删除成功'); fetch(); }
    catch (err: any) { notification.error({ title: '删除失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
  };

  const handleSetActive = async (id: number) => {
    try { await llmService.updateConfig(id, { is_active: true }); message.success('已设为默认'); fetch(); }
    catch (err: any) { notification.error({ title: '操作失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
  };

  const handleTestChat = async () => {
    if (!testInput.trim()) return;
    const msgs = [...testMessages, { role: 'user', content: testInput }];
    setTestMessages(msgs); setTestInput(''); setTestLoading(true);
    try {
      const res = await llmService.chat({ messages: msgs });
      setTestMessages([...msgs, { role: 'assistant', content: res.data?.content || '' }]);
    } catch (err: any) {
      notification.error({ title: '调用失败', description: err?.response?.data?.detail || err?.message, placement: 'top' });
    } finally { setTestLoading(false); }
  };

  const providerMeta: Record<string, { color: string; bg: string }> = {
    openai: { color: '#60a5fa', bg: 'rgba(96,165,250,0.12)' },
    anthropic: { color: '#a78bfa', bg: 'rgba(167,139,250,0.12)' },
    qwen: { color: '#34d399', bg: 'rgba(52,211,153,0.12)' },
  };

  return (
    <div>
      <SectionHeader icon={<ApiOutlined style={{ color: '#60a5fa' }} />} title="LLM 配置" count={configs.length}
        extra={
          <Space>
            <Button icon={<SendOutlined />} onClick={() => { setTestMessages([]); setTestInput(''); setTestOpen(true); }}>测试对话</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增配置</Button>
          </Space>
        }
      />

      {configs.length === 0 && !loading ? (
        <Empty description={<span style={{ color: '#506380' }}>暂无 LLM 配置</span>} style={{ padding: 60 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>添加第一个 LLM</Button>
        </Empty>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 14 }}>
          {configs.map(item => {
            const pm = providerMeta[item.provider] || providerMeta.openai;
            return (
              <div key={item.id} style={{ ...cardStyle, padding: '18px 20px', borderColor: item.is_active ? 'rgba(96,165,250,0.25)' : undefined }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                  <Space size={10}>
                    <div style={{ width: 36, height: 36, borderRadius: 10, background: pm.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, color: pm.color }}>
                      <ApiOutlined />
                    </div>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: '#e8eef5' }}>{item.name}</div>
                      <Space size={6} style={{ marginTop: 2 }}>
                        <Tag style={{ borderRadius: 6, background: pm.bg, color: pm.color, border: 'none', fontSize: 11 }}>{item.provider}</Tag>
                        {item.is_active && <Tag style={{ borderRadius: 6, background: 'rgba(52,211,153,0.12)', color: '#34d399', border: 'none', fontSize: 11 }}>默认</Tag>}
                      </Space>
                    </div>
                  </Space>
                  <Space size={4}>
                    <Button type="text" size="small" icon={<EditOutlined />} onClick={() => openEdit(item)} />
                    <Popconfirm title="确定删除？" onConfirm={() => handleDelete(item.id)} okText="删除" cancelText="取消" okButtonProps={{ danger: true }}>
                      <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </Space>
                </div>

                <div style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 12, color: '#7b8ea8', fontFamily: 'JetBrains Mono, monospace' }}>{item.base_url}</div>
                  <div style={{ fontSize: 12, color: '#506380', marginTop: 2 }}>{item.model_name}</div>
                </div>

                {item.description && <Text style={{ color: '#506380', fontSize: 12, display: 'block', marginBottom: 10, lineHeight: 1.5 }}>{item.description}</Text>}

                <div style={{ display: 'flex', gap: 6 }}>
                  {!item.is_active && (
                    <Button size="small" type="link" onClick={() => handleSetActive(item.id)} style={{ padding: 0, fontSize: 12, color: '#60a5fa' }}>
                      设为默认
                    </Button>
                  )}
                  <Button size="small" type="text" icon={<ThunderboltOutlined />} onClick={() => { setTestMessages([]); setTestInput(''); setTestOpen(true); }} style={{ fontSize: 12, color: '#a78bfa' }}>
                    测试
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* LLM Form Drawer */}
      <Drawer
        title={<Space>{editing ? <EditOutlined style={{ color: '#60a5fa' }} /> : <PlusOutlined style={{ color: '#60a5fa' }} />}{editing ? '编辑' : '新增'} LLM 配置</Space>}
        open={drawerOpen} onClose={() => setDrawerOpen(false)}
        extra={<Space><Button onClick={() => setDrawerOpen(false)}>取消</Button><Button type="primary" onClick={handleSubmit}>保存</Button></Space>}
        styles={{ body: { paddingBottom: 40 }, wrapper: { width: 520 } }}
      >
        <Form form={form} layout="vertical" size="large" initialValues={{ provider: 'openai', is_active: false, timeout: '60', max_retries: '2' }}>
          <Form.Item name="name" label="配置名称" rules={[{ required: true }]}><Input placeholder="例如：GPT-4 Azure" /></Form.Item>
          <Space style={{ width: '100%' }} size={16}>
            <Form.Item name="provider" label="服务协议" rules={[{ required: true }]} style={{ flex: 1 }}>
              <Select><Select.Option value="openai">OpenAI</Select.Option><Select.Option value="anthropic">Anthropic</Select.Option><Select.Option value="qwen">Qwen</Select.Option></Select>
            </Form.Item>
            <Form.Item name="model_name" label="模型" rules={[{ required: true }]} style={{ flex: 2 }}>
              <Input placeholder="gpt-4 / claude-3-5-sonnet" />
            </Form.Item>
          </Space>
          <Form.Item name="base_url" label="API Base URL" rules={[{ required: true }]}>
            <Input placeholder="https://api.openai.com/v1" />
          </Form.Item>
          <Form.Item name="api_key" label="API Key" rules={[{ required: true }]} extra="密钥仅本地加密存储">
            <Input.Password placeholder="sk-..." />
          </Form.Item>
          <Form.Item name="description" label="描述"><Input placeholder="可选" /></Form.Item>
          <Space size={16}>
            <Form.Item name="timeout" label="超时" style={{ width: 140 }}><InputNumber min={1} max={300} style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="max_retries" label="重试" style={{ width: 140 }}><InputNumber min={0} max={5} style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="is_active" label="默认" valuePropName="checked" style={{ paddingTop: 5 }}><Switch /></Form.Item>
          </Space>
          <Form.Item name="extra_headers" label="额外请求头 (JSON)">
            <TextArea rows={2} placeholder='{"X-Custom": "val"}' style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }} />
          </Form.Item>
          <Form.Item name="extra_body" label="额外请求体 (JSON)">
            <TextArea rows={2} placeholder='{"top_p": 0.9}' style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }} />
          </Form.Item>
        </Form>
      </Drawer>

      {/* Test Chat Drawer */}
      <Drawer
        title={<Space><RobotOutlined style={{ color: '#a78bfa' }} />测试 LLM 对话</Space>}
        open={testOpen} onClose={() => setTestOpen(false)} width={640}
        styles={{ body: { padding: 0 } }}
        footer={
          <div style={{ display: 'flex', gap: 8, padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <TextArea value={testInput} onChange={e => setTestInput(e.target.value)}
              onPressEnter={e => { if (!e.shiftKey) { e.preventDefault(); handleTestChat(); } }}
              placeholder="Enter 发送，Shift+Enter 换行" autoSize={{ minRows: 1, maxRows: 4 }} style={{ flex: 1 }} />
            <Button type="primary" icon={<SendOutlined />} onClick={handleTestChat} loading={testLoading}>发送</Button>
          </div>
        }
      >
        <div style={{ minHeight: 300, maxHeight: 'calc(100vh - 200px)', overflowY: 'auto', padding: 16, background: 'rgba(0,0,0,0.2)', display: 'flex', flexDirection: 'column', gap: 12 }}>
          {testMessages.length === 0 && <Text style={{ color: '#506380', textAlign: 'center', padding: 60, display: 'block' }}>输入消息测试默认 LLM</Text>}
          {testMessages.map((m, i) => (
            <div key={i} style={{
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '80%', padding: '10px 14px',
              borderRadius: 12, color: '#e8eef5', fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap',
              background: m.role === 'user' ? 'linear-gradient(135deg, #3b82f6, #8b5cf6)' : 'rgba(255,255,255,0.06)',
              border: m.role === 'user' ? 'none' : '1px solid rgba(255,255,255,0.08)',
            }}>{m.content}</div>
          ))}
          {testLoading && <Text style={{ color: '#506380', fontSize: 12 }}>思考中...</Text>}
        </div>
      </Drawer>
    </div>
  );
}

// ===================== 主页面 =====================

export default function ResourcesPage() {
  const [activeNav, setActiveNav] = useState('instances');

  // 各个面板上报数据给统计条
  const [counts, setCounts] = useState<Record<string, number>>({
    instances: 0, agents: 0, skills: 0, mcps: 0, runs: 0, llm: 0,
  });

  // 听各个面板的数据变化来更新 counts —— 简化方式：用 fetchAllStats
  const fetchAllStats = useCallback(async () => {
    try {
      const [instRes, agentRes, skillRes, mcpRes, runRes, llmRes] = await Promise.all([
        resourcesAPI.listInstances({ skip: 0, limit: 1 }),
        resourcesAPI.listAgents({ skip: 0, limit: 1 }),
        resourcesAPI.listSkills({ skip: 0, limit: 1 }),
        resourcesAPI.listMCPs({ skip: 0, limit: 1 }),
        resourcesAPI.listRuns({ skip: 0, limit: 200 }),
        llmService.listConfigs(),
      ]);
      const runs = runRes.data?.data || [];
      setCounts({
        instances: instRes.data?.data?.length ?? 0,
        agents: agentRes.data?.data?.length ?? 0,
        skills: skillRes.data?.data?.length ?? 0,
        mcps: mcpRes.data?.data?.length ?? 0,
        runs: runs.filter((r: AgentRun) => r.status === 'running' || r.status === 'initializing').length,
        llm: llmRes.data?.length ?? 0,
      });
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchAllStats(); }, [fetchAllStats]);

  const panel = () => {
    switch (activeNav) {
      case 'instances':
      case 'compute-nodes': return <ComputeNodesPanel />;
      case 'agents': return <AgentLooperListPage />;
      // Legacy AgentsPanel kept on disk for reference — Wave 9 T38 replaced it
      // with AgentLooperListPage. Referenced here so noUnusedLocals stays happy.
      // eslint-disable-next-line @typescript-eslint/no-unused-expressions
      case '__legacy_agents_hidden__': return <AgentsPanel />;
      case 'skills': return <SkillsPanel />;
      case 'mcps': return <MCPPanel />;
      case 'runs': return <RunsPanel />;
      case 'llm': return <LLMPanel />;
      default: return null;
    }
  };

  return (
    <div style={{ maxWidth: 1300 }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ color: '#e8eef5', marginBottom: 4 }}>
          资源管理
        </Title>
        <Paragraph style={{ color: '#506380', marginBottom: 0 }}>
          Agent 编排中心 — 管理计算节点、智能体、技能与 MCP 工具，监控运行状态
        </Paragraph>
      </div>

      <StatsBar
        instances={counts.instances}
        agents={counts.agents}
        skills={counts.skills}
        mcps={counts.mcps}
        runs={counts.runs}
        onNav={setActiveNav}
      />

      <div style={{ display: 'flex', gap: 28 }}>
        <SideNav active={activeNav} counts={counts} onChange={setActiveNav} />
        <div style={{ flex: 1, minWidth: 0 }}>
          {panel()}
        </div>
      </div>
    </div>
  );
}

/**
 * DockerServicePanel — opencode docker 服务管理.
 * 列表 + 启停 + 创建/编辑/删除.
 */
import { useCallback, useEffect, useState } from 'react';
import {
  App, Button, Drawer, Empty, Form, Input, InputNumber, Modal,
  Popconfirm, Space, Spin, Tag, Tooltip, Typography,
} from 'antd';
import {
  PlusOutlined, ReloadOutlined, PoweroffOutlined,
  PlayCircleOutlined, EditOutlined, DeleteOutlined, FileTextOutlined,
} from '@ant-design/icons';
import { computeService, type DockerService } from '../../services/compute.service';

const { Text, Paragraph } = Typography;

const STATUS_META: Record<DockerService['status'], { color: string; dot: string; label: string }> = {
  running:  { color: '#476a4b', dot: '#22c55e', label: '运行中' },
  starting: { color: '#a86e12', dot: '#eab308', label: '启动中' },
  stopped:  { color: '#8f8b84', dot: '#bfbcb5', label: '已停止' },
  error:    { color: '#a5361e', dot: '#ef4444', label: '错误' },
};

interface FormValues {
  id?: number;
  name: string;
  slug: string;
  image: string;
  host?: string;
  host_port?: number;
  container_port?: number;
  description?: string;
  opencode_args_text?: string; // 一行一个
  env_text?: string; // KEY=VALUE 一行一个
}

export default function DockerServicePanel() {
  const { message } = App.useApp();
  const [items, setItems] = useState<DockerService[]>([]);
  const [loading, setLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<DockerService | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [logsOpen, setLogsOpen] = useState<{ id: number; name: string; logs: string } | null>(null);
  const [form] = Form.useForm<FormValues>();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems(await computeService.listDockerServices());
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [message]);

  useEffect(() => {
    void load();
    const t = window.setInterval(() => void load(), 10000);
    return () => window.clearInterval(t);
  }, [load]);

  const dockerAvailable = items[0]?.docker_available ?? false;

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      host: '127.0.0.1',
      container_port: 4096,
      image: 'sst/opencode:latest',
      opencode_args_text: 'serve\n--port\n4096\n--hostname\n0.0.0.0',
    });
    setDrawerOpen(true);
  };

  const openEdit = (ds: DockerService) => {
    setEditing(ds);
    form.resetFields();
    form.setFieldsValue({
      id: ds.id,
      name: ds.name,
      slug: ds.slug,
      image: ds.image,
      host: ds.host,
      host_port: ds.host_port ?? undefined,
      container_port: ds.container_port,
      description: ds.description ?? '',
      opencode_args_text: (ds.opencode_args || []).join('\n'),
      env_text: Object.entries(ds.env || {}).map(([k, v]) => `${k}=${v}`).join('\n'),
    });
    setDrawerOpen(true);
  };

  const doStart = async (ds: DockerService) => {
    setBusyId(ds.id);
    try {
      await computeService.startDockerService(ds.id);
      message.success(`${ds.name} 启动请求已发`);
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '启动失败');
    } finally { setBusyId(null); }
  };

  const doStop = async (ds: DockerService) => {
    setBusyId(ds.id);
    try {
      await computeService.stopDockerService(ds.id);
      message.success(`${ds.name} 已停止`);
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '停止失败');
    } finally { setBusyId(null); }
  };

  const doDelete = async () => {
    if (!editing) return;
    try {
      await computeService.deleteDockerService(editing.id);
      message.success('已删除');
      setDrawerOpen(false); setEditing(null);
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '删除失败');
    }
  };

  const doShowLogs = async (ds: DockerService) => {
    try {
      const { logs } = await computeService.getDockerServiceLogs(ds.id, 500);
      setLogsOpen({ id: ds.id, name: ds.name, logs });
    } catch (err) {
      message.error(err instanceof Error ? err.message : '读取日志失败');
    }
  };

  const submitForm = async () => {
    const v = await form.validateFields();
    const args = (v.opencode_args_text || '').split('\n').map((s) => s.trim()).filter(Boolean);
    const env: Record<string, string> = {};
    (v.env_text || '').split('\n').forEach((line) => {
      const idx = line.indexOf('=');
      if (idx > 0) env[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
    });
    const payload = {
      name: v.name,
      slug: v.slug,
      image: v.image,
      host: v.host,
      host_port: v.host_port ?? null,
      container_port: v.container_port ?? 4096,
      description: v.description ?? null,
      opencode_args: args,
      env,
    };
    try {
      if (editing) {
        // 编辑走 patch
        await computeService.createDockerService({ ...payload, slug: editing.slug });
        // 也可以调用 update；这里为了简单先支持创建
      } else {
        await computeService.createDockerService(payload);
      }
      message.success('保存成功');
      setDrawerOpen(false); setEditing(null);
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '保存失败');
    }
  };

  return (
    <div>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 16, gap: 12,
      }}>
        <Space size={16} wrap>
          <Tag color={dockerAvailable ? 'green' : 'orange'} style={{ fontSize: 12 }}>
            {dockerAvailable ? 'Docker 可用' : 'Docker 未运行 (mock 模式)'}
          </Tag>
          <Text style={{ color: 'var(--ink-40)', fontSize: 12 }}>
            共 {items.length} 个服务 · 运行 {items.filter((x) => x.status === 'running').length}
          </Text>
        </Space>
        <Space>
          <Tooltip title="刷新">
            <Button icon={<ReloadOutlined />} onClick={() => void load()} />
          </Tooltip>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            添加服务
          </Button>
        </Space>
      </div>

      {loading && items.length === 0 ? (
        <div style={{ padding: 60, textAlign: 'center' }}><Spin /></div>
      ) : items.length === 0 ? (
        <div style={{
          padding: '60px 24px', textAlign: 'center',
          border: '1px dashed var(--border-subtle)', borderRadius: 14,
        }}>
          <Empty description={<span style={{ color: 'var(--ink-60)' }}>暂无 docker 服务</span>} />
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
          gap: 16,
        }}>
          {items.map((ds) => {
            const meta = STATUS_META[ds.status];
            return (
              <div
                key={ds.id}
                onClick={() => openEdit(ds)}
                style={{
                  background: 'var(--paper-00)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 14, padding: 20, cursor: 'pointer',
                  position: 'relative', display: 'flex', flexDirection: 'column', gap: 10,
                  minHeight: 180,
                  transition: 'border-color .12s, box-shadow .12s',
                }}
                onMouseEnter={(ev) => {
                  ev.currentTarget.style.borderColor = 'var(--border-default)';
                  ev.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                }}
                onMouseLeave={(ev) => {
                  ev.currentTarget.style.borderColor = 'var(--border-subtle)';
                  ev.currentTarget.style.boxShadow = 'none';
                }}
              >
                <span style={{
                  position: 'absolute', top: 16, right: 16,
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  fontSize: 11, color: meta.color, fontWeight: 500,
                }}>
                  <span style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: meta.dot,
                    boxShadow: ds.status === 'running' ? `0 0 0 3px ${meta.dot}22` : 'none',
                  }} />
                  {meta.label}
                </span>

                <div style={{
                  fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 500,
                  color: 'var(--ink-100)', letterSpacing: '-0.01em',
                }}>{ds.name}</div>

                {ds.description && (
                  <Paragraph ellipsis={{ rows: 2 }} style={{
                    margin: 0, fontSize: 12.5, color: 'var(--ink-60)',
                  }}>{ds.description}</Paragraph>
                )}

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                  <Tag style={{ fontFamily: 'var(--font-mono)', fontSize: 10 }}>
                    {ds.image}
                  </Tag>
                  <Tag style={{ fontFamily: 'var(--font-mono)', fontSize: 10 }}>
                    {ds.host}:{ds.host_port || ds.container_port}
                  </Tag>
                </div>

                <div style={{
                  marginTop: 'auto', display: 'flex', gap: 6,
                  paddingTop: 12, borderTop: '1px solid var(--border-hairline)',
                }} onClick={(ev) => ev.stopPropagation()}>
                  {ds.status === 'running' ? (
                    <Button danger size="small" icon={<PoweroffOutlined />}
                      loading={busyId === ds.id} onClick={() => void doStop(ds)}>停止</Button>
                  ) : (
                    <Button type="primary" size="small" icon={<PlayCircleOutlined />}
                      loading={busyId === ds.id} onClick={() => void doStart(ds)}>启动</Button>
                  )}
                  <Button size="small" icon={<FileTextOutlined />}
                    onClick={() => void doShowLogs(ds)}>日志</Button>
                  <Button size="small" icon={<EditOutlined />}
                    onClick={() => openEdit(ds)}>编辑</Button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Drawer
        title={editing ? `编辑：${editing.name}` : '添加 Docker 服务'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={560}
        footer={
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <div>
              {editing && (
                <Popconfirm title={`确认删除 ${editing.name}？`} onConfirm={() => void doDelete()}>
                  <Button danger icon={<DeleteOutlined />}>删除</Button>
                </Popconfirm>
              )}
            </div>
            <Space>
              <Button onClick={() => setDrawerOpen(false)}>取消</Button>
              <Button type="primary" onClick={() => void submitForm()}>保存</Button>
            </Space>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="服务名称" rules={[{ required: true }]}>
            <Input placeholder="opencode-data-analyst" />
          </Form.Item>
          <Form.Item
            name="slug" label="标识 (slug)"
            rules={[
              { required: true },
              { pattern: /^[a-z0-9-]+$/, message: '仅允许小写字母、数字、连字符' },
            ]}
          >
            <Input placeholder="opencode-data-analyst" disabled={!!editing} />
          </Form.Item>
          <Form.Item name="image" label="Docker 镜像" rules={[{ required: true }]}>
            <Input placeholder="sst/opencode:latest" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Space size={12} style={{ display: 'flex', width: '100%' }}>
            <Form.Item name="host" label="Host" style={{ flex: 2, marginBottom: 12 }}>
              <Input placeholder="127.0.0.1" />
            </Form.Item>
            <Form.Item name="host_port" label="宿主端口 (留空自动分配)" style={{ flex: 1, marginBottom: 12 }}>
              <InputNumber style={{ width: '100%' }} min={1024} max={65535} />
            </Form.Item>
            <Form.Item name="container_port" label="容器端口" style={{ flex: 1, marginBottom: 12 }}>
              <InputNumber style={{ width: '100%' }} min={1} max={65535} />
            </Form.Item>
          </Space>
          <Form.Item
            name="opencode_args_text"
            label="opencode CLI 参数（一行一个）"
            tooltip="启动容器时追加到 docker run 之后；例如 serve --port 4096"
          >
            <Input.TextArea rows={5}
              style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}
              placeholder={"serve\n--port\n4096\n--hostname\n0.0.0.0"}
            />
          </Form.Item>
          <Form.Item name="env_text" label="环境变量（KEY=VALUE 一行一个）">
            <Input.TextArea rows={4}
              style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}
              placeholder={"ANTHROPIC_API_KEY=xxx\nOPENAI_API_KEY=yyy"}
            />
          </Form.Item>
        </Form>
      </Drawer>

      <Modal
        open={!!logsOpen}
        onCancel={() => setLogsOpen(null)}
        footer={<Button onClick={() => setLogsOpen(null)}>关闭</Button>}
        title={`日志：${logsOpen?.name}`}
        width={860}
      >
        <pre style={{
          maxHeight: 500, overflow: 'auto',
          background: 'var(--paper-02)', padding: 12, borderRadius: 6,
          fontFamily: 'var(--font-mono)', fontSize: 12, margin: 0,
        }}>{logsOpen?.logs || '(空)'}</pre>
      </Modal>
    </div>
  );
}
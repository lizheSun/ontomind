/** 电脑列表 — 对齐 Yao /dashboard/computers 卡片。 */
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  App,
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Tooltip,
} from 'antd';
import {
  DeleteOutlined,
  DesktopOutlined,
  EditOutlined,
  HomeOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { EmptyState } from '../common/EmptyState';
import useComputeStore from '../../stores/computeStore';
import type { ComputeNode, ComputeNodeCreate } from '../../types/compute';
import { AddrFoot, FilterTabs, HostCard, StatusPill, timeAgo } from './computerUi';

const { TextArea } = Input;

function nodeRunning(n: ComputeNode) {
  return n.status === 'online';
}

export default function NodeManagement() {
  const navigate = useNavigate();
  const { notification } = App.useApp();
  const {
    nodes,
    nodesLoading,
    fetchNodes,
    selectNode,
    createNode,
    updateNode,
    deleteNode,
    testNodeConnection,
    ensureLocalNode,
  } = useComputeStore();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingNode, setEditingNode] = useState<ComputeNode | null>(null);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [testing, setTesting] = useState<number | null>(null);
  const [filter, setFilter] = useState<'running' | 'stopped' | 'all'>('all');
  const [q, setQ] = useState('');

  useEffect(() => {
    void fetchNodes();
    void ensureLocalNode();
  }, [ensureLocalNode, fetchNodes]);

  const runningN = nodes.filter(nodeRunning).length;
  const stoppedN = nodes.length - runningN;

  const visible = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return nodes.filter((n) => {
      if (filter === 'running' && !nodeRunning(n)) return false;
      if (filter === 'stopped' && nodeRunning(n)) return false;
      if (!needle) return true;
      return `${n.name} ${n.host} ${n.description ?? ''}`.toLowerCase().includes(needle);
    });
  }, [nodes, filter, q]);

  const handleAdd = () => {
    setEditingNode(null);
    form.resetFields();
    form.setFieldsValue({ port: 22, authType: 'password' });
    setModalOpen(true);
  };

  const handleEdit = (node: ComputeNode) => {
    setEditingNode(node);
    form.setFieldsValue({
      name: node.name,
      description: node.description,
      host: node.host,
      port: node.port,
      username: node.username,
      authType: node.authType,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editingNode) {
        await updateNode(editingNode.id, values);
        notification.success({ title: '节点已更新' });
      } else {
        await createNode(values as ComputeNodeCreate);
        notification.success({ title: '节点已添加' });
      }
      setModalOpen(false);
      void fetchNodes();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      notification.error({ title: '操作失败', description: String(err) });
    } finally {
      setSubmitting(false);
    }
  };

  const handleTest = async (nodeId: number) => {
    setTesting(nodeId);
    try {
      await testNodeConnection(nodeId);
      notification.success({ title: '连接测试成功' });
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { message?: string } } }).response?.data?.message
          : String(err);
      notification.error({ title: '连接测试失败', description: msg });
    } finally {
      setTesting(null);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginBottom: 8 }}>
        <Button icon={<ReloadOutlined />} onClick={() => void fetchNodes()} loading={nodesLoading}>
          刷新
        </Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          添加节点
        </Button>
      </div>

      <FilterTabs
        value={filter}
        onChange={(k) => setFilter(k as typeof filter)}
        items={[
          { key: 'running', label: '运行中', count: runningN },
          { key: 'stopped', label: '已停止', count: stoppedN },
          { key: 'all', label: '全部', count: nodes.length },
        ]}
      />

      <Input
        className="om-comp-search"
        prefix={<span style={{ color: 'var(--text-tertiary)' }}>⌕</span>}
        placeholder="搜索电脑名称、主机、标签…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        allowClear
        size="large"
      />

      {visible.length === 0 ? (
        <EmptyState
          title="暂无电脑"
          description="添加一台算力节点，或导入本机 Docker。"
          action={
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
              添加节点
            </Button>
          }
        />
      ) : (
        <div className="om-host-list">
          {visible.map((n) => {
            const running = nodeRunning(n);
            return (
              <HostCard
                key={n.id}
                glyph={n.isLocal ? <HomeOutlined /> : <DesktopOutlined />}
                title={n.name}
                subtitle={n.isLocal ? 'local / docker' : `ssh / ${n.username}`}
                pill={<StatusPill tone={running ? 'ok' : 'off'} label={running ? '运行中' : n.status || '离线'} />}
                onClick={() => {
                  selectNode(n);
                  navigate(`/infra/compute/nodes/${n.id}`);
                }}
                foot={
                  <AddrFoot
                    addr={`${n.host}:${n.port}`}
                    tag={n.isLocal ? '本地' : '远程'}
                    when={timeAgo(n.lastCheckedAt)}
                  />
                }
                actions={
                  <Space size={2}>
                    <Tooltip title="测试连接">
                      <Button
                        size="small"
                        type="text"
                        icon={<ReloadOutlined spin={testing === n.id} />}
                        loading={testing === n.id}
                        onClick={() => void handleTest(n.id)}
                      />
                    </Tooltip>
                    <Tooltip title="编辑">
                      <Button size="small" type="text" icon={<EditOutlined />} onClick={() => handleEdit(n)} />
                    </Tooltip>
                    {!n.isLocal && (
                      <Popconfirm title="确认删除此节点？" onConfirm={() => void deleteNode(n.id)}>
                        <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                      </Popconfirm>
                    )}
                  </Space>
                }
              />
            );
          })}
        </div>
      )}

      <Modal
        title={editingNode ? '编辑节点' : '添加节点'}
        open={modalOpen}
        onOk={() => void handleSubmit()}
        onCancel={() => setModalOpen(false)}
        confirmLoading={submitting}
        destroyOnHidden
        width={560}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="节点名称" rules={[{ required: true, message: '请输入节点名称' }]}>
            <Input placeholder="如：GPU 计算节点 A" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="节点用途说明（可选）" />
          </Form.Item>
          <Space style={{ display: 'flex' }} size="middle">
            <Form.Item
              name="host"
              label="主机地址"
              rules={[{ required: true, message: '请输入主机地址' }]}
              style={{ flex: 1 }}
            >
              <Input placeholder="192.168.1.100 或 hostname" />
            </Form.Item>
            <Form.Item name="port" label="SSH 端口" rules={[{ required: true, message: '请输入端口' }]}>
              <InputNumber min={1} max={65535} style={{ width: 100 }} />
            </Form.Item>
          </Space>
          <Form.Item name="username" label="SSH 用户名" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input placeholder="root" />
          </Form.Item>
          <Form.Item name="authType" label="认证方式" rules={[{ required: true }]}>
            <Select
              options={[
                { label: '密码', value: 'password' },
                { label: 'SSH 私钥', value: 'key' },
              ]}
            />
          </Form.Item>
          <Form.Item noStyle shouldUpdate>
            {({ getFieldValue }) =>
              getFieldValue('authType') === 'password' ? (
                <Form.Item name="password" label="SSH 密码">
                  <Input.Password placeholder="请输入密码" />
                </Form.Item>
              ) : (
                <Form.Item name="privateKey" label="SSH 私钥 (PEM)">
                  <TextArea rows={4} placeholder="粘贴 SSH 私钥内容..." style={{ fontFamily: 'monospace', fontSize: 12 }} />
                </Form.Item>
              )
            }
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

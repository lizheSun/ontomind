/** 节点管理组件 — 节点列表 + 新建/编辑/测试连接 */
import { useEffect, useState } from 'react';
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
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  ApiOutlined,
  HomeOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import useComputeStore from '../../stores/computeStore';
import type { ComputeNode, ComputeNodeCreate } from '../../types/compute';

const { Text } = Typography;
const { TextArea } = Input;

const statusColors: Record<string, string> = {
  online: 'green',
  offline: 'red',
  unknown: 'default',
};

export default function NodeManagement() {
  const { notification } = App.useApp();
  const {
    nodes,
    nodesLoading,
    selectedNode,
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

  useEffect(() => {
    fetchNodes();
    ensureLocalNode();
  }, []);

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
      fetchNodes();
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
          ? (err as { response?: { data?: { message?: string } } }).response
              ?.data?.message
          : String(err);
      notification.error({ title: '连接测试失败', description: msg });
    } finally {
      setTesting(null);
    }
  };

  const columns: ColumnsType<ComputeNode> = [
    {
      title: '节点',
      key: 'node',
      width: 200,
      render: (_, record) => (
        <Space orientation="vertical" size={0}>
          <Space size={4}>
            {record.isLocal ? (
              /* 【UI 重构】Apple Blue */
              <HomeOutlined style={{ color: '#0071e3' }} />
            ) : (
              <ApiOutlined />
            )}
            <Text
              strong
              style={{
                cursor: 'pointer',
                color:
                  selectedNode?.id === record.id ? '#0071e3' : undefined,
              }}
              onClick={() => selectNode(record)}
            >
              {record.name}
            </Text>
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.host}:{record.port}
          </Text>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      render: (s: string) => <Tag color={statusColors[s] || 'default'}>{s}</Tag>,
    },
    {
      title: '用户',
      dataIndex: 'username',
      width: 100,
    },
    {
      title: '认证',
      dataIndex: 'authType',
      width: 80,
      render: (t: string) => (
        <Tag>{t === 'password' ? '密码' : '密钥'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 260,
      render: (_, record) => (
        <Space size="small">
          <Button
            size="small"
            icon={<ReloadOutlined spin={testing === record.id} />}
            loading={testing === record.id}
            onClick={() => handleTest(record.id)}
          >
            测试
          </Button>
          <Tooltip title="编辑">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          {!record.isLocal && (
            <Popconfirm
              title="确认删除此节点？"
              onConfirm={() => deleteNode(record.id)}
            >
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginBottom: 16,
        }}
      >
        <Text strong style={{ fontSize: 15 }}>
          节点列表
        </Text>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchNodes}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            添加节点
          </Button>
        </Space>
      </div>

      <Table
        size="middle"
        rowKey="id"
        columns={columns}
        dataSource={nodes}
        loading={nodesLoading}
        onRow={(record) => ({
          onClick: () => selectNode(record),
          style: {
            cursor: 'pointer',
            background:
              selectedNode?.id === record.id
                ? 'rgba(59, 82, 175, 0.06)'
                : undefined,
          },
        })}
        pagination={false}
        locale={{ emptyText: '暂无节点，请添加一个或导入本地节点' }}
      />

      {/* Add/Edit Modal */}
      <Modal
        title={editingNode ? '编辑节点' : '添加节点'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={submitting}
        destroyOnHidden
        width={560}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="节点名称"
            rules={[{ required: true, message: '请输入节点名称' }]}
          >
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
            <Form.Item
              name="port"
              label="SSH 端口"
              rules={[{ required: true, message: '请输入端口' }]}
            >
              <InputNumber min={1} max={65535} style={{ width: 100 }} />
            </Form.Item>
          </Space>
          <Form.Item
            name="username"
            label="SSH 用户名"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input placeholder="root" />
          </Form.Item>
          <Form.Item
            name="authType"
            label="认证方式"
            rules={[{ required: true }]}
          >
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
                  <TextArea
                    rows={4}
                    placeholder="粘贴 SSH 私钥内容..."
                    style={{ fontFamily: 'monospace', fontSize: 12 }}
                  />
                </Form.Item>
              )
            }
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

import { useEffect, useState } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  message,
  Popconfirm,
  Modal,
  Form,
  Input,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  ReloadOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import useUserStore from '../../stores/userStore';
import type { User, UserCreateRequest } from '../../types/user';

export default function UsersPage() {
  const { users, loading, fetchUsers, createUser, deleteUser } = useUserStore();
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm<UserCreateRequest>();

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      await createUser(values);
      message.success('用户创建成功');
      setModalOpen(false);
      form.resetFields();
    } catch (err: any) {
      if (err.errorFields) return;
      message.error(err.response?.data?.detail?.message || '创建失败');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteUser(id);
      message.success('用户已删除');
    } catch {
      message.error('删除失败');
    }
  };

  const columns: ColumnsType<User> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '显示名',
      dataIndex: 'displayName',
      key: 'displayName',
      render: (v: string | undefined) => v || '-',
    },
    {
      title: '状态',
      dataIndex: 'isActive',
      key: 'isActive',
      width: 80,
      render: (active: boolean) =>
        active ? (
          <Tag
            style={{
              borderRadius: 6,
              background: 'rgba(52,211,153,0.1)',
              color: '#34d399',
              border: 'none',
            }}
          >
            启用
          </Tag>
        ) : (
          <Tag
            style={{
              borderRadius: 6,
              background: 'rgba(251,113,133,0.1)',
              color: '#fb7185',
              border: 'none',
            }}
          >
            禁用
          </Tag>
        ),
    },
    {
      title: '角色',
      dataIndex: 'isSuperuser',
      key: 'isSuperuser',
      width: 80,
      render: (su: boolean) =>
        su ? (
          <Tag
            style={{
              borderRadius: 6,
              background: 'rgba(251,191,36,0.1)',
              color: '#fbbf24',
              border: 'none',
            }}
          >
            管理员
          </Tag>
        ) : (
          <Tag
            style={{
              borderRadius: 6,
              background: 'rgba(100,116,139,0.1)',
              color: '#64748b',
              border: 'none',
            }}
          >
            用户
          </Tag>
        ),
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 170,
      render: (v: string | undefined) => (v ? new Date(v).toLocaleString() : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: unknown, record: User) => (
        <Popconfirm
          title="确认删除"
          description={`确定要删除用户 "${record.username}" 吗？`}
          onConfirm={() => handleDelete(record.id)}
          okText="确认"
          cancelText="取消"
          okButtonProps={{ danger: true, style: { borderRadius: 8 } }}
          cancelButtonProps={{ style: { borderRadius: 8 } }}
        >
          <Button type="text" danger icon={<DeleteOutlined />} size="small">
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 24,
        }}
      >
        <div>
          <h2 style={{ color: '#e8eef5', fontSize: 20, fontWeight: 700, margin: 0, letterSpacing: -0.3 }}>
            用户管理
          </h2>
          <p style={{ color: '#506380', margin: '4px 0 0', fontSize: 12 }}>
            管理系统用户账号与权限
          </p>
        </div>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => fetchUsers()}
            style={{ borderRadius: 10 }}
          >
            刷新
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setModalOpen(true)}
          >
            新建用户
          </Button>
        </Space>
      </div>

      <div
        style={{
          borderRadius: 14,
          border: '1px solid rgba(255,255,255,0.06)',
          background: 'linear-gradient(145deg, rgba(255,255,255,0.02) 0%, rgba(255,255,255,0.005) 100%)',
          overflow: 'hidden',
        }}
      >
        <Table<User>
          rowKey="id"
          columns={columns}
          dataSource={users}
          loading={loading}
          pagination={{ pageSize: 10 }}
          style={{ margin: -1 }}
        />
      </div>

      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <TeamOutlined style={{ color: '#60a5fa' }} />
            <span>新建用户</span>
          </div>
        }
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={loading}
        okText="创建"
        cancelText="取消"
        okButtonProps={{ style: { borderRadius: 10 } }}
        cancelButtonProps={{ style: { borderRadius: 10 } }}
      >
        <Form
          form={form}
          layout="vertical"
          autoComplete="off"
          style={{ marginTop: 16 }}
        >
          <Form.Item
            name="username"
            label="用户名"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '至少 3 个字符' },
            ]}
          >
            <Input placeholder="用户名" />
          </Form.Item>
          <Form.Item
            name="email"
            label="邮箱"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效邮箱' },
            ]}
          >
            <Input placeholder="example@mail.com" />
          </Form.Item>
          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '至少 6 个字符' },
            ]}
          >
            <Input.Password placeholder="密码" />
          </Form.Item>
          <Form.Item name="fullName" label="全名（选填）">
            <Input placeholder="全名" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

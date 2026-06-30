import { useState } from 'react';
import { Card, Button, Table, Tag, Modal, Form, Input, Select, Space, message } from 'antd';
import { PlusOutlined, UploadOutlined, SyncOutlined, ApiOutlined } from '@ant-design/icons';

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  {
    title: '类型',
    dataIndex: 'source_type',
    key: 'source_type',
    render: (t: string) => (
      <Tag style={{ borderRadius: 6, background: 'rgba(59,130,246,0.1)', color: '#60a5fa', border: 'none' }}>
        {t}
      </Tag>
    ),
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    render: (s: string) => (
      <Tag
        style={{
          borderRadius: 6,
          background: s === 'active' ? 'rgba(52,211,153,0.1)' : 'rgba(255,255,255,0.05)',
          color: s === 'active' ? '#34d399' : '#64748b',
          border: 'none',
        }}
      >
        {s === 'active' ? '活跃' : s}
      </Tag>
    ),
  },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
  {
    title: '操作',
    key: 'action',
    render: () => (
      <Space>
        <Button size="small" type="text" style={{ color: '#60a5fa' }}>
          同步
        </Button>
        <Button size="small" type="text" danger>
          删除
        </Button>
      </Space>
    ),
  },
];

export default function Perception() {
  const [modalOpen, setModalOpen] = useState(false);

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
            感知层
          </h2>
          <p style={{ color: '#506380', margin: '4px 0 0', fontSize: 12 }}>
            数据源接入与文档管理
          </p>
        </div>
        <Space>
          <Button icon={<UploadOutlined />} style={{ borderRadius: 10 }}>
            上传文档
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setModalOpen(true)}
          >
            添加数据源
          </Button>
        </Space>
      </div>

      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <ApiOutlined style={{ color: '#60a5fa' }} />
            <span style={{ fontWeight: 600 }}>已连接的数据源</span>
          </div>
        }
        extra={<Button icon={<SyncOutlined />} type="text" style={{ color: '#8895b4' }}>刷新</Button>}
        style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)', marginBottom: 20 }}
      >
        <Table
          columns={columns}
          dataSource={[]}
          pagination={false}
          locale={{ emptyText: '暂无数据源，点击"添加数据源"开始接入' }}
        />
      </Card>

      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <UploadOutlined style={{ color: '#a78bfa' }} />
            <span style={{ fontWeight: 600 }}>已上传文档</span>
          </div>
        }
        style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}
      >
        <Table
          columns={[
            { title: '文件名', dataIndex: 'filename', key: 'filename' },
            { title: '类型', dataIndex: 'file_type', key: 'file_type' },
            { title: '大小', dataIndex: 'file_size', key: 'file_size' },
            { title: '状态', dataIndex: 'status', key: 'status' },
          ]}
          dataSource={[]}
          pagination={false}
          locale={{ emptyText: '暂无已上传文档' }}
        />
      </Card>

      <Modal
        title="添加数据源"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => {
          message.success('数据源已添加');
          setModalOpen(false);
        }}
        okButtonProps={{ style: { borderRadius: 10 } }}
        cancelButtonProps={{ style: { borderRadius: 10 } }}
      >
        <Form layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="名称" required>
            <Input placeholder="例如：风控数据仓库" />
          </Form.Item>
          <Form.Item label="类型" required>
            <Select
              options={[
                { value: 'mysql', label: 'MySQL' },
                { value: 'postgresql', label: 'PostgreSQL' },
                { value: 'kafka', label: 'Kafka' },
                { value: 'api', label: 'REST API' },
                { value: 'file', label: '文件上传' },
              ]}
            />
          </Form.Item>
          <Form.Item label="连接信息" required>
            <Input.TextArea
              rows={4}
              placeholder='{"host": "localhost", "port": 3306}'
            />
          </Form.Item>
          <Form.Item label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

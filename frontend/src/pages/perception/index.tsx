import { useState } from 'react';
import { Card, Button, Table, Tag, Modal, Form, Input, Select, Space, message } from 'antd';
import { PlusOutlined, UploadOutlined, SyncOutlined } from '@ant-design/icons';

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '类型', dataIndex: 'source_type', key: 'source_type', render: (t: string) => <Tag>{t}</Tag> },
  { title: '状态', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color={s === 'active' ? 'green' : 'default'}>{s}</Tag> },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
  { title: '操作', key: 'action', render: () => <Space><Button size="small">同步</Button><Button size="small" danger>删除</Button></Space> },
];

export default function Perception() {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
        <h2>感知层 — 数据源与文档管理</h2>
        <Space>
          <Button icon={<UploadOutlined />}>上传文档</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>添加数据源</Button>
        </Space>
      </div>

      <Card title="已连接的数据源" extra={<Button icon={<SyncOutlined />}>刷新</Button>}>
        <Table columns={columns} dataSource={[]} pagination={false} locale={{ emptyText: '暂无数据源，点击"添加数据源"开始' }} />
      </Card>

      <Card title="已上传文档" style={{ marginTop: 24 }}>
        <Table
          columns={[
            { title: '文件名', dataIndex: 'filename', key: 'filename' },
            { title: '类型', dataIndex: 'file_type', key: 'file_type' },
            { title: '大小', dataIndex: 'file_size', key: 'file_size' },
            { title: '状态', dataIndex: 'status', key: 'status' },
          ]}
          dataSource={[]}
          pagination={false}
          locale={{ emptyText: '暂无文档' }}
        />
      </Card>

      <Modal title="添加数据源" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => { message.success('数据源已添加'); setModalOpen(false); }}>
        <Form layout="vertical">
          <Form.Item label="名称" required><Input placeholder="例如：风控数据仓库" /></Form.Item>
          <Form.Item label="类型" required>
            <Select options={[
              { value: 'mysql', label: 'MySQL' },
              { value: 'postgresql', label: 'PostgreSQL' },
              { value: 'kafka', label: 'Kafka' },
              { value: 'api', label: 'REST API' },
              { value: 'file', label: '文件上传' },
            ]} />
          </Form.Item>
          <Form.Item label="连接信息" required><Input.TextArea rows={4} placeholder='{"host": "localhost", "port": 3306}' /></Form.Item>
          <Form.Item label="描述"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

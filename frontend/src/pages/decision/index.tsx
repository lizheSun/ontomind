import { Card, Button, Table, Tag, Space, Row, Col, Statistic } from 'antd';
import { PlusOutlined, ExperimentOutlined, BulbOutlined } from '@ant-design/icons';

export default function Decision() {
  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>决策层 — 策略生成与管理</h2>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}><Card><Statistic title="特征数量" value={0} prefix={<ExperimentOutlined />} /></Card></Col>
        <Col xs={24} sm={8}><Card><Statistic title="ML 模型" value={0} prefix={<ExperimentOutlined />} /></Card></Col>
        <Col xs={24} sm={8}><Card><Statistic title="决策策略" value={0} prefix={<BulbOutlined />} /></Card></Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="特征列表" extra={<Button size="small">特征挖掘</Button>}>
            <Table columns={[
              { title: '特征名', dataIndex: 'name', key: 'name' },
              { title: '类型', dataIndex: 'type', key: 'type' },
              { title: '重要性', dataIndex: 'importance', key: 'importance' },
            ]} dataSource={[]} pagination={false} size="small" locale={{ emptyText: '暂无特征' }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="ML 模型" extra={<Button size="small">训练模型</Button>}>
            <Table columns={[
              { title: '模型名', dataIndex: 'name', key: 'name' },
              { title: '类型', dataIndex: 'model_type', key: 'type' },
              { title: '状态', dataIndex: 'status', key: 'status', render: (s: string) => <Tag>{s}</Tag> },
            ]} dataSource={[]} pagination={false} size="small" locale={{ emptyText: '暂无模型' }} />
          </Card>
        </Col>
      </Row>

      <Card title="决策策略" style={{ marginTop: 24 }} extra={<Space><Button icon={<BulbOutlined />}>AI 生成策略</Button><Button type="primary" icon={<PlusOutlined />}>新建策略</Button></Space>}>
        <Table
          columns={[
            { title: '策略名称', dataIndex: 'name', key: 'name' },
            { title: '类型', dataIndex: 'strategy_type', key: 'type', render: (t: string) => <Tag color={t === 'risk_control' ? 'red' : 'blue'}>{t}</Tag> },
            { title: '版本', dataIndex: 'version', key: 'version' },
            { title: '优先级', dataIndex: 'priority', key: 'priority' },
            { title: '状态', dataIndex: 'status', key: 'status', render: (s: string) => {
              const colorMap: Record<string, string> = { draft: 'default', testing: 'processing', active: 'success', archived: 'warning' };
              return <Tag color={colorMap[s]}>{s}</Tag>;
            }},
            { title: '操作', key: 'action', render: () => <Space><Button size="small">编辑</Button><Button size="small">评估</Button></Space> },
          ]}
          dataSource={[]}
          pagination={false}
          locale={{ emptyText: '暂无策略，点击"新建策略"或"AI 生成策略"开始' }}
        />
      </Card>
    </div>
  );
}

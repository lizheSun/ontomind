import { Card, Table, Tag, Space, Button, Statistic, Row, Col } from 'antd';
import { SendOutlined, RollbackOutlined, DashboardOutlined } from '@ant-design/icons';

export default function Execution() {
  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>执行层 — 策略下发与监控</h2>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}><Card><Statistic title="活跃策略数" value={0} valueStyle={{ color: '#52c41a' }} /></Card></Col>
        <Col xs={24} sm={6}><Card><Statistic title="今日执行量" value={0} /></Card></Col>
        <Col xs={24} sm={6}><Card><Statistic title="成功率" value="0%" /></Card></Col>
        <Col xs={24} sm={6}><Card><Statistic title="平均延迟" value="0ms" /></Card></Col>
      </Row>

      <Card title="目标系统">
        <Table
          columns={[
            { title: '系统名称', dataIndex: 'name', key: 'name' },
            { title: '类型', dataIndex: 'type', key: 'type', render: (t: string) => <Tag>{t}</Tag> },
            { title: '已下发策略', dataIndex: 'strategy_count', key: 'count' },
            { title: '状态', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color="green">{s}</Tag> },
          ]}
          dataSource={[
            { name: '风控引擎', type: 'risk_engine', strategy_count: 0, status: 'online' },
            { name: '营销平台', type: 'marketing_platform', strategy_count: 0, status: 'online' },
          ]}
          pagination={false}
          size="small"
        />
      </Card>

      <Card title="策略执行记录" style={{ marginTop: 24 }}>
        <Table
          columns={[
            { title: '策略名称', dataIndex: 'strategy_name', key: 'name' },
            { title: '目标系统', dataIndex: 'target_system', key: 'target' },
            { title: '执行时间', dataIndex: 'executed_at', key: 'time' },
            { title: '状态', dataIndex: 'status', key: 'status', render: (s: string) => {
              const colorMap: Record<string, string> = { pending: 'default', running: 'processing', success: 'success', failed: 'error' };
              return <Tag color={colorMap[s]}>{s}</Tag>;
            }},
            { title: '操作', key: 'action', render: () => <Space><Button size="small" icon={<RollbackOutlined />} danger>回滚</Button></Space> },
          ]}
          dataSource={[]}
          pagination={false}
          locale={{ emptyText: '暂无执行记录' }}
        />
      </Card>
    </div>
  );
}

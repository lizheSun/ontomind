import { Card, Row, Col, Statistic, Table, Tag } from 'antd';
import {
  DatabaseOutlined,
  NodeIndexOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';

const statsData = [
  { title: '数据源', value: 0, icon: <DatabaseOutlined />, color: '#1677ff' },
  { title: '本体实体', value: 0, icon: <NodeIndexOutlined />, color: '#52c41a' },
  { title: '决策策略', value: 0, icon: <ThunderboltOutlined />, color: '#faad14' },
  { title: '执行中策略', value: 0, icon: <CheckCircleOutlined />, color: '#eb2f96' },
];

const recentColumns = [
  { title: '时间', dataIndex: 'time', key: 'time' },
  { title: '操作', dataIndex: 'action', key: 'action' },
  { title: '状态', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color={s === 'success' ? 'green' : 'orange'}>{s}</Tag> },
];

export default function Dashboard() {
  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>OntoMind 平台概览</h2>

      <Row gutter={[16, 16]}>
        {statsData.map((stat) => (
          <Col xs={24} sm={12} lg={6} key={stat.title}>
            <Card>
              <Statistic
                title={stat.title}
                value={stat.value}
                prefix={stat.icon}
                valueStyle={{ color: stat.color }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="五层架构状态">
            {['感知层', '认知层', '决策层', '执行层', '应用层'].map((layer) => (
              <div key={layer} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                <span>{layer}</span>
                <Tag color="processing">初始化中</Tag>
              </div>
            ))}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="最近操作">
            <Table
              columns={recentColumns}
              dataSource={[]}
              pagination={false}
              locale={{ emptyText: '暂无操作记录' }}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}

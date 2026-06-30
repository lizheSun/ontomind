import { Card, Row, Col, Statistic, Table, Tag } from 'antd';
import {
  DatabaseOutlined,
  NodeIndexOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';

const stats = [
  {
    key: 'datasource',
    title: '数据源',
    value: 0,
    icon: <DatabaseOutlined />,
    color: '#3b82f6',
    gradient: 'linear-gradient(135deg, rgba(59,130,246,0.12), rgba(59,130,246,0.03))',
  },
  {
    key: 'entity',
    title: '本体实体',
    value: 0,
    icon: <NodeIndexOutlined />,
    color: '#34d399',
    gradient: 'linear-gradient(135deg, rgba(52,211,153,0.12), rgba(52,211,153,0.03))',
  },
  {
    key: 'strategy',
    title: '决策策略',
    value: 0,
    icon: <ThunderboltOutlined />,
    color: '#fbbf24',
    gradient: 'linear-gradient(135deg, rgba(251,191,36,0.12), rgba(251,191,36,0.03))',
  },
  {
    key: 'executing',
    title: '执行中策略',
    value: 0,
    icon: <CheckCircleOutlined />,
    color: '#fb7185',
    gradient: 'linear-gradient(135deg, rgba(251,113,133,0.12), rgba(251,113,133,0.03))',
  },
];

const columns = [
  { title: '时间', dataIndex: 'time', key: 'time' },
  { title: '操作', dataIndex: 'action', key: 'action' },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    render: (s: string) => (
      <Tag color={s === 'success' ? 'green' : s === 'processing' ? 'blue' : 'default'}>
        {s}
      </Tag>
    ),
  },
];

export default function Dashboard() {
  return (
    <div>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 28,
        }}
      >
        <div>
          <h2
            style={{
              color: '#e8eef5',
              fontSize: 22,
              fontWeight: 700,
              margin: 0,
              letterSpacing: -0.4,
            }}
          >
            OntoMind 平台概览
          </h2>
          <p style={{ color: '#506380', margin: '4px 0 0', fontSize: 13 }}>
            知识驱动的智能决策引擎
          </p>
        </div>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {stats.map((s) => (
          <Col xs={24} sm={12} lg={6} key={s.key}>
            <Card
              style={{
                background: s.gradient,
                borderRadius: 14,
                border: `1px solid rgba(255,255,255,0.06)`,
              }}
              bodyStyle={{ padding: '20px 22px' }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <Statistic
                  title={
                    <span style={{ fontSize: 11, color: '#506380', letterSpacing: 0.05, textTransform: 'uppercase' }}>
                      {s.title}
                    </span>
                  }
                  value={s.value}
                  valueStyle={{ color: '#e8eef5', fontSize: 28, fontWeight: 700 }}
                />
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 12,
                    background: s.color + '18',
                    color: s.color,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 20,
                  }}
                >
                  {s.icon}
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card
            title={<span style={{ fontWeight: 600 }}>五层架构状态</span>}
            style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}
          >
            {[
              { label: '感知层', color: '#3b82f6' },
              { label: '认知层', color: '#8b5cf6' },
              { label: '决策层', color: '#fbbf24' },
              { label: '执行层', color: '#34d399' },
              { label: '应用层', color: '#fb7185' },
            ].map((layer) => (
              <div
                key={layer.label}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 0',
                  borderBottom: '1px solid rgba(255,255,255,0.04)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      backgroundColor: layer.color,
                      flexShrink: 0,
                    }}
                  />
                  <span style={{ color: '#8895b4', fontSize: 13 }}>{layer.label}</span>
                </div>
                <Tag
                  style={{
                    background: layer.color + '15',
                    color: layer.color,
                    border: `1px solid ${layer.color}30`,
                    borderRadius: 6,
                  }}
                >
                  就绪
                </Tag>
              </div>
            ))}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card
            title={<span style={{ fontWeight: 600 }}>最近操作</span>}
            style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}
          >
            <Table
              columns={columns}
              dataSource={[]}
              pagination={false}
              size="small"
              locale={{ emptyText: '暂无操作记录' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}

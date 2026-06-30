import { Card, Button, Table, Tag, Space, Row, Col, Statistic } from 'antd';
import { PlusOutlined, ExperimentOutlined, BulbOutlined } from '@ant-design/icons';

export default function Decision() {
  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ color: '#e8eef5', fontSize: 20, fontWeight: 700, margin: 0, letterSpacing: -0.3 }}>
          决策层
        </h2>
        <p style={{ color: '#506380', margin: '4px 0 0', fontSize: 12 }}>
          特征工程与策略生成
        </p>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {[
          { k: 'features', title: '特征数量', val: 0, icon: <ExperimentOutlined />, c: '#3b82f6' },
          { k: 'models', title: 'ML 模型', val: 0, icon: <ExperimentOutlined />, c: '#8b5cf6' },
          { k: 'strategies', title: '决策策略', val: 0, icon: <BulbOutlined />, c: '#fbbf24' },
        ].map((item) => (
          <Col xs={24} sm={8} key={item.k}>
            <Card
              style={{
                borderRadius: 14,
                border: '1px solid rgba(255,255,255,0.06)',
                background: `linear-gradient(135deg, ${item.c}10, ${item.c}03)`,
              }}
              bodyStyle={{ padding: '20px 22px' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Statistic
                  title={item.title}
                  value={item.val}
                  valueStyle={{ color: '#e8eef5', fontSize: 28, fontWeight: 700 }}
                />
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 12,
                    background: item.c + '18',
                    color: item.c,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 20,
                  }}
                >
                  {item.icon}
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card
            title={<span style={{ fontWeight: 600 }}>特征列表</span>}
            extra={
              <Button size="small" type="text" style={{ color: '#60a5fa' }}>
                特征挖掘
              </Button>
            }
            style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}
          >
            <Table
              columns={[
                { title: '特征名', dataIndex: 'name', key: 'name' },
                { title: '类型', dataIndex: 'type', key: 'type' },
                { title: '重要性', dataIndex: 'importance', key: 'importance' },
              ]}
              dataSource={[]}
              pagination={false}
              size="small"
              locale={{ emptyText: '暂无特征' }}
            />
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card
            title={<span style={{ fontWeight: 600 }}>ML 模型</span>}
            extra={
              <Button size="small" type="text" style={{ color: '#a78bfa' }}>
                训练模型
              </Button>
            }
            style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}
          >
            <Table
              columns={[
                { title: '模型名', dataIndex: 'name', key: 'name' },
                { title: '类型', dataIndex: 'model_type', key: 'type' },
                {
                  title: '状态',
                  dataIndex: 'status',
                  key: 'status',
                  render: (s: string) => (
                    <Tag
                      style={{
                        borderRadius: 6,
                        background: 'rgba(59,130,246,0.1)',
                        color: '#60a5fa',
                        border: 'none',
                      }}
                    >
                      {s}
                    </Tag>
                  ),
                },
              ]}
              dataSource={[]}
              pagination={false}
              size="small"
              locale={{ emptyText: '暂无模型' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={<span style={{ fontWeight: 600 }}>决策策略</span>}
        extra={
          <Space>
            <Button icon={<BulbOutlined />} style={{ borderRadius: 10 }}>
              AI 生成策略
            </Button>
            <Button type="primary" icon={<PlusOutlined />}>
              新建策略
            </Button>
          </Space>
        }
        style={{ marginTop: 20, borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}
      >
        <Table
          columns={[
            { title: '策略名称', dataIndex: 'name', key: 'name' },
            {
              title: '类型',
              dataIndex: 'strategy_type',
              key: 'type',
              render: (t: string) => (
                <Tag
                  style={{
                    borderRadius: 6,
                    background:
                      t === 'risk_control'
                        ? 'rgba(251,113,133,0.1)'
                        : 'rgba(59,130,246,0.1)',
                    color: t === 'risk_control' ? '#fb7185' : '#60a5fa',
                    border: 'none',
                  }}
                >
                  {t === 'risk_control' ? '风控' : t}
                </Tag>
              ),
            },
            { title: '版本', dataIndex: 'version', key: 'version' },
            { title: '优先级', dataIndex: 'priority', key: 'priority' },
            {
              title: '状态',
              dataIndex: 'status',
              key: 'status',
              render: (s: string) => {
                const map: Record<string, { bg: string; color: string; label: string }> = {
                  draft: { bg: 'rgba(255,255,255,0.05)', color: '#64748b', label: '草稿' },
                  testing: { bg: 'rgba(59,130,246,0.1)', color: '#60a5fa', label: '测试中' },
                  active: { bg: 'rgba(52,211,153,0.1)', color: '#34d399', label: '活跃' },
                  archived: { bg: 'rgba(251,191,36,0.1)', color: '#fbbf24', label: '已归档' },
                };
                const m = map[s] || map.draft;
                return (
                  <Tag
                    style={{
                      borderRadius: 6,
                      background: m.bg,
                      color: m.color,
                      border: 'none',
                    }}
                  >
                    {m.label}
                  </Tag>
                );
              },
            },
            {
              title: '操作',
              key: 'action',
              render: () => (
                <Space>
                  <Button size="small" type="text" style={{ color: '#60a5fa' }}>
                    编辑
                  </Button>
                  <Button size="small" type="text" style={{ color: '#a78bfa' }}>
                    评估
                  </Button>
                </Space>
              ),
            },
          ]}
          dataSource={[]}
          pagination={false}
          locale={{ emptyText: '暂无策略，点击"新建策略"或"AI 生成策略"开始' }}
        />
      </Card>
    </div>
  );
}

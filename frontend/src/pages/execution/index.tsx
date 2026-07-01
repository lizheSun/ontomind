import { Card, Table, Tag, Space, Button, Statistic, Row, Col } from 'antd';
import { RollbackOutlined } from '@ant-design/icons';

export default function Execution() {
  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ color: '#e8eef5', fontSize: 20, fontWeight: 700, margin: 0, letterSpacing: -0.3 }}>
          执行层
        </h2>
        <p style={{ color: '#506380', margin: '4px 0 0', fontSize: 12 }}>
          策略下发与实时监控
        </p>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {[
          { k: 'active', title: '活跃策略数', val: 0, c: '#34d399' },
          { k: 'today', title: '今日执行量', val: 0, c: '#60a5fa' },
          { k: 'rate', title: '成功率', val: '0%', c: '#fbbf24' },
          { k: 'latency', title: '平均延迟', val: '0ms', c: '#a78bfa' },
        ].map((item) => (
          <Col xs={24} sm={6} key={item.k}>
            <Card
              style={{
                borderRadius: 14,
                border: '1px solid rgba(255,255,255,0.06)',
                background: `linear-gradient(135deg, ${item.c}10, ${item.c}03)`,
              }}
              styles={{ body: { padding: '18px 22px' } }}
            >
              <Statistic
                title={item.title}
                value={item.val}
                styles={{
                  content: {
                    color: item.c,
                    fontSize: 26,
                    fontWeight: 700,
                  },
                }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Card
        title={<span style={{ fontWeight: 600 }}>目标系统</span>}
        style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)', marginBottom: 20 }}
      >
        <Table
          columns={[
            { title: '系统名称', dataIndex: 'name', key: 'name' },
            {
              title: '类型',
              dataIndex: 'type',
              key: 'type',
              render: (t: string) => (
                <Tag
                  style={{
                    borderRadius: 6,
                    background: 'rgba(59,130,246,0.1)',
                    color: '#60a5fa',
                    border: 'none',
                  }}
                >
                  {t === 'risk_engine' ? '风控引擎' : '营销平台'}
                </Tag>
              ),
            },
            { title: '已下发策略', dataIndex: 'strategy_count', key: 'count' },
            {
              title: '状态',
              dataIndex: 'status',
              key: 'status',
              render: () => (
                <Tag
                  style={{
                    borderRadius: 6,
                    background: 'rgba(52,211,153,0.1)',
                    color: '#34d399',
                    border: 'none',
                  }}
                >
                  在线
                </Tag>
              ),
            },
          ]}
          dataSource={[
            { name: '风控引擎', type: 'risk_engine', strategy_count: 0, status: 'online' },
            { name: '营销平台', type: 'marketing_platform', strategy_count: 0, status: 'online' },
          ]}
          pagination={false}
          size="small"
        />
      </Card>

      <Card
        title={<span style={{ fontWeight: 600 }}>策略执行记录</span>}
        style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}
      >
        <Table
          columns={[
            { title: '策略名称', dataIndex: 'strategy_name', key: 'name' },
            { title: '目标系统', dataIndex: 'target_system', key: 'target' },
            { title: '执行时间', dataIndex: 'executed_at', key: 'time' },
            {
              title: '状态',
              dataIndex: 'status',
              key: 'status',
              render: (s: string) => {
                const map: Record<string, { bg: string; color: string; label: string }> = {
                  pending: { bg: 'rgba(100,116,139,0.1)', color: '#64748b', label: '等待中' },
                  running: { bg: 'rgba(59,130,246,0.1)', color: '#60a5fa', label: '执行中' },
                  success: { bg: 'rgba(52,211,153,0.1)', color: '#34d399', label: '成功' },
                  failed: { bg: 'rgba(251,113,133,0.1)', color: '#fb7185', label: '失败' },
                };
                const m = map[s] || map.pending;
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
                  <Button
                    size="small"
                    icon={<RollbackOutlined />}
                    type="text"
                    danger
                  >
                    回滚
                  </Button>
                </Space>
              ),
            },
          ]}
          dataSource={[]}
          pagination={false}
          locale={{ emptyText: '暂无执行记录' }}
        />
      </Card>
    </div>
  );
}

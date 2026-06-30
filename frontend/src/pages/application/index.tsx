import { Card, Row, Col, Input, Button, Table, Space } from 'antd';
import { SendOutlined, PlusOutlined, BarChartOutlined } from '@ant-design/icons';

export default function Application() {
  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ color: '#e8eef5', fontSize: 20, fontWeight: 700, margin: 0, letterSpacing: -0.3 }}>
          应用层
        </h2>
        <p style={{ color: '#506380', margin: '4px 0 0', fontSize: 12 }}>
          AIbi 智能分析与数据可视化
        </p>
      </div>

      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <SendOutlined style={{ color: '#60a5fa' }} />
            <span style={{ fontWeight: 600 }}>AIbi 智能分析</span>
          </div>
        }
        style={{
          borderRadius: 14,
          border: '1px solid rgba(255,255,255,0.06)',
          marginBottom: 20,
          background: 'linear-gradient(135deg, rgba(59,130,246,0.04), rgba(139,92,246,0.02))',
        }}
      >
        <Row gutter={16}>
          <Col flex="auto">
            <Input.TextArea
              rows={3}
              placeholder="用自然语言描述你的分析需求，例如：'分析最近30天的风控拒绝率趋势'"
              style={{
                borderRadius: 12,
                background: 'rgba(255,255,255,0.03)',
                fontSize: 14,
              }}
            />
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<SendOutlined />}
              size="large"
              style={{
                height: '100%',
                borderRadius: 12,
                minWidth: 100,
                fontWeight: 600,
              }}
            >
              分析
            </Button>
          </Col>
        </Row>

        <div
          style={{
            marginTop: 16,
            padding: 24,
            borderRadius: 12,
            background: 'rgba(255,255,255,0.02)',
            border: '1px dashed rgba(255,255,255,0.06)',
            minHeight: 120,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <span style={{ color: '#405070', fontSize: 13 }}>
            AI 分析结果将在此展示...
          </span>
        </div>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card
            title={<span style={{ fontWeight: 600 }}>数据集</span>}
            extra={
              <Button
                size="small"
                type="text"
                icon={<PlusOutlined />}
                style={{ color: '#60a5fa' }}
              >
                添加
              </Button>
            }
            style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}
          >
            <Table
              columns={[
                { title: '名称', dataIndex: 'name', key: 'name' },
                { title: '来源', dataIndex: 'source', key: 'source' },
                { title: '行数', dataIndex: 'rows', key: 'rows' },
              ]}
              dataSource={[]}
              pagination={false}
              size="small"
              locale={{ emptyText: '暂无数据集' }}
            />
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card
            title={<span style={{ fontWeight: 600 }}>仪表盘</span>}
            extra={
              <Button
                size="small"
                type="text"
                icon={<BarChartOutlined />}
                style={{ color: '#a78bfa' }}
              >
                新建图表
              </Button>
            }
            style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}
          >
            <div
              style={{
                height: 200,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: 12,
                background:
                  'radial-gradient(ellipse at center, rgba(59,130,246,0.04) 0%, transparent 70%)',
              }}
            >
              <div style={{ textAlign: 'center' }}>
                <BarChartOutlined style={{ fontSize: 40, color: '#2d3a5e', marginBottom: 12 }} />
                <p style={{ color: '#506380', fontSize: 13, margin: 0 }}>
                  创建你的第一个图表
                </p>
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

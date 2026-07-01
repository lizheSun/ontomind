import { Card, Button, Table, Tag, Space, Row, Col, Input } from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  ThunderboltOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons';

export default function Cognition() {
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
            认知层
          </h2>
          <p style={{ color: '#506380', margin: '4px 0 0', fontSize: 12 }}>
            本体图谱构建与语义分析
          </p>
        </div>
        <Space>
          <Button icon={<ThunderboltOutlined />} type="primary">
            自动抽取本体
          </Button>
          <Button icon={<PlusOutlined />} style={{ borderRadius: 10 }}>
            添加实体
          </Button>
        </Space>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <NodeIndexOutlined style={{ color: '#a78bfa' }} />
                <span style={{ fontWeight: 600 }}>本体图谱</span>
              </div>
            }
            style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}
            styles={{
              body: {
                height: 380,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background:
                  'radial-gradient(ellipse at center, rgba(139,92,246,0.04) 0%, transparent 70%)',
                borderRadius: '0 0 14px 14px',
              },
            }}
          >
            <div style={{ textAlign: 'center' }}>
              <NodeIndexOutlined
                style={{ fontSize: 52, color: '#3d2e6b', marginBottom: 16 }}
              />
              <p style={{ color: '#506380', fontSize: 14, margin: 0 }}>
                本体图谱可视化区域
              </p>
              <p style={{ color: '#304060', fontSize: 12, marginTop: 6 }}>
                连接数据源后将自动生成本体知识图谱
              </p>
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={10}>
          <Card
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <SearchOutlined style={{ color: '#60a5fa' }} />
                <span style={{ fontWeight: 600 }}>语义搜索</span>
              </div>
            }
            style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)', marginBottom: 16 }}
          >
            <Input.Search
              placeholder="输入自然语言查询..."
              enterButton={
                <Button type="primary" style={{ borderRadius: '0 10px 10px 0' }}>
                  <SearchOutlined />
                </Button>
              }
              size="large"
            />
          </Card>

          <Card
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontWeight: 600 }}>实体列表</span>
                <Tag style={{ background: 'rgba(139,92,246,0.1)', color: '#a78bfa', border: 'none', borderRadius: 6 }}>
                  0 个
                </Tag>
              </div>
            }
            style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}
          >
            <Table
              columns={[
                { title: '实体名', dataIndex: 'name', key: 'name' },
                {
                  title: '类型',
                  dataIndex: 'entity_type',
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
                      {t}
                    </Tag>
                  ),
                },
                { title: '置信度', dataIndex: 'confidence', key: 'conf' },
              ]}
              dataSource={[]}
              pagination={false}
              size="small"
              locale={{ emptyText: '暂无实体数据' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontWeight: 600 }}>本体关系</span>
          </div>
        }
        style={{ marginTop: 20, borderRadius: 14, border: '1px solid rgba(255,255,255,0.06)' }}
      >
        <Table
          columns={[
            { title: '主体', dataIndex: 'subject', key: 'subject' },
            {
              title: '关系',
              dataIndex: 'predicate',
              key: 'predicate',
              render: (p: string) => (
                <Tag
                  style={{
                    borderRadius: 6,
                    background: 'rgba(59,130,246,0.1)',
                    color: '#60a5fa',
                    border: 'none',
                  }}
                >
                  {p}
                </Tag>
              ),
            },
            { title: '客体', dataIndex: 'object', key: 'object' },
            { title: '置信度', dataIndex: 'confidence', key: 'confidence' },
          ]}
          dataSource={[]}
          pagination={false}
          locale={{ emptyText: '暂无关系数据' }}
        />
      </Card>
    </div>
  );
}

import { Card, Button, Table, Tag, Space, Row, Col, Input } from 'antd';
import { PlusOutlined, SearchOutlined, ThunderboltOutlined } from '@ant-design/icons';

export default function Cognition() {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
        <h2>认知层 — 本体图谱构建</h2>
        <Space>
          <Button icon={<ThunderboltOutlined />} type="primary">自动抽取本体</Button>
          <Button icon={<PlusOutlined />}>添加实体</Button>
        </Space>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card title="本体图谱" bodyStyle={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fafafa' }}>
            <div style={{ textAlign: 'center', color: '#999' }}>
              <NodeIndexOutlined style={{ fontSize: 48 }} />
              <p style={{ marginTop: 16 }}>本体图谱可视化区域</p>
              <p style={{ fontSize: 12 }}>连接数据源后自动生成知识图谱</p>
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title="语义搜索">
            <Input.Search placeholder="输入自然语言查询..." enterButton={<SearchOutlined />} size="large" />
          </Card>
          <Card title="实体列表" style={{ marginTop: 16 }}>
            <Table
              columns={[
                { title: '实体名', dataIndex: 'name', key: 'name' },
                { title: '类型', dataIndex: 'entity_type', key: 'type', render: (t: string) => <Tag>{t}</Tag> },
                { title: '置信度', dataIndex: 'confidence', key: 'conf' },
              ]}
              dataSource={[]}
              pagination={false}
              size="small"
              locale={{ emptyText: '暂无实体' }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="本体关系" style={{ marginTop: 24 }}>
        <Table
          columns={[
            { title: '主体', dataIndex: 'subject', key: 'subject' },
            { title: '关系', dataIndex: 'predicate', key: 'predicate', render: (p: string) => <Tag color="blue">{p}</Tag> },
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

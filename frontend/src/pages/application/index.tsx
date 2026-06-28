import { Card, Row, Col, Input, Button, Table, Tag, Space } from 'antd';
import { SendOutlined, PlusOutlined, BarChartOutlined } from '@ant-design/icons';

export default function Application() {
  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>应用层 — AIbi 智能分析 & 数据可视化</h2>

      <Card title="AIbi 智能分析" style={{ marginBottom: 24 }}>
        <Row gutter={16}>
          <Col flex="auto">
            <Input.TextArea rows={3} placeholder="用自然语言描述你的分析需求，例如：'分析最近30天的风控拒绝率趋势'" />
          </Col>
          <Col>
            <Button type="primary" icon={<SendOutlined />} size="large" style={{ height: '100%' }}>分析</Button>
          </Col>
        </Row>
        <div style={{ marginTop: 16, padding: 16, background: '#fafafa', borderRadius: 8, minHeight: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
          AI 分析结果将在此展示...
        </div>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="数据集" extra={<Button size="small" icon={<PlusOutlined />}>添加</Button>}>
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
          <Card title="仪表盘" extra={<Button size="small" icon={<BarChartOutlined />}>新建图表</Button>}>
            <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fafafa', borderRadius: 8 }}>
              <div style={{ textAlign: 'center', color: '#999' }}>
                <BarChartOutlined style={{ fontSize: 36 }} />
                <p style={{ marginTop: 8 }}>创建你的第一个图表</p>
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
